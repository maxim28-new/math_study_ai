"use strict";

const assert = require("assert");
const fs = require("fs");
const pathModule = require("path");
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
assert.strictEqual(layers.schema, 3);
assert.deepStrictEqual(layers.model.layers, [1, 2, 3, 4, 5]);

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

const fixtures = JSON.parse(fs.readFileSync(
  pathModule.join(__dirname, "board_v3_fixtures.json"),
  "utf8"
));
fixtures.valid.forEach((raw) => {
  assert.deepStrictEqual(B.normalize(raw), raw, `valid V3 fixture: ${raw.kind}`);
});
fixtures.invalid.forEach((raw) => {
  assert.strictEqual(B.normalize(raw), null, `invalid V3 fixture: ${raw.kind}`);
});
const geometry = B.normalize(fixtures.valid.find((raw) => raw.kind === "geometry_compass"));
assert.deepStrictEqual(geometry.model.labels, ["A", "B", "P"]);
const colors = B.normalize(fixtures.valid.find((raw) => raw.kind === "color_sequence"));
assert.deepStrictEqual(colors.model.unit, ["red", "red", "blue"]);
assert.strictEqual(B.isBoardLike({ type: "geometry_demo" }), true);

const oddSquare = B.normalize({
  schema: 3,
  kind: "layer_sum",
  model: { layers: [1, 3, 5], item: "积木" },
  task: { action: "count", ask: "total", prompt: "看。" },
  view: { reveal: "items_without_total" },
});
assert.strictEqual(oddSquare.view.reveal, "stepwise");
assert.deepStrictEqual(oddSquare.model.layers, [1, 3, 5]);

console.log("semantic_board_test.js ok");
