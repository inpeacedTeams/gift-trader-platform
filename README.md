<div align="center">

# 🎁 Gift Trader Platform

**A trading terminal for Telegram NFT gifts on TON.**

Every price on screen came from a marketplace we actually read.
Nothing is estimated, filled in, or demoed.

[Quick start](#-quick-start) · [Features](#-what-it-does) · [Data sources](#-where-the-data-comes-from) · [Configuration](#-configuration) · [API](#-api) · [Architecture](#-architecture)

</div>

---

## The idea

Telegram gifts trade across half a dozen venues that do not talk to each
other. The same gift can sit at 40 TON on one and 55 on another, a rare
backdrop gets priced like a common one, and by the time you have opened four
tabs the cheap lot is gone.

This crawls all of them into one database, keeps the history, and turns it
into the four questions a trader actually asks:

> **What is it worth? · Is this cheap? · Can I sell it again? · Am I up or down?**

### One rule

**If we do not know, we say so.** A gift with no listing shows *no price*,
not zero. A short price history reports *not enough data*, not a confident
number built on three points. A source that is down says why, on the
Settings page, instead of quietly disappearing. Profit is always after fees
and gas, because a 4% spread on a venue that keeps 5% is a loss.

---

## ✨ What it does

### Find

| | |
| --- | --- |
| **Catalog** | Every tracked gift with search, price and depth filters, sorting, and filters on model, backdrop, symbol and rarity tier |
| **Collections** | Browse by collection, with floor and listing count per collection |
| **Deals** | Lots priced below the median of their peer group (same collection, model *and* rarity), so a rare backdrop is not compared to a plain one |
| **Movers** | Biggest gainers and losers over 24h or 7d |
| **Opportunities** | Cross marketplace spreads, net of the seller fee at the exit venue and the gas of moving the gift |
| **Live feed** | Listings, delistings and price changes as they land, polled every 15s |

### Judge

| | |
| --- | --- |
| **Gift page** | Floor, median, depth, full order book, and a price chart coloured by direction with a crosshair |
| **Rarity** | Model, backdrop and symbol with their published scarcity, and a badge for the rarest trait |
| **Liquidity** | Median time to sale, sales per week, order book depth, and a warning when the floor is one lonely lot |
| **Volatility** | Daily price spread, trading range, worst drawdown, and how often the price moves at all |
| **Sale history** | Confirmed sales, which outrank listing prices for valuation |
| **Flip calculator** | Buy at X, sell at Y: commission, gas, net proceeds, ROI and the breakeven price |
| **AI analyst** | Chat and per gift verdicts, grounded strictly in our database. It cannot browse and will not invent a price |

### Act

| | |
| --- | --- |
| **Sniper** | Standing orders on the fast loop. Polls the cheapest page every ~20s and pings Telegram when something matches. Off by default |
| **Alerts** | Price thresholds and percentage moves per gift or across the whole market, delivered to Telegram |
| **Watchlist** | Saved gifts as live cards, not bare ids |
| **Positions** | What you paid, days held, and P&L marked against what an exit would really pay today |
| **Selling** | Your own lots, matched by the Telegram id the marketplaces publish as the seller |
| **Undercut alerts** | *«Ваш лот перебили»*: fires when a comparable lot appears below yours, once, and again only if the rival drops further |
| **Portfolio** | TON wallets, holdings and valuation history |

---

## 🚀 Quick start

```bash
git clone https://github.com/inpeacedTeams/gift-trader-platform.git
cd gift-trader-platform
cp .env.example .env

# Required: the app refuses to boot in production with the placeholder secret
python -c "import secrets; print(secrets.token_urlsafe(48))"   # → JWT_SECRET

docker compose up -d --build
```

The crawler starts on its own and fills the database within a few minutes.
Watch it arrive:

```bash
curl localhost:8000/api/health
curl localhost:8000/api/sources/status   # per source health and failure reasons
curl localhost:8000/api/overview         # headline numbers once the first pass lands
```

**No credentials are needed to start.** Tonnel is public and GetGems works
without a token. Everything below is optional and each one unlocks something
specific.

### Without Docker

```bash
docker compose up -d postgres
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.lock
python -m app.db.migrate && python -m app.db.verify_schema
uvicorn app.main:app --reload

cd web && npm ci && npm run dev
```

### Upgrading an existing install

```bash
git pull
docker compose up -d --build   # migrations run on boot
```

---

## 📡 Where the data comes from

Active parsers are chosen with `MARKET_SOURCES` (default `tonnel,getgems`).

| Source | Credentials | What it gives you |
| --- | --- | --- |
| **Tonnel** | none | Primary listing feed and confirmed sale history. Public endpoint, full book |
| **GetGems** | optional `TONAPI_TOKEN` | Collection items via TONAPI, filtered to active sales |
| **MRKT** | `MRKT_TOKEN` or `MRKT_INIT_DATA` | Second venue, which is what makes arbitrage possible at all |
| **Portals** | `PORTALS_AUTH_DATA` | Large book, but the mini app initData expires within hours |
| **Fragment** | none | HTML scrape. Fragile by nature and fails loudly when the page changes |

**Arbitrage needs at least two venues carrying the same gift.** With the
default pair the Opportunities page will mostly be empty; add `mrkt` to
`MARKET_SOURCES` to light it up.

A source that cannot deliver never invents listings and never falls back to
fixtures. It reports `unavailable` with the reason, and the Settings page
distinguishes *not configured* from *broken* from *stale*.

---

## ⚙️ Configuration

Full list with comments in [`.env.example`](.env.example). The ones that matter:

### Required

| Variable | Why |
| --- | --- |
| `JWT_SECRET` | Signs login tokens. Boot fails in production while it is the placeholder or too short |
| `DATABASE_URL` | PostgreSQL. Docker Compose sets this for you |

### Unlock a feature

| Variable | Unlocks | How to get it |
| --- | --- | --- |
| `TELEGRAM_BOT_TOKEN` | Alert and sniper delivery to Telegram | [@BotFather](https://t.me/BotFather) |
| `OPENROUTER_API_KEY` | The AI analyst and per gift verdicts | [openrouter.ai/keys](https://openrouter.ai/keys) |
| `TONNEL_AUTH_DATA` | Confirmed sale history, which beats listing prices for valuation | market.tonnel.network → DevTools → Application → Local Storage → `web-initData` |
| `MRKT_TOKEN` | MRKT as a second venue, and with it real arbitrage | Telegram Web → @mrkt → DevTools → Network → `Authorization` header |
| `TONAPI_TOKEN` | Higher GetGems rate limits | [tonconsole.com](https://tonconsole.com) |
| `ADMIN_TOKEN` | The manual crawl endpoints. Empty disables them entirely | Any long random string |

> ⚠️ `TONNEL_AUTH_DATA`, `MRKT_TOKEN` and `PORTALS_AUTH_DATA` are live session
> credentials for your own accounts. `.env` is gitignored. Keep it that way,
> and never paste them into a chat.

### Worth knowing

| Variable | Default | Note |
| --- | --- | --- |
| `MARKET_SYNC_INTERVAL_SECONDS` | `300` | Full crawl of every enabled source |
| `CRAWL_MAX_PAGES` | `200` | How deep one pass goes. Lower it if a source starts rate limiting |
| `SNIPER_ENABLED` | `false` | A 20s loop is real traffic against the marketplaces. Opt in deliberately |
| `RATE_LIMIT_*` | `120` read / `20` write per minute | In memory, so **per process**. Move it to Redis before scaling out |
| `AI_REQUESTS_PER_HOUR` | `30` | The OpenRouter key is yours, so every endpoint that spends it is capped |

---

## 🔌 API

All routes are under `/api`. Reads are public, anything personal needs a
Telegram login.

<details>
<summary><b>Market</b></summary>

| Method | Path | |
| --- | --- | --- |
| `GET` | `/overview` | Headline stats and data freshness |
| `GET` | `/gifts` | Catalog: search, filters, rarity, sorting, pagination |
| `GET` | `/gifts/{id}` | One gift with its full order book |
| `GET` | `/gifts/{id}/history` | Floor and median over time |
| `GET` | `/gifts/{id}/trades` | Confirmed sales |
| `GET` | `/gifts/attributes` | Traits with scarcity and the floor each one trades at |
| `GET` | `/collections` | Collections with floor and depth |
| `GET` | `/deals` | Underpriced against the peer median |
| `GET` | `/movers` | Top gainers and losers |
| `GET` | `/events` | Change log, `after_id` for incremental polling |
| `GET` | `/arbitrage` | Fee aware cross venue spreads |
| `GET` | `/fees` | Per venue seller fees and the gas estimate |
| `GET` | `/volatility/gifts/{id}` | Price stability, or an honest "unknown" |
| `GET` | `/sniper/gifts/{id}/liquidity` | Time to sale, depth, floor thickness |
| `GET` | `/sources/status` | Per source health, configured / stale / broken |

</details>

<details>
<summary><b>Yours (Telegram login required)</b></summary>

| Method | Path | |
| --- | --- | --- |
| `POST` | `/auth/telegram` | Sign in with mini app initData |
| `GET` | `/positions` | Your book with live P&L |
| `POST` | `/positions` | Record a buy |
| `PATCH` | `/positions/{id}` | Close, correct, or reopen a lot |
| `GET` | `/selling/listings` | Your lots and whoever is undercutting them |
| `POST` | `/selling/identities` | Claim a seller handle on a venue that is not Telegram keyed |
| `GET` | `/watchlist` | Saved gifts as full cards |
| `GET` | `/alerts/rules` · `/alerts/events` | Rules and what they fired |
| `GET` | `/sniper/watches` | Standing orders for the fast loop |
| `GET` | `/portfolio/overview` · `/portfolio/history` | Wallet holdings and valuation |
| `POST` | `/ai/ask` · `GET /ai/gifts/{id}/verdict` | The analyst, grounded in the database |

</details>

<details>
<summary><b>Admin (needs <code>X-Admin-Token</code>)</b></summary>

| Method | Path | |
| --- | --- | --- |
| `POST` | `/jobs/market-sync` | Force a crawl without waiting for the scheduler |
| `POST` | `/jobs/trade-sync` | Force a sale history pass |

</details>

---

## 🏗 Architecture

```
              ┌──────────── background workers ────────────┐
  Tonnel ──┐  │  market sync  every 5m   full book crawl   │
  MRKT ────┤  │  sniper       every 20s  cheapest page     │
  GetGems ─┼──┤  trade sync   every 15m  confirmed sales   │──┐
  Portals ─┤  │  portfolio    every 5m   wallet valuation  │  │
  Fragment ┘  │  delivery     every 30s  Telegram alerts   │  │
              └────────────────────────────────────────────┘  │
                                                              ▼
                                                       ┌─────────────┐
   React + Vite  ◄────  FastAPI  ◄──── reads only ────►│ PostgreSQL  │
                                                       └─────────────┘
```

**Writes belong to the workers, reads belong to the API.** Page loads never
trigger a crawl, which is why a dashboard renders in milliseconds instead of
waiting minutes on five marketplaces.

```
app/
├─ market/        parsers, normalisation, rarity, fee and profit math
├─ db/            models, migrations, repositories (all query logic)
├─ routes/        HTTP layer, thin by design
├─ workers/       the scheduled loops
├─ notifications/ alert rules, undercut detection, Telegram delivery
├─ ai/            OpenRouter client, prompts, grounding, quotas
└─ core/          config, auth, rate limiting, secret validation

web/src/
├─ pages/         one file per screen
├─ components/    panels shared across screens
├─ api.ts         the only place that talks to the backend
└─ format.ts      money and percentage formatting, shared everywhere
```

### Database

Ordered SQL migrations in `migrations/versions/`, applied on boot with a
checksum per file.

```bash
python -m app.db.migrate         # idempotent, safe to re-run
python -m app.db.verify_schema   # fails loudly on a half applied schema
```

---

## ✅ Verification

```bash
ruff check app tests
pytest -q
cd web && npm ci && npm run build
```

Python dependencies are pinned in `pyproject.toml` and `requirements.lock`.
GitHub Actions installs that lock file and runs the same lint, tests and
frontend build on every push and pull request to `main`.

---

## 🗺 Roadmap

Shipped and next up are tracked in the roadmap doc. Currently unbuilt:

- Telegram Mini App as the primary entry point
- Order book depth on the card (2nd and 3rd cheapest)
- Saved filter presets
- Redis backed rate limits and AI quotas, needed before running more than one worker
