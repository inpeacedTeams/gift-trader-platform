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

# Columns added by later migrations. A table can exist while a migration that
# only adds columns silently failed to run, and the first symptom would be a
# query blowing up in production rather than a clear message on boot.
REQUIRED_COLUMNS = {
    "gifts": {
        "backdrop",
        "symbol",
        "model_rarity",
        "backdrop_rarity",
        "symbol_rarity",
        "rarity_tier",
    },
    "listings": {"closed_at"},
}


async def verify_schema() -> None:
    async with engine.connect() as connection:
        rows = await connection.execute(
            text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
        )
        actual = {row[0] for row in rows}
        columns = await connection.execute(
            text(
                "SELECT table_name, column_name FROM information_schema.columns "
                "WHERE table_schema = 'public'"
            )
        )
    missing = REQUIRED_TABLES - actual
    if missing:
        raise RuntimeError(f"Missing required tables: {', '.join(sorted(missing))}")

    present: dict[str, set[str]] = {}
    for table_name, column_name in columns:
        present.setdefault(table_name, set()).add(column_name)
    gaps = [
        f"{table}.{column}"
        for table, required in REQUIRED_COLUMNS.items()
        for column in sorted(required - present.get(table, set()))
    ]
    if gaps:
        raise RuntimeError(f"Missing required columns: {', '.join(gaps)}")


if __name__ == "__main__":
    asyncio.run(verify_schema())
