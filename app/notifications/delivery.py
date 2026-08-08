from datetime import datetime, timezone

from sqlalchemy import select

from app.db.models import AlertEvent, User
from app.db.session import SessionLocal
from app.notifications.telegram import TelegramNotifier

MAX_ATTEMPTS = 3
BATCH = 100


async def deliver_pending_alerts() -> int:
    """Send whatever the evaluators queued.

    Events are written by the sync workers and drained here, so a slow or
    failing Telegram never blocks a market crawl.
    """
    notifier = TelegramNotifier()
    delivered = 0
    async with SessionLocal() as session:
        rows = list(
            (
                await session.execute(
                    select(AlertEvent, User)
                    .join(User, User.id == AlertEvent.user_id)
                    .where(
                        AlertEvent.notification_sent_at.is_(None),
                        AlertEvent.notification_attempts < MAX_ATTEMPTS,
                    )
                    .order_by(AlertEvent.created_at.asc())
                    .limit(BATCH)
                )
            ).all()
        )
        for event, user in rows:
            event.notification_attempts += 1
            try:
                await notifier.send(user.telegram_id, event.message)
                event.notification_sent_at = datetime.now(timezone.utc)
                event.notification_error = None
                delivered += 1
            except Exception as exc:
                event.notification_error = str(exc)[:1000]
        await session.commit()
    return delivered
