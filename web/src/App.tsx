import { useEffect, useState } from "react";
import { RefreshCw, ShieldCheck } from "lucide-react";
import { authenticateTelegram, getArbitrage, getMarkets, getMe, getWatchlist, type User } from "./api";
import { clearToken } from "./auth";
import type { ArbitrageResponse, MarketResponse } from "./types";
import { Nav, type View } from "./components/Nav";
import { LoadingState, ErrorState } from "./components/State";
import { formatCount, formatPercent, formatTon, formatTonDelta } from "./format";
import { Collections } from "./pages/Collections";
import { Gifts, type CollectionFilter } from "./pages/Gifts";
import { GiftPage } from "./pages/GiftPage";
import { Opportunities } from "./pages/Opportunities";
import { Watchlist } from "./pages/Watchlist";
import { Portfolio } from "./pages/Portfolio";
import { Alerts } from "./pages/Alerts";
import { Settings } from "./pages/Settings";
import "./styles.css";

const TITLES: Record<View, string> = { overview: "Market overview", collections: "Collections", gifts: "Gifts", opportunities: "Opportunities", watchlist: "Watchlist", portfolio: "Portfolio", alerts: "Alerts", settings: "Settings" };

export default function App() {
  const [view, setView] = useState<View>("overview");
  const [selectedGift, setSelectedGift] = useState<number | null>(null);
  const [collection, setCollection] = useState<CollectionFilter | null>(null);
  const [markets, setMarkets] = useState<MarketResponse | null>(null);
  const [arbitrage, setArbitrage] = useState<ArbitrageResponse | null>(null);
  const [watchlistIds, setWatchlistIds] = useState<number[]>([]);
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const refresh = async () => { setLoading(true); setError(null); try { const [marketData, arbitrageData] = await Promise.all([getMarkets(), getArbitrage()]); setMarkets(marketData); setArbitrage(arbitrageData); } catch (e) { setError(e instanceof Error ? e.message : "Live API unavailable"); } finally { setLoading(false); } };
  useEffect(() => { void refresh(); void (async () => { try { const authenticated = await authenticateTelegram(); const me = authenticated ?? await getMe().catch(() => null); setUser(me); if (me) setWatchlistIds((await getWatchlist()).items.map(item => item.gift_id)); } catch { setUser(null); } })(); }, []);
  const signOut = () => { clearToken(); setUser(null); setWatchlistIds([]); };
  const changeView = (next: View) => { setSelectedGift(null); if (next !== "gifts") setCollection(null); setView(next); };
  const openCollection = (item: { id: number; name?: string | null; chain_address: string }) => { setCollection({ id: item.id, name: item.name ?? item.chain_address.slice(0, 16) }); setSelectedGift(null); setView("gifts"); };
  const opportunities = arbitrage?.opportunities ?? [];
  const page = view === "collections"
    ? <Collections onOpen={openCollection}/>
    : view === "gifts"
    ? (selectedGift === null
        ? <Gifts onOpen={setSelectedGift} collection={collection} onClearCollection={() => setCollection(null)}/>
        : <GiftPage giftId={selectedGift} onBack={() => setSelectedGift(null)} onOpenCollection={openCollection}/>)
    : view === "opportunities" ? <Opportunities items={opportunities}/>
    : view === "watchlist" ? <Watchlist markets={markets?.markets ?? []} watchlistIds={watchlistIds} authenticated={Boolean(user)} onToggle={async (giftId, active) => { if (!user) return; const api = await import("./api"); if (active) { await api.removeFromWatchlist(giftId); setWatchlistIds(ids => ids.filter(id => id !== giftId)); } else { await api.addToWatchlist(giftId); setWatchlistIds(ids => [...ids, giftId]); } }}/>
    : view === "portfolio" ? <Portfolio/>
    : view === "alerts" ? <Alerts available={opportunities.length > 0}/>
    : view === "settings" ? <Settings/>
    : <Overview markets={markets} opportunities={opportunities} loading={loading} onBrowse={() => changeView("collections")} />;
  return <div className="app-shell"><aside className="sidebar"><div className="brand"><span className="brand-mark">G</span><span>gift trader</span></div><div className="nav-label">Workspace</div><Nav view={view} onChange={changeView} count={opportunities.length}/><div className="sidebar-bottom"><div className="live-chip"><i/> Live data only</div></div></aside><main className="main"><header className="topbar"><div><p className="eyebrow">SAT 08 AUG 2026 · TON MARKET</p><h1>{TITLES[view]}</h1></div><div className="top-actions"><span className="auth-chip">{user ? <><ShieldCheck size={14}/> {user.username ? `@${user.username}` : user.first_name}</> : "Guest mode"}</span><button className="icon-btn" aria-label="Refresh live data" onClick={() => void refresh()}><RefreshCw size={18} className={loading ? "spin" : ""}/></button><button className="avatar" aria-label={user ? "Sign out" : "Profile"} onClick={user ? signOut : undefined}>IN</button></div></header>{error && view !== "gifts" && view !== "collections" ? <ErrorState detail={error} retry={() => void refresh()}/> : page}</main></div>;
}
function Overview({ markets, opportunities, loading, onBrowse }: { markets: MarketResponse | null; opportunities: ArbitrageResponse["opportunities"]; loading: boolean; onBrowse: () => void }) { const listingCount = markets?.markets.reduce((sum, market) => sum + market.listings.length, 0) ?? 0; const profit = opportunities.reduce((sum, item) => sum + Number(item.profit_ton), 0); return <section className="page-section"><div className="hero-card"><div className="hero-copy"><span className="kicker">◉ Decision cockpit</span><h2>See the market.<br/><em>Move with clarity.</em></h2><p>Cross-market pricing, verified identities, and fee-aware opportunities in one calm view.</p><button className="outline-btn" onClick={onBrowse}>Browse collections</button></div><div className="signal-orbit"><div className="orbit-ring"/><div className="orbit-core"><span>{loading ? "--" : formatCount(opportunities.length)}</span><small>signals</small></div></div></div><div className="metric-grid"><div className="metric green"><span>Net opportunity</span><strong>{loading ? "--" : formatTon(profit)}</strong><small>after marketplace fees</small></div><div className="metric blue"><span>Tracked listings</span><strong>{loading ? "--" : formatCount(listingCount)}</strong><small>from live sources</small></div><div className="metric violet"><span>Markets online</span><strong>{loading ? "--" : formatCount(markets?.markets.length ?? 0)}</strong><small>active sources</small></div></div><div className="section-head overview-head"><div><p className="eyebrow">NEXT ACTION</p><h2>Arbitrage radar</h2></div><span className="fresh"><i/> {formatCount(opportunities.length)} verified signals</span></div><div className="table-card">{loading ? <LoadingState/> : opportunities.slice(0, 5).map(item => <div className="table-row" key={`${item.buy_listing_id}-${item.sell_listing_id}`}><div className="gift-cell"><div className="gift-icon">✦</div><div><strong>{item.gift_key.split(":").slice(-1)[0]}</strong><small>{item.buy_marketplace} → {item.sell_marketplace}</small></div></div><div><b>{formatTon(item.buy_price_ton)}</b><small>buy</small></div><div><b>{formatTon(item.sell_price_ton)}</b><small>sell</small></div><div className="edge"><strong>{formatTonDelta(item.profit_ton)}</strong><small>{formatPercent(item.profit_percent)}</small></div></div>)}</div></section>; }
