-- Attribute rarity. A gift is not just its model: the backdrop and the symbol
-- carry most of the premium on a rare specimen, and both were being discarded
-- at parse time, so a one-in-a-thousand backdrop was priced against a plain one.
ALTER TABLE gifts ADD COLUMN IF NOT EXISTS backdrop VARCHAR(255);
ALTER TABLE gifts ADD COLUMN IF NOT EXISTS symbol VARCHAR(255);
ALTER TABLE gifts ADD COLUMN IF NOT EXISTS model_rarity NUMERIC(6, 3);
ALTER TABLE gifts ADD COLUMN IF NOT EXISTS backdrop_rarity NUMERIC(6, 3);
ALTER TABLE gifts ADD COLUMN IF NOT EXISTS symbol_rarity NUMERIC(6, 3);
-- Bucket of the scarcest trait. NULL means we have no rarity data yet, which
-- is deliberately not the same as common.
ALTER TABLE gifts ADD COLUMN IF NOT EXISTS rarity_tier VARCHAR(16);

-- The catalog, the deal scan and the sniper all compare a gift against peers
-- in the same collection, model and rarity tier, so this triple is hot.
CREATE INDEX IF NOT EXISTS ix_gifts_peer_group
    ON gifts(collection_id, model, rarity_tier);

CREATE INDEX IF NOT EXISTS ix_gifts_backdrop
    ON gifts(backdrop) WHERE backdrop IS NOT NULL;

CREATE INDEX IF NOT EXISTS ix_gifts_symbol
    ON gifts(symbol) WHERE symbol IS NOT NULL;
