import { useEffect, useState } from "react";
import { ExternalLink, TrendingDown } from "lucide-react";
import { getDeals } from "../api";
import type { Deal } from "../types";
import { EmptyState, ErrorState, LoadingState } from "../components/State";
import { GiftImage } from "../components/GiftImage";
import { Select } from "../components/Select";
import { formatCount, formatPercent, formatTon } from "../format";
import "../gifts.css";
import "../deals.css";

const DISCOUNT_OPTIONS = [
  { value: "5", label: "5% below median" },
  { value: "10", label: "10% below median" },
  { value: "20", label: "20% below median" },
  { value: "35", label: "35% below median" },
];

/** Listings cheaper than the median of the same model in the same collection. */
export function Deals({ onOpen }: { onOpen: (giftId: number) => void }) {
  const [items, setItems] = useState<Deal[]>([]);
  const [discount, setDiscount] = useState("10");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      setItems((await getDeals({ minDiscountPercent: discount })).items);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Deals unavailable");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, [discount]);

  return (
    <section className="page-section">
      <div className="section-head">
        <div>
          <p className="eyebrow">UNDERVALUED</p>
          <h2>Deals</h2>
        </div>
        <span className="fresh">
          <i /> {formatCount(items.length)} below median
        </span>
      </div>
      <div className="deals-intro">
        <TrendingDown size={20} />
        <p>
          Every listing here is priced under the median of the same model in the same collection. Groups with fewer than three
          listings are skipped, because one outlier is not a market.
        </p>
        <Select label="Minimum discount" value={discount} onChange={setDiscount} options={DISCOUNT_OPTIONS} />
      </div>
      {error ? (
        <ErrorState detail={error} retry={() => void load()} />
      ) : loading ? (
        <LoadingState />
      ) : items.length ? (
        <div className="deal-list">
          {items.map(deal => (
            <article className="deal-row" key={`${deal.gift_id}-${deal.marketplace}-${deal.price_ton}`}>
              <button className="deal-identity" onClick={() => onOpen(deal.gift_id)}>
                <GiftImage src={deal.image_url} alt={deal.model ?? deal.name ?? "gift"} />
                <div>
                  <strong>{deal.model ?? deal.name ?? `Gift #${deal.gift_id}`}</strong>
                  <small>
                    {[deal.collection_name ?? deal.name, deal.gift_number ? `#${deal.gift_number}` : null].filter(Boolean).join(" · ")}
                  </small>
                </div>
              </button>
              <div className="deal-price">
                <b>{formatTon(deal.price_ton)}</b>
                <small>on {deal.marketplace}</small>
              </div>
              <div className="deal-median">
                <b>{formatTon(deal.median_ton)}</b>
                <small>median of {formatCount(deal.peer_count)} listings</small>
              </div>
              <div className="deal-discount">
                <strong>{formatPercent(-Number(deal.discount_percent))}</strong>
                <small>vs peers</small>
              </div>
              <div className="listing-action">
                {deal.url ? (
                  <a className="outline-btn" href={deal.url} target="_blank" rel="noreferrer">
                    Buy <ExternalLink size={13} />
                  </a>
                ) : (
                  <span className="tag-unvalued">no link</span>
                )}
              </div>
            </article>
          ))}
        </div>
      ) : (
        <EmptyState title="Nothing undervalued right now" detail="Lower the discount threshold, or wait for the next market sync." />
      )}
    </section>
  );
}
