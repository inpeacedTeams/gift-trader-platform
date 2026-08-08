import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, Calculator, TrendingUp } from "lucide-react";
import { getFees, type FeeSchedule } from "../api";
import { Select } from "./Select";
import { formatPercent, formatTon, formatTonDelta } from "../format";
import "./flip-calc.css";

type Props = {
  floorTon?: string | number | null;
  medianTon?: string | number | null;
  /** Venues this gift actually trades on, so the fee picked is a real one. */
  venues?: string[];
};

function toNumber(value: string | number | null | undefined): number | null {
  if (value === null || value === undefined || value === "") return null;
  const amount = Number(value);
  return Number.isFinite(amount) ? amount : null;
}

/** What a flip actually pays out.
 *
 * The catalog shows a discount against the peer median, but a 6% discount on
 * a venue that keeps 5% of the sale is not a trade. This does the subtraction
 * out loud: fees, gas, and the price the exit has to clear to break even.
 *
 * Fees come from the API rather than living here, so the calculator and the
 * arbitrage scanner always agree on what a trade costs. Recording an actual
 * purchase is LogBuy's job, right above this panel.
 */
export function FlipCalc({ floorTon, medianTon, venues = [] }: Props) {
  const [fees, setFees] = useState<FeeSchedule | null>(null);
  const floor = toNumber(floorTon);
  const median = toNumber(medianTon);
  const suggestedSell = median !== null && floor !== null ? Math.max(median, floor) : median ?? floor;

  const [buyText, setBuyText] = useState(floor !== null ? String(floor) : "");
  const [sellText, setSellText] = useState(suggestedSell !== null ? String(suggestedSell) : "");
  const [venue, setVenue] = useState(venues[0] ?? "");

  useEffect(() => {
    let cancelled = false;
    void getFees()
      .then(result => {
        if (cancelled) return;
        setFees(result);
        setVenue(current => current || venues[0] || result.marketplaces[0]?.marketplace || "");
      })
      .catch(() => {
        if (!cancelled) setFees(null);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Prices arrive after the first render, so seed the fields once they do.
  useEffect(() => {
    if (floor !== null) setBuyText(current => (current === "" ? String(floor) : current));
    if (suggestedSell !== null) setSellText(current => (current === "" ? String(suggestedSell) : current));
  }, [floor, suggestedSell]);

  const options = useMemo(() => {
    const known = fees?.marketplaces.map(item => item.marketplace) ?? [];
    const all = Array.from(new Set([...venues, ...known])).filter(Boolean);
    return all.map(item => ({ value: item, label: item }));
  }, [fees, venues]);

  if (!fees) return null;

  const feePercent = Number(
    fees.marketplaces.find(item => item.marketplace === venue)?.sell_fee_percent ??
      fees.default_sell_fee_percent
  );
  const gas = Number(fees.gas_ton);
  const buy = toNumber(buyText);
  const sell = toNumber(sellText);
  const keep = 1 - feePercent / 100;

  const cost = buy === null ? null : buy + gas;
  const feeCost = sell === null ? null : (sell * feePercent) / 100;
  const net = sell === null || feeCost === null ? null : sell - feeCost;
  const profit = cost === null || net === null ? null : net - cost;
  const roi = profit === null || cost === null || cost <= 0 ? null : (profit / cost) * 100;
  const breakeven = cost === null || keep <= 0 ? null : cost / keep;
  // The exit price only exists if someone pays it: a breakeven above the
  // current floor means undercutting is not an option.
  const floorShort = breakeven !== null && floor !== null && breakeven > floor;

  return (
    <div className="flip-panel">
      <div className="flip-head">
        <Calculator size={16} />
        <div>
          <strong>Прибыль после комиссий</strong>
          <small>Сколько реально останется на руках</small>
        </div>
      </div>
      <div className="flip-inputs">
        <label className="flip-field">
          <span>Покупка, TON</span>
          <input
            inputMode="decimal"
            value={buyText}
            onChange={event => setBuyText(event.target.value)}
            placeholder="0"
          />
          {floor !== null && (
            <p className="flip-hint">
              floor {formatTon(floor)} ·{" "}
              <button type="button" onClick={() => setBuyText(String(floor))}>
                подставить
              </button>
            </p>
          )}
        </label>
        <label className="flip-field">
          <span>Продажа, TON</span>
          <input
            inputMode="decimal"
            value={sellText}
            onChange={event => setSellText(event.target.value)}
            placeholder="0"
          />
          {median !== null && (
            <p className="flip-hint">
              медиана {formatTon(median)} ·{" "}
              <button type="button" onClick={() => setSellText(String(median))}>
                подставить
              </button>
            </p>
          )}
        </label>
        <div className="flip-field">
          <span>Площадка продажи</span>
          <Select value={venue} onChange={setVenue} options={options} label="Площадка продажи" />
          <p className="flip-hint">комиссия {formatPercent(feePercent)?.replace("+", "")}</p>
        </div>
      </div>
      <div className="flip-breakdown">
        <div>
          <span>Комиссия площадки</span>
          <b>{feeCost === null ? "--" : `-${formatTon(feeCost)}`}</b>
        </div>
        <div>
          <span>Газ</span>
          <b>-{formatTon(gas)}</b>
        </div>
        <div>
          <span>На руки</span>
          <b>{formatTon(net)}</b>
        </div>
        <div>
          <span>Прибыль</span>
          <b className={profit === null ? undefined : profit >= 0 ? "profit" : "loss"}>
            {profit === null ? "--" : formatTonDelta(profit)}
          </b>
        </div>
        <div>
          <span>ROI</span>
          <b className={roi === null ? undefined : roi >= 0 ? "profit" : "loss"}>
            {roi === null ? "--" : formatPercent(roi)}
          </b>
        </div>
      </div>
      {breakeven !== null && (
        <p className={floorShort ? "flip-note warn" : "flip-note"}>
          {floorShort ? <AlertTriangle size={13} /> : <TrendingUp size={13} />}
          {floorShort ? (
            <span>
              Ноль только от {formatTon(breakeven)}, а текущий floor {formatTon(floor)}. Придётся ждать
              рост, а не перебивать стакан.
            </span>
          ) : (
            <span>Безубыток от {formatTon(breakeven)}. Всё выше этой цены уже твоё.</span>
          )}
        </p>
      )}
    </div>
  );
}
