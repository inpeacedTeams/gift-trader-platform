-- Strategy research.
--
-- A strategy is stored as JSON, not as columns. Its shape will grow, and a
-- saved rule must keep meaning what it meant on the day it was measured;
-- typed columns would silently rewrite old strategies with every migration.
CREATE TABLE IF NOT EXISTS strategies (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(120) NOT NULL,
    -- discovered | ai | manual
    source VARCHAR(16) NOT NULL DEFAULT 'manual',
    definition JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_strategies_user_created ON strategies(user_id, created_at DESC);

-- Runs are append only. A backtest re-run against more history is a
-- different result, and overwriting would hide that the answer moved.
CREATE TABLE IF NOT EXISTS strategy_runs (
    id BIGSERIAL PRIMARY KEY,
    strategy_id BIGINT NOT NULL REFERENCES strategies(id) ON DELETE CASCADE,
    window_days INTEGER NOT NULL,
    history_days NUMERIC(8,2) NOT NULL,
    trades INTEGER NOT NULL DEFAULT 0,
    median_profit_percent NUMERIC(10,2),
    -- The half the strategy was not selected on. The honest column.
    out_of_sample_percent NUMERIC(10,2),
    holds_up BOOLEAN NOT NULL DEFAULT FALSE,
    metrics JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_strategy_runs_strategy ON strategy_runs(strategy_id, created_at DESC);

-- The backtest walks listings by when they appeared, which nothing else did.
CREATE INDEX IF NOT EXISTS ix_listings_first_seen ON listings(first_seen_at);
