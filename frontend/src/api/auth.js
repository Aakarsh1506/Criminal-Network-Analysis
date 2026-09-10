// Talks to backend/routes/auth.js. The session lives in an httpOnly cookie
// set by the server on login — this file never sees or stores a token
// itself, it just needs `credentials: "include"` on every call so the
// cookie is sent (and, in prod, when frontend/backend are different
// origins).

const BASE = "/api/auth";

export async function login(username, password) {
  const res = await fetch(`${BASE}/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ username, password }),
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.error || "Login failed");
  }

  return res.json(); // officer profile
}

export async function logout() {
  await fetch(`${BASE}/logout`, { method: "POST", credentials: "include" });
}

// Returns the officer profile if the session cookie is still valid, or
// null if not logged in / expired. Never throws — callers just branch on
// the return value.
export async function fetchCurrentOfficer() {
  const res = await fetch(`${BASE}/me`, { credentials: "include" });
  if (!res.ok) return null;
  return res.json();
}