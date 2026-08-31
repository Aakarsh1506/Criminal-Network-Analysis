import { useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { criminalsDB, presetTags } from "../data/criminals";
import "./Dashboard.css";

function Dashboard() {
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [selectedTags, setSelectedTags] = useState([]);
  const [showDropdown, setShowDropdown] = useState(false);

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
    </div>
  );
}

export default Dashboard;