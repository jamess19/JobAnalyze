from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
import os


class Base(DeclarativeBase):
    pass


def get_engine(database_url: str | None = None):
    url = database_url or os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:password@localhost:5433/job_market"
    )
    return create_engine(url, pool_pre_ping=True, pool_size=5)


def get_session_factory(engine):
    return sessionmaker(bind=engine)
