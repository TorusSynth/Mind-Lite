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

function collectTextsByTag(root, tagName) {
  const texts = [];

  if (root.tagName === tagName && typeof root.textContent === "string") {
    texts.push(root.textContent);
  }

  for (const child of root.children) {
    texts.push(...collectTextsByTag(child, tagName));
  }

  return texts;
}

async function run() {
  const originalLoad = Module._load;
  const originalDocument = globalThis.document;
  const originalFetch = globalThis.fetch;
  const originalPrompt = globalThis.prompt;

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
            notices.push(message);
          }
        }
      };
    }

    return originalLoad.call(this, request, parent, isMain);
  };

  globalThis.document = createDocument();

  try {
    const mainModule = require(mainPath);
    const MindLitePlugin = mainModule.default;

    const plugin = new MindLitePlugin();
    await plugin.onload();

    const commandIds = plugin.commands.map((command) => command.id);
    assert.ok(commandIds.includes("mind-lite-propose-links"));
    assert.ok(commandIds.includes("mind-lite-apply-links"));

    const fetchCalls = [];
    const promptCalls = [];
    const promptResponses = ["source-note", "candidate-z, candidate-a, candidate-b", "0.72"];
    let failNextProposeRequest = false;
    globalThis.fetch = async (url, init) => {
      const body = init?.body == null ? undefined : JSON.parse(init.body);
      fetchCalls.push({ url, method: init?.method, body });

      if (url.endsWith("/links/propose")) {
        if (failNextProposeRequest) {
          failNextProposeRequest = false;
          return {
            ok: false,
            status: 500,
            json: async () => ({ message: "boom" })
          };
        }

        return {
          ok: true,
          status: 200,
          json: async () => ({
            source_note_id: "source-note",
            suggestions: [
              { target_note_id: "candidate-z", confidence: 0.33, reason: "weak_similarity" },
              { target_note_id: "candidate-a", confidence: 0.95, reason: "shared_project_context" },
              { target_note_id: "candidate-b", confidence: 0.72, reason: "semantic_similarity" }
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

    globalThis.prompt = (message) => {
      promptCalls.push(message);
      return promptResponses.shift() ?? null;
    };

    await plugin.commands.find((command) => command.id === "mind-lite-propose-links").callback();
    await new Promise((resolve) => setTimeout(resolve, 0));

    assert.deepEqual(fetchCalls[0], {
      url: "http://localhost:8000/links/propose",
      method: "POST",
      body: {
        source_note_id: "source-note",
        candidate_notes: [
          { note_id: "candidate-z" },
          { note_id: "candidate-a" },
          { note_id: "candidate-b" }
        ]
      }
    });

    const modal = openedModals.at(-1);
    assert.ok(modal);
    assert.deepEqual(collectTextsByTag(modal.contentEl, "li"), [
      "candidate-a (0.95) - shared_project_context",
      "candidate-b (0.72) - semantic_similarity",
      "candidate-z (0.33) - weak_similarity"
    ]);

    await plugin.commands.find((command) => command.id === "mind-lite-apply-links").callback();

    assert.deepEqual(fetchCalls[1], {
      url: "http://localhost:8000/links/apply",
      method: "POST",
      body: {
        source_note_id: "source-note",
        links: [
          { target_note_id: "candidate-a", confidence: 0.95 },
          { target_note_id: "candidate-b", confidence: 0.72 },
          { target_note_id: "candidate-z", confidence: 0.33 }
        ],
        min_confidence: 0.72
      }
    });

    assert.deepEqual(promptCalls, [
      "Source note id",
      "Candidate note ids (comma-separated)",
      "Minimum confidence (0-1, optional)"
    ]);

    promptResponses.push(null);
    await plugin.commands.find((command) => command.id === "mind-lite-propose-links").callback();

    const fetchCountAfterCancelledPropose = fetchCalls.length;
    const promptCountAfterCancelledPropose = promptCalls.length;

    await plugin.commands.find((command) => command.id === "mind-lite-apply-links").callback();

    assert.equal(fetchCalls.length, fetchCountAfterCancelledPropose);
    assert.equal(promptCalls.length, promptCountAfterCancelledPropose);

    promptResponses.push("source-note", "candidate-z, candidate-a");
    failNextProposeRequest = true;
    await plugin.commands.find((command) => command.id === "mind-lite-propose-links").callback();

    const fetchCountAfterFailedPropose = fetchCalls.length;
    const promptCountAfterFailedPropose = promptCalls.length;

    await plugin.commands.find((command) => command.id === "mind-lite-apply-links").callback();

    assert.equal(fetchCalls.length, fetchCountAfterFailedPropose);
    assert.equal(promptCalls.length, promptCountAfterFailedPropose);

    const noCacheNotice = "No fresh link suggestions available. Run Propose Links first.";
    assert.equal(notices.filter((message) => message === noCacheNotice).length, 2);

    console.log("Links commands test passed");
  } finally {
    Module._load = originalLoad;
    globalThis.document = originalDocument;
    globalThis.fetch = originalFetch;
    globalThis.prompt = originalPrompt;
  }
}

run();
