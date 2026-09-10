import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import RemoveDocumentButton from "../components/RemoveDocumentButton";
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
  const navigate = useNavigate();
  const [document, setDocument] = useState(null);
  const [error, setError] = useState(null);
  const [confirming, setConfirming] = useState(false);
  const [reload, setReload] = useState(0);
  const [selection, setSelection] = useState({ key: null, entities: {}, relationships: {} });
  const snapshot = JSON.stringify(document?.extraction || null);
  const selectionKey = `${id}:${snapshot}`;
  const choices = selection.key === selectionKey ? selection : { entities: {}, relationships: {} };
  const rejectedEntities = new Set(Object.keys(choices.entities).filter((key) => choices.entities[key] === false).map(Number));

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
    if (!document || confirming || remaining > 0 || document.status !== "awaiting_review") return;
    setConfirming(true); setError(null);
    try {
      const updated = await confirmDocument(document.id, document.extraction, [...rejected], [...rejectedEntities]);
      setDocument((current) => ({ ...current, ...updated }));
      setReload((value) => value + 1);
    } catch (err) { setError(err.message); }
    finally { setConfirming(false); }
  }

  const entities = document?.extraction?.entities || [];
  const relationships = document?.extraction?.relationships || [];
  const excluded = document?.extraction?.excluded_relationships || [];
  const excludedEntities = document?.extraction?.excluded_entities || [];
  const byRef = Object.fromEntries([...entities, ...excludedEntities].map((entity, index) => [entity.ref, { ...entity, index }]));
  const rejectedRefs = new Set(entities.filter((_, index) => rejectedEntities.has(index)).map((entity) => entity.ref));
  const endpointRejected = (relation) => rejectedRefs.has(relation.subject) || rejectedRefs.has(relation.object);
  const rejected = new Set(relationships.flatMap((relation, index) =>
    choices.relationships[index] === false || endpointRejected(relation) ? [index] : []));
  const remaining = entities.filter((_, index) => choices.entities[index] === undefined).length
    + relationships.filter((relation, index) => !endpointRejected(relation) && choices.relationships[index] === undefined).length;
  const acceptedEntityCount = entities.filter((_, index) => choices.entities[index] === true).length;
  const acceptedRelationshipCount = relationships.filter((relation, index) =>
    choices.relationships[index] === true && !endpointRejected(relation)).length;
  const reviewing = document?.status === "awaiting_review";
  const link = (ref) => byRef[ref] ? <a href={`#review-entity-${byRef[ref].index}`}>{byRef[ref].name}</a> : <span>{ref}</span>;
  function choose(kind, index, value) {
    setSelection((current) => {
      const next = current.key === selectionKey ? current : { entities: {}, relationships: {} };
      return { ...next, key: selectionKey, [kind]: { ...next[kind], [index]: value } };
    });
  }
  const reviewControl = (index, kind = "relationships") => {
    const blocked = kind === "relationships" && endpointRejected(relationships[index]);
    const value = blocked ? false : choices[kind][index];
    return reviewing && <div className="review-relation-actions" role="group"
      aria-label={`Review ${kind === "entities" ? "entity" : "relationship"} ${index + 1}`}>
      <span>Keep this {kind === "entities" ? "entity" : "relationship"}?</span>
      {[true, false].map((answer) => <button key={String(answer)} type="button"
        disabled={confirming || blocked} aria-pressed={value === answer}
        onClick={() => choose(kind, index, answer)}>{answer ? "Yes" : "No"}</button>)}
      <span>{blocked ? "Excluded because an entity was rejected" : value === undefined ? "Choose Yes or No" : value ? "Will be saved" : "Will not be saved"}</span>
    </div>;
  };

  return <main className="dossier-page document-review">
    <header className="review-heading">
      <Link to="/upload" className="review-back">← Back to documents</Link>
      <p className="form-number">Document review</p>
      <h1>{document?.name || "Loading document…"}</h1>
      <p role="status">{document ? STATUS[document.status] : "Loading extracted information…"}</p>
      {error && <p role="alert" className="review-error">{error} <button onClick={() => setReload((value) => value + 1)}>Reload</button></p>}
      {document?.processingError && <p role="alert" className="review-error">{document.processingError}</p>}
      {document && <RemoveDocumentButton document={document} disabled={confirming}
        onError={setError} onRemoved={() => navigate("/upload")} />}
      {reviewing && <p>Choose Yes or No for every entity and relationship. Rejecting an entity also excludes its connected relationships. Confirm and save to keep your choices; leaving this page discards pending selections.</p>}
      {excluded.length > 0 && <p className="review-error">{excluded.length} relationship suggestions were excluded from saving. Review their reasons below.</p>}
      {document?.confirmedAt && <p>Confirmed on {new Date(document.confirmedAt).toLocaleString()}.</p>}
    </header>

    {document?.extraction ? <div className="review-layout">
      <aside className="dossier-sheet review-index">
        <h2>Extracted records</h2>
        <p>{entities.length} entities · {relationships.length} relationships</p>
        <nav aria-label="Extracted entities" className="no-scrollbar" tabIndex={0}>
          {entities.map((entity, index) => <a key={entity.ref} href={`#review-entity-${index}`}>
            <span>{entity.name}</span><small>{entity.kind}</small>
          </a>)}
          <a href="#review-relationships">All relationships <small>{relationships.length}</small></a>
          {excluded.length > 0 && <a href="#review-excluded">Excluded relationships <small>{excluded.length}</small></a>}
          {excludedEntities.length > 0 && <a href="#review-excluded-entities">Excluded entities <small>{excludedEntities.length}</small></a>}
          <a href="#review-source">Source text</a>
        </nav>
        <a href={documentFileUrl(document.id)} target="_blank" rel="noreferrer">Open original document ↗</a>
      </aside>

      <div className="review-records">
        {!entities.length && <section className="dossier-sheet"><h2>No supported entities found</h2><p>There are no entity records to save.</p></section>}
        {entities.map((entity, index) => {
          const connected = relationships.map((relation, relationIndex) => ({ relation, relationIndex }))
            .filter(({ relation }) => relation.subject === entity.ref || relation.object === entity.ref);
          return <article key={entity.ref} id={`review-entity-${index}`} className={`dossier-sheet review-entity ${rejectedEntities.has(index) ? "review-relation-rejected" : ""}`}>
            <header className="review-entity-heading">
              <div className="review-initials" aria-hidden="true">{entity.name.split(/\s+/).slice(0, 2).map((part) => part[0]).join("")}</div>
              <div><span className="form-number">{entity.kind} · Entity {index + 1} of {entities.length}</span><h2>{entity.name}</h2></div>
              {reviewControl(index, "entities")}
            </header>
            <dl className="review-fields">
              <div><dt>Entity type</dt><dd>{entity.kind}</dd></div>
              <div><dt>Source identifier</dt><dd>{entity.identifier || "Not provided"}</dd></div>
              {entity.attributes.map((attribute, i) => <div key={`${attribute.key}-${i}`}><dt>{label(attribute.key)}</dt><dd>{attribute.value}</dd></div>)}
            </dl>
            <section className="dossier-section"><h3>Source evidence</h3><blockquote>{entity.evidence}</blockquote></section>
            <section className="dossier-section"><h3>Relationships ({connected.length})</h3>
              {connected.length ? connected.map(({ relation, relationIndex }) => <div className={`review-relation ${rejected.has(relationIndex) ? "review-relation-rejected" : ""}`} key={relationIndex}>
                <p>{link(relation.subject)} <span className="review-predicate">{label(relation.predicate)}</span> {link(relation.object)}</p>
                <blockquote>{relation.evidence}</blockquote>
                {reviewControl(relationIndex)}
              </div>) : <p>No relationships extracted for this entity.</p>}
            </section>
          </article>;
        })}
        <section className="dossier-sheet" id="review-relationships">
          <h2>All relationships ({relationships.length})</h2>
          <p>Arrows show the subject → predicate → object direction.</p>
          {relationships.map((relation, index) => <article key={index} className={`review-relation ${rejected.has(index) ? "review-relation-rejected" : ""}`}>
            <p>{link(relation.subject)} → <strong>{label(relation.predicate)}</strong> → {link(relation.object)}</p>
            <blockquote>{relation.evidence}</blockquote>
            {reviewControl(index)}
          </article>)}
          {!relationships.length && <p>No relationships were extracted.</p>}
        </section>
        {excludedEntities.length > 0 && <section className="dossier-sheet" id="review-excluded-entities">
          <h2>Excluded entities ({excludedEntities.length})</h2>
          {excludedEntities.map((entity, index) => <article key={entity.ref} id={`review-entity-${entities.length + index}`}>
            <h3>{entity.name} · {entity.kind}</h3><p className="review-error">{entity.reason}</p>
            <blockquote>{entity.evidence}</blockquote>
          </article>)}
        </section>}
        {excluded.length > 0 && <section className="dossier-sheet" id="review-excluded">
          <h2>Excluded relationships ({excluded.length})</h2>
          <p>These suggestions are retained for review history but are excluded from saved graph links. Each reason identifies a validation failure or reviewer rejection.</p>
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
      <div><strong>{acceptedEntityCount} entities · {acceptedRelationshipCount} relationships selected to save · {rejected.size + rejectedEntities.size} rejected</strong>
        <p role="status">{remaining ? `${remaining} decisions remaining` : "All records reviewed"}</p>
        <p>Confirmation saves these source assertions; it does not establish guilt or verify allegations.</p></div>
      <div className="review-confirm-actions"><Link to="/upload">Review later</Link>
        <button className="stamp-btn" disabled={confirming || remaining > 0} onClick={confirm}>{confirming ? "Confirming…" : "Confirm and save"}</button></div>
    </footer>}
  </main>;
}
