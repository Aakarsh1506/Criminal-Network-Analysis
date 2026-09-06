import { useState } from "react";
import { useNavigate } from "react-router-dom";
import "./LoginPage.css";

// TODO: replace with a real backend call once available.
const MOCK_VALID_CODE = "CNA-1234"; // temporary — remove when backend exists

const STEPS = [
  { key: "name", label: "Officer name", type: "text", prompt: "State your full name for the record." },
  { key: "dob", label: "Date of birth", type: "text", placeholder: "DD.MM.YYYY", prompt: "Confirm your date of birth." },
  { key: "orgName", label: "Organisation name", type: "text", prompt: "Identify your organisation." },
  { key: "orgCode", label: "Organisation access code", type: "password", prompt: "Enter your organisation access code to unlock this file." },
];

function LoginPage() {
  const navigate = useNavigate();
  const [form, setForm] = useState({ name: "", dob: "", orgName: "", orgCode: "" });
  const [stepIndex, setStepIndex] = useState(0);
  const [value, setValue] = useState("");
  const [status, setStatus] = useState("idle"); // "idle" | "denied" | "flipped"

  const step = STEPS[stepIndex];
  const isLastStep = stepIndex === STEPS.length - 1;

  const handleChange = (e) => {
    setValue(e.target.value);
    if (status === "denied") setStatus("idle");
  };

  const handleSubmitStep = (e) => {
    e.preventDefault();
    if (!value.trim()) return;

    if (isLastStep) {
      // TODO: swap for a real API call, e.g. const ok = await api.login({ ...form, orgCode: value });
      const ok = value === MOCK_VALID_CODE;
      if (ok) {
        setForm((f) => ({ ...f, orgCode: value }));
        setStatus("flipped"); // triggers the page-turn reveal, waits for "Enter"
      } else {
        setStatus("denied");
      }
      return;
    }

    setForm((f) => ({ ...f, [step.key]: value }));
    setValue("");
    setStepIndex((i) => i + 1);
  };

  const handleEnter = () => navigate("/dashboard");
  const handleBack = () => navigate("/");

  const statusLabel =
    status === "denied" ? "ACCESS DENIED" : `AWAITING ${step.label.toUpperCase()}`;

  return (
    <div className="login-page">
      <button type="button" className="back-btn" onClick={handleBack}>
        ← Back
      </button>

      <div className={`case-flip-wrapper ${status === "flipped" ? "is-flipped" : ""}`}>
        <div className="case-flip-inner">

          {/* FRONT — the unlock steps */}
          <div className={`case-face case-face-front ${status === "denied" ? "status-denied" : ""}`}>
            <div className="case-meta">
              <div className="case-meta-left">
                <div className="meta-row"><span>CASE ID</span><span>: OFFICER-ACCESS</span></div>
                <div className="meta-row"><span>CLASSIFICATION</span><span>: <em className="hot">TOP SECRET</em> / LEVEL S</span></div>
                <div className="meta-row"><span>PRIORITY</span><span>: ABSOLUTE</span></div>
                <div className="meta-row">
                  <span>STATUS</span>
                  <span>: <em className={status === "denied" ? "hot" : "pending"}>{statusLabel}</em></span>
                </div>
                <div className="meta-row"><span>FILE TYPE</span><span>: OFFICER ACCESS</span></div>
              </div>

              <div className="scales-box">
                <svg viewBox="0 0 64 64" width="32" height="32" fill="none" stroke="#d1453c" strokeWidth="2">
                  <path
                    d="M32 6v40M14 18h36M14 18l-8 16h16l-8-16zM50 18l-8 16h16l-8-16zM20 54h24"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
                <p>NO ONE ENTERS UNVERIFIED.</p>
              </div>
            </div>

            <div className="subject-block">
              <div className="subject-photo">
                <span className="tape" aria-hidden="true" />
                <svg viewBox="0 0 100 120" width="100%" height="100%">
                  <rect width="100" height="120" fill="#0c0c0c" />
                  <circle cx="50" cy="42" r="20" fill="#1c1c1c" />
                  <path d="M15 118c2-28 20-40 35-40s33 12 35 40z" fill="#1c1c1c" />
                </svg>
                <span className="stamp stamp-photo">{status === "denied" ? "DENIED" : "UNVERIFIED"}</span>
              </div>

              <div className="subject-info">
                <p className="subject-label">Subject</p>
                <p className="subject-name">{form.name ? form.name.toUpperCase() : "UNKNOWN"}</p>

                <p className="subject-line"><span>DOB</span>{form.dob || "UNKNOWN"}</p>
                <p className="subject-line"><span>ORGANISATION</span>{form.orgName || "UNKNOWN"}</p>
                <p className="subject-line"><span>THREAT LEVEL</span><em className="hot">EXTREME</em></p>
              </div>
            </div>

            <form className="unlock-form" onSubmit={handleSubmitStep}>
              <label className="unlock-label">
                {step.prompt}
                <input
                  type={step.type}
                  value={value}
                  placeholder={step.placeholder}
                  onChange={handleChange}
                  autoFocus
                  required
                />
              </label>

              <button type="submit" className="unlock-btn">
                {isLastStep ? "Unlock file" : "Continue"}
              </button>

              {status === "denied" && <p className="denied-text">Access code rejected. Try again.</p>}
            </form>

            <div className="warning-strip">
              <span className="warn-icon">!</span>
              <p>
                THIS FILE CONTAINS SENSITIVE INFORMATION. UNAUTHORIZED ACCESS, COPYING, OR
                DISCLOSURE IS STRICTLY PROHIBITED. VIOLATORS WILL BE PROSECUTED TO THE FULL EXTENT OF THE LAW.
              </p>
              <span className="lock-icon" aria-hidden="true">🔒</span>
            </div>
          </div>

          {/* BACK — confirmation, revealed by the page turn */}
          <div className="case-face case-face-back">
            <div className="seal" aria-hidden="true">
              <span>CNA</span>
            </div>
            <h2 className="back-title">Criminal Network Analysis</h2>
            <p className="back-subtitle">Identity confirmed. Review before entering the case system.</p>

            <div className="back-summary">
              <div className="summary-row"><span>Officer name</span><span>{form.name}</span></div>
              <div className="summary-row"><span>Date of birth</span><span>{form.dob}</span></div>
              <div className="summary-row"><span>Organisation</span><span>{form.orgName}</span></div>
              <div className="summary-row"><span>Access code</span><span>••••••••</span></div>
            </div>

            <button type="button" className="enter-btn" onClick={handleEnter}>
              Enter
            </button>
          </div>

        </div>
      </div>
    </div>
  );
}

export default LoginPage;