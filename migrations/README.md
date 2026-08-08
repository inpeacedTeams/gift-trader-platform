# Database migrations

Migrations are applied in lexical order by `python -m app.db.migrate` and recorded in `schema_migrations` with checksums. The canonical tree is:

```text
0001_market_foundation.sql
0002_user_features.sql
0003_portfolio_holdings.sql
0004_portfolio_valuation.sql
0005_portfolio_valuation_provenance.sql
0006_alert_notification_delivery.sql
```

For a checkout created from an older snapshot, run `python scripts/clean_migration_tree.py` once before applying migrations. It removes only the four known legacy duplicate filenames and is idempotent.
