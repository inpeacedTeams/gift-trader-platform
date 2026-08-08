# Database migrations

The repository uses one ordered SQL migration chain in `versions/`:

1. `0001_market_foundation.sql`
2. `0002_user_features.sql`
3. `0003_portfolio_holdings.sql`
4. `0004_portfolio_valuation.sql`
5. `0005_portfolio_valuation_provenance.sql`
6. `0006_alert_notification_delivery.sql`

Run it with:

```bash
python -m app.db.migrate
```

The runner creates `schema_migrations`, applies files in lexical order, and records each filename transactionally. All migrations are idempotent for clean and previously initialized databases. The duplicate legacy `0002` track has been removed and its portfolio migration is now `0003`, after the user tables it depends on.
