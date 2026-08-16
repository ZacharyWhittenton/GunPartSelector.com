from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))


class InvalidTokenError(Exception):
    """Raised when a bearer token is missing, malformed, or expired."""


def create_access_token(
    *,
    user_id: str,
    email_address: str,
    full_name: str,
    role: str,
    secret_key: str,
    algorithm: str,
    expires_delta: timedelta,
    now: datetime | None = None,
) -> str:
    issued_at = now or datetime.now(UTC)
    payload = {
        "sub": user_id,
        "email": email_address,
        "full_name": full_name,
        "role": role,
        "iat": issued_at,
        "exp": issued_at + expires_delta,
    }
    return jwt.encode(payload, secret_key, algorithm=algorithm)


def decode_access_token(token: str, *, secret_key: str, algorithm: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, secret_key, algorithms=[algorithm])
    except jwt.PyJWTError as error:
        raise InvalidTokenError from error
