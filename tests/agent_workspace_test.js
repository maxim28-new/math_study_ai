"use strict";

const fs = require("fs");
const path = require("path");
const vm = require("vm");

const src = fs.readFileSync(path.join(__dirname, "..", "web", "board", "workspace.js"), "utf8");
const sandbox = { console, globalThis: {} };
sandbox.globalThis = sandbox;
vm.runInNewContext(src, sandbox);
const W = sandbox.XiaoouMathWorkspace;
if (!W) throw new Error("XiaoouMathWorkspace missing");

const card = {
  hook: "连续奇数能围成正方形吗",
  insight: "连续奇数相加得到平方数",
  board: {
    kind: "layer_sum",
    model: { layers: [1, 3, 5], item: "积木" },
  },
};

const seeded = W.seedFromCard(card, "arithmetic");
if (W.formsSquare(seeded).tile_count !== 1) throw new Error("seed should be 1 tile");
if (W.formsSquare(seeded).side !== 1) throw new Error("seed should be 1x1");

const ring1 = W.addNextOddRing(seeded);
if (!ring1.ok) throw new Error("first ring failed: " + ring1.error);
if (ring1.visible_snapshot.side !== 2 || ring1.visible_snapshot.tile_count !== 4) {
  throw new Error("first ring should be 2x2");
}

const ring2 = W.addNextOddRing(ring1.workspace);
if (!ring2.ok) throw new Error("second ring failed: " + ring2.error);
if (ring2.visible_snapshot.side !== 3 || ring2.visible_snapshot.tile_count !== 9) {
  throw new Error("second ring should be 3x3");
}

const ring3 = W.addNextOddRing(ring2.workspace);
if (ring3.ok) throw new Error("third ring should be rejected");
if (W.formsSquare(ring2.workspace).tile_count !== 9) throw new Error("failed ring mutated workspace");

if (!W.matchesCard(seeded, card)) throw new Error("matchesCard");
console.log("agent_workspace_test.js ok");
