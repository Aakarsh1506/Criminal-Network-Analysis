import { useState } from "react";
import { cancelDocument, retryDocument } from "../api/documents";
import RemoveDocumentButton from "./RemoveDocumentButton";
import "./DocumentActions.css";

export default function DocumentActions({ document, disabled, onUpdated, onRemoved, onError }) {
  const [retrying, setRetrying] = useState(false);
  const [removing, setRemoving] = useState(false);
  const canProcess = ["stored", "failed", "sync_failed", "cancelled"].includes(document.status);
  const busy = ["queued", "processing", "syncing"].includes(document.status);

  async function process() {
    if (!canProcess || disabled || retrying || removing) return;
    setRetrying(true);
    try { onUpdated(await retryDocument(document.id)); }
    catch (error) { onError(error.message); }
    finally { setRetrying(false); }
  }

  async function stop() {
    if (!busy || disabled || retrying || removing) return;
    setRetrying(true);
    try { onUpdated(await cancelDocument(document.id)); }
    catch (error) { onError(error.message); }
    finally { setRetrying(false); }
  }

  return <div className="document-actions">
    <div className="document-action-buttons">
      {canProcess && <button type="button" className="stamp-btn" disabled={disabled || retrying || removing}
        onClick={process}>{retrying ? "Queuing…" : document.status === "sync_failed" ? "Retry saving" : document.status === "cancelled" ? "Process again" : "Process document"}</button>}
      {busy && <button type="button" className="stamp-btn document-stop-button" disabled={disabled || retrying || removing}
        onClick={stop}>{retrying ? "Stopping…" : "Stop processing"}</button>}
      <RemoveDocumentButton document={document} disabled={disabled || retrying}
        onBusyChange={setRemoving} onRemoved={onRemoved} onError={onError} />
    </div>
    {busy && <p>Processing is already running. Actions become available when it finishes.</p>}
    {document.status === "awaiting_review" && <p>Ready to review. You can remove this draft or review and save it.</p>}
    {document.confirmedAt && <p>This document is retained as the source for confirmed records.</p>}
  </div>;
}
