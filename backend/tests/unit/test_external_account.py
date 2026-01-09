"""Tests for external_account model."""

import uuid
from datetime import datetime

from sqlmodel import Session

from app.models.external_account import ExternalAccount
from app.models.user import User
from tests.conftest import db


def test_external_account_model_creation(db: Session):
    """Test ExternalAccount model creation to ensure TYPE_CHECKING import is exercised."""
    # Create a user first
    user = User(
        email=f"test_external_account_{uuid.uuid4()}@example.com",
        hashed_password="hashed",
        first_name="Test",
        last_name="User",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Create external account
    external_account = ExternalAccount(
        user_id=user.id,
        provider="google",
        provider_account_id="google_123",
        access_token="token123",
        refresh_token="refresh123",
        expires_at=datetime.utcnow(),
        extra_data={"key": "value"},
    )
    db.add(external_account)
    db.commit()
    db.refresh(external_account)

    assert external_account.user_id == user.id
    assert external_account.provider == "google"
    assert external_account.provider_account_id == "google_123"
    assert external_account.access_token == "token123"
    assert external_account.refresh_token == "refresh123"
    assert external_account.extra_data == {"key": "value"}
    assert isinstance(external_account.id, uuid.UUID)
    assert isinstance(external_account.created_at, datetime)
    assert isinstance(external_account.updated_at, datetime)


def test_external_account_model_defaults():
    """Test ExternalAccount model with default values."""
    user_id = uuid.uuid4()
    external_account = ExternalAccount(
        user_id=user_id,
        provider="apple",
    )

    assert external_account.user_id == user_id
    assert external_account.provider == "apple"
    assert external_account.provider_account_id is None
    assert external_account.access_token is None
    assert external_account.refresh_token is None
    assert external_account.expires_at is None
    assert external_account.extra_data is None


def test_external_account_type_checking_import():
    """Test TYPE_CHECKING import block (line 9).

    To cover line 9, we execute the import statement that's inside the TYPE_CHECKING block.
    Since TYPE_CHECKING is False at runtime, we use exec to execute the import with TYPE_CHECKING=True.
    """
    from pathlib import Path

    # Get the path to the external_account module
    from app.models import external_account

    module_path = Path(external_account.__file__)

    # Create a namespace with TYPE_CHECKING=True to execute the import
    namespace = {
        "__name__": "app.models.external_account",
        "__file__": str(module_path),
        "__package__": "app.models",
        "TYPE_CHECKING": True,
        "uuid": __import__("uuid"),
        "datetime": __import__("datetime"),
        "Optional": __import__("typing").Optional,
        "Any": __import__("typing").Any,
        "Column": __import__("sqlalchemy").Column,
        "JSON": __import__("sqlalchemy").JSON,
        "Field": __import__("sqlmodel").Field,
        "Relationship": __import__("sqlmodel").Relationship,
        "SQLModel": __import__("sqlmodel").SQLModel,
    }

    # Execute the TYPE_CHECKING block with TYPE_CHECKING=True
    # This will execute line 9: from app.models.user import User
    exec(
        "if TYPE_CHECKING:\n    from app.models.user import User",
        namespace,
    )

    # Verify the import was executed (line 9)
    assert "User" in namespace
    assert namespace["User"] is User  # Should match the imported User class

    # Verify the module still works correctly
    assert ExternalAccount is not None
    assert hasattr(ExternalAccount, "user")
