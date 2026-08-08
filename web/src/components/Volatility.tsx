import { useEffect, useState } from "react";
import { Activity, TrendingDown } from "lucide-react";
import { getGiftVolatility, type GiftVolatility } from "../api";
import { formatCount, formatPercent, formatTon } from "../format";
import "./volatility.css";

const LABELS: Record<string, { text: string; tone: string; note: string }> = {
  calm: {
    text: "Спокойный",
    tone: "vol-calm",
    note: "Цена почти не двигается: floor можно считать реальной ценой.",
  },
  normal: {
    text: "Обычный",
    tone: "vol-normal",
    note: "Нормальные для рынка колебания. Floor держится в пределах дня.",
  },
  active: {
    text: "Активный",
    tone: "vol-active",
    note: "Заметно ходит. Заходить стоит с запасом по цене.",
  },
  wild: {
    text: "Дикий",
    tone: "vol-wild",
    note: "Цена скачет. Floor сейчас и floor через час это разные числа.",
  },
  unknown: {
    text: "Мало данных",
    tone: "vol-unknown",
    note: "Наблюдений пока мало, чтобы честно посчитать разброс.",
  },
};

/** How stable the price is.
 *
 * Two gifts at the same floor are not the same trade if one has not moved in
 * a week and the other swings fifteen percent between crawls. Everything
 * here is measured on stored observations, and it says "мало данных" rather
 * than inventing precision when the series is short.
 */
export function Volatility({ giftId }: { giftId: number }) {
  const [data, setData] = useState<GiftVolatility | null>(null);

  useEffect(() => {
    let cancelled = false;
    void getGiftVolatility(giftId)
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

  if (!data || data.samples === 0) return null;

  const label = LABELS[data.label] ?? LABELS.unknown;
  const drawdown = data.max_drawdown_percent === null || data.max_drawdown_percent === undefined
    ? null
    : Number(data.max_drawdown_percent);

  return (
    <div className="volatility-panel">
      <div className="volatility-head">
        <Activity size={16} />
        <div>
          <strong>Волатильность</strong>
          <small>Насколько цена держится на месте · {data.window_days} дней</small>
        </div>
        <span className={`vol-badge ${label.tone}`}>{label.text}</span>
      </div>
      <div className="volatility-grid">
        <div>
          <span>Разброс за день</span>
          <b>{data.daily_percent ? `±${Number(data.daily_percent).toFixed(1)}%` : "n/a"}</b>
        </div>
        <div>
          <span>Коридор</span>
          <b>
            {formatTon(data.low_ton, { suffix: false })} – {formatTon(data.high_ton)}
          </b>
        </div>
        <div>
          <span>Максимальная просадка</span>
          <b>{drawdown === null ? "n/a" : `-${drawdown.toFixed(1)}%`}</b>
        </div>
        <div>
          <span>Изменений цены</span>
          <b>
            {formatCount(data.price_changes)}
            {data.changes_per_day ? <em> · {data.changes_per_day}/день</em> : null}
          </b>
        </div>
      </div>
      <p className="volatility-note">
        {label.note}
        {data.max_move_percent && data.confident
          ? ` Самое резкое движение за окно: ${formatPercent(data.max_move_percent)}.`
          : ""}
      </p>
      {!data.confident && (
        <p className="muted-copy">
          <TrendingDown size={12} /> Нужно минимум шесть наблюдений цены, сейчас {formatCount(data.samples)}.
        </p>
      )}
    </div>
  );
}
