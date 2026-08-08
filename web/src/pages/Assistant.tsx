import { FormEvent, useEffect, useRef, useState } from "react";
import { LoaderCircle, Send, Sparkles } from "lucide-react";
import { askAssistant, getAiStatus } from "../api";
import { EmptyState } from "../components/State";
import "../assistant.css";

type Turn = { role: "user" | "assistant"; text: string };

const OPENERS = [
  "Какие подарки сейчас недооценены?",
  "Что сильнее всего выросло за сутки?",
  "На какой площадке дешевле всего заходить?",
  "Какие коллекции самые ликвидные?",
];

/** Market questions answered from our own database, never from the open web. */
export function Assistant({ authenticated }: { authenticated: boolean }) {
  const [enabled, setEnabled] = useState<boolean | null>(null);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [question, setQuestion] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [remaining, setRemaining] = useState<number | null>(null);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    void getAiStatus()
      .then(status => setEnabled(status.enabled))
      .catch(() => setEnabled(false));
  }, []);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [turns, pending]);

  const send = async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || pending) return;
    setTurns(current => [...current, { role: "user", text: trimmed }]);
    setQuestion("");
    setPending(true);
    setError(null);
    try {
      const result = await askAssistant(trimmed);
      setTurns(current => [...current, { role: "assistant", text: result.answer }]);
      setRemaining(result.remaining_today);
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

  if (enabled === false) {
    return (
      <section className="page-section">
        <EmptyState
          title="Ассистент выключен"
          detail="Добавьте OPENROUTER_API_KEY в окружение бэкенда, чтобы включить его."
        />
      </section>
    );
  }

  if (!authenticated) {
    return (
      <section className="page-section">
        <EmptyState
          title="Нужен вход"
          detail="Войдите через Telegram, чтобы задавать вопросы по рынку."
        />
      </section>
    );
  }

  return (
    <section className="page-section assistant">
      <div className="section-head">
        <div>
          <p className="eyebrow">MARKET ASSISTANT</p>
          <h2>Спросите про рынок</h2>
        </div>
        {remaining !== null && <span className="fresh">осталось {remaining} на сегодня</span>}
      </div>

      <div className="chat-log">
        {turns.length === 0 && (
          <div className="chat-intro">
            <Sparkles size={20} />
            <p>
              Отвечаю только по данным, которые мы собрали с площадок. Если чего-то нет в базе,
              так и скажу, а не придумаю цифру.
            </p>
            <div className="openers">
              {OPENERS.map(item => (
                <button key={item} className="opener" onClick={() => void send(item)}>
                  {item}
                </button>
              ))}
            </div>
          </div>
        )}
        {turns.map((turn, index) => (
          <div className={`bubble ${turn.role}`} key={index}>
            {turn.text}
          </div>
        ))}
        {pending && (
          <div className="bubble assistant thinking">
            <LoaderCircle size={15} className="spin" /> Смотрю данные...
          </div>
        )}
        <div ref={endRef} />
      </div>

      {error && <div className="notice error">{error}</div>}

      <form className="chat-input" onSubmit={submit}>
        <input
          value={question}
          onChange={event => setQuestion(event.target.value)}
          placeholder="Например: какие Plush Pepe сейчас дешевле медианы?"
          maxLength={500}
        />
        <button className="outline-btn" disabled={pending || !question.trim()}>
          {pending ? <LoaderCircle size={15} className="spin" /> : <Send size={15} />} Спросить
        </button>
      </form>
    </section>
  );
}
