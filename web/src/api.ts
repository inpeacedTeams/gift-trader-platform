import type { ArbitrageList, AttributeGroups, CollectionCard, CollectionPage, DealList, GiftDetail, GiftHistory, GiftLiquidity, GiftPage, GiftTrades, MarketEventFeed, MoversResponse, OverviewStats, RarityTier, SourceStatusList, WatchlistPage } from "./types";
import { clearToken, getToken, setToken, telegramInitData, type User } from "./auth";
export type { User } from "./auth";
const base = (import.meta.env.VITE_API_URL ?? "/api").replace(/\/$/, "");

/** Thrown when the API asks us to slow down. Carries the wait in seconds. */
export class RateLimited extends Error {
  readonly retryAfter: number;

  constructor(retryAfter: number) {
    super(`Слишком много запросов. Повторите через ${retryAfter} с.`);
    this.name = "RateLimited";
    this.retryAfter = retryAfter;
  }
}

/** Prefer the server's own explanation over a bare status code. */
async function errorText(response: Response): Promise<string> {
  try {
    const body = await response.json();
    if (body && typeof body.detail === "string") return body.detail;
  } catch {
    // no JSON body, fall back to the status
  }
  return `API ${response.status}`;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  if (init.body) headers.set("Content-Type", "application/json");
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(`${base}${path}`, { ...init, headers });
  if (response.status === 401) {
    clearToken();
    throw new Error("Authentication required");
  }
  if (response.status === 429) {
    throw new RateLimited(Number(response.headers.get("Retry-After") ?? 5));
  }
  if (!response.ok) throw new Error(await errorText(response));
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}
export type WalletItem = { id: number; address: string; label?: string | null; created_at?: string };
export type PortfolioNft = { nft_address: string; name?: string | null; image_url?: string | null; estimated_price_ton?: string | null; valuation_source: string; valuation_confidence?: string | null };
export type PortfolioWallet = { wallet_id: number; address: string; label?: string | null; ton_balance: string; nfts: PortfolioNft[] };
export type PortfolioOverview = { data_mode: string; total_assets: number; valued_assets: number; unvalued_assets: number; estimated_nft_value_ton: string; wallets: PortfolioWallet[]; unavailable: { wallet_id: number; address: string; error: string }[] };
export type PortfolioPoint = { observed_at: string; total_ton: string; ton_balance: string; nft_value_ton: string; asset_count: number };

/** Gift labels ride along so the UI never has to print a bare id. */
export type GiftLabel = {
  gift_name?: string | null;
  gift_model?: string | null;
  gift_image_url?: string | null;
};
export type AlertRule = GiftLabel & {
  id: number;
  gift_id?: number | null;
  rule_type: string;
  threshold: string;
  is_active: boolean;
  created_at?: string;
};
export type AlertEvent = GiftLabel & {
  id: number;
  rule_id?: number | null;
  gift_id?: number | null;
  message: string;
  observed_value?: string | null;
  is_read: boolean;
  created_at: string;
};
export type SniperWatch = {
  id: number;
  gift_name?: string | null;
  model?: string | null;
  max_price_ton?: string | null;
  min_discount_percent?: string | null;
  marketplace?: string | null;
  is_active: boolean;
  hits: number;
};
export type AiStatus = { enabled: boolean; model?: string | null; hourly_limit?: number };
export type AiAnswer = { answer: string; model: string; grounded_in?: string; remaining?: number; cached?: boolean };
export type GiftSort = "recent" | "floor_asc" | "floor_desc" | "depth" | "change_desc" | "change_asc" | "deal_desc";

/** What a trade costs. Served by the API so the browser never guesses. */
export type MarketplaceFee = { marketplace: string; sell_fee_percent: string };
export type FeeSchedule = {
  data_mode: string;
  gas_ton: string;
  default_sell_fee_percent: string;
  marketplaces: MarketplaceFee[];
};

/** One recorded buy, marked to the live market.
 *
 * `net_value_ton` is what a sale would actually pay out after the venue fee.
 * `valued` is false when the gift has no active listing anywhere: unknown
 * value rather than zero, and such rows stay out of the totals.
 */
export type PositionCard = {
  id: number;
  gift_id: number;
  name?: string | null;
  model?: string | null;
  gift_number?: number | null;
  image_url?: string | null;
  rarity_tier?: RarityTier | null;
  collection_name?: string | null;
  buy_price_ton: string;
  buy_marketplace?: string | null;
  opened_at: string;
  sell_price_ton?: string | null;
  sell_marketplace?: string | null;
  closed_at?: string | null;
  note?: string | null;
  is_open: boolean;
  days_held: number;
  cost_ton: string;
  gas_ton: string;
  exit_marketplace?: string | null;
  exit_fee_percent: string;
  floor_ton?: string | null;
  net_value_ton?: string | null;
  profit_ton?: string | null;
  profit_percent?: string | null;
  valued: boolean;
};
export type PositionSummary = {
  open_count: number;
  closed_count: number;
  unvalued_count: number;
  invested_ton: string;
  market_value_ton: string;
  unrealized_ton: string;
  unrealized_percent?: string | null;
  realized_ton: string;
  win_rate_percent?: string | null;
};
export type PositionList = { data_mode: string; items: PositionCard[]; summary: PositionSummary };

/** A seller handle known to belong to this user.
 *
 * `source` is "telegram" when it came from the login, which is the only kind
 * we can vouch for, and "manual" when the user claimed it themselves.
 */
export type SellerIdentity = {
  id: number;
  seller: string;
  marketplace?: string | null;
  source: string;
  created_at: string;
};

/** One of the user's own listings, with the competition beside it. */
export type MyListing = {
  listing_id: number;
  gift_id: number;
  name?: string | null;
  model?: string | null;
  backdrop?: string | null;
  symbol?: string | null;
  rarity_tier?: RarityTier | null;
  gift_number?: number | null;
  image_url?: string | null;
  collection_name?: string | null;
  marketplace: string;
  price_ton: string;
  net_proceeds_ton: string;
  url?: string | null;
  listed_at: string;
  rival_price_ton?: string | null;
  rival_marketplace?: string | null;
  rival_url?: string | null;
  rival_gift_id?: number | null;
  competitors: number;
  undercut: boolean;
  undercut_percent?: string | null;
};
export type SellingSummary = {
  listed_count: number;
  undercut_count: number;
  listed_value_ton: string;
  net_value_ton: string;
};
export type SellingPage = {
  data_mode: string;
  items: MyListing[];
  summary: SellingSummary;
  identities: SellerIdentity[];
};

/** How much a gift's floor moves, measured on observations we stored.
 *
 * `confident` is false while the series is too short, so the interface can
 * admit it does not know instead of printing a number built on noise.
 */
export type GiftVolatility = {
  window_days: number;
  samples: number;
  observed_days: number;
  price_changes: number;
  changes_per_day?: number | null;
  low_ton?: string | null;
  high_ton?: string | null;
  range_percent?: string | null;
  daily_percent?: string | null;
  max_move_percent?: string | null;
  max_drawdown_percent?: string | null;
  confident: boolean;
  label: string;
};

/** Strategy research.
 *
 * Every figure in `StrategyMetrics` is computed by our backtest engine over
 * stored history. No model produces a number here: the assistant can only
 * propose a rule set or describe a result that was already measured.
 */
export type StrategyFilters = {
  collection_id?: number | null;
  marketplaces: string[];
  min_price_ton?: number | null;
  max_price_ton?: number | null;
  min_discount_percent?: number | null;
  max_rarity_percent?: number | null;
  max_hours_to_sell?: number | null;
  min_closed_listings?: number | null;
};
export type Strategy = {
  name: string;
  filters: StrategyFilters;
  hold_hours: number;
  exit_at: "floor" | "median";
  require_sold: boolean;
};
export type StrategyMetrics = {
  trades: number;
  wins: number;
  win_rate?: number | null;
  median_profit_percent?: number | null;
  mean_profit_percent?: number | null;
  total_profit_ton: number;
  median_hold_hours?: number | null;
  best_percent?: number | null;
  worst_percent?: number | null;
  /** Entries whose exit falls past the end of our history. Not wins, not losses. */
  unresolved: number;
};
export type SimulatedTrade = {
  gift_id: number;
  gift_name?: string | null;
  marketplace: string;
  entry_at: string;
  entry_price: number;
  exit_price: number;
  profit_ton: number;
  profit_percent: number;
  sold: boolean;
};
export type Backtest = {
  status: string;
  reason?: string | null;
  strategy: Strategy;
  summary: string;
  conditions: string[];
  window_days: number;
  history_days: number;
  overall: StrategyMetrics;
  in_sample: StrategyMetrics;
  out_of_sample: StrategyMetrics;
  /** True only when the half the rule was not selected on also pays. */
  holds_up: boolean;
  examples: SimulatedTrade[];
};
export type DiscoveryResult = {
  status: string;
  reason?: string | null;
  tested: number;
  window_days: number;
  history_days: number;
  results: Backtest[];
};
export type SavedStrategy = {
  id: number;
  name: string;
  source: string;
  summary: string;
  conditions: string[];
  definition: Strategy;
  created_at: string;
  last_trades?: number | null;
  last_median_percent?: number | null;
  last_out_of_sample_percent?: number | null;
  last_holds_up?: boolean | null;
};

/** Dashboard numbers and spreads, both served from stored rows. */
export const getOverview = () => request<OverviewStats>("/overview");
export const getArbitrage = (minPercent = 0, limit = 50) =>
  request<ArbitrageList>(`/arbitrage?min_profit_percent=${minPercent}&limit=${limit}`);
export const getFees = () => request<FeeSchedule>("/fees");
export const getMe = () => request<User>("/auth/me");
export async function authenticateTelegram(): Promise<User | null> { const initData = telegramInitData(); if (!initData) return null; const result = await request<{ access_token: string; user: User }>("/auth/telegram", { method: "POST", body: JSON.stringify({ init_data: initData }) }); setToken(result.access_token); return result.user; }

/** Saved gifts as full cards. Ids alone were never enough to render a row. */
export const getWatchlist = () => request<WatchlistPage>("/watchlist");
export const addToWatchlist = (giftId: number) => request(`/watchlist/${giftId}`, { method: "POST" });
export const removeFromWatchlist = (giftId: number) => request(`/watchlist/${giftId}`, { method: "DELETE" });

export const getSourceStatus = () => request<SourceStatusList>("/sources/status");

/** Sniper: standing orders for the fast loop. */
export const getWatches = () => request<{ items: SniperWatch[] }>("/sniper/watches");
export const createWatch = (payload: {
  gift_name?: string;
  model?: string;
  max_price_ton?: string;
  min_discount_percent?: string;
  marketplace?: string;
}) => request<SniperWatch>("/sniper/watches", { method: "POST", body: JSON.stringify(payload) });
export const toggleWatch = (watchId: number, isActive: boolean) =>
  request<SniperWatch>(`/sniper/watches/${watchId}?is_active=${isActive}`, { method: "PATCH" });
export const deleteWatch = (watchId: number) => request(`/sniper/watches/${watchId}`, { method: "DELETE" });
export const getGiftLiquidity = (giftId: number) =>
  request<GiftLiquidity>(`/sniper/gifts/${giftId}/liquidity`);

/** How jumpy the floor is. Fourteen days is long enough to have a shape and
 *  short enough that last month's regime does not pollute today's answer. */
export const getGiftVolatility = (giftId: number, windowDays = 14) =>
  request<GiftVolatility>(`/volatility/gifts/${giftId}?window_days=${windowDays}`);

/** Research. `discover` and `backtest` never touch a model; `propose` uses one
 *  to pick thresholds and `explain` to put a measured result into words. */
export const discoverStrategies = (windowDays = 30, collectionId?: number) => {
  const params = new URLSearchParams({ window_days: String(windowDays) });
  if (collectionId) params.set("collection_id", String(collectionId));
  return request<DiscoveryResult>(`/research/discover?${params.toString()}`, { method: "POST" });
};
export const backtestStrategy = (strategy: Strategy, windowDays = 30) =>
  request<Backtest>("/research/backtest", {
    method: "POST",
    body: JSON.stringify({ strategy, window_days: windowDays }),
  });
export const proposeStrategy = (question: string, windowDays = 30) =>
  request<{ strategy: Strategy; backtest: Backtest }>("/research/propose", {
    method: "POST",
    body: JSON.stringify({ request: question, window_days: windowDays }),
  });
export const explainStrategy = (strategy: Strategy, windowDays = 30) =>
  request<{ explanation: string; model: string; backtest: Backtest }>("/research/explain", {
    method: "POST",
    body: JSON.stringify({ strategy, window_days: windowDays }),
  });
export const getSavedStrategies = () => request<SavedStrategy[]>("/research/strategies");
export const saveStrategy = (strategy: Strategy, source: string, windowDays = 30) =>
  request<SavedStrategy>(`/research/strategies?window_days=${windowDays}`, {
    method: "POST",
    body: JSON.stringify({ strategy, source }),
  });
export const deleteStrategy = (strategyId: number) =>
  request(`/research/strategies/${strategyId}`, { method: "DELETE" });
/** Turn a researched rule into a live watch. `dropped` names every condition
 *  the fast loop cannot enforce, because a looser armed rule is a trap. */
export const armStrategy = (strategyId: number) =>
  request<{ watch_id: number; dropped: string[] }>(`/research/strategies/${strategyId}/arm`, {
    method: "POST",
  });

/** Selling: the same market, seen from behind your own listings. */
export const getMyListings = () => request<SellingPage>("/selling/listings");
export const getSellerIdentities = () => request<{ items: SellerIdentity[] }>("/selling/identities");
export const addSellerIdentity = (seller: string, marketplace?: string) =>
  request<SellerIdentity>("/selling/identities", {
    method: "POST",
    body: JSON.stringify({ seller, ...(marketplace ? { marketplace } : {}) }),
  });
export const removeSellerIdentity = (identityId: number) =>
  request(`/selling/identities/${identityId}`, { method: "DELETE" });

/** Positions: the user's own book, priced against the live market. */
export const getPositions = (includeClosed = true) =>
  request<PositionList>(`/positions?include_closed=${includeClosed}`);
export const openPosition = (payload: {
  gift_id: number;
  buy_price_ton: string;
  buy_marketplace?: string;
  opened_at?: string;
  note?: string;
}) => request<PositionCard>("/positions", { method: "POST", body: JSON.stringify(payload) });
export const updatePosition = (
  positionId: number,
  payload: {
    buy_price_ton?: string;
    buy_marketplace?: string;
    opened_at?: string;
    sell_price_ton?: string;
    sell_marketplace?: string;
    closed_at?: string;
    note?: string;
    reopen?: boolean;
  }
) => request<PositionCard>(`/positions/${positionId}`, { method: "PATCH", body: JSON.stringify(payload) });
/** Booking an exit needs the price it actually sold for, never a guess. */
export const closePosition = (positionId: number, sellPriceTon: string, sellMarketplace?: string) =>
  updatePosition(positionId, {
    sell_price_ton: sellPriceTon,
    ...(sellMarketplace ? { sell_marketplace: sellMarketplace } : {}),
  });
/** Undo a mistyped exit: the lot goes back on the open book, entry intact. */
export const reopenPosition = (positionId: number) => updatePosition(positionId, { reopen: true });
export const deletePosition = (positionId: number) => request(`/positions/${positionId}`, { method: "DELETE" });

export const getWallets = () => request<{ items: WalletItem[] }>("/portfolio/wallets"); export const addWallet = (address: string, label?: string) => request<WalletItem>("/portfolio/wallets", { method: "POST", body: JSON.stringify({ address, label }) }); export const removeWallet = (walletId: number) => request(`/portfolio/wallets/${walletId}`, { method: "DELETE" });
export const getPortfolioOverview = () => request<PortfolioOverview>("/portfolio/overview"); export const getPortfolioHistory = () => request<{ data_mode: string; points: PortfolioPoint[] }>("/portfolio/history");
export const getAlertRules = () => request<{ items: AlertRule[] }>("/alerts/rules");
export const createAlertRule = (payload: { gift_id?: number; rule_type: string; threshold: string }) => request<AlertRule>("/alerts/rules", { method: "POST", body: JSON.stringify(payload) });
export const updateAlertRule = (ruleId: number, is_active: boolean) => request<Pick<AlertRule, "id" | "is_active">>(`/alerts/rules/${ruleId}`, { method: "PATCH", body: JSON.stringify({ is_active }) });
export const deleteAlertRule = (ruleId: number) => request(`/alerts/rules/${ruleId}`, { method: "DELETE" });
export const getAlertEvents = () => request<{ items: AlertEvent[] }>("/alerts/events");
export const markAlertRead = (eventId: number) => request(`/alerts/events/${eventId}/read`, { method: "PATCH" });

// AI analyst. The key stays on the server, the browser only talks to us.
export const getAiStatus = () => request<AiStatus>("/ai/status");
export const askAssistant = (question: string, giftId?: number) =>
  request<AiAnswer>("/ai/ask", {
    method: "POST",
    body: JSON.stringify({ question, ...(giftId ? { gift_id: giftId } : {}) }),
  });
export const getGiftVerdict = (giftId: number) => request<AiAnswer>(`/ai/gifts/${giftId}/verdict`);
// Older call sites use these names.
export const askAi = askAssistant;
export const getAiVerdict = getGiftVerdict;

/** Live market changes. `afterId` makes each poll ask only for what is new. */
export const getEvents = (options: { afterId?: number; limit?: number; eventType?: string; giftId?: number } = {}) => {
  const params = new URLSearchParams();
  params.set("limit", String(options.limit ?? 40));
  if (options.afterId !== undefined) params.set("after_id", String(options.afterId));
  if (options.eventType) params.set("event_type", options.eventType);
  if (options.giftId) params.set("gift_id", String(options.giftId));
  return request<MarketEventFeed>(`/events?${params.toString()}`);
};

export const getCollections = (options: { page?: number; pageSize?: number; search?: string } = {}) => {
  const params = new URLSearchParams();
  params.set("page", String(options.page ?? 1));
  params.set("page_size", String(options.pageSize ?? 48));
  if (options.search) params.set("search", options.search);
  return request<CollectionPage>(`/collections?${params.toString()}`);
};
export const getCollection = (collectionId: number) => request<CollectionCard>(`/collections/${collectionId}`);

export const getDeals = (options: { minDiscountPercent?: string; collectionId?: number; limit?: number } = {}) => {
  const params = new URLSearchParams();
  params.set("min_discount_percent", options.minDiscountPercent ?? "10");
  params.set("limit", String(options.limit ?? 50));
  if (options.collectionId) params.set("collection_id", String(options.collectionId));
  return request<DealList>(`/deals?${params.toString()}`);
};

export const getMovers = (hours = 24, limit = 5) =>
  request<MoversResponse>(`/movers?hours=${hours}&limit=${limit}`);

export const getGifts = (
  options: {
    page?: number;
    pageSize?: number;
    search?: string;
    marketplace?: string;
    collectionId?: number;
    model?: string;
    backdrop?: string;
    symbol?: string;
    rarityTier?: RarityTier | "";
    minPrice?: string;
    maxPrice?: string;
    dealsOnly?: boolean;
    sort?: GiftSort;
  } = {}
) => {
  const params = new URLSearchParams();
  params.set("page", String(options.page ?? 1));
  params.set("page_size", String(options.pageSize ?? 24));
  params.set("sort", options.sort ?? "recent");
  if (options.search) params.set("search", options.search);
  if (options.marketplace) params.set("marketplace", options.marketplace);
  if (options.collectionId) params.set("collection_id", String(options.collectionId));
  if (options.model) params.set("model", options.model);
  if (options.backdrop) params.set("backdrop", options.backdrop);
  if (options.symbol) params.set("symbol", options.symbol);
  if (options.rarityTier) params.set("rarity_tier", options.rarityTier);
  if (options.minPrice) params.set("min_price", options.minPrice);
  if (options.maxPrice) params.set("max_price", options.maxPrice);
  if (options.dealsOnly) params.set("deals_only", "true");
  return request<GiftPage>(`/gifts?${params.toString()}`);
};
export const getGiftModels = (collectionId?: number) =>
  request<string[]>(`/gifts/models${collectionId ? `?collection_id=${collectionId}` : ""}`);
/** Traits with their scarcity and the floor each one trades at. */
export const getGiftAttributes = (collectionId?: number) =>
  request<AttributeGroups>(`/gifts/attributes${collectionId ? `?collection_id=${collectionId}` : ""}`);
export const getGift = (giftId: number) => request<GiftDetail>(`/gifts/${giftId}`);
export const getGiftHistory = (giftId: number, marketplace?: string) =>
  request<GiftHistory>(`/gifts/${giftId}/history${marketplace ? `?marketplace=${encodeURIComponent(marketplace)}` : ""}`);
export const getGiftTrades = (giftId: number, limit = 20) =>
  request<GiftTrades>(`/gifts/${giftId}/trades?limit=${limit}`);
