import type { ArbitrageResponse, CollectionCard, CollectionPage, GiftDetail, GiftHistory, GiftPage, MarketResponse } from "./types";
import { clearToken, getToken, setToken, telegramInitData, type User } from "./auth";
export type { User } from "./auth";
const base = (import.meta.env.VITE_API_URL ?? "/api").replace(/\/$/, "");
async function request<T>(path: string, init: RequestInit = {}): Promise<T> { const headers = new Headers(init.headers); headers.set("Accept", "application/json"); if (init.body) headers.set("Content-Type", "application/json"); const token = getToken(); if (token) headers.set("Authorization", `Bearer ${token}`); const response = await fetch(`${base}${path}`, { ...init, headers }); if (response.status === 401) { clearToken(); throw new Error("Authentication required"); } if (!response.ok) throw new Error(`API ${response.status}`); if (response.status === 204) return undefined as T; return response.json() as Promise<T>; }
export type WalletItem = { id: number; address: string; label?: string | null; created_at?: string };
export type PortfolioNft = { nft_address: string; name?: string | null; image_url?: string | null; estimated_price_ton?: string | null; valuation_source: string; valuation_confidence?: string | null };
export type PortfolioWallet = { wallet_id: number; address: string; label?: string | null; ton_balance: string; nfts: PortfolioNft[] };
export type PortfolioOverview = { data_mode: string; total_assets: number; valued_assets: number; unvalued_assets: number; estimated_nft_value_ton: string; wallets: PortfolioWallet[]; unavailable: { wallet_id: number; address: string; error: string }[] };
export type PortfolioPoint = { observed_at: string; total_ton: string; ton_balance: string; nft_value_ton: string; asset_count: number };
export type AlertRule = { id: number; gift_id?: number | null; rule_type: string; threshold: string; is_active: boolean };
export type AlertEvent = { id: number; message: string; is_read: boolean; created_at: string };
export type GiftSort = "recent" | "floor_asc" | "floor_desc" | "depth" | "change_desc" | "change_asc" | "deal_desc";
export const getMarkets = (collections: string[] = []) => request<MarketResponse>(`/markets/snapshots${collections.length ? `?${collections.map(c => `collection=${encodeURIComponent(c)}`).join("&")}` : ""}`); export const getArbitrage = (minimum = 0) => request<ArbitrageResponse>(`/arbitrage?min_profit_percent=${minimum}`); export const getMe = () => request<User>("/auth/me");
export async function authenticateTelegram(): Promise<User | null> { const initData = telegramInitData(); if (!initData) return null; const result = await request<{ access_token: string; user: User }>("/auth/telegram", { method: "POST", body: JSON.stringify({ init_data: initData }) }); setToken(result.access_token); return result.user; }
export const getWatchlist = () => request<{ items: { id: number; gift_id: number; created_at: string }[] }>("/watchlist"); export const addToWatchlist = (giftId: number) => request(`/watchlist/${giftId}`, { method: "POST" }); export const removeFromWatchlist = (giftId: number) => request(`/watchlist/${giftId}`, { method: "DELETE" });
export const getWallets = () => request<{ items: WalletItem[] }>("/portfolio/wallets"); export const addWallet = (address: string, label?: string) => request<WalletItem>("/portfolio/wallets", { method: "POST", body: JSON.stringify({ address, label }) }); export const removeWallet = (walletId: number) => request(`/portfolio/wallets/${walletId}`, { method: "DELETE" });
export const getPortfolioOverview = () => request<PortfolioOverview>("/portfolio/overview"); export const getPortfolioHistory = () => request<{ data_mode: string; points: PortfolioPoint[] }>("/portfolio/history");
export const getAlertRules = () => request<{ items: AlertRule[] }>("/alerts/rules"); export const createAlertRule = (payload: { gift_id?: number; rule_type: string; threshold: string }) => request<AlertRule>("/alerts/rules", { method: "POST", body: JSON.stringify(payload) }); export const updateAlertRule = (ruleId: number, is_active: boolean) => request<Pick<AlertRule, "id" | "is_active">>(`/alerts/rules/${ruleId}`, { method: "PATCH", body: JSON.stringify({ is_active }) }); export const deleteAlertRule = (ruleId: number) => request(`/alerts/rules/${ruleId}`, { method: "DELETE" }); export const getAlertEvents = () => request<{ items: AlertEvent[] }>("/alerts/events"); export const markAlertRead = (eventId: number) => request(`/alerts/events/${eventId}/read`, { method: "PATCH" });

export const getCollections = (options: { page?: number; pageSize?: number; search?: string } = {}) => {
  const params = new URLSearchParams();
  params.set("page", String(options.page ?? 1));
  params.set("page_size", String(options.pageSize ?? 48));
  if (options.search) params.set("search", options.search);
  return request<CollectionPage>(`/collections?${params.toString()}`);
};
export const getCollection = (collectionId: number) => request<CollectionCard>(`/collections/${collectionId}`);

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
export const triggerMarketSync = () => request<{ status: string; job: string }>("/jobs/market-sync", { method: "POST" });
