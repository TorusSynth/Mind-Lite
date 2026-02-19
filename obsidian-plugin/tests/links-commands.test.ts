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
          constructor() {}
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
    globalThis.fetch = async (url, init) => {
      const body = init?.body == null ? undefined : JSON.parse(init.body);
      fetchCalls.push({ url, method: init?.method, body });

      if (url.endsWith("/links/propose")) {
        return {
          ok: true,
          status: 200,
          json: async () => ([
            { source: "delta", target: "epsilon", confidence: 0.33 },
            { source: "alpha", target: "beta", confidence: 0.95 },
            { source: "alpha", target: "gamma", confidence: 0.72 }
          ])
        };
      }

      return {
        ok: true,
        status: 200,
        json: async () => ({})
      };
    };

    await plugin.commands.find((command) => command.id === "mind-lite-propose-links").callback();
    await new Promise((resolve) => setTimeout(resolve, 0));

    assert.deepEqual(fetchCalls[0], {
      url: "http://localhost:8000/links/propose",
      method: "POST",
      body: {}
    });

    const modal = openedModals.at(-1);
    assert.ok(modal);
    assert.deepEqual(collectTextsByTag(modal.contentEl, "li"), [
      "alpha -> beta (0.95)",
      "alpha -> gamma (0.72)",
      "delta -> epsilon (0.33)"
    ]);

    globalThis.prompt = () => "0.72";
    await plugin.commands.find((command) => command.id === "mind-lite-apply-links").callback();

    assert.deepEqual(fetchCalls[1], {
      url: "http://localhost:8000/links/apply",
      method: "POST",
      body: { minimum_confidence: 0.72 }
    });

    console.log("Links commands test passed");
  } finally {
    Module._load = originalLoad;
    globalThis.document = originalDocument;
    globalThis.fetch = originalFetch;
    globalThis.prompt = originalPrompt;
  }
}

run();
