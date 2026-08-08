import asyncio
import hashlib
from pathlib import Path
from sqlalchemy import text
from app.db.session import engine

MIGRATIONS = Path(__file__).resolve().parents[2] / "migrations" / "versions"

async def upgrade() -> list[str]:
    applied: list[str] = []
    async with engine.begin() as connection:
        await connection.execute(text("CREATE TABLE IF NOT EXISTS schema_migrations (version VARCHAR(255) PRIMARY KEY, checksum VARCHAR(64) NOT NULL, status VARCHAR(16) NOT NULL DEFAULT 'applied', applied_at TIMESTAMPTZ NOT NULL DEFAULT now())"))
        await connection.execute(text("ALTER TABLE schema_migrations ADD COLUMN IF NOT EXISTS checksum VARCHAR(64)"))
        await connection.execute(text("ALTER TABLE schema_migrations ADD COLUMN IF NOT EXISTS status VARCHAR(16) NOT NULL DEFAULT 'applied'"))
        rows = await connection.execute(text("SELECT version, checksum FROM schema_migrations")); existing = {row[0]: row[1] for row in rows}; seen_checksums: set[str] = set(existing.values())
        for path in sorted(MIGRATIONS.glob("*.sql")):
            checksum = hashlib.sha256(path.read_bytes()).hexdigest()
            if path.name in existing:
                continue
            if checksum in seen_checksums:
                await connection.execute(text("INSERT INTO schema_migrations(version, checksum, status) VALUES (:version, :checksum, 'skipped_duplicate')"), {"version": path.name, "checksum": checksum})
                continue
            statements = [statement.strip() for statement in path.read_text(encoding="utf-8").split(";") if statement.strip()]
            for statement in statements:
                await connection.execute(text(statement))
            await connection.execute(text("INSERT INTO schema_migrations(version, checksum, status) VALUES (:version, :checksum, 'applied')"), {"version": path.name, "checksum": checksum})
            seen_checksums.add(checksum); applied.append(path.name)
    return applied

if __name__ == "__main__":
    print(asyncio.run(upgrade()))
