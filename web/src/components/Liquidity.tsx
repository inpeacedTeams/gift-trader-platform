import { useEffect, useState } from "react";
import { AlertTriangle, Timer } from "lucide-react";
import { getGiftLiquidity } from "../api";
import type { GiftLiquidity } from "../types";
import { formatCount, formatPercent } from "../format";
import "./liquidity.css";

const LABELS: Record<string, { text: string; tone: string }> = {
  fast: { text: "Быстро продаётся", tone: "liq-fast" },
  steady: { text: "Продаётся за пару дней", tone: "liq-steady" },
  slow: { text: "Продаётся долго", tone: "liq-slow" },
  unknown: { text: "Мало данных", tone: "liq-unknown" },
};

function humanHours(hours?: number | null): string {
  if (hours === null || hours === undefined) return "нет данных";
  if (hours < 1) return "меньше часа";
  if (hours < 48) return `${Math.round(hours)} ч`;
  return `${Math.round(hours / 24)} дн`;
}

/** Can this be sold again, and how fast.
 *
 * A discount only matters if there is an exit; without this a flipper is
 * guessing whether the money comes back this week or next month.
 */
export function Liquidity({ giftId }: { giftId: number }) {
  const [data, setData] = useState<GiftLiquidity | null>(null);

  useEffect(() => {
    let cancelled = false;
    void getGiftLiquidity(giftId)
      .then(result => {
        if (!cancelled) setData(result);
      })
      .catch(() => {
        if (!cancelled) setData(null);
      });
    return () => {
      cancelled = true;
    };
  }, [giftId]);

  if (!data) return null;

  const label = LABELS[data.label] ?? LABELS.unknown;
  const gap = data.floor_gap_percent === null || data.floor_gap_percent === undefined
    ? null
    : Number(data.floor_gap_percent);
  // A big jump to the second listing means the floor is one lone lot.
  const thinFloor = gap !== null && gap >= 25;

  return (
    <div className="liquidity-panel">
      <div className="liquidity-head">
        <Timer size={16} />
        <div>
          <strong>Ликвидность</strong>
          <small>Насколько легко выйти из позиции</small>
        </div>
        <span className={`liq-badge ${label.tone}`}>{label.text}</span>
      </div>
      <div className="liquidity-grid">
        <div>
          <span>Время на продажу</span>
          <b>{humanHours(data.median_hours_to_sell)}</b>
        </div>
        <div>
          <span>Продаж в неделю</span>
          <b>{data.sales_per_week ?? 0}</b>
        </div>
        <div>
          <span>Лотов в стакане</span>
          <b>{formatCount(data.active_depth)}</b>
        </div>
        <div>
          <span>Разрыв до второго</span>
          <b>{gap === null ? "n/a" : formatPercent(gap)}</b>
        </div>
      </div>
      {thinFloor && (
        <p className="liquidity-warning">
          <AlertTriangle size={13} /> Floor держится на одном лоте: следующий дороже на {formatPercent(gap)}.
          Перепродать по этой цене вряд ли выйдет.
        </p>
      )}
      {!data.confident && (
        <p className="muted-copy">
          Оценка приблизительная: пока мало закрытых лотов, чтобы считать честно.
        </p>
      )}
    </div>
  );
}
