import { useState } from "react";
import { BadgeCheck, Briefcase } from "lucide-react";
import { openPosition } from "../api";
import "../positions.css";

type Props = {
  giftId: number;
  floorTon?: string | null;
  venue?: string | null;
  authenticated?: boolean;
};

/** Record a purchase where the purchase is decided.
 *
 * The price paid is the one fact the market cannot recover later, and a form
 * on another screen is a form nobody fills in. Prefilled with the floor and
 * the venue it trades on, both editable, because the fill is rarely exactly
 * the number on the card.
 */
export function LogBuy({ giftId, floorTon, venue, authenticated = false }: Props) {
  const [open, setOpen] = useState(false);
  const [price, setPrice] = useState(floorTon ? String(Number(floorTon)) : "");
  const [market, setMarket] = useState(venue ?? "");
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  if (!authenticated) return null;

  const submit = async () => {
    if (!price) return;
    setSaving(true);
    try {
      await openPosition({
        gift_id: giftId,
        buy_price_ton: price,
        ...(market ? { marketplace: market } : {}),
      });
      setSaved(true);
      setOpen(false);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось записать покупку");
    } finally {
      setSaving(false);
    }
  };

  if (saved) {
    return (
      <p className="log-buy done">
        <BadgeCheck size={14} /> Позиция открыта. P&amp;L считается на вкладке Positions.
      </p>
    );
  }

  return (
    <div className="log-buy">
      {open ? (
        <>
          <input
            inputMode="decimal"
            value={price}
            onChange={event => setPrice(event.target.value)}
            placeholder="цена покупки, TON"
          />
          <input value={market} onChange={event => setMarket(event.target.value)} placeholder="площадка" />
          <button className="primary-btn" disabled={!price || saving} onClick={() => void submit()}>
            Сохранить
          </button>
          <button className="outline-btn" onClick={() => setOpen(false)}>
            Отмена
          </button>
        </>
      ) : (
        <button className="outline-btn" onClick={() => setOpen(true)}>
          <Briefcase size={13} /> Записать покупку
        </button>
      )}
      {error && <small className="log-buy-error">{error}</small>}
    </div>
  );
}
