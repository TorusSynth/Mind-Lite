import fs from "node:fs";
import path from "node:path";
import process from "node:process";

const mainPath = path.resolve(process.cwd(), "src/main.ts");

if (!fs.existsSync(mainPath)) {
  throw new Error(`Expected file to exist: ${mainPath}`);
}

console.log("Smoke test passed");
