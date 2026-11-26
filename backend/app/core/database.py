from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.core.config import settings


def normalize_database_url(url: str) -> str:
    """Normalizes Neon/Render postgres:// or postgresql:// URIs to psycopg v3 dialect."""
    cleaned = (url or "").strip()
    if cleaned.startswith("postgres://"):
        return "postgresql+psycopg://" + cleaned[len("postgres://"):]
    if cleaned.startswith("postgresql://"):
        return "postgresql+psycopg://" + cleaned[len("postgresql://"):]
    return cleaned


# SQLAlchemy 2.0 Engine
engine = create_engine(
    normalize_database_url(settings.DATABASE_URL),
    pool_pre_ping=True,
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """Database session generator dependency for FastAPI endpoints."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()