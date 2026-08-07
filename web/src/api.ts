import type { ArbitrageResponse, MarketResponse } from "./types";
import { clearToken, getToken, setToken, telegramInitData, type User } from "./auth";
const base = (import.meta.env.VITE_API_URL ?? "http://localhost:8000/api").replace(/\/$/, "");
async function request<T>(path: string, init: RequestInit = {}): Promise<T> { const headers = new Headers(init.headers); headers.set("Accept", "application/json"); if (init.body) headers.set("Content-Type", "application/json"); const token = getToken(); if (token) headers.set("Authorization", `Bearer ${token}`); const response = await fetch(`${base}${path}`, { ...init, headers }); if (response.status === 401) { clearToken(); throw new Error("Authentication required"); } if (!response.ok) throw new Error(`API ${response.status}`); if (response.status === 204) return undefined as T; return response.json() as Promise<T>; }
export const getMarkets = (collections: string[] = []) => request<MarketResponse>(`/markets/snapshots${collections.length ? `?${collections.map(c => `collection=${encodeURIComponent(c)}`).join("&")}` : ""}`);
export const getArbitrage = (minimum = 0) => request<ArbitrageResponse>(`/arbitrage?min_profit_percent=${minimum}`);
export const getMe = () => request<User>("/auth/me");
export async function authenticateTelegram(): Promise<User | null> { const initData = telegramInitData(); if (!initData) return null; const result = await request<{ access_token: string; user: User }>("/auth/telegram", { method: "POST", body: JSON.stringify({ init_data: initData }) }); setToken(result.access_token); return result.user; }
export const getWatchlist = () => request<{ items: { id: number; gift_id: number; created_at: string }[] }>("/watchlist");
export const addToWatchlist = (giftId: number) => request(`/watchlist/${giftId}`, { method: "POST" });
export const removeFromWatchlist = (giftId: number) => request(`/watchlist/${giftId}`, { method: "DELETE" });
export const getWallets = () => request<{ items: { id: number; address: string; label?: string | null }[] }>("/portfolio/wallets");
export const addWallet = (address: string, label?: string) => request("/portfolio/wallets", { method: "POST", body: JSON.stringify({ address, label }) );
export const removeWallet = (walletId: number) => request(`/portfolio/wallets/${walletId}`, { method: "DELETE" });
export const getPortfolioOverview = () => request<{ data_mode: string; total_assets: number; estimated_nft_value_ton: string; wallets: { wallet_id: number; address: string; label?: string | null; ton_balance: string; nfts: { nft_address: string; name?: string; estimated_price_ton?: string | null }[] }[]; unavailable: { wallet_id: number; address: string; error: string }[] }>("/portfolio/overview");
export const getAlertRules = () => request<{ items: { id: number; gift_id?: number | null; rule_type: string; threshold: string; is_active: boolean }[] }>("/alerts/rules");
export const createAlertRule = (payload: { gift_id?: number; rule_type: string; threshold: string }) => request("/alerts/rules", { method: "POST", body: JSON.stringify(payload) });
export const deleteAlertRule = (ruleId: number) => request(`/alerts/rules/${ruleId}`, { method: "DELETE" });
export const getAlertEvents = () => request<{ items: { id: number; message: string; is_read: boolean; created_at: string }[] }>("/alerts/events");
