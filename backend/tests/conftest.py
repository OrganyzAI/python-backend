from collections.abc import Generator
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, delete, select

from app.core import security
from app.core.config import settings
from app.core.db import get_engine
from app.enums.user_enum import UserRole
from app.main import app
from app.models.otp import OTP
from app.models.user import User


# Helper utilities used by tests (keeps tests self-contained when utils/ is missing)
def authentication_token_from_email(
    client: TestClient, email: str, db: Session
) -> dict[str, str]:
    statement = select(User).where(User.email == email)
    user = db.exec(statement).first()
    if not user:
        hashed = security.get_password_hash("password")
        user = User(
            email=email, hashed_password=hashed, first_name="Test", last_name="User"
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    token = security.create_access_token(
        subject=str(user.id),
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return {"Authorization": f"Bearer {token}"}


def get_superuser_token_headers(client: TestClient, db: Session) -> dict[str, str]:
    email = (
        settings.FIRST_SUPERUSER
        if hasattr(settings, "FIRST_SUPERUSER")
        else "super@example.com"
    )
    password = (
        settings.FIRST_SUPERUSER_PASSWORD
        if hasattr(settings, "FIRST_SUPERUSER_PASSWORD")
        else "password"
    )
    statement = select(User).where(User.email == email)
    user = db.exec(statement).first()
    if not user:
        hashed = security.get_password_hash(password)
        user = User(
            email=email,
            hashed_password=hashed,
            first_name="Super",
            last_name="User",
            role=UserRole.admin,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        # ensure role is admin
        user.role = UserRole.admin
        db.add(user)
        db.commit()
        db.refresh(user)

    token = security.create_access_token(
        subject=str(user.id),
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return {"Authorization": f"Bearer {token}"}


# Small test utilities used across tests when `tests.utils` helpers are not present
def random_lower_string(length: int = 8) -> str:
    import random
    import string

    return "".join(random.choice(string.ascii_lowercase) for _ in range(length))


def random_email() -> str:
    return f"{random_lower_string()}@example.com"


@pytest.fixture(scope="session", autouse=True)
def db() -> Generator[Session, None, None]:
    # Ensure all SQLModel models are registered/imported and tables created
    SQLModel.metadata.create_all(get_engine())
    with Session(get_engine()) as session:
        yield session
        # Clean up created rows after the test session
        statement = delete(OTP)
        session.execute(statement)
        statement = delete(User)
        session.execute(statement)
        session.commit()


@pytest.fixture(scope="module")
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def superuser_token_headers(client: TestClient) -> dict[str, str]:
    return get_superuser_token_headers(client)


@pytest.fixture(scope="module")
def normal_user_token_headers(client: TestClient, db: Session) -> dict[str, str]:
    return authentication_token_from_email(
        client=client, email=settings.EMAIL_TEST_USER, db=db
    )
