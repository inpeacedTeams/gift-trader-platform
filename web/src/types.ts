export type Marketplace = "fragment" | "portals" | "getgems" | "tonapi";
export type Listing = { marketplace: Marketplace; listing_id: string; gift_id: string; canonical_id?: string | null; collection_id?: string | null; collection_name?: string | null; name?: string | null; price_ton: string; url?: string | null; observed_at: string };
export type Snapshot = { marketplace: Marketplace; observed_at: string; listings: Listing[] };
export type Opportunity = { gift_key: string; buy_marketplace: Marketplace; sell_marketplace: Marketplace; buy_listing_id: string; sell_listing_id: string; buy_price_ton: string; sell_price_ton: string; profit_ton: string; profit_percent: string };
export type MarketResponse = { data_mode: "live-only"; markets: Snapshot[] };
export type ArbitrageResponse = { data_mode: "live-only"; opportunities: Opportunity[]; unavailable: { marketplace: string; reason: string }[] };
