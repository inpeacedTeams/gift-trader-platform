import { useEffect, useState } from "react";
import { LoaderCircle, Sparkles } from "lucide-react";
import { getAiStatus, getGiftVerdict } from "../api";
import "./ai.css";

type Props = {
  giftId: number;
  authenticated: boolean;
  /** Skips the status call when the parent already knows. */
  enabled?: boolean;
};

/** A short read on one gift, grounded in the rows we hold for it.
 *
 * Fetched on click, not on mount: most gift page visits are browsing, and
 * every verdict costs a model round trip against a shared hourly budget.
 */
export function Verdict({ giftId, authenticated, enabled }: Props) {
  const [available, setAvailable] = useState(enabled ?? false);
  const [text, setText] = useState<string | null>(null);
  const [model, setModel] = useState<string | null>(null);
  const [cached, setCached] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (enabled !== undefined) {
      setAvailable(enabled);
      return;
    }
    void getAiStatus()
      .then(status => setAvailable(status.enabled))
      .catch(() => setAvailable(false));
  }, [enabled]);

  // A verdict belongs to one gift. Moving to another one has to clear it.
  useEffect(() => {
    setText(null);
    setModel(null);
    setCached(false);
    setError(null);
  }, [giftId]);

  if (!available) return null;

  const run = async () => {
    if (pending) return;
    setPending(true);
    setError(null);
    try {
      const reply = await getGiftVerdict(giftId);
      setText(reply.answer);
      setModel(reply.model);
      setCached(Boolean(reply.cached));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Аналитик недоступен");
    } finally {
      setPending(false);
    }
  };

  return (
    <section className="ai-panel">
      <div className="ai-head">
        <Sparkles size={17} />
        <div>
          <strong>Вердикт по подарку</strong>
          <small>Считает по нашим ценам и сделкам. Ничего не додумывает.</small>
        </div>
        {authenticated && (
          <button className="outline-btn" onClick={() => void run()} disabled={pending}>
            {pending ? <LoaderCircle size={14} className="spin" /> : <Sparkles size={14} />}
            {text ? "Пересчитать" : "Оценить"}
          </button>
        )}
      </div>
      {!authenticated ? (
        <p className="muted-copy">Войдите через Telegram, чтобы получить оценку.</p>
      ) : (
        <>
          {error && <p className="ai-error">{error}</p>}
          {text && (
            <div className="ai-answer">
              <p>{text}</p>
              <small>{cached && model ? `${model} · из кэша` : model}</small>
            </div>
          )}
        </>
      )}
    </section>
  );
}
