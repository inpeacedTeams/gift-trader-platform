import { FormEvent, useEffect, useState } from "react";
import { Wallet, Plus, ShieldCheck, Trash2, LoaderCircle } from "lucide-react";
import { addWallet, getWallets, removeWallet } from "../api";
import { EmptyState } from "../components/State";

type WalletItem = { id: number; address: string; label?: string | null };

export function Portfolio() {
  const [wallets, setWallets] = useState<WalletItem[]>([]);
  const [address, setAddress] = useState("");
  const [label, setLabel] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = async () => { setLoading(true); try { setWallets((await getWallets()).items); setError(null); } catch (e) { setError(e instanceof Error ? e.message : "Sign in to manage wallets"); } finally { setLoading(false); } };
  useEffect(() => { void load(); }, []);
  const submit = async (event: FormEvent) => { event.preventDefault(); if (!address.trim()) return; setSaving(true); try { const created = await addWallet(address.trim(), label.trim() || undefined) as WalletItem; setWallets(items => items.some(item => item.id === created.id) ? items : [created, ...items]); setAddress(""); setLabel(""); setError(null); } catch (e) { setError(e instanceof Error ? e.message : "Could not connect wallet"); } finally { setSaving(false); } };
  const remove = async (id: number) => { try { await removeWallet(id); setWallets(items => items.filter(item => item.id !== id)); } catch (e) { setError(e instanceof Error ? e.message : "Could not remove wallet"); } };

  return <section className="page-section"><div className="section-head"><div><p className="eyebrow">CAPITAL VIEW</p><h2>Portfolio</h2></div><span className="fresh">{wallets.length} connected wallet{wallets.length === 1 ? "" : "s"}</span></div><div className="portfolio-hero"><div><span className="kicker"><ShieldCheck size={15}/> On-chain only</span><h3>Track what you own,<br/><em>not just what moves.</em></h3><p>Wallets are stored privately and used as the source for holdings.</p></div><Wallet size={88} strokeWidth={1} className="portfolio-icon"/></div>{error && <div className="notice error">{error}</div>}<form className="wallet-form" onSubmit={submit}><label>TON wallet address<input value={address} onChange={e => setAddress(e.target.value)} placeholder="EQ... or UQ..." minLength={10} required /></label><label>Label<input value={label} onChange={e => setLabel(e.target.value)} placeholder="Main wallet" /></label><button className="outline-btn" disabled={saving}>{saving ? <LoaderCircle className="spin" size={15}/> : <Plus size={15}/>} Connect wallet</button></form>{loading ? <div className="page-state"><LoaderCircle className="spin" size={22}/><span>Loading wallets...</span></div> : wallets.length ? <div className="wallet-list">{wallets.map(item => <div className="wallet-row" key={item.id}><div><strong>{item.label || "Unnamed wallet"}</strong><small>{item.address}</small></div><button className="icon-btn" aria-label={`Remove ${item.label || "wallet"}`} onClick={() => void remove(item.id)}><Trash2 size={15}/></button></div>)}</div> : <EmptyState title="No wallets connected" detail="Connect a TON address to start building the portfolio view."/>}<div className="metric-grid portfolio-metrics"><div className="metric"><span>Portfolio value</span><strong>-- TON</strong><small>Holdings sync comes next</small></div><div className="metric"><span>Assets</span><strong>--</strong><small>Waiting for wallet index</small></div><div className="metric"><span>24h change</span><strong>--</strong><small>No valuation snapshot yet</small></div></div></section>;
}
