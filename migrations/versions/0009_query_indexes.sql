-- Active listings drive the catalog, deals, arbitrage and alerts.
-- A partial index keeps it small: sold and delisted rows are never queried.
CREATE INDEX IF NOT EXISTS ix_listings_gift_active
    ON listings(gift_id, price_ton) WHERE active;

-- The sync loads every listing of one marketplace up front on each pass.
CREATE INDEX IF NOT EXISTS ix_listings_marketplace_external
    ON listings(marketplace, external_id);

-- Stale listing detection scans by marketplace and last seen time.
CREATE INDEX IF NOT EXISTS ix_listings_marketplace_seen
    ON listings(marketplace, last_seen_at) WHERE active;

-- Peer medians group by collection and model.
CREATE INDEX IF NOT EXISTS ix_gifts_collection_model
    ON gifts(collection_id, model) WHERE is_active;

-- Catalog search does ILIKE on name and model.
CREATE INDEX IF NOT EXISTS ix_gifts_name_lower ON gifts(lower(name));
CREATE INDEX IF NOT EXISTS ix_gifts_model_lower ON gifts(lower(model));

-- Movers and gift history read snapshots newest first per gift.
CREATE INDEX IF NOT EXISTS ix_price_snapshots_gift_time
    ON price_snapshots(gift_id, observed_at DESC);

-- Sale history panel and trade stats.
CREATE INDEX IF NOT EXISTS ix_trades_gift_time ON trades(gift_id, traded_at DESC);

-- Alert cooldown checks hit rule, gift and time together.
CREATE INDEX IF NOT EXISTS ix_alert_events_rule_gift_time
    ON alert_events(rule_id, gift_id, created_at DESC);

-- The delivery worker only ever wants unsent events.
CREATE INDEX IF NOT EXISTS ix_alert_events_pending
    ON alert_events(created_at) WHERE notification_sent_at IS NULL;

-- Alert evaluation loads active rules by type.
CREATE INDEX IF NOT EXISTS ix_alert_rules_active_type
    ON alert_rules(rule_type, gift_id) WHERE is_active;

-- Watchlist reads a user's saved gifts newest first.
CREATE INDEX IF NOT EXISTS ix_watchlist_user_created
    ON watchlist_items(user_id, created_at DESC);
