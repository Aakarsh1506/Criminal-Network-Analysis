import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { fetchCriminalById, fetchCrimeTypes } from "../api/criminals";
import { fetchStats } from "../api/stats";
import { fetchWorkspace, unpinCriminal, removeFromWorkingList } from "../api/workspace";
import NetworkGraph from "../components/NetworkGraph";
import RelationGraph from "../components/RelationGraph";
import "./Dashboard.css";

function Dashboard() {
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [selectedTags, setSelectedTags] = useState([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const [presetTags, setPresetTags] = useState([]);
  const [graphMode, setGraphMode] = useState("map"); // "map" | "network"

  const [stats, setStats] = useState(null);

  const [pinnedId, setPinnedIdState] = useState(null);
  const [pinnedCriminal, setPinnedCriminal] = useState(null);
  const [pinnedRelations, setPinnedRelations] = useState([]);
  const [workingList, setWorkingList] = useState([]);

  useEffect(() => {
    fetchStats().then(setStats).catch(() => setStats(null));
    fetchCrimeTypes().then(setPresetTags).catch(() => setPresetTags([]));
    fetchWorkspace()
      .then(({ pinnedId, workingList }) => {
        setPinnedIdState(pinnedId);
        setWorkingList(workingList);
      })
      .catch(() => {
        setPinnedIdState(null);
        setWorkingList([]);
      });
  }, []);

  useEffect(() => {
    if (!pinnedId) {
      setPinnedCriminal(null);
      setPinnedRelations([]);
      return;
    }
    let cancelled = false;
    fetchCriminalById(pinnedId).then((data) => {
      if (cancelled || !data) return;
      setPinnedCriminal(data.criminal);
      setPinnedRelations(data.relations);
    });
    return () => {
      cancelled = true;
    };
  }, [pinnedId]);

  const toggleTag = (tag) => {
    setSelectedTags((prev) =>
      prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag]
    );
  };

  const handleSearch = () => {
    const params = new URLSearchParams();
    if (query.trim()) params.set("q", query.trim());
    if (selectedTags.length) params.set("tags", selectedTags.join(","));
    navigate(`/search?${params.toString()}`);
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter") handleSearch();
  };

  const handleUnpin = async () => {
    try {
      await unpinCriminal();
      setPinnedIdState(null);
    } catch (err) {
      console.error("Failed to unpin criminal", err);
    }
  };

  const handleRemoveFromList = async (id) => {
    try {
      await removeFromWorkingList(id);
      setWorkingList((prev) => prev.filter((c) => c.id !== id));
    } catch (err) {
      console.error("Failed to remove from list", err);
    }
  };

  const tagCounts = stats?.tagCounts || [];
  const cityCounts = stats?.cityCounts || [];
  const maxTagCount = Math.max(...tagCounts.map((t) => t[1]), 1);

  return (
    <div className="board-page">
      <div className="search-tab-wrapper">
        <div className="search-tab">
          <input
            type="text"
            className="search-input"
            placeholder="Search a name, or type a crime — robbery, fraud..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onFocus={() => setShowDropdown(true)}
            onKeyDown={handleKeyDown}
          />
          <button className="stamp-btn small" onClick={handleSearch}>
            Search
          </button>
        </div>

        {showDropdown && (
          <div className="tag-note">
            <div className="tag-note-head">
              <span>Known crime tags</span>
              <button onClick={() => setShowDropdown(false)}>Close</button>
            </div>
            <div className="tag-chip-list">
              {presetTags.map((tag) => (
                <button
                  key={tag}
                  className={`tag-chip ${selectedTags.includes(tag) ? "tag-chip-active" : ""}`}
                  onClick={() => toggleTag(tag)}
                >
                  {tag}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="working-section">
        <h3 className="working-heading">Currently Pinned</h3>

        <div className="working-grid">
          {/* Map now occupies the full wide (2fr) column instead of a single narrow slot */}
          <div className="working-col working-map-col">
            {pinnedCriminal ? (
              <>
                <div className="working-map-toolbar">
                  <div className="graph-toggle" role="tablist" aria-label="Graph view">
                    <button
                      type="button"
                      className={`graph-toggle-btn ${graphMode === "map" ? "graph-toggle-active" : ""}`}
                      onClick={() => setGraphMode("map")}
                    >
                      Map
                    </button>
                    <button
                      type="button"
                      className={`graph-toggle-btn ${graphMode === "network" ? "graph-toggle-active" : ""}`}
                      onClick={() => setGraphMode("network")}
                    >
                      Network
                    </button>
                  </div>
                </div>
                <div className="graph-frame mini">
                  {graphMode === "map" ? (
                    <NetworkGraph
                      mainCriminal={pinnedCriminal}
                      relations={pinnedRelations}
                      onNodeClick={(relatedId) => navigate(`/criminal/${relatedId}`)}
                      height={560}
                    />
                  ) : (
                    <RelationGraph
                      mainCriminal={pinnedCriminal}
                      onNodeClick={(relatedId) => navigate(`/criminal/${relatedId}`)}
                      height={560}
                    />
                  )}
                </div>
              </>
            ) : (
              <div className="working-empty">
                <p className="empty-note">Not working on anyone currently</p>
              </div>
            )}
          </div>

          {/* Narrow (1fr) column split into two stacked halves: profile on top, list below */}
          <div className="working-col working-side-col">
            <div className="working-side-top">
              {pinnedCriminal ? (
                <div className="mini-dossier">
                  <img src={pinnedCriminal.photo} alt={pinnedCriminal.name} className="mini-photo" />
                  <h4>{pinnedCriminal.name}</h4>
                  <p className="dossier-alias">Known as "{pinnedCriminal.alias}"</p>
                  <div className="dossier-row"><span>Last seen</span><span>{pinnedCriminal.lastSeen}</span></div>
                  <div className="tag-row">
                    {pinnedCriminal.crimeTags.map((tag) => (
                      <span key={tag} className="tag-stamp">{tag}</span>
                    ))}
                  </div>
                  <div className="mini-actions">
                    <button className="stamp-btn small" onClick={() => navigate(`/criminal/${pinnedCriminal.id}`)}>
                      Open file
                    </button>
                    <button className="stamp-btn small" onClick={handleUnpin}>
                      Unpin
                    </button>
                  </div>
                </div>
              ) : (
                <div className="working-empty">
                  <p className="empty-note">Not working on anyone currently</p>
                </div>
              )}
            </div>

            <div className="working-side-divider" />

            <div className="working-side-bottom">
              <h4 className="working-list-title">On the list</h4>
              {workingList.length === 0 ? (
                <p className="empty-note">No cases added yet</p>
              ) : (
                <ul className="working-list-items">
                  {workingList.map((c) => (
                    <li key={c.id}>
                      <div className="working-list-info" onClick={() => navigate(`/criminal/${c.id}`)}>
                        <strong>{c.name}</strong>
                        <div className="tag-row">
                          {c.crimeTags.map((tag) => (
                            <span key={tag} className="tag-stamp small">{tag}</span>
                          ))}
                        </div>
                      </div>
                      <button className="list-remove-btn" onClick={() => handleRemoveFromList(c.id)}>
                        ×
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="pinboard">
        <div className="pin-card card-1">
          <span className="pin" />
          <h3>Records on file</h3>
          <div className="pin-number">{stats ? stats.totalCriminals : "…"}</div>
          <p className="pin-note">Criminals currently tracked</p>
        </div>

        <div className="pin-card card-2 wide">
          <span className="pin" />
          <h3>Crime tag frequency</h3>
          <div className="bar-list">
            {tagCounts.map(([tag, count]) => (
              <div className="bar-row" key={tag}>
                <span className="bar-label">{tag}</span>
                <div className="bar-track">
                  <div className="bar-fill" style={{ width: `${(count / maxTagCount) * 100}%` }} />
                </div>
                <span className="bar-count">{count}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="pin-card card-3">
          <span className="pin" />
          <h3>Cities under watch</h3>
          <ul className="city-list">
            {cityCounts.map(([city, count]) => (
              <li key={city}>
                <span>{city}</span>
                <span>{count}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="pin-card card-4">
          <span className="pin" />
          <h3>Traced connections</h3>
          <div className="pin-number">{stats ? stats.tracedConnections : "…"}</div>
          <p className="pin-note">Links between known associates</p>
        </div>
      </div>
    </div>
  );
}

export default Dashboard;