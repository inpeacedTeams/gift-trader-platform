import { useEffect, useState } from "react";
import { Briefcase, Check, Plus, Trash2, Undo2 } from "lucide-react";
import {
  closePosition,
  createPosition,
  deletePosition,
  getGifts,
  getPositions,
  reopenPosition,
  type Position,
  type PositionSummary,
} from "../api";
import type { GiftCard } from "../types";
import { GiftImage } from "../components/GiftImage";
import { ErrorState, LoadingState } from "../components/State";
import { formatPercent, formatTon, formatTonDelta } from "../format";
import "../positions.css";

type Props = { authenticated: boolean; onOpenGift?: (giftId: number) => void };

function tone(value?: string | null): string {
  if (value === null || value === undefined) return "";
  return Number(value) >= 0 ? "profit" : "loss";
}

/** What the market is doing to you, rather than what it is doing.
 *
 * Cost basis includes the gas already spent, and the current value is what a
 * sale would actually pay after the venue's cut. Anything we cannot price is
 * labelled as such and kept out of the totals.
 */
export function Positions({ authenticated, onOpenGift }: Props) {
  const [items, setItems] = useState<Position[]>([]);
  const [summary, setSummary] = useState<PositionSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [includeClosed, setIncludeClosed] = useState(true);

  const [search, setSearch] = useState("");
  const [results, setResults] = useState<GiftCard[]>([]);
  const [picked, setPicked] = useState<GiftCard | null>(null);
  const [buyPrice, setBuyPrice] = useState("");
  const [venue, setVenue] = useState("");
  const [saving, setSaving] = useState(false);

  const [closingId, setClosingId] = useState<number | null>(null);
  const [sellPrice, setSellPrice] = useState("");

  const load = async () => {
    if (!authenticated) {
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const page = await getPositions(includeClosed);
      setItems(page.items);
      setSummary(page.summary);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Позиции недоступны");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, [authenticated, includeClosed]);

  // Search the catalog rather than asking the user to remember an id.
  useEffect(() => {
    if (search.trim().length < 2) {
      setResults([]);
      return;
    }
    let cancelled = false;
    const timer = window.setTimeout(() => {
      void getGifts({ search: search.trim(), pageSize: 6 })
        .then(page => {
          if (!cancelled) setResults(page.items);
        })
        .catch(() => {
          if (!cancelled) setResults([]);
        });
    }, 250);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [search]);

  const pick = (gift: GiftCard) => {
    setPicked(gift);
    setResults([]);
    setSearch(gift.name ?? `Gift #${gift.id}`);
    if (gift.floor_ton) setBuyPrice(String(Number(gift.floor_ton)));
    if (gift.best_marketplace) setVenue(gift.best_marketplace);
  };

  const submit = async () => {
    if (!picked || !buyPrice) return;
    setSaving(true);
    try {
      await createPosition({
        gift_id: picked.id,
        buy_price_ton: buyPrice,
        ...(venue ? { buy_marketplace: venue } : {}),
      });
      setPicked(null);
      setSearch("");
      setBuyPrice("");
      setVenue("");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось добавить позицию");
    } finally {
      setSaving(false);
    }
  };

  const close = async (position: Position) => {
    if (!sellPrice) return;
    try {
      await closePosition(position.id, {
        sell_price_ton: sellPrice,
        ...(position.exit_marketplace ? { sell_marketplace: position.exit_marketplace } : {}),
      });
      setClosingId(null);
      setSellPrice("");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось закрыть позицию");
    }
  };

  if (!authenticated) {
    return (
      <section className="page-section">
        <p className="muted-copy">
          Войдите через Telegram, чтобы вести позиции: цену входа знаете только вы, из рынка её не достать.
        </p>
      </section>
    );
  }
  if (loading) return <LoadingState />;
  if (error && !items.length) return <ErrorState detail={error} retry={() => void load()} />;

  return (
    <section className="page-section">
      {summary && (
        <div className="metric-grid">
          <div className="metric blue">
            <span>Вложено</span>
            <strong>{formatTon(summary.invested_ton)}</strong>
            <small>{summary.open_count} открытых лотов</small>
          </div>
          <div className="metric violet">
            <span>Сейчас на руки</span>
            <strong>{formatTon(summary.market_value_ton)}</strong>
            <small>после комиссии площадки</small>
          </div>
          <div className={`metric ${Number(summary.unrealized_ton) >= 0 ? "green" : "red"}`}>
            <span>Нереализованный P&amp;L</span>
            <strong className={tone(summary.unrealized_ton)}>{formatTonDelta(summary.unrealized_ton)}</strong>
            <small>{summary.unrealized_percent ? formatPercent(summary.unrealized_percent) : "нет оценки"}</small>
          </div>
          <div className="metric green">
            <span>Зафиксировано</span>
            <strong className={tone(summary.realized_ton)}>{formatTonDelta(summary.realized_ton)}</strong>
            <small>
              {summary.closed_count} сделок
              {summary.win_rate_percent ? ` · ${Number(summary.win_rate_percent).toFixed(0)}% в плюс` : ""}
            </small>
          </div>
        </div>
      )}
      {summary && summary.unvalued_count > 0 && (
        <p className="muted-copy">
          {summary.unvalued_count} позиций без активных лотов на рынке: оценить их нечем, поэтому в суммы они не входят.
        </p>
      )}

      <div className="position-form">
        <div className="pos-search">
          <label>
            <span>Подарок</span>
            <input
              value={search}
              onChange={event => {
                setSearch(event.target.value);
                setPicked(null);
              }}
              placeholder="Начните вводить название"
            />
          </label>
          {results.length > 0 && (
            <ul className="pos-results">
              {results.map(gift => (
                <li key={gift.id}>
                  <button type="button" onClick={() => pick(gift)}>
                    <GiftImage src={gift.image_url} alt={gift.name ?? "gift"} className="tiny" />
                    <span>
                      <strong>{gift.name ?? `Gift #${gift.id}`}</strong>
                      <small>
                        {gift.model ?? "без модели"} · floor {formatTon(gift.floor_ton)}
                      </small>
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
        <label>
          <span>Цена покупки, TON</span>
          <input inputMode="decimal" value={buyPrice} onChange={event => setBuyPrice(event.target.value)} placeholder="0" />
        </label>
        <label>
          <span>Площадка</span>
          <input value={venue} onChange={event => setVenue(event.target.value)} placeholder="tonnel" />
        </label>
        <button className="primary-btn" disabled={!picked || !buyPrice || saving} onClick={() => void submit()}>
          <Plus size={14} /> Добавить
        </button>
      </div>

      <div className="section-head">
        <div>
          <p className="eyebrow">PORTFOLIO</p>
          <h3>Мои позиции</h3>
        </div>
        <button className="outline-btn" onClick={() => setIncludeClosed(current => !current)}>
          {includeClosed ? "Только открытые" : "Показать закрытые"}
        </button>
      </div>

      {items.length === 0 ? (
        <p className="muted-copy">
          Пока пусто. Добавьте покупку, и продукт начнёт считать вашу прибыль, а не только цены рынка.
        </p>
      ) : (
        <div className="table-card">
          {items.map(position => (
            <div className={position.is_open ? "position-row" : "position-row closed"} key={position.id}>
              <button className="gift-cell" onClick={() => onOpenGift?.(position.gift_id)}>
                <GiftImage src={position.image_url} alt={position.name ?? "gift"} className="tiny" />
                <div>
                  <strong>
                    {position.name ?? `Gift #${position.gift_id}`}
                    {position.gift_number ? ` #${position.gift_number}` : ""}
                  </strong>
                  <small>
                    {position.model ?? position.collection_name ?? ""} · {position.days_held} дн в позиции
                  </small>
                </div>
              </button>
              <div>
                <b>{formatTon(position.buy_price_ton)}</b>
                <small>вход{position.buy_marketplace ? ` · ${position.buy_marketplace}` : ""}</small>
              </div>
              <div>
                <b>{position.valued ? formatTon(position.net_value_ton) : "нет цены"}</b>
                <small>
                  {position.is_open ? "на руки сейчас" : `продано ${formatTon(position.sell_price_ton)}`}
                </small>
              </div>
              <div className="edge">
                <strong className={tone(position.profit_ton)}>
                  {position.valued ? formatTonDelta(position.profit_ton) : "--"}
                </strong>
                <small>{position.valued ? formatPercent(position.profit_percent) : "не оценить"}</small>
              </div>
              <div className="position-actions">
                {position.is_open ? (
                  closingId === position.id ? (
                    <>
                      <input
                        inputMode="decimal"
                        value={sellPrice}
                        onChange={event => setSellPrice(event.target.value)}
                        placeholder="цена продажи"
                      />
                      <button className="outline-btn" onClick={() => void close(position)}>
                        <Check size={13} />
                      </button>
                    </>
                  ) : (
                    <button
                      className="outline-btn"
                      onClick={() => {
                        setClosingId(position.id);
                        setSellPrice(position.floor_ton ? String(Number(position.floor_ton)) : "");
                      }}
                    >
                      <Briefcase size={13} /> Закрыть
                    </button>
                  )
                ) : (
                  <button className="outline-btn" onClick={() => void reopenPosition(position.id).then(load)}>
                    <Undo2 size={13} />
                  </button>
                )}
                <button
                  className="icon-btn"
                  aria-label="Удалить позицию"
                  onClick={() => void deletePosition(position.id).then(load)}
                >
                  <Trash2 size={14} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
