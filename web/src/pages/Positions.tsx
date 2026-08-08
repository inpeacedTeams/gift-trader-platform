import { useEffect, useState } from "react";
import { Check, RotateCcw, Trash2 } from "lucide-react";
import {
  closePosition,
  deletePosition,
  getPositions,
  reopenPosition,
  type PositionCard,
  type PositionSummary,
} from "../api";
import { ErrorState, LoadingState } from "../components/State";
import { GiftImage } from "../components/GiftImage";
import { formatAgo, formatPercent, formatTon, formatTonDelta } from "../format";
import "../positions.css";

type Props = { authenticated: boolean; onOpen: (giftId: number) => void };

function tone(value?: string | null): string | undefined {
  if (value === null || value === undefined) return undefined;
  return Number(value) >= 0 ? "profit" : "loss";
}

/** The user's own book.
 *
 * Everything else in the app answers "what is the market doing". This answers
 * "am I actually making money", which is the only question that settles an
 * argument about a strategy. Closed trades stay so the win rate is counted,
 * not remembered.
 */
export function Positions({ authenticated, onOpen }: Props) {
  const [items, setItems] = useState<PositionCard[]>([]);
  const [summary, setSummary] = useState<PositionSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [exits, setExits] = useState<Record<number, string>>({});

  const load = async () => {
    setLoading(true);
    try {
      const result = await getPositions(true);
      setItems(result.items);
      setSummary(result.summary);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Positions unavailable");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (authenticated) void load();
    else setLoading(false);
  }, [authenticated]);

  if (!authenticated) {
    return (
      <section className="page-section">
        <p className="muted-copy">Позиции привязаны к аккаунту: войдите через Telegram, чтобы вести свой журнал сделок.</p>
      </section>
    );
  }
  if (loading) return <LoadingState />;
  if (error) return <ErrorState detail={error} retry={() => void load()} />;

  const open = items.filter(item => item.is_open);
  const closed = items.filter(item => !item.is_open);

  const close = async (position: PositionCard) => {
    const price = exits[position.id];
    if (!price || !Number.isFinite(Number(price)) || Number(price) <= 0) return;
    await closePosition(position.id, {
      sell_price_ton: price,
      ...(position.exit_venue ? { sell_marketplace: position.exit_venue } : {}),
    });
    setExits(current => ({ ...current, [position.id]: "" }));
    await load();
  };

  const row = (position: PositionCard) => (
    <div className={position.is_open ? "pos-row" : "pos-row closed"} key={position.id}>
      <div className="pos-title">
        <GiftImage src={position.image_url} alt={position.name ?? "gift"} />
        <div>
          <button onClick={() => onOpen(position.gift_id)}>
            {position.name ?? `Gift #${position.gift_id}`}
            {position.gift_number ? ` #${position.gift_number}` : ""}
          </button>
          <small>
            {position.quantity > 1 ? `${position.quantity} шт · ` : ""}
            куплено {formatAgo(position.opened_at)}
            {position.marketplace ? ` · ${position.marketplace}` : ""}
          </small>
        </div>
      </div>
      <div>
        <b>{formatTon(position.buy_price_ton)}</b>
        <small>покупка</small>
      </div>
      <div>
        <b>{position.is_open ? formatTon(position.floor_ton) : formatTon(position.sell_price_ton)}</b>
        <small>{position.is_open ? "floor сейчас" : "продано"}</small>
      </div>
      <div>
        <b className={tone(position.profit_ton)}>
          {position.profit_ton === null || position.profit_ton === undefined
            ? "--"
            : formatTonDelta(position.profit_ton)}
        </b>
        <small>
          {position.roi_percent === null || position.roi_percent === undefined
            ? position.is_open
              ? "нет активных лотов"
              : "без оценки"
            : `${formatPercent(position.roi_percent)} после комиссий`}
        </small>
      </div>
      <div className="pos-actions">
        {position.is_open ? (
          <>
            <input
              inputMode="decimal"
              placeholder="продал за"
              value={exits[position.id] ?? ""}
              onChange={event =>
                setExits(current => ({ ...current, [position.id]: event.target.value }))
              }
            />
            <button className="pos-ghost" title="Закрыть позицию" onClick={() => void close(position)}>
              <Check size={14} />
            </button>
          </>
        ) : (
          <button
            className="pos-ghost"
            title="Вернуть в открытые"
            onClick={() => void reopenPosition(position.id).then(load)}
          >
            <RotateCcw size={14} />
          </button>
        )}
        <button
          className="pos-ghost danger"
          title="Удалить"
          onClick={() => void deletePosition(position.id).then(load)}
        >
          <Trash2 size={14} />
        </button>
      </div>
    </div>
  );

  return (
    <section className="page-section">
      {summary && (
        <div className="pos-summary">
          <div className="pos-tile">
            <span>Вложено</span>
            <strong>{formatTon(summary.invested_ton)}</strong>
            <small>{summary.open_count} открытых позиций</small>
          </div>
          <div className="pos-tile">
            <span>Сейчас стоит</span>
            <strong>{formatTon(summary.market_value_ton)}</strong>
            <small>
              {summary.unpriced_count > 0
                ? `${summary.unpriced_count} без активных лотов`
                : "по floor за вычетом комиссий"}
            </small>
          </div>
          <div className="pos-tile">
            <span>Бумажный P&L</span>
            <strong className={tone(summary.unrealized_ton)}>{formatTonDelta(summary.unrealized_ton)}</strong>
            <small>если продать прямо сейчас</small>
          </div>
          <div className="pos-tile">
            <span>Зафиксировано</span>
            <strong className={tone(summary.realized_ton)}>{formatTonDelta(summary.realized_ton)}</strong>
            <small>{summary.closed_count} закрытых сделок</small>
          </div>
          <div className="pos-tile">
            <span>Винрейт</span>
            <strong>
              {summary.win_rate_percent === null || summary.win_rate_percent === undefined
                ? "--"
                : `${Math.round(Number(summary.win_rate_percent))}%`}
            </strong>
            <small>{summary.wins} в плюс из {summary.closed_count}</small>
          </div>
        </div>
      )}
      <div className="section-head">
        <div>
          <p className="eyebrow">OPEN BOOK</p>
          <h3>Открытые позиции</h3>
        </div>
        <span className="fresh">{open.length}</span>
      </div>
      <div className="table-card">
        {open.length ? (
          open.map(row)
        ) : (
          <p className="muted-copy" style={{ padding: 20 }}>
            Пока пусто. Купил подарок — нажми «Записать покупку» на его странице, и он появится здесь с живым
            P&L.
          </p>
        )}
      </div>
      {closed.length > 0 && (
        <>
          <div className="section-head">
            <div>
              <p className="eyebrow">HISTORY</p>
              <h3>Закрытые сделки</h3>
            </div>
            <span className="fresh">{closed.length}</span>
          </div>
          <div className="table-card">{closed.map(row)}</div>
        </>
      )}
    </section>
  );
}
