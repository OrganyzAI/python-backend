from sqlalchemy import Engine
from sqlmodel import create_engine

from app.core.config import settings

_engine: Engine | None = None


def get_engine() -> Engine:
    """Return a cached SQLAlchemy Engine instance."""
    global _engine
    if _engine is None:
        _engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))
    return _engine


# Keep a module-level `engine` symbol for backwards compatibility, but
# initialize it lazily to avoid import-time DB access which can fail
# when settings are not fully constructed during early imports.
engine: Engine | None = None
