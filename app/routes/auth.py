from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.auth import issue_token, validate_telegram_init_data, current_user
from app.db.models import User
from app.db.session import get_session

router = APIRouter(prefix="/auth", tags=["auth"])

class TelegramAuthRequest(BaseModel):
    init_data: str

@router.post("/telegram")
async def telegram_auth(body: TelegramAuthRequest, session: AsyncSession = Depends(get_session)):
    telegram = validate_telegram_init_data(body.init_data)
    user = await session.scalar(select(User).where(User.telegram_id == int(telegram["id"])))
    now = datetime.now(timezone.utc)
    if user is None:
        user = User(telegram_id=int(telegram["id"]), username=telegram.get("username"), first_name=telegram.get("first_name"), last_name=telegram.get("last_name"), created_at=now, last_login_at=now)
        session.add(user)
    else:
        user.username = telegram.get("username")
        user.first_name = telegram.get("first_name")
        user.last_name = telegram.get("last_name")
        user.last_login_at = now
    await session.commit()
    await session.refresh(user)
    return {"access_token": issue_token(user.id), "token_type": "bearer", "user": {"id": user.id, "telegram_id": user.telegram_id, "username": user.username, "first_name": user.first_name}}

@router.get("/me")
async def me(user: User = Depends(current_user)):
    return {"id": user.id, "telegram_id": user.telegram_id, "username": user.username, "first_name": user.first_name, "last_name": user.last_name}
