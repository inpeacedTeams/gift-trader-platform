import { useEffect, useState } from "react";
import { LoaderCircle, Sparkles } from "lucide-react";
import { getAiStatus, getGiftVerdict } from "../api";
import "../assistant.css";

/** On demand read of one gift.
 *
 * Generated on click, not on page load: every call costs us money and most
 * visitors are just browsing.
 */
export function Verdict({ giftId, authenticated }: { giftId: number; authenticated: boolean }) {
  const [enabled, setEnabled] = useState(false);
  const [text, setText] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setText(null);
    setError(null);
    void getAiStatus()
      .then(status => setEnabled(status.enabled))
      .catch(() => setEnabled(false));
  }, [giftId]);

  if (!enabled || !authenticated) return null;

  const run = async () => {
    setPending(true);
    setError(null);
    try {
      const result = await getGiftVerdict(giftId);
      setText(result.answer);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось получить оценку");
    } finally {
      setPending(false);
    }
  };

  return (
    <div className="verdict-card">
      <div className="verdict-head">
        <Sparkles size={16} />
        <div>
          <strong>Стоит ли брать</strong>
          <small>Короткая оценка по нашим данным о цене, истории и продажах.</small>
        </div>
        {!text && (
          <button className="outline-btn" onClick={() => void run()} disabled={pending}>
            {pending ? <LoaderCircle size={14} className="spin" /> : <Sparkles size={14} />}
            {pending ? "Считаю" : "Оценить"}
          </button>
        )}
      </div>
      {text && <p className="verdict-text">{text}</p>}
      {error && <p className="verdict-error">{error}</p>}
    </div>
  );
}
