import test from 'node:test';
import assert from 'node:assert/strict';
import { buildInsightContext, validateSelection } from './insight.js';
import { explainNetwork } from './groq.js';

const edge = { id: 'e1', source: 'n1', target: 'n2', label: 'KNOWS', evidence: 'Source statement', reviewStatus: 'pending' };
const network = { nodes: [{ id: 'n1', personId: 'P1' }, { id: 'n2' }, { id: 'unrelated' }], edges: [edge] };

test('requires a valid selection and rejects records outside the network', () => {
  for (const selection of [null, {}, { type: 'node', id: 1 }, { type: 'invalid', id: 'n1' }]) {
    assert.throws(() => validateSelection(selection), { status: 400 });
  }
  assert.throws(() => buildInsightContext(network, { type: 'edge', id: 'missing' }), { status: 404 });
});

test('relationship insight sends server evidence and only its endpoints to the provider', async () => {
  const insightContext = buildInsightContext(network, { type: 'edge', id: 'e1', evidence: 'fabricated' });
  assert.deepEqual(insightContext.selection.record, edge);
  assert.deepEqual(insightContext.nodes.map((node) => node.id), ['n1', 'n2']);
  await explainNetwork({}, { apiKey: 'test', insightContext, fetchImpl: async (_, options) => {
    const body = JSON.parse(options.body);
    assert.deepEqual(JSON.parse(body.messages[1].content), insightContext);
    assert.match(body.messages[0].content, /investigative analyst/);
    return { ok: true, json: async () => ({ choices: [{ message: { content: 'Insight' } }] }) };
  } });
});

test('node insights resolve map person IDs and report omitted connections', () => {
  const many = { ...network, truncated: true, edges: Array.from({ length: 30 }, (_, i) => ({ ...edge, id: `e${i}` })) };
  const context = buildInsightContext(many, { type: 'person', id: 'P1' });
  assert.equal(context.selection.record.id, 'n1');
  assert.equal(context.relationships.length, 25);
  assert.equal(context.limitations.connectionsOmitted, true);
  assert.equal(context.limitations.networkTruncated, true);
});
