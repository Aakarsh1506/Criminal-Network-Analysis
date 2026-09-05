import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { fetchCriminalById } from "../api/criminals";
import {
  getPinnedId, setPinnedId, clearPinnedId,
  isInWorkingList, addToWorkingList, removeFromWorkingList,
} from "../utils/workspace";
import NetworkGraph from "../components/NetworkGraph";
import indiaMap from "/images/India.svg";
import "./CriminalProfile.css";

function CriminalProfile() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [criminal, setCriminal] = useState(null);
  const [relations, setRelations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);

  const [pinnedId, setPinnedIdState] = useState(() => getPinnedId());
  const [inList, setInList] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setNotFound(false);

    fetchCriminalById(id)
      .then((data) => {
        if (cancelled) return;
        if (!data) {
          setNotFound(true);
          return;
        }
        setCriminal(data.criminal);
        setRelations(data.relations);
        setInList(isInWorkingList(data.criminal.id));
      })
      .catch(() => {
        if (!cancelled) setNotFound(true);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [id]);

  if (loading) {
    return <div className="dossier-page"><p className="empty-note">Loading file…</p></div>;
  }

  if (notFound || !criminal) {
    return (
      <div className="dossier-page">
        <p className="empty-note">This file does not exist.</p>
        <button className="stamp-btn" onClick={() => navigate("/dashboard")}>Back to dashboard</button>
      </div>
    );
  }

  const isPinned = pinnedId === criminal.id;

  const handlePinToggle = () => {
    if (isPinned) {
      clearPinnedId();
      setPinnedIdState(null);
    } else {
      setPinnedId(criminal.id);
      setPinnedIdState(criminal.id);
    }
  };

  const handleListToggle = () => {
    if (inList) {
      removeFromWorkingList(criminal.id);
      setInList(false);
    } else {
      addToWorkingList(criminal);
      setInList(true);
    }
  };

  return (
    <div className="dossier-page">
      <div className="dossier-grid">
        <div className="dossier-left">
          <div className="dossier-sheet">
            <div className="dossier-header">
              <img src={criminal.photo} alt={criminal.name} className="dossier-photo" />
              <span className="form-number">File {criminal.id}</span>
              <h2>{criminal.name}</h2>
              <p className="dossier-alias">Known as "{criminal.alias}"</p>
            </div>

            <div className="dossier-row"><span>Date of birth</span><span>{criminal.dob}</span></div>
            <div className="dossier-row"><span>Age</span><span>{criminal.age}</span></div>
            <div className="dossier-row"><span>Height</span><span>{criminal.heightCm} cm</span></div>
            <div className="dossier-row"><span>Last seen</span><span>{criminal.lastSeen}</span></div>
            <div className="dossier-row"><span>Status</span><span>{criminal.recordStatus}</span></div>

            {criminal.familyKnown && (
              <div className="dossier-section">
                <h4>Family known</h4>
                <p>{criminal.familyKnown}</p>
              </div>
            )}

            <div className="dossier-section">
              <h4>Crimes committed</h4>
              <div className="tag-row">
                {criminal.crimeTags.map((tag) => <span key={tag} className="tag-stamp">{tag}</span>)}
              </div>
            </div>

            {criminal.cases && criminal.cases.length > 0 && (
              <div className="dossier-section">
                <h4>Case history</h4>
                {criminal.cases.map((c) => (
                  <div className="dossier-row" key={c.caseId}>
                    <span>{c.caseId} — {c.crime}, {c.location}</span>
                    <span>{c.status}</span>
                  </div>
                ))}
              </div>
            )}

            <div className="dossier-actions">
              <button className={`stamp-btn small ${isPinned ? "stamp-btn-active" : ""}`} onClick={handlePinToggle}>
                {isPinned ? "Unpin from dashboard" : "Pin to dashboard"}
              </button>
              <button className={`stamp-btn small ${inList ? "stamp-btn-active" : ""}`} onClick={handleListToggle}>
                {inList ? "Remove from list" : "Add to list"}
              </button>
            </div>
          </div>

          <button className="stamp-btn full-width" onClick={() => navigate("/dashboard")}>Close file</button>
        </div>

        <div className="dossier-right">
          <p className="board-caption">Traced associates across India</p>
          <div
            className="graph-frame"
            style={{ "--india-map-url": `url(${indiaMap})` }}
          >
            <NetworkGraph
              mainCriminal={criminal}
              relations={relations}
              onNodeClick={(relatedId) => navigate(`/criminal/${relatedId}`)}
              height={520}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

export default CriminalProfile;