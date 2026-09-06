// Talks to the backend API (backend/routes/criminals.js), which reads from
// the real Postgres database instead of a hardcoded array.

const BASE = "/api/criminals";

export async function fetchCriminals({ q = "", tags = [] } = {}) {
  const params = new URLSearchParams();
  if (q) params.set("q", q);
  if (tags.length) params.set("tags", tags.join(","));
  const qs = params.toString();
  const res = await fetch(qs ? `${BASE}?${qs}` : BASE);
  if (!res.ok) throw new Error("Failed to load criminals");
  return res.json();
}

// Returns every criminal on file — used by the full database listing page,
// unlike fetchCriminals() which returns [] with no query/tags.
export async function fetchAllCriminals() {
  const res = await fetch(`${BASE}?all=true`);
  if (!res.ok) throw new Error("Failed to load criminals");
  return res.json();
}

// Returns { criminal, relations } or null if not found
export async function fetchCriminalById(id) {
  const res = await fetch(`${BASE}/${id}`);
  if (res.status === 404) return null;
  if (!res.ok) throw new Error("Failed to load criminal");
  return res.json();
}

export async function fetchCrimeTypes() {
  const res = await fetch("/api/crime-types");
  if (!res.ok) throw new Error("Failed to load crime types");
  return res.json();
}