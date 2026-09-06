import { useEffect, useRef, useState } from "react";

export default function NetworkExplanation({ id }) {
  const [explanation, setExplanation] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const request = useRef(null);

  useEffect(() => () => request.current?.abort(), []);

  async function explain() {
    if (request.current) return;
    const controller = new AbortController();
    request.current = controller;
    setLoading(true);
    setError("");
    try {
      const response = await fetch(`/api/criminals/${encodeURIComponent(id)}/explain`, {
        method: "POST", signal: controller.signal,
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Unable to generate a summary.");
      if (typeof data.explanation !== "string" || !data.explanation.trim()) throw new Error("No summary was returned. Please try again.");
      if (!controller.signal.aborted) setExplanation(data.explanation);
    } catch (err) {
      if (!controller.signal.aborted) setError(err instanceof SyntaxError ? "The AI service is unavailable. Check that the backend is running." : err.message);
    } finally {
      request.current = null;
      if (!controller.signal.aborted) setLoading(false);
    }
  }

  return (
    <section className="network-ai" aria-labelledby="network-ai-title" aria-busy={loading}>
      <h3 id="network-ai-title">AI network summary</h3>
      <p>Explain this profile’s cases and shared locations or crime types. Generating a summary sends relevant records to Groq.</p>
      <button className="stamp-btn" onClick={explain} disabled={loading}>
        {loading ? "Generating summary…" : explanation ? "Regenerate summary" : "Explain this network"}
      </button>
      {loading && <p role="status">Reading the available records…</p>}
      {error && <p className="network-ai-error" role="alert">{error}</p>}
      {explanation && <div className="network-ai-answer" aria-live="polite">{explanation}</div>}
      <p className="network-ai-note">AI can make mistakes. Verify against source records. Shared attributes do not establish a personal relationship or guilt.</p>
    </section>
  );
}
