from datetime import datetime, timezone
from sqlalchemy import select
from app.db.models import AlertEvent, User
from app.db.session import SessionLocal
from app.notifications.telegram import TelegramNotifier

async def deliver_pending_alerts() -> int:
    notifier = TelegramNotifier(); delivered = 0
    async with SessionLocal() as session:
        rows = list((await session.execute(select(AlertEvent, User).join(User, User.id == AlertEvent.user_id).where(AlertEvent.notification_sent_at.is_(None), AlertEvent.notification_attempts < 3).order_by(AlertEvent.created_at.asc()).limit(100))).all())
        for event, user in rows:
            event.notification_attempts += 1
            try:
                await notifier.send(user.telegram_id, f"Gift Trader alert\n\n{event.message}")
                event.notification_sent_at = datetime.now(timezone.utc); event.notification_error = None; delivered += 1
            except Exception as exc:
                event.notification_error = str(exc)[:1000]
        await session.commit()
    return delivered
