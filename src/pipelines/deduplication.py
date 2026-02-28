import os
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
        - Step D: Calculate exact Jaccard similarity (threshold >= 0.9)
    
    NOTE: Removed file-based cache layer for simpler, DB-only deduplication
    """

    JACCARD_THRESHOLD = 0.9  # 90% similarity = duplicate

    def __init__(self):
        self.deduplicator = MinHashDeduplicator(num_perm=128, num_bands=16)
        self.stats = {
            "near_dup": 0, 
            "unique": 0,
            "lsh_candidates_found": 0,
            "jaccard_verifications": 0,
        }
        self.repo: JobRepository | None = None
        self.Session = None

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
            f"DeduplicationPipeline: Database-backed LSH with Jaccard verification enabled (threshold={self.JACCARD_THRESHOLD})"
        )

    def process_item(self, item, spider):
        """
        Check for duplicates using database-backed LSH with Jaccard verification
        """
        adapter = ItemAdapter(item)
        url = adapter.get("job_url", "")

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
                    spider
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
                                f"{max_dups} consecutive duplicates reached, closing spider immediately."
                            )
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
        
        Combines: title + description + requirements
        """
        text_parts = [
            adapter.get("title", ""),
            adapter.get("description", ""),
            adapter.get("requirements", ""),
        ]
        return " ".join(filter(None, text_parts))

    def _verify_candidates_exact(
        self, 
        session, 
        query_minhash, 
        candidate_job_ids: set[str], 
        spider
    ) -> tuple[bool, str | None, float]:
        """
        Verify candidates using EXACT Jaccard similarity calculation.
        
        :param session: Database session
        :param query_minhash: MinHash object of current job
        :param candidate_job_ids: Set of candidate job IDs from LSH query
        :param spider: Spider instance for logging
        :return: (is_duplicate, duplicate_job_id, similarity_score)
        
        Algorithm:
        1. Fetch all candidate signatures from database
        2. Calculate exact Jaccard similarity for each candidate
        3. If any candidate has similarity >= threshold, mark as duplicate
        """
        # Step 1: Fetch all candidate signatures from database
        candidate_signatures = self.repo.get_signatures(session, list(candidate_job_ids))
        
        if not candidate_signatures:
            spider.logger.warning(
                f"LSH found {len(candidate_job_ids)} candidates but none have stored signatures"
            )
            return False, None, 0.0
        
        spider.logger.debug(
            f"Fetched {len(candidate_signatures)} signatures for Jaccard verification"
        )
        
        # Step 2: Calculate exact Jaccard similarity for each candidate
        max_similarity = 0.0
        best_match_id = None
        
        for candidate_job_id, candidate_signature_array in candidate_signatures.items():
            self.stats["jaccard_verifications"] += 1
            
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
                spider.logger.info(
                    f"DUPLICATE FOUND: Jaccard similarity = {similarity:.4f} >= {self.JACCARD_THRESHOLD} "
                    f"with job {candidate_job_id}"
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
        spider.logger.info(f"  LSH candidates found: {self.stats['lsh_candidates_found']}")
        spider.logger.info(f"  Jaccard verifications performed: {self.stats['jaccard_verifications']}")
        spider.logger.info("=" * 60)


