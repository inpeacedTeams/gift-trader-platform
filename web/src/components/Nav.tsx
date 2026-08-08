import { Activity, Bell, Briefcase, Crosshair, FlaskConical, Gem, Layers, LayoutDashboard, Settings2, Sparkles, Star, Store, Tag, Wallet } from "lucide-react";

export type View =
  | "overview"
  | "collections"
  | "gifts"
  | "deals"
  | "sniper"
  | "analyst"
  | "research"
  | "opportunities"
  | "watchlist"
  | "positions"
  | "selling"
  | "portfolio"
  | "alerts"
  | "settings";

export function Nav({ view, onChange, count }: { view: View; onChange: (view: View) => void; count: number }) {
  const items: { id: View; label: string; icon: typeof LayoutDashboard }[] = [
    { id: "overview", label: "Overview", icon: LayoutDashboard },
    { id: "collections", label: "Collections", icon: Layers },
    { id: "gifts", label: "Gifts", icon: Gem },
    { id: "deals", label: "Deals", icon: Tag },
    { id: "sniper", label: "Sniper", icon: Crosshair },
    { id: "analyst", label: "Analyst", icon: Sparkles },
    { id: "research", label: "Research", icon: FlaskConical },
    { id: "opportunities", label: "Opportunities", icon: Activity },
    { id: "watchlist", label: "Watchlist", icon: Star },
    { id: "positions", label: "Positions", icon: Briefcase },
    { id: "selling", label: "Selling", icon: Store },
    { id: "portfolio", label: "Portfolio", icon: Wallet },
    { id: "alerts", label: "Alerts", icon: Bell },
  ];
  return <nav className="side-nav" aria-label="Primary navigation">{items.map(({ id, label, icon: Icon }) => <button key={id} className={view === id ? "active" : ""} onClick={() => onChange(id)}><Icon size={18} /><span>{label}</span>{id === "opportunities" && <b>{count}</b>}</button>)}<button className={view === "settings" ? "active" : ""} onClick={() => onChange("settings")}><Settings2 size={18}/><span>Settings</span></button></nav>;
}
