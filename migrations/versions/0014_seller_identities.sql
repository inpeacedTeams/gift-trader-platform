-- Recognise a user's own listings.
--
-- Tonnel publishes `owner` and MRKT publishes `ownerId`, both Telegram user
-- ids, and the product signs in with Telegram. Storing that link lets the
-- market data answer "which of these lots are mine" without the user proving
-- ownership of anything.
CREATE TABLE IF NOT EXISTS seller_identities (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    -- NULL means the handle is valid on every venue, which is true of a
    -- Telegram id. A venue with its own seller key gets its own row.
    marketplace VARCHAR(64),
    seller VARCHAR(255) NOT NULL,
    source VARCHAR(16) NOT NULL DEFAULT 'manual',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- COALESCE because Postgres treats NULLs as distinct, which would otherwise
-- allow the same market wide handle to be stored twice.
CREATE UNIQUE INDEX IF NOT EXISTS uq_seller_identity
    ON seller_identities(user_id, COALESCE(marketplace, ''), seller);
CREATE INDEX IF NOT EXISTS ix_seller_identities_seller ON seller_identities(seller);

-- One notice per listing, holding the rival price that triggered it, so a
-- second warning only goes out when somebody actually went lower again.
CREATE TABLE IF NOT EXISTS undercut_notices (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    listing_id BIGINT NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    my_price_ton NUMERIC(24,9) NOT NULL,
    rival_price_ton NUMERIC(24,9) NOT NULL,
    notified_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_undercut_listing UNIQUE (listing_id)
);

CREATE INDEX IF NOT EXISTS ix_undercut_notices_user ON undercut_notices(user_id, notified_at DESC);

-- Seller is only ever read as a filter, and the table is large.
CREATE INDEX IF NOT EXISTS ix_listings_seller_active
    ON listings(seller) WHERE active AND seller IS NOT NULL;
