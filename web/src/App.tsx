import { useEffect, useMemo, useState } from "react";
import { Activity, ArrowDownToLine, Bell, ChevronRight, CircleAlert, Database, LayoutDashboard, RefreshCw, Search, Settings2, Star, TrendingUp, Wallet } from "lucide-react";
import { getArbitrage, getMarkets } from "./api";
import type { ArbitrageResponse, MarketResponse, Opportunity } from "./types";
import "./styles.css";

const money = (value: string | number) => Number(value).toLocaleString("en-US", { maximumFractionDigits: 3 });
const title = (value: string) => value.replace(/^collection:/, "").split(":gift:")[0].slice(0, 12);

function App() {
  const [markets, setMarkets] = useState<MarketResponse | null>(null);
  const [arbitrage, setArbitrage] = useState<ArbitrageResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const refresh = async () => {
    setLoading(true); setError(null);
    try { const [m, a] = await Promise.all([getMarkets(), getArbitrage()]); setMarkets(m); setArbitrage(a); }
    catch (e) { setError(e instanceof Error ? e.message : "Live market is unavailable"); }
    finally { setLoading(false); }
  };
  useEffect(() => { void refresh(); }, []);
  const opportunities = useMemo(() => (arbitrage?.opportunities ?? []).filter((item) => `${item.gift_key} ${item.buy_marketplace} ${item.sell_marketplace}`.toLowerCase().includes(query.toLowerCase())), [arbitrage, query]);
  const listingCount = markets?.markets.reduce((sum, market) => sum + market.listings.length, 0) ?? 0;
  const netProfit = opportunities.reduce((sum, item) => sum + Number(item.profit_ton), 0);

  return <div className="app-shell"><aside className="sidebar"><div className="brand"><span className="brand-mark">G</span><span>gift trader</span></div><div className="nav-label">Workspace</div><nav><a className="active"><LayoutDashboard size={18}/> Overview</a><a><TrendingUp size={18}/> Opportunities <span className="nav-count">{opportunities.length}</span></a><a><Star size={18}/> Watchlist</a><a><Wallet size={18}/> Portfolio</a></nav><div className="sidebar-bottom"><a><Bell size={18}/> Alerts</a><a><Settings2 size={18}/> Settings</a><div className="live-chip"><i/> Live data only</div></div></aside><main className="main"><header className="topbar"><div><p className="eyebrow">SAT 08 AUG 2026 · TON MARKET</p><h1>Market overview</h1></div><div className="top-actions"><label className="search"><Search size={17}/><input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search gifts or markets" /></label><button className="icon-btn" aria-label="Refresh data" onClick={() => void refresh()}><RefreshCw size={18} className={loading ? "spin" : ""}/></button><button className="avatar" aria-label="Open profile">IN</button></div></header>{error && <div className="notice error"><CircleAlert size={18}/><span>Live sources are unavailable: {error}</span><button onClick={() => void refresh()}>Retry</button></div>}<section className="hero-grid"><div className="hero-card"><div className="hero-copy"><span className="kicker"><Activity size={15}/> Decision cockpit</span><h2>See the market.<br/><em>Move with clarity.</em></h2><p>Cross-market pricing, verified identities, and fee-aware opportunities in one calm view.</p></div><div className="signal-orbit"><div className="orbit-ring"/><div className="orbit-core"><span>{loading ? "--" : opportunities.length}</span><small>signals</small></div><span className="orbit-dot d1"/><span className="orbit-dot d2"/><span className="orbit-dot d3"/></div></div><div className="metric-grid"><Metric label="Net opportunity" value={`${money(netProfit)} TON`} accent="green" detail="after marketplace fees"/><Metric label="Tracked listings" value={loading ? "--" : listingCount.toString()} accent="blue" detail="from live sources"/><Metric label="Markets online" value={loading ? "--" : `${markets?.markets.length ?? 0} / 3`} accent="violet" detail="Fragment · Portals · GetGems"/></div></section><section className="section-head"><div><p className="eyebrow">LIVE FEED</p><h2>Arbitrage radar</h2></div><div className="toolbar"><span className="fresh"><i/> Updated just now</span><button className="outline-btn"><ArrowDownToLine size={15}/> Export</button></div></section><section className="table-card"><div className="table-head"><span>Gift / identity</span><span>Buy here</span><span>Sell there</span><span>Net edge</span><span/></div>{loading ? <div className="state"><RefreshCw className="spin"/><span>Reading live marketplaces...</span></div> : opportunities.length === 0 ? <div className="state"><Database size={22}/><strong>No verified opportunities yet</strong><span>Try again when the collectors have fresh listings.</span></div> : opportunities.slice(0, 8).map((item) => <OpportunityRow key={`${item.buy_listing_id}-${item.sell_listing_id}`} item={item}/>)}</section><footer><span><i className="green-dot"/> Data provenance is visible on every signal</span><span>Built for TON gift traders <ChevronRight size={14}/></span></footer></main></div>;
}
function Metric({ label, value, detail, accent }: { label: string; value: string; detail: string; accent: string }) { return <div className={`metric ${accent}`}><span>{label}</span><strong>{value}</strong><small>{detail}</small></div>; }
function OpportunityRow({ item }: { item: Opportunity }) { return <div className="table-row"><div className="gift-cell"><div className="gift-icon">✦</div><div><strong>{title(item.gift_key)}</strong><small>{item.gift_key.startsWith("canonical:") ? "Verified on-chain identity" : "Derived identity"}</small></div></div><div><b>{money(item.buy_price_ton)} TON</b><small className="market">{item.buy_marketplace}</small></div><div><b>{money(item.sell_price_ton)} TON</b><small className="market">{item.sell_marketplace}</small></div><div className="edge"><strong>+{money(item.profit_ton)} TON</strong><small>+{money(item.profit_percent)}%</small></div><button className="row-btn" aria-label="Open opportunity"><ChevronRight size={17}/></button></div>; }
export default App;
