/* Unit test standalone untuk isNodeVisible() — pure function, no framework.
 * Jalankan: node test_visibility.js
 * ponytail: copy-paste fungsi dari graph.js (closure-private, nggak bisa di-require),
 * test cuma logika visibility. Edge case §6 #1 (false-positive prefix) wajib lulus.
 */
const assert = require("assert");

function dirDepth(id) { return id.split("/").length - 1; }

// direct-parent semantics (§2/§7): grandchild hidden kalau cuma parent di-expand
function isNodeVisible(node, openDirsSet) {
  const depth = dirDepth(node.id);
  if (depth === 0) return true;
  const parts = node.id.split("/");
  const parent = parts.slice(0, parts.length - 1).join("/");
  return openDirsSet.has(parent);
}

// depth-0 selalu visible walau openDirs kosong
assert.strictEqual(isNodeVisible({ id: "app.py" }, new Set()), true);
// direct child visible kalau parent di-expand
assert.strictEqual(isNodeVisible({ id: "src/app.py" }, new Set(["src"])), true);
// edge case §6 #1: "src2/app.py" TIDAK boleh match openDir "src"
assert.strictEqual(isNodeVisible({ id: "src2/app.py" }, new Set(["src"])), false);
// grandchild hidden kalau cuma parent di-expand (perlu ancestor langsung)
assert.strictEqual(isNodeVisible({ id: "src/utils/x.py" }, new Set(["src"])), false);
// grandchild visible kalau parent + grandparent keduanya di-expand
assert.strictEqual(isNodeVisible({ id: "src/utils/x.py" }, new Set(["src", "src/utils"])), true);
// node dalam folder kosong-state (openDirs kosong) → hidden
assert.strictEqual(isNodeVisible({ id: "src/app.py" }, new Set()), false);

console.log("all visibility tests passed");
