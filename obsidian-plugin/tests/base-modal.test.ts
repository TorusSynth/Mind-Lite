const assert = require("node:assert/strict");
const path = require("node:path");

const modalPath = path.resolve(process.cwd(), "dist/modals/base.js");
const { createErrorText } = require(modalPath);

function run() {
  assert.equal(createErrorText("Network unavailable"), "Network unavailable");
  assert.equal(createErrorText(new Error("Request failed")), "Request failed");
  assert.equal(createErrorText({ message: "Server unavailable" }), "Server unavailable");
  assert.equal(createErrorText({}), "Something went wrong. Please try again.");
  assert.equal(createErrorText("   "), "Something went wrong. Please try again.");

  console.log("Base modal utility test passed");
}

run();
