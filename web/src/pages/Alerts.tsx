import { FormEvent, useEffect, useState } from "react";
import { BellRing, Plus, SlidersHorizontal, Trash2, LoaderCircle } from "lucide-react";
import { createAlertRule, deleteAlertRule, getAlertEvents, getAlertRules } from "../api";
import { EmptyState } from "../components/State";

type Rule = { id: number; gift_id?: number | null; rule_type: string; threshold: string; is_active: boolean };
type Event = { id: number; message: string; is_read: boolean; created_at: string };

export function Alerts({ available }: { available: boolean }) {
  const [rules, setRules] = useState<Rule[]>([]);
  const [events, setEvents] = useState<Event[]>([]);
  const [ruleType, setRuleType] = useState("price_below");
  const [threshold, setThreshold] = useState("10");
  const [giftId, setGiftId] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = async () => { setLoading(true); try { const [ruleData, eventData] = await Promise.all([getAlertRules(), getAlertEvents()]); setRules(ruleData.items); setEvents(eventData.items); setError(null); } catch (e) { setError(e instanceof Error ? e.message : "Sign in to manage alerts"); } finally { setLoading(false); } };
  useEffect(() => { void load(); }, []);
  const submit = async (event: FormEvent) => { event.preventDefault(); setSaving(true); try { const created = await createAlertRule({ rule_type: ruleType, threshold, ...(giftId.trim() ? { gift_id: Number(giftId) } : {}) }) as Rule; setRules(items => [created, ...items]); setThreshold("10"); setGiftId(""); setError(null); } catch (e) { setError(e instanceof Error ? e.message : "Could not create alert"); } finally { setSaving(false); } };
  const remove = async (id: number) => { try { await deleteAlertRule(id); setRules(items => items.filter(item => item.id !== id)); } catch (e) { setError(e instanceof Error ? e.message : "Could not delete alert"); } };
  const label = (type: string) => ({ price_below: "Price below", price_above: "Price above", change_percent: "Change above", listed_below: "Listing below" }[type] || type);

  return <section className="page-section"><div className="section-head"><div><p className="eyebrow">NOTIFICATION RULES</p><h2>Alerts</h2></div><span className="fresh">{rules.length} active rule{rules.length === 1 ? "" : "s"}</span></div><div className="alert-setup"><BellRing size={24}/><div><h3>Turn market movement into a signal</h3><p>Rules are private to your account and evaluated against persisted market data.</p></div><SlidersHorizontal size={20}/></div>{error && <div className="notice error">{error}</div>}<form className="alert-form" onSubmit={submit}><label>Rule<select value={ruleType} onChange={e => setRuleType(e.target.value)}><option value="price_below">Price below</option><option value="price_above">Price above</option><option value="change_percent">Change above %</option><option value="listed_below">Listing below</option></select></label><label>Threshold<input type="number" min="0.000000001" step="any" value={threshold} onChange={e => setThreshold(e.target.value)} required /></label><label>Gift ID <span>(optional)</span><input inputMode="numeric" value={giftId} onChange={e => setGiftId(e.target.value.replace(/\D/g, ""))} placeholder="All gifts" /></label><button className="outline-btn" disabled={saving}>{saving ? <LoaderCircle className="spin" size={15}/> : <Plus size={15}/>} Create alert</button></form>{loading ? <div className="page-state"><LoaderCircle className="spin" size={22}/><span>Loading alerts...</span></div> : rules.length ? <div className="alert-list">{rules.map(rule => <div className="alert-row" key={rule.id}><span className="status-toggle"/><div><strong>{label(rule.rule_type)} {rule.threshold}</strong><small>{rule.gift_id ? `Gift #${rule.gift_id}` : "All verified gifts"} · {rule.is_active ? "active" : "paused"}</small></div><button className="icon-btn" aria-label="Delete alert" onClick={() => void remove(rule.id)}><Trash2 size={15}/></button></div>)}</div> : <EmptyState title="No alerts configured" detail={available ? "Create a rule to watch the live market." : "Sign in through Telegram to create a private alert."}/>}<div className="events-section"><div className="section-head"><div><p className="eyebrow">ACTIVITY</p><h3>Recent events</h3></div></div>{events.length ? events.map(item => <div className="event-row" key={item.id}><span className={item.is_read ? "event-dot read" : "event-dot"}/><div><strong>{item.message}</strong><small>{new Date(item.created_at).toLocaleString()}</small></div></div>) : <p className="muted-copy">No triggered alerts yet.</p>}</div></section>;
}
