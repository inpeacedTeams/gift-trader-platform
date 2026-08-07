import hashlib
import hmac
import json
import time
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import get_settings
from app.db.models import User
from app.db.session import get_session

bearer = HTTPBearer(auto_error=False)

def validate_telegram_init_data(init_data: str) -> dict:
    settings = get_settings()
    if not settings.telegram_bot_token:
        raise HTTPException(503, "Telegram auth is not configured")
    values = dict(item.split("=", 1) for item in init_data.split("&") if "=" in item)
    received = values.pop("hash", None)
    if not received:
        raise HTTPException(401, "Missing Telegram auth hash")
    check = "\n".join(f"{key}={values[key]}" for key in sorted(values))
    secret = hmac.new(b"WebAppData", settings.telegram_bot_token.encode(), hashlib.sha256).digest()
    expected = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, received):
        raise HTTPException(401, "Invalid Telegram auth signature")
    if time.time() - int(values.get("auth_date", "0")) > 86400:
        raise HTTPException(401, "Telegram auth data expired")
    user = json.loads(values.get("user", "{}"))
    if not user.get("id"):
        raise HTTPException(401, "Telegram user is missing")
    return user

def issue_token(user_id: int) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    return jwt.encode({"sub": str(user_id), "iat": now, "exp": now + timedelta(seconds=settings.jwt_ttl_seconds)}, settings.jwt_secret, algorithm="HS256")

async def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer), session: AsyncSession = Depends(get_session)) -> User:
    if not credentials:
        raise HTTPException(401, "Bearer token required")
    try:
        payload = jwt.decode(credentials.credentials, get_settings().jwt_secret, algorithms=["HS256"])
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise HTTPException(401, "Invalid access token") from exc
    user = await session.scalar(select(User).where(User.id == user_id, User.is_active.is_(True)))
    if user is None:
        raise HTTPException(401, "User not found")
    return user
