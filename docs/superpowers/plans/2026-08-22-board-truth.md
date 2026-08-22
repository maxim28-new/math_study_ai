# 盘面说了算 · 定死开场 · 规律成芯片

> **For agentic workers:** Implement top to bottom. Check off as you go. Do not restore 70s author retries, 3×3 explore fallback, or stairs keyword coercion. Do not hand-write entire seed cards. Do not put `insight` on any child-visible surface. Do not add new board kinds. Do not paint stickers/oranges.

**Goal:** 点格占用是权威数字；开场白用题卡第一问，不再让模型修饰；孩子答「你总结出什么规律了吗？」且通过死规则后落芯片；对孩子只说蓝块/格子。

**顺序：**

1. 定死开场白（不调 kickoff 模型）
2. 占用进工作区 + `board_set_rows` + 提示词跟占用走
3. 规律问答落芯片
4. 蓝格子词表（字幕、第一问、旁标）

---

## 产品契约

- 开场 = `card.first_question`。字幕和第一条小欧气泡同一句。禁止打招呼改写。
- `first_question` 由画板生成（`first_question_for_v3`）。点格说蓝块/上排/下排/托盘。
- 占用表：上排几、下排几、托盘几。嘴不能说占用表里没有的个数。
- `board_set_rows` 只写合法摆放（每行 ≤ 列数，总数 ≤ 托盘）。失败则盘面不变。
- 开场不要调用摆放工具；孩子自己拖。工具是后来合法意图用的。
- 芯片：小欧问固定句「你总结出什么规律了吗？」→ 孩子下一句为候选。通过 = 非空、不泄洞见全文、对不上题卡 `misconceptions`。字只用孩子原话。
- 换一题留芯片；开启新的探究清空。
- `pair_rows` 旁标改成「上排」「下排」。

### File map

- Create: 本文件
- Modify: `server/board.py` — 点格第一问用蓝格子
- Modify: `server/lesson.py` / `web/lesson/state.js` — `accept_regularity`、`REGULARITY_ASK`
- Modify: `server/agent/workspace.py` / `web/board/workspace.js` — 点格占用
- Modify: `server/agent/tools.py` — `board_set_rows`
- Modify: `server/agent/runtime.py` / `skills.py` / `tutor.py`
- Modify: `web/app.js` — `playFixedOpening`；占用同步；规律收芯片
- Modify: `web/activity/snap-grid.js` — 上排/下排
- Modify: `data/seed_catalog.json` — 仅贴纸题 ladder/prompt 收成蓝格子（不重写整卡）
- Modify: tests + cache `v=20260822-board`

---

## Slice 1 — 定死开场

- [x] `playFixedOpening(card)`：`setCaption(first_question)`；若还没有小欧气泡，写入一条 assistant 消息。
- [x] `startPlay` / `applyNewExploreCard` 不再 `streamAssistant(true)`。
- [x] 回归：开场函数存在；apply 段没有 `streamAssistant(true)`。
- [x] e2e 不再要求 kickoff POST；字幕含蓝格子开场。

## Slice 2 — 占用权威

- [x] 点格种子带 `grid_rows/cols/tray` 与空占用。
- [x] `board_set_rows({counts})`：合法则写占用并 bump；10 和 2 在 2×8/托盘12 上失败。
- [x] 孩子拖完把占用写回 `mathWorkspace`（settle 时 bump）。
- [x] `applyMathWorkspace` 按占用重挂点格。
- [x] 可见快照带 `occupancy`。提示：只能说这些数；要改图先工具成功。

## Slice 3 — 规律芯片

- [x] `accept_regularity(said, card, topic)` 纯函数 + JS 镜像。
- [x] 上一句小欧含 `REGULARITY_ASK` 时，孩子下一句带 `lesson_event=regularity` 并尝试收芯片。
- [x] 第 2 档削薄提示要求本轮问这句固定问。

## Slice 4 — 蓝格子词

- [x] 点格 `first_question_for_v3` 用蓝块/上排/下排。
- [x] `pair_rows` 旁标上排/下排。
- [x] 贴纸题 ladder/task.prompt 收成蓝格子。
- [x] AGENT 提示：对孩子禁止贴纸/橘子/哥哥/弟弟等比喻。

## 不做

- 贴纸/橘子皮肤。
- 让字幕数字去开画板。
- 恢复现场 Author 长等待。
- 两步 claim + acceptance 作为芯片唯一开关。
