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
    const fetchCalls = [];
    globalThis.fetch = async (url, init) => {
      const body = init?.body == null ? undefined : JSON.parse(init.body);
      fetchCalls.push({ url, method: init?.method, body });

      if (url.endsWith("/publish/prepare")) {
        return {
          ok: true,
          status: 200,
          json: async () => ({
            draft_id: body.draft_id,
            target: body.target,
            prepared_content: body.content,
            sanitized: true
          })
        };
      }

      if (url.endsWith("/publish/score")) {
        if (body.draft_id === "draft-fail") {
          return {
            ok: true,
            status: 200,
            json: async () => ({
              draft_id: body.draft_id,
              scores: { overall: 0.45 },
              gate_passed: false
            })
          };
        }

        return {
          ok: true,
          status: 200,
          json: async () => ({
            draft_id: body.draft_id,
            scores: { overall: 0.92 },
            gate_passed: true
          })
        };
      }

      if (url.endsWith("/publish/mark-for-gom")) {
        return {
          ok: true,
          status: 200,
          json: async () => ({
            draft_id: body.draft_id,
            status: "queued_for_gom"
          })
        };
      }

      return {
        ok: true,
        status: 200,
        json: async () => ({})
      };
    };

    const promptCalls = [];
    const promptResponses = [
      "draft-pass",
      "# Weekly Update\n\nConcrete outcomes and next steps.",
      "gom",
      "draft-fail",
      "todo",
      "gom"
    ];
    globalThis.prompt = (message) => {
      promptCalls.push(message);
      return promptResponses.shift() ?? null;
    };

    const mainModule = require(mainPath);
    const MindLitePlugin = mainModule.default;
    const plugin = new MindLitePlugin();
    await plugin.onload();

    const commandIds = plugin.commands.map((command) => command.id);
    assert.ok(commandIds.includes("mind-lite-publish-to-gom"));

    await plugin.commands.find((command) => command.id === "mind-lite-publish-to-gom").callback();
    const prepareModal = openedModals.at(-1);
    assert.ok(prepareModal);
    assert.equal(prepareModal.title, "Mind Lite: Publish Prepare");

    const continueButton = findButton(prepareModal.contentEl, "Continue");
    assert.ok(continueButton);
    await continueButton.onclick({});
    await new Promise((resolve) => setTimeout(resolve, 0));

    const gatePassModal = openedModals.at(-1);
    assert.ok(gatePassModal);
    assert.equal(gatePassModal.title, "Mind Lite: GOM Gate Results");
    assert.deepEqual(collectTextsByTag(gatePassModal.contentEl, "li"), [
      "prepare: ok - target=gom, sanitized=yes",
      "score: ok - overall=0.92, gate_passed=true",
      "mark-for-gom: ok - queued_for_gom"
    ]);

    await plugin.commands.find((command) => command.id === "mind-lite-publish-to-gom").callback();
    const secondPrepareModal = openedModals.at(-1);
    const secondContinueButton = findButton(secondPrepareModal.contentEl, "Continue");
    assert.ok(secondContinueButton);
    await secondContinueButton.onclick({});
    await new Promise((resolve) => setTimeout(resolve, 0));

    const gateFailModal = openedModals.at(-1);
    assert.ok(gateFailModal);
    assert.deepEqual(collectTextsByTag(gateFailModal.contentEl, "li"), [
      "prepare: ok - target=gom, sanitized=yes",
      "score: ok - overall=0.45, gate_passed=false",
      "mark-for-gom: failed - Skipped because gate did not pass"
    ]);

    assert.deepEqual(fetchCalls[0], {
      url: "http://localhost:8000/publish/prepare",
      method: "POST",
      body: {
        draft_id: "draft-pass",
        content: "# Weekly Update\n\nConcrete outcomes and next steps.",
        target: "gom"
      }
    });
    assert.deepEqual(fetchCalls[1], {
      url: "http://localhost:8000/publish/score",
      method: "POST",
      body: {
        draft_id: "draft-pass",
        content: "# Weekly Update\n\nConcrete outcomes and next steps."
      }
    });
    assert.deepEqual(fetchCalls[2], {
      url: "http://localhost:8000/publish/mark-for-gom",
      method: "POST",
      body: {
        draft_id: "draft-pass",
        title: "Weekly Update",
        prepared_content: "# Weekly Update\n\nConcrete outcomes and next steps."
      }
    });

    assert.deepEqual(fetchCalls[3], {
      url: "http://localhost:8000/publish/prepare",
      method: "POST",
      body: {
        draft_id: "draft-fail",
        content: "todo",
        target: "gom"
      }
    });
    assert.deepEqual(fetchCalls[4], {
      url: "http://localhost:8000/publish/score",
      method: "POST",
      body: {
        draft_id: "draft-fail",
        content: "todo"
      }
    });

    assert.equal(fetchCalls.length, 5);
    assert.equal(notices.length, 0);
    assert.deepEqual(promptCalls, [
      "Draft id",
      "Content",
      "Target",
      "Draft id",
      "Content",
      "Target"
    ]);

    console.log("GOM publish flow command test passed");
  } finally {
    Module._load = originalLoad;
    globalThis.document = originalDocument;
    globalThis.fetch = originalFetch;
    globalThis.prompt = originalPrompt;
  }
}

run();
