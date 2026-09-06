import { useEffect, useState } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { fetchCriminals } from "../api/criminals";
import { getWorkingList, addToWorkingList, removeFromWorkingList } from "../utils/workspace";
import "./CriminalList.css";

function CriminalList() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const [listedIds, setListedIds] = useState(() => getWorkingList().map((c) => c.id));
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const q = (searchParams.get("q") || "").trim();
  const tags = (searchParams.get("tags") || "").split(",").map((t) => t.trim()).filter(Boolean);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    fetchCriminals({ q, tags })
      .then((data) => {
        if (!cancelled) setResults(data);
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
  }, [q, tags.join(",")]);

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
      <header className="list-top">
        <button className="link-back" onClick={() => navigate("/dashboard")}>Back to dashboard</button>
        <h2>{loading ? "Searching…" : `${results.length} file${results.length !== 1 ? "s" : ""} matched`}</h2>
      </header>

      <div className="folder-stack">
        {error && <p className="empty-note">{error}</p>}
        {!loading && !error && results.length === 0 && (
          <p className="empty-note">No case file matches that search.</p>
        )}

        {results.map((c, i) => (
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

export default CriminalList;