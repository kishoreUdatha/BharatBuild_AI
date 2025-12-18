"""
Unit Tests for Security Module
Tests for: password hashing, JWT tokens, API keys
"""
import pytest
from unittest.mock import patch
from datetime import datetime, timedelta
from jose import jwt, JWTError
from fastapi import HTTPException

from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_api_key,
    generate_secret_key,
    get_current_user_token,
    verify_api_key
)
from app.core.config import settings


class TestPasswordHashing:
    """Test password hashing functions"""

    def test_hash_password_returns_different_value(self):
        """Test that hashing returns a different value than input"""
        password = "testpassword123"
        hashed = get_password_hash(password)

        assert hashed != password
        assert len(hashed) > 0

    def test_hash_password_different_each_time(self):
        """Test that hashing same password returns different hashes"""
        password = "testpassword123"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)

        # Bcrypt generates different salts
        assert hash1 != hash2

    def test_verify_password_correct(self):
        """Test verifying correct password"""
        password = "testpassword123"
        hashed = get_password_hash(password)

        result = verify_password(password, hashed)

        assert result is True

    def test_verify_password_incorrect(self):
        """Test verifying incorrect password"""
        password = "testpassword123"
        wrong_password = "wrongpassword"
        hashed = get_password_hash(password)

        result = verify_password(wrong_password, hashed)

        assert result is False

    def test_hash_long_password_truncated(self):
        """Test that long passwords are truncated to bcrypt limit"""
        # Bcrypt has 72 byte limit
        long_password = "a" * 100
        hashed = get_password_hash(long_password)

        # Should still work with verification (truncated)
        result = verify_password(long_password, hashed)
        assert result is True

    def test_hash_unicode_password(self):
        """Test hashing unicode passwords"""
        password = "tëst🔐pässwörd"
        hashed = get_password_hash(password)

        result = verify_password(password, hashed)
        assert result is True

    def test_hash_empty_password(self):
        """Test hashing empty password"""
        password = ""
        hashed = get_password_hash(password)

        result = verify_password(password, hashed)
        assert result is True


class TestAccessToken:
    """Test access token functions"""

    def test_create_access_token(self):
        """Test creating access token"""
        data = {"sub": "user123", "email": "test@example.com"}
        token = create_access_token(data)

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_access_token_with_expiry(self):
        """Test creating access token with custom expiry"""
        data = {"sub": "user123"}
        expires = timedelta(hours=1)
        token = create_access_token(data, expires_delta=expires)

        # Decode and check expiry
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        exp = datetime.utcfromtimestamp(payload["exp"])
        now = datetime.utcnow()

        # Should expire in about 1 hour
        assert (exp - now).total_seconds() < 3700  # About 1 hour + buffer
        assert (exp - now).total_seconds() > 3500

    def test_access_token_has_type(self):
        """Test access token includes type claim"""
        data = {"sub": "user123"}
        token = create_access_token(data)

        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        assert payload["type"] == "access"

    def test_access_token_includes_data(self):
        """Test access token includes original data"""
        data = {"sub": "user123", "email": "test@example.com", "role": "student"}
        token = create_access_token(data)

        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        assert payload["sub"] == "user123"
        assert payload["email"] == "test@example.com"
        assert payload["role"] == "student"


class TestRefreshToken:
    """Test refresh token functions"""

    def test_create_refresh_token(self):
        """Test creating refresh token"""
        data = {"sub": "user123"}
        token = create_refresh_token(data)

        assert token is not None
        assert isinstance(token, str)

    def test_refresh_token_has_type(self):
        """Test refresh token includes type claim"""
        data = {"sub": "user123"}
        token = create_refresh_token(data)

        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        assert payload["type"] == "refresh"

    def test_refresh_token_long_expiry(self):
        """Test refresh token has longer expiry than access token"""
        data = {"sub": "user123"}
        access_token = create_access_token(data)
        refresh_token = create_refresh_token(data)

        access_payload = jwt.decode(access_token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        refresh_payload = jwt.decode(refresh_token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])

        access_exp = datetime.utcfromtimestamp(access_payload["exp"])
        refresh_exp = datetime.utcfromtimestamp(refresh_payload["exp"])

        # Refresh should expire later than access
        assert refresh_exp > access_exp


class TestDecodeToken:
    """Test token decoding"""

    def test_decode_valid_token(self):
        """Test decoding valid token"""
        data = {"sub": "user123", "email": "test@example.com"}
        token = create_access_token(data)

        payload = decode_token(token)

        assert payload["sub"] == "user123"
        assert payload["email"] == "test@example.com"

    def test_decode_invalid_token(self):
        """Test decoding invalid token raises exception"""
        with pytest.raises(HTTPException) as exc_info:
            decode_token("invalid_token_string")

        assert exc_info.value.status_code == 401
        assert "Could not validate credentials" in exc_info.value.detail

    def test_decode_expired_token(self):
        """Test decoding expired token raises exception"""
        data = {"sub": "user123"}
        expired_token = jwt.encode(
            {**data, "exp": datetime.utcnow() - timedelta(hours=1), "type": "access"},
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )

        with pytest.raises(HTTPException) as exc_info:
            decode_token(expired_token)

        assert exc_info.value.status_code == 401

    def test_decode_token_wrong_secret(self):
        """Test decoding token with wrong secret"""
        data = {"sub": "user123"}
        token = jwt.encode(
            {**data, "exp": datetime.utcnow() + timedelta(hours=1)},
            "wrong_secret_key",
            algorithm=settings.JWT_ALGORITHM
        )

        with pytest.raises(HTTPException) as exc_info:
            decode_token(token)

        assert exc_info.value.status_code == 401


class TestApiKeyGeneration:
    """Test API key generation"""

    def test_generate_api_key_format(self):
        """Test API key has correct format"""
        api_key = generate_api_key()

        assert api_key.startswith("bb_")
        assert len(api_key) > 32

    def test_generate_api_key_unique(self):
        """Test API keys are unique"""
        key1 = generate_api_key()
        key2 = generate_api_key()

        assert key1 != key2

    def test_generate_secret_key(self):
        """Test secret key generation"""
        secret = generate_secret_key()

        assert len(secret) > 30  # Should be reasonably long

    def test_generate_secret_key_unique(self):
        """Test secret keys are unique"""
        secret1 = generate_secret_key()
        secret2 = generate_secret_key()

        assert secret1 != secret2


class TestVerifyApiKey:
    """Test API key verification"""

    def test_verify_valid_api_key(self):
        """Test verifying valid API key format"""
        api_key = generate_api_key()
        secret_key = generate_secret_key()

        result = verify_api_key(api_key, secret_key)

        assert result is True

    def test_verify_invalid_api_key_format(self):
        """Test verifying invalid API key format"""
        api_key = "invalid_key"
        secret_key = generate_secret_key()

        result = verify_api_key(api_key, secret_key)

        assert result is False

    def test_verify_short_secret(self):
        """Test verifying with too short secret"""
        api_key = generate_api_key()
        secret_key = "short"

        result = verify_api_key(api_key, secret_key)

        assert result is False


class TestGetCurrentUserToken:
    """Test get_current_user_token dependency"""

    @pytest.mark.asyncio
    async def test_get_user_token_valid(self):
        """Test getting user from valid token"""
        from unittest.mock import MagicMock

        data = {"sub": "user123", "email": "test@example.com", "role": "student"}
        token = create_access_token(data)

        mock_credentials = MagicMock()
        mock_credentials.credentials = token

        payload = await get_current_user_token(mock_credentials)

        assert payload["sub"] == "user123"
        assert payload["email"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_get_user_token_wrong_type(self):
        """Test getting user with refresh token fails"""
        from unittest.mock import MagicMock

        data = {"sub": "user123"}
        token = create_refresh_token(data)  # Using refresh token instead of access

        mock_credentials = MagicMock()
        mock_credentials.credentials = token

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user_token(mock_credentials)

        assert exc_info.value.status_code == 401
        assert "Invalid token type" in exc_info.value.detail


class TestTokenPayloadPreservation:
    """Test that token payload data is preserved correctly"""

    def test_complex_payload_preserved(self):
        """Test complex payload data is preserved"""
        data = {
            "sub": "550e8400-e29b-41d4-a716-446655440000",
            "email": "user@example.com",
            "role": "admin",
            "is_active": True,
            "permissions": ["read", "write", "delete"]
        }
        token = create_access_token(data)
        payload = decode_token(token)

        assert payload["sub"] == data["sub"]
        assert payload["email"] == data["email"]
        assert payload["role"] == data["role"]

    def test_special_characters_in_payload(self):
        """Test special characters in payload"""
        data = {
            "sub": "user123",
            "email": "test+special@example.com",
            "full_name": "Tëst Üsér"
        }
        token = create_access_token(data)
        payload = decode_token(token)

        assert payload["email"] == data["email"]
        assert payload["full_name"] == data["full_name"]


class TestSecurityEdgeCases:
    """Test edge cases in security functions"""

    def test_hash_password_with_whitespace(self):
        """Test hashing password with whitespace"""
        password = "  password with spaces  "
        hashed = get_password_hash(password)

        result = verify_password(password, hashed)
        assert result is True

    def test_token_with_none_values(self):
        """Test token creation with None values in payload"""
        data = {"sub": "user123", "optional_field": None}
        token = create_access_token(data)
        payload = decode_token(token)

        assert payload["sub"] == "user123"
        assert payload["optional_field"] is None

    def test_empty_payload_token(self):
        """Test token with empty payload (only required fields added)"""
        data = {}
        token = create_access_token(data)
        payload = decode_token(token)

        # Should have exp and type added
        assert "exp" in payload
        assert payload["type"] == "access"
