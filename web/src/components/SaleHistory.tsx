import { useEffect, useState } from "react";
import { Receipt } from "lucide-react";
import { getGiftTrades } from "../api";
import type { GiftTrades } from "../types";
import { formatAgo, formatCount, formatTon } from "../format";
import "./sale-history.css";

/** Prices the market actually paid.
 *
 * Listings are asking prices and can sit unsold forever, so a sold price is
 * the stronger valuation signal whenever we have one.
 */
export function SaleHistory({ giftId }: { giftId: number }) {
  const [data, setData] = useState<GiftTrades | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    void getGiftTrades(giftId)
      .then(result => {
        if (!cancelled) setData(result);
      })
      .catch(() => {
        if (!cancelled) setData(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [giftId]);

  if (loading || !data) return null;

  const { stats, items } = data;

  return (
    <div className="sales-panel">
      <div className="section-head">
        <div>
          <p className="eyebrow">SOLD PRICES</p>
          <h3>Recent sales</h3>
        </div>
        <span className="fresh">
          {formatCount(stats.sales_count)} in {stats.window_days}d
        </span>
      </div>
      {items.length ? (
        <>
          <div className="sales-stats">
            <div>
              <span>Median sold</span>
              <b>{formatTon(stats.median_ton)}</b>
            </div>
            <div>
              <span>Range</span>
              <b>
                {formatTon(stats.lowest_ton, { suffix: false })} – {formatTon(stats.highest_ton)}
              </b>
            </div>
            <div>
              <span>Volume</span>
              <b>{formatTon(stats.volume_ton)}</b>
            </div>
          </div>
          <div className="sales-list">
            {items.map(trade => (
              <div className="sale-row" key={trade.id}>
                <Receipt size={13} />
                <b>{formatTon(trade.price_ton)}</b>
                <span>{trade.marketplace}</span>
                <small>{formatAgo(trade.traded_at)}</small>
              </div>
            ))}
          </div>
        </>
      ) : (
        <p className="muted-copy">
          No confirmed sales stored yet. Sale history needs TONNEL_AUTH_DATA and a completed trade sync.
        </p>
      )}
    </div>
  );
}
