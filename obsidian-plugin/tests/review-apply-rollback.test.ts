const assert = require("node:assert/strict");
const Module = require("node:module");
const path = require("node:path");

const historyPath = path.resolve(process.cwd(), "dist/features/runs/history.js");
const mainPath = path.resolve(process.cwd(), "dist/main.js");

class FakeClassList {
  constructor() {
    this.values = new Set();
  }

  add(...tokens) {
    for (const token of tokens) {
      this.values.add(token);
    }
  }

  remove(...tokens) {
    for (const token of tokens) {
      this.values.delete(token);
    }
  }

  toggle(token, force) {
    if (force === true) {
      this.values.add(token);
      return true;
    }

    if (force === false) {
      this.values.delete(token);
      return false;
    }

    if (this.values.has(token)) {
      this.values.delete(token);
      return false;
    }

    this.values.add(token);
    return true;
  }
}

class FakeElement {
  constructor(tagName) {
    this.tagName = tagName;
    this.children = [];
    this.classList = new FakeClassList();
    this.textContent = "";
    this.type = "";
    this.value = "";
    this.placeholder = "";
    this.onclick = null;
  }

  appendChild(child) {
    this.children.push(child);
    return child;
  }

  append(...elements) {
    for (const element of elements) {
      this.appendChild(element);
    }
  }

  empty() {
    this.children = [];
    this.textContent = "";
  }
}

function createDocument() {
  return {
    createElement(tagName) {
      return new FakeElement(tagName);
    }
  };
}

function findByText(root, text) {
  if (root.textContent === text) {
    return root;
  }

  for (const child of root.children) {
    const found = findByText(child, text);
    if (found != null) {
      return found;
    }
  }

  return null;
}

function findButton(root, label) {
  if (root.tagName === "button" && root.textContent === label) {
    return root;
  }

  for (const child of root.children) {
    const found = findButton(child, label);
    if (found != null) {
      return found;
    }
  }

  return null;
}

async function run() {
  const originalLoad = Module._load;
  const originalDocument = globalThis.document;
  const originalFetch = globalThis.fetch;

  const noticeMessages = [];
  const openedModals = [];

  Module._load = function patchedLoad(request, parent, isMain) {
    if (request === "obsidian") {
      class Modal {
        constructor(app) {
          this.app = app;
          this.contentEl = new FakeElement("div");
          this.title = "";
        }

        setTitle(title) {
          this.title = title;
        }

        open() {
          openedModals.push(this);
          if (typeof this.onOpen === "function") {
            this.onOpen();
          }
        }

        close() {}
      }

      class Plugin {
        constructor() {
          this.app = { vault: { adapter: {} } };
          this.commands = [];
        }

        addCommand(command) {
          this.commands.push(command);
        }
      }

      return {
        Modal,
        App: class App {},
        Plugin,
        Notice: class Notice {
          constructor(message) {
            noticeMessages.push(message);
          }
        }
      };
    }

    return originalLoad.call(this, request, parent, isMain);
  };

  globalThis.document = createDocument();

  try {
    const { setLastRunId, getLastRunId, clearLastRunId } = require(historyPath);
    const mainModule = require(mainPath);
    const MindLitePlugin = mainModule.default;

    const plugin = new MindLitePlugin();
    await plugin.onload();

    const commandIds = plugin.commands.map((command) => command.id);
    assert.ok(commandIds.includes("mind-lite-review-proposals"));
    assert.ok(commandIds.includes("mind-lite-apply-approved"));
    assert.ok(commandIds.includes("mind-lite-rollback-last-batch"));

    clearLastRunId();
    setLastRunId({ bad: true });
    assert.equal(getLastRunId(), null);
    noticeMessages.length = 0;
    await plugin.commands.find((command) => command.id === "mind-lite-review-proposals").callback();
    assert.deepEqual(noticeMessages, ["Mind Lite has no recent run to review."]);

    setLastRunId("run-42");
    let fetchCalls = [];

    globalThis.fetch = async (url, init) => {
      fetchCalls.push({ url, method: init?.method });

      if (url.endsWith("/proposals")) {
        return {
          ok: true,
          status: 200,
          json: async () => ({
            proposals: [
              { proposal_id: "p1", status: "approved", risk_tier: "high" },
              { proposal_id: "p2", status: "approved", risk_tier: "high" },
              { proposal_id: "p3", status: "queued", risk_tier: "low" }
            ]
          })
        };
      }

      return {
        ok: true,
        status: 200,
        json: async () => ({})
      };
    };

    openedModals.length = 0;
    await plugin.commands.find((command) => command.id === "mind-lite-review-proposals").callback();
    await new Promise((resolve) => setTimeout(resolve, 0));

    assert.deepEqual(fetchCalls[0], {
      url: "http://localhost:8000/runs/run-42/proposals",
      method: "GET"
    });

    const reviewModal = openedModals.at(-1);
    assert.ok(reviewModal);
    assert.ok(findByText(reviewModal.contentEl, "approved / high (2)"));
    assert.ok(findByText(reviewModal.contentEl, "queued / low (1)"));

    fetchCalls = [];
    await plugin.commands.find((command) => command.id === "mind-lite-apply-approved").callback();
    assert.deepEqual(fetchCalls[0], {
      url: "http://localhost:8000/runs/run-42/approve",
      method: "POST"
    });
    assert.deepEqual(fetchCalls[1], {
      url: "http://localhost:8000/runs/run-42/apply",
      method: "POST"
    });

    fetchCalls = [];
    noticeMessages.length = 0;
    globalThis.fetch = async (url, init) => {
      fetchCalls.push({ url, method: init?.method });

      if (url.endsWith("/apply")) {
        return {
          ok: false,
          status: 500,
          json: async () => ({})
        };
      }

      return {
        ok: true,
        status: 200,
        json: async () => ({})
      };
    };

    await plugin.commands.find((command) => command.id === "mind-lite-apply-approved").callback();
    assert.deepEqual(fetchCalls[0], {
      url: "http://localhost:8000/runs/run-42/approve",
      method: "POST"
    });
    assert.deepEqual(fetchCalls[1], {
      url: "http://localhost:8000/runs/run-42/apply",
      method: "POST"
    });
    assert.deepEqual(noticeMessages, ["API request failed with status 500"]);

    fetchCalls = [];
    openedModals.length = 0;
    await plugin.commands.find((command) => command.id === "mind-lite-rollback-last-batch").callback();

    const rollbackModal = openedModals.at(-1);
    const rollbackButton = findButton(rollbackModal.contentEl, "Rollback");
    assert.ok(rollbackButton);
    await rollbackButton.onclick({});

    assert.deepEqual(fetchCalls[0], {
      url: "http://localhost:8000/runs/run-42/rollback",
      method: "POST"
    });

    console.log("Review/apply/rollback workflow test passed");
  } finally {
    Module._load = originalLoad;
    globalThis.document = originalDocument;
    globalThis.fetch = originalFetch;
  }
}

run();
