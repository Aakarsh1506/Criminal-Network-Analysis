import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import BackButton from "../components/BackButton";
import RemoveDocumentButton from "../components/RemoveDocumentButton";
import {
  fetchDocuments, fetchDocument, fetchSourceTypes, uploadDocument,
  retryDocument, documentFileUrl,
} from "../api/documents";
import "./UploadDoc.css";

const STATUS = {
  awaiting_review: "Ready to review · confirmation needed",
  stored: "Stored · ready to process", queued: "Queued", processing: "Extracting text and entities",
  syncing: "Saving relationships to Neo4j", complete: "Saved to PostgreSQL and Neo4j",
  failed: "Processing failed", sync_failed: "Saved to PostgreSQL · Neo4j sync failed",
};
const BUSY = new Set(["queued", "processing", "syncing"]);
const RETRYABLE = new Set(["stored", "failed", "sync_failed"]);

export default function UploadDoc() {
  const navigate = useNavigate();
  const input = useRef(null);
  const [documents, setDocuments] = useState([]);
  const [selected, setSelected] = useState(null);
  const [detail, setDetail] = useState(null);
  const [types, setTypes] = useState({});
  const [extensions, setExtensions] = useState([]);
  const [sourceType, setSourceType] = useState("fir");
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [retrying, setRetrying] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    let active = true;
    Promise.all([fetchDocuments(), fetchSourceTypes()]).then(([docs, config]) => {
      if (!active) return;
      setDocuments(docs); setTypes(config.sourceTypes); setExtensions(config.extensions);
    }).catch((err) => { if (active) setError(err.message); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  const processing = documents.some((doc) => BUSY.has(doc.status));
  useEffect(() => {
    if (!processing) return;
    let active = true;
    const timer = setInterval(() => {
      fetchDocuments().then((docs) => { if (active) setDocuments(docs); })
        .catch((err) => { if (active) setError(err.message); });
    }, 3000);
    return () => { active = false; clearInterval(timer); };
  }, [processing]);

  const selectedStatus = documents.find((doc) => doc.id === selected)?.status;
  useEffect(() => {
    if (selected === null) return;
    let active = true;
    fetchDocument(selected).then((doc) => { if (active) setDetail(doc); })
      .catch((err) => { if (active) setError(err.message); });
    return () => { active = false; };
  }, [selected, selectedStatus]);

  async function upload(event) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    if (file.size > 20 * 1024 * 1024) { setError("Files must be 20 MB or smaller."); return; }
    setUploading(true); setError(null);
    try {
      const doc = await uploadDocument(file, sourceType);
      setDocuments((prev) => [doc, ...prev]); navigate(`/documents/${doc.id}/review`);
    } catch (err) { setError(err.message); }
    finally { setUploading(false); }
  }

  async function retry() {
    setRetrying(true); setError(null);
    try {
      const doc = await retryDocument(selected);
      setDocuments((prev) => prev.map((item) => item.id === doc.id ? doc : item));
      setDetail((prev) => ({ ...prev, ...doc }));
    } catch (err) { setError(err.message); }
    finally { setRetrying(false); }
  }

  const entities = detail?.extraction?.entities || [];
  const relationships = detail?.extraction?.relationships || [];
  const names = Object.fromEntries(entities.map((entity) => [entity.ref, entity.name]));
  return <div className="upload-page">
    <BackButton />
    <section className="upload-top upload-controls">
      <h2>Upload and analyze records</h2>
      <label htmlFor="source-type">Record source</label>
      <select id="source-type" value={sourceType} disabled={loading || uploading}
        onChange={(event) => setSourceType(event.target.value)}>
        {Object.entries(types).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
      </select>
      <p>PDF, PNG, JPEG, TIFF, TXT, CSV, JSON, or Word (.docx). Up to 20 MB, 30 scanned pages, and 60,000 extracted characters.</p>
      <p>Scans use OCR. Extracted text is sent to Groq; you can review every entity and relationship before confirming the database save.</p>
      <input ref={input} className="upload-input-hidden" type="file" accept={extensions.join(",")}
        onChange={upload} />
      <button className="stamp-btn upload-btn-center" disabled={uploading || loading || !extensions.length}
        onClick={() => input.current?.click()}>{uploading ? "Uploading…" : "Upload and extract"}</button>
    </section>
    {error && <p role="alert" className="upload-error">{error}</p>}
    {loading ? <p role="status" className="empty-note">Loading documents…</p> :
      <div className="doc-grid">
        {documents.map((doc) => <button type="button" className="doc-card" key={doc.id}
          onClick={() => { if (doc.status === "awaiting_review") { navigate(`/documents/${doc.id}/review`); return; } if (selected !== doc.id) { setDetail(null); setSelected(doc.id); } }} aria-pressed={selected === doc.id}>
          <span className="doc-card-tag">{types[doc.sourceType] || "Document"}</span>
          <h3>{doc.name}</h3>
          <p className="doc-card-meta">{(doc.size / 1024).toFixed(1)} KB · {new Date(doc.uploadedAt).toLocaleDateString()}</p>
          <p className="doc-status">{STATUS[doc.status] || doc.status}</p>
        </button>)}
        {!documents.length && <p className="empty-note">No documents uploaded yet.</p>}
      </div>}
    {selected !== null && <section className="doc-preview extraction-detail" aria-live="polite">
      <div className="doc-preview-header">
        <h2>{detail?.name || "Loading extracted information…"}</h2>
        <button className="doc-preview-close" onClick={() => { setSelected(null); setDetail(null); }}>Close</button>
      </div>
      {detail && <>
        <p role="status">{STATUS[detail.status]}</p>
        <RemoveDocumentButton document={detail} disabled={retrying} onError={setError}
          onRemoved={(id) => {
            setDocuments((prev) => prev.filter((doc) => doc.id !== id));
            setSelected(null); setDetail(null); setError(null);
          }} />
        {detail.processingError && <p role="alert" className="upload-error">{detail.processingError}</p>}
        {RETRYABLE.has(detail.status) && <button className="stamp-btn" disabled={retrying} onClick={retry}>
          {retrying ? "Queuing…" : detail.status === "sync_failed" ? "Retry Neo4j sync" : "Process document"}
        </button>}
        <p><a href={documentFileUrl(detail.id)} target="_blank" rel="noreferrer">Open original document</a></p>
        {detail.extraction && <>
          <p><Link to={`/documents/${detail.id}/review`}>Open full entity review →</Link></p>
          <h3>{entities.length} entities · {relationships.length} relationships</h3>
          <p>Source assertions may contain errors or allegations. Witnesses and mentioned people are not automatically suspects.</p>
          {entities.map((entity) => <details key={entity.ref} className="extracted-item">
            <summary>{entity.kind}: {entity.name}</summary>
            {entity.identifier && <p>Source identifier: {entity.identifier}</p>}
            <dl>{entity.attributes.map((attr, index) => <div key={`${attr.key}-${index}`}>
              <dt>{attr.key.replaceAll("_", " ")}</dt><dd>{attr.value}</dd>
            </div>)}</dl>
            <blockquote>{entity.evidence}</blockquote>
          </details>)}
          {relationships.map((relation, index) => <details key={index} className="extracted-item">
            <summary>{names[relation.subject]} → {relation.predicate} → {names[relation.object]}</summary>
            <blockquote>{relation.evidence}</blockquote>
          </details>)}
          {!entities.length && <p>No supported entities were found in this source.</p>}
        </>}
        {detail.text && <details className="extracted-item"><summary>Extracted source text</summary>
          <pre className="extracted-text">{detail.text}</pre></details>}
      </>}
    </section>}
  </div>;
}
