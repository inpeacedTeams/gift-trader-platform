import { FormEvent, MouseEvent, useEffect, useState } from "react";
import { ChevronLeft, ChevronRight, Search, Star, Tag, X } from "lucide-react";
import { getGiftModels, getGifts, type GiftSort } from "../api";
import type { GiftCard as GiftCardType } from "../types";
import { EmptyState, ErrorState, LoadingState } from "../components/State";
import { GiftImage } from "../components/GiftImage";
import { Select } from "../components/Select";
import { formatCount, formatPercent, formatTon } from "../format";
import "../gifts.css";
import "../catalog-deals.css";

const MARKET_OPTIONS = [
  { value: "", label: "All marketplaces" },
  { value: "tonnel", label: "Tonnel" },
  { value: "getgems", label: "GetGems" },
  { value: "portals", label: "Portals" },
  { value: "fragment", label: "Fragment" },
];

const SORT_OPTIONS = [
  { value: "recent", label: "Recently added" },
  { value: "deal_desc", label: "Biggest discount", hint: "Furthest below its model peers" },
  { value: "floor_asc", label: "Cheapest first" },
  { value: "floor_desc", label: "Most expensive" },
  { value: "depth", label: "Most listed" },
  { value: "change_desc", label: "Top gainers 24h" },
  { value: "change_asc", label: "Top losers 24h" },
];

export type CollectionFilter = { id: number; name: string };

type CardProps = {
  gift: GiftCardType;
  onOpen: (id: number) => void;
  saved: boolean;
  canSave: boolean;
  onToggleSave: (giftId: number, saved: boolean) => void;
};

function Card({ gift, onOpen, saved, canSave, onToggleSave }: CardProps) {
  const change = formatPercent(gift.change_percent);
  const rising = Number(gift.change_percent ?? 0) >= 0;
  const deal = gift.deal_percent === null || gift.deal_percent === undefined ? null : Number(gift.deal_percent);
  const title = gift.name ?? gift.canonical_id.slice(0, 18);
  const save = (event: MouseEvent) => {
    event.stopPropagation();
    onToggleSave(gift.id, saved);
  };
  return (
    <div className="gift-card-shell">
      <button className="gift-card" onClick={() => onOpen(gift.id)}>
        <div className="gift-card-media">
          <GiftImage src={gift.image_url} alt={title} />
          {deal !== null && deal >= 1 && (
            <span className="deal-badge" title="Below the median of the same model">
              <Tag size={11} /> {deal.toFixed(0)}% under
            </span>
          )}
        </div>
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
          {gift.best_marketplace && <span className="venue-badge">cheapest on {gift.best_marketplace}</span>}
        </div>
      </button>
      {canSave && (
        <button
          className={saved ? "card-star saved" : "card-star"}
          aria-label={saved ? `Remove ${title} from watchlist` : `Save ${title} to watchlist`}
          aria-pressed={saved}
          onClick={save}
        >
          <Star size={14} fill={saved ? "currentColor" : "none"} />
        </button>
      )}
    </div>
  );
}

export function Gifts({
  onOpen,
  collection,
  onClearCollection,
  watchlistIds = [],
  authenticated = false,
  onToggleWatchlist,
}: {
  onOpen: (id: number) => void;
  collection?: CollectionFilter | null;
  onClearCollection?: () => void;
  watchlistIds?: number[];
  authenticated?: boolean;
  onToggleWatchlist?: (giftId: number, saved: boolean) => void;
}) {
  const [items, setItems] = useState<GiftCardType[]>([]);
  const [models, setModels] = useState<string[]>([]);
  const [query, setQuery] = useState("");
  const [search, setSearch] = useState("");
  const [marketplace, setMarketplace] = useState("");
  const [model, setModel] = useState("");
  const [sort, setSort] = useState<GiftSort>("recent");
  const [dealsOnly, setDealsOnly] = useState(false);
  const [minPrice, setMinPrice] = useState("");
  const [maxPrice, setMaxPrice] = useState("");
  const [priceFilter, setPriceFilter] = useState({ min: "", max: "" });
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [hasNext, setHasNext] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      const data = await getGifts({
        page,
        sort,
        dealsOnly,
        search: search || undefined,
        marketplace: marketplace || undefined,
        model: model || undefined,
        minPrice: priceFilter.min || undefined,
        maxPrice: priceFilter.max || undefined,
        collectionId: collection?.id,
      });
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
    setPage(1);
    setModel("");
    void getGiftModels(collection?.id)
      .then(setModels)
      .catch(() => setModels([]));
  }, [collection?.id]);

  useEffect(() => {
    void load();
  }, [page, search, marketplace, model, sort, dealsOnly, priceFilter, collection?.id]);

  const submit = (event: FormEvent) => {
    event.preventDefault();
    setPage(1);
    setSearch(query.trim());
    setPriceFilter({ min: minPrice.trim(), max: maxPrice.trim() });
  };

  const toggleDeals = () => {
    setPage(1);
    setDealsOnly(current => !current);
  };

  const modelOptions = [{ value: "", label: "All models" }, ...models.map(item => ({ value: item, label: item }))];

  return (
    <section className="page-section">
      <div className="section-head">
        <div>
          <p className="eyebrow">{collection ? "COLLECTION" : "PERSISTED CATALOG"}</p>
          <h2>{collection?.name ?? "Gifts"}</h2>
        </div>
        <span className="fresh">
          <i /> {formatCount(total)} tracked
        </span>
      </div>
      {collection && onClearCollection && (
        <button className="filter-chip" onClick={onClearCollection}>
          {collection.name}
          <X size={13} />
        </button>
      )}
      <form className="gift-search" onSubmit={submit}>
        <Search size={16} />
        <input value={query} onChange={event => setQuery(event.target.value)} placeholder="Search by name, model or identity" />
        <div className="price-range">
          <input
            type="number"
            min="0"
            step="any"
            value={minPrice}
            onChange={event => setMinPrice(event.target.value)}
            placeholder="min"
            aria-label="Minimum price in TON"
          />
          <span>–</span>
          <input
            type="number"
            min="0"
            step="any"
            value={maxPrice}
            onChange={event => setMaxPrice(event.target.value)}
            placeholder="max"
            aria-label="Maximum price in TON"
          />
        </div>
        <button className="outline-btn">Apply</button>
      </form>
      <div className="catalog-filters">
        <Select
          label="Sort"
          value={sort}
          onChange={next => {
            setPage(1);
            setSort(next as GiftSort);
          }}
          options={SORT_OPTIONS}
        />
        {models.length > 0 && (
          <Select
            label="Model"
            value={model}
            onChange={next => {
              setPage(1);
              setModel(next);
            }}
            options={modelOptions}
          />
        )}
        <Select
          label="Marketplace"
          value={marketplace}
          onChange={next => {
            setPage(1);
            setMarketplace(next);
          }}
          options={MARKET_OPTIONS}
        />
        <button
          type="button"
          className={dealsOnly ? "toggle-chip on" : "toggle-chip"}
          aria-pressed={dealsOnly}
          onClick={toggleDeals}
        >
          <Tag size={13} /> Underpriced
        </button>
      </div>
      {error ? (
        <ErrorState detail={error} retry={() => void load()} />
      ) : loading ? (
        <LoadingState />
      ) : items.length ? (
        <>
          <div className="gift-grid">
            {items.map(gift => (
              <Card
                key={gift.id}
                gift={gift}
                onOpen={onOpen}
                saved={watchlistIds.includes(gift.id)}
                canSave={authenticated && Boolean(onToggleWatchlist)}
                onToggleSave={(giftId, saved) => onToggleWatchlist?.(giftId, saved)}
              />
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
        <EmptyState
          title={dealsOnly ? "No discounts right now" : "Nothing tracked yet"}
          detail={
            dealsOnly
              ? "Nothing is trading below its model median. Turn the filter off to see the full catalog."
              : "Run a market sync, then refresh. Listings appear as soon as a source responds."
          }
        />
      )}
    </section>
  );
}
