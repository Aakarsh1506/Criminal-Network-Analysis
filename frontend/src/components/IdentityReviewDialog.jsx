import { useEffect, useRef, useState } from "react";
import { useTranslation } from "../i18n";
import "./IdentityReviewDialog.css";

export default function IdentityReviewDialog({ suggestions, busy, error, onConfirm, onClose }) {
  const { t } = useTranslation();
  const dialog = useRef(null);
  const [choices, setChoices] = useState({});
  useEffect(() => {
    const node = dialog.current;
    node.showModal();
    return () => node.close();
  }, []);
  const groups = Object.groupBy(suggestions, (item) => item.ref);
  const complete = Object.keys(groups).every((ref) => Object.hasOwn(choices, ref));
  const choose = (ref, personId) => setChoices((current) => ({ ...current, [ref]: personId }));
  return <dialog ref={dialog} className="identity-review-dialog dossier-sheet" aria-labelledby="identity-review-title"
    onCancel={(event) => { event.preventDefault(); if (!busy) onClose(); }}>
    <header className="identity-review-header">
      <span className="form-number">{t("identityEyebrow")}</span>
      <h2 id="identity-review-title">{t("identityTitle")}</h2>
      <p>{t("identityHint")}</p>
    </header>
    <div className="identity-review-body">
      {Object.entries(groups).map(([ref, matches]) => <fieldset key={ref} className="identity-review-person" disabled={busy}>
        <legend>{matches[0].name}</legend>
        {matches.map((match) => <label className="identity-review-option" key={match.personId}>
          <input type="radio" name={`identity-${ref}`} value={match.personId}
            checked={choices[ref] === match.personId} onChange={() => choose(ref, match.personId)} />
          <span className="identity-review-option-body">
            <span className="identity-review-option-title">{t("identityUse")}</span>
            <span className="identity-review-facts">
              {match.age != null && <span><small>{t("identityAge")}</small>{match.age}</span>}
              {(match.city || match.state) && <span><small>{t("identityPlace")}</small>
                {[match.city, match.state].filter(Boolean).join(", ")}</span>}
              <span><small>{t("identityCases")}</small>
                {match.cases?.length ? match.cases.join(", ") : t("identityNoCases")}</span>
            </span>
            <span className="identity-review-count">{match.sharedConnections.length} {t("identityShared")}</span>
            {match.sharedConnections.length > 0 && <ul className="tag-row">
              {match.sharedConnections.map((node) => <li className="tag-stamp" key={`${node.kind}:${node.id}`}>
                {node.name} <small>{node.kind}</small>
              </li>)}
            </ul>}
            <small className="identity-review-id">{t("identityRecordId")}: {match.personId}</small>
          </span>
        </label>)}
        <label className="identity-review-option identity-review-separate">
          <input type="radio" name={`identity-${ref}`} value=""
            checked={choices[ref] === ""} onChange={() => choose(ref, "")} />
          <span className="identity-review-option-body">
            <span className="identity-review-option-title">{t("identitySeparate")}</span>
          </span>
        </label>
      </fieldset>)}
    </div>
    {error && <p role="alert" className="review-error identity-review-error">{error}</p>}
    <footer className="identity-review-actions">
      <button type="button" disabled={busy} onClick={onClose}>{t("identityBack")}</button>
      <button type="button" className="identity-review-save" disabled={busy || !complete}
        onClick={() => onConfirm(Object.fromEntries(Object.entries(choices).filter(([, id]) => id)))}>
        {busy ? t("identitySaving") : t("identitySave")}
      </button>
    </footer>
  </dialog>;
}
