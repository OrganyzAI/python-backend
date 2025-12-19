"""Package initializer for app models.

Import each model module here so that when Alembic imports
`app.models` during `env.py` execution, all SQLModel models are
registered on `SQLModel.metadata` and are available for
`--autogenerate` migrations.

Keep imports explicit to avoid accidental heavy imports at runtime.
"""

from . import otp, user  # noqa: F401

__all__ = ["otp", "user"]
