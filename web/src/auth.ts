export type User = { id: number; telegram_id: number; username?: string | null; first_name?: string | null; last_name?: string | null };

const TOKEN_KEY = "gift-trader.access-token";
export const getToken = () => localStorage.getItem(TOKEN_KEY);
export const setToken = (token: string) => localStorage.setItem(TOKEN_KEY, token);
export const clearToken = () => localStorage.removeItem(TOKEN_KEY);

export function telegramInitData(): string | null {
  const telegram = (window as Window & { Telegram?: { WebApp?: { initData?: string } } }).Telegram;
  return telegram?.WebApp?.initData || null;
}
