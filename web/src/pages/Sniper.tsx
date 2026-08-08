import { FormEvent, useEffect, useState } from "react";
import { Crosshair, LoaderCircle, Pause, Play, Plus, Trash2 } from "lucide-react";
import { createWatch, deleteWatch, getWatches, toggleWatch, type SniperWatch } from "../api";
import { EmptyState, LoadingState } from "../components/State";
import { formatCount, formatTon } from "../format";
import "../components/liquidity.css";

/** Standing orders for the fast loop.
 *
 * The five minute crawl cannot catch a mispriced lot: it is bought before a
 * full pass ends. These watches drive a much shorter poll.
 */
export function Sniper({ authenticated }: { authenticated: boolean }) {
  const [items, setItems] = useState<SniperWatch[]>([]);
  const [giftName, setGiftName] = useState("");
  const [maxPrice, setMaxPrice] = useState("");
  const [minDiscount, setMinDiscount] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    if (!authenticated) {
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      setItems((await getWatches()).items);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось загрузить правила");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, [authenticated]);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setSaving(true);
    try {
      const created = await createWatch({
        gift_name: giftName.trim() || undefined,
        max_price_ton: maxPrice.trim() || undefined,
        min_discount_percent: minDiscount.trim() || undefined,
      });
      setItems(current => [created, ...current]);
      setGiftName("");
      setMaxPrice("");
      setMinDiscount("");
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось создать правило");
    } finally {
      setSaving(false);
    }
  };

  const remove = async (id: number) => {
    setItems(current => current.filter(item => item.id !== id));
    await deleteWatch(id).catch(() => void load());
  };

  const flip = async (watch: SniperWatch) => {
    const updated = await toggleWatch(watch.id, !watch.is_active).catch(() => null);
    if (updated) setItems(current => current.map(item => (item.id === watch.id ? updated : item)));
  };

  const describe = (watch: SniperWatch): string => {
    const parts: string[] = [];
    if (watch.gift_name) parts.push(watch.gift_name);
    if (watch.model) parts.push(watch.model);
    return parts.join(" · ") || "Любой подарок";
  };

  const conditions = (watch: SniperWatch): string => {
    const parts: string[] = [];
    if (watch.max_price_ton) parts.push(`дешевле ${formatTon(watch.max_price_ton)}`);
    if (watch.min_discount_percent) parts.push(`скидка от ${watch.min_discount_percent}%`);
    if (watch.marketplace) parts.push(watch.marketplace);
    return parts.join(", ") || "без условий";
  };

  return (
    <section className="page-section">
      <div className="section-head">
        <div>
          <p className="eyebrow">FAST LANE</p>
          <h2>Снайпер</h2>
        </div>
        <span className="fresh">{formatCount(items.filter(item => item.is_active).length)} активных</span>
      </div>
      <div className="alert-setup">
        <Crosshair size={24} />
        <div>
          <h3>Ловит недооценённые лоты за секунды</h3>
          <p>
            Проверяет самые дешёвые лоты каждые 20 секунд и присылает уведомление, пока лот ещё висит.
            Обычный обход рынка для этого слишком медленный.
          </p>
        </div>
      </div>
      {!authenticated ? (
        <p className="muted-copy">Войдите через Telegram, чтобы создавать правила.</p>
      ) : (
        <>
          {error && <div className="notice error">{error}</div>}
          <form className="alert-form" onSubmit={submit}>
            <label>
              Подарок
              <input value={giftName} onChange={e => setGiftName(e.target.value)} placeholder="Plush Pepe" />
            </label>
            <label>
              Дешевле, TON
              <input
                type="number"
                min="0"
                step="any"
                value={maxPrice}
                onChange={e => setMaxPrice(e.target.value)}
                placeholder="900"
              />
            </label>
            <label>
              Скидка от, %
              <input
                type="number"
                min="0"
                max="99"
                value={minDiscount}
                onChange={e => setMinDiscount(e.target.value)}
                placeholder="15"
              />
            </label>
            <button className="outline-btn" disabled={saving}>
              {saving ? <LoaderCircle className="spin" size={15} /> : <Plus size={15} />} Создать
            </button>
          </form>
          {loading ? (
            <LoadingState />
          ) : items.length ? (
            <div className="alert-list stagger">
              {items.map(watch => (
                <div className={`alert-row ${watch.is_active ? "" : "paused"}`} key={watch.id}>
                  <button
                    className="status-toggle"
                    aria-label={watch.is_active ? "Пауза" : "Возобновить"}
                    onClick={() => void flip(watch)}
                  >
                    {watch.is_active ? <Pause size={11} /> : <Play size={11} />}
                  </button>
                  <div>
                    <strong>{describe(watch)}</strong>
                    <small>
                      {conditions(watch)} · сработало {formatCount(watch.hits)}
                    </small>
                  </div>
                  <button className="icon-btn" aria-label="Удалить" onClick={() => void remove(watch.id)}>
                    <Trash2 size={15} />
                  </button>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState
              title="Правил пока нет"
              detail="Например: Plush Pepe дешевле 900 TON, или любая позиция со скидкой от 20%."
            />
          )}
        </>
      )}
    </section>
  );
}
