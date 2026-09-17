import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import RelationGraph from "../components/RelationGraph";
import { fetchAllCriminals, fetchCriminalNetwork } from "../api/criminals";
import { mergeNetworks, searchPeople } from "../utils/investigatorWorkspace";
import { useTranslation } from "../i18n";
import formatInsight from "../utils/formatInsight";
import "./InvestigatorAnalysis.css";

export default function InvestigatorAnalysis() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { t } = useTranslation();
  const [people, setPeople] = useState([]);
  const [catalogLoading, setCatalogLoading] = useState(true);
  const [catalogRetry, setCatalogRetry] = useState(0);
  const [catalogError, setCatalogError] = useState(false);
  const [query, setQuery] = useState("");
  const [searchOpen, setSearchOpen] = useState(false);
  const [highlight, setHighlight] = useState(0);
  const [entries, setEntries] = useState([]);
  const [adding, setAdding] = useState(null);
  const [graphError, setGraphError] = useState("");
  const [selection, setSelection] = useState(null);
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [phase, setPhase] = useState("analysisThinking");
  const request = useRef(null);
  const graphRequest = useRef(null);
  const legacyLoaded = useRef(null);
  const messagesRef = useRef(null);
  const inputRef = useRef(null);
  const results = useMemo(() => searchPeople(people, query), [people, query]);
  const network = useMemo(() => mergeNetworks(entries), [entries]);

  useEffect(() => {
    let active = true;
    fetchAllCriminals().then((data) => { if (active) setPeople(data); })
      .catch(() => { if (active) setCatalogError(true); })
      .finally(() => { if (active) setCatalogLoading(false); });
    return () => { active = false; };
  }, [catalogRetry]);

  useEffect(() => () => { request.current?.abort(); graphRequest.current?.abort(); }, []);
  useEffect(() => {
    const panel = messagesRef.current;
    if (panel) panel.scrollTop = panel.scrollHeight;
  }, [messages, loading]);

  async function addPerson(person) {
    if (graphRequest.current || entries.some((entry) => entry.person.id === person.id)) return;
    const controller = new AbortController();
    graphRequest.current = controller;
    setAdding(person.id); setGraphError("");
    try {
      const graph = await fetchCriminalNetwork(person.id, { signal: controller.signal });
      if (controller.signal.aborted) return;
      setEntries((current) => [...current, { person, network: graph }]);
      setSelection(null); setQuery(""); setSearchOpen(false);
    } catch (error) {
      if (!controller.signal.aborted) setGraphError(error.message);
    } finally {
      if (graphRequest.current === controller) graphRequest.current = null;
      if (!controller.signal.aborted) setAdding(null);
    }
  }

  // Keep existing bookmarked /analysis/:id links useful.
  useEffect(() => {
    if (!id || !people.length || legacyLoaded.current === id) return;
    legacyLoaded.current = id;
    const person = people.find((item) => String(item.id) === id);
    if (person) void addPerson(person);
  });

  async function ask(event) {
    event?.preventDefault();
    const text = question.trim();
    if (!text || !selection || request.current) return;
    const target = { ...selection };
    const contextKey = JSON.stringify([target.personId, target.type, target.id]);
    const history = messages.filter((message) => message.contextKey === contextKey
      && ["user", "assistant"].includes(message.role)).slice(-6)
      .map((message) => ({ role: message.role, content: message.text.slice(0, 4000) }));
    const controller = new AbortController();
    request.current = controller;
    setQuestion(""); setLoading(true); setPhase("analysisThinking");
    const timer = window.setTimeout(() => setPhase("analysisReviewing"), 1600);
    setMessages((current) => [...current, { role: "user", text, context: target.label, contextKey }]);
    try {
      const response = await fetch(`/api/criminals/${encodeURIComponent(target.personId)}/explain`, {
        method: "POST", signal: controller.signal, headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ selection: { type: target.type, id: target.id }, question: text, history }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || t("analysisFailed"));
      if (typeof data.explanation !== "string" || !data.explanation.trim()) throw new Error(t("analysisFailed"));
      if (!controller.signal.aborted) setMessages((current) => [...current, { role: "assistant", text: data.explanation, contextKey }]);
    } catch (error) {
      if (!controller.signal.aborted) setMessages((current) => [...current, { role: "error", text: error.message, retryQuestion: text, target }]);
    } finally {
      window.clearTimeout(timer);
      if (request.current === controller) request.current = null;
      if (!controller.signal.aborted) { setLoading(false); inputRef.current?.focus(); }
    }
  }

  return <main className="analysis-page">
    <header className="analysis-header"><p className="form-number">{t("investigatorWorkspace")}</p><h1>{t("investigatorAnalysis")}</h1><p>{t("analysisIntro")}</p></header>
    <section className="analysis-search" aria-label={t("analysisFind")}>
      <label htmlFor="analysis-search-input">{t("analysisFind")}</label>
      <div className="analysis-search-row">
        <input id="analysis-search-input" role="combobox" aria-expanded={searchOpen && !!query.trim()} aria-controls="analysis-results" aria-autocomplete="list" aria-activedescendant={searchOpen && results[highlight] ? `analysis-result-${highlight}` : undefined}
          autoComplete="off" placeholder={t("analysisSearchHint")} value={query} disabled={catalogLoading || catalogError}
          onFocus={() => setSearchOpen(true)} onBlur={() => setSearchOpen(false)}
          onChange={(event) => { setQuery(event.target.value.slice(0, 100)); setHighlight(0); setSearchOpen(true); }}
          onKeyDown={(event) => {
            if (event.key === "Escape") setSearchOpen(false);
            if (event.key === "ArrowDown" || event.key === "ArrowUp") {
              event.preventDefault(); setSearchOpen(true);
              setHighlight((current) => Math.max(0, Math.min(results.length - 1, current + (event.key === "ArrowDown" ? 1 : -1))));
            }
            if (event.key === "Enter" && searchOpen && results[highlight]) { event.preventDefault(); void addPerson(results[highlight]); }
          }} />
        {catalogLoading && <span role="status">{t("loadingRecords")}</span>}
        {adding && <span role="status">{t("analysisAdding")}</span>}
      </div>
      {searchOpen && !!query.trim() && <ul className="analysis-results" id="analysis-results" role="listbox" aria-label={t("analysisFind")}>
        {results.map((person, index) => {
          const added = entries.some((entry) => entry.person.id === person.id);
          return <li id={`analysis-result-${index}`} key={person.id} role="option" aria-selected={highlight === index} aria-disabled={added || !!adding}
            onMouseDown={(event) => event.preventDefault()} onMouseEnter={() => setHighlight(index)} onClick={() => void addPerson(person)}>
            <span><strong>{person.name}</strong><small>{[person.id, person.alias, person.location?.city].filter(Boolean).join(" · ")}</small></span><span>{added ? t("analysisAdded") : t("analysisAdd")}</span>
          </li>;
        })}
        {!results.length && <li role="option" aria-disabled="true" aria-selected="false">{t("noSearchMatches")}</li>}
      </ul>}
      {catalogError && <p role="alert">{t("analysisCatalogError")} <button type="button" onClick={() => { setCatalogError(false); setCatalogLoading(true); setCatalogRetry((value) => value + 1); }}>{t("retry")}</button></p>}
      {graphError && <p className="analysis-error" role="alert">{t("analysisGraphError")} {graphError}</p>}
    </section>
    <div className="analysis-layout">
      <section className="analysis-connections" aria-label={t("connections")}>
        <div className="analysis-panel-heading"><h2>{t("connections")}</h2><span>{network.nodes.length} {t("analysisNodes")} · {network.edges.length} {t("analysisLinks")}</span></div>
        <div className="analysis-people">{entries.map(({ person }) => <span className="analysis-person" key={person.id}>{person.name}<button type="button" aria-label={`${t("analysisRemove")} ${person.name}`} onClick={() => { setEntries((current) => current.filter((entry) => entry.person.id !== person.id)); setSelection(null); }}>×</button></span>)}</div>
        {entries.length ? <RelationGraph key={entries.map((entry) => entry.person.id).join(":")} mainCriminal={{ id: "workspace", name: t("investigatorWorkspace") }} network={network} onSelectionChange={setSelection} onNodeClick={(personId) => navigate(`/criminal/${personId}`)} height={480} />
          : <div className="analysis-empty-workspace"><span aria-hidden="true">◎</span><h3>{t("analysisStart")}</h3><p>{t("analysisStartHint")}</p></div>}
      </section>
      <section className="analysis-chat" aria-label={t("aiInvestigator")}>
        <div className="analysis-panel-heading"><h2>{t("aiInvestigator")}</h2><button type="button" disabled={loading || !messages.length} onClick={() => setMessages([])}>{t("analysisClearChat")}</button></div>
        <p className="analysis-selected">{selection ? `${t("analysisSelected")}: ${selection.label}` : t("analysisSelect")}</p>
        <div ref={messagesRef} className="analysis-messages" role="log" aria-live="polite" aria-label={t("analysisMessages")} tabIndex={0}>
          {!messages.length && <div className="analysis-empty"><h3>{t("analysisChatWelcome")}</h3><p>{t("analysisChatHint")}</p>{["analysisPrompt1", "analysisPrompt2"].map((key) => <button className="analysis-prompt" key={key} disabled={!selection} onClick={() => { setQuestion(t(key)); inputRef.current?.focus(); }}>{t(key)}</button>)}</div>}
          {messages.map((message, index) => <article key={index} className={`analysis-message ${message.role}`}><strong>{message.role === "user" ? t("analysisYou") : t("aiInvestigator")}</strong>{message.context && <small>{message.context}</small>}{message.role === "assistant" ? <div className="analysis-answer">{formatInsight(message.text)}</div> : <p>{message.text}</p>}{message.retryQuestion && <button disabled={loading} onClick={() => { const present = network.nodes.concat(network.edges).find((item) => item.id === message.target.id); if (present) setSelection({ ...message.target, personId: present.originPersonId }); setQuestion(message.retryQuestion); inputRef.current?.focus(); }}>{t("analysisRetryQuestion")}</button>}</article>)}
          {loading && <p className="analysis-thinking" role="status"><span aria-hidden="true">•••</span> {t(phase)}</p>}
        </div>
        <form className="analysis-form" onSubmit={ask}>
          <label className="analysis-compose-label" htmlFor="analysis-question">{t("analysisQuestion")}</label>
          <textarea ref={inputRef} id="analysis-question" value={question} maxLength={2000} rows={3} disabled={!selection} onChange={(event) => setQuestion(event.target.value)} placeholder={t(selection ? "analysisQuestionHint" : "analysisSelect")}
            onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) { event.preventDefault(); void ask(); } }} />
          <div className="analysis-compose-footer"><small>{t("analysisEnterHint")}</small><button className="stamp-btn" disabled={!selection || !question.trim() || loading}>{loading ? t("analysisReviewing") : t("askAI")}</button></div>
        </form>
      </section>
    </div>
  </main>;
}
