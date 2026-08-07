import asyncio
from pathlib import Path
from sqlalchemy import text
from app.db.session import engine

MIGRATIONS = Path(__file__).resolve().parents[2] / "migrations" / "versions"

async def upgrade() -> list[str]:
    applied: list[str] = []
    async with engine.begin() as connection:
        await connection.execute(text("CREATE TABLE IF NOT EXISTS schema_migrations (version VARCHAR(255) PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT now())"))
        rows = await connection.execute(text("SELECT version FROM schema_migrations"))
        existing = {row[0] for row in rows}
        for path in sorted(MIGRATIONS.glob("*.sql")):
            if path.name in existing:
                continue
            statements = [statement.strip() for statement in path.read_text(encoding="utf-8").split(";") if statement.strip()]
            for statement in statements:
                await connection.execute(text(statement))
            await connection.execute(text("INSERT INTO schema_migrations(version) VALUES (:version)"), {"version": path.name})
            applied.append(path.name)
    return applied

if __name__ == "__main__":
    print(asyncio.run(upgrade()))
