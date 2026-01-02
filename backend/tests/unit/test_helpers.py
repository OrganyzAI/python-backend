"""Tests for helpers.py utility functions."""

import hashlib
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import jwt
import pytest

from app.core.config import settings
from app.utils_helper.helpers import (
    add_time,
    format_datetime,
    generate_hash,
    generate_uuid,
    get_current_timestamp,
    parse_datetime,
    verify_apple_token,
    verify_google_token,
)


def test_generate_uuid():
    """Test generate_uuid function (line 13)."""
    uuid_str = generate_uuid()
    assert isinstance(uuid_str, str)
    # Verify it's a valid UUID
    uuid.UUID(uuid_str)


def test_generate_hash():
    """Test generate_hash function (line 17)."""
    data = "test_data"
    hash_result = generate_hash(data)
    assert isinstance(hash_result, str)
    assert len(hash_result) == 64  # SHA256 hex digest length
    # Verify it's the correct hash
    expected = hashlib.sha256(data.encode()).hexdigest()
    assert hash_result == expected


def test_get_current_timestamp():
    """Test get_current_timestamp function (line 21)."""
    timestamp = get_current_timestamp()
    assert isinstance(timestamp, datetime)
    # Should be close to now (within 1 second)
    now = datetime.utcnow()
    assert abs((now - timestamp).total_seconds()) < 1


def test_add_time():
    """Test add_time function (line 25)."""
    result = add_time(hours=1, minutes=30, days=1)
    assert isinstance(result, datetime)
    # Verify it's approximately correct (within 1 second)
    expected = datetime.utcnow() + timedelta(hours=1, minutes=30, days=1)
    assert abs((expected - result).total_seconds()) < 1

    # Test with only hours
    result2 = add_time(hours=2)
    expected2 = datetime.utcnow() + timedelta(hours=2)
    assert abs((expected2 - result2).total_seconds()) < 1


def test_format_datetime():
    """Test format_datetime function (line 29)."""
    dt = datetime(2023, 1, 15, 10, 30, 45)
    formatted = format_datetime(dt)
    assert formatted == "2023-01-15 10:30:45"

    # Test with custom format
    formatted_custom = format_datetime(dt, fmt="%Y-%m-%d")
    assert formatted_custom == "2023-01-15"


def test_parse_datetime():
    """Test parse_datetime function (line 33)."""
    dt_str = "2023-01-15 10:30:45"
    parsed = parse_datetime(dt_str)
    assert isinstance(parsed, datetime)
    assert parsed == datetime(2023, 1, 15, 10, 30, 45)

    # Test with custom format
    dt_str2 = "2023-01-15"
    parsed2 = parse_datetime(dt_str2, fmt="%Y-%m-%d")
    assert parsed2 == datetime(2023, 1, 15)


@pytest.mark.asyncio
async def test_verify_google_token_success():
    """Test verify_google_token with successful response (lines 37-49)."""
    mock_data = {
        "aud": "test_client_id",
        "email": "test@example.com",
        "sub": "123456789",
    }

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_data

    mock_client_instance = AsyncMock()
    mock_client_instance.get = AsyncMock(return_value=mock_response)

    # Create a proper async context manager
    class AsyncContextManager:
        async def __aenter__(self):
            return mock_client_instance

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            return False

    mock_client_class = MagicMock(return_value=AsyncContextManager())

    with patch("app.utils_helper.helpers.httpx.AsyncClient", mock_client_class):
        with patch.object(settings, "GOOGLE_CLIENT_ID", "test_client_id"):
            result = await verify_google_token("test_token")
            assert result == mock_data


@pytest.mark.asyncio
async def test_verify_google_token_invalid_status():
    """Test verify_google_token with invalid status code."""
    mock_response = AsyncMock()
    mock_response.status_code = 400

    mock_client_instance = AsyncMock()
    mock_client_instance.get = AsyncMock(return_value=mock_response)

    mock_client_class = AsyncMock()
    mock_client_class.return_value.__aenter__ = AsyncMock(
        return_value=mock_client_instance
    )
    mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)

    with patch("app.utils_helper.helpers.httpx.AsyncClient", mock_client_class):
        result = await verify_google_token("test_token")
        assert result is None


@pytest.mark.asyncio
async def test_verify_google_token_audience_mismatch():
    """Test verify_google_token with audience mismatch."""
    mock_data = {
        "aud": "wrong_client_id",
        "email": "test@example.com",
    }

    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json = AsyncMock(return_value=mock_data)

    mock_client_instance = AsyncMock()
    mock_client_instance.get = AsyncMock(return_value=mock_response)

    mock_client_class = AsyncMock()
    mock_client_class.return_value.__aenter__ = AsyncMock(
        return_value=mock_client_instance
    )
    mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)

    with patch("app.utils_helper.helpers.httpx.AsyncClient", mock_client_class):
        with patch.object(settings, "GOOGLE_CLIENT_ID", "correct_client_id"):
            result = await verify_google_token("test_token")
            assert result is None


@pytest.mark.asyncio
async def test_verify_google_token_exception():
    """Test verify_google_token with exception (line 50-51)."""
    mock_client_class = AsyncMock()
    mock_client_class.return_value.__aenter__ = AsyncMock(
        side_effect=Exception("Network error")
    )
    mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)

    with patch("app.utils_helper.helpers.httpx.AsyncClient", mock_client_class):
        result = await verify_google_token("test_token")
        assert result is None


# @pytest.mark.asyncio
# async def test_verify_apple_token_success():
#     """Test verify_apple_token with successful verification (lines 55-72)."""
#     mock_payload = {
#         "sub": "123456789",
#         "email": "test@example.com",
#     }

#     # Create a mock signing key with a key attribute
#     mock_signing_key = MagicMock()
#     mock_signing_key.key = "mock_public_key"

#     # Create a mock JWK client instance
#     mock_jwk_client_instance = MagicMock()
#     mock_jwk_client_instance.get_signing_key_from_jwt = MagicMock(
#         return_value=mock_signing_key
#     )

#     # Mock PyJWKClient to return our mock instance when instantiated
#     with patch("app.utils_helper.helpers.jwt.PyJWKClient") as mock_jwk_client:
#         mock_jwk_client.return_value = mock_jwk_client_instance
#         with patch("app.utils_helper.helpers.jwt.decode", return_value=mock_payload):
#             with patch.object(settings, "APPLE_CLIENT_ID", "test_client_id"):
#                 result = await verify_apple_token("test_token")
#                 # Verify the function returns the expected payload
#                 # This exercises all code paths including lines 63-71
#                 assert result == mock_payload


# @pytest.mark.asyncio
# async def test_verify_apple_token_no_audience():
#     """Test verify_apple_token without audience configured."""
#     mock_payload = {
#         "sub": "123456789",
#         "email": "test@example.com",
#     }

#     # Create a mock signing key with a key attribute
#     mock_signing_key = MagicMock()
#     mock_signing_key.key = "mock_public_key"

#     # Create a mock JWK client instance
#     mock_jwk_client_instance = MagicMock()
#     mock_jwk_client_instance.get_signing_key_from_jwt = MagicMock(
#         return_value=mock_signing_key
#     )

#     # Mock PyJWKClient to return our mock instance when instantiated
#     with patch("app.utils_helper.helpers.jwt.PyJWKClient") as mock_jwk_client:
#         mock_jwk_client.return_value = mock_jwk_client_instance
#         with patch("app.utils_helper.helpers.jwt.decode", return_value=mock_payload):
#             with patch.object(settings, "APPLE_CLIENT_ID", None):
#                 result = await verify_apple_token("test_token")
#                 # Verify the function returns the expected payload
#                 # This exercises all code paths including lines 63-64 with audience=None
#                 assert result == mock_payload


@pytest.mark.asyncio
async def test_verify_apple_token_jwk_exception():
    """Test verify_apple_token with JWK client exception (lines 60-61)."""
    with patch("app.utils_helper.helpers.jwt.PyJWKClient") as mock_jwk_client:
        mock_jwk_client.return_value.get_signing_key_from_jwt.side_effect = Exception(
            "JWK error"
        )

        result = await verify_apple_token("test_token")
        assert result is None


@pytest.mark.asyncio
async def test_verify_apple_token_decode_exception():
    """Test verify_apple_token with decode exception (line 73-74)."""
    with patch("app.utils_helper.helpers.jwt.PyJWKClient") as mock_jwk_client:
        mock_signing_key = MagicMock()
        mock_signing_key.key = "mock_public_key"
        mock_jwk_client.return_value.get_signing_key_from_jwt.return_value = (
            mock_signing_key
        )

        with patch("app.utils_helper.helpers.jwt.decode") as mock_decode:
            mock_decode.side_effect = Exception("Decode error")

            result = await verify_apple_token("test_token")
            assert result is None
