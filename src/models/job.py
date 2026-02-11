import uuid
from sqlalchemy import Column, Text, DateTime, Numeric, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, ARRAY, INTEGER
from sqlalchemy.orm import relationship
from models.base import Base


class Job(Base):
    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    posted_date = Column(DateTime, primary_key=True)
    source = Column(Text, default="web scrape")
    title = Column(Text)
    company_name = Column(Text)
    url = Column(Text)
    salary_min = Column(Numeric(15, 2))
    salary_max = Column(Numeric(15, 2))
    salary_currency = Column(Text, default="VND")
    experience = Column(Text)
    location_id = Column(UUID(as_uuid=True), ForeignKey("locations.id"), nullable=True)
    processed_at = Column(DateTime, server_default="now()")
    last_seen = Column(DateTime, server_default="now()")
    
    # Deduplication: MinHash signature for Jaccard similarity
    minhash_signature = Column(ARRAY(INTEGER), nullable=True)

    # Relationships
    location = relationship("Location", back_populates="jobs", foreign_keys=[location_id])
