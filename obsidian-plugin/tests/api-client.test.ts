const assert = require("node:assert/strict");
const path = require("node:path");

const clientPath = path.resolve(process.cwd(), "dist/api/client.js");
const { APIError, apiGet, apiPost } = require(clientPath);

async function run() {
  const originalFetch = globalThis.fetch;

  try {
    globalThis.fetch = async (url, init) => {
      assert.equal(url, "http://localhost:8000/health");
      assert.equal(init?.method, "GET");
      return {
        ok: true,
        status: 200,
        json: async () => ({ status: "ok" })
      };
    };

    const health = await apiGet("/health");
    assert.deepEqual(health, { status: "ok" });

    globalThis.fetch = async (url, init) => {
      assert.equal(url, "http://localhost:8000/ask");
      assert.equal(init?.method, "POST");
      assert.equal(init?.headers?.["Content-Type"], "application/json");
      assert.equal(init?.body, JSON.stringify({ query: "hello" }));
      return {
        ok: true,
        status: 200,
        json: async () => ({ answer: "hi" })
      };
    };

    const answer = await apiPost("/ask", { query: "hello" });
    assert.deepEqual(answer, { answer: "hi" });

    globalThis.fetch = async () => ({
      ok: false,
      status: 503,
      json: async () => ({ error: { message: "unavailable" } })
    });

    await assert.rejects(apiGet("/health"), (error) => {
      assert.ok(error instanceof APIError);
      assert.equal(error.status, 503);
      return true;
    });
  } finally {
    globalThis.fetch = originalFetch;
  }
}

run().then(() => {
  console.log("API client test passed");
});
