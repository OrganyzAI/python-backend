import pytest
from pydantic import ValidationError

from app.core.config import settings
from app.schemas.user import LoginSchema, RegisterSchema


def test_password_validator_accepts_strong():
    s = LoginSchema(email="a@b.com", password=settings.USER_PASSWORD)
    assert s.password == settings.USER_PASSWORD

    r = RegisterSchema(
        first_name="A",
        last_name="B",
        email="u@v.com",
        password=settings.USER_PASSWORD,
    )
    assert r.password == settings.USER_PASSWORD


def test_password_validator_rejects_weak():
    with pytest.raises(ValidationError):
        LoginSchema(email="a@b.com", password=settings.USER_PASSWORD[:4])
    with pytest.raises(ValidationError):
        RegisterSchema(
            first_name="A",
            last_name="B",
            email="u@v.com",
            password=settings.USER_PASSWORD[:4],
        )
