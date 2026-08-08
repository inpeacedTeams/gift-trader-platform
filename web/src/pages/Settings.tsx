import { useState } from "react";
import { Database, ExternalLink, ShieldCheck } from "lucide-react";
import { Select } from "../components/Select";

const CURRENCIES = [{ value: "TON", label: "TON", hint: "Native settlement currency" }];

export function Settings() {
  const [currency, setCurrency] = useState("TON");
  return (
    <section className="page-section">
      <div className="section-head">
        <div>
          <p className="eyebrow">CONTROL ROOM</p>
          <h2>Settings</h2>
        </div>
      </div>
      <div className="settings-grid stagger">
        <article className="settings-card lift">
          <div className="settings-title">
            <Database size={18} />
            <h3>Data sources</h3>
          </div>
          <div className="setting-line">
            <span>Tonnel</span>
            <b className="source-live">Live</b>
          </div>
          <div className="setting-line">
            <span>GetGems / TONAPI</span>
            <b className="source-live">Live</b>
          </div>
          <div className="setting-line">
            <span>Portals</span>
            <b className="source-optional">Needs auth</b>
          </div>
        </article>
        <article className="settings-card lift">
          <div className="settings-title">
            <ShieldCheck size={18} />
            <h3>Trading guardrails</h3>
          </div>
          <label className="field">
            Minimum net edge
            <input type="number" min="0" defaultValue="10" />
            <small>Signals below this percentage stay hidden.</small>
          </label>
          <div className="field">
            Currency
            <div className="field-control">
              <Select label="Currency" value={currency} onChange={setCurrency} options={CURRENCIES} />
            </div>
          </div>
        </article>
      </div>
      <a className="docs-link" href="https://github.com/inpeacedTeams/gift-trader-platform" target="_blank" rel="noreferrer">
        Open project documentation <ExternalLink size={14} />
      </a>
    </section>
  );
}
