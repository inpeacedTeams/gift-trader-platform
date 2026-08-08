# Database migrations

Ordered SQL files in `versions/`, applied in lexical order.

```bash
python -m app.db.migrate         # idempotent, safe to re-run
python -m app.db.verify_schema   # fails loudly on a half applied schema
```

The runner creates `schema_migrations`, stores a SHA-256 checksum per file and
records every version transactionally. If two legacy files contain identical
SQL, the later one is recorded as `skipped_duplicate` rather than executed
twice.

`verify_schema` is the safety net: a migration that only adds columns can fail
silently, and the first symptom would otherwise be a query blowing up in
production. It checks the tables, the columns later migrations added, and the
columns later migrations made nullable.

## Current order

| File | What it adds |
| --- | --- |
| `0001_market_foundation.sql` | Collections, gifts, listings, price snapshots |
| `0002_user_features.sql` | Users, watchlist, wallets, alert rules and events |
| `0003_portfolio_holdings.sql` | Wallet holdings |
| `0004_portfolio_valuation.sql` | Valuation history |
| `0005_portfolio_valuation_provenance.sql` | Where a valuation came from |
| `0006_alert_notification_delivery.sql` | Telegram delivery state on alerts |
| `0007_resolver_telemetry.sql` | Unresolved NFT telemetry |
| `0008_market_events.sql` | Change log: listed, delisted, price up, price down |
| `0009_query_indexes.sql` | Partial indexes for the hot read paths |
| `0010_liquidity.sql` | `listings.closed_at`, which gives time to sale |
| `0011_sniper.sql` | Sniper watches and hits |
| `0012_attribute_rarity.sql` | Backdrop, symbol, per trait rarity, rarity tier |
| `0013_positions.sql` | Positions: entry price, exit, P&L basis |
| `0014_seller_identities.sql` | Seller handles and undercut notices |
| `0015_alert_events_without_rule.sql` | Alerts that fire without a rule (sniper, undercut) |
| `0016_strategies.sql` | Saved strategies and their backtest runs |

New migrations must use a unique filename and must not reuse a numeric prefix.
