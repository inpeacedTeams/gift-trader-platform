CREATE TABLE IF NOT EXISTS sniper_watches (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    gift_name VARCHAR(255),
    model VARCHAR(255),
    max_price_ton NUMERIC(24,9),
    min_discount_percent NUMERIC(6,2),
    marketplace VARCHAR(64),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_sniper_watches_active ON sniper_watches(is_active, user_id);

-- One hit per listing per watch, so a lot that sits on the book is announced
-- once instead of on every poll.
CREATE TABLE IF NOT EXISTS sniper_hits (
    id BIGSERIAL PRIMARY KEY,
    watch_id BIGINT NOT NULL REFERENCES sniper_watches(id) ON DELETE CASCADE,
    listing_id BIGINT NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    price_ton NUMERIC(24,9) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_sniper_hit UNIQUE (watch_id, listing_id)
);
CREATE INDEX IF NOT EXISTS ix_sniper_hits_created ON sniper_hits(created_at DESC);
