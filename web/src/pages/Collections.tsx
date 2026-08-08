import { useEffect, useState } from "react";
import { Search } from "lucide-react";
import { getCollections } from "../api";
import type { CollectionCard } from "../types";
import { EmptyState, ErrorState, LoadingState } from "../components/State";
import { GiftImage } from "../components/GiftImage";
import { formatCount, formatTon } from "../format";
import "../gifts.css";

/** Every tracked gift series. Picking one opens the catalog filtered to it. */
export function Collections({ onOpen }: { onOpen: (collection: CollectionCard) => void }) {
  const [items, setItems] = useState<CollectionCard[]>([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      setItems((await getCollections()).items);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Collections unavailable");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const visible = items.filter(item => item.name.toLowerCase().includes(query.trim().toLowerCase()));

  return (
    <section className="page-section">
      <div className="section-head">
        <div>
          <p className="eyebrow">GIFT SERIES</p>
          <h2>Collections</h2>
        </div>
        <span className="fresh">
          <i /> {formatCount(items.length)} tracked
        </span>
      </div>
      <form className="gift-search" onSubmit={event => event.preventDefault()}>
        <Search size={16} />
        <input value={query} onChange={event => setQuery(event.target.value)} placeholder="Find a collection, e.g. Snoop Dogg" />
      </form>
      {error ? (
        <ErrorState detail={error} retry={() => void load()} />
      ) : loading ? (
        <LoadingState />
      ) : visible.length ? (
        <div className="collection-grid">
          {visible.map(item => (
            <button className="collection-card" key={item.id} onClick={() => onOpen(item)}>
              <GiftImage src={item.image_url} alt={item.name} />
              <div className="collection-body">
                <strong>{item.name}</strong>
                <small>{formatCount(item.gift_count)} models · {formatCount(item.listings_count)} listed</small>
                <div className="collection-floor">
                  <span>floor</span>
                  <b>{formatTon(item.floor_ton)}</b>
                </div>
              </div>
            </button>
          ))}
        </div>
      ) : (
        <EmptyState title="No collections yet" detail="Collections appear once a market sync stores its first listings." />
      )}
    </section>
  );
}
