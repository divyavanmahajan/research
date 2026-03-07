from datetime import datetime, timedelta
from typing import Optional

from fastapi import Request, Depends
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from database import get_db
import models

SECRET_KEY = "wms-demo-secret-change-in-production-2026"
ALGORITHM = "HS256"
TOKEN_EXPIRY_HOURS = 8

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ── Exceptions (converted to redirects in main.py) ──────────────────────────

class NotAuthenticated(Exception):
    pass


class NotAuthorized(Exception):
    pass


# ── Password helpers ─────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ── JWT helpers ───────────────────────────────────────────────────────────────

def create_token(user_id: int, username: str, role: str) -> str:
    expire = datetime.utcnow() + timedelta(hours=TOKEN_EXPIRY_HOURS)
    payload = {
        "sub": str(user_id),
        "username": username,
        "role": role,
        "exp": expire,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


# ── FastAPI dependencies ──────────────────────────────────────────────────────

def require_user(request: Request, db: Session = Depends(get_db)) -> models.User:
    token = request.cookies.get("access_token")
    if not token:
        raise NotAuthenticated()
    payload = decode_token(token)
    if not payload:
        raise NotAuthenticated()
    user = db.get(models.User, int(payload["sub"]))
    if not user:
        raise NotAuthenticated()
    return user


def require_admin(user: models.User = Depends(require_user)) -> models.User:
    if user.role != "admin":
        raise NotAuthorized()
    return user
