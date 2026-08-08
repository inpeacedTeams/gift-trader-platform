import type { ArbitrageList, CollectionCard, CollectionPage, DealList, GiftDetail, GiftHistory, GiftLiquidity, GiftPage, GiftTrades, MarketEventFeed, MoversResponse, OverviewStats, SourceStatusList, WatchlistPage } from "./types";
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

/** Dashboard numbers and spreads, both served from stored rows. */
export const getOverview = () => request<OverviewStats>("/overview");
export const getArbitrage = (minPercent = 0, limit = 50) =>
  request<ArbitrageList>(`/arbitrage?min_profit_percent=${minPercent}&limit=${limit}`);
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
  if (options.minPrice) params.set("min_price", options.minPrice);
  if (options.maxPrice) params.set("max_price", options.maxPrice);
  if (options.dealsOnly) params.set("deals_only", "true");
  return request<GiftPage>(`/gifts?${params.toString()}`);
};
export const getGiftModels = (collectionId?: number) =>
  request<string[]>(`/gifts/models${collectionId ? `?collection_id=${collectionId}` : ""}`);
export const getGift = (giftId: number) => request<GiftDetail>(`/gifts/${giftId}`);
export const getGiftHistory = (giftId: number, marketplace?: string) =>
  request<GiftHistory>(`/gifts/${giftId}/history${marketplace ? `?marketplace=${encodeURIComponent(marketplace)}` : ""}`);
export const getGiftTrades = (giftId: number, limit = 20) =>
  request<GiftTrades>(`/gifts/${giftId}/trades?limit=${limit}`);
