-- How long a listing survived before it left the book. Filled when a listing
-- is delisted, which for a cheap lot usually means it sold.
ALTER TABLE listings ADD COLUMN IF NOT EXISTS closed_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS ix_listings_gift_closed
    ON listings(gift_id, closed_at) WHERE closed_at IS NOT NULL;
