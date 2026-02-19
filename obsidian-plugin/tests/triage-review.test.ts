const assert = require("node:assert/strict");
const Module = require("node:module");
const path = require("node:path");

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

function collectTexts(root, tagName) {
  const texts = [];

  if (root.tagName === tagName && typeof root.textContent === "string") {
    texts.push(root.textContent);
  }

  for (const child of root.children) {
    texts.push(...collectTexts(child, tagName));
  }

  return texts;
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

  const openedModals = [];
  const notices = [];

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
          this.app = {
            vault: { adapter: { basePath: "/vault" } },
            workspace: {
              getActiveFile() {
                return {
                  parent: { path: "projects" }
                };
              }
            }
          };
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
            notices.push(message);
          }
        }
      };
    }

    return originalLoad.call(this, request, parent, isMain);
  };

  globalThis.document = createDocument();

  try {
    const fetchCalls = [];
    globalThis.fetch = async (url, init) => {
      const method = init?.method ?? "GET";
      const body = init?.body == null ? undefined : JSON.parse(init.body);
      fetchCalls.push({ url, method, body });

      if (url.endsWith("/onboarding/analyze-folder")) {
        return {
          ok: true,
          status: 200,
          json: async () => ({
            run_id: "run-triage-1",
            state: "awaiting_review",
            proposal_counts: {
              safe_auto: 3,
              needs_review: 2
            }
          })
        };
      }

      if (url.endsWith("/runs")) {
        return {
          ok: true,
          status: 200,
          json: async () => ([
            { run_id: "run-1", state: "awaiting_review" },
            { run_id: "run-2", state: "ready_safe_auto" },
            { run_id: "run-3", state: "awaiting_review" }
          ])
        };
      }

      return {
        ok: true,
        status: 200,
        json: async () => ({})
      };
    };

    const mainModule = require(mainPath);
    const MindLitePlugin = mainModule.default;
    const plugin = new MindLitePlugin();
    await plugin.onload();

    const commandIds = plugin.commands.map((command) => command.id);
    assert.ok(commandIds.includes("mind-lite-daily-triage"));
    assert.ok(commandIds.includes("mind-lite-weekly-deep-review"));

    openedModals.length = 0;
    notices.length = 0;
    await plugin.commands.find((command) => command.id === "mind-lite-daily-triage").callback();

    assert.deepEqual(fetchCalls[0], {
      url: "http://localhost:8000/onboarding/analyze-folder",
      method: "POST",
      body: {
        folder_path: "projects",
        mode: "analyze"
      }
    });

    const triageModal = openedModals.at(-1);
    assert.ok(triageModal);
    assert.equal(triageModal.title, "Mind Lite: Analyze Run Status");
    assert.ok(notices.includes("Mind Lite daily triage complete: run-triage-1 (awaiting_review)"));

    await plugin.commands.find((command) => command.id === "mind-lite-weekly-deep-review").callback();
    await new Promise((resolve) => setTimeout(resolve, 0));

    assert.deepEqual(fetchCalls[1], {
      url: "http://localhost:8000/runs",
      method: "GET",
      body: undefined
    });

    const reviewModal = openedModals.at(-1);
    assert.ok(reviewModal);

    const buttonTexts = collectTexts(reviewModal.contentEl, "button");
    assert.ok(buttonTexts.includes("All (3)"));
    assert.ok(buttonTexts.includes("awaiting_review (2)"));
    assert.ok(buttonTexts.includes("ready_safe_auto (1)"));

    const runItemsBefore = collectTexts(reviewModal.contentEl, "li");
    assert.deepEqual(runItemsBefore, [
      "run-1 - awaiting_review",
      "run-2 - ready_safe_auto",
      "run-3 - awaiting_review"
    ]);

    const awaitingReviewButton = findButton(reviewModal.contentEl, "awaiting_review (2)");
    assert.ok(awaitingReviewButton);
    await awaitingReviewButton.onclick({});

    const runItemsAfter = collectTexts(reviewModal.contentEl, "li");
    assert.deepEqual(runItemsAfter, [
      "run-1 - awaiting_review",
      "run-3 - awaiting_review"
    ]);

    console.log("Daily triage and weekly review commands test passed");
  } finally {
    Module._load = originalLoad;
    globalThis.document = originalDocument;
    globalThis.fetch = originalFetch;
  }
}

run();
