const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const ts = require("typescript");

function loadModule(relativePath) {
  const sourcePath = path.resolve(__dirname, relativePath);
  const source = fs.readFileSync(sourcePath, "utf8");
  const compiled = ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2020,
    },
  }).outputText;
  const loaded = { exports: {} };
  new Function("module", "exports", "require", compiled)(loaded, loaded.exports, (mod) => {
    if (mod.startsWith("./") || mod.startsWith("../")) {
      const resolved = path.resolve(path.dirname(sourcePath), mod);
      return loadModule(path.relative(__dirname, resolved.endsWith(".ts") ? resolved : resolved + ".ts"));
    }
    return require(mod);
  });
  return loaded.exports;
}

test("LRUCache manages capacity and evicts oldest items first", () => {
  const { LRUCache } = loadModule("../src/features/digest/cache/lruCache.ts");
  const cache = new LRUCache({ maxSize: 3, ttlMs: 60000 });

  cache.set("a", 1);
  cache.set("b", 2);
  cache.set("c", 3);

  assert.equal(cache.get("a"), 1); // Access "a", making it MRU. Order becomes: b (oldest), c, a (newest)
  cache.set("d", 4); // Should evict "b"

  assert.equal(cache.has("b"), false, "b should have been evicted");
  assert.equal(cache.get("a"), 1);
  assert.equal(cache.get("c"), 3);
  assert.equal(cache.get("d"), 4);
});

test("LRUCache respects TTL expiration", async () => {
  const { LRUCache } = loadModule("../src/features/digest/cache/lruCache.ts");
  const cache = new LRUCache({ maxSize: 10, ttlMs: 30 }); // 30ms TTL

  cache.set("temp", "value");
  assert.equal(cache.get("temp"), "value");

  await new Promise((resolve) => setTimeout(resolve, 45));
  assert.equal(cache.get("temp"), undefined, "Entry should expire after TTL");
});

test("digestCache synchronizes paper favorite states across cached groups", () => {
  const { digestCache } = loadModule("../src/features/digest/cache/digestCacheService.ts");

  const mockGroup1 = {
    publish_date: "2026-09-10",
    paper_count: 2,
    page: 1,
    page_size: 50,
    has_more: false,
    items: [
      { id: 101, title_zh: "文献A", is_favorited: false },
      { id: 102, title_zh: "文献B", is_favorited: false },
    ],
  };

  const mockGroup2 = {
    publish_date: "2026-09-09",
    paper_count: 1,
    page: 1,
    page_size: 50,
    has_more: false,
    items: [
      { id: 101, title_zh: "文献A", is_favorited: false },
    ],
  };

  digestCache.setCachedGroup({ publishDate: "2026-09-10" }, mockGroup1);
  digestCache.setCachedGroup({ publishDate: "2026-09-09" }, mockGroup2);

  // Atomically favorite paper 101
  digestCache.updatePaperFavoriteState(101, true);

  const updated1 = digestCache.getCachedGroup({ publishDate: "2026-09-10" });
  const updated2 = digestCache.getCachedGroup({ publishDate: "2026-09-09" });

  assert.equal(updated1.items.find((p) => p.id === 101).is_favorited, true);
  assert.equal(updated1.items.find((p) => p.id === 102).is_favorited, false);
  assert.equal(updated2.items.find((p) => p.id === 101).is_favorited, true);
});
