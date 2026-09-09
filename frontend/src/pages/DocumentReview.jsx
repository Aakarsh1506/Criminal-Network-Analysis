import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { confirmDocument, fetchDocument, documentFileUrl } from "../api/documents";
import "./CriminalProfile.css";
import "./DocumentReview.css";

const STATUS = {
  stored: "Ready for extraction", queued: "Queued", processing: "Processing document",
  awaiting_review: "Awaiting your confirmation", syncing: "Saving to Neo4j",
  complete: "Saved to PostgreSQL and Neo4j", failed: "Processing failed",
  sync_failed: "PostgreSQL saved; Neo4j sync needs a retry",
};
const PENDING = new Set(["queued", "processing", "syncing"]);
const label = (value) => value.replaceAll("_", " ");

export default function DocumentReview() {
  const { id } = useParams();
  const [document, setDocument] = useState(null);
  const [error, setError] = useState(null);
  const [confirming, setConfirming] = useState(false);
  const [reload, setReload] = useState(0);

  useEffect(() => {
    let active = true;
    let timer;
    async function refresh() {
      try {
        const next = await fetchDocument(id);
        if (!active) return;
        setDocument(next); setError(null);
        if (PENDING.has(next.status)) timer = setTimeout(refresh, 3000);
      } catch (err) { if (active) setError(err.message); }
    }
    refresh();
    return () => { active = false; clearTimeout(timer); };
  }, [id, reload]);

  async function confirm() {
    if (!document || confirming || document.status !== "awaiting_review") return;
    setConfirming(true); setError(null);
    try {
      const updated = await confirmDocument(document.id, document.extraction);
      setDocument((current) => ({ ...current, ...updated }));
      setReload((value) => value + 1);
    } catch (err) { setError(err.message); }
    finally { setConfirming(false); }
  }

  const entities = document?.extraction?.entities || [];
  const relationships = document?.extraction?.relationships || [];
  const excluded = document?.extraction?.excluded_relationships || [];
  const byRef = Object.fromEntries(entities.map((entity, index) => [entity.ref, { ...entity, index }]));
  const reviewing = document?.status === "awaiting_review";
  const link = (ref) => byRef[ref] ? <a href={`#review-entity-${byRef[ref].index}`}>{byRef[ref].name}</a> : <span>{ref}</span>;

  return <main className="dossier-page document-review">
    <header className="review-heading">
      <Link to="/upload" className="review-back">← Back to documents</Link>
      <p className="form-number">Document review</p>
      <h1>{document?.name || "Loading document…"}</h1>
      <p role="status">{document ? STATUS[document.status] : "Loading extracted information…"}</p>
      {error && <p role="alert" className="review-error">{error} <button onClick={() => setReload((value) => value + 1)}>Reload</button></p>}
      {document?.processingError && <p role="alert" className="review-error">{document.processingError}</p>}
      {reviewing && <p>Review every entity, its details, and the recorded relationships below. Confirm when you are ready to save these records.</p>}
      {excluded.length > 0 && <p className="review-error">{excluded.length} invalid relationship suggestions were excluded and will not be saved. Review their reasons below.</p>}
      {document?.confirmedAt && <p>Confirmed on {new Date(document.confirmedAt).toLocaleString()}.</p>}
    </header>

    {document?.extraction ? <div className="review-layout">
      <aside className="dossier-sheet review-index">
        <h2>Extracted records</h2>
        <p>{entities.length} entities · {relationships.length} relationships</p>
        <nav aria-label="Extracted entities">
          {entities.map((entity, index) => <a key={entity.ref} href={`#review-entity-${index}`}>
            <span>{entity.name}</span><small>{entity.kind}</small>
          </a>)}
          <a href="#review-relationships">All relationships <small>{relationships.length}</small></a>
          {excluded.length > 0 && <a href="#review-excluded">Excluded relationships <small>{excluded.length}</small></a>}
          <a href="#review-source">Source text</a>
        </nav>
        <a href={documentFileUrl(document.id)} target="_blank" rel="noreferrer">Open original document ↗</a>
      </aside>

      <div className="review-records">
        {!entities.length && <section className="dossier-sheet"><h2>No supported entities found</h2><p>There are no entity records to save.</p></section>}
        {entities.map((entity, index) => {
          const connected = relationships.filter((relation) => relation.subject === entity.ref || relation.object === entity.ref);
          return <article key={entity.ref} id={`review-entity-${index}`} className="dossier-sheet review-entity">
            <header className="review-entity-heading">
              <div className="review-initials" aria-hidden="true">{entity.name.split(/\s+/).slice(0, 2).map((part) => part[0]).join("")}</div>
              <div><span className="form-number">{entity.kind} · Entity {index + 1} of {entities.length}</span><h2>{entity.name}</h2></div>
            </header>
            <dl className="review-fields">
              <div><dt>Entity type</dt><dd>{entity.kind}</dd></div>
              <div><dt>Source identifier</dt><dd>{entity.identifier || "Not provided"}</dd></div>
              {entity.attributes.map((attribute, i) => <div key={`${attribute.key}-${i}`}><dt>{label(attribute.key)}</dt><dd>{attribute.value}</dd></div>)}
            </dl>
            <section className="dossier-section"><h3>Source evidence</h3><blockquote>{entity.evidence}</blockquote></section>
            <section className="dossier-section"><h3>Relationships ({connected.length})</h3>
              {connected.length ? connected.map((relation, i) => <div className="review-relation" key={i}>
                <p>{link(relation.subject)} <span className="review-predicate">{label(relation.predicate)}</span> {link(relation.object)}</p>
                <blockquote>{relation.evidence}</blockquote>
              </div>) : <p>No relationships extracted for this entity.</p>}
            </section>
          </article>;
        })}
        <section className="dossier-sheet" id="review-relationships">
          <h2>All relationships ({relationships.length})</h2>
          <p>Arrows show the subject → predicate → object direction.</p>
          {relationships.map((relation, index) => <article key={index} className="review-relation">
            <p>{link(relation.subject)} → <strong>{label(relation.predicate)}</strong> → {link(relation.object)}</p>
            <blockquote>{relation.evidence}</blockquote>
          </article>)}
          {!relationships.length && <p>No relationships were extracted.</p>}
        </section>
        {excluded.length > 0 && <section className="dossier-sheet" id="review-excluded">
          <h2>Excluded relationships ({excluded.length})</h2>
          <p>These invalid AI suggestions will not be saved to either database. Their quoted evidence has not been validated.</p>
          {excluded.map((relation, index) => <article key={index} className="review-relation">
            <p>{link(relation.subject)} → <strong>{label(relation.predicate)}</strong> → {link(relation.object)}</p>
            <p className="review-error">{relation.reason}</p>
            <blockquote>{relation.evidence}</blockquote>
          </article>)}
        </section>}
        <section className="dossier-sheet" id="review-source"><h2>Extracted source text</h2><pre className="review-source-text">{document.text || "No source text available."}</pre></section>
      </div>
    </div> : document && <section className="dossier-sheet review-placeholder">
      <p>{PENDING.has(document.status) ? "Preparing the entity profiles and relationships for your review…" : "No extraction is available to review yet."}</p>
      <Link to="/upload">Return to documents</Link>
    </section>}

    {reviewing && <footer className="review-confirm-bar">
      <div><strong>{entities.length} entities and {relationships.length} relationships ready for review</strong>
        <p>Confirmation saves these source assertions; it does not establish guilt or verify allegations.</p></div>
      <div className="review-confirm-actions"><Link to="/upload">Review later</Link>
        <button className="stamp-btn" disabled={confirming || !entities.length} onClick={confirm}>{confirming ? "Confirming…" : "Confirm and save"}</button></div>
    </footer>}
  </main>;
}
