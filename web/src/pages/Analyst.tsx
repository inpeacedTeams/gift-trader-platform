import { AiPanel } from "../components/AiPanel";
import "../components/ai.css";

/** Full page home for the assistant.
 *
 * Same panel as the overview, given room to breathe plus an explanation of
 * exactly what the model can and cannot see.
 */
export function Analyst({ enabled, authenticated }: { enabled: boolean; authenticated: boolean }) {
  return (
    <section className="page-section">
      <div className="section-head">
        <div>
          <p className="eyebrow">AI ANALYST</p>
          <h2>Спросить про рынок</h2>
        </div>
      </div>
      {enabled ? (
        <AiPanel authenticated={authenticated} />
      ) : (
        <div className="ai-panel">
          <p className="muted-copy">
            Ассистент выключен: на сервере не задан OPENROUTER_API_KEY.
          </p>
        </div>
      )}
      <div className="ai-panel">
        <strong style={{ display: "block", marginBottom: 10, fontSize: 13 }}>Что он видит</strong>
        <p className="muted-copy" style={{ margin: 0, lineHeight: 1.7 }}>
          Только нашу базу: активные листинги, floor и медиану по каждому подарку,
          движение за сутки, скидки относительно своей модели и подтверждённые сделки.
          В интернет он не ходит и цену не придумывает: если данных нет, так и скажет.
        </p>
      </div>
    </section>
  );
}
