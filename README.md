# Gift Trader Platform

Market intelligence for Telegram NFT gifts on TON.

## Principles

- Real marketplace and on-chain data only
- No demo fixtures or fake market values
- Every price and signal keeps its source and freshness
- Arbitrage is calculated after marketplace fees and network costs

## Live market parsers

The API currently has three independent live collectors:

- **Fragment**: reads the public gifts marketplace page and extracts current listing links and TON prices.
- **Portals**: reads the marketplace API at `https://portal-market.com/api` and normalizes gift listings. The endpoint is configurable because the marketplace API is not an official stable public contract.
- **GetGems**: reads collection NFT items through TONAPI and keeps only listings whose marketplace is GetGems.

TONAPI is an additional source and verification layer, not the only marketplace parser. If a source is unavailable or changes its response, the API returns `status=unavailable` with the source error. It never invents listings or silently falls back to demo data.

## Run locally

```bash
git clone https://github.com/inpeacedTeams/gift-trader-platform.git
cd gift-trader-platform
cp .env.example .env
# Set DATABASE_URL, JWT_SECRET, TELEGRAM_BOT_TOKEN, and TONAPI_TOKEN

docker compose up -d postgres
python -m venv .venv
source .venv/bin/activate
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
