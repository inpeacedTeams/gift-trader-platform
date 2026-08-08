import asyncio

from sqlalchemy import text

from app.db.session import engine

REQUIRED_TABLES = {
    "schema_migrations",
    "collections",
    "gifts",
    "listings",
    "price_snapshots",
    "market_events",
    "sniper_watches",
    "sniper_hits",
    "trades",
    "source_statuses",
    "users",
    "watchlist_items",
    "portfolio_wallets",
    "portfolio_holdings",
    "portfolio_valuations",
    "alert_rules",
    "alert_events",
}


async def verify_schema() -> None:
    async with engine.connect() as connection:
        rows = await connection.execute(
            text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
        )
        actual = {row[0] for row in rows}
    missing = REQUIRED_TABLES - actual
    if missing:
        raise RuntimeError(f"Missing required tables: {', '.join(sorted(missing))}")


if __name__ == "__main__":
    asyncio.run(verify_schema())
