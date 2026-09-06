import { useRef, useState } from "react";
import BackButton from "../components/BackButton";
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

  const handleUploadClick = () => fileInputRef.current?.click();

  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const doc = {
      id: `${Date.now()}-${file.name}`,
      name: file.name,
      type: file.type,
      size: file.size,
      url: URL.createObjectURL(file),
      uploadedAt: new Date(),
    };

    setDocuments((prev) => [doc, ...prev]);
    e.target.value = "";
  };

  const openPreview = (doc) => setActiveDoc(doc);
  const closePreview = () => setActiveDoc(null);

  return (
    <div className="upload-page">
      {activeDoc ? (
        <BackButton label="← Back to documents" onClick={closePreview} />
      ) : (
        <BackButton />
      )}

      <input
        type="file"
        ref={fileInputRef}
        className="upload-input-hidden"
        accept=".pdf"
        onChange={handleFileChange}
      />

      {activeDoc ? (
        <div className="doc-preview">
          <div className="doc-preview-header">
            <h2>{activeDoc.name}</h2>
            <span className="doc-preview-meta">{formatSize(activeDoc.size)}</span>
          </div>

          <div className="doc-preview-body">
            <iframe src={activeDoc.url} title={activeDoc.name} className="doc-preview-frame" />
          </div>
        </div>
      ) : documents.length === 0 ? (
        <div className="upload-empty">
          <p className="empty-note">No documents uploaded yet</p>
          <button className="stamp-btn upload-btn-center" onClick={handleUploadClick}>
            Upload Document
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
                  {formatSize(doc.size)} · {doc.uploadedAt.toLocaleDateString("en-IN", {
                    day: "numeric",
                    month: "short",
                    year: "numeric",
                  })}
                </p>
              </div>
            ))}
          </div>

          <button className="stamp-btn upload-btn-fab" onClick={handleUploadClick}>
            Upload Document
          </button>
        </>
      )}
    </div>
  );
}

export default UploadDoc;