import { useNavigate } from "react-router-dom";
import "./LandingPage.css";

function LandingPage() {
  const navigate = useNavigate();

  return (
    <div className="landing-page">
      <div className="cover-sheet">
        <span className="cover-stamp">Restricted</span>
        <p className="cover-case-no">Case file no. CNA-000</p>
        <h1 className="cover-title">Criminal Network Analysis</h1>
        <p className="cover-subtitle">
          Compiled intelligence on active suspects, their known associates, and the
          ground they move on.
        </p>
        <button className="stamp-btn" onClick={() => navigate("/login")}>
          Authenticate
        </button>
      </div>
    </div>
  );
}

export default LandingPage;