-- A trader's own book. Buys are recorded by hand because no marketplace
-- exposes "what this wallet paid", and a P&L guessed from floor history
-- would be fiction.
CREATE TABLE IF NOT EXISTS positions (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    gift_id BIGINT NOT NULL REFERENCES gifts(id),
    buy_price_ton NUMERIC(24,9) NOT NULL,
    buy_marketplace VARCHAR(64),
    opened_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    sell_price_ton NUMERIC(24,9),
    sell_marketplace VARCHAR(64),
    closed_at TIMESTAMPTZ,
    note VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- An earlier draft of this migration shipped a different shape. Anyone who
-- applied it gets migrated instead of left with a table the ORM cannot use.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'positions' AND column_name = 'buy_marketplace'
    ) THEN
        ALTER TABLE positions ADD COLUMN buy_marketplace VARCHAR(64);
    END IF;
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'positions' AND column_name = 'marketplace'
    ) THEN
        UPDATE positions SET buy_marketplace = marketplace WHERE buy_marketplace IS NULL;
        ALTER TABLE positions DROP COLUMN marketplace;
    END IF;
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'positions' AND column_name = 'quantity'
    ) THEN
        ALTER TABLE positions DROP COLUMN quantity;
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'positions' AND column_name = 'created_at'
    ) THEN
        ALTER TABLE positions ADD COLUMN created_at TIMESTAMPTZ NOT NULL DEFAULT now();
    END IF;
END $$;

-- The open book is the hot read: every visit to the tab asks for it.
CREATE INDEX IF NOT EXISTS ix_positions_user_open ON positions(user_id, closed_at);
CREATE INDEX IF NOT EXISTS ix_positions_gift ON positions(gift_id);
