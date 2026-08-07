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

## Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
uvicorn app.main:app --reload
```

Live snapshots are available at `GET /api/markets/snapshots?collection=<TON_COLLECTION_ADDRESS>`.
