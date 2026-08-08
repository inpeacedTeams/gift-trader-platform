-- Positions: what a trader paid, which is the one number the market cannot
-- tell us. Without it every screen shows prices and none of them show whether
-- the user is up or down.
CREATE TABLE IF NOT EXISTS positions (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    gift_id BIGINT NOT NULL REFERENCES gifts(id),
    buy_price_ton NUMERIC(24,9) NOT NULL,
    buy_marketplace VARCHAR(64),
    opened_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- Filled in on exit. A closed row keeps its history instead of vanishing.
    sell_price_ton NUMERIC(24,9),
    sell_marketplace VARCHAR(64),
    closed_at TIMESTAMPTZ,
    note VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Open lots are read on every visit, closed ones only when asked for.
CREATE INDEX IF NOT EXISTS ix_positions_user_open ON positions(user_id, closed_at);
CREATE INDEX IF NOT EXISTS ix_positions_gift ON positions(gift_id);
