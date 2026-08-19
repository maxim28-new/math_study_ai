"use strict";
const assert = require("assert");
const path = require("path");
const L = require(path.join(__dirname, "..", "web", "lesson", "state.js"));

const empty = L.emptyLesson();
assert.strictEqual(empty.rung, "do");
assert.strictEqual(empty.shrinks, 0);

let why = L.normalizeLesson({ rung: "why", shrinks: 0 });
why = L.applyShrink(why);
assert.strictEqual(why.rung, "why");
assert.strictEqual(why.shrinks, 1);
why = L.applyShrink(why);
assert.strictEqual(why.rung, "see");
assert.strictEqual(why.shrinks, 2);
why = L.applyShrink(why);
assert.strictEqual(why.shrinks, 3);
assert.strictEqual(L.applyShrink(why).shrinks, 3);

const stay = L.applyShrink(L.applyShrink(L.emptyLesson()));
assert.strictEqual(stay.rung, "do");

const kept = L.resetForNewCard({
  rung: "see",
  shrinks: 2,
  discoveries: [{ insight_key: "equalize_by_half_diff", child_said: "差会少 2", topic: "wordproblems" }],
});
assert.strictEqual(kept.rung, "do");
assert.strictEqual(kept.discoveries[0].child_said, "差会少 2");

const insight = "每移过去一张，哥哥这边少一张、弟弟那边多一张，两行的差距一次缩小2";
assert.strictEqual(L.leaksInsight(insight, insight), true);
assert.strictEqual(L.leaksInsight("移一张，差少 2", insight), false);

const leaked = L.harvestDiscovery(
  { accepted_by_child: true, statement: insight },
  insight,
  insight,
  "equalize_by_half_diff"
);
assert.strictEqual(leaked, null);

const got = L.harvestDiscovery(
  { accepted_by_child: true, statement: insight },
  "移一张，差少 2",
  insight,
  "equalize_by_half_diff",
  "wordproblems"
);
assert.strictEqual(got.child_said, "移一张，差少 2");

const merged = L.mergeDiscovery(L.emptyLesson(), got);
assert.strictEqual(merged.discoveries.length, 1);

assert.ok(L.lastChildText([{ role: "user", content: "移一张" }]).includes("移一张"));
assert.strictEqual(L.SHRINK_MESSAGE.indexOf("再小一点") >= 0, true);

console.log("lesson_state_test.js ok");
