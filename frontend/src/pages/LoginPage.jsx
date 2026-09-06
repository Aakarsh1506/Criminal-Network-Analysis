import { useState } from "react";
import { useNavigate } from "react-router-dom";
import "./LoginPage.css";

// TODO: replace with real backend call once available.
const MOCK_VALID_ORG_ID = "CNA-1234"; // temporary — remove when backend exists
function mockAuthenticate(form) {
  return form.orgId === MOCK_VALID_ORG_ID;
}

function LoginPage() {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    name: "",
    codeName: "",
    orgName: "",
    orgId: "",
  });
  const [status, setStatus] = useState("idle"); // "idle" | "error" | "success"

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
    if (status !== "idle") setStatus("idle");
  };

  const handleAuthenticate = (e) => {
    e.preventDefault();

    // TODO: swap for a real API call, e.g. const ok = await api.login(form);
    const ok = mockAuthenticate(form);

    if (ok) {
      setStatus("success");
      setTimeout(() => navigate("/dashboard"), 500);
    } else {
      setStatus("error");
    }
  };

  const goToLanding = () => navigate("/"); // update path if your landing route differs

  return (
    <div className="login-page">
      <div className="top-bar">
        <button
          type="button"
          className="brand-logo"
          onClick={goToLanding}
          aria-label="Go to landing page"
        >
          Criminal Network Analysis
        </button>

        <button
          type="button"
          className="go-back-btn"
          onClick={goToLanding}
        >
          <svg viewBox="0 0 24 24" width="16" height="16" fill="none">
            <path
              d="M15 18l-6-6 6-6"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
          Go back
        </button>
      </div>

      <form
        className={`login-card status-${status}`}
        onSubmit={handleAuthenticate}
      >

        <h2 className="login-heading">Officer Verification</h2>
        <p className="login-instruction">Complete every field to open the case system.</p>

        <label className="field">
          <span>Officer name</span>
          <input type="text" name="name" value={form.name} onChange={handleChange} required />
        </label>

        <label className="field">
          <span>Code name</span>
          <input type="text" name="codeName" value={form.codeName} onChange={handleChange} required />
        </label>

        <label className="field">
          <span>Organisation name</span>
          <input type="text" name="orgName" value={form.orgName} onChange={handleChange} required />
        </label>

        <label className="field">
          <span>Organisation ID number</span>
          <input type="password" name="orgId" value={form.orgId} onChange={handleChange} required />
        </label>

        <button type="submit" className="login-btn full-width">
          Authenticate
        </button>

        {status === "error" && (
          <p className="status-message error">Verification failed. Check your details.</p>
        )}
        {status === "success" && (
          <p className="status-message success">Verified. Opening case system…</p>
        )}

        <p className="login-footnote">Restricted access · Authorized personnel only</p>
      </form>
    </div>
  );
}

export default LoginPage;