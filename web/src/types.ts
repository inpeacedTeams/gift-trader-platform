export type Marketplace = "fragment" | "portals" | "getgems" | "tonnel" | "tonapi";
export type Listing = { marketplace: Marketplace; listing_id: string; gift_id: string; canonical_id?: string | null; collection_id?: string | null; collection_name?: string | null; name?: string | null; price_ton: string; url?: string | null; observed_at: string };
export type Snapshot = { marketplace: Marketplace; observed_at: string; listings: Listing[] };
export type MarketResponse = { data_mode: "live-only"; markets: Snapshot[] };

export type OverviewStats = {
  data_mode: string;
  active_listings: number;
  listed_gifts: number;
  tracked_gifts: number;
  collections: number;
  market_value_ton?: string | null;
  sources_online: number;
  events_24h: number;
  sales_24h: number;
  last_sync_at?: string | null;
};

export type ArbitrageOpportunity = {
  gift_id: number;
  name?: string | null;
  model?: string | null;
  image_url?: string | null;
  collection_name?: string | null;
  buy_marketplace: string;
  sell_marketplace: string;
  buy_price_ton: string;
  sell_price_ton: string;
  buy_url?: string | null;
  sell_url?: string | null;
  profit_ton: string;
  profit_percent: string;
};
export type ArbitrageList = { data_mode: string; items: ArbitrageOpportunity[] };

export type SourceStatusCard = {
  marketplace: string;
  status: string;
  configured: boolean;
  stale: boolean;
  listings_count: number;
  last_attempt_at?: string | null;
  last_success_at?: string | null;
  last_error?: string | null;
};
export type SourceStatusList = { data_mode: string; sources: SourceStatusCard[] };

export type CollectionCard = {
  id: number;
  name?: string | null;
  slug?: string | null;
  chain_address: string;
  gift_count: number;
  listings_count: number;
  floor_ton?: string | null;
  image_url?: string | null;
};
export type CollectionPage = { data_mode: string; items: CollectionCard[]; page: number; page_size: number; total: number; has_next: boolean };

/** Scarcity bucket of a gift's rarest trait. Absent means we hold no rarity
 *  data for it yet, which is deliberately not the same as "common". */
export type RarityTier = "legendary" | "rare" | "uncommon" | "common";

export type GiftCard = {
  id: number;
  canonical_id: string;
  collection_id?: number | null;
  collection_name?: string | null;
  name?: string | null;
  model?: string | null;
  model_rarity?: string | null;
  backdrop?: string | null;
  backdrop_rarity?: string | null;
  symbol?: string | null;
  symbol_rarity?: string | null;
  rarity_tier?: RarityTier | null;
  gift_number?: number | null;
  image_url?: string | null;
  floor_ton?: string | null;
  median_ton?: string | null;
  listings_count: number;
  change_percent?: string | null;
  best_marketplace?: string | null;
  deal_percent?: string | null;
};
export type GiftPage = { data_mode: string; items: GiftCard[]; page: number; page_size: number; total: number; has_next: boolean };

/** One trait value with its scarcity and what it currently trades at. */
export type AttributeStat = {
  value: string;
  rarity_percent?: string | null;
  gift_count: number;
  listings_count: number;
  floor_ton?: string | null;
};
export type AttributeGroups = {
  data_mode: string;
  models: AttributeStat[];
  backdrops: AttributeStat[];
  symbols: AttributeStat[];
};

export type WatchlistCard = GiftCard & { saved_at: string };
export type WatchlistPage = { data_mode: string; items: WatchlistCard[] };
export type GiftListing = {
  id: number;
  marketplace: string;
  external_id: string;
  price_ton: string;
  seller?: string | null;
  url?: string | null;
  first_seen_at: string;
  last_seen_at: string;
  active: boolean;
};
export type GiftDetail = GiftCard & { listings: GiftListing[]; sources: string[] };
export type PricePoint = { observed_at: string; marketplace: string; floor_ton?: string | null; median_ton?: string | null; volume_ton?: string | null; listings_count: number };
export type GiftHistory = { data_mode: string; gift_id: number; points: PricePoint[] };

export type MarketEventType = "listed" | "price_down" | "price_up" | "delisted";
export type MarketEvent = {
  id: number;
  gift_id: number;
  name?: string | null;
  model?: string | null;
  image_url?: string | null;
  collection_name?: string | null;
  marketplace: string;
  event_type: MarketEventType;
  price_ton?: string | null;
  previous_ton?: string | null;
  change_percent?: string | null;
  occurred_at: string;
};
export type MarketEventFeed = { data_mode: string; items: MarketEvent[]; latest_id?: number | null };

export type TradeRecord = {
  id: number;
  marketplace: string;
  price_ton: string;
  seller?: string | null;
  buyer?: string | null;
  traded_at: string;
};
export type TradeStats = {
  window_days: number;
  sales_count: number;
  lowest_ton?: string | null;
  highest_ton?: string | null;
  median_ton?: string | null;
  volume_ton?: string | null;
  last_sold_at?: string | null;
};
export type GiftTrades = { data_mode: string; gift_id: number; stats: TradeStats; items: TradeRecord[] };

export type Deal = {
  gift_id: number;
  name?: string | null;
  model?: string | null;
  backdrop?: string | null;
  symbol?: string | null;
  rarity_tier?: RarityTier | null;
  gift_number?: number | null;
  image_url?: string | null;
  collection_id?: number | null;
  collection_name?: string | null;
  marketplace: string;
  price_ton: string;
  median_ton: string;
  peer_count: number;
  discount_percent: string;
  url?: string | null;
};
export type DealList = { data_mode: string; items: Deal[] };

export type MoverCard = {
  gift_id: number;
  name?: string | null;
  model?: string | null;
  image_url?: string | null;
  collection_id?: number | null;
  collection_name?: string | null;
  floor_ton: string;
  previous_ton: string;
  change_percent: string;
};
export type MoversResponse = { data_mode: string; window_hours: number; gainers: MoverCard[]; losers: MoverCard[] };

/** How quickly a gift actually converts to cash.
 *
 * A discount only matters if somebody buys. `confident` is false until we
 * have observed enough completed listings to trust the median, so the UI
 * can say "not enough data" instead of quoting a number built on one sale.
 */
export type GiftLiquidity = {
  median_hours_to_sell?: number | null;
  closed_listings: number;
  sales_per_week: number;
  active_depth: number;
  confident: boolean;
  label: string;
  floor_gap_percent?: string | null;
};
