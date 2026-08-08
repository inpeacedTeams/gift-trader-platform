import { useMemo, useState } from "react";
import { Filter, Search } from "lucide-react";
import type { Opportunity } from "../types";
import { EmptyState } from "../components/State";
import { formatCount, formatPercent, formatTon, formatTonDelta } from "../format";

export function Opportunities({ items }: { items: Opportunity[] }) {
  const [query, setQuery] = useState("");
  const [minimum, setMinimum] = useState("0");
  const filtered = useMemo(() => items.filter(item => Number(item.profit_percent) >= Number(minimum) && `${item.gift_key} ${item.buy_marketplace} ${item.sell_marketplace}`.toLowerCase().includes(query.toLowerCase())), [items, query, minimum]);
  return <section className="page-section"><div className="section-head"><div><p className="eyebrow">EXECUTION QUEUE</p><h2>Opportunities</h2></div><span className="fresh"><i/> {formatCount(filtered.length)} verified signals</span></div><div className="filter-bar"><label className="search"><Search size={16}/><input aria-label="Search opportunities" value={query} onChange={e => setQuery(e.target.value)} placeholder="Search collection or marketplace"/></label><label className="select-control"><Filter size={15}/> Minimum edge<select value={minimum} onChange={e => setMinimum(e.target.value)}><option value="0">Any</option><option value="5">5%</option><option value="10">10%</option><option value="20">20%</option></select></label></div>{filtered.length ? <div className="opportunity-grid">{filtered.map(item => <article className="opportunity-card" key={`${item.buy_listing_id}-${item.sell_listing_id}`}><div className="card-top"><span className="gift-icon">✦</span><span className="verified">VERIFIED IDENTITY</span></div><h3>{item.gift_key.split(":").slice(-1)[0]}</h3><div className="route"><span>Buy on <b>{item.buy_marketplace}</b><strong>{formatTon(item.buy_price_ton)}</strong></span><span>Sell on <b>{item.sell_marketplace}</b><strong>{formatTon(item.sell_price_ton)}</strong></span></div><div className="card-profit"><span>Net edge</span><strong>{formatTonDelta(item.profit_ton)}</strong><b>{formatPercent(item.profit_percent)}</b></div></article>)}</div> : <EmptyState title="No matching opportunities" detail="Lower the minimum edge or wait for the live collectors to refresh."/>}</section>;
}
