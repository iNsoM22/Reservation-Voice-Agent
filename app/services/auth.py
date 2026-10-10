"""Admin bootstrap and password verification."""

import hashlib
import hmac
import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1)
    return f"scrypt$16384${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, cost, salt, digest = stored.split("$")
        if scheme != "scrypt" or cost != "16384":
            return False
        actual = hashlib.scrypt(
            password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1
        )
        return hmac.compare_digest(actual, bytes.fromhex(digest))
    except (ValueError, TypeError):
        return False


def bootstrap_admin(session: Session, email: str, password: str) -> bool:
    email = email.strip().lower()
    if not email or not password:
        return False
    if session.scalar(select(User).where(User.email == email)):
        return False
    session.add(User(email=email, password_hash=hash_password(password), role="admin"))
    session.commit()
    return True
