import test from 'node:test';
import assert from 'node:assert/strict';
import { fetchNetwork, NETWORK_PATH_LIMIT, serializeNetwork } from './network.js';

const node = (id) => ({ elementId: id, labels: ['Person'], properties: { person_id: id, name: id } });
const [a, b, c] = ['a', 'b', 'c'].map(node);
const segment = (start, end, id, reverse = false) => ({ start, end, relationship: { elementId: id, startNodeElementId: (reverse ? end : start).elementId, endNodeElementId: (reverse ? start : end).elementId, type: 'SEEN_WITH', properties: { source: 'synthetic_demo' } } });
test('deduplicates paths, keeps minimum hop distance and original edge direction', () => {
  const graph = serializeNetwork([
    { path: { start: a, segments: [segment(a, b, 'ab'), segment(b, c, 'cb', true)] } },
    { path: { start: a, segments: [segment(a, c, 'ac')] } },
    { path: { start: a, segments: [segment(a, b, 'ab')] } },
  ]);
  assert.equal(graph.nodes.length, 3);
  assert.equal(graph.edges.length, 3);
  assert.equal(graph.nodes.find(n => n.id === 'c').depth, 1);
  assert.equal(graph.edges.find(e => e.id === 'cb').source, 'c');
  assert.equal(graph.edges[0].provenance, 'synthetic_demo');
});
test('keeps isolated root nodes and handles an empty result', () => {
  assert.deepEqual(serializeNetwork([]), { nodes: [], edges: [] });
  const graph = serializeNetwork([{ path: { start: a, segments: [] } }]);
  assert.equal(graph.nodes[0].depth, 0);
  assert.equal(graph.edges.length, 0);
});

test('preserves parallel relationships, record types, and synthetic provenance', () => {
  const vehicle = { elementId: 'vehicle', labels: ['Vehicle'], properties: { registration: 'TEST-001', source: 'synthetic_demo' } };
  const graph = serializeNetwork([
    { path: { start: a, segments: [segment(a, b, 'ab1')] } },
    { path: { start: a, segments: [segment(a, b, 'ab2')] } },
    { path: { start: a, segments: [segment(a, vehicle, 'av')] } },
  ]);
  assert.equal(graph.edges.length, 3);
  const record = graph.nodes.find(n => n.id === 'vehicle');
  assert.equal(record.kind, 'Vehicle');
  assert.equal(record.label, 'TEST-001');
  assert.equal(record.personId, null);
  assert.equal(record.provenance, 'synthetic_demo');
  for (const edge of graph.edges) {
    assert.ok(graph.nodes.some(n => n.id === edge.source));
    assert.ok(graph.nodes.some(n => n.id === edge.target));
  }
});

test('returns null for missing Neo4j people and propagates database failures', async () => {
  assert.equal(await fetchNetwork('missing', async () => []), null);
  await assert.rejects(fetchNetwork('a', async () => { throw new Error('offline'); }), /offline/);
});

test('binds the selected ID and reports truncation only when extra paths exist', async () => {
  const rootPath = { path: { start: a, segments: [] } };
  const paths = [rootPath, ...Array.from({ length: NETWORK_PATH_LIMIT - 1 }, (_, index) => ({
    path: { start: a, segments: [segment(a, node(`person-${index}`), `edge-${index}`)] },
  }))];
  const graph = await fetchNetwork("a' injected", async (_query, params) => {
    assert.deepEqual(params, { id: "a' injected" });
    return paths;
  });
  assert.equal(graph.truncated, false);
  const overflow = { path: { start: a, segments: [segment(a, node('overflow'), 'extra')] } };
  const capped = await fetchNetwork('a', async () => [...paths, overflow]);
  assert.equal(capped.truncated, true);
  assert.equal(capped.pathLimit, NETWORK_PATH_LIMIT);
  assert.equal(capped.nodes.some(n => n.id === 'overflow'), false);
});
