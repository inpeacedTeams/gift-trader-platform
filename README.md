# Gift Trader Platform

Market intelligence and a trading terminal for Telegram NFT gifts on TON.
Crawls every marketplace it can reach, stores the whole book, and turns it
into the numbers a flipper actually acts on: what is underpriced, what it
costs to exit, how fast it sells, and whether anybody has undercut you.

## Principles

- Real marketplace and on-chain data only. No demo fixtures, no filler values.
- Every price keeps its source and its freshness. A stale number says so.
- A source that cannot deliver reports the reason instead of returning nothing.
- Profit is always shown net of marketplace fees and gas, never as a raw spread.
- Unknown is not zero. A gift nobody lists has no value, and stays out of totals.

## What it does

**Market data**

- Full market crawl on a timer, every listing per gift, not just the floor.
- Change log: listed, delisted, price up, price down, with a live feed.
- Price history, floor and median, with a directional chart.
- Attribute rarity: model, backdrop and symbol with their published share, so a
  rare specimen is never priced against a plain one.

**Finding trades**

- Deals: listings under the median of their peer group (same collection, model
  and rarity tier), with a minimum peer count so a thin group cannot fake one.
- Opportunities: cross marketplace spreads, computed after the seller fee and
  gas of the round trip.
- Movers: biggest gainers and losers over 24h or 7d.
- Sniper: standing orders checked on a fast loop for lots that appear cheap.
  Off by default, see `SNIPER_ENABLED`.
- Flip calculator on every gift page: buy price, exit venue, breakeven.

**Judging a trade**

- Liquidity: median time from listing to sale, sales per week, order book
  depth, and a warning when the floor is one lonely lot.
- Volatility: daily spread of the floor, its range, worst drawdown, and how
  often the price moves at all. Reports "unknown" below six observations
  rather than quoting a number built on noise.
- Sale history from confirmed Tonnel trades, which outrank asking prices.
- AI analyst: a market chat and a per gift verdict, grounded only in the
  database. It never browses and never invents a price.

**Your side of the market**

- Positions: what you paid, days held, and P&L marked against what an exit
  would really pay after fees.
- Selling: the lots on sale under your Telegram account, each with the
  cheapest comparable lot that is not yours.
- "Your lot was undercut" alerts, sent once per listing and repeated only if
  the rival drops further.
- Price alerts, one click from a gift page, delivered to Telegram.
- Watchlist and wallet portfolio valuation.

## Live market parsers

Active sources are chosen with `MARKET_SOURCES` (default `tonnel,getgems`).

| Source | Credentials | Notes |
| --- | --- | --- |
| **Tonnel** | none | Public `pageGifts`, the primary feed. Sale history needs `TONNEL_AUTH_DATA` |
| **GetGems** | optional `TONAPI_TOKEN` | Collection items via TONAPI, filtered to GetGems sales |
| **MRKT** | `MRKT_TOKEN` or `MRKT_INIT_DATA` | Second venue, which is what makes arbitrage possible |
| **Portals** | `PORTALS_AUTH_DATA` | Telegram mini app initData, expires within hours |
| **Fragment** | none | HTML scrape, breaks whenever the page layout changes |

A source that fails is reported as `unavailable` with its reason on
`/api/sources/status`, alongside whether it is even configured. A switched off
source is not the same as a broken one, and neither is ever hidden.

Tonnel and MRKT publish the seller as a Telegram user id, which is how the
product recognises your own listings without you configuring anything.

## Run locally

```bash
git clone https://github.com/inpeacedTeams/gift-trader-platform.git
cd gift-trader-platform
cp .env.example .env

docker compose up -d --build
python -m app.db.migrate
python -m app.db.verify_schema
```

No credentials are needed for the default setup: Tonnel is public. The
scheduler starts crawling on boot, so data appears within a few minutes.

To force a pass instead of waiting, set `ADMIN_TOKEN` and:

```bash
curl -X POST localhost:8000/api/jobs/market-sync -H "X-Admin-Token: $ADMIN_TOKEN"
curl localhost:8000/api/sources/status
```

Backend without Docker:

```bash
docker compose up -d postgres
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.lock
uvicorn app.main:app --reload
```

The frontend runs separately from `web` with `npm ci && npm run dev`.

## Configuration

Everything is read from `.env`. The ones that change behaviour:

| Variable | Default | What it does |
| --- | --- | --- |
| `JWT_SECRET` | placeholder | Must be changed. Production refuses to boot on the default |
| `ADMIN_TOKEN` | unset | Required to trigger crawls by hand; without it `/api/jobs/*` is disabled |
| `MARKET_SOURCES` | `tonnel,getgems` | Which parsers run |
| `CRAWL_MAX_PAGES` | `200` | How deep one pass goes. Lower it if a source rate limits |
| `MARKET_SYNC_INTERVAL_SECONDS` | `300` | Time between full crawls |
| `SNIPER_ENABLED` | `false` | Opt in: a 20s loop is steady traffic against marketplaces |
| `TELEGRAM_BOT_TOKEN` | unset | Without it alerts are stored but never delivered |
| `OPENROUTER_API_KEY` | unset | Turns on the AI analyst. Key stays server side |
| `OPENROUTER_MODEL` | `openrouter/free` | Free router by default |
| `AI_REQUESTS_PER_HOUR` | `30` | The key is yours, so every endpoint spending it is capped |
| `RATE_LIMIT_READS_PER_MINUTE` | `120` | Public API budget per caller |
| `RATE_LIMIT_WRITES_PER_MINUTE` | `20` | Same, for writes |

Secrets belong in a local `.env` only. It is gitignored; keep it that way.

## Database

Ordered SQL migrations in `migrations/versions/`, applied by a runner that
records a checksum per version:

```bash
python -m app.db.migrate         # apply everything pending
python -m app.db.verify_schema   # fails loudly if a migration was skipped
```

`verify_schema` is worth running after every deploy. A migration that only
adds a column can fail silently, and the first symptom would otherwise be a
query blowing up in a background worker where nobody is watching.

New migrations must use a fresh numeric prefix and never reuse an old one.

## Key endpoints

All under `/api`.

**Market**

- `GET /overview`: dashboard stats and data freshness, read from storage
- `GET /gifts`: catalog with search, price range, trait and rarity filters
- `GET /gifts/attributes`: traits with their scarcity and what each one trades at
- `GET /gifts/{id}`: one gift with its full order book
- `GET /gifts/{id}/history`: floor and median over time
- `GET /gifts/{id}/trades`: confirmed sales
- `GET /collections`: collections with gift counts and floors
- `GET /events`: change log, `after_id` for incremental polling
- `GET /movers`: gainers and losers

**Trading**

- `GET /deals`: listings under their peer median
- `GET /arbitrage`: fee-aware cross marketplace spreads
- `GET /fees`: seller fees per venue and the gas estimate
- `GET /volatility/gifts/{id}`: how much the floor moves, and how often
- `GET /sniper/gifts/{id}/liquidity`: time to sale, depth, floor gap
- `GET|POST|PATCH|DELETE /sniper/watches`: standing orders for the fast loop

**Yours** (Telegram auth required)

- `GET|POST|PATCH|DELETE /positions`: your book with live P&L
- `GET /selling/listings`: your lots and whoever is undercutting them
- `GET|POST|DELETE /selling/identities`: seller handles we match you by
- `GET|POST|DELETE /watchlist`
- `GET|POST|PATCH|DELETE /alerts/rules`, `GET /alerts/events`
- `GET /portfolio/overview`, `GET /portfolio/history`

**AI and operations**

- `GET /ai/status`, `POST /ai/ask`, `GET /ai/gifts/{id}/verdict`
- `GET /sources/status`: per source health, config state and failure reasons
- `POST /jobs/market-sync`, `POST /jobs/trade-sync`: admin token required

## Verification

```bash
ruff check app tests
pytest -q
cd web && npm ci && npm run build
```

Direct Python dependencies are pinned in `pyproject.toml` and
`requirements.lock`. GitHub Actions installs that lock file and runs the same
backend lint and tests plus the frontend build on every push and pull request
to `main`.

## Known limits

- Rate limiting and the AI quota are per process. Running more than one worker
  needs Redis behind them before those numbers mean anything.
- Portals initData expires within hours, so that source needs a fresh value to
  stay online.
- Manually claimed seller handles cannot be verified; only the Telegram id
  derived from login is trustworthy, and the interface labels which is which.
