import { useEffect, useState } from "react";
import { ArrowLeft, ExternalLink } from "lucide-react";
import { getGift, getGiftHistory } from "../api";
import type { GiftDetail, PricePoint } from "../types";
import { ErrorState, LoadingState } from "../components/State";
import { GiftImage } from "../components/GiftImage";
import { PriceChart } from "../components/PriceChart";
import "../gifts.css";

function price(value?: string | null): string {
  return value ? `${Number(value).toFixed(3)} TON` : "--";
}

function ago(value: string): string {
  const minutes = Math.round((Date.now() - new Date(value).getTime()) / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  return hours < 24 ? `${hours}h ago` : `${Math.round(hours / 24)}d ago`;
}

export function GiftPage({ giftId, onBack }: { giftId: number; onBack: () => void }) {
  const [gift, setGift] = useState<GiftDetail | null>(null);
  const [points, setPoints] = useState<PricePoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      const [detail, history] = await Promise.all([getGift(giftId), getGiftHistory(giftId)]);
      setGift(detail);
      setPoints(history.points);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Gift unavailable");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, [giftId]);

  if (loading) return <LoadingState />;
  if (error || !gift) return <ErrorState detail={error ?? "Gift not found"} retry={() => void load()} />;

  const change = gift.change_percent === null || gift.change_percent === undefined ? null : Number(gift.change_percent);
  const title = gift.name ?? gift.canonical_id.slice(0, 18);
  const active = gift.listings.filter(listing => listing.active);

  return (
    <section className="page-section">
      <button className="back-btn" onClick={onBack}>
        <ArrowLeft size={15} /> Back to catalog
      </button>
      <div className="gift-hero">
        <GiftImage src={gift.image_url} alt={title} className="large" />
        <div className="gift-hero-copy">
          <p className="eyebrow">{gift.sources.join(" · ") || "no active source"}</p>
          <h2>
            {title}
            {gift.gift_number ? <em> #{gift.gift_number}</em> : null}
          </h2>
          <p className="muted-copy">{gift.model ? `Model ${gift.model}` : "Model not resolved yet"}</p>
          <div className="gift-hero-price">
            <strong>{price(gift.floor_ton)}</strong>
            {change !== null && (
              <span className={change >= 0 ? "trend-up" : "trend-down"}>
                {change >= 0 ? "+" : ""}
                {change.toFixed(2)}% · 24h
              </span>
            )}
          </div>
        </div>
      </div>
      <div className="metric-grid">
        <div className="metric green">
          <span>Floor</span>
          <strong>{price(gift.floor_ton)}</strong>
          <small>cheapest active listing</small>
        </div>
        <div className="metric blue">
          <span>Median</span>
          <strong>{price(gift.median_ton)}</strong>
          <small>across tracked listings</small>
        </div>
        <div className="metric violet">
          <span>Depth</span>
          <strong>{gift.listings_count}</strong>
          <small>{active.length} currently active</small>
        </div>
      </div>
      <div className="valuation-panel">
        <div className="section-head">
          <div>
            <p className="eyebrow">PRICE HISTORY</p>
            <h3>Floor and median</h3>
          </div>
          <span className="fresh">{points.length} snapshots</span>
        </div>
        <PriceChart points={points} />
      </div>
      <div className="section-head">
        <div>
          <p className="eyebrow">ORDER BOOK</p>
          <h3>Live listings</h3>
        </div>
        <span className="fresh">{active.length} active</span>
      </div>
      <div className="table-card">
        {gift.listings.map(listing => (
          <div className={listing.active ? "listing-row" : "listing-row stale"} key={listing.id}>
            <div className="gift-cell">
              <div className="gift-icon">{listing.marketplace.slice(0, 1).toUpperCase()}</div>
              <div>
                <strong>{listing.marketplace}</strong>
                <small>seen {ago(listing.last_seen_at)}</small>
              </div>
            </div>
            <div>
              <b>{Number(listing.price_ton).toFixed(3)} TON</b>
              <small>{listing.active ? "active" : "gone"}</small>
            </div>
            <div className="listing-action">
              {listing.url ? (
                <a className="outline-btn" href={listing.url} target="_blank" rel="noreferrer">
                  Open <ExternalLink size={13} />
                </a>
              ) : (
                <span className="tag-unvalued">no link</span>
              )}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
