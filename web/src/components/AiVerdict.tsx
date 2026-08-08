import { useState } from "react";
import { LoaderCircle, Sparkles } from "lucide-react";
import { getAiVerdict } from "../api";
import "./ai.css";

type Props = {
  giftId: number;
  enabled: boolean;
  authenticated: boolean;
};

/** Short read on one gift, requested only when the user asks for it.
 *
 * Loading it automatically would burn the shared API quota on every page view.
 */
export function AiVerdict({ giftId, enabled, authenticated }: Props) {
  const [answer, setAnswer] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!enabled) return null;

  const run = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await getAiVerdict(giftId);
      setAnswer(result.answer);
    } catch (e) {
      setError(e instanceof Error ? e.message : "The analyst is unavailable");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="ai-card">
      <div className="ai-card-head">
        <Sparkles size={16} />
        <div>
          <strong>Analyst verdict</strong>
          <small>Reads floor, peers and confirmed sales for this gift.</small>
        </div>
        {!answer && (
          <button className="outline-btn" disabled={loading || !authenticated} onClick={() => void run()}>
            {loading ? <LoaderCircle size={14} className="spin" /> : <Sparkles size={14} />}
            {authenticated ? "Ask" : "Sign in"}
          </button>
        )}
      </div>
      {answer && <p className="ai-answer">{answer}</p>}
      {error && <p className="ai-error">{error}</p>}
    </div>
  );
}
