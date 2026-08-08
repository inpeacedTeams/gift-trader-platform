import { FormEvent, useEffect, useState } from "react";
import { ChevronRight, Search } from "lucide-react";
import { getCollections } from "../api";
import type { CollectionCard } from "../types";
import { EmptyState, ErrorState, LoadingState } from "../components/State";
import { GiftImage } from "../components/GiftImage";
import { formatCount, formatTon } from "../format";
import "../gifts.css";

export function Collections({ onOpen }: { onOpen: (collection: CollectionCard) => void }) {
  const [items, setItems] = useState<CollectionCard[]>([]);
  const [query, setQuery] = useState("");
  const [search, setSearch] = useState("");
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      const data = await getCollections({ search: search || undefined });
      setItems(data.items);
      setTotal(data.total);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Collections unavailable");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, [search]);

  const submit = (event: FormEvent) => {
    event.preventDefault();
    setSearch(query.trim());
  };

  return (
    <section className="page-section">
      <div className="section-head">
        <div>
          <p className="eyebrow">BY COLLECTION</p>
          <h2>Collections</h2>
        </div>
        <span className="fresh">
          <i /> {formatCount(total)} tracked
        </span>
      </div>
      <form className="gift-search" onSubmit={submit}>
        <Search size={16} />
        <input value={query} onChange={event => setQuery(event.target.value)} placeholder="Find a collection, e.g. Snoop Dogg" />
        <button className="outline-btn">Search</button>
      </form>
      {error ? (
        <ErrorState detail={error} retry={() => void load()} />
      ) : loading ? (
        <LoadingState />
      ) : items.length ? (
        <div className="collection-grid">
          {items.map(collection => (
            <button className="collection-card" key={collection.id} onClick={() => onOpen(collection)}>
              <GiftImage src={collection.image_url} alt={collection.name ?? "Collection"} />
              <div className="collection-body">
                <strong>{collection.name ?? collection.chain_address.slice(0, 16)}</strong>
                <small>{formatCount(collection.gift_count)} models · {formatCount(collection.listings_count)} listed</small>
                <div className="collection-floor">
                  <span>floor</span>
                  <b>{formatTon(collection.floor_ton)}</b>
                </div>
              </div>
              <ChevronRight size={16} className="collection-caret" />
            </button>
          ))}
        </div>
      ) : (
        <EmptyState title="No collections yet" detail="Collections appear once a market sync stores its first listings." />
      )}
    </section>
  );
}
