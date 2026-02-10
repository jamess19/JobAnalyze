import logging
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session
from models import Job, Location, Skill, Domain
from models.associations import job_skills

logger = logging.getLogger(__name__)


class JobRepository:
    def __init__(self, session_factory):
        self.Session = session_factory

    def save_batch(self, items: list[dict]) -> int:
        """Batch upsert jobs + dimensions. Returns number of jobs saved."""
        saved = 0
        with self.Session() as session:
            for item in items:
                try:
                    location = self._upsert_location(session, item)
                    job = self._upsert_job(session, item, location)
                    self._upsert_skills(session, item, job)
                    saved += 1
                except Exception as e:
                    session.rollback()
                    logger.warning(f"Failed to save job {item.get('job_url')}: {e}")
                    continue
            session.commit()
        return saved

    def _upsert_location(self, session: Session, item: dict) -> Location | None:
        city = item.get("location_raw") or item.get("location_city")
        if not city:
            return None

        stmt = insert(Location).values(
            city_name=city, country="Vietnam", raw_name=item.get("location_raw")
        ).on_conflict_do_nothing(index_elements=["city_name"])
        session.execute(stmt)

        return session.query(Location).filter_by(city_name=city).first()

    def _upsert_job(self, session: Session, item: dict, location: Location | None) -> Job:
        stmt = insert(Job).values(
            id=item.get("job_id"),
            posted_date=item.get("date_posted") or item.get("crawl_date"),
            source=item.get("source"),
            title=item.get("title"),
            company_name=item.get("company_name"),
            url=item.get("job_url"),
            salary_min=item.get("salary_min"),
            salary_max=item.get("salary_max"),
            salary_currency=item.get("salary_currency", "VND"),
            experience=item.get("experience_required"),
            location_id=location.id if location else None,
        ).on_conflict_do_update(
            index_elements=["id", "posted_date"],
            set_={"last_seen": "now()"},
        )
        session.execute(stmt)
        return session.query(Job).filter_by(id=item["job_id"]).first()

    def _upsert_skills(self, session: Session, item: dict, job: Job):
        skills_raw = item.get("skills_tags") or item.get("skills_required") or []
        if isinstance(skills_raw, str):
            skills_raw = [s.strip() for s in skills_raw.split(",")]

        for skill_name in skills_raw:
            if not skill_name:
                continue
            stmt = insert(Skill).values(
                name=skill_name
            ).on_conflict_do_nothing(index_elements=["name"])
            session.execute(stmt)

            skill = session.query(Skill).filter_by(name=skill_name).first()
            session.execute(
                insert(job_skills).values(
                    job_id=job.id,
                    skill_id=skill.id,
                    posted_date=job.posted_date,
                ).on_conflict_do_nothing()
            )
