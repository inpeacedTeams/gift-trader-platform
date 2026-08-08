import { useEffect, useState } from "react";
import { RefreshCw, ShieldCheck } from "lucide-react";
import {
  addToWatchlist,
  authenticateTelegram,
  getAiStatus,
  getArbitrage,
  getMe,
  getOverview,
  getWatchlist,
  removeFromWatchlist,
  type User,
} from "./api";
import { clearToken } from "./auth";
import type { ArbitrageOpportunity, OverviewStats } from "./types";
import { Nav, type View } from "./components/Nav";
import { LoadingState, ErrorState } from "./components/State";
import { LiveFeed } from "./components/LiveFeed";
import { Movers } from "./components/Movers";
import { formatAgo, formatCount, formatPercent, formatTon, formatTonDelta } from "./format";
import { Analyst } from "./pages/Analyst";
import { Collections } from "./pages/Collections";
import { Deals } from "./pages/Deals";
import { Gifts, type CollectionFilter } from "./pages/Gifts";
import { GiftPage } from "./pages/GiftPage";
import { Opportunities } from "./pages/Opportunities";
import { Positions } from "./pages/Positions";
import { Sniper } from "./pages/Sniper";
import { Watchlist } from "./pages/Watchlist";
import { Portfolio } from "./pages/Portfolio";
import { Alerts } from "./pages/Alerts";
import { Settings } from "./pages/Settings";
import "./styles.css";

const TITLES: Record<View, string> = { overview: "Market overview", collections: "Collections", gifts: "Gifts", deals: "Deals", analyst: "Analyst", opportunities: "Opportunities", sniper: "Sniper", watchlist: "Watchlist", positions: "Positions", portfolio: "Portfolio", alerts: "Alerts", settings: "Settings" };

export default function App() {
  const [view, setView] = useState<View>("overview");
  const [selectedGift, setSelectedGift] = useState<number | null>(null);
  const [collection, setCollection] = useState<CollectionFilter | null>(null);
  const [stats, setStats] = useState<OverviewStats | null>(null);
  const [topSpreads, setTopSpreads] = useState<ArbitrageOpportunity[]>([]);
  const [watchlistIds, setWatchlistIds] = useState<number[]>([]);
  const [user, setUser] = useState<User | null>(null);
  const [aiEnabled, setAiEnabled] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  /** Reads stored data only. Crawling happens on the worker, not on page load. */
  const refresh = async () => {
    setLoading(true);
    setError(null);
    try {
      const [overview, spreads] = await Promise.all([getOverview(), getArbitrage(0, 5)]);
      setStats(overview);
      setTopSpreads(spreads.items);
    } catch (e) {
      setError(e instanceof Error ? e.message : "API unavailable");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void refresh();
    void getAiStatus()
      .then(status => setAiEnabled(status.enabled))
      .catch(() => setAiEnabled(false));
    void (async () => {
      try {
        const authenticated = await authenticateTelegram();
        const me = authenticated ?? (await getMe().catch(() => null));
        setUser(me);
        if (me) setWatchlistIds((await getWatchlist()).items.map(item => item.id));
      } catch {
        setUser(null);
      }
    })();
  }, []);

  const toggleWatchlist = async (giftId: number, saved: boolean) => {
    if (!user) return;
    setWatchlistIds(ids => (saved ? ids.filter(id => id !== giftId) : [...ids, giftId]));
    try {
      if (saved) await removeFromWatchlist(giftId);
      else await addToWatchlist(giftId);
    } catch {
      setWatchlistIds(ids => (saved ? [...ids, giftId] : ids.filter(id => id !== giftId)));
    }
  };

  const signOut = () => {
    clearToken();
    setUser(null);
    setWatchlistIds([]);
  };
  const changeView = (next: View) => {
    setSelectedGift(null);
    if (next !== "gifts") setCollection(null);
    setView(next);
  };
  const openCollection = (item: { id: number; name?: string | null; chain_address: string }) => {
    setCollection({ id: item.id, name: item.name ?? item.chain_address.slice(0, 16) });
    setSelectedGift(null);
    setView("gifts");
  };
  const openGift = (giftId: number) => {
    setSelectedGift(giftId);
    setView("gifts");
  };
  const page =
    view === "collections" ? (
      <Collections onOpen={openCollection} />
    ) : view === "deals" ? (
      <Deals onOpen={openGift} />
    ) : view === "analyst" ? (
      <Analyst enabled={aiEnabled} authenticated={Boolean(user)} />
    ) : view === "gifts" ? (
      selectedGift === null ? (
        <Gifts
          onOpen={setSelectedGift}
          collection={collection}
          onClearCollection={() => setCollection(null)}
          watchlistIds={watchlistIds}
          authenticated={Boolean(user)}
          onToggleWatchlist={(giftId, saved) => void toggleWatchlist(giftId, saved)}
        />
      ) : (
        <GiftPage
          giftId={selectedGift}
          onBack={() => setSelectedGift(null)}
          authenticated={Boolean(user)}
          aiEnabled={aiEnabled}
          onOpenCollection={openCollection}
        />
      )
    ) : view === "opportunities" ? (
      <Opportunities onOpen={openGift} />
    ) : view === "sniper" ? (
      <Sniper authenticated={Boolean(user)} />
    ) : view === "watchlist" ? (
      <Watchlist
        authenticated={Boolean(user)}
        onOpen={openGift}
        onToggle={(giftId, saved) => toggleWatchlist(giftId, saved)}
      />
    ) : view === "positions" ? (
      <Positions authenticated={Boolean(user)} onOpenGift={openGift} />
    ) : view === "portfolio" ? (
      <Portfolio />
    ) : view === "alerts" ? (
      <Alerts available={topSpreads.length > 0} onOpenGift={openGift} />
    ) : view === "settings" ? (
      <Settings />
    ) : (
      <Overview
        stats={stats}
        spreads={topSpreads}
        loading={loading}
        onBrowse={() => changeView("collections")}
        onOpenGift={openGift}
      />
    );
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">G</span>
          <span>gift trader</span>
        </div>
        <div className="nav-label">Workspace</div>
        <Nav view={view} onChange={changeView} count={topSpreads.length} />
        <div className="sidebar-bottom">
          <div className="live-chip">
            <i /> {stats?.last_sync_at ? `Синк ${formatAgo(stats.last_sync_at)}` : "Ожидание синка"}
          </div>
        </div>
      </aside>
      <main className="main">
        <header className="topbar">
          <div>
            <p className="eyebrow">SAT 08 AUG 2026 · TON MARKET</p>
            <h1>{TITLES[view]}</h1>
          </div>
          <div className="top-actions">
            <span className="auth-chip">
              {user ? (
                <>
                  <ShieldCheck size={14} /> {user.username ? `@${user.username}` : user.first_name}
                </>
              ) : (
                "Guest mode"
              )}
            </span>
            <button className="icon-btn" aria-label="Обновить данные" onClick={() => void refresh()}>
              <RefreshCw size={18} className={loading ? "spin" : ""} />
            </button>
            {user && (
              <button className="avatar" aria-label="Sign out" onClick={signOut}>
                {(user.username ?? user.first_name ?? "IN").slice(0, 2).toUpperCase()}
              </button>
            )}
          </div>
        </header>
        {error && view === "overview" ? <ErrorState detail={error} retry={() => void refresh()} /> : page}
      </main>
    </div>
  );
}
function Overview({
  stats,
  spreads,
  loading,
  onBrowse,
  onOpenGift,
}: {
  stats: OverviewStats | null;
  spreads: ArbitrageOpportunity[];
  loading: boolean;
  onBrowse: () => void;
  onOpenGift: (giftId: number) => void;
}) {
  return (
    <section className="page-section">
      <div className="hero-card">
        <div className="hero-copy">
          <span className="kicker">◉ Decision cockpit</span>
          <h2>
            See the market.
            <br />
            <em>Move with clarity.</em>
          </h2>
          <p>Cross-market pricing, verified identities, and fee-aware opportunities in one calm view.</p>
          <button className="outline-btn" onClick={onBrowse}>
            Browse collections
          </button>
        </div>
        <div className="signal-orbit">
          <div className="orbit-ring" />
          <div className="orbit-core">
            <span>{loading ? "--" : formatCount(stats?.events_24h ?? 0)}</span>
            <small>changes 24h</small>
          </div>
        </div>
      </div>
      <div className="metric-grid">
        <div className="metric green">
          <span>Active listings</span>
          <strong>{loading ? "--" : formatCount(stats?.active_listings ?? 0)}</strong>
          <small>{formatCount(stats?.listed_gifts ?? 0)} gifts on sale</small>
        </div>
        <div className="metric blue">
          <span>Tracked gifts</span>
          <strong>{loading ? "--" : formatCount(stats?.tracked_gifts ?? 0)}</strong>
          <small>{formatCount(stats?.collections ?? 0)} collections</small>
        </div>
        <div className="metric violet">
          <span>Sources online</span>
          <strong>{loading ? "--" : formatCount(stats?.sources_online ?? 0)}</strong>
          <small>
            {stats?.last_sync_at ? `последний синк ${formatAgo(stats.last_sync_at)}` : "ждём первый проход"}
          </small>
        </div>
      </div>
      <LiveFeed onOpen={onOpenGift} />
      <Movers onOpen={onOpenGift} />
      <div className="section-head overview-head">
        <div>
          <p className="eyebrow">NEXT ACTION</p>
          <h2>Arbitrage radar</h2>
        </div>
        <span className="fresh">
          <i /> {formatCount(spreads.length)} spreads after fees
        </span>
      </div>
      <div className="table-card">
        {loading ? (
          <LoadingState />
        ) : spreads.length ? (
          spreads.map(item => (
            <button
              className="table-row"
              key={`${item.gift_id}-${item.buy_marketplace}-${item.sell_marketplace}`}
              onClick={() => onOpenGift(item.gift_id)}
            >
              <div className="gift-cell">
                <div className="gift-icon">✦</div>
                <div>
                  <strong>{item.name ?? item.collection_name ?? `Gift #${item.gift_id}`}</strong>
                  <small>
                    {item.buy_marketplace} → {item.sell_marketplace}
                  </small>
                </div>
              </div>
              <div>
                <b>{formatTon(item.buy_price_ton)}</b>
                <small>buy</small>
              </div>
              <div>
                <b>{formatTon(item.sell_price_ton)}</b>
                <small>sell</small>
              </div>
              <div className="edge">
                <strong>{formatTonDelta(item.profit_ton)}</strong>
                <small>{formatPercent(item.profit_percent)}</small>
              </div>
            </button>
          ))
        ) : (
          <p className="muted-copy" style={{ padding: 20 }}>
            Спред появляется, когда один подарок торгуется минимум на двух площадках.
          </p>
        )}
      </div>
    </section>
  );
}
