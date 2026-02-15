from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import secrets
from typing import Any

from jose import jwt

from app.core.config import get_settings

settings = get_settings()

PBKDF2_ALGORITHM = "sha256"
PBKDF2_ITERATIONS = 120000
SALT_BYTES = 16


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        scheme, algo, iterations, salt_hex, digest_hex = hashed_password.split("$", 4)
        if scheme != "pbkdf2":
            return False
        digest = hashlib.pbkdf2_hmac(
            algo,
            plain_password.encode("utf-8"),
            bytes.fromhex(salt_hex),
            int(iterations),
        )
        return hmac.compare_digest(digest.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


def get_password_hash(password: str) -> str:
    salt = secrets.token_bytes(SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        PBKDF2_ALGORITHM,
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
    )
    return f"pbkdf2${PBKDF2_ALGORITHM}${PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def create_access_token(subject: str, expires_minutes: int | None = None, **extra: Any) -> str:
    expire = datetime.now(tz=timezone.utc) + timedelta(
        minutes=expires_minutes or settings.access_token_expire_minutes
    )
    payload: dict[str, Any] = {"sub": subject, "exp": expire, **extra}
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def hash_gift_token(token: str) -> str:
    base = f"{settings.secret_key}:{token}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()


def create_claim_content_token(red_packet_id: int, expires_minutes: int = 30) -> str:
    expire = datetime.now(tz=timezone.utc) + timedelta(minutes=expires_minutes)
    payload: dict[str, Any] = {
        "sub": "claim-content",
        "red_packet_id": red_packet_id,
        "exp": expire,
    }
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def verify_claim_content_token(token: str) -> int:
    payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    if payload.get("sub") != "claim-content":
        raise ValueError("无效内容凭证")
    red_packet_id = payload.get("red_packet_id")
    if not isinstance(red_packet_id, int):
        raise ValueError("内容凭证格式错误")
    return red_packet_id
