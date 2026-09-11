import { useEffect, useRef, useState } from "react";

function formatInsight(text) {
  return text.split("\n").map((line, index) => {
    const heading = line.trim().match(/^\*\*(.+?)\*\*:?$/);
    if (heading) return <h4 className="network-ai-heading" key={`${index}-${line}`}>{heading[1]}</h4>;
    const parts = line.split(/(\*\*.+?\*\*)/g);
    return <p className="network-ai-line" key={`${index}-${line}`}>{parts.map((part, partIndex) => {
      const bold = part.match(/^\*\*(.+?)\*\*$/);
      return bold ? <strong key={partIndex}>{bold[1]}</strong> : part;
    })}</p>;
  });
}

export default function NetworkExplanation({ id, selection, onClear }) {
  const [explanation, setExplanation] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const request = useRef(null);

  useEffect(() => () => request.current?.abort(), []);

  async function explain() {
    if (!selection || request.current) return;
    const controller = new AbortController();
    request.current = controller;
    setLoading(true);
    setError("");
    try {
      const response = await fetch(`/api/criminals/${encodeURIComponent(id)}/explain`, {
        method: "POST", signal: controller.signal,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ selection: { type: selection.type, id: selection.id } }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Unable to generate an insight.");
      if (typeof data.explanation !== "string" || !data.explanation.trim()) throw new Error("No insight was returned. Please try again.");
      if (!controller.signal.aborted) setExplanation(data.explanation);
    } catch (err) {
      if (!controller.signal.aborted) setError(
        err instanceof SyntaxError || err instanceof TypeError
          ? "Cannot reach the backend. Start or restart FastAPI on port 5050, then try again."
          : err.message
      );
    } finally {
      request.current = null;
      if (!controller.signal.aborted) setLoading(false);
    }
  }

  return (
    <section className="network-ai" aria-labelledby="network-ai-title" aria-busy={loading}>
      <h3 id="network-ai-title">AI insight</h3>
      <p>{selection ? `Selected: ${selection.label}` : "Select a node or relationship in the graph to enable AI insight."}</p>
      {selection && <p>Review the evidence, investigative significance, and follow-up checks for this selection. The configured AI provider receives the relevant records.</p>}
      <button className="stamp-btn small" onClick={explain} disabled={!selection || loading}>
        {loading ? "Generating insight…" : explanation ? "Regenerate insight" : "AI insight"}
      </button>
      {selection && <button className="stamp-btn small" type="button" onClick={onClear}>Clear selection</button>}
      {loading && <p role="status">Reading the available records…</p>}
      {error && <p className="network-ai-error" role="alert">{error}</p>}
      {explanation && <div className="network-ai-answer" aria-live="polite">{formatInsight(explanation)}</div>}

    </section>
  );
}
