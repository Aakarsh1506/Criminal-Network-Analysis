import { useEffect, useState } from "react";
import { Navigate, Outlet } from "react-router-dom";
import { fetchCurrentOfficer } from "../api/auth";

// Wraps protected routes (see App.jsx). Confirms the session cookie is
// still valid before rendering anything behind it, and bounces to /login
// otherwise — covers direct URL access, page refresh, and expired tokens.
function RequireAuth() {
  const [status, setStatus] = useState("checking"); // "checking" | "authed" | "denied"

  useEffect(() => {
    let cancelled = false;
    fetchCurrentOfficer().then((officer) => {
      if (cancelled) return;
      setStatus(officer ? "authed" : "denied");
    });
    return () => {
      cancelled = true;
    };
  }, []);

  if (status === "checking") return null; // avoid a flash of protected content
  if (status === "denied") return <Navigate to="/login" replace />;
  return <Outlet />;
}

export default RequireAuth;