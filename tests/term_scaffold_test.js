"use strict";

const assert = require("assert");
require("../web/terms/glossary.js");
const S = require("../web/terms/scaffold.js");

assert.ok(global.XiaoouTerms.byId.center);
assert.ok(global.XiaoouTerms.byId.line);
assert.ok(global.XiaoouTerms.byId.segment.words.includes("直线段"));
assert.deepStrictEqual(
  S.splitByTerms("看看交点到两个圆心的距离。").map((p) => p.id),
  ["", "intersection", "", "center", ""]
);
assert.deepStrictEqual(
  S.splitByTerms("直线段 AB 可以延长成直线。").map((p) => p.id),
  ["segment", "", "line", ""]
);
assert.deepStrictEqual(
  S.splitByTerms("先看线段 AB。").map((p) => p.id),
  ["", "segment", ""]
);
assert.ok(!S.formatCaption("这条线更长吗？", (s) => s).includes("term-chip"));
assert.ok(S.formatCaption("圆最中间的点叫圆心。", (s) => s).includes('data-term="center"'));
assert.ok(S.formatCaption("这是一条直线。", (s) => s).includes('data-term="line"'));
assert.ok(!S.formatCaption("先数一数方块。", (s) => s).includes("term-chip"));
assert.strictEqual(S.highlightKey("radius"), "radius");
assert.strictEqual(S.highlightKey("line"), "line");
assert.strictEqual(S.highlightKey("missing"), "");
assert.strictEqual(typeof S.flashTerm, "function");
assert.strictEqual(typeof S.bindHistory, "function");
assert.strictEqual(typeof S.linkTermsInElement, "function");

console.log("term_scaffold_test.js ok");
