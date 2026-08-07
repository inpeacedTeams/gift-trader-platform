# Gift Trader Platform

Market intelligence for Telegram NFT gifts on TON.

## Principles

- Real marketplace and on-chain data only
- No demo fixtures or fake market values
- Every price and signal keeps its source and freshness
- Arbitrage is calculated after marketplace fees and network costs

## Initial architecture

- `app`: API and domain foundation
- PostgreSQL for normalized market data
- Redis for freshness and job coordination

The first implementation slice is the data foundation: typed source records, health checks, and a collector boundary that refuses to silently turn missing data into fake data.

## Data policy

A source failure produces an explicit unavailable state and structured error. The API never substitutes mock listings, prices, or arbitrage opportunities.
