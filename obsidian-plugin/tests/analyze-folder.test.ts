const assert = require("node:assert/strict");
const Module = require("node:module");
const path = require("node:path");

const clientPath = path.resolve(process.cwd(), "dist/api/client.js");
const featurePath = path.resolve(process.cwd(), "dist/features/onboarding/analyze-folder.js");

const client = require(clientPath);

const noticeMessages = [];
const analyzeModalInstances = [];

class FakeAnalyzeModal {
  constructor(app, defaultFolderPath, runAnalyze, onAnalyzeSuccess) {
    this.app = app;
    this.defaultFolderPath = defaultFolderPath;
    this.runAnalyze = runAnalyze;
    this.onAnalyzeSuccess = onAnalyzeSuccess;
    this.opened = false;
    analyzeModalInstances.push(this);
  }

  open() {
    this.opened = true;
  }
}

const originalLoad = Module._load;
Module._load = function patchedLoad(request, parent, isMain) {
  if (request === "obsidian") {
    return {
      Modal: class Modal {},
      App: class App {},
      Plugin: class Plugin {},
      Notice: class Notice {
        constructor(message) {
          noticeMessages.push(message);
        }
      }
    };
  }

  if (request === "./modals/AnalyzeModal") {
    return {
      AnalyzeModal: FakeAnalyzeModal
    };
  }

  if (request === "./modals/RunStatusModal") {
    return {
      RunStatusModal: class RunStatusModal {
        open() {}
      }
    };
  }

  return originalLoad.call(this, request, parent, isMain);
};

const { analyzeFolder, registerAnalyzeFolderCommand } = require(featurePath);
Module._load = originalLoad;

function createPlugin(basePath) {
  return {
    app: {
      vault: {
        adapter: {
          basePath
        }
      }
    },
    addCommand(command) {
      this.command = command;
    }
  };
}

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

  noticeMessages.length = 0;
  analyzeModalInstances.length = 0;

  const pluginWithBasePath = createPlugin(" /tmp/vault-root ");
  registerAnalyzeFolderCommand(pluginWithBasePath);
  pluginWithBasePath.command.callback();

  assert.equal(analyzeModalInstances.length, 1);
  assert.equal(analyzeModalInstances[0].defaultFolderPath, "/tmp/vault-root");
  assert.equal(analyzeModalInstances[0].opened, true);
  assert.deepEqual(noticeMessages, []);

  noticeMessages.length = 0;
  analyzeModalInstances.length = 0;

  const pluginWithoutBasePath = createPlugin(undefined);
  registerAnalyzeFolderCommand(pluginWithoutBasePath);
  pluginWithoutBasePath.command.callback();

  assert.equal(analyzeModalInstances.length, 1);
  assert.equal(analyzeModalInstances[0].defaultFolderPath, "");
  assert.equal(analyzeModalInstances[0].opened, true);
  assert.deepEqual(noticeMessages, [
    "Mind Lite could not detect your vault path. Enter a folder path to continue."
  ]);

  console.log("Analyze folder feature test passed");
}

run();
