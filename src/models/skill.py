import uuid
from sqlalchemy import Column, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from models.base import Base


class Skill(Base):
    __tablename__ = "skills"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, unique=True, nullable=False)
    category = Column(Text)
