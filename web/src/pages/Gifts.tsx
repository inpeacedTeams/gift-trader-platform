import { FormEvent, MouseEvent, useEffect, useState } from "react";
import { ChevronLeft, ChevronRight, Search, Star, Tag, X } from "lucide-react";
import { getGiftAttributes, getGifts, type GiftSort } from "../api";
import type { AttributeGroups, AttributeStat, GiftCard as GiftCardType, RarityTier } from "../types";
import { EmptyState, ErrorState, LoadingState } from "../components/State";
import { GiftImage } from "../components/GiftImage";
import { RARITY_TIERS, RarityBadge } from "../components/Rarity";
import { Select } from "../components/Select";
import { formatCount, formatPercent, formatRarity, formatTon } from "../format";
import "../gifts.css";
import "../catalog-deals.css";

const EMPTY_ATTRIBUTES: AttributeGroups = { data_mode: "persisted", models: [], backdrops: [], symbols: [] };

const MARKET_OPTIONS = [
  { value: "", label: "All marketplaces" },
  { value: "tonnel", label: "Tonnel" },
  { value: "getgems", label: "GetGems" },
  { value: "mrkt", label: "MRKT" },
  { value: "portals", label: "Portals" },
  { value: "fragment", label: "Fragment" },
];

const SORT_OPTIONS = [
  { value: "recent", label: "Recently added" },
  { value: "deal_desc", label: "Biggest discount", hint: "Furthest below its peer group" },
  { value: "floor_asc", label: "Cheapest first" },
  { value: "floor_desc", label: "Most expensive" },
  { value: "depth", label: "Most listed" },
  { value: "change_desc", label: "Top gainers 24h" },
  { value: "change_asc", label: "Top losers 24h" },
];

const RARITY_OPTIONS = [
  { value: "", label: "Any rarity" },
  ...RARITY_TIERS.map(tier => ({ value: tier.value, label: tier.label, hint: tier.hint })),
];

/** Each trait option carries its scarcity and its floor.
 *
 * Those two numbers together are the trade: a 0.2% backdrop sitting at the
 * same floor as a plain one is the whole reason to open the gift.
 */
function attributeOptions(allLabel: string, stats: AttributeStat[]) {
  return [
    { value: "", label: allLabel },
    ...stats.map(stat => ({
      value: stat.value,
      label: stat.value,
      hint:
        [
          formatRarity(stat.rarity_percent),
          stat.listings_count ? `floor ${formatTon(stat.floor_ton)}` : "none listed",
        ]
          .filter(Boolean)
          .join(" · ") || undefined,
    })),
  ];
}

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
  const traits = [gift.model, gift.backdrop, gift.symbol].filter(Boolean).join(" · ");
  const save = (event: MouseEvent) => {
    event.stopPropagation();
    onToggleSave(gift.id, saved);
  };
  return (
    <div className="gift-card-shell">
      <button className="gift-card" onClick={() => onOpen(gift.id)}>
        <div className="gift-card-media">
          <GiftImage src={gift.image_url} alt={title} />
          <RarityBadge gift={gift} />
          {deal !== null && deal >= 1 && (
            <span className="deal-badge" title="Below the median of its own model and rarity tier">
              <Tag size={11} /> {deal.toFixed(0)}% under
            </span>
          )}
        </div>
        <div className="gift-card-body">
          <strong>{title}</strong>
          <small>{[traits, gift.gift_number ? `#${gift.gift_number}` : null].filter(Boolean).join(" · ") || "traits pending"}</small>
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
  const [attributes, setAttributes] = useState<AttributeGroups>(EMPTY_ATTRIBUTES);
  const [query, setQuery] = useState("");
  const [search, setSearch] = useState("");
  const [marketplace, setMarketplace] = useState("");
  const [model, setModel] = useState("");
  const [backdrop, setBackdrop] = useState("");
  const [symbol, setSymbol] = useState("");
  const [rarityTier, setRarityTier] = useState<RarityTier | "">("");
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
        backdrop: backdrop || undefined,
        symbol: symbol || undefined,
        rarityTier: rarityTier || undefined,
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
    setBackdrop("");
    setSymbol("");
    void getGiftAttributes(collection?.id)
      .then(setAttributes)
      .catch(() => setAttributes(EMPTY_ATTRIBUTES));
  }, [collection?.id]);

  useEffect(() => {
    void load();
  }, [page, search, marketplace, model, backdrop, symbol, rarityTier, sort, dealsOnly, priceFilter, collection?.id]);

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

  const pick = (setter: (value: string) => void) => (next: string) => {
    setPage(1);
    setter(next);
  };

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
        <input value={query} onChange={event => setQuery(event.target.value)} placeholder="Search by name, model, backdrop or symbol" />
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
        <Select label="Sort" value={sort} onChange={pick(next => setSort(next as GiftSort))} options={SORT_OPTIONS} />
        {attributes.models.length > 0 && (
          <Select
            label="Model"
            value={model}
            onChange={pick(setModel)}
            options={attributeOptions("All models", attributes.models)}
          />
        )}
        {attributes.backdrops.length > 0 && (
          <Select
            label="Backdrop"
            value={backdrop}
            onChange={pick(setBackdrop)}
            options={attributeOptions("All backdrops", attributes.backdrops)}
          />
        )}
        {attributes.symbols.length > 0 && (
          <Select
            label="Symbol"
            value={symbol}
            onChange={pick(setSymbol)}
            options={attributeOptions("All symbols", attributes.symbols)}
          />
        )}
        <Select
          label="Rarity"
          value={rarityTier}
          onChange={pick(next => setRarityTier(next as RarityTier | ""))}
          options={RARITY_OPTIONS}
        />
        <Select label="Marketplace" value={marketplace} onChange={pick(setMarketplace)} options={MARKET_OPTIONS} />
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
          title={dealsOnly ? "No discounts right now" : "Nothing matches"}
          detail={
            dealsOnly
              ? "Nothing is trading below its peer median. Turn the filter off to see the full catalog."
              : "Loosen the filters, or run a market sync if the catalog is still empty."
          }
        />
      )}
    </section>
  );
}
