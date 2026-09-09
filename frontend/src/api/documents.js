const BASE = "/api/documents";

async function request(path, options = {}) {
  const response = await fetch(`${BASE}${path}`, { credentials: "include", ...options });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.error || "Document request failed");
  return body;
}

export const fetchDocuments = () => request("");
export const fetchDocument = (id) => request(`/${id}`);
export const fetchSourceTypes = () => request("/source-types");
export const retryDocument = (id) => request(`/${id}/process`, { method: "POST" });

export function uploadDocument(file, sourceType) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("sourceType", sourceType);
  // Let the browser add the multipart boundary.
  return request("", { method: "POST", body: formData });
}

export function documentFileUrl(id) {
  return `${BASE}/${id}/file`;
}

export const confirmDocument = (id, extraction) => request(`/${id}/confirm`, {
  method: "POST", headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ extraction }),
});
