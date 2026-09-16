import { useState } from "react";
import { canRemoveDocument, deleteDocument } from "../api/documents";

export default function RemoveDocumentButton({ document, disabled, onRemoved, onError, onBusyChange }) {
  const [removing, setRemoving] = useState(false);
  const allowed = canRemoveDocument(document);

  async function remove() {
    if (!allowed || removing || disabled) return;
    if (!window.confirm(`Remove “${document.name}”?\n\nThis permanently deletes the uploaded file, source text, extracted relationships in PostgreSQL and Neo4j, and AI search chunks. Records created by this import are removed when no other source uses them. Shared and pre-existing records remain. This cannot be undone.`)) return;
    setRemoving(true);
    onBusyChange?.(true);
    try {
      await deleteDocument(document.id);
      onRemoved(document.id);
    } catch (error) { onError(error.message); }
    finally { setRemoving(false); onBusyChange?.(false); }
  }

  return <button type="button" className="stamp-btn" onClick={remove}
    disabled={!allowed || disabled || removing}
    title={allowed ? "Remove this document and its extracted data" : "Stop processing before removing this document"}>
    {removing ? "Removing…" : "Remove document"}
  </button>;
}
