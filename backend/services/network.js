export const NETWORK_PATH_LIMIT = 1000;

// Include the root even when it has no relationships. Search both directions;
// ordering shortest paths first keeps hop distances correct when capped.
// Crime types describe cases but must not bridge otherwise unrelated cases.
// Exclude them from every position except the final node in a path.
export const NETWORK_QUERY = `
  MATCH path = (root:Person {person_id: $id})-[*0..4]-(connected)
  WHERE none(node IN nodes(path)[0..-1] WHERE node:CrimeType)
  RETURN path
  ORDER BY length(path), elementId(connected)
  LIMIT ${NETWORK_PATH_LIMIT + 1}
`;

export async function fetchNetwork(id, runCypher) {
  const records = await runCypher(NETWORK_QUERY, { id });
  if (records.length === 0) return null;
  return {
    ...serializeNetwork(records.slice(0, NETWORK_PATH_LIMIT)),
    truncated: records.length > NETWORK_PATH_LIMIT,
    pathLimit: NETWORK_PATH_LIMIT,
  };
}

// Preserve Neo4j element IDs so parallel relationships and node types stay distinct.
export function serializeNetwork(records) {
  const nodes = new Map();
  const edges = new Map();
  for (const { path } of records) {
    const addNode = (node, depth) => {
      const existing = nodes.get(node.elementId);
      if (existing) { existing.depth = Math.min(existing.depth, depth); return; }
      const p = node.properties;
      const name = p.name || p.city || p.crime_name || p.registration || p.case_id || p.person_id || node.labels[0];
      nodes.set(node.elementId, {
        id: node.elementId, kind: node.labels[0] || 'Record', depth,
        label: name, displayLabel: p.name ? `${name}\n${p.alias ? `“${p.alias}”` : p.person_id || ''}` : name,
        personId: p.person_id == null ? null : String(p.person_id), alias: p.alias || null, city: p.city || null,
        provenance: p.source || null,
      });
    };
    addNode(path.start, 0);
    path.segments.forEach((segment, index) => {
      addNode(segment.end, index + 1);
      const r = segment.relationship;
      edges.set(r.elementId, {
        id: r.elementId, source: r.startNodeElementId, target: r.endNodeElementId,
        label: r.type.replaceAll('_', ' '), provenance: r.properties.source || null,
        reason: r.properties.reason || null,
      });
    });
  }
  return { nodes: [...nodes.values()], edges: [...edges.values()] };
}
