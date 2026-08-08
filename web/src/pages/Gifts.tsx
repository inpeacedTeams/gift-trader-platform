import { FormEvent, useEffect, useState } from "react";
import { ChevronLeft, ChevronRight, Search } from "lucide-react";
import { getGifts } from "../api";
import type { GiftCard as GiftCardType } from "../types";
import { EmptyState, ErrorState, LoadingState } from "../components/State";
import { GiftImage } from "../components/GiftImage";
import { formatCount, formatPercent, formatTon } from "../format";
import "../gifts.css";

function Card({ gift, onOpen }: { gift: GiftCardType; onOpen: (id: number) => void }) {
  const change = formatPercent(gift.change_percent);
  const rising = Number(gift.change_percent ?? 0) >= 0;
  const title = gift.name ?? gift.canonical_id.slice(0, 18);
  return (
    <button className="gift-card" onClick={() => onOpen(gift.id)}>
      <GiftImage src={gift.image_url} alt={title} />
      <div className="gift-card-body">
        <strong>{title}</strong>
        <small>{[gift.model, gift.gift_number ? `#${gift.gift_number}` : null].filter(Boolean).join(" · ") || "model pending"}</small>
        <div className="gift-card-price">
          <span>{formatTon(gift.floor_ton)}</span>
          {change && <b className={rising ? "trend-up" : "trend-down"}>{change}</b>}
        </div>
        <div className="gift-card-meta">
          <span>median {formatTon(gift.median_ton)}</span>
          <span>{formatCount(gift.listings_count)} listed</span>
        </div>
      </div>
    </button>
  );
}

export function Gifts({ onOpen }: { onOpen: (id: number) => void }) {
  const [items, setItems] = useState<GiftCardType[]>([]);
  const [query, setQuery] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [hasNext, setHasNext] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      const data = await getGifts({ page, search: search || undefined });
      setItems(data.items);
      setTotal(data.total);
      setHasNext(data.has_next);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Catalog unavailable");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, [page, search]);

  const submit = (event: FormEvent) => {
    event.preventDefault();
    setPage(1);
    setSearch(query.trim());
  };

  return (
    <section className="page-section">
      <div className="section-head">
        <div>
          <p className="eyebrow">PERSISTED CATALOG</p>
          <h2>Gifts</h2>
        </div>
        <span className="fresh">
          <i /> {formatCount(total)} tracked
        </span>
      </div>
      <form className="gift-search" onSubmit={submit}>
        <Search size={16} />
        <input value={query} onChange={event => setQuery(event.target.value)} placeholder="Search by name, model or identity" />
        <button className="outline-btn">Search</button>
      </form>
      {error ? (
        <ErrorState detail={error} retry={() => void load()} />
      ) : loading ? (
        <LoadingState />
      ) : items.length ? (
        <>
          <div className="gift-grid">
            {items.map(gift => (
              <Card key={gift.id} gift={gift} onOpen={onOpen} />
            ))}
          </div>
          <div className="pager">
            <button className="icon-btn" aria-label="Previous page" disabled={page === 1} onClick={() => setPage(current => Math.max(1, current - 1))}>
              <ChevronLeft size={16} />
            </button>
            <span>page {page}</span>
            <button className="icon-btn" aria-label="Next page" disabled={!hasNext} onClick={() => setPage(current => current + 1)}>
              <ChevronRight size={16} />
            </button>
          </div>
        </>
      ) : (
        <EmptyState title="Nothing tracked yet" detail="Run a market sync, then refresh. Listings appear as soon as a source responds." />
      )}
    </section>
  );
}
