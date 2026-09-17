import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { fetchCriminalRecord, generateCriminalRecord } from "../api/criminals";
import { useTranslation } from "../i18n";
import "./DetailedRecord.css";

const categories = ["identity", "cases", "locations", "connections", "sourceDetails"];
const fieldLabel = (value) => value.replace(/([a-z])([A-Z])/g, "$1 $2").replaceAll("_", " ");

export default function DetailedRecord({ personId, onLocationChange }) {
  const { t, language } = useTranslation();
  const [record, setRecord] = useState(null);
  const [generated, setGenerated] = useState(null);
  const [error, setError] = useState("");
  const [aiError, setAiError] = useState("");
  const [busy, setBusy] = useState(false);
  const [retry, setRetry] = useState(0);
  const generation = useRef(null);
  useEffect(() => {
    const controller = new AbortController();
    fetchCriminalRecord(personId, { signal: controller.signal }).then((data) => {
      if (controller.signal.aborted) return;
      setRecord(data); setError("");
      onLocationChange({ id: personId, location: data.location });
    }).catch((err) => { if (!controller.signal.aborted) setError(err.message); });
    return () => { controller.abort(); generation.current?.abort(); };
  }, [personId, retry, onLocationChange]);
  async function generate() {
    if (generation.current) return;
    const controller = new AbortController();
    generation.current = controller;
    setBusy(true); setAiError("");
    try {
      const data = await generateCriminalRecord(personId, language, { signal: controller.signal });
      if (!controller.signal.aborted) setGenerated(data);
    } catch (err) { if (!controller.signal.aborted) setAiError(err.message); }
    finally {
      if (generation.current === controller) generation.current = null;
      if (!controller.signal.aborted) setBusy(false);
    }
  }
  const sources = Object.fromEntries([...(record?.sources || []), ...(generated?.sources || [])].map((source) => [source.id, source]));
  const cite = (id) => <a key={id} href={`#record-source-${id}`} onClick={() => {
    const target = document.getElementById(`record-source-${id}`);
    if (target?.closest("details")) target.closest("details").open = true;
  }}>{sources[id]?.label || id}</a>;
  return <section className="detailed-record" aria-labelledby="detailed-record-title">
    <header><h3 id="detailed-record-title">{t("recordTitle")}</h3><p>{t("recordDescription")}</p></header>
    {!record && !error && <p role="status">{t("loadingRecords")}</p>}
    {error && <p role="alert">{error} <button onClick={() => setRetry((value) => value + 1)}>{t("retry")}</button></p>}
    {record && <>
      <div className="detailed-record-tools">
        <p>{record.index.documents} {t("recordDocuments")} · {record.index.embedded}/{record.index.chunks} {t("recordEmbedded")}</p>
        <button type="button" disabled={busy} onClick={generate}>{busy ? t("recordGenerating") : generated ? t("recordRegenerate") : t("recordGenerate")}</button>
      </div>
      {busy && <p role="status">{t("recordWorking")}</p>}
      {aiError && <p role="alert">{aiError}</p>}
      {generated && <article className="detailed-record-ai">
        <h4>{t("recordAI")}</h4><p>{t("recordVerify")}</p>
        {generated.coverage.includedFacts < generated.coverage.totalFacts && <p>{t("recordPartial")}</p>}
        {generated.sections.map((section) => <section key={section.category}>
          <h4>{t(`record_${section.category}`)}</h4>
          {section.items.map((item, index) => <div key={index}><p>{item.text}</p><small className="detailed-record-citations">{item.sources.map(cite)}</small></div>)}
        </section>)}
      </article>}
      <div className="detailed-record-sections">
        {categories.map((category) => {
          const facts = record.facts.filter((fact) => fact.category === category);
          return <details key={category} open={category === "identity" || category === "cases"}>
            <summary>{t(`record_${category}`)} ({facts.length})</summary>
            {!facts.length && <p>{t("recordNoDetails")}</p>}
            {facts.map((fact) => <article key={fact.id}>
              <h5>{fieldLabel(fact.label)}</h5><p>{fact.text}</p>
              {fact.needsReview && <p className="detailed-record-warning">{t("activityEvidenceMismatch")}</p>}
              {fact.evidence && <blockquote>{fact.evidence}</blockquote>}
              <small>{cite(fact.source)}</small>
            </article>)}
          </details>;
        })}
      </div>
      <details className="detailed-record-sources"><summary>{t("recordSources")} ({Object.keys(sources).length})</summary>
        {Object.values(sources).map((source) => <article key={source.id} id={`record-source-${source.id}`}>
          <h5>{source.documentId ? <Link to={`/documents/${source.documentId}/review`}>{source.label}</Link> : source.label}</h5>
          {source.start != null && <small>{t("recordCharacters")}: {source.start}–{source.end}</small>}
          {source.quote && <blockquote>{source.quote}</blockquote>}
        </article>)}
      </details>
    </>}
  </section>;
}
