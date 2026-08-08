CREATE TABLE IF NOT EXISTS market_events (
    id BIGSERIAL PRIMARY KEY,
    gift_id BIGINT NOT NULL REFERENCES gifts(id) ON DELETE CASCADE,
    listing_id BIGINT REFERENCES listings(id) ON DELETE SET NULL,
    marketplace VARCHAR(64) NOT NULL,
    event_type VARCHAR(32) NOT NULL,
    price_ton NUMERIC(24,9),
    previous_ton NUMERIC(24,9),
    change_percent NUMERIC(8,2),
    occurred_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_market_events_occurred ON market_events(occurred_at DESC);
CREATE INDEX IF NOT EXISTS ix_market_events_gift ON market_events(gift_id, occurred_at DESC);
CREATE INDEX IF NOT EXISTS ix_market_events_type ON market_events(event_type, occurred_at DESC);
