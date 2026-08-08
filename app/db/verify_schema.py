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
    "positions",
    "seller_identities",
    "undercut_notices",
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
    "positions": {"buy_price_ton", "opened_at", "closed_at"},
}

# Columns a later migration made optional. Still NOT NULL means the migration
# did not run, and the first symptom would be an alert insert failing inside a
# background worker where nobody is watching.
NULLABLE_COLUMNS = {("alert_events", "rule_id")}


async def verify_schema() -> None:
    async with engine.connect() as connection:
        rows = await connection.execute(
            text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
        )
        actual = {row[0] for row in rows}
        columns = await connection.execute(
            text(
                "SELECT table_name, column_name, is_nullable FROM information_schema.columns "
                "WHERE table_schema = 'public'"
            )
        )
        column_rows = list(columns)
    missing = REQUIRED_TABLES - actual
    if missing:
        raise RuntimeError(f"Missing required tables: {', '.join(sorted(missing))}")

    present: dict[str, set[str]] = {}
    not_null: set[tuple[str, str]] = set()
    for table_name, column_name, is_nullable in column_rows:
        present.setdefault(table_name, set()).add(column_name)
        if is_nullable == "NO":
            not_null.add((table_name, column_name))
    gaps = [
        f"{table}.{column}"
        for table, required in REQUIRED_COLUMNS.items()
        for column in sorted(required - present.get(table, set()))
    ]
    if gaps:
        raise RuntimeError(f"Missing required columns: {', '.join(gaps)}")

    stuck = sorted(f"{table}.{column}" for table, column in NULLABLE_COLUMNS & not_null)
    if stuck:
        raise RuntimeError(f"Columns should be nullable: {', '.join(stuck)}")


if __name__ == "__main__":
    asyncio.run(verify_schema())
