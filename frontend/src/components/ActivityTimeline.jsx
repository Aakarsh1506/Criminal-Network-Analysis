import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchCriminalActivity } from "../api/criminals";
import { useTranslation } from "../i18n";
import "./ActivityTimeline.css";

export default function ActivityTimeline({ personId, cases = [], onLocationChange }) {
  const { t, language } = useTranslation();
  const [result, setResult] = useState(null);
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    fetchCriminalActivity(personId, { signal: controller.signal }).then((data) => {
      if (controller.signal.aborted) return;
      setResult({ id: personId, data });
      onLocationChange({ id: personId, location: data.location });
    }).catch(() => {
      if (!controller.signal.aborted) setResult({ id: personId, error: true });
    });
    return () => controller.abort();
  }, [personId, retry, onLocationChange]);
  const current = result?.id === personId ? result : null;
  const entries = current?.data?.entries || [];
  const activities = entries.filter((entry) => entry.kind !== "PERSON_RECORD");
  const profileRecords = entries.filter((entry) => entry.kind === "PERSON_RECORD");
  const locale = language === "hi" ? "hi-IN" : "en-IN";
  const formatDate = (value) => new Date(value).toLocaleString(locale, { dateStyle: "medium", timeStyle: "short" });
  const renderEntry = (entry) => <li key={entry.id} className={entry.needsReview ? "activity-needs-review" : ""}>
    <div className="activity-meta"><span>{t(`activity_${entry.kind}`)}</span><time dateTime={entry.recordedAt}>{t("activityRecorded")} {formatDate(entry.recordedAt)}</time></div>
    <p className="activity-subject">{entry.subject}{entry.object && <> → {entry.object}</>}</p>
    {entry.needsReview
      ? <><p className="activity-review-note">{t("activityEvidenceMismatch")}</p><details><summary>{t("activityInspectQuote")}</summary><blockquote>{entry.evidence}</blockquote></details></>
      : entry.evidence && <blockquote>{entry.evidence}</blockquote>}
    <small>{t("activitySource")}: {entry.canOpenSource
      ? <Link to={`/documents/${entry.documentId}/review`}>{entry.documentName}</Link>
      : entry.documentName}</small>
  </li>;

  return <section className="activity-timeline" aria-labelledby="activity-title">
    <header><h3 id="activity-title">{t("activityTitle")}</h3><p>{t("activityDescription")}</p></header>
    {!current && <p role="status">{t("loadingRecords")}</p>}
    {current?.error && <p role="alert">{t("activityError")} <button type="button" onClick={() => { setResult(null); setRetry((value) => value + 1); }}>{t("retry")}</button></p>}
    {current?.data && <div className="activity-scroll" tabIndex={0} aria-label={t("activityTitle")}>
      {!!activities.length && <ol>{activities.map(renderEntry)}</ol>}
      {!activities.length && <p className="activity-empty">{t("activityEmpty")}</p>}
      {!!profileRecords.length && <details className="activity-cases"><summary>{t("activityProfileDetails")} ({profileRecords.length})</summary><ol>{profileRecords.map(renderEntry)}</ol></details>}
      {!!cases.length && <details className="activity-cases"><summary>{t("caseHistory")} ({cases.length})</summary><ol>
        {[...cases].sort((a, b) => (b.month || "").localeCompare(a.month || "")).map((item, index) => <li key={`${item.caseId}:${index}`}>
          <div className="activity-meta"><span>{item.caseId}</span><span>{item.month ? `${t("activityCaseDate")}: ${item.month}` : t("activityDateUnknown")}</span></div>
          <p>{[item.crime, item.location, item.status].filter(Boolean).join(" · ")}</p>
        </li>)}
      </ol></details>}
    </div>}
  </section>;
}
