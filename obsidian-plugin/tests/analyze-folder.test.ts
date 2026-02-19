const assert = require("node:assert/strict");
const Module = require("node:module");
const path = require("node:path");

const clientPath = path.resolve(process.cwd(), "dist/api/client.js");
const featurePath = path.resolve(process.cwd(), "dist/features/onboarding/analyze-folder.js");

const client = require(clientPath);

const originalLoad = Module._load;
Module._load = function patchedLoad(request, parent, isMain) {
  if (request === "obsidian") {
    return {
      Modal: class Modal {},
      App: class App {},
      Plugin: class Plugin {}
    };
  }

  return originalLoad.call(this, request, parent, isMain);
};

const { analyzeFolder } = require(featurePath);
Module._load = originalLoad;

async function run() {
  const originalApiPost = client.apiPost;
  let calledWith = null;

  client.apiPost = async (requestPath, payload) => {
    calledWith = { requestPath, payload };
    return {
      run_id: "run-123",
      state: "awaiting_review",
      proposal_counts: {
        auto: 1,
        manual: 2
      }
    };
  };

  try {
    const result = await analyzeFolder("/tmp/vault");

    assert.deepEqual(calledWith, {
      requestPath: "/onboarding/analyze-folder",
      payload: {
        folder_path: "/tmp/vault",
        mode: "analyze"
      }
    });

    assert.equal(result.run_id, "run-123");
    assert.equal(result.state, "awaiting_review");
    assert.deepEqual(result.proposal_counts, {
      auto: 1,
      manual: 2
    });
  } finally {
    client.apiPost = originalApiPost;
  }

  console.log("Analyze folder feature test passed");
}

run();
