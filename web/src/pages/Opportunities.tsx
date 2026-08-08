import { useEffect, useMemo, useState } from "react";
import { ExternalLink, Filter, Search } from "lucide-react";
import { getArbitrage } from "../api";
import type { ArbitrageOpportunity } from "../types";
import { EmptyState, ErrorState, LoadingState } from "../components/State";
import { GiftImage } from "../components/GiftImage";
import { Select } from "../components/Select";
import { formatCount, formatPercent, formatTon, formatTonDelta } from "../format";
import "../gifts.css";

const EDGE_OPTIONS = [
  { value: "0", label: "Any edge" },
  { value: "5", label: "5% and above" },
  { value: "10", label: "10% and above" },
  { value: "20", label: "20% and above" },
];

export function Opportunities({ onOpen }: { onOpen: (giftId: number) => void }) {
  const [items, setItems] = useState<ArbitrageOpportunity[]>([]);
  const [query, setQuery] = useState("");
  const [minimum, setMinimum] = useState("0");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      setItems((await getArbitrage(Number(minimum))).items);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Arbitrage unavailable");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, [minimum]);

  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return items;
    return items.filter(item =>
      `${item.name ?? ""} ${item.model ?? ""} ${item.collection_name ?? ""} ${item.buy_marketplace} ${item.sell_marketplace}`
        .toLowerCase()
        .includes(needle)
    );
  }, [items, query]);

  return (
    <section className="page-section">
      <div className="section-head">
        <div>
          <p className="eyebrow">EXECUTION QUEUE</p>
          <h2>Opportunities</h2>
        </div>
        <span className="fresh">
          <i /> {formatCount(filtered.length)} verified signals
        </span>
      </div>
      <div className="filter-bar">
        <label className="search">
          <Search size={16} />
          <input
            aria-label="Search opportunities"
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="Search gift, model or marketplace"
          />
        </label>
        <div className="filter-select">
          <Filter size={15} />
          <Select label="Minimum edge" value={minimum} onChange={setMinimum} options={EDGE_OPTIONS} />
        </div>
      </div>
      {error ? (
        <ErrorState detail={error} retry={() => void load()} />
      ) : loading ? (
        <LoadingState />
      ) : filtered.length ? (
        <div className="opportunity-grid stagger">
          {filtered.map(item => (
            <article className="opportunity-card lift" key={`${item.gift_id}-${item.buy_marketplace}-${item.sell_marketplace}`}>
              <div className="card-top">
                <GiftImage src={item.image_url} alt={item.name ?? "gift"} className="arb-thumb" />
                <span className="verified">FEE AWARE</span>
              </div>
              <h3>
                <button className="link-btn" onClick={() => onOpen(item.gift_id)}>
                  {item.name ?? item.collection_name ?? `Gift #${item.gift_id}`}
                </button>
              </h3>
              {item.model && <p className="muted-copy">{item.model}</p>}
              <div className="route">
                <span>
                  Buy on <b>{item.buy_marketplace}</b>
                  <strong>{formatTon(item.buy_price_ton)}</strong>
                </span>
                <span>
                  Sell on <b>{item.sell_marketplace}</b>
                  <strong>{formatTon(item.sell_price_ton)}</strong>
                </span>
              </div>
              <div className="card-profit">
                <span>Net edge</span>
                <strong>{formatTonDelta(item.profit_ton)}</strong>
                <b>{formatPercent(item.profit_percent)}</b>
              </div>
              {item.buy_url && (
                <a className="outline-btn" href={item.buy_url} target="_blank" rel="noreferrer">
                  Открыть лот <ExternalLink size={13} />
                </a>
              )}
            </article>
          ))}
        </div>
      ) : (
        <EmptyState
          title="No matching opportunities"
          detail="Спред считается только по подаркам, которые есть минимум на двух площадках. Подключите второй источник или снизьте порог."
        />
      )}
    </section>
  );
}
