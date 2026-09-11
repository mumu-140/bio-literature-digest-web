const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const ts = require("typescript");

function loadDiscussionModule() {
  const sourcePath = path.resolve(__dirname, "../src/features/digest/deerflowDiscussion.ts");
  const source = fs.readFileSync(sourcePath, "utf8");
  const compiled = ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2020,
    },
  }).outputText;
  const loaded = { exports: {} };
  new Function("module", "exports", compiled)(loaded, loaded.exports);
  return loaded.exports;
}

test("builds a stable multi-paper DeerFlow discussion URL", () => {
  const { buildDeerFlowDiscussionUrl } = loadDiscussionModule();
  const url = new URL(buildDeerFlowDiscussionUrl([
    "doi:10.1000/alpha",
    "url:https://example.org/paper",
    "doi:10.1000/alpha",
  ]));

  assert.equal(url.origin, "https://deerflow.muaiword.com");
  assert.equal(url.pathname, "/workspace/chats/new");
  assert.deepEqual(url.searchParams.getAll("literature_key"), [
    "doi:10.1000/alpha",
    "url:https://example.org/paper",
  ]);
});

test("requires between one and ten unique literature keys", () => {
  const { buildDeerFlowDiscussionUrl } = loadDiscussionModule();

  assert.throws(() => buildDeerFlowDiscussionUrl([]), /至少选择 1 篇/);
  assert.throws(
    () => buildDeerFlowDiscussionUrl(Array.from({ length: 11 }, (_, index) => `doi:10.1000/${index}`)),
    /最多选择 10 篇/,
  );
});

test("does not serialize paper content or credentials into the URL", () => {
  const { buildDeerFlowDiscussionUrl } = loadDiscussionModule();
  const url = buildDeerFlowDiscussionUrl(["doi:10.1000/safe-key"]);

  assert.doesNotMatch(url, /abstract|summary|token|authorization/i);
});
