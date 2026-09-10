// Per-officer "currently working on" state, backed by /api/workspace.
// Replaces the old localStorage version — the cookie-authenticated backend
// now scopes pin/list to whichever officer is logged in.

const BASE = "/api/workspace";

export async function fetchWorkspace() {
  const res = await fetch(BASE);
  if (!res.ok) throw new Error("Failed to load workspace");
  return res.json(); // { pinnedId, workingList: [{id, name, crimeTags}] }
}

export async function pinCriminal(personId) {
  const res = await fetch(`${BASE}/pin`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ personId }),
  });
  if (!res.ok) throw new Error("Failed to pin criminal");
  return res.json();
}

export async function unpinCriminal() {
  const res = await fetch(`${BASE}/pin`, { method: "DELETE" });
  if (!res.ok) throw new Error("Failed to unpin criminal");
  return res.json();
}

export async function addToWorkingList(personId) {
  const res = await fetch(`${BASE}/list`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ personId }),
  });
  if (!res.ok) throw new Error("Failed to add to list");
  return res.json();
}

export async function removeFromWorkingList(personId) {
  const res = await fetch(`${BASE}/list/${personId}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Failed to remove from list");
  return res.json();
}