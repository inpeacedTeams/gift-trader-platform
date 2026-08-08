import { useEffect, useState } from "react";
import { BellPlus, BellRing, Check, LoaderCircle, Trash2 } from "lucide-react";
import { createAlertRule, deleteAlertRule, getAlertRules, type AlertRule } from "../api";
import { formatTon } from "../format";
import "./quick-alert.css";

const DROPS = [5, 10, 20];

type Props = {
  giftId: number;
  floorTon?: string | null;
  authenticated: boolean;
};

function preset(floor: number, percent: number): string {
  const target = floor * (1 - percent / 100);
  // Nine decimals is the TON precision, anything beyond is noise.
  return target.toFixed(target >= 1 ? 3 : 9).replace(/0+$/, "").replace(/\.$/, "");
}

/** Create a price alert for the gift in view, without retyping its id.
 *
 * Presets are relative to the live floor because that is the number a trader
 * is actually reacting to.
 */
export function QuickAlert({ giftId, floorTon, authenticated }: Props) {
  const [rules, setRules] = useState<AlertRule[]>([]);
  const [custom, setCustom] = useState("");
  const [pending, setPending] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const floor = Number(floorTon ?? 0);

  useEffect(() => {
    if (!authenticated) return;
    void getAlertRules()
      .then(data => setRules(data.items.filter(rule => rule.gift_id === giftId)))
      .catch(() => setRules([]));
  }, [giftId, authenticated]);

  const create = async (threshold: string, key: string) => {
    if (!threshold || Number(threshold) <= 0) return;
    setPending(key);
    setError(null);
    try {
      const rule = await createAlertRule({ gift_id: giftId, rule_type: "price_below", threshold });
      setRules(items => [rule, ...items]);
      setCustom("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not create the alert");
    } finally {
      setPending(null);
    }
  };

  const remove = async (ruleId: number) => {
    setRules(items => items.filter(item => item.id !== ruleId));
    try {
      await deleteAlertRule(ruleId);
    } catch {
      void getAlertRules().then(data => setRules(data.items.filter(rule => rule.gift_id === giftId)));
    }
  };

  if (!authenticated) {
    return (
      <div className="quick-alert guest">
        <BellRing size={16} />
        <p>Sign in through Telegram to get a message when this gift drops.</p>
      </div>
    );
  }

  return (
    <div className="quick-alert">
      <div className="quick-alert-head">
        <BellRing size={16} />
        <div>
          <strong>Alert me when it drops</strong>
          <small>Triggers on the floor across every tracked marketplace.</small>
        </div>
      </div>
      <div className="quick-alert-actions">
        {floor > 0 &&
          DROPS.map(percent => {
            const threshold = preset(floor, percent);
            const key = `drop-${percent}`;
            return (
              <button
                key={key}
                className="preset-btn"
                disabled={pending !== null}
                onClick={() => void create(threshold, key)}
                title={`Alert below ${formatTon(threshold)}`}
              >
                {pending === key ? <LoaderCircle size={13} className="spin" /> : <BellPlus size={13} />}
                -{percent}%
              </button>
            );
          })}
        <div className="custom-threshold">
          <input
            type="number"
            min="0"
            step="any"
            value={custom}
            onChange={event => setCustom(event.target.value)}
            placeholder={floor > 0 ? formatTon(floor, { suffix: false }) : "price"}
            aria-label="Custom alert price in TON"
          />
          <button className="preset-btn" disabled={pending !== null || !custom} onClick={() => void create(custom.trim(), "custom")}>
            {pending === "custom" ? <LoaderCircle size={13} className="spin" /> : <Check size={13} />}
            Set
          </button>
        </div>
      </div>
      {error && <p className="quick-alert-error">{error}</p>}
      {rules.length > 0 && (
        <div className="quick-alert-rules">
          {rules.map(rule => (
            <span className="rule-pill" key={rule.id}>
              below {formatTon(rule.threshold)}
              <button aria-label="Remove this alert" onClick={() => void remove(rule.id)}>
                <Trash2 size={11} />
              </button>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
