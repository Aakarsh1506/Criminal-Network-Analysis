const BASE = "/api/officers";

export async function fetchOfficers() {
  const res = await fetch(BASE, { credentials: "include" });
  if (!res.ok) throw new Error("Failed to load officers");
  return res.json();
}

export async function createOfficer(officer) {
  const res = await fetch(BASE, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(officer),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.error || "Failed to create officer");
  }
  return res.json();
}

export async function deactivateOfficer(officerId) {
  const res = await fetch(`${BASE}/${officerId}/deactivate`, {
    method: "PATCH",
    credentials: "include",
  });
  if (!res.ok) throw new Error("Failed to deactivate officer");
  return res.json();
}