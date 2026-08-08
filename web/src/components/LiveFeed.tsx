import { useEffect, useRef, useState } from "react";
import { ArrowDownRight, ArrowUpRight, Plus, Radio, X } from "lucide-react";
import { getEvents, RateLimited } from "../api";
import type { MarketEvent } from "../types";
import { GiftImage } from "./GiftImage";
import { formatAgo, formatPercent, formatTon } from "../format";
import "./live-feed.css";

const POLL_MS = 15000;
const MAX_ROWS = 30;
const HIGHLIGHT_MS = 2500;

const LABELS: Record<string, string> = {
  listed: "выставлен",
  price_down: "дешевле",
  price_up: "дороже",
  delisted: "снят",
};

function Icon({ type }: { type: string }) {
  if (type === "price_down") return <ArrowDownRight size={14} />;
  if (type === "price_up") return <ArrowUpRight size={14} />;
  if (type === "delisted") return <X size={14} />;
  return <Plus size={14} />;
}

/** Everything that changed since the last crawl, updating by itself.
 *
 * Polls with an id cursor. If the API asks us to slow down, the next poll
 * waits as long as it says: a throttled client that keeps hammering only
 * makes the throttling worse.
 */
export function LiveFeed({ onOpen }: { onOpen: (giftId: number) => void }) {
  const [items, setItems] = useState<MarketEvent[]>([]);
  const [freshIds, setFreshIds] = useState<Set<number>>(new Set());
  const [live, setLive] = useState(false);
  const cursor = useRef<number | null>(null);
  const loaded = useRef(false);

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;
    let highlightTimer: ReturnType<typeof setTimeout>;

    const schedule = (delay: number) => {
      if (cancelled) return;
      timer = setTimeout(() => void pull(), delay);
    };

    const pull = async () => {
      try {
        const feed = await getEvents({ afterId: cursor.current ?? undefined, limit: MAX_ROWS });
        if (cancelled) return;
        setLive(true);
        if (feed.items.length) {
          cursor.current = feed.latest_id ?? cursor.current;
          setItems(current => [...feed.items, ...current].slice(0, MAX_ROWS));
          // The very first page is history, not news, so it does not flash.
          if (loaded.current) {
            setFreshIds(new Set(feed.items.map(item => item.id)));
            clearTimeout(highlightTimer);
            highlightTimer = setTimeout(() => {
              if (!cancelled) setFreshIds(new Set());
            }, HIGHLIGHT_MS);
          }
        }
        loaded.current = true;
        schedule(POLL_MS);
      } catch (error) {
        if (cancelled) return;
        setLive(false);
        schedule(error instanceof RateLimited ? error.retryAfter * 1000 : POLL_MS * 2);
      }
    };

    void pull();
    return () => {
      cancelled = true;
      clearTimeout(timer);
      clearTimeout(highlightTimer);
    };
  }, []);

  return (
    <section className="feed-panel">
      <div className="section-head">
        <div>
          <p className="eyebrow">LIVE</p>
          <h2>Что происходит на рынке</h2>
        </div>
        <span className={live ? "feed-live on" : "feed-live"}>
          <Radio size={13} /> {live ? "обновляется" : "нет связи"}
        </span>
      </div>
      {items.length ? (
        <div className="feed-list">
          {items.map(event => (
            <button
              key={event.id}
              className={`feed-row ${event.event_type}${freshIds.has(event.id) ? " fresh" : ""}`}
              onClick={() => onOpen(event.gift_id)}
            >
              <span className="feed-icon">
                <Icon type={event.event_type} />
              </span>
              <GiftImage src={event.image_url} alt={event.name ?? "gift"} />
              <div className="feed-identity">
                <strong>{event.name ?? event.collection_name ?? `Gift #${event.gift_id}`}</strong>
                <small>
                  {event.model ?? "model pending"} · {event.marketplace}
                </small>
              </div>
              <div className="feed-price">
                <b>{formatTon(event.price_ton)}</b>
                {event.previous_ton && <small>было {formatTon(event.previous_ton)}</small>}
              </div>
              <span className="feed-tag">
                {event.change_percent ? formatPercent(event.change_percent) : LABELS[event.event_type]}
              </span>
              <small className="feed-time">{formatAgo(event.occurred_at)}</small>
            </button>
          ))}
        </div>
      ) : (
        <p className="muted-copy">
          Пока тихо. Лента заполнится после первого прохода парсеров: новые лоты, изменения цен и снятия.
        </p>
      )}
    </section>
  );
}
