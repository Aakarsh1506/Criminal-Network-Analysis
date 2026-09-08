import test from "node:test";
import assert from "node:assert/strict";
import { explainNetwork } from "./groq.js";

const profile = {
  criminal: { id: "P1", name: "Example", photo: "private-photo", dob: "private-dob", cases: [{ caseId: "C1", status: "Pending" }] },
  relations: [{ criminal: { id: "P2", name: "Other", photo: "private-photo" }, type: "Shared Location: Delhi" }],
};
const response = (content, finish_reason = "stop") => ({ ok: true, json: async () => ({ choices: [{ message: { content }, finish_reason }] }) });

test("uses server records, excludes demographics, and returns text", async () => {
  const result = await explainNetwork(profile, { apiKey: "test-key", fetchImpl: async (url, options) => {
    assert.equal(url, "https://api.groq.com/openai/v1/chat/completions");
    assert.equal(options.headers.Authorization, "Bearer test-key");
    const body = JSON.parse(options.body);
    assert.ok(body.messages[1].content.includes("C1"));
    assert.ok(!body.messages[1].content.includes("private-photo"));
    assert.ok(!body.messages[1].content.includes("private-dob"));
    assert.ok(options.signal instanceof AbortSignal);
    return response(" Summary ");
  } });
  assert.equal(result, "Summary");
});

test("missing key never calls provider", async () => {
  await assert.rejects(explainNetwork(profile, { apiKey: "", fetchImpl: () => assert.fail("must not call") }), { status: 503 });
});

for (const [upstream, expected] of [[401, 503], [403, 503], [429, 429], [500, 502]]) {
  test(`handles provider ${upstream} without leaking response`, async () => {
    await assert.rejects(explainNetwork(profile, { apiKey: "test", fetchImpl: async () => ({ ok: false, status: upstream }) }), { status: expected });
  });
}
for (const [name, expected] of [["TimeoutError", 504], ["TypeError", 502]]) {
  test(`handles ${name}`, async () => {
    await assert.rejects(explainNetwork(profile, { apiKey: "test", fetchImpl: async () => { throw Object.assign(new Error("secret"), { name }); } }), (err) => err.status === expected && !err.message.includes("secret"));
  });
}
for (const [content, reason] of [["", "stop"], [null, "stop"], ["partial", "length"]]) {
  test(`rejects unusable response ${content}/${reason}`, async () => {
    await assert.rejects(explainNetwork(profile, { apiKey: "test", fetchImpl: async () => response(content, reason) }), { status: 502 });
  });
}

test("unavailable model produces an actionable configuration error", async () => {
  await assert.rejects(explainNetwork(profile, {
    apiKey: "test",
    fetchImpl: async () => ({ ok: false, status: 404, json: async () => ({ error: { code: "model_not_found", message: "private provider details" } }) }),
  }), (err) => err.status === 503 && err.message.includes("GROQ_MODEL") && !err.message.includes("private provider details"));
});
