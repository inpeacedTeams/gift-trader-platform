/** Money formatting shared by every surface.
 *
 * Prices must never invent precision: 90 TON stays "90 TON", not "90.000 TON".
 * Precision adapts to magnitude so cheap gifts keep their meaningful digits.
 */

type Numeric = string | number | null | undefined;

function toNumber(value: Numeric): number | null {
  if (value === null || value === undefined || value === "") return null;
  const amount = Number(value);
  return Number.isFinite(amount) ? amount : null;
}

function decimalsFor(magnitude: number): number {
  if (magnitude >= 1000) return 0;
  if (magnitude >= 1) return 2;
  if (magnitude >= 0.01) return 4;
  return 6;
}

/** Format a TON amount, trimming trailing zeros. Returns "--" when unknown. */
export function formatTon(value: Numeric, options: { suffix?: boolean } = {}): string {
  const amount = toNumber(value);
  if (amount === null) return "--";
  const text = new Intl.NumberFormat("en-US", {
    maximumFractionDigits: decimalsFor(Math.abs(amount)),
  }).format(amount);
  return options.suffix === false ? text : `${text} TON`;
}

/** Signed TON amount for changes and profit: "+1.5 TON", "-0.25 TON". */
export function formatTonDelta(value: Numeric): string {
  const amount = toNumber(value);
  if (amount === null) return "--";
  return `${amount > 0 ? "+" : ""}${formatTon(amount)}`;
}

/** Signed percentage without padded zeros: "+12.5%", "-3%". */
export function formatPercent(value: Numeric): string | null {
  const amount = toNumber(value);
  if (amount === null) return null;
  const text = new Intl.NumberFormat("en-US", {
    maximumFractionDigits: Math.abs(amount) >= 10 ? 1 : 2,
  }).format(amount);
  return `${amount > 0 ? "+" : ""}${text}%`;
}

/** Unsigned rarity share: "12%", "1.5%", "0.28%".
 *
 * Rarity is not a change, so it never gets a sign, and the scarce end of the
 * scale keeps its digits: rounding 0.28% down to 0% would erase the point.
 */
export function formatRarity(value: Numeric): string | null {
  const amount = toNumber(value);
  if (amount === null || amount <= 0) return null;
  const text = new Intl.NumberFormat("en-US", {
    maximumFractionDigits: amount >= 10 ? 0 : amount >= 1 ? 1 : 2,
  }).format(amount);
  return `${text}%`;
}

/** Whole counts with separators: 1,248. */
export function formatCount(value: Numeric): string {
  const amount = toNumber(value);
  if (amount === null) return "0";
  return new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 }).format(amount);
}

/** Compact relative time for freshness labels. */
export function formatAgo(value: string): string {
  const minutes = Math.round((Date.now() - new Date(value).getTime()) / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  return hours < 24 ? `${hours}h ago` : `${Math.round(hours / 24)}d ago`;
}
