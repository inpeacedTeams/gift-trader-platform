import { useEffect, useState } from "react";
import { AlertTriangle, Crosshair, FlaskConical, Save, Sparkles, Trash2 } from "lucide-react";
import {
  armStrategy,
  backtestStrategy,
  deleteStrategy,
  discoverStrategies,
  explainStrategy,
  getSavedStrategies,
  proposeStrategy,
  saveStrategy,
  type Backtest,
  type SavedStrategy,
  type Strategy,
  type StrategyMetrics,
} from "../api";
import { ErrorState } from "../components/State";
import { formatCount, formatTonDelta } from "../format";
import "../research.css";

type Props = { authenticated: boolean; aiEnabled?: boolean };

const WINDOWS = [7, 14, 30];

function percent(value?: number | null): string {
  if (value === null || value === undefined) return "--";
  return `${value > 0 ? "+" : ""}${value.toFixed(1)}%`;
}

function tone(value?: number | null): string {
  if (value === null || value === undefined) return "";
  return value >= 0 ? "res-up" : "res-down";
}

/** One half of the split, as a column.
 *
 * Both halves are always shown. The in-sample number is the one a backtest
 * tool normally puts in a big font, and it is the one that means the least.
 */
function Column({ title, note, metrics }: { title: string; note: string; metrics: StrategyMetrics }) {
  return (
    <div className="res-column">
      <span className="res-column-title">{title}</span>
      <small className="res-column-note">{note}</small>
      {metrics.trades === 0 ? (
        <b className="res-empty">нет сделок</b>
      ) : (
        <>
          <b className={tone(metrics.median_profit_percent)}>{percent(metrics.median_profit_percent)}</b>
          <small>
            {formatCount(metrics.trades)} сделок · {metrics.win_rate?.toFixed(0)}% в плюс
          </small>
          <small>итог {formatTonDelta(metrics.total_profit_ton)}</small>
        </>
      )}
    </div>
  );
}

function Result({
  result,
  aiEnabled,
  windowDays,
  onSaved,
}: {
  result: Backtest;
  aiEnabled: boolean;
  windowDays: number;
  onSaved: () => void;
}) {
  const [explanation, setExplanation] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const insufficient = result.status !== "ok";
  const badge = insufficient
    ? { text: "Мало данных", tone: "res-badge-unknown" }
    : result.holds_up
    ? { text: "Подтвердилась на проверке", tone: "res-badge-ok" }
    : { text: "Не подтвердилась", tone: "res-badge-warn" };

  const act = async (action: () => Promise<void>) => {
    setBusy(true);
    try {
      await action();
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не получилось");
    } finally {
      setBusy(false);
    }
  };

  return (
    <article className="res-card">
      <header className="res-head">
        <div>
          <strong>{result.strategy.name}</strong>
          <small>{result.summary}</small>
        </div>
        <span className={`res-badge ${badge.tone}`}>{badge.text}</span>
      </header>

      {result.conditions.length > 0 && (
        <ul className="res-chips">
          {result.conditions.map(condition => (
            <li key={condition}>{condition}</li>
          ))}
        </ul>
      )}

      {insufficient ? (
        <p className="res-note warn">
          <AlertTriangle size={13} /> {result.reason}
        </p>
      ) : (
        <>
          <div className="res-columns">
            <Column
              title="Отбор"
              note="первая половина истории"
              metrics={result.in_sample}
            />
            <Column
              title="Проверка"
              note="вторая половина, её стратегия не видела"
              metrics={result.out_of_sample}
            />
          </div>
          <p className="res-note">
            Всего {formatCount(result.overall.trades)} сделок за {result.history_days} дней истории.
            Худшая {percent(result.overall.worst_percent)}, лучшая {percent(result.overall.best_percent)}.
            {result.overall.unresolved > 0 &&
              ` Ещё ${result.overall.unresolved} входов не успели закрыться и в расчёт не вошли.`}
          </p>

          {result.examples.length > 0 && (
            <div className="res-trades">
              <span className="res-trades-title">Худшие сделки из выборки</span>
              {result.examples.map(trade => (
                <div className="res-trade" key={`${trade.gift_id}-${trade.entry_at}`}>
                  <span>{trade.gift_name ?? `Gift #${trade.gift_id}`}</span>
                  <span>
                    {trade.entry_price} → {trade.exit_price} TON
                  </span>
                  <span className={tone(trade.profit_percent)}>{percent(trade.profit_percent)}</span>
                  <small>{trade.sold ? "лот ушёл с рынка" : "лот остался висеть"}</small>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {explanation && <p className="res-explain">{explanation}</p>}
      {error && <p className="res-note warn">{error}</p>}

      <footer className="res-actions">
        <button
          className="outline-btn"
          disabled={busy}
          onClick={() =>
            void act(async () => {
              await saveStrategy(result.strategy, "discovered", windowDays);
              onSaved();
            })
          }
        >
          <Save size={13} /> Сохранить
        </button>
        {aiEnabled && !insufficient && (
          <button
            className="outline-btn"
            disabled={busy}
            onClick={() =>
              void act(async () => {
                const reply = await explainStrategy(result.strategy, windowDays);
                setExplanation(reply.explanation);
              })
            }
          >
            <Sparkles size={13} /> Объяснить
          </button>
        )}
      </footer>
    </article>
  );
}

/** Strategy research.
 *
 * The search and the simulation are plain arithmetic over stored history.
 * The assistant only translates a request into thresholds and puts a
 * finished result into words, which is why the numbers here can be trusted
 * in a way that "ask the AI how this strategy did" never could.
 */
export function Research({ authenticated, aiEnabled = false }: Props) {
  const [windowDays, setWindowDays] = useState(30);
  const [results, setResults] = useState<Backtest[]>([]);
  const [meta, setMeta] = useState<{ tested: number; history: number; reason?: string | null } | null>(null);
  const [saved, setSaved] = useState<SavedStrategy[]>([]);
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [armNote, setArmNote] = useState<string | null>(null);

  const loadSaved = async () => {
    try {
      setSaved(await getSavedStrategies());
    } catch {
      setSaved([]);
    }
  };

  useEffect(() => {
    if (authenticated) void loadSaved();
  }, [authenticated]);

  const run = async (action: () => Promise<void>) => {
    setBusy(true);
    setError(null);
    try {
      await action();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не получилось");
    } finally {
      setBusy(false);
    }
  };

  const discover = () =>
    run(async () => {
      const found = await discoverStrategies(windowDays);
      setResults(found.results);
      setMeta({ tested: found.tested, history: found.history_days, reason: found.reason });
    });

  const ask = () =>
    run(async () => {
      const reply = await proposeStrategy(question.trim(), windowDays);
      setResults([reply.backtest]);
      setMeta(null);
    });

  const rerun = (strategy: Strategy) =>
    run(async () => {
      setResults([await backtestStrategy(strategy, windowDays)]);
      setMeta(null);
    });

  const arm = (strategyId: number) =>
    run(async () => {
      const armed = await armStrategy(strategyId);
      setArmNote(
        armed.dropped.length
          ? `Снайпер вооружён, но без условий: ${armed.dropped.join(", ")}. Живое правило слабее протестированного.`
          : "Снайпер вооружён целиком по этой стратегии."
      );
    });

  if (!authenticated) {
    return (
      <section className="page-section">
        <p className="muted-copy">Войдите через Telegram, чтобы искать и сохранять стратегии.</p>
      </section>
    );
  }

  return (
    <section className="page-section">
      <div className="res-intro">
        <FlaskConical size={18} />
        <div>
          <strong>Поиск стратегий по истории</strong>
          <p>
            Движок перебирает правила и проигрывает их на сохранённых листингах и снимках цен. Историю
            делим пополам: на первой половине стратегия отбирается, на второй проверяется. Считается
            только та половина, которую она не выбирала. Выход берётся по цене через N часов за вычетом
            комиссии и газа, исчезновение лота не считается доказательством цены продажи.
          </p>
        </div>
      </div>

      <div className="res-controls">
        <div className="res-window">
          {WINDOWS.map(days => (
            <button
              key={days}
              className={days === windowDays ? "active" : ""}
              onClick={() => setWindowDays(days)}
            >
              {days} дней
            </button>
          ))}
        </div>
        <button className="primary-btn" disabled={busy} onClick={() => void discover()}>
          <FlaskConical size={14} /> {busy ? "Считаю…" : "Найти стратегии"}
        </button>
      </div>

      {aiEnabled && (
        <div className="res-ask">
          <input
            value={question}
            onChange={event => setQuestion(event.target.value)}
            placeholder="Например: дешёвые редкие подарки, которые быстро продаются"
            onKeyDown={event => {
              if (event.key === "Enter" && question.trim().length > 2) void ask();
            }}
          />
          <button className="outline-btn" disabled={busy || question.trim().length < 3} onClick={() => void ask()}>
            <Sparkles size={13} /> Собрать правило
          </button>
          <small>AI выбирает пороги. Цифры считает движок.</small>
        </div>
      )}

      {error && <ErrorState detail={error} retry={() => void discover()} />}
      {armNote && <p className="res-note">{armNote}</p>}

      {meta && (
        <p className="muted-copy">
          Проверено комбинаций: {meta.tested}. Истории: {meta.history} дней.
          {meta.reason ? ` ${meta.reason}` : ""}
        </p>
      )}

      <div className="res-list">
        {results.map((result, index) => (
          <Result
            key={`${result.strategy.name}-${index}`}
            result={result}
            aiEnabled={aiEnabled}
            windowDays={windowDays}
            onSaved={() => void loadSaved()}
          />
        ))}
      </div>

      {saved.length > 0 && (
        <>
          <div className="section-head">
            <div>
              <p className="eyebrow">SAVED</p>
              <h3>Мои стратегии</h3>
            </div>
          </div>
          <div className="table-card">
            {saved.map(item => (
              <div className="res-saved" key={item.id}>
                <button className="res-saved-main" onClick={() => void rerun(item.definition)}>
                  <strong>{item.name}</strong>
                  <small>{item.summary}</small>
                </button>
                <div>
                  <b className={tone(item.last_out_of_sample_percent)}>
                    {percent(item.last_out_of_sample_percent)}
                  </b>
                  <small>на проверке · {formatCount(item.last_trades ?? 0)} сделок</small>
                </div>
                <div className="res-saved-actions">
                  <button className="outline-btn" disabled={busy} onClick={() => void arm(item.id)}>
                    <Crosshair size={13} /> Вооружить
                  </button>
                  <button
                    className="icon-btn"
                    aria-label="Удалить стратегию"
                    onClick={() => void deleteStrategy(item.id).then(loadSaved)}
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </section>
  );
}
