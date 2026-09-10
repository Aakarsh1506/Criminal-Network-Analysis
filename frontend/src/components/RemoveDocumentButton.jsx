import { useState } from "react";
import { canRemoveDocument, deleteDocument } from "../api/documents";

export default function RemoveDocumentButton({ document, disabled, onRemoved, onError }) {
  const [removing, setRemoving] = useState(false);
  const allowed = canRemoveDocument(document);

  async function remove() {
    if (!allowed || removing || disabled) return;
    if (!window.confirm(`Remove “${document.name}”?\n\nThis permanently deletes the uploaded file and its extraction draft. This cannot be undone.`)) return;
    setRemoving(true);
    try {
      await deleteDocument(document.id);
      onRemoved(document.id);
    } catch (error) { onError(error.message); }
    finally { setRemoving(false); }
  }

  return <button type="button" className="stamp-btn" onClick={remove}
    disabled={!allowed || disabled || removing}
    title={allowed ? "Remove this document and its draft" : "Processing documents and confirmed extraction sources cannot be removed"}>
    {removing ? "Removing…" : "Remove document"}
  </button>;
}
