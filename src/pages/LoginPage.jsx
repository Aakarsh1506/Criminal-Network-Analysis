import { useState } from "react";
import { useNavigate } from "react-router-dom";
import "./LoginPage.css";

function LoginPage() {
  const navigate = useNavigate();
  const [form, setForm] = useState({ name: "", dob: "", codeName: "", orgCode: "" });

  const handleChange = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  const handleAuthenticate = (e) => {
    e.preventDefault();
    navigate("/dashboard");
  };

  return (
    <div className="login-page">
      <form className="case-form" onSubmit={handleAuthenticate}>
        <span className="form-pin" />
        <span className="form-number">Form CNA-1</span>
        <h2 className="form-heading">Officer verification</h2>
        <p className="form-instruction">Complete every field to open the case system.</p>

        <label className="field">
          <span>Name</span>
          <input type="text" name="name" value={form.name} onChange={handleChange} required />
        </label>

        <label className="field">
          <span>Date of birth</span>
          <input type="date" name="dob" value={form.dob} onChange={handleChange} required />
        </label>

        <label className="field">
          <span>Code name</span>
          <input type="text" name="codeName" value={form.codeName} onChange={handleChange} required />
        </label>

        <label className="field">
          <span>Organisation code word</span>
          <input type="password" name="orgCode" value={form.orgCode} onChange={handleChange} required />
        </label>

        <button type="submit" className="stamp-btn full-width">
          Authenticate
        </button>
      </form>
    </div>
  );
}

export default LoginPage;