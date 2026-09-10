import { AIError } from "./groq.js";

export function validateSelection(selection) {
  if (!selection || !["node", "edge", "person"].includes(selection.type)
      || typeof selection.id !== "string" || !selection.id.trim() || selection.id.length > 512) {
    throw new AIError("Select a node or relationship to generate AI insight.", 400);
  }
}

export function buildInsightContext(network, selection) {
  validateSelection(selection);
  const { nodes = [], edges = [] } = network ?? {};
  const records = selection.type === "edge" ? edges : nodes;
  const selected = records.find((item) => (selection.type === "person" ? String(item.personId) : item.id) === selection.id);
  if (!selected) throw new AIError("Selection is no longer available in this network. Select another record.", 404);
  const connected = selection.type === "edge" ? [selected] : edges.filter((edge) => edge.source === selected.id || edge.target === selected.id);
  const relationships = connected.slice(0, 25);
  const ids = new Set(relationships.flatMap((edge) => [edge.source, edge.target]));
  if (selection.type !== "edge") ids.add(selected.id);
  return {
    selection: { type: selection.type === "edge" ? "edge" : "node", record: selected },
    nodes: nodes.filter((node) => ids.has(node.id)), relationships,
    limitations: {
      networkTruncated: Boolean(network?.truncated), connectionsOmitted: connected.length > relationships.length,
      scope: "Selected record and at most 25 immediate connections. Graph steps do not prove personal association. Evidence and review status may be missing; recorded claims are not automatically verified.",
    },
  };
}
