# 小欧 Tutor Agent：Skills 与数学 Tools

## 状态

提案。本文定义 BoardSpec V3 之后的目标架构，不代表当前代码已经具备这些能力。

## 一句话原则

> 约束动作，不约束思路。

小欧负责像数学家和老师一样判断下一步；程序只约束它能对数学世界和画板做哪些
可验证的动作。不要把教学路线写成固定状态机，也不要让模型直接生成 SVG、DOM 或
任意画图 JSON。

## 为什么要改

当前系统分成两个近似单次调用的模型：

1. 作者生成一张题卡和一张固定 BoardSpec V3；
2. 陪练读取题卡和盘面 snapshot，只输出自然语言；
3. 画板只会响应预先写好的交互，不会因为对话自动选择新表示或做新构造。

这保证了画板不会被模型随意改坏，但也带来三个结构性问题：

- 题卡选错表示时，后面的陪练无法纠正；
- 陪练说到新的认知阶段，画板仍停在旧画面；
- 每出现一种数学关系，就容易新增一个专用 `kind` 或关键词特判。

这些问题不能靠继续增加案例判断解决。目标应从“固定题卡 + 固定活动”升级为
“持久数学工作区 + Tutor Agent + 受控数学工具”。

## 产品目标

- 小欧能根据孩子的回答自主选择追问、反例、构造、表示切换或保持画板不变；
- 推理尽量从当前主题的定义、公理、已知条件和孩子已经认可的结论出发；
- 每次画板变化都与小欧说的话一致，并可由服务端验证；
- 画板展示的是当前推理所需的信息，不提前泄露答案；
- 同一数学思想可以有不同教学路径，不由代码预先规定唯一顺序；
- 失败时保留上一张有效盘面和自然语言对话，不展示协议或半成品。

## 非目标

- 不要求每轮对话都改变画板；
- 不把完整课程写成 `step 1 → step 2 → step 3` 的固定流程；
- 不允许模型执行 JavaScript、HTML、SVG、Canvas 或 Konva 代码；
- 不向孩子展示模型私有思维链；
- 不让“工具调用成功”代替数学正确性检查；
- 不在第一版建设通用计算机代数系统或自动定理证明器。

## 设计边界

### Agent 拥有的自由

Tutor Agent 可以决定：

- 当前最值得追问的一个问题；
- 是否需要画板；
- 继续使用当前表示，还是换成数轴、积木、点阵、线段、表格或几何构造；
- 添加、移动、分组、高亮或隐藏哪些数学对象；
- 是否用一个反例检验孩子的猜想；
- 是否暂时不做任何画板动作；
- 何时回到定义、公理或已知条件。

### Runtime 必须控制的边界

Runtime 负责：

- 工具参数 schema；
- 数量、坐标、对象引用和资源上限；
- 数学对象之间的基本一致性；
- 动作是否只引用当前工作区中的对象；
- 是否泄露题卡标记为隐藏的结论；
- 事务提交、失败回滚、幂等和审计；
- 前端确定性渲染。

## 总体架构

```text
孩子输入 / 画板操作
        │
        ▼
┌───────────────────────┐
│ Tutor Agent Runtime   │
│ 读取会话、题目、盘面、│
│ 公理、证明台账与 Skills│
└──────────┬────────────┘
           │ 0..N 次工具调用
           ▼
┌───────────────────────┐
│ Tool Gateway          │
│ schema + policy +     │
│ math/scene validation │
└──────────┬────────────┘
           │ 原子提交
           ▼
┌───────────────────────┐
│ Math Workspace        │
│ objects / relations / │
│ claims / visibility   │
└──────────┬────────────┘
           │ BoardPatch + snapshot
           ▼
┌───────────────────────┐
│ Deterministic Renderer│
└───────────────────────┘

Agent 最终输出一句孩子可见的话。
```

作者仍可生成题目、目标和初始数学对象，但不再决定完整教学路线。运行时 Tutor Agent
可以在题目约束内选择新的合法表示。

## Agent 的一轮

一轮不是“调用一次模型直接流文字”，而是一个有上限的 agent loop：

1. **Observe**：读取孩子输入、当前画板 snapshot、最近结论和待验证猜想；
2. **Choose skill**：选择当前有用的教学/数学策略；
3. **Act（可选）**：调用 0～3 个受控工具；
4. **Verify**：读取工具结果，确认图、话、数量和可见性一致；
5. **Speak**：只向孩子输出一个清晰问题或短反馈；
6. **Persist**：保存工作区版本、工具调用和结构化教学台账。

工具失败时，Agent 可以换一种合法表示或只用语言继续；不能假装工具已经成功。

不是每轮都需要 `Act`。例如孩子只是说“我没听懂”，Agent 可以先换一句白话，而不动
画板。只有视觉变化能推进当前思考时才调用工具。

## Skills

Skill 是策略说明和选择条件，不是固定步骤脚本。Skill 不直接操作 DOM，只能指导
Agent 选择 Tools。

### `euclidean_reasoning`

目标：从定义、公理、已知条件和已经建立的结论出发。

- 先指出当前使用的对象和关系；
- 需要时做一个合法构造；
- 区分“看到的现象”“猜想”和“已经说明的结论”；
- 一次只要求孩子说明一个关键连接；
- 记录简短依据，例如“由同圆半径相等”，不记录或展示私有思维链。

### `socratic_tutoring`

- 判断孩子回答属于正确、部分正确、猜测、误解还是表达困难；
- 优先问能区分这些情况的最小问题；
- 不连续抛多个问题；
- 孩子已跨过一个台阶时，不重复要求同一步。

### `choose_representation`

- 数量位置与大小：数轴；
- 部分与整体、对应比较：条形图或线段图；
- 计数、乘法、面积：积木或点阵；
- 顺序与周期：序列；
- 长度、相交、全等关系：几何构造；
- 若当前表示造成误解，允许保留数学对象并切换视图。

这些是偏好，不是关键词映射。最终选择必须结合题目关系和孩子当前困难。

### `test_conjecture`

- 用最小正例或反例检验孩子的猜想；
- 明确区分“一个例子成立”和“所有情况都成立”；
- 反例只揭示当前需要的信息。

### `concrete_to_abstract`

- 先让孩子操作或观察少量具体对象；
- 再比较不变的关系；
- 最后才命名规律或写符号；
- 术语第一次出现时使用受控词卡和画板指示。

### `diagnose_misconception`

区分：

- 算错；
- 数学对象理解错；
- 图的读法错；
- 语言表达不清；
- 当前表示不合适。

只有“表示不合适”时才优先换图，避免把所有错误都变成动画。

## Math Workspace

工作区是会话的数学事实来源，不是截图或 HTML。

```json
{
  "version": 12,
  "problem": {
    "topic": "arithmetic",
    "goal": "发现连续奇数形成平方数",
    "givens": []
  },
  "objects": [],
  "relations": [],
  "claims": [],
  "conjectures": [],
  "visibility": {},
  "view": {},
  "child_model": {}
}
```

### Objects

第一阶段支持少量组合性强的对象：

- `tile`
- `point`
- `segment`
- `circle`
- `number`
- `interval`
- `bar`
- `sequence_item`
- `group`

每个对象有稳定 `id`。Agent 后续只能通过 `id` 引用，不能依赖屏幕像素或 DOM selector。

### Relations

- `equal_length`
- `same_group`
- `ordered_before`
- `contains`
- `intersects`
- `adjacent`
- `forms_rectangle`
- `forms_square`
- `sum_of`

关系必须引用已有对象。部分关系可由验证器计算，不能只因为模型声称成立就写入台账。

### Claims 与 proof ledger

```json
{
  "id": "claim_square_2",
  "statement": "四块积木组成 2×2 正方形",
  "status": "observed",
  "based_on": ["group_center", "group_ring_3"],
  "accepted_by_child": false
}
```

台账保存可审计的“结论 + 简短依据”，不保存模型私有 chain-of-thought。

### Child model

只保存教学所需的结构化状态：

- 已经认可的结论；
- 当前猜想；
- 最近一次误解类型；
- 已理解术语；
- 当前需要验证的问题。

不推断敏感人格、能力标签或长期画像。

## Tools

工具按照“数学意图”设计，而不是按照组件设计。

### 观察

```text
workspace.inspect()
workspace.inspect_visible()
math.check_claim(claim)
```

`inspect_visible` 返回孩子真实看见的内容，避免 Agent 根据隐藏对象提问。

### 构造

```text
board.add_tiles(count, group_id?)
board.add_point(label?)
board.add_segment(from_id, to_id)
board.add_circle(center_id, radius_relation)
board.mark_intersection(object_a, object_b)
```

### 组织与变换

```text
board.arrange(object_ids, layout, constraints)
board.group(object_ids, group_id)
board.move(object_ids, target_relation)
board.switch_view(representation, preserve_relations)
```

`layout` 是有限枚举或受校验参数，例如 `row`、`grid`、`outer_ring`、`numberline`；
不是 SVG path。

### 注意与揭示

```text
board.highlight(object_ids, style="focus")
board.hide(object_ids)
board.reveal(object_ids)
board.annotate(target_id, text_kind)
```

注释文本优先来自受控 label 或数学值，不允许任意富文本。

### 教学台账

```text
lesson.record_conjecture(statement, object_ids)
lesson.record_claim(statement, based_on)
lesson.mark_child_acceptance(claim_id)
lesson.set_focus(question_id)
```

`record_claim` 不等于证明成功。可计算关系由 `math.check_claim` 校验；不可自动验证的命题
标成 `proposed`，不能伪装为 `verified`。

## Tool 调用协议

模型输出使用提供商的原生 tool calling；如果模型端不支持，再使用严格 JSON envelope。
不要从自然语言或 Markdown 中用正则提取画板指令。

示例：

```json
{
  "tool": "board.arrange",
  "arguments": {
    "object_ids": ["center", "ring3_1", "ring3_2", "ring3_3"],
    "layout": "outer_ring",
    "constraints": {
      "around": "center",
      "target_shape": "square"
    }
  },
  "expected_workspace_version": 12
}
```

Tool Gateway 返回：

```json
{
  "ok": true,
  "workspace_version": 13,
  "created_relations": ["square_2x2"],
  "visible_snapshot": {
    "tile_count": 4,
    "shape": "square",
    "side": 2
  }
}
```

每次调用携带 `expected_workspace_version`，防止慢请求覆盖孩子刚做的新操作。

## BoardSpec V4 的定位

V4 不再是一张不可变的“活动模板”，而是 Math Workspace 的一个版本化投影：

```json
{
  "schema": 4,
  "workspace_version": 13,
  "scene": {
    "objects": [],
    "relations": []
  },
  "view": {
    "representation": "tiles",
    "camera": "fit",
    "hidden": []
  },
  "affordances": [
    "select",
    "drag",
    "group"
  ]
}
```

前端接收完整 snapshot 或经过验证的增量 `BoardPatch`，执行后回传新的可见 snapshot。
V4 仍然不包含 DOM、SVG、Canvas、Konva 或任意代码。

V3 专用组件可以作为 V4 renderer 的早期实现继续使用：

- `snap_grid` → tiles + grid renderer；
- `layer_sum` → tiles + groups；
- `path_count` → points + directed moves；
- `geometry_compass` → points + segments + circles；
- `color_sequence` → sequence items。

迁移过程中不要求一次删除 V3。

## 图、话一致性

Agent 最终说话前，Runtime 做以下检查：

1. 回复中引用的对象在当前可见 snapshot 中存在；
2. 数量与 workspace 一致；
3. “相等、相交、正方形”等关系已验证或明确表述为猜想；
4. 没有提到隐藏答案；
5. 若工具失败，回复不能描述失败动作已经发生；
6. 若切换表示，核心数学关系必须被保留。

无法可靠解析自然语言里的所有数学断言时，先要求 Agent 同时给出简短结构化
`utterance_refs`，Runtime 用它检查关键对象和数值。

## 出题作者与 Tutor Agent 的分工

### 作者

作者负责：

- 题目目标；
- 已知条件；
- 允许使用的主题公理；
- 初始对象；
- 预期洞见；
- 不能提前揭示的结论；
- 典型误解。

作者不负责：

- 写死完整对话；
- 决定每一轮画板状态；
- 规定唯一表示；
- 生成渲染代码。

### Tutor Agent

Tutor Agent 负责运行时教学：

- 根据孩子真实回答调整路径；
- 选择 Skill；
- 调用 Tools；
- 维护 conjecture / claim / child model；
- 生成当前唯一一个问题。

同一主题内应保持一个持久 Agent session，而不是每轮只靠拼接聊天文本重新猜状态。

## 与现有代码的对应

第一版不需要引入独立 Agent 框架。可以在现有服务内增加清晰边界：

```text
server/agent/runtime.py       # 有上限的 tool loop
server/agent/workspace.py     # workspace reducer、版本与事务
server/agent/tools.py         # tool schema、执行器与权限
server/agent/validators.py    # 数学关系和可见性校验
server/skills/*.md|py         # 版本化 Skills
server/app.py                 # HTTP/SSE 边界，不承载数学逻辑
web/board/workspace.js        # V4 snapshot / patch 客户端
web/board/renderers/*         # 确定性 renderer
```

现有模块的迁移关系：

- `server/author.py` 保留作者职责，输出 problem contract 和初始 workspace；
- `server/tutor.py` 中的大段系统提示拆成 Skills 与运行时策略；
- `server/board.py` 的标准化逻辑逐步下沉为 workspace/tool validators；
- `web/board/state.js` 从 `kind` 分发器演进为对象/关系投影；
- V3 的各 renderer 先作为 V4 对象组合的适配器复用；
- `web/app.js` 不再从字幕、消息 Markdown 或 DOM 恢复数学状态。

### 会话与持久化

canonical workspace 应保存在服务端 session 中，浏览器只缓存最近的只读 snapshot：

- 每个主题有独立 `workspace_id`；
- 每次请求携带 `workspace_id` 和 `expected_workspace_version`；
- 服务端提交后返回新 version；
- localStorage 可用于离线 UI 恢复，但不能覆盖较新的服务端 workspace；
- 没有账号体系时，可以使用门禁 cookie 关联的随机 session id；不要把数学状态塞进 cookie。

这样工具调用、刷新和多标签页竞争都使用同一套版本规则，而不是继续依赖前端
`topicWorkspaces` 作为唯一事实来源。

### SSE 顺序

一轮中的协议事件建议为：

```text
agent_status       # 可选：正在看画板 / 正在检查
board_patch        # 工具事务已经成功提交
workspace_snapshot # patch 后的可见状态与 version
text_delta         # 孩子可见回复
done
```

如果回复引用了新画面，必须先提交并发送 `board_patch`，再开始流对应文字。若工具失败，
只能流基于旧 snapshot 的回复。前端不能先显示“已经围成正方形”，再等待一个可能失败的
画板动作。

## 安全与资源限制

- 每轮最多 3 次写工具调用，最多 1 次表示切换；
- 对象数量、坐标范围、文本长度和图片尺寸设上限；
- 写工具在临时 workspace 上执行，全部成功后原子提交；
- 未知工具、未知字段、越权对象引用全部 fail closed；
- 工具不能访问文件、网络、环境变量或浏览器 API；
- 不把 API key、系统提示或内部验证错误发送给孩子；
- 保留工具调用、验证结果和 workspace diff，便于复盘；
- 发生冲突时优先保留孩子刚完成的操作。

## 失败策略

- Skill 选择失败：只用自然语言问一个澄清问题；
- Tool 参数不合法：返回机器可读错误，允许 Agent 修正一次；
- 数学关系不成立：不提交，Agent 可以改成“这是一个猜想，我们试试看”；
- renderer 不支持：保留 workspace，换到已支持表示或显示文字提示；
- Agent 超过调用上限：停止工具循环，基于最后有效 snapshot 说话；
- 网络中断：保留上一版 workspace，不出现半张图；
- 会话恢复：按 workspace version 恢复，不从字幕或 DOM 反推数学状态。

## 例子：1 + 3

这不是固定课程状态机，而是一次可能的 Agent 选择。

初始 workspace 只有一个 tile。孩子说“四块呀”后，Agent 可以：

1. 调用 `board.add_tiles(count=3)`；
2. 调用 `board.arrange(..., layout="outer_ring", target_shape="square")`；
3. Tool Gateway 验证四块确实形成 2×2；
4. Agent 问：“新来的三块围在哪些边上？为什么刚好补成正方形？”

如果孩子对“围一圈”不理解，Agent 也可以改用 2×2 空格拖拽；如果孩子已经看懂，
它可以不动画板，直接追问下一层需要几块。路径由 Agent 选择，不由代码写死。

## 分阶段落地

### Phase 0：观测与契约

- 给现有 V3 snapshot 增加稳定对象 id、可见对象和 workspace version；
- 记录当前每轮“话里提到什么、画板实际有什么”的不一致；
- 建立 tool trace 和 workspace diff 格式；
- 不改变孩子端交互。

### Phase 1：只读 Agent

- Tutor 改为 agent loop，但只开放 `inspect`、`math.check_claim`；
- Skills 先以版本化文档/模块提供；
- 最终仍只输出自然语言；
- 验证 Agent 能正确引用当前盘面。

### Phase 2：注意类工具

- 开放 `highlight`、`annotate`、`hide/reveal`；
- 这些动作不改变数学事实，风险最低；
- 验证字幕、对话与画板同步提交。

### Phase 3：组合构造

- 开放 tiles、points、segments、circles、groups；
- 支持 `add`、`arrange`、`group` 和有限表示切换；
- 引入事务、版本冲突和数学关系校验；
- 先覆盖算术积木与圆规几何两条端到端路径。

### Phase 4：孩子与 Agent 共用工作区

- 孩子的拖动和 Agent 工具调用都写入同一 workspace；
- Agent 每轮读取孩子刚完成的 diff；
- 冲突时不覆盖孩子动作；
- 支持从操作证据更新 claim 和 child model。

## 测试

### 协议

- Python/JS 共享合法与非法 tool-call fixture；
- 未知工具、字段、对象 id、过期 version 均拒绝；
- 同一调用使用 idempotency key 不会重复添加对象。

### 数学性质

- tile 数量在变换前后守恒；
- `forms_square(side=n)` 必须有 `n²` 个互不重叠 tile；
- 同圆半径相等由 workspace 关系产生，不由模型字符串产生；
- 隐藏对象不会出现在 visible snapshot；
- 表示切换不改变已验证的核心关系。

### Agent 行为

- 无需画板时不强行调用工具；
- 工具失败后不声称画面已改变；
- 一轮最多问一个核心问题；
- 不引用孩子看不见的对象；
- 不把 `proposed` claim 说成已证明；
- 同一题允许不同合法教学路径。

### 回归

- V3 旧会话仍可读取；
- 切换主题不串 workspace；
- 刷新按 workspace version 恢复；
- 字幕只承担简短提示，不成为数学状态来源；
- 门禁、语音、画笔和术语卡行为不回退。

## 评估指标

不要只评估“工具调用成功率”。至少跟踪：

- 图文一致率；
- 数学关系验证通过率；
- 不必要画板变化率；
- 工具失败后的恢复率；
- 孩子操作后 Agent 正确读取盘面的比例；
- 同一题不同回答下教学路径的多样性；
- 直接泄露答案率；
- 从公理/已知条件到当前结论的可追溯率。

## 关键决策

1. 不采用固定课程状态机；
2. 采用有上限的 Tutor Agent loop；
3. Skills 是可选择策略，不是顺序脚本；
4. Tools 面向数学对象和关系，不面向 DOM/组件；
5. Agent 可自由选择表示，Runtime 验证动作和事实；
6. 画板不要求每轮变化；
7. 数学状态保存在 workspace，不保存在字幕、截图或聊天 Markdown；
8. 保存结构化结论与依据，不保存或展示私有思维链；
9. V3 渐进迁移，不一次推倒重写。
