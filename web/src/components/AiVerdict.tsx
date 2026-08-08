import { useEffect, useState } from "react";
import { LoaderCircle, Sparkles } from "lucide-react";
import { getAiStatus, getAiVerdict } from "../api";
import "./ai.css";

type Props = {
  giftId: number;
  authenticated: boolean;
};

/** Short read on one gift, requested only when the user asks for it.
 *
 * Loading it automatically would spend the shared API budget on every page
 * view, so the call is behind a button.
 */
export function AiVerdict({ giftId, authenticated }: Props) {
  const [enabled, setEnabled] = useState(false);
  const [answer, setAnswer] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void getAiStatus()
      .then(status => setEnabled(status.enabled))
      .catch(() => setEnabled(false));
  }, []);

  useEffect(() => {
    setAnswer(null);
    setError(null);
  }, [giftId]);

  if (!enabled) return null;

  const run = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await getAiVerdict(giftId);
      setAnswer(result.answer);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ассистент недоступен");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="ai-card">
      <div className="ai-card-head">
        <Sparkles size={16} />
        <div>
          <strong>Мнение аналитика</strong>
          <small>Читает цену, соседей по модели и реальные продажи этого подарка.</small>
        </div>
        {!answer && (
          <button className="outline-btn" disabled={loading || !authenticated} onClick={() => void run()}>
            {loading ? <LoaderCircle size={14} className="spin" /> : <Sparkles size={14} />}
            {authenticated ? "Спросить" : "Нужен вход"}
          </button>
        )}
      </div>
      {answer && <p className="ai-answer">{answer}</p>}
      {error && <p className="ai-error">{error}</p>}
    </div>
  );
}
