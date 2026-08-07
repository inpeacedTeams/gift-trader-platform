import type { ArbitrageResponse, MarketResponse } from "./types";

const base = (import.meta.env.VITE_API_URL ?? "http://localhost:8000/api").replace(/\/$/, "");

async function get<T>(path: string): Promise<T> {
  const response = await fetch(`${base}${path}`, { headers: { Accept: "application/json" } });
  if (!response.ok) throw new Error(`API ${response.status}`);
  return response.json() as Promise<T>;
}

export const getMarkets = () => get<MarketResponse>("/markets/snapshots");
export const getArbitrage = () => get<ArbitrageResponse>("/arbitrage");
