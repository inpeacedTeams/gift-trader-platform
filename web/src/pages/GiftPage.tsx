import { useEffect, useState } from "react";
import { ArrowLeft, ExternalLink, Layers, Tag } from "lucide-react";
import { getGift, getGiftHistory } from "../api";
import type { GiftDetail, PricePoint } from "../types";
import { ErrorState, LoadingState } from "../components/State";
import { FlipCalc } from "../components/FlipCalc";
import { GiftImage } from "../components/GiftImage";
import { Liquidity } from "../components/Liquidity";
import { LogBuy } from "../components/LogBuy";
import { PriceChart } from "../components/PriceChart";
import { QuickAlert } from "../components/QuickAlert";
import { RarityBadge, TraitGrid } from "../components/Rarity";
import { SaleHistory } from "../components/SaleHistory";
import { Verdict } from "../components/Verdict";
import { Volatility } from "../components/Volatility";
import { formatAgo, formatCount, formatPercent, formatTon } from "../format";
import "../gifts.css";
import "../catalog-deals.css";

type Props = {
  giftId: number;
  onBack: () => void;
  authenticated?: boolean;
  /** Passed down so the page does not re-ask for AI status on every open. */
  aiEnabled?: boolean;
  onOpenCollection?: (collection: { id: number; name?: string | null; chain_address: string }) => void;
};

export function GiftPage({ giftId, onBack, authenticated = false, aiEnabled, onOpenCollection }: Props) {
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

  const change = formatPercent(gift.change_percent);
  const rising = Number(gift.change_percent ?? 0) >= 0;
  const deal = gift.deal_percent === null || gift.deal_percent === undefined ? null : Number(gift.deal_percent);
  const title = gift.name ?? gift.canonical_id.slice(0, 18);
  const active = gift.listings.filter(listing => listing.active);
  // Where a buy would actually happen, so the purchase log opens on the right venue.
  const cheapest = active.length
    ? active.reduce((best, listing) => (Number(listing.price_ton) < Number(best.price_ton) ? listing : best))
    : null;

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
          {gift.collection_id && gift.collection_name && onOpenCollection && (
            <button
              className="collection-link"
              onClick={() =>
                onOpenCollection({ id: gift.collection_id!, name: gift.collection_name, chain_address: "" })
              }
            >
              <Layers size={13} /> {gift.collection_name}
            </button>
          )}
          <div className="gift-hero-price">
            <strong>{formatTon(gift.floor_ton)}</strong>
            {change && <span className={rising ? "trend-up" : "trend-down"}>{change} · 24h</span>}
            <RarityBadge gift={gift} inline />
            {deal !== null && deal >= 1 && (
              <span className="deal-badge inline">
                <Tag size={11} /> {deal.toFixed(0)}% under its peer median
              </span>
            )}
          </div>
          <LogBuy
            giftId={gift.id}
            floorTon={gift.floor_ton}
            venue={cheapest ? cheapest.marketplace : gift.best_marketplace}
            authenticated={authenticated}
          />
        </div>
      </div>
      <TraitGrid gift={gift} />
      <Verdict giftId={gift.id} authenticated={authenticated} enabled={aiEnabled} />
      <Liquidity giftId={gift.id} />
      <Volatility giftId={gift.id} />
      <FlipCalc floorTon={gift.floor_ton} medianTon={gift.median_ton} venues={gift.sources} />
      <QuickAlert giftId={gift.id} floorTon={gift.floor_ton} authenticated={authenticated} />
      <div className="metric-grid">
        <div className="metric green">
          <span>Floor</span>
          <strong>{formatTon(gift.floor_ton)}</strong>
          <small>cheapest active listing</small>
        </div>
        <div className="metric blue">
          <span>Median</span>
          <strong>{formatTon(gift.median_ton)}</strong>
          <small>across tracked listings</small>
        </div>
        <div className="metric violet">
          <span>Depth</span>
          <strong>{formatCount(gift.listings_count)}</strong>
          <small>{formatCount(active.length)} currently active</small>
        </div>
      </div>
      <SaleHistory giftId={gift.id} />
      <div className="valuation-panel">
        <div className="section-head">
          <div>
            <p className="eyebrow">PRICE HISTORY</p>
            <h3>Floor and median</h3>
          </div>
          <span className="fresh">{formatCount(points.length)} snapshots</span>
        </div>
        <PriceChart points={points} />
      </div>
      <div className="section-head">
        <div>
          <p className="eyebrow">ORDER BOOK</p>
          <h3>Live listings</h3>
        </div>
        <span className="fresh">{formatCount(active.length)} active</span>
      </div>
      <div className="table-card">
        {gift.listings.map(listing => (
          <div className={listing.active ? "listing-row" : "listing-row stale"} key={listing.id}>
            <div className="gift-cell">
              <div className="gift-icon">{listing.marketplace.slice(0, 1).toUpperCase()}</div>
              <div>
                <strong>{listing.marketplace}</strong>
                <small>seen {formatAgo(listing.last_seen_at)}</small>
              </div>
            </div>
            <div>
              <b>{formatTon(listing.price_ton)}</b>
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
