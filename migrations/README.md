# Database migrations

The repository uses ordered SQL migrations in `versions/`.

Run them with:

```bash
python -m app.db.migrate
python -m app.db.migrate  # safe no-op, required in CI
python -m app.db.verify_schema
```

The runner creates `schema_migrations`, applies files in lexical order, stores a SHA-256 checksum, and records every version transactionally. If two legacy files contain the same SQL, the later one is recorded as `skipped_duplicate` instead of executing the same migration twice.

Current clean-install order is:

1. `0001_market_foundation.sql`
2. `0002_user_features.sql`
3. `0003_portfolio_holdings.sql`
4. `0004_portfolio_valuation.sql`
5. `0005_portfolio_valuation_provenance.sql`
6. `0006_alert_notification_delivery.sql`

Legacy duplicate filenames may remain in old checkouts for compatibility, but new migrations must use a unique filename and must not reuse a numeric prefix.
