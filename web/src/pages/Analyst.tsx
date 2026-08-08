import { FormEvent, useState } from "react";
import { LoaderCircle, Send, Sparkles } from "lucide-react";
import { askAi } from "../api";
import "../components/ai.css";

const SUGGESTIONS = [
  "Какие подарки сейчас недооценены и почему?",
  "Что сильнее всего просело за сутки?",
  "Какая коллекция самая ликвидная прямо сейчас?",
  "Где расходятся цены между площадками?",
];

type Turn = { question: string; answer: string };

/** Market questions answered from stored data only. */
export function Analyst({ enabled, authenticated }: { enabled: boolean; authenticated: boolean }) {
  const [question, setQuestion] = useState("");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const ask = async (text: string) => {
    const trimmed = text.trim();
    if (trimmed.length < 3 || loading) return;
    setLoading(true);
    setError(null);
    try {
      const result = await askAi(trimmed);
      setTurns(items => [{ question: trimmed, answer: result.answer }, ...items]);
      setQuestion("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "The analyst is unavailable");
    } finally {
      setLoading(false);
    }
  };

  const submit = (event: FormEvent) => {
    event.preventDefault();
    void ask(question);
  };

  return (
    <section className="page-section">
      <div className="section-head">
        <div>
          <p className="eyebrow">MARKET ANALYST</p>
          <h2>Ask about the market.</h2>
        </div>
        <span className="fresh">grounded in stored data</span>
      </div>

      {!enabled ? (
        <div className="ai-card guest">
          <Sparkles size={18} />
          <p>The analyst is switched off. Add OPENROUTER_API_KEY to the backend to enable it.</p>
        </div>
      ) : !authenticated ? (
        <div className="ai-card guest">
          <Sparkles size={18} />
          <p>Sign in through Telegram to ask the analyst.</p>
        </div>
      ) : (
        <>
          <form className="ai-form" onSubmit={submit}>
            <input
              value={question}
              onChange={event => setQuestion(event.target.value)}
              placeholder="Например: стоит ли брать Plush Pepe по текущей цене?"
              maxLength={500}
            />
            <button className="outline-btn" disabled={loading || question.trim().length < 3}>
              {loading ? <LoaderCircle size={14} className="spin" /> : <Send size={14} />} Ask
            </button>
          </form>
          <div className="ai-suggestions">
            {SUGGESTIONS.map(item => (
              <button key={item} className="ai-chip" disabled={loading} onClick={() => void ask(item)}>
                {item}
              </button>
            ))}
          </div>
          {error && <p className="ai-error">{error}</p>}
          {loading && (
            <div className="ai-card thinking">
              <LoaderCircle size={16} className="spin" />
              <p>Reading the market...</p>
            </div>
          )}
          <div className="ai-thread">
            {turns.map((turn, index) => (
              <div className="ai-turn" key={`${index}-${turn.question}`}>
                <strong>{turn.question}</strong>
                <p>{turn.answer}</p>
              </div>
            ))}
          </div>
        </>
      )}
    </section>
  );
}
