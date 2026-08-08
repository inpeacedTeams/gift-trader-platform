export type Marketplace = "fragment" | "portals" | "getgems" | "tonnel" | "tonapi";
export type Listing = { marketplace: Marketplace; listing_id: string; gift_id: string; canonical_id?: string | null; collection_id?: string | null; collection_name?: string | null; name?: string | null; price_ton: string; url?: string | null; observed_at: string };
export type Snapshot = { marketplace: Marketplace; observed_at: string; listings: Listing[] };
export type Opportunity = { gift_key: string; buy_marketplace: Marketplace; sell_marketplace: Marketplace; buy_listing_id: string; sell_listing_id: string; buy_price_ton: string; sell_price_ton: string; profit_ton: string; profit_percent: string };
export type MarketResponse = { data_mode: "live-only"; markets: Snapshot[] };
export type ArbitrageResponse = { data_mode: "live-only"; opportunities: Opportunity[]; unavailable: { marketplace: string; reason: string }[] };

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

export type GiftCard = {
  id: number;
  canonical_id: string;
  collection_id?: number | null;
  collection_name?: string | null;
  name?: string | null;
  model?: string | null;
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

export type Deal = {
  gift_id: number;
  name?: string | null;
  model?: string | null;
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
