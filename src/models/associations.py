from sqlalchemy import Column, DateTime, ForeignKey, Table
from sqlalchemy.dialects.postgresql import UUID
from models.base import Base

job_skills = Table(
    "job_skills", Base.metadata,
    Column("job_id", UUID(as_uuid=True), primary_key=True),
    Column("skill_id", UUID(as_uuid=True), ForeignKey("skills.id"), primary_key=True),
    Column("posted_date", DateTime, primary_key=True),
)

job_domain = Table(
    "job_domain", Base.metadata,
    Column("job_id", UUID(as_uuid=True), primary_key=True),
    Column("domain_id", UUID(as_uuid=True), ForeignKey("domains.id"), primary_key=True),
    Column("posted_date", DateTime, primary_key=True),
)
