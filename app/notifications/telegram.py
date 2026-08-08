from app.core.config import get_settings
from app.market.http import MarketHttp


class TelegramNotifier:
    def __init__(self, http: MarketHttp | None = None):
        settings = get_settings()
        self.token = settings.telegram_bot_token
        self.http = http or MarketHttp(
            timeout=settings.source_timeout_seconds,
            retries=settings.source_retries,
            backoff_seconds=settings.source_backoff_seconds,
        )

    async def send(self, chat_id: int, text: str) -> None:
        if not self.token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured")
        await self.http.get_json(
            "telegram",
            f"https://api.telegram.org/bot{self.token}/sendMessage",
            params={
                "chat_id": chat_id,
                "text": text,
                # The listing link is the point of the message, so previews
                # stay off but the link itself must remain clickable.
                "disable_web_page_preview": "true",
            },
        )
