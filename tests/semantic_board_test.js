"use strict";

const assert = require("assert");
const B = require("../web/board/state.js");

const layers = B.normalize({
  schema: 2,
  kind: "layer_sum",
  layers: [1, 2, 3, 4, 5],
  item: "罐",
  ask: "total",
  reveal: "items_without_total",
});
assert.strictEqual(layers.kind, "layer_sum");
assert.deepStrictEqual(layers.layers, [1, 2, 3, 4, 5]);

const path = B.normalize({
  schema: 2,
  kind: "path_count",
  start: 0,
  target: 2,
  moves: [1, 2],
  ask: "number_of_paths",
  reveal: "rules_only",
});
assert.strictEqual(path.kind, "path_count");

const state = B.createPathState(path);
assert.deepStrictEqual(state.snapshot().found_paths, []);
assert.strictEqual(state.move(1).reached, false);
assert.strictEqual(state.move(1).reached, true);
assert.deepStrictEqual(state.snapshot().found_paths, [[1, 1]]);
state.resetRoute();
assert.strictEqual(state.move(2).reached, true);
assert.deepStrictEqual(state.snapshot().found_paths, [[1, 1], [2]]);
state.resetRoute();
state.move(2);
assert.deepStrictEqual(state.snapshot().found_paths, [[1, 1], [2]], "duplicate routes are ignored");

assert.strictEqual(B.normalize({ schema: 2, kind: "stairs", rows: 2 }), null);
assert.strictEqual(B.normalize({
  schema: 2,
  kind: "path_count",
  start: 0,
  target: 2,
  moves: [0, 2],
  ask: "number_of_paths",
  reveal: "rules_only",
}), null);
assert.ok(B.formatSnapshot(state.snapshot()).includes("语义画板盘面"));

console.log("semantic_board_test.js ok");
