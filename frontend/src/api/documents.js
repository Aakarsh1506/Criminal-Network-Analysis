const BASE = "/api/documents";

export async function fetchDocuments() {
  const res = await fetch(BASE, { credentials: "include" });
  if (!res.ok) throw new Error("Failed to load documents");
  return res.json();
}

export async function uploadDocument(file) {
  const formData = new FormData();
  formData.append("file", file);
  // No Content-Type header here — the browser sets the multipart
  // boundary itself when the body is a FormData object.
  const res = await fetch(BASE, {
    method: "POST",
    credentials: "include",
    body: formData,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.error || "Failed to upload document");
  }
  return res.json();
}

export function documentFileUrl(id) {
  return `${BASE}/${id}/file`;
}