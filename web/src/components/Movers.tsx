import { useEffect, useState } from "react";
import { TrendingDown, TrendingUp } from "lucide-react";
import { getMovers } from "../api";
import type { MoverCard } from "../types";
import { GiftImage } from "./GiftImage";
import { Select } from "./Select";
import { formatPercent, formatTon } from "../format";
import "./movers.css";

const WINDOWS = [
  { value: "24", label: "Last 24 hours" },
  { value: "168", label: "Last 7 days" },
];

function Column({
  title,
  items,
  direction,
  onOpen,
}: {
  title: string;
  items: MoverCard[];
  direction: "up" | "down";
  onOpen: (giftId: number) => void;
}) {
  return (
    <div className="mover-column">
      <div className="mover-head">
        {direction === "up" ? <TrendingUp size={15} /> : <TrendingDown size={15} />}
        <strong>{title}</strong>
      </div>
      {items.length ? (
        items.map(item => (
          <button className="mover-row" key={item.gift_id} onClick={() => onOpen(item.gift_id)}>
            <GiftImage src={item.image_url} alt={item.name ?? "gift"} />
            <div className="mover-identity">
              <strong>{item.name ?? item.collection_name ?? `Gift #${item.gift_id}`}</strong>
              <small>{item.model ?? item.collection_name ?? "model pending"}</small>
            </div>
            <div className="mover-price">
              <b>{formatTon(item.floor_ton)}</b>
              <small>from {formatTon(item.previous_ton)}</small>
            </div>
            <span className={direction === "up" ? "trend-up" : "trend-down"}>{formatPercent(item.change_percent)}</span>
          </button>
        ))
      ) : (
        <p className="mover-empty">Nothing moved in this window.</p>
      )}
    </div>
  );
}

/** Biggest floor moves in both directions. Needs at least two snapshots per gift. */
export function Movers({ onOpen }: { onOpen: (giftId: number) => void }) {
  const [hours, setHours] = useState("24");
  const [gainers, setGainers] = useState<MoverCard[]>([]);
  const [losers, setLosers] = useState<MoverCard[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    void getMovers(Number(hours))
      .then(data => {
        if (cancelled) return;
        setGainers(data.gainers);
        setLosers(data.losers);
      })
      .catch(() => {
        if (cancelled) return;
        setGainers([]);
        setLosers([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [hours]);

  const empty = !loading && gainers.length === 0 && losers.length === 0;

  return (
    <section className="movers-panel">
      <div className="section-head">
        <div>
          <p className="eyebrow">MARKET MOVEMENT</p>
          <h2>Top movers</h2>
        </div>
        <Select label="Window" value={hours} onChange={setHours} options={WINDOWS} />
      </div>
      {empty ? (
        <p className="mover-empty wide">
          Movement needs at least two stored snapshots per gift. Come back after a few sync cycles.
        </p>
      ) : (
        <div className="movers-grid">
          <Column title="Gainers" items={gainers} direction="up" onOpen={onOpen} />
          <Column title="Losers" items={losers} direction="down" onOpen={onOpen} />
        </div>
      )}
    </section>
  );
}
