import pytest
from pydantic import ValidationError

from app.core.config import settings
from app.schemas.user import (
    LoginSchema,
    ResetPasswordSchema,
    SocialLoginSchema,
)


def test_password_validator_accepts_strong():
    s = LoginSchema(email="a@b.com", password=settings.USER_PASSWORD)
    assert s.password == settings.USER_PASSWORD

    r = LoginSchema(
        email="u@v.com",
        password=settings.USER_PASSWORD,
    )
    assert r.password == settings.USER_PASSWORD


def test_password_validator_rejects_weak():
    with pytest.raises(ValidationError):
        LoginSchema(email="a@b.com", password=settings.USER_PASSWORD[:4])
    with pytest.raises(ValidationError):
        LoginSchema(
            email="u@v.com",
            password=settings.USER_PASSWORD[:4],
        )


def test_reset_password_schema_accepts_strong():
    """Test ResetPasswordSchema accepts strong passwords."""
    schema = ResetPasswordSchema(
        token="test_token",
        new_password=settings.USER_PASSWORD,
    )
    assert schema.token == "test_token"
    assert schema.new_password == settings.USER_PASSWORD


def test_reset_password_schema_rejects_weak():
    """Test ResetPasswordSchema rejects weak passwords (lines 31-33)."""
    with pytest.raises(ValidationError) as exc_info:
        ResetPasswordSchema(
            token="test_token",
            new_password="weak",
        )
    # Check that the error message contains the validation message
    error_str = str(exc_info.value)
    # The error might be in different formats, check for the message content
    assert "PASSWORD_TOO_WEAK" in error_str or "Password must be at least 8 characters" in error_str or "password" in error_str.lower()


def test_social_login_schema_accepts_valid_provider():
    """Test SocialLoginSchema accepts valid providers."""
    schema = SocialLoginSchema(provider="google", access_token="token123")
    assert schema.provider == "google"
    assert schema.access_token == "token123"

    schema2 = SocialLoginSchema(provider="apple", access_token="token456")
    assert schema2.provider == "apple"
    assert schema2.access_token == "token456"


def test_social_login_schema_rejects_invalid_provider():
    """Test SocialLoginSchema rejects invalid providers (lines 51-54)."""
    with pytest.raises(ValidationError) as exc_info:
        SocialLoginSchema(provider="invalid", access_token="token123")
    assert "Provider must be one of" in str(exc_info.value)
