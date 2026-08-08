import { FormEvent, useEffect, useState } from "react";
import { Briefcase, Check, LoaderCircle, RotateCcw, Trash2, X } from "lucide-react";
import {
  deletePosition,
  getPositions,
  updatePosition,
  type Position,
  type PositionSummary,
} from "../api";
import { EmptyState, LoadingState } from "../components/State";
import { GiftImage } from "../components/GiftImage";
import { formatCount, formatPercent, formatTon, formatTonDelta } from "../format";
import "../positions.css";

/** The flipper's own book.
 *
 * The rest of the product prices the market; this prices the user. Open lots
 * are marked against the live floor minus the venue fee and the gas already
 * spent, so the number on screen is money that would actually arrive.
 */
export function Positions({
  authenticated,
  onOpen,
}: {
  authenticated: boolean;
  onOpen: (giftId: number) => void;
}) {
  const [items, setItems] = useState<Position[]>([]);
  const [summary, setSummary] = useState<PositionSummary | null>(null);
  const [includeClosed, setIncludeClosed] = useState(true);
  const [closingId, setClosingId] = useState<number | null>(null);
  const [sellPrice, setSellPrice] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    if (!authenticated) {
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const book = await getPositions(includeClosed);
      setItems(book.items);
      setSummary(book.summary);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось загрузить позиции");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, [authenticated, includeClosed]);

  const close = async (event: FormEvent, position: Position) => {
    event.preventDefault();
    if (!sellPrice.trim()) return;
    setBusy(true);
    try {
      await updatePosition(position.id, { sell_price_ton: sellPrice.trim() });
      setClosingId(null);
      setSellPrice("");
      // Totals and the win rate move with every close, so re-read the book.
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось закрыть позицию");
    } finally {
      setBusy(false);
    }
  };

  const reopen = async (position: Position) => {
    setBusy(true);
    try {
      await updatePosition(position.id, { reopen: true });
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось вернуть позицию");
    } finally {
      setBusy(false);
    }
  };

  const remove = async (position: Position) => {
    setItems(current => current.filter(item => item.id !== position.id));
    await deletePosition(position.id).catch(() => undefined);
    await load();
  };

  const title = (position: Position): string => {
    const name = position.name ?? position.model ?? `Gift #${position.gift_id}`;
    return position.gift_number ? `${name} #${position.gift_number}` : name;
  };

  const entry = (position: Position): string => {
    const parts = [formatTon(position.buy_price_ton)];
    if (position.buy_marketplace) parts.push(position.buy_marketplace);
    parts.push(position.is_open ? `${formatCount(position.days_held)} дн. в позиции` : `держал ${formatCount(position.days_held)} дн.`);
    return parts.join(" · ");
  };

  if (!authenticated) {
    return (
      <section className="page-section">
        <p className="muted-copy">Войдите через Telegram, чтобы вести свои позиции.</p>
      </section>
    );
  }

  return (
    <section className="page-section">
      <div className="section-head">
        <div>
          <p className="eyebrow">YOUR BOOK</p>
          <h2>Мои позиции</h2>
        </div>
        <span className="fresh">
          <i /> {formatCount(summary?.open_count ?? 0)} открытых
        </span>
      </div>
      <div className="alert-setup">
        <Briefcase size={24} />
        <div>
          <h3>Сколько ты реально заработал</h3>
          <p>
            Открытые лоты оцениваются по текущему floor за вычетом комиссии площадки и газа: это
            деньги, которые дойдут до кошелька, а не цена в объявлении. Закрытые дают винрейт.
          </p>
        </div>
      </div>
      {error && <div className="notice error">{error}</div>}
      {summary && (
        <div className="position-summary">
          <div>
            <span>Вложено</span>
            <strong>{formatTon(summary.invested_ton)}</strong>
            <small>{formatCount(summary.open_count)} открытых лотов</small>
          </div>
          <div>
            <span>Сейчас стоит</span>
            <strong>{formatTon(summary.market_value_ton)}</strong>
            <small>
              {summary.unvalued_count
                ? `${formatCount(summary.unvalued_count)} без цены, вне итогов`
                : "чистыми после комиссий"}
            </small>
          </div>
          <div>
            <span>Нереализованный P&L</span>
            <strong className={Number(summary.unrealized_ton) >= 0 ? "trend-up" : "trend-down"}>
              {formatTonDelta(summary.unrealized_ton)}
            </strong>
            <small>{formatPercent(summary.unrealized_percent) ?? "нет оценки"}</small>
          </div>
          <div>
            <span>Реализованный P&L</span>
            <strong className={Number(summary.realized_ton) >= 0 ? "trend-up" : "trend-down"}>
              {formatTonDelta(summary.realized_ton)}
            </strong>
            <small>{formatCount(summary.closed_count)} закрытых сделок</small>
          </div>
          <div>
            <span>Винрейт</span>
            <strong>
              {summary.win_rate_percent === null || summary.win_rate_percent === undefined
                ? "--"
                : `${Number(summary.win_rate_percent).toFixed(0)}%`}
            </strong>
            <small>по закрытым в плюс</small>
          </div>
        </div>
      )}
      <div className="position-toolbar">
        <button className="outline-btn" onClick={() => setIncludeClosed(value => !value)}>
          {includeClosed ? "Только открытые" : "Показать закрытые"}
        </button>
      </div>
      {loading ? (
        <LoadingState />
      ) : items.length ? (
        <div className="table-card">
          {items.map(position => (
            <div className={`position-row ${position.is_open ? "" : "closed"}`} key={position.id}>
              <GiftImage src={position.image_url} alt={title(position)} />
              <button className="position-name" onClick={() => onOpen(position.gift_id)}>
                <strong>{title(position)}</strong>
                <small>{entry(position)}</small>
              </button>
              <div className="position-col">
                <b>
                  {position.is_open
                    ? position.valued
                      ? formatTon(position.net_value_ton)
                      : "нет цены"
                    : formatTon(position.sell_price_ton)}
                </b>
                <small>
                  {position.is_open
                    ? position.valued
                      ? `floor ${formatTon(position.floor_ton)} минус ${Number(position.exit_fee_percent)}%`
                      : "ни одного активного лота"
                    : `продано${position.sell_marketplace ? ` на ${position.sell_marketplace}` : ""}`}
                </small>
              </div>
              <div className="position-col">
                {position.profit_ton === null || position.profit_ton === undefined ? (
                  <span className="tag-unvalued">без оценки</span>
                ) : (
                  <>
                    <b className={Number(position.profit_ton) >= 0 ? "trend-up" : "trend-down"}>
                      {formatTonDelta(position.profit_ton)}
                    </b>
                    <small>{formatPercent(position.profit_percent) ?? ""}</small>
                  </>
                )}
              </div>
              <div className="position-actions">
                {position.is_open ? (
                  closingId === position.id ? (
                    <form className="position-close-form" onSubmit={event => void close(event, position)}>
                      <input
                        type="number"
                        min="0"
                        step="any"
                        autoFocus
                        value={sellPrice}
                        onChange={event => setSellPrice(event.target.value)}
                        placeholder="Цена продажи"
                      />
                      <button className="outline-btn" disabled={busy}>
                        {busy ? <LoaderCircle className="spin" size={14} /> : <Check size={14} />}
                      </button>
                      <button
                        type="button"
                        className="icon-btn"
                        aria-label="Отмена"
                        onClick={() => setClosingId(null)}
                      >
                        <X size={14} />
                      </button>
                    </form>
                  ) : (
                    <button
                      className="outline-btn"
                      onClick={() => {
                        setClosingId(position.id);
                        setSellPrice(position.net_value_ton ?? "");
                      }}
                    >
                      Продал
                    </button>
                  )
                ) : (
                  <button
                    className="icon-btn"
                    aria-label="Вернуть в открытые"
                    disabled={busy}
                    onClick={() => void reopen(position)}
                  >
                    <RotateCcw size={15} />
                  </button>
                )}
                <button className="icon-btn" aria-label="Удалить" onClick={() => void remove(position)}>
                  <Trash2 size={15} />
                </button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <EmptyState
          title="Позиций пока нет"
          detail="Открой карточку подарка и нажми «Записал покупку»: цена подставится из текущего floor."
        />
      )}
    </section>
  );
}
