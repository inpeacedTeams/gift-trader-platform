import { useEffect, useState } from "react";
import { Database, ExternalLink, RefreshCw, Sparkles } from "lucide-react";
import { getAiStatus, getSourceStatus, type AiStatus } from "../api";
import type { SourceStatusCard } from "../types";
import { formatAgo, formatCount } from "../format";

type Health = { label: string; tone: string };

/** Turn a raw status into something a human can act on. */
function health(source: SourceStatusCard): Health {
  if (!source.configured) return { label: "Нужен ключ", tone: "source-optional" };
  if (source.status === "disabled") return { label: "Выключен", tone: "source-muted" };
  if (source.status === "pending") return { label: "Ждёт первый проход", tone: "source-muted" };
  if (source.status !== "ok") return { label: "Не отвечает", tone: "source-down" };
  if (source.stale) return { label: "Данные устарели", tone: "source-optional" };
  return { label: "Live", tone: "source-live" };
}

export function Settings() {
  const [sources, setSources] = useState<SourceStatusCard[]>([]);
  const [ai, setAi] = useState<AiStatus | null>(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    const [status, aiStatus] = await Promise.all([
      getSourceStatus().catch(() => null),
      getAiStatus().catch(() => null),
    ]);
    setSources(status?.sources ?? []);
    setAi(aiStatus);
    setLoading(false);
  };

  useEffect(() => {
    void load();
  }, []);

  return (
    <section className="page-section">
      <div className="section-head">
        <div>
          <p className="eyebrow">CONTROL ROOM</p>
          <h2>Settings</h2>
        </div>
        <button className="icon-btn" aria-label="Refresh status" onClick={() => void load()}>
          <RefreshCw size={16} className={loading ? "spin" : ""} />
        </button>
      </div>
      <div className="settings-grid stagger">
        <article className="settings-card lift">
          <div className="settings-title">
            <Database size={18} />
            <h3>Источники данных</h3>
          </div>
          {sources.length ? (
            sources.map(source => {
              const state = health(source);
              return (
                <div className="setting-line" key={source.marketplace}>
                  <div>
                    <span>{source.marketplace}</span>
                    <small className="source-meta">
                      {source.last_success_at
                        ? `${formatCount(source.listings_count)} лотов · ${formatAgo(source.last_success_at)}`
                        : source.last_error ?? "нет данных"}
                    </small>
                  </div>
                  <b className={state.tone}>{state.label}</b>
                </div>
              );
            })
          ) : (
            <p className="muted-copy">{loading ? "Загружаю статус..." : "Статус недоступен."}</p>
          )}
        </article>
        <article className="settings-card lift">
          <div className="settings-title">
            <Sparkles size={18} />
            <h3>AI-аналитик</h3>
          </div>
          <div className="setting-line">
            <span>Статус</span>
            <b className={ai?.enabled ? "source-live" : "source-muted"}>
              {ai?.enabled ? "Включён" : "Нужен ключ"}
            </b>
          </div>
          <div className="setting-line">
            <span>Модель</span>
            <b className="source-meta">{ai?.model ?? "не задана"}</b>
          </div>
          {ai?.hourly_limit ? (
            <div className="setting-line">
              <span>Лимит запросов</span>
              <b className="source-meta">{ai.hourly_limit} в час</b>
            </div>
          ) : null}
          <p className="muted-copy">
            Настройки задаются на сервере в .env, чтобы ключи не уезжали в браузер.
          </p>
        </article>
      </div>
      <a
        className="docs-link"
        href="https://github.com/inpeacedTeams/gift-trader-platform"
        target="_blank"
        rel="noreferrer"
      >
        Open project documentation <ExternalLink size={14} />
      </a>
    </section>
  );
}
