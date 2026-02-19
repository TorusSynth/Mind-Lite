const assert = require("node:assert/strict");
const Module = require("node:module");
const path = require("node:path");

const mainPath = path.resolve(process.cwd(), "dist/main.js");

const REQUIRED_COMMAND_IDS = [
  "mind-lite-analyze-folder",
  "mind-lite-review-proposals",
  "mind-lite-apply-approved",
  "mind-lite-rollback-last-batch",
  "mind-lite-daily-triage",
  "mind-lite-weekly-deep-review",
  "mind-lite-propose-links",
  "mind-lite-apply-links",
  "mind-lite-publish-to-gom"
];

async function run() {
  const originalLoad = Module._load;

  Module._load = function patchedLoad(request, parent, isMain) {
    if (request === "obsidian") {
      class Plugin {
        constructor() {
          this.app = {
            vault: { adapter: {} },
            workspace: { getActiveFile: () => null }
          };
          this.commands = [];
        }

        addCommand(command) {
          this.commands.push(command);
        }
      }

      return {
        Modal: class Modal {},
        App: class App {},
        Plugin,
        Notice: class Notice {}
      };
    }

    return originalLoad.call(this, request, parent, isMain);
  };

  try {
    const mainModule = require(mainPath);
    const MindLitePlugin = mainModule.default;
    const plugin = new MindLitePlugin();
    await plugin.onload();

    const registeredIds = new Set(plugin.commands.map((command) => command.id));

    for (const commandId of REQUIRED_COMMAND_IDS) {
      assert.ok(registeredIds.has(commandId), `Expected command to be registered: ${commandId}`);
    }

    console.log("Commands smoke test passed");
  } finally {
    Module._load = originalLoad;
  }
}

run();
