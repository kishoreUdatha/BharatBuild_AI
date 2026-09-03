from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
import bcrypt
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import secrets

from app.core.config import settings

# Bearer token security
security = HTTPBearer()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password"""
    # Handle None or empty password hash (OAuth users)
    if not hashed_password:
        return False

    try:
        # Bcrypt has a 72 byte limit - truncate password if necessary
        password_bytes = plain_password.encode('utf-8')[:72]
        return bcrypt.checkpw(password_bytes, hashed_password.encode('utf-8'))
    except (ValueError, TypeError):
        # Invalid salt or hash format - return False instead of crashing
        return False


def get_password_hash(password: str) -> str:
    """Hash password with configurable rounds (BCRYPT_ROUNDS in .env)"""
    # Bcrypt has a 72 byte limit - truncate password if necessary
    password_bytes = password.encode('utf-8')[:72]
    hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt(rounds=settings.BCRYPT_ROUNDS))
    return hashed.decode('utf-8')


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: Dict[str, Any]) -> str:
    """Create JWT refresh token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Dict[str, Any]:
    """Decode JWT token"""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def generate_api_key() -> str:
    """Generate secure API key"""
    return f"bb_{secrets.token_urlsafe(32)}"


def generate_secret_key() -> str:
    """Generate secret key for API key"""
    return secrets.token_urlsafe(48)


async def get_current_user_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """Get current user from JWT token"""
    token = credentials.credentials
    payload = decode_token(token)

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type"
        )

    return payload


async def verify_api_key(api_key: str, secret_key: str) -> bool:
    """
    Verify API key and secret against database.

    Args:
        api_key: The API key (format: bb_xxxx)
        secret_key: The secret key associated with the API key

    Returns:
        True if API key and secret are valid, False otherwise
    """
    # Basic format validation
    if not api_key or not secret_key:
        return False

    if not api_key.startswith("bb_") or len(api_key) < 10:
        return False

    if len(secret_key) < 32:
        return False

    # Database validation
    #
    # This used raw SQL against columns that do not exist on the api_keys table
    # (`api_key`, `secret_key_hash`, `is_active`), so every lookup raised and was
    # swallowed by the handler below - the function could only ever return False.
    # Going through the ORM means the column names are checked against the model
    # rather than being restated by hand, so the two cannot drift apart again.
    #
    # It also compared a sha256 of the secret, while create_api_key stores a
    # bcrypt hash. Even with the right columns nothing would have matched;
    # verification has to use the same primitive that wrote the hash.
    try:
        from app.core.database import AsyncSessionLocal
        from app.models.api_key import APIKey, APIKeyStatus
        from sqlalchemy import select

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(APIKey).where(APIKey.key == api_key)
            )
            key_record = result.scalar_one_or_none()

            if not key_record:
                return False

            if key_record.status != APIKeyStatus.ACTIVE:
                return False

            if key_record.expires_at:
                from datetime import datetime
                if datetime.utcnow() > key_record.expires_at:
                    return False

            # bcrypt.checkpw is itself constant-time, so verify_password covers
            # the timing concern the previous hmac.compare_digest was reaching for.
            return verify_password(secret_key, key_record.secret_hash)

    except Exception as e:
        # Log error but don't expose details
        import logging
        logging.getLogger(__name__).error(f"API key verification error: {e}")
        return False
