import { useState } from "react";
import { canRemoveDocument, deleteDocument } from "../api/documents";

export default function RemoveDocumentButton({ document, disabled, onRemoved, onError, onBusyChange }) {
  const [removing, setRemoving] = useState(false);
  const allowed = canRemoveDocument(document);

  async function remove() {
    if (!allowed || removing || disabled) return;
    if (!window.confirm(`Remove “${document.name}”?\n\nThis permanently deletes the uploaded file, source text, extracted entities, relationships, and AI search chunks. Shared criminal and case records remain. This cannot be undone.`)) return;
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
