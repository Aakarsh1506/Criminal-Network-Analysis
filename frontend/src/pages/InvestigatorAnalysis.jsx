import { useState } from "react";
import { useParams } from "react-router-dom";
import RelationGraph from "../components/RelationGraph";
import "./InvestigatorAnalysis.css";

export default function InvestigatorAnalysis() {
  const { id } = useParams();
  const [selection, setSelection] = useState(null);
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [phase, setPhase] = useState("");

  async function ask(event) {
    event.preventDefault();
    const text = question.trim();
    if (!text || !selection || loading) return;
    setQuestion(""); setLoading(true); setPhase("Thinking…");
    const phaseTimer = window.setTimeout(() => setPhase("Reviewing selected records…"), 900);
    setMessages((current) => [...current, { role: "user", text }]);
    try {
      const response = await fetch(`/api/criminals/${encodeURIComponent(id)}/explain`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ selection: { type: selection.type, id: selection.id }, question: text }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Unable to generate an analysis.");
      setMessages((current) => [...current, { role: "assistant", text: data.explanation }]);
    } catch (error) { setMessages((current) => [...current, { role: "error", text: error.message }]); }
    finally { window.clearTimeout(phaseTimer); setLoading(false); setPhase(""); }
  }

  return <main className="analysis-page">
    <header className="analysis-header"><p className="form-number">Investigator workspace</p><h1>Network analysis</h1><p>Select a connection on the left, then ask the AI about the evidence.</p></header>
    <div className="analysis-layout">
      <section className="analysis-connections"><h2>Connections</h2><RelationGraph mainCriminal={{ id, name: "Selected person" }} onSelectionChange={setSelection} height={600} /></section>
      <section className="analysis-chat" aria-label="AI investigator chat">
        <h2>AI investigator</h2>
        <p className="analysis-selected">{selection ? `Selected: ${selection.label}` : "Select a node or relationship to begin."}</p>
        <div className="analysis-messages" aria-live="polite">
          {!messages.length && <p className="analysis-empty">Ask about evidence, significance, gaps, or recommended follow-up checks.</p>}
          {messages.map((message, index) => <div key={index} className={`analysis-message ${message.role}`}><span>{message.role === "user" ? "You" : "AI"}</span><p>{message.text}</p></div>)}
          {loading && <p className="analysis-thinking">{phase}</p>}
        </div>
        <form className="analysis-form" onSubmit={ask}><input value={question} onChange={(event) => setQuestion(event.target.value)} disabled={!selection || loading} placeholder={selection ? "Ask an investigative question…" : "Select a connection first"} /><button className="stamp-btn" disabled={!selection || !question.trim() || loading}>{loading ? "Reviewing…" : "Ask AI"}</button></form>
      </section>
    </div>
  </main>;
}
