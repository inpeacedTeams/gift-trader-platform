import { useEffect, useState } from "react";
import { LockKeyhole, Star } from "lucide-react";
import { getWatchlist } from "../api";
import type { WatchlistCard } from "../types";
import { EmptyState, ErrorState, LoadingState } from "../components/State";
import { GiftImage } from "../components/GiftImage";
import { formatCount, formatTon } from "../format";
import "../gifts.css";
import "../catalog-deals.css";

/** Saved gifts with their current price.
 *
 * Reads a dedicated endpoint rather than filtering live snapshots: a saved
 * gift must stay visible even when every listing for it disappears.
 */
export function Watchlist({
  authenticated,
  onOpen,
  onToggle,
}: {
  authenticated: boolean;
  onOpen: (giftId: number) => void;
  onToggle: (giftId: number, saved: boolean) => Promise<void> | void;
}) {
  const [items, setItems] = useState<WatchlistCard[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    if (!authenticated) {
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      setItems((await getWatchlist()).items);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Watchlist unavailable");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, [authenticated]);

  const remove = async (giftId: number) => {
    setItems(current => current.filter(item => item.id !== giftId));
    await onToggle(giftId, true);
  };

  return (
    <section className="page-section">
      <div className="section-head">
        <div>
          <p className="eyebrow">PERSONAL RADAR</p>
          <h2>Watchlist</h2>
        </div>
        <span className="fresh">
          {authenticated ? `${formatCount(items.length)} saved gifts` : "Sign in to sync"}
        </span>
      </div>
      {!authenticated ? (
        <div className="auth-prompt">
          <LockKeyhole size={22} />
          <div>
            <strong>Sign in through Telegram</strong>
            <p>Your watchlist is private and syncs across devices after authentication.</p>
          </div>
        </div>
      ) : error ? (
        <ErrorState detail={error} retry={() => void load()} />
      ) : loading ? (
        <LoadingState />
      ) : items.length ? (
        <div className="gift-grid">
          {items.map(gift => {
            const title = gift.name ?? gift.canonical_id.slice(0, 18);
            return (
              <div className="gift-card-shell" key={gift.id}>
                <button className="gift-card" onClick={() => onOpen(gift.id)}>
                  <div className="gift-card-media">
                    <GiftImage src={gift.image_url} alt={title} />
                  </div>
                  <div className="gift-card-body">
                    <strong>{title}</strong>
                    <small>
                      {[gift.model, gift.gift_number ? `#${gift.gift_number}` : null]
                        .filter(Boolean)
                        .join(" · ") || "model pending"}
                    </small>
                    <div className="gift-card-price">
                      <span>{formatTon(gift.floor_ton)}</span>
                    </div>
                    <div className="gift-card-meta">
                      <span>median {formatTon(gift.median_ton)}</span>
                      <span>{formatCount(gift.listings_count)} listed</span>
                    </div>
                    {gift.listings_count === 0 && <span className="venue-badge">нет активных лотов</span>}
                    {gift.best_marketplace && (
                      <span className="venue-badge">cheapest on {gift.best_marketplace}</span>
                    )}
                  </div>
                </button>
                <button
                  className="card-star saved"
                  aria-label={`Remove ${title} from watchlist`}
                  aria-pressed
                  onClick={() => void remove(gift.id)}
                >
                  <Star size={14} fill="currentColor" />
                </button>
              </div>
            );
          })}
        </div>
      ) : (
        <EmptyState
          title="Your watchlist is empty"
          detail="Tap the star on any gift in the catalog to follow its price here."
        />
      )}
    </section>
  );
}
