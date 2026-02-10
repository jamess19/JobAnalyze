import uuid
from sqlalchemy import Column, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from models.base import Base


class Location(Base):
    __tablename__ = "locations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    city_name = Column(Text, unique=True)
    country = Column(Text, default="Vietnam")
    raw_name = Column(Text)

    jobs = relationship("Job", back_populates="location")
