from sqlmodel import create_engine
from sqlalchemy import Engine

from app.core.config import settings

_engine: Engine | None = None


def get_engine() -> Engine:
    """Return a cached SQLAlchemy Engine instance."""
    global _engine
    if _engine is None:
        _engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))
    return _engine


engine = get_engine()

