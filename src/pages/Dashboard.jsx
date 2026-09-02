import { useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { criminalsDB, presetTags, getCriminalById, getRelationsForCriminal } from "../data/criminals";
import { getPinnedId, clearPinnedId, getWorkingList, removeFromWorkingList } from "../utils/workspace";
import "./Dashboard.css";

function Dashboard() {
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [selectedTags, setSelectedTags] = useState([]);
  const [showDropdown, setShowDropdown] = useState(false);

  const [pinnedId, setPinnedIdState] = useState(() => getPinnedId());
  const [workingList, setWorkingList] = useState(() => getWorkingList());

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

  const handleUnpin = () => {
    clearPinnedId();
    setPinnedIdState(null);
  };

  const handleRemoveFromList = (id) => {
    const updated = removeFromWorkingList(id);
    setWorkingList(updated);
  };

  const totalCriminals = criminalsDB.length;

  const tagCounts = useMemo(() => {
    const counts = {};
    criminalsDB.forEach((c) =>
      c.crimeTags.forEach((tag) => {
        counts[tag] = (counts[tag] || 0) + 1;
      })
    );
    return Object.entries(counts).sort((a, b) => b[1] - a[1]);
  }, []);

  const cityCounts = useMemo(() => {
    const counts = {};
    criminalsDB.forEach((c) => {
      counts[c.location.city] = (counts[c.location.city] || 0) + 1;
    });
    return Object.entries(counts);
  }, []);

  const maxTagCount = Math.max(...tagCounts.map((t) => t[1]), 1);

  const pinnedCriminal = pinnedId ? getCriminalById(pinnedId) : null;
  const pinnedRelations = pinnedCriminal ? getRelationsForCriminal(pinnedCriminal.id) : [];

  return (
    <div className="board-page">
      <header className="board-header">
        <span className="header-mark">CNA</span>
        <span className="header-title">Criminal Investigation</span>
      </header>

      <div className="search-tab-wrapper">
        <div className="search-tab">
          <input
            type="text"
            className="search-input"
            placeholder="Search a name, or type a crime — murder, theft..."
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

      <div className="pinboard">
        <div className="pin-card card-1">
          <span className="pin" />
          <h3>Records on file</h3>
          <div className="pin-number">{totalCriminals}</div>
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
          <div className="pin-number">5</div>
          <p className="pin-note">Links between known associates</p>
        </div>
      </div>

      <div className="working-section">
        <h3 className="working-heading">Currently working on / researching</h3>

        <div className="working-grid">
          <div className="working-col working-map-col">
            {pinnedCriminal ? (
              <div className="string-board mini-board">
                <svg className="string-svg" viewBox="0 0 100 100" preserveAspectRatio="none">
                  {pinnedRelations.map((r) => (
                    <line
                      key={r.criminal.id}
                      x1={pinnedCriminal.location.x}
                      y1={pinnedCriminal.location.y}
                      x2={r.criminal.location.x}
                      y2={r.criminal.location.y}
                      className="string-line"
                    />
                  ))}
                </svg>

                <div
                  className="board-pin main-pin"
                  style={{ left: `${pinnedCriminal.location.x}%`, top: `${pinnedCriminal.location.y}%` }}
                >
                  <img src={pinnedCriminal.photo} alt={pinnedCriminal.name} />
                  <span className="pin-label">{pinnedCriminal.name}</span>
                </div>

                {pinnedRelations.map((r) => (
                  <div
                    key={r.criminal.id}
                    className="board-pin"
                    style={{ left: `${r.criminal.location.x}%`, top: `${r.criminal.location.y}%` }}
                    onClick={() => navigate(`/criminal/${r.criminal.id}`)}
                  >
                    <img src={r.criminal.photo} alt={r.criminal.name} />
                    <span className="pin-label">{r.criminal.name}</span>
                    <span className="pin-relation">{r.type}</span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="working-empty">
                <p className="empty-note">Not working on anyone currently</p>
              </div>
            )}
          </div>

          <div className="working-col working-profile-col">
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

          <div className="working-col working-list-col">
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
  );
}

export default Dashboard;