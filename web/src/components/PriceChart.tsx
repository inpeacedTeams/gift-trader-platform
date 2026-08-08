import { useMemo } from "react";
import type { PricePoint } from "../types";
import { formatPercent, formatTon } from "../format";

const WIDTH = 100;
const HEIGHT = 100;
const PADDING = 8;

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

/** Floor and median price over every persisted snapshot for one gift. */
export function PriceChart({ points }: { points: PricePoint[] }) {
  const usable = useMemo(
    () => points.filter(point => point.floor_ton !== null && point.floor_ton !== undefined),
    [points]
  );
  const chart = useMemo(() => {
    if (usable.length < 2) return null;
    const floors = usable.map(point => Number(point.floor_ton));
    const medians = usable.map(point => Number(point.median_ton ?? point.floor_ton));
    const all = [...floors, ...medians];
    const min = Math.min(...all);
    const max = Math.max(...all);
    const range = max - min || 1;
    const coords = toCoords(floors, min, range);
    return {
      floors,
      min,
      max,
      medianPath: path(toCoords(medians, min, range)),
      parts: segments(floors, coords),
    };
  }, [usable]);

  if (!chart) {
    return (
      <div className="chart-empty">
        Price history builds from stored snapshots. Come back after a few sync cycles.
      </div>
    );
  }

  const first = chart.floors[0];
  const last = chart.floors[chart.floors.length - 1];
  const change = ((last - first) / first) * 100;
  const rising = change >= 0;
  return (
    <div className="price-chart">
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
