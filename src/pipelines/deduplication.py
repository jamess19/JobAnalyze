import os
import hashlib
from datetime import datetime, timedelta, date as date_type
from scrapy.exceptions import DropItem
from itemadapter import ItemAdapter
from utils.deduplicator import MinHashDeduplicator
from models.base import get_engine, get_session_factory
from repositories.job_repository import JobRepository


class DeduplicationPipeline:
    """
    Database-backed deduplication with EXACT Jaccard verification:
    
    Single layer: MinHash LSH (database-backed) with full Jaccard verification
        - Step A: Generate MinHash signature (128 integers)
        - Step B: Query LSH buckets for candidates
        - Step C: Fetch candidate signatures from DB
        - Step D: Calculate exact Jaccard similarity (threshold >= 0.85)
                  + metadata guard (company_name AND location_id must match)
    
    Also includes an in-memory batch cache to prevent race conditions
    where identical jobs enter the pipeline simultaneously.
    """

    JACCARD_THRESHOLD = 0.85  # 85% similarity = duplicate candidate (was 0.9)
    REPOST_DAYS_THRESHOLD = 30  # days apart to consider a duplicate as a repost

    def __init__(self):
        self.deduplicator = MinHashDeduplicator(num_perm=128, num_bands=16)
        self.stats = {
            "near_dup": 0, 
            "unique": 0,
            "reposted": 0,
            "lsh_candidates_found": 0,
            "jaccard_verifications": 0,
            "batch_dup": 0,
            "metadata_mismatch": 0,
        }
        self.repo: JobRepository | None = None
        self.Session = None

        # ── Race condition protection ──
        # In-memory cache keyed by md5(title|company_name) to catch items
        # with identical (title, company) that arrive within the same batch
        # before any of them reach the database.
        self._batch_cache: dict[str, str] = {}  # cache_key → job_url (first seen)

    @classmethod
    def from_crawler(cls, crawler):
        """Create pipeline from Scrapy crawler settings"""
        pipeline = cls()
        pipeline.database_url = crawler.settings.get("DATABASE_URL")
        return pipeline

    def open_spider(self, spider):
        """Initialize database connection"""
        # Initialize database connection
        engine = get_engine(self.database_url)
        self.Session = get_session_factory(engine)
        self.repo = JobRepository(self.Session)
        
        spider.logger.info(
            f"DeduplicationPipeline: Database-backed LSH with Jaccard verification enabled "
            f"(threshold={self.JACCARD_THRESHOLD}, metadata_guard=company+location)"
        )

    def process_item(self, item, spider):
        """
        Check for duplicates using database-backed LSH with Jaccard verification.
        
        Flow:
        1. Batch cache check (race condition guard)
        2. MinHash LSH → find candidates → Jaccard verify → metadata guard
        """
        adapter = ItemAdapter(item)
        url = adapter.get("job_url", "")
        title = adapter.get("title", "") or ""
        company_name = adapter.get("company_name", "") or ""
        current_date_posted = adapter.get("date_posted", "")

        # ==================== BATCH CACHE (RACE CONDITION GUARD) ====================
        # Prevent identical (title, company) items from slipping through when
        # they arrive within the same batch before any is persisted to DB.
        cache_key = hashlib.md5(
            f"{title.strip()}|{company_name.strip()}".lower().encode()
        ).hexdigest()

        if title.strip() and company_name.strip() and cache_key in self._batch_cache:
            self.stats["batch_dup"] += 1
            first_url = self._batch_cache[cache_key]
            # Update consecutive dup counter
            is_vip = adapter.get('is_vip', False)
            if hasattr(spider, 'consecutive_dup_count') and not is_vip:
                spider.consecutive_dup_count += 1
            raise DropItem(
                f"Batch duplicate: same (title, company) as {first_url}"
            )

        # ==================== MINHASH LSH + JACCARD VERIFICATION ====================
        
        # Step A: Generate MinHash signature (128 integers)
        text = self._build_text_for_comparison(adapter)
        
        if not text.strip():
            spider.logger.warning(f"Empty text for deduplication: {url}")
            # Allow empty items through (will be caught by validation)
            self.stats["unique"] += 1
            self._mark_as_seen(url, text)
            return item
        
        # Compute MinHash signature
        minhash = self.deduplicator.compute_signature(text)
        # Convert numpy.uint64 to Python int to avoid psycopg2 type error
        signature_array = [int(x) for x in minhash.hashvalues]  # 128 integers
        buckets = self.deduplicator.get_buckets(minhash)
        
        # Step B: Query database for candidate duplicates using LSH buckets
        with self.Session() as session:
            candidate_job_ids = self.repo.check_lsh_candidates(session, buckets)
            
            if candidate_job_ids:
                self.stats["lsh_candidates_found"] += len(candidate_job_ids)
                spider.logger.debug(f"LSH found {len(candidate_job_ids)} candidates for {url}")
                
                # Step C: Verify candidates using EXACT Jaccard similarity
                is_duplicate, duplicate_job_id, similarity_score = self._verify_candidates_exact(
                    session, 
                    minhash, 
                    candidate_job_ids, 
                    spider,
                    current_date_posted,
                    adapter,
                )
                
                if is_duplicate:
                    self.stats["near_dup"] += 1
                    # Update consecutive dup counter on spider (VIP jobs are excluded)
                    is_vip = adapter.get('is_vip', False)
                    if hasattr(spider, 'consecutive_dup_count') and not is_vip:
                        spider.consecutive_dup_count += 1
                        max_dups = getattr(spider, 'MAX_CONSECUTIVE_DUPS', 15)
                        spider.logger.debug(
                            f"Consecutive duplicates: {spider.consecutive_dup_count}/{max_dups}"
                        )
                        if spider.consecutive_dup_count >= max_dups:
                            spider.logger.info(
                                f"{max_dups} consecutive duplicates reached for current keyword."
                            )
                            if getattr(spider, 'per_keyword_stop', False):
                                # Per-keyword stop: only break the current keyword's scroll loop
                                spider.should_stop = True
                            else:
                                spider.crawler.engine.close_spider(spider, 'consecutive_duplicates_limit_reached')
                    raise DropItem(
                        f"Near-duplicate detected: {url} is {similarity_score:.2%} similar to job {duplicate_job_id} (threshold={self.JACCARD_THRESHOLD})"
                    )
        
        # ==================== UNIQUE ITEM ====================
        self.stats["unique"] += 1
        
        # Reset consecutive dup counter on spider
        if hasattr(spider, 'consecutive_dup_count'):
            spider.consecutive_dup_count = 0
        
        # Mark URL as seen (Layer 1)
        self._mark_as_seen(url, text)
        
        # Add to batch cache (race condition guard)
        if title.strip() and company_name.strip():
            self._batch_cache[cache_key] = url
        
        # Attach MinHash data to item for DatabasePipeline to persist
        item['lsh_buckets'] = buckets
        item['minhash_signature'] = signature_array  # Store for future verification
        
        spider.logger.debug(
            f"Unique job: {url} (attached {len(buckets)} LSH buckets + signature)"
        )
        
        return item

    def _build_text_for_comparison(self, adapter: ItemAdapter) -> str:
        """
        Build combined text for MinHash comparison
        
        Combines: title + company_name + description + requirements
        
        Including company_name improves LSH bucketing accuracy — jobs from
        same company with similar JD land in the same bucket more often.
        """
        text_parts = [
            adapter.get("title", ""),
            adapter.get("company_name", ""),
            adapter.get("description", ""),
            adapter.get("requirements", ""),
        ]
        return " ".join(filter(None, text_parts))

    def _verify_candidates_exact(
        self, 
        session, 
        query_minhash, 
        candidate_job_ids: set[str], 
        spider,
        current_date_posted: str = "",
        adapter: ItemAdapter | None = None,
    ) -> tuple[bool, str | None, float]:
        """
        Verify candidates using EXACT Jaccard similarity calculation.
        After passing Jaccard threshold, applies metadata guard:
          - company_name AND location_id must BOTH match to confirm duplicate
          - If either differs → different job (same JD posted for different position)
        
        If a duplicate is found but the posting dates differ by >= REPOST_DAYS_THRESHOLD,
        treat it as a repost (new hiring need) and allow it through.
        
        :param session: Database session
        :param query_minhash: MinHash object of current job
        :param candidate_job_ids: Set of candidate job IDs from LSH query
        :param spider: Spider instance for logging
        :param current_date_posted: Date posted of the current item (YYYY-MM-DD string)
        :param adapter: ItemAdapter of current item (for metadata comparison)
        :return: (is_duplicate, duplicate_job_id, similarity_score)
        """
        # Step 1: Fetch all candidate signatures + metadata from database
        candidate_data_map = self.repo.get_signatures(session, list(candidate_job_ids))
        
        if not candidate_data_map:
            spider.logger.warning(
                f"LSH found {len(candidate_job_ids)} candidates but none have stored signatures"
            )
            return False, None, 0.0
        
        spider.logger.debug(
            f"Fetched {len(candidate_data_map)} signatures for Jaccard verification"
        )
        
        # Parse current item's posted date for comparison
        current_date = None
        if current_date_posted:
            try:
                if isinstance(current_date_posted, str):
                    current_date = datetime.strptime(current_date_posted, "%Y-%m-%d")
                elif isinstance(current_date_posted, datetime):
                    current_date = current_date_posted
            except (ValueError, TypeError):
                spider.logger.warning(f"Could not parse current date_posted: {current_date_posted}")
        
        # Extract current item's metadata for guard check
        current_company = ""
        current_location_id = None
        if adapter:
            current_company = (adapter.get("company_name", "") or "").strip().lower()
            # location_id is resolved by DatabasePipeline later, but we can
            # use location_raw for a best-effort comparison.  For now we'll
            # compare against the DB's location_id if available.
        
        # Step 2: Calculate exact Jaccard similarity for each candidate
        max_similarity = 0.0
        best_match_id = None
        
        for candidate_job_id, candidate_data in candidate_data_map.items():
            self.stats["jaccard_verifications"] += 1
            
            candidate_signature_array = candidate_data["signature"]
            candidate_posted_date = candidate_data["posted_date"]
            candidate_company = (candidate_data.get("company_name") or "").strip().lower()
            candidate_location_id = candidate_data.get("location_id")
            
            # Reconstruct MinHash object from stored signature
            candidate_minhash = self._reconstruct_minhash(candidate_signature_array)
            
            # Calculate exact Jaccard similarity
            similarity = self.deduplicator.compute_similarity(query_minhash, candidate_minhash)
            
            spider.logger.debug(
                f"Jaccard similarity with job {candidate_job_id}: {similarity:.4f}"
            )
            
            # Track best match
            if similarity > max_similarity:
                max_similarity = similarity
                best_match_id = candidate_job_id
            
            # Step 3: Check threshold
            if similarity >= self.JACCARD_THRESHOLD:
                # ── Metadata guard: company_name AND location_id must BOTH match ──
                # Same JD posted by different company or in different city = different job
                if current_company and candidate_company:
                    if current_company != candidate_company:
                        self.stats["metadata_mismatch"] += 1
                        spider.logger.info(
                            f"METADATA GUARD: Jaccard={similarity:.4f} >= {self.JACCARD_THRESHOLD} "
                            f"but company differs: current='{current_company}' vs "
                            f"candidate='{candidate_company}' (job {candidate_job_id}) → NOT duplicate"
                        )
                        continue

                # Location guard: if both have location_id and they differ → not duplicate
                if current_location_id is not None and candidate_location_id is not None:
                    if current_location_id != candidate_location_id:
                        self.stats["metadata_mismatch"] += 1
                        spider.logger.info(
                            f"METADATA GUARD: Jaccard={similarity:.4f} >= {self.JACCARD_THRESHOLD} "
                            f"but location differs: current={current_location_id} vs "
                            f"candidate={candidate_location_id} (job {candidate_job_id}) → NOT duplicate"
                        )
                        continue

                # Step 3a: Check if this is a repost (dates differ >= 30 days)
                if current_date and candidate_posted_date:
                    try:
                        if isinstance(candidate_posted_date, str):
                            db_date = datetime.strptime(candidate_posted_date, "%Y-%m-%d")
                        else:
                            db_date = candidate_posted_date
                            if isinstance(db_date, date_type) and not isinstance(db_date, datetime):
                                # bare date object → convert to datetime
                                db_date = datetime.combine(db_date, datetime.min.time())
                        
                        date_diff = abs((current_date - db_date).days)
                        
                        if date_diff >= self.REPOST_DAYS_THRESHOLD:
                            self.stats["reposted"] += 1
                            spider.logger.info(
                                f"REPOST DETECTED: {candidate_job_id} similar ({similarity:.2%}) "
                                f"but dates differ by {date_diff} days "
                                f"(current={current_date_posted}, db={candidate_posted_date}) "
                                f">= {self.REPOST_DAYS_THRESHOLD}d → treating as NEW job"
                            )
                            # Skip this candidate — it's a repost, not a true duplicate
                            continue
                    except (ValueError, TypeError) as e:
                        spider.logger.warning(
                            f"Could not compare dates for repost check: {e}"
                        )
                
                # Step 3b: True duplicate (same content + same company + same location, posted within 30 days)
                spider.logger.info(
                    f"DUPLICATE FOUND: Jaccard similarity = {similarity:.4f} >= {self.JACCARD_THRESHOLD} "
                    f"with job {candidate_job_id} "
                    f"(company='{candidate_company}', location={candidate_location_id})"
                )
                return True, candidate_job_id, similarity
        
        # No duplicates found
        spider.logger.debug(
            f"No duplicates found. Best match: {best_match_id} with {max_similarity:.4f} similarity"
        )
        return False, None, max_similarity

    def _reconstruct_minhash(self, signature_array: list[int]):
        """
        Reconstruct MinHash object from stored signature array.
        
        :param signature_array: List of 128 integers (may contain numpy types from DB)
        :return: MinHash object
        """
        from datasketch import MinHash
        
        mh = MinHash(num_perm=self.deduplicator.num_perm)
        # Ensure values are Python int (convert from numpy if needed)
        safe_values = [int(x) for x in signature_array]
        mh.hashvalues[:] = safe_values
        return mh

    def _mark_as_seen(self, url: str, text: str):
        """
        Mark URL and text as seen
        
        :param url: Job URL
        :param text: Job text (for in-memory LSH index)
        """
        # Add to in-memory LSH index (for within-session dedup only)
        if text.strip():
            self.deduplicator.add(text)

    def close_spider(self, spider):
        """Log deduplication statistics"""
        spider.logger.info("=" * 60)
        spider.logger.info("Deduplication Statistics:")
        spider.logger.info(f"  Unique jobs: {self.stats['unique']}")
        spider.logger.info(f"  Near duplicates (Jaccard >= {self.JACCARD_THRESHOLD}): {self.stats['near_dup']}")
        spider.logger.info(f"  Batch duplicates (same title+company in-flight): {self.stats['batch_dup']}")
        spider.logger.info(f"  Metadata mismatches (diff company/location): {self.stats['metadata_mismatch']}")
        spider.logger.info(f"  Reposted jobs (>={self.REPOST_DAYS_THRESHOLD}d apart): {self.stats['reposted']}")
        spider.logger.info(f"  LSH candidates found: {self.stats['lsh_candidates_found']}")
        spider.logger.info(f"  Jaccard verifications performed: {self.stats['jaccard_verifications']}")
        spider.logger.info("=" * 60)
