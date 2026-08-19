# 发现留下 · 换看法 · 再小一点

> **For agentic workers:** Implement top to bottom. Check off steps as you go. Do not restore 70s author retries, 3×3 explore fallback, or stairs keyword coercion. Do not hand-write entire seed cards. Do not put `insight` in any child-visible surface.

**Goal:** 探索课变成同一份课状态：孩子的原话能活过换一题；卡住可以把问题削薄；同一堆数学对象可以换成另一种合法看法。

**Architecture:** 纯函数课状态放在 `server/lesson.py` 与 `web/lesson/state.js`（规则与 activity/state.js 一样，无 Konva）。陪练提示注入当前台阶与已说出口的发现。换看法是受检工具 `board_switch_view`，只允许题卡 `allowed_views` 里的投影。画板种类不新增。

**Tech Stack:** 现有原生 JS H5、FastAPI、Tutor Agent tools、`unittest` + Node assert + Playwright 手机视口。

**顺序（必须按这个做，不要并行铺开）：**

1. **Slice A** — 「再小一点」+ 发现能留下。六种现有画板都能用。不碰新渲染。
2. **Slice B** — 一根 `switch_view` 管子。贴纸题（2×8、12 块）作为孩子能看见的样板：`snap_grid` ↔ `pair_rows`。
3. **Slice C** — 第三次「再小一点」若有第二看法就提议换看法，否则缩小数字。仍然不给答案。

---

## 产品契约（全程有效）

- 题卡 `insight` 只给陪练。字幕、词卡、发现芯片、孩子气泡里都不得出现未认可的洞见全文。
- 芯片上的字必须是孩子说过的话（可短裁），不是 insight 段落。
- `insight_key` 是短英文键，用来判断下一题能不能引用上一句。对不齐键就闭嘴。
- do → see → why 不是单向关卡：孩子自己跨层，跟上去即可。
- 「再小一点」没有揭晓开关。`shrinks` 到顶仍禁止说出答案。
- `board_switch_view` 失败时只用嘴继续，盘面保持上一张有效图。
- 换看法不清发现芯片。开启新的探究才清空发现与台阶厚度。
- 换一题：发现留下，`rung` 回到 `do`，`shrinks` 归零，看法回到题卡默认。
- 现场长文出题仍暂停。只给 18 张种子补 `insight_key` / 少数 `allowed_views`。

### 课状态

```text
{
  rung: "do" | "see" | "why",
  shrinks: 0 | 1 | 2 | 3,
  view: "",
  discoveries: [{ insight_key, child_said, topic }]
}
```

跟着主题走（进 `topicWorkspaces`），不跟着这一道题走。

### 削薄

| 点的次数 | shrinks 变为 | 陪练必须做 | 禁止 |
|---|---|---|---|
| 第 1 次 | 1 | 留在当前层，问句变短；可高亮一个对象 | 说出 insight、跳到 why |
| 第 2 次 | 2 | 掉一层（why→see，see→do）；已在 do 就再削，并动一次画板 | 换题、给答案 |
| 第 3 次 | 3 | Slice C：有第二看法则提议换看法；否则数字缩小一档 | 仍然不给答案 |

加号里的「小提示」改成「再小一点」。带题模式横条「我卡住了」不动。

---

### File map

- Create: `docs/superpowers/plans/2026-08-19-lesson-discoveries.md`（本文件）
- Create: `server/lesson.py`
- Create: `web/lesson/state.js`
- Create: `tests/test_lesson.py`
- Create: `tests/lesson_state_test.js`
- Modify: `server/author.py` — `insight_key`、`allowed_views` 进入 normalize
- Modify: `data/seed_catalog.json` — 18 张补 `insight_key`；贴纸题补 `allowed_views`
- Modify: `server/tutor.py` — 课状态注入提示；AGENT 工具说明
- Modify: `server/app.py` — `ChatRequest.lesson` / `lesson_event`
- Modify: `server/agent/runtime.py` / `tools.py` / `workspace.py` / `skills.py`
- Modify: `web/app.js` / `web/index.html` / `web/styles.css`
- Modify: `web/activity/snap-grid.js` — `pair_rows` 行标签
- Modify: `web/board/workspace.js` — 种子带上 insight_key / allowed_views
- Modify: `tests/test_frontend_regressions.py` / `tests/test_author.py` / `tests/e2e/test_phone_ux.py`
- Cache bust: `v=20260819-lesson`

---

## Slice A — 再小一点 + 发现留下

### Task A1: 课状态纯函数（TDD）

**Files:** `tests/test_lesson.py`, `server/lesson.py`

- [x] **Step 1:** 断言 `empty_lesson`、`normalize_lesson`、`apply_shrink`（do 上两次削薄仍停在 do；why→see→do）、`insight_key_of`、`leaks_insight`、`harvest_discovery`（洞见全文被拒，孩子原话收下）、`discovery_prompt_block`（只注入同 key 的原话）、`shrink_prompt_block`、`lesson_guidance`（含当前层 ladder.ask，不含把 insight 当作孩子可见文案）。
- [x] **Step 2:** `python3 -m unittest tests.test_lesson -v` 先红。
- [x] **Step 3:** 实现 `server/lesson.py`。
- [x] **Step 4:** 再跑到绿。

`leaks_insight(text, insight)`：任一方包含另一方，或连续 8 字窗口重叠，即视为泄底。

### Task A2: 前端镜像（TDD）

**Files:** `tests/lesson_state_test.js`, `web/lesson/state.js`

- [x] 与 Python 对齐：`emptyLesson`、`normalizeLesson`、`applyShrink`、`leaksInsight`、`harvestDiscovery`、`SHRINK_MESSAGE`。
- [x] `node tests/lesson_state_test.js` 输出 `lesson_state_test.js ok`。
- [x] `test_frontend_regressions.py` 增加调用该 Node 测试（仿 `activity_state_test.js`）。

### Task A3: 题卡 insight_key

**Files:** `server/author.py`, `data/seed_catalog.json`, `tests/test_author.py`

- [x] `normalize_card` 写入 `insight_key`（合法 `[a-z][a-z0-9_]{2,47}` 则保留，否则由 insight 做稳定短键）和 `allowed_views`（缺省 `[]`）。
- [x] 18 张种子补显式 `insight_key`。同一洞见家族共用一键；本库 18 张各不相同即可。
- [x] 断言 `seed_variants` 每张卡都有 `insight_key`。

键名（固定）：

| 主题 | 键 |
|---|---|
| arithmetic | `place_value_bundle_ten`, `pair_ends_multiply`, `common_measure_gcd` |
| wordproblems | `compare_then_total`, `equalize_by_half_diff`, `enumerate_by_large_move` |
| algebra | `undo_last_operation`, `same_both_sides`, `repeated_add_is_multiply` |
| reasoning | `remainder_in_cycle`, `last_jump_recurrence`, `pair_ends_or_level` |
| fractions | `equal_share_of_pile`, `compare_unit_pieces`, `bigger_denominator_smaller_unit` |
| geometry | `equal_radii_equilateral`, `diagonal_halves_rectangle`, `reflection_equal_distance` |

### Task A4: 陪练注入 + API

**Files:** `server/tutor.py`, `server/app.py`, `server/agent/runtime.py`

- [x] `build_system_prompt(..., lesson=None, lesson_event="")` 追加 `lesson.lesson_guidance(lesson, card)` 与 `seen_terms` 同级。
- [x] `lesson_event == "shrink"` 时再追加本轮削薄指令。
- [x] `ChatRequest` 增加 `lesson: dict | None`、`lesson_event: str`。
- [x] Agent prompt 同样注入；`AGENT_TOOLS_GUIDE`：孩子用自己的话说圆了，必须 `lesson_record_claim`（statement=孩子原话）再 `lesson_mark_child_acceptance`；禁止把 insight 写进 statement。
- [x] 不要把 insight 写进任何孩子可见 SSE 字段。

### Task A5: H5 会话、按钮、芯片

**Files:** `web/app.js`, `web/index.html`, `web/styles.css`

- [x] `state.lesson`；`snapshotWorkspace` / `saveSession` / `applyWorkspace` / `emptyWorkspace` 带上它。
- [x] `startExplore`：保留 `discoveries`，`rung=do`，`shrinks=0`，`view=""`。
- [x] `resetBtn`：`lesson = emptyLesson()`。
- [x] `#hintBtn` 文案「再小一点」；点击 `applyShrink` + `pendingLessonEvent="shrink"` + `sendMessage(SHRINK_MESSAGE)`。
- [x] `/api/chat` body 带 `lesson`、`lesson_event`。
- [x] `applyMathWorkspace` 后用最近一条孩子原话 `harvestDiscovery`；芯片只显示 `child_said`。
- [x] 「刚才的对话」顶上 `#discoveryStrip`。点芯片只展开孩子原话（`#discoveryCard`），不展开 insight。
- [x] 脚本顺序：`lesson/state.js` 在 `app.js` 之前。资源戳 `v=20260819-lesson`。

### Task A6: Slice A 测试

- [x] 前端回归：`再小一点`、`id="discoveryStrip"`、`v=20260819-lesson`、`function applyShrink` / `harvestDiscovery`。
- [x] e2e：加号里能看见「再小一点」；点下去会多一条孩子消息且 tutor 被调用；历史里有发现条（可为空）。
- [x] `unittest discover` 保持绿。

---

## Slice B — 换看法管子

### Task B1: 题卡允许的看法 + 工具

**Files:** `server/agent/workspace.py`, `web/board/workspace.js`, `server/agent/tools.py`, `tests/test_agent_workspace.py`

- [x] `seed_from_card` 把 `insight_key`、`allowed_views` 写入 `problem`。缺省 `allowed_views` 为当前默认 representation。
- [x] 工具 `board_switch_view({view_id})`：不在名单里则失败；成功则 `workspace.view.representation = view_id` 并 bump。
- [x] 贴纸题 `allowed_views: ["snap_grid", "pair_rows"]`，默认 `snap_grid`。
- [x] Skills `choose_representation`：允许调用该工具，禁止口头假装已经换图。

### Task B2: 贴纸第二看法

**Files:** `web/activity/snap-grid.js`, `web/app.js`, `data/seed_catalog.json`

- [x] `pair_rows`：同一 2×8 点格，两行旁标「哥哥」「弟弟」，格子与托盘仍空着，不预摆 8+4。
- [x] `applyMathWorkspace` 若 representation 在 snap_grid / pair_rows 间切换，按新看法重挂点格，保留占用。
- [x] 失败或非法 view_id：不重挂。

### Task B3: Slice B 测试

- [x] 工具：合法切换 ok，非法 id 失败且 version 不变。
- [x] 回归：`board_switch_view`、`pair_rows`、`还没放进去的方块` 仍在。
- [x] e2e 贴纸题默认仍是空 6+6 托盘；不要求自动切看法。

---

## Slice C — 削到头接上看法

### Task C1: 第三次削薄的提示

**Files:** `server/lesson.py`, `web/lesson/state.js`, `tests/test_lesson.py`

- [x] `shrinks` 到 3 时 `shrink_prompt_block`：若 `allowed_views` 有别于当前的 id，要求本轮用一句话问要不要换看法，需要时调用 `board_switch_view`；否则用更小数字问同一件事。
- [x] 仍然禁止 insight 和完整解法。
- [x] 前端 `applyShrink` 封顶 3。

### Task C2: 收尾测试与线上

- [x] 全量 `unittest discover`（含 e2e）。
- [x] 提交、推送、PR；缓存戳已换则重启 `xiaoou-server`。

---

## 不做

- 知识点树、掌握度条、家长周报（以后再说）。
- 新棋盘 kind。
- 第一种看法以外的任意切换（尺规、跳台阶、涂色互切）。
- 恢复现场 Author 长等待。
- 发现芯片里放 insight 全文「方便家长」。
- 第四个探索底栏按钮。
