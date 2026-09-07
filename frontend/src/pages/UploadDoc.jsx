import { useEffect, useRef, useState } from "react";
import BackButton from "../components/BackButton";
import { fetchDocuments, uploadDocument, documentFileUrl } from "../api/documents";
import "./UploadDoc.css";

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function UploadDoc() {
  const fileInputRef = useRef(null);

  const [documents, setDocuments] = useState([]);
  const [activeDoc, setActiveDoc] = useState(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchDocuments()
      .then(setDocuments)
      .catch(() => setError("Could not load your documents."))
      .finally(() => setLoading(false));
  }, []);

  const handleUploadClick = () => fileInputRef.current?.click();

  const handleFileChange = async (e) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;

    setUploading(true);
    setError(null);
    try {
      const doc = await uploadDocument(file);
      setDocuments((prev) => [doc, ...prev]);
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  };

  const openPreview = (doc) => setActiveDoc(doc);
  const closePreview = () => setActiveDoc(null);

  return (
    <div className="upload-page">
      {!activeDoc && <BackButton />}

      <input
        type="file"
        ref={fileInputRef}
        className="upload-input-hidden"
        accept=".pdf"
        onChange={handleFileChange}
      />

      {error && <p className="empty-note upload-error">{error}</p>}

      {activeDoc ? (
        <div className="doc-preview">
          <div className="doc-preview-header">
            <div>
              <h2>{activeDoc.name}</h2>
              <span className="doc-preview-meta">{formatSize(activeDoc.size)}</span>
            </div>
            <button className="doc-preview-close" onClick={closePreview} aria-label="Close preview">
              ✕ Close
            </button>
          </div>

          <div className="doc-preview-body">
            <iframe src={documentFileUrl(activeDoc.id)} title={activeDoc.name} className="doc-preview-frame" />
          </div>
        </div>
      ) : loading ? (
        <p className="empty-note">Loading documents…</p>
      ) : documents.length === 0 ? (
        <div className="upload-empty">
          <p className="empty-note">No documents uploaded yet</p>
          <button className="stamp-btn upload-btn-center" onClick={handleUploadClick} disabled={uploading}>
            {uploading ? "Uploading..." : "Upload Document"}
          </button>
        </div>
      ) : (
        <>
          <header className="upload-top">
            <h2>{documents.length} document{documents.length !== 1 ? "s" : ""} uploaded</h2>
          </header>

          <div className="doc-grid">
            {documents.map((doc) => (
              <div key={doc.id} className="doc-card" onClick={() => openPreview(doc)}>
                <span className="doc-card-tag">{doc.name.split(".").pop().toUpperCase()}</span>
                <h3>{doc.name}</h3>
                <p className="doc-card-meta">
                  {formatSize(doc.size)} · {new Date(doc.uploadedAt).toLocaleDateString("en-IN", {
                    day: "numeric",
                    month: "short",
                    year: "numeric",
                  })}
                </p>
              </div>
            ))}
          </div>

          <button className="stamp-btn upload-btn-fab" onClick={handleUploadClick} disabled={uploading}>
            {uploading ? "Uploading..." : "Upload Document"}
          </button>
        </>
      )}
    </div>
  );
}

export default UploadDoc;