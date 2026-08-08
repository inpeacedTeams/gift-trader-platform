# Database migrations

Ordered SQL migrations live in `versions/`.

```bash
python -m app.db.migrate
python -m app.db.migrate  # safe no-op, required in CI
python -m app.db.verify_schema
```

The runner creates `schema_migrations`, applies files in lexical order, stores
a SHA-256 checksum, and records every version transactionally. If two legacy
files contain the same SQL, the later one is recorded as `skipped_duplicate`
instead of executing twice.

`verify_schema` is the safety net. A migration that only adds a column can
fail without taking the table with it, and the first symptom would otherwise
be a query breaking inside a background worker.

## Clean install order

| Version | What it adds |
| --- | --- |
| `0001_market_foundation` | Collections, gifts, listings, price snapshots |
| `0002_user_features` | Users, watchlist, wallets, alert rules and events |
| `0003_portfolio_holdings` | Wallet holdings |
| `0004_portfolio_valuation` | Portfolio value over time |
| `0005_portfolio_valuation_provenance` | Where each valuation came from |
| `0006_alert_notification_delivery` | Telegram delivery state on alert events |
| `0007_resolver_telemetry` | Why an NFT could not be priced |
| `0008_market_events` | Change log: listed, delisted, price moves |
| `0009_query_indexes` | Partial indexes for the hot read paths |
| `0010_liquidity` | `listings.closed_at`, which gives time to sale |
| `0011_sniper` | Sniper watches and their hits |
| `0012_attribute_rarity` | Backdrop, symbol, per trait rarity and rarity tier |
| `0013_positions` | What the user paid, and what they sold it for |
| `0014_seller_identities` | Seller handles, plus undercut notice state |
| `0015_alert_events_without_rule` | Alerts that fire from a watch, not a rule |

New migrations must use a fresh filename and a fresh numeric prefix. Never
reuse a prefix, and never edit a migration that has already been applied: the
checksum is what makes a partial deploy detectable.
