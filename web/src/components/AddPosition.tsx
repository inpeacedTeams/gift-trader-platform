import { FormEvent, useState } from "react";
import { Check, LoaderCircle, Plus } from "lucide-react";
import { createPosition } from "../api";
import "../positions.css";

/** Record a buy without retyping it.
 *
 * The price a flipper just paid is almost always the floor they were looking
 * at a second ago, so it is prefilled. Everything else is optional.
 */
export function AddPosition({
  giftId,
  floorTon,
  venues,
  authenticated,
}: {
  giftId: number;
  floorTon?: string | number | null;
  venues: string[];
  authenticated: boolean;
}) {
  const [price, setPrice] = useState(floorTon ? String(floorTon) : "");
  const [venue, setVenue] = useState(venues[0] ?? "");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!authenticated) return null;

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!price.trim()) return;
    setSaving(true);
    try {
      await createPosition({
        gift_id: giftId,
        buy_price_ton: price.trim(),
        buy_marketplace: venue.trim() || undefined,
      });
      setSaved(true);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось записать покупку");
    } finally {
      setSaving(false);
    }
  };

  return (
    <form className="position-add" onSubmit={submit}>
      <div className="position-add-head">
        <strong>Записал покупку</strong>
        <small>Попадёт в «Мои позиции» и будет переоцениваться по текущему floor.</small>
      </div>
      <label>
        Цена покупки, TON
        <input
          type="number"
          min="0"
          step="any"
          value={price}
          onChange={event => setPrice(event.target.value)}
          placeholder="900"
        />
      </label>
      <label>
        Площадка
        <input value={venue} onChange={event => setVenue(event.target.value)} placeholder="tonnel" />
      </label>
      <button className="outline-btn" disabled={saving || saved}>
        {saving ? (
          <LoaderCircle className="spin" size={15} />
        ) : saved ? (
          <Check size={15} />
        ) : (
          <Plus size={15} />
        )}
        {saved ? "В позициях" : "Записать"}
      </button>
      {error && <div className="notice error">{error}</div>}
    </form>
  );
}
