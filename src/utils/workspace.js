// Shared "currently working on" state for the dashboard.
// Pinning a criminal replaces whatever was pinned before (single slot).
// Adding to the list can hold many criminals (name + crime tags only).

const PIN_KEY = "cna_pinned_criminal_id";
const LIST_KEY = "cna_working_list";

export function getPinnedId() {
  const raw = localStorage.getItem(PIN_KEY);
  return raw ? Number(raw) : null;
}

export function setPinnedId(id) {
  localStorage.setItem(PIN_KEY, String(id));
}

export function clearPinnedId() {
  localStorage.removeItem(PIN_KEY);
}

export function getWorkingList() {
  try {
    const raw = localStorage.getItem(LIST_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveWorkingList(list) {
  localStorage.setItem(LIST_KEY, JSON.stringify(list));
  return list;
}

export function isInWorkingList(id) {
  return getWorkingList().some((c) => c.id === id);
}

export function addToWorkingList(criminal) {
  const list = getWorkingList();
  if (list.some((c) => c.id === criminal.id)) return list;
  const entry = { id: criminal.id, name: criminal.name, crimeTags: criminal.crimeTags };
  return saveWorkingList([...list, entry]);
}

export function removeFromWorkingList(id) {
  return saveWorkingList(getWorkingList().filter((c) => c.id !== id));
}