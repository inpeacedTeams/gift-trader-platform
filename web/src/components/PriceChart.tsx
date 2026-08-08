import { useState } from "react";
import type { PricePoint } from "../types";
import { formatPercent, formatTon } from "../format";

const WIDTH = 100;
const HEIGHT = 100;
const PADDING = 8;

type Coord = { x: number; y: number; value: number; at: string };

function coords(values: number[], points: PricePoint[], min: number, range: number): Coord[] {
  return values.map((value, index) => ({
    x: values.length === 1 ? WIDTH / 2 : (index / (values.length - 1)) * WIDTH,
    y: HEIGHT - PADDING - ((value - min) / range) * (HEIGHT - PADDING * 2),
    value,
    at: points[index].observed_at,
  }));
}

function day(value: string): string {
  return new Date(value).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function moment(value: string): string {
  return new Date(value).toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

/** Floor and median over stored snapshots.
 *
 * Each floor segment is colored by its own direction, so a drop reads red and
 * a recovery reads green even inside one trend.
 */
export function PriceChart({ points }: { points: PricePoint[] }) {
  const [hover, setHover] = useState<number | null>(null);
  const usable = points.filter(point => point.floor_ton !== null && point.floor_ton !== undefined);
  if (usable.length < 2) {
    return <div className="chart-empty">Price history builds from stored snapshots. Come back after a few sync cycles.</div>;
  }
  const floors = usable.map(point => Number(point.floor_ton));
  const medians = usable.map(point => Number(point.median_ton ?? point.floor_ton));
  const all = [...floors, ...medians];
  const min = Math.min(...all);
  const max = Math.max(...all);
  const range = max - min || 1;
  const floorCoords = coords(floors, usable, min, range);
  const medianCoords = coords(medians, usable, min, range);
  const first = floors[0];
  const last = floors[floors.length - 1];
  const change = ((last - first) / first) * 100;
  const active = hover === null ? null : floorCoords[hover];

  const onMove = (event: React.MouseEvent<HTMLDivElement>) => {
    const bounds = event.currentTarget.getBoundingClientRect();
    const ratio = (event.clientX - bounds.left) / bounds.width;
    const index = Math.round(ratio * (floorCoords.length - 1));
    setHover(Math.min(floorCoords.length - 1, Math.max(0, index)));
  };

  return (
    <div className="price-chart">
      <div className="chart-head">
        <div>
          <strong>{formatTon(active ? active.value : last)}</strong>
          <small>{active ? moment(active.at) : "current floor"}</small>
        </div>
        <span className={change >= 0 ? "trend-up" : "trend-down"}>{formatPercent(change)}</span>
      </div>
      <div className="chart-body" onMouseMove={onMove} onMouseLeave={() => setHover(null)}>
        <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} preserveAspectRatio="none" role="img" aria-label={`Floor price from ${formatTon(first)} to ${formatTon(last)}`}>
          <polyline className="chart-median" points={medianCoords.map(point => `${point.x},${point.y}`).join(" ")} fill="none" strokeWidth="1.4" strokeDasharray="3 3" vectorEffect="non-scaling-stroke" />
          {floorCoords.slice(1).map((point, index) => {
            const previous = floorCoords[index];
            return (
              <line
                key={point.at}
                className={point.value >= previous.value ? "seg-up" : "seg-down"}
                x1={previous.x}
                y1={previous.y}
                x2={point.x}
                y2={point.y}
                strokeWidth="2.2"
                strokeLinecap="round"
                vectorEffect="non-scaling-stroke"
              />
            );
          })}
          {active && (
            <>
              <line className="chart-crosshair" x1={active.x} y1="0" x2={active.x} y2={HEIGHT} strokeWidth="1" vectorEffect="non-scaling-stroke" />
              <circle className="chart-dot" cx={active.x} cy={active.y} r="2.4" vectorEffect="non-scaling-stroke" />
            </>
          )}
        </svg>
        <div className="chart-axis-y">
          <span>{formatTon(max, { suffix: false })}</span>
          <span>{formatTon(min, { suffix: false })}</span>
        </div>
      </div>
      <div className="chart-axis-x">
        <span>{day(usable[0].observed_at)}</span>
        <span className="chart-legend">
          <i className="dot-up" /> up <i className="dot-down" /> down <i className="dot-median" /> median
        </span>
        <span>{day(usable[usable.length - 1].observed_at)}</span>
      </div>
    </div>
  );
}
