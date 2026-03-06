import logging
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session
from sqlalchemy import text
from models import Job, Location, Skill, Domain
from models.associations import job_skills, job_domain
from utils.skill_normalizer import SkillNormalizer
from utils.normalizer import DataNormalizer

logger = logging.getLogger(__name__)


class JobRepository:
    def __init__(self, session_factory):
        self.Session = session_factory
        self.skill_normalizer = SkillNormalizer()
        self.normalizer = DataNormalizer()

    def save_batch(self, items: list[dict]) -> int:
        """Batch upsert jobs + dimensions. Returns number of jobs saved."""
        saved = 0
        with self.Session() as session:
            for item in items:
                try:
                    location = self._upsert_location(session, item)
                    
                    # Extract MinHash signature if present
                    signature = item.get('minhash_signature')
                    
                    job = self._upsert_job(session, item, location, signature)
                    self._upsert_skills(session, item, job)
                    
                    # NEW: Upsert domains if present
                    domains_list = self._extract_domains_from_item(item)
                    if domains_list:
                        self._upsert_domains(session, job.id, job.posted_date, domains_list)
                    
                    # NEW: Save LSH buckets if present
                    lsh_buckets = item.get('lsh_buckets')
                    if lsh_buckets:
                        self.save_lsh_buckets(session, job.id, job.posted_date, lsh_buckets)
                    
                    saved += 1
                except Exception as e:
                    session.rollback()
                    logger.warning(f"Failed to save job {item.get('job_url')}: {e}")
                    continue
            session.commit()
        return saved

    def _upsert_location(self, session: Session, item: dict) -> Location | None:
        extra_data = item.get("extra_data") or {}
        # extra_data['location_city'] is already parsed by the spider's field_extractor
        raw = extra_data.get("location_city") or item.get("location_raw")
        if not raw:
            return None

        city_slug, _ = self.normalizer.normalize_location_to_province(raw)
        if not city_slug:
            logger.debug(f"Location not mapped to province: '{raw}'")
            return None

        # Only lookup — locations are pre-seeded (63 provinces)
        return session.query(Location).filter_by(city_name=city_slug).first()

    def _upsert_job(self, session: Session, item: dict, location: Location | None, signature: list[int] | None = None) -> Job:
        """
        Upsert job with optional MinHash signature
        
        :param session: SQLAlchemy session
        :param item: Job item dict
        :param location: Location object
        :param signature: MinHash signature (list of 128 integers)
        :return: Job object
        """
        source = item.get("source", "")
        skills_tags = item.get("skills_tags") or []
        if isinstance(skills_tags, str):
            skills_tags = [s.strip() for s in skills_tags.split(",")]

        # --- Salary ---
        salary_min = item.get("salary_min")
        salary_max = item.get("salary_max")
        salary_currency = item.get("salary_currency", "VND")
        if source == "topcv":
            salary_raw = item.get("salary_raw") or ""
            parsed_salary = DataNormalizer.parse_salary_topcv(salary_raw)
            if parsed_salary:
                salary_min      = parsed_salary.get("salary_min")
                salary_max      = parsed_salary.get("salary_max")
                salary_currency = parsed_salary.get("salary_currency", "VND")

        # --- Experience ---
        experience = item.get("experience_required")
        if not experience and source == "topcv":
            experience = DataNormalizer.extract_experience_from_tags(skills_tags)
        if not experience:
            experience = DataNormalizer.extract_experience_from_text(item.get("requirements") or "")

        values = {
            "id": item.get("job_id"),
            "posted_date": item.get("date_posted") or item.get("crawl_date"),
            "source": source,
            "title": item.get("title"),
            "company_name": item.get("company_name"),
            "url": item.get("job_url"),
            "salary_min": salary_min,
            "salary_max": salary_max,
            "salary_currency": salary_currency,
            "experience": experience,
            "location_id": location.id if location else None,
        }
        
        # Add MinHash signature if provided
        if signature is not None:
            # Convert numpy types to Python int for psycopg2 compatibility
            values["minhash_signature"] = [int(x) for x in signature]
        
        stmt = insert(Job).values(**values).on_conflict_do_update(
            index_elements=["id", "posted_date"],
            set_={"last_seen": "now()"},
        )
        session.execute(stmt)
        return session.query(Job).filter_by(id=item["job_id"]).first()

    def _upsert_skills(self, session: Session, item: dict, job: Job):
        skills_raw = item.get("skills_tags") or item.get("skills_required") or []
        if isinstance(skills_raw, str):
            skills_raw = [s.strip() for s in skills_raw.split(",")]

        seen: set[str] = set()
        for skill_name in skills_raw:
            if not skill_name:
                continue

            # Normalize to canonical form
            canonical = self.skill_normalizer.normalize(skill_name)
            if not canonical or canonical in seen:
                continue
            seen.add(canonical)

            category = self.skill_normalizer.get_category(canonical)

            # Upsert skill with category
            set_clause = {"category": category} if category else {}
            stmt = insert(Skill).values(
                name=canonical,
                category=category,
            ).on_conflict_do_update(
                index_elements=["name"],
                set_=set_clause,
            ) if set_clause else insert(Skill).values(
                name=canonical,
                category=category,
            ).on_conflict_do_nothing(index_elements=["name"])
            session.execute(stmt)

            skill = session.query(Skill).filter_by(name=canonical).first()
            session.execute(
                insert(job_skills).values(
                    job_id=job.id,
                    skill_id=skill.id,
                    posted_date=job.posted_date,
                ).on_conflict_do_nothing()
            )

    def _extract_domains_from_item(self, item: dict) -> list[str]:
        """
        Extract domain list from item.
        
        Supports:
        - item['domains'] (direct list from SkillExtractor)
        - item['extra_data']['domains'] (from spider extra_data)
        
        :param item: Job item dict
        :return: List of domain names
        """
        # Check direct 'domains' field
        domains = item.get('domains')
        if domains and isinstance(domains, list):
            return [d.strip() for d in domains if d and d.strip()]
        
        # Check extra_data
        extra_data = item.get('extra_data', {})
        if isinstance(extra_data, dict):
            domains = extra_data.get('domains')
            if domains and isinstance(domains, list):
                return [d.strip() for d in domains if d and d.strip()]
        
        return []

    def _upsert_domains(self, session: Session, job_id: str, posted_date: str, domains_list: list[str]):
        """
        Upsert domains and create job-domain associations.
        
        :param session: SQLAlchemy session
        :param job_id: Job UUID
        :param posted_date: Job posting date
        :param domains_list: List of domain names (e.g., ['Fintech', 'E-commerce'])
        """
        if not domains_list:
            return
        
        for domain_name in domains_list:
            if not domain_name or not domain_name.strip():
                continue
            
            domain_name = domain_name.strip()
            
            # Insert domain if not exists
            stmt = insert(Domain).values(
                name=domain_name
            ).on_conflict_do_nothing(index_elements=["name"])
            session.execute(stmt)
            
            # Get domain ID
            domain = session.query(Domain).filter_by(name=domain_name).first()
            
            if domain:
                # Insert into job_domain association table
                session.execute(
                    insert(job_domain).values(
                        job_id=job_id,
                        domain_id=domain.id,
                        posted_date=posted_date,
                    ).on_conflict_do_nothing()
                )
                logger.debug(f"Associated job {job_id} with domain '{domain_name}'")

    def check_lsh_candidates(self, session: Session, buckets: list[tuple[int, str]]) -> set[str]:
        """
        Query LSH buckets to find candidate duplicate job IDs.
        
        OPTIMIZED: Uses single IN clause with tuples instead of loop with OR conditions.
        
        :param session: SQLAlchemy session
        :param buckets: List of (band_idx, bucket_hash) tuples (16 buckets from MinHash)
        :return: Set of job_id candidates that share any bucket
        
        Example:
            buckets = [(0, 'abc123'), (1, 'def456'), ...]
            Returns: {'job_uuid_1', 'job_uuid_2', ...}
        """
        if not buckets:
            return set()
        
        try:
            # PostgreSQL supports: WHERE (band_idx, bucket_hash) IN ((0, 'abc'), (1, 'def'))
            # Build the query with bound parameters
            query = text("""
                SELECT DISTINCT job_id 
                FROM lsh_buckets 
                WHERE (band_idx, bucket_hash) IN :buckets
            """)
            
            # Execute query with tuple list
            result = session.execute(
                query,
                {"buckets": tuple(buckets)}
            )
            
            candidates = {row[0] for row in result}
            
            if candidates:
                logger.debug(f"LSH query: Found {len(candidates)} candidate duplicates from {len(buckets)} buckets")
            
            return candidates
            
        except Exception as e:
            logger.error(f"Error querying LSH buckets: {e}")
            return set()

    def get_signatures(self, session: Session, job_ids: list[str]) -> dict[str, dict]:
        """
        Fetch MinHash signatures, posted_date, company_name, and location_id
        for a list of job IDs.
        
        :param session: SQLAlchemy session
        :param job_ids: List of job UUID strings
        :return: Dictionary mapping job_id -> {
            "signature": list[int],
            "posted_date": datetime,
            "company_name": str | None,
            "location_id": int | None,
        }
        """
        if not job_ids:
            return {}
        
        try:
            query = text("""
                SELECT id, minhash_signature, posted_date, company_name, location_id
                FROM jobs 
                WHERE id = ANY(:job_ids)
                AND minhash_signature IS NOT NULL
            """)
            
            result = session.execute(query, {"job_ids": list(job_ids)})
            
            # Build dictionary
            signatures = {}
            for row in result:
                job_id = str(row[0])
                signature = row[1]  # PostgreSQL ARRAY mapped to Python list
                posted_date = row[2]
                company_name = row[3]
                location_id = row[4]
                if signature:
                    signatures[job_id] = {
                        "signature": signature,
                        "posted_date": posted_date,
                        "company_name": company_name,
                        "location_id": location_id,
                    }
            
            logger.debug(f"Fetched {len(signatures)} signatures for {len(job_ids)} candidates")
            return signatures
            
        except Exception as e:
            logger.error(f"Error fetching MinHash signatures: {e}")
            return {}

    def save_lsh_buckets(self, session: Session, job_id: str, posted_date: str, buckets: list[tuple[int, str]]):
        """
        Save LSH bucket assignments for a job to enable future deduplication.
        
        :param session: SQLAlchemy session
        :param job_id: Job UUID
        :param posted_date: Job posting date (unused, kept for backward compatibility)
        :param buckets: List of (band_idx, bucket_hash) tuples (typically 16 bands)
        
        Example:
            buckets = [
                (0, 'abc123def456'),
                (1, 'def456ghi789'),
                ...
                (15, 'xyz789abc012')
            ]
        """
        if not buckets:
            logger.warning(f"No LSH buckets provided for job {job_id}")
            return
        
        try:
            # Batch insert using raw SQL for better performance
            for band_idx, bucket_hash in buckets:
                insert_sql = text("""
                    INSERT INTO lsh_buckets (band_idx, bucket_hash, job_id)
                    VALUES (:band_idx, :bucket_hash, :job_id)
                    ON CONFLICT (band_idx, bucket_hash, job_id) DO NOTHING
                """)
                session.execute(insert_sql, {
                    'band_idx': band_idx,
                    'bucket_hash': bucket_hash,
                    'job_id': job_id
                })
            
            logger.debug(f"Saved {len(buckets)} LSH buckets for job {job_id}")
            
        except Exception as e:
            logger.error(f"Error saving LSH buckets for job {job_id}: {e}")
            raise

    def get_job_minhash_signature(self, session: Session, job_id: str) -> list[tuple[int, str]] | None:
        """
        Retrieve stored LSH buckets for a job (for manual similarity checks).
        
        :param session: SQLAlchemy session
        :param job_id: Job UUID
        :return: List of (band_idx, bucket_hash) tuples or None if not found
        """
        try:
            query = text("""
                SELECT band_idx, bucket_hash 
                FROM lsh_buckets 
                WHERE job_id = :job_id 
                ORDER BY band_idx
            """)
            
            result = session.execute(query, {"job_id": job_id})
            buckets = [(row[0], row[1]) for row in result]
            
            return buckets if buckets else None
            
        except Exception as e:
            logger.error(f"Error retrieving LSH signature for job {job_id}: {e}")
            return None

    def delete_old_lsh_buckets(self, session: Session, days_old: int = 90):
        """
        Clean up old LSH buckets to prevent table bloat.
        
        :param session: SQLAlchemy session
        :param days_old: Delete buckets older than this many days
        :return: Number of rows deleted
        """
        try:
            delete_sql = text("""
                DELETE FROM lsh_buckets 
                WHERE posted_date < NOW() - INTERVAL ':days days'
            """)
            
            result = session.execute(delete_sql, {"days": days_old})
            deleted_count = result.rowcount
            session.commit()
            
            logger.info(f"Deleted {deleted_count} old LSH bucket entries (>{days_old} days)")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error deleting old LSH buckets: {e}")
            session.rollback()
            return 0

    def get_max_posted_date(self, source: str = None):
        """Return max(posted_date) from jobs table filtered by source.
        
        :param source: Source name to filter (e.g. 'itviec', 'topcv', 'linkedin').
                       If None, queries across all sources.
        :return: datetime.date or None (None means no jobs from that source yet).
        """
        with self.Session() as session:
            if source:
                result = session.execute(
                    text("SELECT MAX(posted_date) FROM jobs WHERE source = :source"),
                    {"source": source}
                ).scalar()
            else:
                result = session.execute(text("SELECT MAX(posted_date) FROM jobs")).scalar()
            return result  # datetime.date or None

    def has_lsh_entry(self, session: Session, job_id: str) -> bool:
        """
        Check whether a job has been previously indexed (has LSH buckets stored).
        Uses lsh_buckets table — LSH infrastructure — not jobs.id directly.
        If a job_id exists in lsh_buckets, it was fully crawled and indexed before.
        """
        result = session.execute(
            text("SELECT 1 FROM lsh_buckets WHERE job_id = :job_id LIMIT 1"),
            {"job_id": job_id}
        ).first()
        return result is not None
