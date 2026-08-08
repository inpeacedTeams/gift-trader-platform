from datetime import datetime, timezone


class DailyQuota:
    """In process per user counter.

    We pay for every call, so an unbounded chat box is an open tab on our own
    wallet. Resets on the calendar day in UTC.
    """

    def __init__(self, limit: int):
        self.limit = limit
        self._day: str = ""
        self._used: dict[int, int] = {}

    def _roll(self) -> None:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if today != self._day:
            self._day = today
            self._used = {}

    def remaining(self, user_id: int) -> int:
        self._roll()
        return max(0, self.limit - self._used.get(user_id, 0))

    def consume(self, user_id: int) -> bool:
        self._roll()
        used = self._used.get(user_id, 0)
        if used >= self.limit:
            return False
        self._used[user_id] = used + 1
        return True
