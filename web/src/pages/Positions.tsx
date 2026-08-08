import { useEffect, useState } from "react";
import { Check, LockKeyhole, Plus, RotateCcw, Trash2, X } from "lucide-react";
import {
  closePosition,
  deletePosition,
  getGifts,
  getPositions,
  openPosition,
  reopenPosition,
  type PositionCard,
  type PositionSummary,
} from "../api";
import type { GiftCard } from "../types";
import { EmptyState, ErrorState, LoadingState } from "../components/State";
import { GiftImage } from "../components/GiftImage";
import { formatCount, formatPercent, formatTon, formatTonDelta } from "../format";
import "../positions.css";

const VENUES = ["tonnel", "mrkt", "portals", "getgems", "fragment"];

function toNumber(value?: string | null): number | null {
  if (value === null || value === undefined || value === "") return null;
  const amount = Number(value);
  return Number.isFinite(amount) ? amount : null;
}

/** Win rate is a share, not a change, so it never carries a sign. */
function plainPercent(value?: string | null): string | null {
  const amount = toNumber(value);
  if (amount === null) return null;
  return `${new Intl.NumberFormat("en-US", { maximumFractionDigits: amount >= 10 ? 0 : 1 }).format(amount)}%`;
}

function giftTitle(item: { name?: string | null; model?: string | null; gift_id?: number }): string {
  return item.name ?? item.model ?? `Gift #${item.gift_id ?? ""}`;
}

/** The flipper's own book.
 *
 * Every other screen prices the market; this one prices the user. Open lots
 * are marked against the live floor net of the venue fee, so the number on
 * screen is money that would actually arrive. A gift with no active listing
 * reports no value instead of being marked to the last thing we saw.
 */
export function Positions({
  authenticated,
  onOpen,
}: {
  authenticated: boolean;
  onOpen: (giftId: number) => void;
}) {
  const [items, setItems] = useState<PositionCard[]>([]);
  const [summary, setSummary] = useState<PositionSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);

  const load = async () => {
    if (!authenticated) {
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const data = await getPositions();
      setItems(data.items);
      setSummary(data.summary);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Positions unavailable");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, [authenticated]);

  const open = items.filter(item => item.is_open);
  const closed = items.filter(item => !item.is_open);

  return (
    <section className="page-section">
      <div className="section-head">
        <div>
          <p className="eyebrow">YOUR BOOK</p>
          <h2>Positions</h2>
        </div>
        {authenticated && !loading && !error && (
          <button className="outline-btn" onClick={() => setAdding(value => !value)}>
            {adding ? <X size={15} /> : <Plus size={15} />} {adding ? "Отмена" : "Записать покупку"}
          </button>
        )}
      </div>

      {!authenticated ? (
        <div className="auth-prompt">
          <LockKeyhole size={22} />
          <div>
            <strong>Sign in through Telegram</strong>
            <p>Книга сделок приватная: чтобы вести свой P&amp;L, нужно войти.</p>
          </div>
        </div>
      ) : error ? (
        <ErrorState detail={error} retry={() => void load()} />
      ) : loading ? (
        <LoadingState />
      ) : (
        <>
          {summary && <Summary summary={summary} />}
          {adding && (
            <AddPosition
              onCreated={() => {
                setAdding(false);
                void load();
              }}
            />
          )}
          {open.length > 0 && (
            <div className="pos-block">
              <h3 className="pos-heading">Открытые · {formatCount(open.length)}</h3>
              <div className="pos-list">
                {open.map(position => (
                  <PositionRow
                    key={position.id}
                    position={position}
                    onOpen={onOpen}
                    onChanged={() => void load()}
                  />
                ))}
              </div>
            </div>
          )}
          {closed.length > 0 && (
            <div className="pos-block">
              <h3 className="pos-heading">Закрытые · {formatCount(closed.length)}</h3>
              <div className="pos-list">
                {closed.map(position => (
                  <PositionRow
                    key={position.id}
                    position={position}
                    onOpen={onOpen}
                    onChanged={() => void load()}
                  />
                ))}
              </div>
            </div>
          )}
          {items.length === 0 && !adding && (
            <EmptyState
              title="Книга пустая"
              detail="Запишите покупку, и продукт начнёт считать вашу прибыль, а не только цены рынка."
            />
          )}
        </>
      )}
    </section>
  );
}

function Summary({ summary }: { summary: PositionSummary }) {
  const unrealized = toNumber(summary.unrealized_ton) ?? 0;
  const realized = toNumber(summary.realized_ton) ?? 0;
  const winRate = plainPercent(summary.win_rate_percent);
  return (
    <>
      <div className="metric-grid">
        <div className="metric blue">
          <span>Вложено</span>
          <strong>{formatTon(summary.invested_ton)}</strong>
          <small>{formatCount(summary.open_count)} открытых позиций</small>
        </div>
        <div className="metric green">
          <span>Сейчас стоит</span>
          <strong>{formatTon(summary.market_value_ton)}</strong>
          <small className={unrealized >= 0 ? "pos-up" : "pos-down"}>
            {formatTonDelta(summary.unrealized_ton)} нереализовано
          </small>
        </div>
        <div className="metric violet">
          <span>Зафиксировано</span>
          <strong className={realized >= 0 ? "pos-up" : "pos-down"}>{formatTonDelta(summary.realized_ton)}</strong>
          <small>
            {winRate
              ? `винрейт ${winRate} · ${formatCount(summary.wins)} из ${formatCount(summary.closed_count)}`
              : "нет закрытых сделок"}
          </small>
        </div>
      </div>
      {summary.unpriced_count > 0 && (
        <p className="pos-note">
          {formatCount(summary.unpriced_count)} позиций без активных лотов на рынке: их стоимость неизвестна, поэтому
          они не попадают в итоги.
        </p>
      )}
    </>
  );
}

function PositionRow({
  position,
  onOpen,
  onChanged,
}: {
  position: PositionCard;
  onOpen: (giftId: number) => void;
  onChanged: () => void;
}) {
  const [closing, setClosing] = useState(false);
  const [sellPrice, setSellPrice] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const profit = toNumber(position.profit_ton);
  const title = giftTitle(position);
  const meta = [position.model, position.gift_number ? `#${position.gift_number}` : null, position.marketplace]
    .filter(Boolean)
    .join(" · ");

  const run = async (action: () => Promise<unknown>) => {
    setBusy(true);
    setError(null);
    try {
      await action();
      onChanged();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не получилось");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className={`pos-row${position.is_open ? "" : " closed"}`}>
      <button className="pos-gift" onClick={() => onOpen(position.gift_id)}>
        <span className="pos-media">
          <GiftImage src={position.image_url} alt={title} />
        </span>
        <span className="pos-name">
          <strong>{title}</strong>
          <small>{meta || "model pending"}</small>
        </span>
      </button>

      <div className="pos-cell">
        <b>{formatTon(position.cost_basis_ton)}
        </b>
        <small>
          вход {formatTon(position.buy_price_ton)}
          {position.quantity > 1 ? ` × ${position.quantity}` : ""}
        </small>
      </div>

      <div className="pos-cell">
        {position.is_open ? (
          position.exit_net_ton ? (
            <>
              <b>{formatTon(position.exit_net_ton)}</b>
              <small>чистыми{position.exit_venue ? ` на ${position.exit_venue}` : ""}</small>
            </>
          ) : (
            <>
              <b className="pos-unknown">--</b>
              <small>нет активных лотов</small>
            </>
          )
        ) : (
          <>
            <b>{formatTon(position.sell_price_ton)}</b>
            <small>продано{position.sell_marketplace ? ` на ${position.sell_marketplace}` : ""}</small>
          </>
        )}
      </div>

      <div className="pos-cell pos-pnl">
        {profit === null ? (
          <b className="pos-unknown">--</b>
        ) : (
          <>
            <b className={profit >= 0 ? "pos-up" : "pos-down"}>{formatTonDelta(position.profit_ton)}</b>
            <small className={profit >= 0 ? "pos-up" : "pos-down"}>{formatPercent(position.roi_percent) ?? ""}</small>
          </>
        )}
      </div>

      <div className="pos-actions">
        {position.is_open ? (
          closing ? (
            <div className="pos-close">
              <input
                type="number"
                min="0"
                step="0.01"
                placeholder="цена продажи"
                value={sellPrice}
                onChange={event => setSellPrice(event.target.value)}
                autoFocus
              />
              <button
                className="pos-confirm"
                disabled={busy || !sellPrice}
                onClick={() => void run(() => closePosition(position.id, sellPrice))}
                aria-label="Подтвердить продажу"
              >
                <Check size={15} />
              </button>
              <button className="pos-icon" onClick={() => setClosing(false)} aria-label="Отмена">
                <X size={15} />
              </button>
            </div>
          ) : (
            <button className="pos-sell" onClick={() => setClosing(true)}>
              Продал
            </button>
          )
        ) : (
          <button
            className="pos-icon"
            disabled={busy}
            onClick={() => void run(() => reopenPosition(position.id))}
            aria-label="Вернуть в открытые"
            title="Вернуть в открытые"
          >
            <RotateCcw size={15} />
          </button>
        )}
        <button
          className="pos-icon danger"
          disabled={busy}
          onClick={() => void run(() => deletePosition(position.id))}
          aria-label="Удалить позицию"
        >
          <Trash2 size={15} />
        </button>
      </div>
      {error && <p className="pos-error">{error}</p>}
    </div>
  );
}

/** Records a buy. The gift is picked from the catalog rather than typed, so a
 *  position always points at something we can actually price. */
function AddPosition({ onCreated }: { onCreated: () => void }) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<GiftCard[]>([]);
  const [gift, setGift] = useState<GiftCard | null>(null);
  const [price, setPrice] = useState("");
  const [quantity, setQuantity] = useState("1");
  const [venue, setVenue] = useState(VENUES[0]);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (gift || query.trim().length < 2) {
      setResults([]);
      return;
    }
    const timer = setTimeout(() => {
      void getGifts({ search: query.trim(), pageSize: 6 })
        .then(page => setResults(page.items))
        .catch(() => setResults([]));
    }, 300);
    return () => clearTimeout(timer);
  }, [query, gift]);

  const pick = (item: GiftCard) => {
    setGift(item);
    setQuery(item.name ?? item.model ?? item.canonical_id.slice(0, 18));
    setResults([]);
    // The floor is the most likely price paid, and it stays editable.
    if (!price && item.floor_ton) setPrice(item.floor_ton);
    if (item.best_marketplace) setVenue(item.best_marketplace);
  };

  const submit = async () => {
    if (!gift || !price) return;
    setBusy(true);
    setError(null);
    try {
      await openPosition({
        gift_id: gift.id,
        buy_price_ton: price,
        marketplace: venue,
        quantity: Number(quantity) || 1,
        note: note.trim() || undefined,
      });
      onCreated();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось записать покупку");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="pos-form">
      <div className="pos-search">
        <input
          placeholder="Найти подарок в каталоге"
          value={query}
          onChange={event => {
            setQuery(event.target.value);
            setGift(null);
          }}
        />
        {results.length > 0 && (
          <div className="pos-results">
            {results.map(item => (
              <button key={item.id} onClick={() => pick(item)}>
                <span className="pos-result-media">
                  <GiftImage src={item.image_url} alt={item.name ?? "gift"} />
                </span>
                <span>
                  <strong>{item.name ?? item.canonical_id.slice(0, 18)}</strong>
                  <small>
                    {[item.model, item.floor_ton ? `floor ${formatTon(item.floor_ton)}` : "нет лотов"]
                      .filter(Boolean)
                      .join(" · ")}
                  </small>
                </span>
              </button>
            ))}
          </div>
        )}
      </div>
      <div className="pos-fields">
        <label>
          <span>Цена покупки, TON</span>
          <input
            type="number"
            min="0"
            step="0.01"
            value={price}
            onChange={event => setPrice(event.target.value)}
            placeholder="0"
          />
        </label>
        <label>
          <span>Количество</span>
          <input
            type="number"
            min="1"
            step="1"
            value={quantity}
            onChange={event => setQuantity(event.target.value)}
          />
        </label>
        <label>
          <span>Площадка</span>
          <select value={venue} onChange={event => setVenue(event.target.value)}>
            {VENUES.map(item => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </label>
        <label className="pos-note-field">
          <span>Заметка</span>
          <input value={note} onChange={event => setNote(event.target.value)} placeholder="необязательно" />
        </label>
      </div>
      {error && <p className="pos-error">{error}</p>}
      <div className="pos-form-actions">
        <button className="outline-btn" disabled={!gift || !price || busy} onClick={() => void submit()}>
          {busy ? "Сохраняю..." : "Записать"}
        </button>
        {!gift && <small>Сначала выберите подарок из каталога.</small>}
      </div>
    </div>
  );
}
