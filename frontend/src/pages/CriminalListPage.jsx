import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { fetchAllCriminals } from "../api/criminals";
import { getWorkingList, addToWorkingList, removeFromWorkingList } from "../utils/workspace";
import BackButton from "../components/BackButton";
import "./CriminalList.css";

function CriminalListPage() {
  const navigate = useNavigate();

  const [listedIds, setListedIds] = useState(() => getWorkingList().map((c) => c.id));
  const [criminals, setCriminals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    fetchAllCriminals()
      .then((data) => {
        if (!cancelled) setCriminals(data);
      })
      .catch(() => {
        if (!cancelled) setError("Could not reach the case database.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const handleToggleList = (e, criminal) => {
    e.stopPropagation();
    if (listedIds.includes(criminal.id)) {
      removeFromWorkingList(criminal.id);
      setListedIds((prev) => prev.filter((id) => id !== criminal.id));
    } else {
      addToWorkingList(criminal);
      setListedIds((prev) => [...prev, criminal.id]);
    }
  };

  return (
    <div className="list-page">
      <BackButton />

      <header className="list-top">
        <h2>{loading ? "Loading records…" : `${criminals.length} criminal${criminals.length !== 1 ? "s" : ""} on file`}</h2>
      </header>

      <div className="folder-stack">
        {error && <p className="empty-note">{error}</p>}
        {!loading && !error && criminals.length === 0 && (
          <p className="empty-note">No records found in the database.</p>
        )}

        {criminals.map((c, i) => (
          <div
            key={c.id}
            className="folder"
            style={{ transform: `rotate(${i % 2 === 0 ? -0.5 : 0.5}deg)` }}
            onClick={() => navigate(`/criminal/${c.id}`)}
          >
            <span className="folder-tab">{c.id}</span>
            <img src={c.photo} alt={c.name} className="folder-photo" />
            <div className="folder-info">
              <h3>{c.name}</h3>
              <p className="folder-alias">Known as "{c.alias}", based in {c.location.city}</p>
              <div className="tag-row">
                {c.crimeTags.map((tag) => <span key={tag} className="tag-stamp">{tag}</span>)}
              </div>
            </div>
            <button
              className={`list-toggle-btn ${listedIds.includes(c.id) ? "list-toggle-active" : ""}`}
              onClick={(e) => handleToggleList(e, c)}
            >
              {listedIds.includes(c.id) ? "Remove from list" : "Add to list"}
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

export default CriminalListPage;