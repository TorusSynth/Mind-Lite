const fs = require("node:fs");
const path = require("node:path");

const mainPath = path.resolve(process.cwd(), "main.js");

if (!fs.existsSync(mainPath)) {
  throw new Error(`Expected built plugin entrypoint to exist: ${mainPath}`);
}

const builtContents = fs.readFileSync(mainPath, "utf8");
const hasCjsSignal = builtContents.includes("module.exports") || builtContents.includes("exports.");

if (!hasCjsSignal) {
  throw new Error("Expected built main.js to contain CommonJS export markers");
}

console.log("Smoke test passed");
