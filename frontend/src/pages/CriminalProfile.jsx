import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { fetchCriminalById } from "../api/criminals";
import {
  fetchWorkspace, pinCriminal, unpinCriminal,
  addToWorkingList, removeFromWorkingList,
} from "../api/workspace";
import NetworkExplanation from "../components/NetworkExplanation";
import NetworkGraph from "../components/NetworkGraph";
import BackButton from "../components/BackButton";
import "./CriminalProfile.css";
import RelationGraph from "../components/RelationGraph";

function CriminalProfile() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [criminal, setCriminal] = useState(null);
  const [relations, setRelations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);

  const [pinnedId, setPinnedIdState] = useState(null);
  const [inList, setInList] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setNotFound(false);

    Promise.all([fetchCriminalById(id), fetchWorkspace()])
      .then(([data, workspace]) => {
        if (cancelled) return;
        if (!data) {
          setNotFound(true);
          return;
        }
        setCriminal(data.criminal);
        setRelations(data.relations);
        setPinnedIdState(workspace.pinnedId);
        setInList(workspace.workingList.some((c) => c.id === data.criminal.id));
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
        <BackButton />
        <p className="empty-note">This file does not exist.</p>
      </div>
    );
  }

  const isPinned = pinnedId === criminal.id;

  const handlePinToggle = async () => {
    try {
      if (isPinned) {
        await unpinCriminal();
        setPinnedIdState(null);
      } else {
        await pinCriminal(criminal.id);
        setPinnedIdState(criminal.id);
      }
    } catch (err) {
      console.error("Failed to update pin", err);
    }
  };

  const handleListToggle = async () => {
    try {
      if (inList) {
        await removeFromWorkingList(criminal.id);
        setInList(false);
      } else {
        await addToWorkingList(criminal.id);
        setInList(true);
      }
    } catch (err) {
      console.error("Failed to update working list", err);
    }
  };

  return (
    <div className="dossier-page">
      <BackButton />

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
          >
            <RelationGraph
              mainCriminal={criminal}
              onNodeClick={(relatedId) => navigate(`/criminal/${relatedId}`)}
              height={520}
            />
          </div>
          <NetworkExplanation key={id} id={id} />
        </div>
      </div>
    </div>
  );
}

export default CriminalProfile;
