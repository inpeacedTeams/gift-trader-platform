import type { PricePoint } from "../types";
import { formatPercent, formatTon } from "../format";

const WIDTH = 100;
const HEIGHT = 100;
const PADDING = 8;

function line(values: number[], min: number, range: number): string {
  return values
    .map((value, index) => {
      const x = values.length === 1 ? WIDTH / 2 : (index / (values.length - 1)) * WIDTH;
      const y = HEIGHT - PADDING - ((value - min) / range) * (HEIGHT - PADDING * 2);
      return `${x.toFixed(2)},${y.toFixed(2)}`;
    })
    .join(" ");
}

function day(value: string): string {
  return new Date(value).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

/** Floor and median price over every persisted snapshot for one gift. */
export function PriceChart({ points }: { points: PricePoint[] }) {
  const usable = points.filter(point => point.floor_ton !== null && point.floor_ton !== undefined);
  if (usable.length < 2) {
    return (
      <div className="chart-empty">
        Price history builds from stored snapshots. Come back after a few sync cycles.
      </div>
    );
  }
  const floors = usable.map(point => Number(point.floor_ton));
  const medians = usable.map(point => Number(point.median_ton ?? point.floor_ton));
  const all = [...floors, ...medians];
  const min = Math.min(...all);
  const max = Math.max(...all);
  const range = max - min || 1;
  const first = floors[0];
  const last = floors[floors.length - 1];
  const change = ((last - first) / first) * 100;
  return (
    <div className="price-chart">
      <div className="chart-head">
        <div>
          <strong>{formatTon(last)}</strong>
          <small>current floor</small>
        </div>
        <span className={change >= 0 ? "trend-up" : "trend-down"}>{formatPercent(change)}</span>
      </div>
      <div className="chart-body">
        <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} preserveAspectRatio="none" role="img" aria-label={`Floor price from ${formatTon(first)} to ${formatTon(last)}`}>
          <polyline className="chart-median" points={line(medians, min, range)} fill="none" strokeWidth="1.4" strokeDasharray="3 3" vectorEffect="non-scaling-stroke" />
          <polyline className="chart-floor" points={line(floors, min, range)} fill="none" strokeWidth="2.2" vectorEffect="non-scaling-stroke" />
        </svg>
        <div className="chart-axis-y">
          <span>{formatTon(max, { suffix: false })}</span>
          <span>{formatTon(min, { suffix: false })}</span>
        </div>
      </div>
      <div className="chart-axis-x">
        <span>{day(usable[0].observed_at)}</span>
        <span className="chart-legend">
          <i className="dot-floor" /> floor <i className="dot-median" /> median
        </span>
        <span>{day(usable[usable.length - 1].observed_at)}</span>
      </div>
    </div>
  );
}
