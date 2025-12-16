import pytest
from pydantic import ValidationError
from app.schemas.user import LoginSchema, RegisterSchema


def test_password_validator_accepts_strong():
    s = LoginSchema(email="a@b.com", password="Aa1!aaaa")
    assert s.password == "Aa1!aaaa"

    r = RegisterSchema(first_name="A", last_name="B", email="u@v.com", password="Ab1!zzzz")
    assert r.password == "Ab1!zzzz"


def test_password_validator_rejects_weak():
    with pytest.raises(ValidationError):
        LoginSchema(email="a@b.com", password="weak")
    with pytest.raises(ValidationError):
        RegisterSchema(first_name="A", last_name="B", email="u@v.com", password="12345678")
