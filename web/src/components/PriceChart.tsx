import { useMemo, useState } from "react";
import type { PricePoint } from "../types";
import { formatPercent, formatTon } from "../format";

const WIDTH = 100;
const HEIGHT = 100;
const PADDING = 8;

const RANGES = [
  { id: "24h", label: "24h", hours: 24 },
  { id: "7d", label: "7d", hours: 24 * 7 },
  { id: "all", label: "All", hours: 0 },
] as const;

type RangeId = (typeof RANGES)[number]["id"];
type Coord = { x: number; y: number };

function toCoords(values: number[], min: number, range: number): Coord[] {
  return values.map((value, index) => ({
    x: values.length === 1 ? WIDTH / 2 : (index / (values.length - 1)) * WIDTH,
    y: HEIGHT - PADDING - ((value - min) / range) * (HEIGHT - PADDING * 2),
  }));
}

function path(points: Coord[]): string {
  return points.map(point => `${point.x.toFixed(2)},${point.y.toFixed(2)}`).join(" ");
}

/** Split the line so each move is coloured by its own direction.
 *
 * Consecutive moves in the same direction share one polyline, which keeps the
 * node count near the number of trend flips instead of the number of points.
 */
function segments(values: number[], coords: Coord[]) {
  const result: { rising: boolean; points: Coord[] }[] = [];
  for (let index = 1; index < values.length; index += 1) {
    const rising = values[index] >= values[index - 1];
    const last = result[result.length - 1];
    if (last && last.rising === rising) {
      last.points.push(coords[index]);
    } else {
      result.push({ rising, points: [coords[index - 1], coords[index]] });
    }
  }
  return result;
}

function day(value: string): string {
  return new Date(value).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

/** Floor and median price over the persisted snapshots for one gift. */
export function PriceChart({ points }: { points: PricePoint[] }) {
  const [range, setRange] = useState<RangeId>("all");

  const usable = useMemo(() => {
    const hours = RANGES.find(item => item.id === range)?.hours ?? 0;
    const since = hours ? Date.now() - hours * 3600_000 : 0;
    return points
      .filter(point => point.floor_ton !== null && point.floor_ton !== undefined)
      .filter(point => !since || new Date(point.observed_at).getTime() >= since)
      .sort((a, b) => new Date(a.observed_at).getTime() - new Date(b.observed_at).getTime());
  }, [points, range]);

  const chart = useMemo(() => {
    if (usable.length < 2) return null;
    const floors = usable.map(point => Number(point.floor_ton));
    const medians = usable.map(point => Number(point.median_ton ?? point.floor_ton));
    const all = [...floors, ...medians];
    const min = Math.min(...all);
    const max = Math.max(...all);
    const span = max - min || 1;
    return {
      floors,
      min,
      max,
      medianPath: path(toCoords(medians, min, span)),
      parts: segments(floors, toCoords(floors, min, span)),
    };
  }, [usable]);

  const switcher = (
    <div className="chart-ranges" role="group" aria-label="History range">
      {RANGES.map(item => (
        <button
          key={item.id}
          className={item.id === range ? "active" : ""}
          aria-pressed={item.id === range}
          onClick={() => setRange(item.id)}
        >
          {item.label}
        </button>
      ))}
    </div>
  );

  if (!chart) {
    return (
      <div className="price-chart">
        {switcher}
        <div className="chart-empty">
          {points.length
            ? "Not enough snapshots in this range yet. Try a wider one."
            : "Price history builds from stored snapshots. Come back after a few sync cycles."}
        </div>
      </div>
    );
  }

  const first = chart.floors[0];
  const last = chart.floors[chart.floors.length - 1];
  const change = ((last - first) / first) * 100;
  const rising = change >= 0;
  return (
    <div className="price-chart">
      {switcher}
      <div className="chart-head">
        <div>
          <strong className={rising ? "trend-up" : "trend-down"}>{formatTon(last)}</strong>
          <small>current floor</small>
        </div>
        <span className={rising ? "trend-up" : "trend-down"}>{formatPercent(change)}</span>
      </div>
      <div className="chart-body">
        <svg
          viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
          preserveAspectRatio="none"
          role="img"
          aria-label={`Floor price from ${formatTon(first)} to ${formatTon(last)}`}
        >
          <polyline className="chart-median" points={chart.medianPath} fill="none" strokeWidth="1.4" strokeDasharray="3 3" vectorEffect="non-scaling-stroke" />
          {chart.parts.map((part, index) => (
            <polyline
              key={index}
              className={part.rising ? "chart-rise" : "chart-fall"}
              points={path(part.points)}
              fill="none"
              strokeWidth="2.2"
              strokeLinecap="round"
              strokeLinejoin="round"
              vectorEffect="non-scaling-stroke"
            />
          ))}
        </svg>
        <div className="chart-axis-y">
          <span>{formatTon(chart.max, { suffix: false })}</span>
          <span>{formatTon(chart.min, { suffix: false })}</span>
        </div>
      </div>
      <div className="chart-axis-x">
        <span>{day(usable[0].observed_at)}</span>
        <span className="chart-legend">
          <i className="dot-rise" /> up <i className="dot-fall" /> down <i className="dot-median" /> median
        </span>
        <span>{day(usable[usable.length - 1].observed_at)}</span>
      </div>
    </div>
  );
}
