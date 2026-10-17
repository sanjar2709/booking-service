from datetime import UTC, datetime, timedelta

import jwt
from pwdlib import PasswordHash

from core import settings

password_hash = PasswordHash.recommended()

ALGORITHM = 'HS256'


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return password_hash.verify(password, hashed)


def create_token(user_id: int, token_type: str, lifetime: timedelta) -> str:
    now = datetime.now(UTC)
    payload = {'sub': str(user_id), 'type': token_type, 'iat': now, 'exp': now + lifetime}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def create_access_token(user_id: int) -> str:
    return create_token(user_id, 'access', timedelta(minutes=settings.ACCESS_TOKEN_LIFETIME_MINUTES))


def create_refresh_token(user_id: int) -> str:
    return create_token(user_id, 'refresh', timedelta(days=settings.REFRESH_TOKEN_LIFETIME_DAYS))


def decode_token(token: str, token_type: str) -> int | None:
    """Return user id from a valid token of the given type, otherwise None."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=(ALGORITHM,))
    except jwt.PyJWTError:
        return None
    if payload.get('type') != token_type:
        return None
    return int(payload['sub'])
