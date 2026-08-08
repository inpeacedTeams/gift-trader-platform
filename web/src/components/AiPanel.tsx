import { FormEvent, useEffect, useState } from "react";
import { LoaderCircle, Send, Sparkles } from "lucide-react";
import { askAi, getAiStatus } from "../api";
import "./ai.css";

const SUGGESTIONS = [
  "Что сейчас недооценено?",
  "Какие подарки сильнее всего упали за сутки?",
  "Где самый большой спред между площадками?",
];

/** Market questions answered from our own database.
 *
 * The key lives on the server, so the browser only ever talks to our API.
 */
export function AiPanel({ authenticated }: { authenticated: boolean }) {
  const [enabled, setEnabled] = useState(false);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<string | null>(null);
  const [model, setModel] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void getAiStatus()
      .then(status => setEnabled(status.enabled))
      .catch(() => setEnabled(false));
  }, []);

  if (!enabled) return null;

  const send = async (text: string) => {
    const trimmed = text.trim();
    if (trimmed.length < 3 || pending) return;
    setPending(true);
    setError(null);
    try {
      const reply = await askAi(trimmed);
      setAnswer(reply.answer);
      setModel(reply.model);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ассистент недоступен");
    } finally {
      setPending(false);
    }
  };

  const submit = (event: FormEvent) => {
    event.preventDefault();
    void send(question);
  };

  return (
    <section className="ai-panel">
      <div className="ai-head">
        <Sparkles size={17} />
        <div>
          <strong>Спросить аналитика</strong>
          <small>Отвечает только по собранным нами данным. Цены не выдумывает.</small>
        </div>
      </div>
      {authenticated ? (
        <>
          <form className="ai-form" onSubmit={submit}>
            <input
              value={question}
              onChange={event => setQuestion(event.target.value)}
              placeholder="Например: какие Plush Pepe сейчас дешевле медианы?"
              maxLength={500}
            />
            <button className="outline-btn" disabled={pending || question.trim().length < 3}>
              {pending ? <LoaderCircle size={14} className="spin" /> : <Send size={14} />}
              Спросить
            </button>
          </form>
          <div className="ai-suggestions">
            {SUGGESTIONS.map(item => (
              <button
                key={item}
                type="button"
                className="ai-chip"
                disabled={pending}
                onClick={() => {
                  setQuestion(item);
                  void send(item);
                }}
              >
                {item}
              </button>
            ))}
          </div>
          {error && <p className="ai-error">{error}</p>}
          {answer && (
            <div className="ai-answer">
              <p>{answer}</p>
              {model && <small>{model}</small>}
            </div>
          )}
        </>
      ) : (
        <p className="muted-copy">Войдите через Telegram, чтобы задавать вопросы по рынку.</p>
      )}
    </section>
  );
}
