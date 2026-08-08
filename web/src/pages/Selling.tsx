import { useEffect, useState } from "react";
import { AlertTriangle, ExternalLink, Plus, Store, Trash2 } from "lucide-react";
import {
  addSellerIdentity,
  getMyListings,
  removeSellerIdentity,
  type MyListing,
  type SellerIdentity,
  type SellingSummary,
} from "../api";
import { GiftImage } from "../components/GiftImage";
import { ErrorState, LoadingState } from "../components/State";
import { formatAgo, formatCount, formatTon } from "../format";
import "../selling.css";

type Props = { authenticated: boolean; onOpen?: (giftId: number) => void };

/** The market from behind your own listings.
 *
 * Tonnel and MRKT publish the seller as a Telegram user id, and sign in is
 * Telegram, so the lots on sale under this account are recognised without
 * the user setting anything up. Each row carries the cheapest comparable lot
 * that is not theirs, which is the only number that decides whether to move
 * the price.
 */
export function Selling({ authenticated, onOpen }: Props) {
  const [items, setItems] = useState<MyListing[]>([]);
  const [summary, setSummary] = useState<SellingSummary | null>(null);
  const [identities, setIdentities] = useState<SellerIdentity[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [handle, setHandle] = useState("");
  const [venue, setVenue] = useState("");
  const [onlyUndercut, setOnlyUndercut] = useState(false);

  const load = async () => {
    if (!authenticated) {
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const page = await getMyListings();
      setItems(page.items);
      setSummary(page.summary);
      setIdentities(page.identities);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось загрузить ваши лоты");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, [authenticated]);

  const addHandle = async () => {
    if (!handle.trim()) return;
    try {
      await addSellerIdentity(handle.trim(), venue.trim() || undefined);
      setHandle("");
      setVenue("");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось добавить продавца");
    }
  };

  if (!authenticated) {
    return (
      <section className="page-section">
        <p className="muted-copy">
          Войдите через Telegram. Площадки публикуют продавца как telegram id, по нему мы и находим ваши лоты.
        </p>
      </section>
    );
  }
  if (loading) return <LoadingState />;
  if (error && !items.length && !identities.length) {
    return <ErrorState detail={error} retry={() => void load()} />;
  }

  const visible = onlyUndercut ? items.filter(item => item.undercut) : items;

  return (
    <section className="page-section">
      {summary && (
        <div className="metric-grid">
          <div className="metric blue">
            <span>Лотов на продаже</span>
            <strong>{formatCount(summary.listed_count)}</strong>
            <small>найдено по вашим продавцам</small>
          </div>
          <div className="metric violet">
            <span>Ценник</span>
            <strong>{formatTon(summary.listed_value_ton)}</strong>
            <small>на руки {formatTon(summary.net_value_ton)} после комиссий</small>
          </div>
          <div className={summary.undercut_count ? "metric red" : "metric green"}>
            <span>Перебили</span>
            <strong>{formatCount(summary.undercut_count)}</strong>
            <small>{summary.undercut_count ? "есть лоты дешевле ваших" : "вы самый дешёвый"}</small>
          </div>
        </div>
      )}

      <div className="section-head">
        <div>
          <p className="eyebrow">MY LISTINGS</p>
          <h3>Ваши подарки на продаже</h3>
        </div>
        <button className="outline-btn" onClick={() => setOnlyUndercut(current => !current)}>
          {onlyUndercut ? "Показать все" : "Только перебитые"}
        </button>
      </div>

      {visible.length === 0 ? (
        <p className="muted-copy">
          {items.length === 0
            ? "Ни одного лота под вашим telegram id мы на рынке не нашли. Либо вы сейчас ничего не продаёте, либо площадка публикует продавца иначе: добавьте её ключ ниже."
            : "Ни один лот не перебит. Вы самый дешёвый в своих группах."}
        </p>
      ) : (
        <div className="table-card">
          {visible.map(item => (
            <div className={item.undercut ? "selling-row undercut" : "selling-row"} key={item.listing_id}>
              <button className="gift-cell" onClick={() => onOpen?.(item.gift_id)}>
                <GiftImage src={item.image_url} alt={item.name ?? "gift"} className="tiny" />
                <div>
                  <strong>
                    {item.name ?? `Gift #${item.gift_id}`}
                    {item.gift_number ? ` #${item.gift_number}` : ""}
                  </strong>
                  <small>
                    {item.model ?? item.collection_name ?? ""} · выставлен {formatAgo(item.listed_at)}
                  </small>
                </div>
              </button>
              <div>
                <b>{formatTon(item.price_ton)}</b>
                <small>ваша цена · {item.marketplace}</small>
              </div>
              <div>
                <b>{item.rival_price_ton ? formatTon(item.rival_price_ton) : "нет конкурентов"}</b>
                <small>
                  {item.rival_price_ton
                    ? `дешевле всех · ${item.rival_marketplace}`
                    : "похожих лотов нет"}
                </small>
              </div>
              <div className="edge">
                {item.undercut ? (
                  <>
                    <strong className="loss">-{Number(item.undercut_percent).toFixed(1)}%</strong>
                    <small>вас перебили</small>
                  </>
                ) : (
                  <>
                    <strong className="profit">лучший</strong>
                    <small>{formatCount(item.competitors)} рядом</small>
                  </>
                )}
              </div>
              <div className="selling-actions">
                {item.undercut && item.rival_url && (
                  <a className="outline-btn" href={item.rival_url} target="_blank" rel="noreferrer">
                    <AlertTriangle size={13} /> Конкурент
                  </a>
                )}
                {item.url && (
                  <a className="outline-btn" href={item.url} target="_blank" rel="noreferrer">
                    Мой лот <ExternalLink size={13} />
                  </a>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="section-head">
        <div>
          <p className="eyebrow">SELLER IDS</p>
          <h3>Как мы узнаём ваши лоты</h3>
        </div>
      </div>
      <div className="identity-card">
        <ul className="identity-list">
          {identities.map(identity => (
            <li key={identity.id}>
              <Store size={13} />
              <span>
                <strong>{identity.seller}</strong>
                <small>
                  {identity.marketplace ?? "все площадки"} ·{" "}
                  {identity.source === "telegram" ? "из вашего Telegram" : "добавлено вручную"}
                </small>
              </span>
              {identity.source !== "telegram" && (
                <button
                  className="icon-btn"
                  aria-label="Удалить продавца"
                  onClick={() => void removeSellerIdentity(identity.id).then(load)}
                >
                  <Trash2 size={14} />
                </button>
              )}
            </li>
          ))}
        </ul>
        <div className="identity-form">
          <input
            value={handle}
            onChange={event => setHandle(event.target.value)}
            placeholder="id или ник продавца"
          />
          <input
            value={venue}
            onChange={event => setVenue(event.target.value)}
            placeholder="площадка (необязательно)"
          />
          <button className="primary-btn" disabled={!handle.trim()} onClick={() => void addHandle()}>
            <Plus size={14} /> Добавить
          </button>
        </div>
        <p className="muted-copy">
          Telegram id подставлен автоматически: Tonnel и MRKT публикуют владельца именно так. Ручные записи мы
          проверить не можем, поэтому они помечены отдельно.
        </p>
      </div>
      {error && <p className="muted-copy">{error}</p>}
    </section>
  );
}
