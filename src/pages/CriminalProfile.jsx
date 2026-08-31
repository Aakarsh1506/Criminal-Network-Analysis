import { useParams, useNavigate } from "react-router-dom";
import { getCriminalById, getRelationsForCriminal } from "../data/criminals";
import "./CriminalProfile.css";

function CriminalProfile() {
  const { id } = useParams();
  const navigate = useNavigate();
  const criminal = getCriminalById(id);
  const relations = getRelationsForCriminal(id);

  if (!criminal) {
    return (
      <div className="dossier-page">
        <p className="empty-note">This file does not exist.</p>
        <button className="stamp-btn" onClick={() => navigate("/dashboard")}>
          Back to dashboard
        </button>
      </div>
    );
  }

  return (
    <div className="dossier-page">
      <div className="dossier-grid">
        <div className="dossier-left">
          <div className="dossier-sheet">
            <span className="form-number">File {criminal.id.toString().padStart(3, "0")}</span>
            <img src={criminal.photo} alt={criminal.name} className="dossier-photo" />
            <h2>{criminal.name}</h2>
            <p className="dossier-alias">Known as "{criminal.alias}"</p>

            <div className="dossier-row"><span>Date of birth</span><span>{criminal.dob}</span></div>
            <div className="dossier-row"><span>Age</span><span>{criminal.age}</span></div>
            <div className="dossier-row"><span>Height</span><span>{criminal.height}</span></div>
            <div className="dossier-row"><span>Last seen</span><span>{criminal.lastSeen}</span></div>

            <div className="dossier-section">
              <h4>Family</h4>
              {criminal.family.map((f) => (
                <div className="dossier-row" key={f.name}>
                  <span>{f.name}, {f.relation.toLowerCase()}</span>
                  <span>{f.age} yrs</span>
                </div>
              ))}
            </div>

            <div className="dossier-section">
              <h4>Crimes committed</h4>
              <div className="tag-row">
                {criminal.crimeTags.map((tag) => (
                  <span key={tag} className="tag-stamp">{tag}</span>
                ))}
              </div>
            </div>
          </div>

          <button className="stamp-btn full-width" onClick={() => navigate("/dashboard")}>
            Close file
          </button>
        </div>

        <div className="dossier-right">
          <p className="board-caption">Traced associates across India</p>
          <div className="string-board">
            <svg className="string-svg" viewBox="0 0 100 100" preserveAspectRatio="none">
              {relations.map((r) => (
                <line
                  key={r.criminal.id}
                  x1={criminal.location.x}
                  y1={criminal.location.y}
                  x2={r.criminal.location.x}
                  y2={r.criminal.location.y}
                  className="string-line"
                />
              ))}
            </svg>

            <div className="board-pin main-pin" style={{ left: `${criminal.location.x}%`, top: `${criminal.location.y}%` }}>
              <img src={criminal.photo} alt={criminal.name} />
              <span className="pin-label">{criminal.name}</span>
            </div>

            {relations.map((r) => (
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
        </div>
      </div>
    </div>
  );
}

export default CriminalProfile;