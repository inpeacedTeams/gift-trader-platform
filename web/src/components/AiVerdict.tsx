import { useState } from "react";
import { LoaderCircle, Sparkles } from "lucide-react";
import { getAiVerdict } from "../api";
import "./ai.css";

/** On demand read of a single gift.
 *
 * Deliberately not auto-loaded: every view would otherwise cost a call,
 * and most visits to a gift page are just browsing.
 */
export function AiVerdict({ giftId, enabled, authenticated }: { giftId: number; enabled: boolean; authenticated: boolean }) {
  const [verdict, setVerdict] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!enabled) return null;

  const load = async () => {
    setPending(true);
    setError(null);
    try {
      const reply = await getAiVerdict(giftId);
      setVerdict(reply.answer);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ассистент недоступен");
    } finally {
      setPending(false);
    }
  };

  return (
    <div className="ai-verdict">
      <div className="ai-head">
        <Sparkles size={16} />
        <div>
          <strong>Разбор от аналитика</strong>
          <small>Оценка по нашим данным: цена, глубина и реальные сделки.</small>
        </div>
        {!verdict && authenticated && (
          <button className="outline-btn" onClick={() => void load()} disabled={pending}>
            {pending ? <LoaderCircle size={14} className="spin" /> : <Sparkles size={14} />}
            Разобрать
          </button>
        )}
      </div>
      {!authenticated && <p className="muted-copy">Доступно после входа через Telegram.</p>}
      {error && <p className="ai-error">{error}</p>}
      {verdict && <pre className="ai-verdict-body">{verdict}</pre>}
    </div>
  );
}
