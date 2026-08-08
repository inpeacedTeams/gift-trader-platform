# Gift Trader Platform

Market intelligence for Telegram NFT gifts on TON.

## Principles

- Real marketplace and on-chain data only
- No demo fixtures or fake market values
- Every price and signal keeps its source and freshness
- Arbitrage is calculated after marketplace fees and network costs

## Live market parsers

Active parsers are chosen with `MARKET_SOURCES` (default `tonnel,getgems`).

| Source | Credentials | Notes |
| --- | --- | --- |
| **Tonnel** | none | Public `pageGifts` endpoint, primary listing feed |
| **GetGems** | optional `TONAPI_TOKEN` | Collection items through TONAPI, filtered to GetGems sales |
| **Portals** | `PORTALS_AUTH_DATA` | Telegram mini app initData, expires within hours |
| **Fragment** | none | HTML scrape, breaks whenever the page layout changes |

A source that cannot deliver fails loudly: the API returns `status=unavailable`
with the reason on `/api/source-status`. It never invents listings and never
falls back to demo data.

## Run locally

```bash
git clone https://github.com/inpeacedTeams/gift-trader-platform.git
cd gift-trader-platform
cp .env.example .env

docker compose up -d --build
curl -X POST localhost:8000/api/jobs/market-sync
curl localhost:8000/api/source-status
```

No credentials are required for the default setup. Add `TONAPI_TOKEN` to raise
GetGems rate limits, and `PORTALS_AUTH_DATA` if you enable the Portals source.

For backend development without Docker:

```bash
docker compose up -d postgres
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.lock
uvicorn app.main:app --reload
```

The frontend runs separately from `web` with `npm ci && npm run dev`.

## Verification

```bash
ruff check app tests
pytest -q
cd web && npm ci && npm run build
```

All direct Python dependencies are pinned in `pyproject.toml` and `requirements.lock`. GitHub Actions installs that lock file and runs the same backend lint/tests and frontend build for pushes and pull requests to `main`.

## Key endpoints

- `GET /api/markets/snapshots`: live source snapshots, persisted to PostgreSQL
- `GET /api/gifts`: persisted catalog with search and pagination
- `GET /api/gifts/{id}/history`: price history
- `GET /api/arbitrage`: fee-aware live opportunities
- `GET /api/portfolio/overview`: TONAPI holdings and valuation
- `GET /api/portfolio/history`: persisted portfolio valuation history
- `GET /api/portfolio/resolver-summary`: unknown NFT resolver telemetry
- `GET /api/alerts/events`: user alert events
- `GET /api/source-status`: per source health and failure reasons
- `POST /api/jobs/market-sync`: trigger a sync without waiting for the scheduler
