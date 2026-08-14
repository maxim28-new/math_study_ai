"use strict";
const assert = require("assert");
const path = require("path");
const A = require(path.join(__dirname, "..", "web", "activity", "state.js"));

function spec(over) {
  return Object.assign({ type: "snap_grid", cols: 3, rows: 3, tray: 9, goal: "fill", caption: "" }, over || {});
}
function snap(filled, trayLeft, over) {
  return A.makeSnapshot(spec(over), filled, trayLeft);
}

assert.strictEqual(A.parseSnapGrid("nope"), null);
assert.strictEqual(A.parseSnapGrid({ type: "dots" }), null);
assert.strictEqual(A.parseSnapGrid({ type: "snap_grid", cols: 0, rows: 3 }), null);
assert.strictEqual(A.parseSnapGrid("{"), null);

const d = A.parseSnapGrid({ type: "snap_grid" });
assert.strictEqual(d.cols, 3);
assert.strictEqual(d.rows, 3);
assert.strictEqual(d.tray, 9);
assert.strictEqual(d.goal, "fill");

const clamped = A.parseSnapGrid({ type: "snap_grid", cols: 99, rows: 1, tray: 3, goal: "other", caption: "x" });
assert.strictEqual(clamped.cols, 8);
assert.strictEqual(clamped.tray, 3);
assert.strictEqual(clamped.goal, "fill");
assert.strictEqual(clamped.caption, "x");

const s0 = snap(0, 9);
const s8 = snap(8, 1);
const s9 = snap(9, 0);
const s9extra = snap(9, 3);
const s7empty = snap(7, 0);

assert.strictEqual(A.detectMilestone(s0, s8), null);
assert.strictEqual(A.detectMilestone(s8, s9), "board_full");
assert.strictEqual(A.detectMilestone(s9, s8), null);
assert.strictEqual(A.detectMilestone(s8, s9), "board_full");
assert.strictEqual(A.detectMilestone(s8, s9extra), "board_full");
assert.strictEqual(A.detectMilestone(s0, s7empty), "tiles_exhausted");
assert.strictEqual(A.detectMilestone(s7empty, s7empty), null);
assert.strictEqual(A.detectMilestone(s8, s9extra) === "tiles_exhausted", false);

assert.strictEqual(A.milestoneHolds("board_full", s9), true);
assert.strictEqual(A.milestoneHolds("board_full", s8), false);
assert.strictEqual(A.milestoneHolds("tiles_exhausted", s7empty), true);
assert.strictEqual(A.milestoneHolds("tiles_exhausted", s9), false);

const note = A.formatBoardNote(s9, "board_full");
assert.ok(note.includes("（孩子在学具上摆完了一步，这不是她打的字）"));
assert.ok(note.includes("学具：snap_grid"));
assert.ok(note.includes("格子：3×3"));
assert.ok(note.includes("已放：9"));
assert.ok(note.includes("空格：0"));
assert.ok(note.includes("托盘剩余：0"));
assert.ok(note.includes("节点：board_full"));

const liveNote = A.formatBoardNote(s8, null);
assert.ok(liveNote.includes("（当前学具盘面，这不是她打的字）"));
assert.ok(!liveNote.includes("节点："));

assert.strictEqual(A.childLabel("board_full", s9), "摆好了：9 个格子都满了");
assert.strictEqual(A.childLabel("tiles_exhausted", s7empty), "方块用完了，格子还空着");

const html = A.renderSnapGridPlaceholder(d);
assert.ok(html.includes("data-snap-grid"));
assert.ok(html.includes("data-spec="));
assert.ok(html.includes("snap-grid-stage"));
assert.ok(html.includes("<svg"));

console.log("activity_state_test.js ok");
