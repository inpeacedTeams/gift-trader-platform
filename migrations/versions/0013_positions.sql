-- A trader's own book. Buys are recorded by hand because no marketplace
-- exposes "what this wallet paid", and a P&L guessed from floor history
-- would be fiction.
CREATE TABLE IF NOT EXISTS positions (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    gift_id BIGINT NOT NULL REFERENCES gifts(id) ON DELETE CASCADE,
    marketplace VARCHAR(64),
    buy_price_ton NUMERIC(24,9) NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    opened_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    sell_price_ton NUMERIC(24,9),
    sell_marketplace VARCHAR(64),
    closed_at TIMESTAMPTZ,
    note TEXT
);

-- The open book is the hot read: every dashboard visit asks for it.
CREATE INDEX IF NOT EXISTS ix_positions_user_open ON positions(user_id, closed_at);
CREATE INDEX IF NOT EXISTS ix_positions_gift ON positions(gift_id);
