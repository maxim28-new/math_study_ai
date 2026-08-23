# 《小欧数学世界》V2 可实施计划

> **状态：** 可执行实施计划  
> **来源：** 《小欧数学世界》产品与交互设计文档 v0.1  
> **首个垂直切片：** 26 号桥梁工坊  
> **实施原则：** V1 冻结；V2 独立开发；先数学内核，再世界表现，最后接入 AI  
> **目标：** 验证孩子能否通过改变世界，自主发现数量守恒、十进制成组、加法结合方式、平均分与奇偶的前置经验

---

## 0. 一句话定义

V2 不是“3D 版题库”，而是一个由确定性规则驱动的数学箱庭：

- 孩子操作有数学语义的对象；
- 世界只接受数学上合法的变换；
- 操作产生可回放的语义事件；
- 规则引擎决定什么是真的；
- 小欧决定此刻什么值得被看见；
- AI 不能直接修改世界，也不能裁定数学事实。

首期只证明一个命题：

> 同一批 26 个单位，在稳定规则下，能否让孩子通过多条路径发现 `26`、`13 + 13`，并对 `27` 不能平均分成两份产生新的问题。

---

## 1. 交付边界

### 1.1 必须交付

1. 一个横屏优先、固定斜俯视的体素数学箱庭；
2. 26 号桥梁工坊完整连续体验；
3. 26 个有来源、不会凭空增减的单位块；
4. 10、10、6 三组初始材料；
5. 合并、拆分、整组搬运、分配、对齐、撤销；
6. 总量守恒、十个成组、桥长相等三类确定性规则；
7. 至少识别三条策略：
   - 先合并两个 10；
   - 先合并 6 和 10；
   - 从一个 10 中取 4，给 6 补成 10；
8. 两条桥分成 13 和 13 后锁定并运行；
9. 新增第 27 块后形成无法平分的新局面；
10. 语义事件记录、撤销、回放和动作到算式的转译；
11. 小欧的指向、半步、方法镜像；
12. AI 导演只能发出受检意图，不能绕过规则引擎；
13. 儿童测试所需的匿名观察指标。

### 1.2 明确不做

- 无限地图；
- 第一人称自由探索；
- 生存、战斗、经济、合成系统；
- 复杂背包；
- 昼夜循环；
- 自由对话 NPC；
- 通用数学课程；
- 自动生成任意数学世界；
- AI 直接输出坐标并操纵实体；
- 排行榜、星星、金币、皮肤奖励；
- 多人联机；
- 移动端竖屏完整适配；
- 账号体系和跨设备云存档；
- 将 V1 页面原地改造成 V2。

### 1.3 成功门槛

垂直切片只有同时满足以下条件才算成功：

- 去掉文字后，孩子仍会尝试触碰或移动材料；
- 世界反馈足以让孩子自主调整不等长的桥；
- 三条合法路径都能继续推进，不依赖预设点击顺序；
- 规则引擎永远不出现单位凭空增加、丢失或重复；
- 小欧不说答案，也不替孩子完成最后一步；
- `26 → 13 + 13 → 27` 是同一世界连续变化，而非换题；
- 操作可被回放为可理解的语义过程；
- 关闭 AI 后，数学世界仍完全正确、可玩。

---

## 2. V1 与 V2 的隔离策略

### 2.1 冻结 V1

V1 继续保留现有入口、数据和部署方式，只接受阻断性修复。V2 不重写：

- `web/` 现有 H5；
- BoardSpec V3 六类画板；
- V1 的 seed card 与 tutor 对话流程；
- V1 的探索课状态。

### 2.2 可复用能力

从 V1 复用思想和后端基础设施，不复用页面结构：

| V1 能力 | V2 用法 |
|---|---|
| Math Workspace 的版本与对象关系 | 作为 V2 `WorldState` 设计参考 |
| 受检 Agent tools | 作为 V2 导演意图验证模式 |
| FastAPI、门禁、配置 | 继续承载 `/api/v2/*` |
| 本地 SenseVoice | 后续作为“语音石”输入 |
| lesson discoveries | 演化为策略发现与思考轨迹 |
| semantic board 的确定性规则 | 演化为独立 TypeScript 数学规则包 |
| SSE/模型连接 | 用于异步小欧导演响应 |

### 2.3 独立入口

- V1：`/`
- V2 开发入口：`/v2/`
- V2 API：`/api/v2/*`
- V2 资产：独立构建到 `v2/apps/web/dist/`
- 未达到验收门槛前，不替换 V1 默认入口。

路由实现约束：

- Vite 必须设置 `base: "/v2/"`；
- FastAPI 必须在现有根目录 `app.mount("/")` 之前挂载 `/v2`；
- `/v2/` 与 `/api/v2/*` 首期共享 V1 门禁 cookie，不另建登录态；
- V2 会话和 V1 lesson/session 使用不同存储前缀，不能相互读取；
- 必须有回归测试证明 `/`、`/api/config`、V1 静态资产和门禁行为不变。

---

## 3. 技术选型

### 3.1 前端

- TypeScript；
- Vite；
- Three.js；
- 原生 DOM UI，不引入 React；
- Vitest；
- fast-check，用于规则属性测试；
- Playwright，用于浏览器与儿童操作路径测试。

选择 Three.js 的理由：

- 首期是固定斜俯视箱庭，不需要完整游戏引擎；
- 对体素、正交相机、拾取、拖拽、补间动画足够；
- 数学规则与渲染层可以彻底分离；
- 资产和运行体积可控；
- 后续仍能增加角色、光照和小范围世界。

### 3.2 后端

- 继续使用 FastAPI；
- Pydantic 定义 API；
- 现有模型供应商用于小欧语言与导演决策；
- 本地 JSONL/SQLite 记录开发期会话；
- 生产持久化接口保留抽象，首期不引入大型数据库。

### 3.3 为什么不先做完整 Minecraft 引擎

首期验证对象是数学机制，不是开放世界能力。第一人称移动、碰撞、背包和自由相机都会增加操作负担，且难以判断孩子卡在数学还是卡在游戏控制。

首期使用：

- 正交相机；
- 固定斜俯视；
- 有限工坊；
- 自动聚焦；
- 直接拖动物体；
- 无角色移动摇杆。

如果验证成立，再增加可漫游世界作为微世界之间的连接层。

---

## 4. 代码结构

```text
math_study_ai/
├── server/
│   └── v2/
│       ├── api.py                 # /api/v2 路由
│       ├── director.py            # 小欧导演调用
│       ├── director_contract.py   # 受检意图 schema
│       ├── intervention.py        # 确定性介入策略
│       ├── persistence.py         # 会话/事件存储
│       └── prompts.py             # 只处理语言与导演提示
├── v2/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── apps/
│   │   └── web/
│   │       ├── index.html
│   │       └── src/
│   │           ├── main.ts
│   │           ├── app.ts
│   │           ├── styles.css
│   │           ├── scene/
│   │           │   ├── renderer.ts
│   │           │   ├── camera.ts
│   │           │   ├── picking.ts
│   │           │   ├── drag.ts
│   │           │   ├── animations.ts
│   │           │   └── audio.ts
│   │           ├── ui/
│   │           │   ├── caption.ts
│   │           │   ├── voice-stone.ts
│   │           │   ├── undo.ts
│   │           │   └── replay.ts
│   │           └── controller/
│   │               ├── world-controller.ts
│   │               ├── director-controller.ts
│   │               └── session-controller.ts
│   ├── packages/
│   │   ├── domain/
│   │   │   └── src/
│   │   │       ├── types.ts
│   │   │       ├── commands.ts
│   │   │       ├── events.ts
│   │   │       ├── engine.ts
│   │   │       ├── invariants.ts
│   │   │       ├── canonicalize.ts
│   │   │       ├── derivation.ts
│   │   │       ├── replay.ts
│   │   │       └── hash.ts
│   │   ├── bridge-26/
│   │   │   └── src/
│   │   │       ├── scenario.ts
│   │   │       ├── phases.ts
│   │   │       ├── devices.ts
│   │   │       ├── strategy.ts
│   │   │       ├── transitions.ts
│   │   │       └── copy.ts
│   │   └── protocol/
│   │       └── src/
│   │           ├── api.ts
│   │           ├── director.ts
│   │           └── telemetry.ts
│   ├── generated/
│   │   ├── protocol.schema.json  # TypeScript schema 生成的单一协议
│   │   └── protocol_models.py    # 由 schema 生成，禁止手改
│   ├── tools/
│   │   └── replay-session.ts     # 后端/CI 调用同一 reducer 审计事件
│   └── tests/
│       ├── properties/
│       ├── scenarios/
│       ├── fixtures/
│       └── e2e/
└── tests/
    └── test_v2_api.py
```

模块约束：

- `domain` 不得导入 Three.js、DOM、FastAPI 或 LLM；
- `bridge-26` 只能通过 `domain` 提供的命令和事件改变世界；
- 渲染层不得直接修改数学状态；
- AI 输出不得成为 `WorldState`；
- 所有世界变化必须来自 `applyCommand` 的成功结果。
- TypeScript protocol 是跨端 schema 的唯一来源；Python model 必须生成，不能手工复制。

---

## 5. 核心领域模型

### 5.1 单位来源

总量守恒不能只靠比较数字。每个单位必须有不可变 ID：

```ts
type UnitId = `unit_${number}`;

interface Unit {
  id: UnitId;
  value: 1;
  unit: "block";
  source:
    | { kind: "initial_material"; pile: "ten_a" | "ten_b" | "six" }
    | { kind: "world_event"; eventId: "add_27th_block" };
}
```

一个数量组不是“值为 10 的方块”，而是一组单位 ID：

```ts
interface QuantityGroup {
  id: string;
  kind: "quantity_group";
  unitIds: UnitId[];
  representation: "loose" | "row" | "ten_bar";
  anchor: SemanticAnchor;
  owner: "child" | "xiaoou" | "world";
  locked: boolean;
}
```

领域层只使用离散语义锚点，绝不保存 Three.js 浮点坐标：

```ts
type SemanticAnchor =
  | { zone: "material"; cell: string }
  | { zone: "workbench"; row: number; column: number }
  | { zone: "bridge_left"; slot: number }
  | { zone: "bridge_right"; slot: number }
  | { zone: "xiaoou_preview"; cell: string };
```

像素、世界坐标、拖拽插值仅存在渲染层，不进入 state hash 或回放。

因此：

- 组值 = `unitIds.length`；
- 合并是集合并集；
- 拆分是集合分区；
- 同一 `UnitId` 不得同时属于两个组；
- 除明确的世界事件外，不得出现新 `UnitId`；
- 撤销通过事件逆操作恢复，不重新生成单位。

### 5.2 世界状态

```ts
interface WorldState {
  schema: 1;
  sessionId: string;
  revision: number;
  scenario: "bridge_26";
  phase:
    | "arrival"
    | "organize"
    | "compose"
    | "split_bridges"
    | "bridge_running"
    | "odd_variant"
    | "reflection";
  units: Record<UnitId, Unit>;
  groups: Record<string, QuantityGroup>;
  unitOwner: Record<UnitId, string>; // 唯一权威归属：group、bridge 或 device id
  bridges: {
    left: BridgeLane;
    right: BridgeLane;
  };
  devices: {
    transport: { id: "transport"; unitIds: UnitId[] };
    vehicle: { id: "vehicle"; status: "parked" | "running" | "stopped" };
  };
  focus: FocusState;
  discoveries: Discovery[];
  derivation: DerivationGraph;
  history: SemanticEvent[];
  redo: SemanticEvent[][];
  director: DirectorState;
}
```

### 5.3 桥梁装置

```ts
interface BridgeLane {
  id: "bridge_left" | "bridge_right";
  slots: UnitId[];
  capacity: 27;
  locked: boolean;
  endpointOffset: number; // 离散长度差投影，不存渲染坐标
}
```

桥梁事实：

- `length = slots.length`；
- 两桥可锁定当且仅当：
  - 两桥等长；
  - 当前任务要求的全部可分配单位均已在两桥；
  - 当前 phase 允许锁定；
- 小车运行当且仅当两桥锁定；
- 27 个单位全部放入两桥时，两边不可能等长；
- 不通过文案宣布错误，只表现为桥头未对齐、无法锁定。

`unitOwner` 是单位归属的唯一事实。`groups[*].unitIds` 和
`bridges[*].slots` 是 reducer 同步维护的索引：

- 装桥时单位从原 group 移除，owner 改为 bridge；
- 从桥上取回时创建或合并到目标 group；
- 桥间移动先卸载再装载，形成一个原子命令；
- 任一单位同时出现在两个 container 时整条命令失败。

必须支持 `12/14 → 13/13`：

```ts
| { type: "unload_from_bridge"; bridgeId: string; count: number; target: SemanticAnchor }
| { type: "transfer_between_bridges"; fromBridgeId: string; toBridgeId: string; count: number }
```

第 27 块是一个受检系统事务：

1. 停止车辆；
2. 解除两桥锁定；
3. 创建唯一 `unit_27`，source 为 `add_27th_block`；
4. 将它放入运输装置的语义锚点；
5. 播放掉落效果；
6. 允许孩子把它放到任一桥；
7. 桥长变成 13/14 后由同一规则产生一边下沉。

锁定只限制车辆运行，不阻止 `odd_variant` 中重新移动桥上单位。

### 5.4 表征不是新对象

十条、散块、桥面是同一批 `UnitId` 的不同表征：

```ts
interface RepresentationChanged {
  type: "representation_changed";
  groupId: string;
  from: QuantityGroup["representation"];
  to: QuantityGroup["representation"];
  unitIds: UnitId[];
}
```

切换表征不得改变单位集合。

---

## 6. 命令、事件与规则引擎

### 6.1 命令

命令表示玩家意图，尚未被判定：

```ts
type WorldCommand =
  | { type: "focus"; entityIds: string[] }
  | { type: "move_group"; groupId: string; target: SemanticAnchor }
  | { type: "merge_groups"; groupIds: string[]; target: SemanticAnchor }
  | { type: "split_group"; groupId: string; take: number; target: SemanticAnchor }
  | { type: "place_on_bridge"; groupId: string; bridgeId: string }
  | { type: "unload_from_bridge"; bridgeId: string; count: number; target: SemanticAnchor }
  | { type: "transfer_between_bridges"; fromBridgeId: string; toBridgeId: string; count: number }
  | { type: "transfer_units"; fromId: string; toId: string; count: number }
  | { type: "align_groups"; groupIds: string[] }
  | { type: "change_representation"; groupId: string; to: QuantityGroup["representation"] }
  | { type: "accept_proposal"; proposalId: string }
  | { type: "undo" }
  | { type: "redo" };
```

命令必须放在信封中：

```ts
interface CommandEnvelope {
  commandId: string;          // 网络重试幂等键
  expectedRevision: number;   // 乐观并发
  actor: "child" | "xiaoou" | "world";
  command: WorldCommand | SystemCommand;
}

type SystemCommand =
  | { type: "advance_phase"; to: WorldState["phase"]; causeEventId: string }
  | { type: "lock_bridges"; causeEventId: string }
  | { type: "start_vehicle"; causeEventId: string }
  | { type: "add_27th_block"; causeEventId: string };
```

自动变化不是 reducer 外的特例。场景 transition 只能生成受限
`SystemCommand`，再通过同一校验、事件生成和不变量检查管线执行。

### 6.2 规则结果

```ts
type CommandResult =
  | {
      ok: true;
      state: WorldState;
      events: SemanticEvent[];
      effects: WorldEffect[];
    }
  | {
      ok: false;
      state: WorldState;
      reason:
        | "unknown_entity"
        | "locked_entity"
        | "unit_overlap"
        | "invalid_split"
        | "invalid_target"
        | "phase_disallows_action";
      effects: WorldEffect[];
    };
```

失败不能改变数学状态，但可以产生世界效果：

- 回到原位置；
- 轻微晃动；
- 桥头仍未对齐；
- 吸附未发生。

不显示红叉或“答错”。

### 6.3 语义事件

```ts
type SemanticEvent =
  | UnitsFocused
  | GroupMoved
  | GroupsMerged
  | GroupSplit
  | UnitsTransferred
  | RepresentationChanged
  | BridgeLoaded
  | BridgeLengthsCompared
  | BridgesLocked
  | VehicleStarted
  | WorldUnitAdded
  | StrategyRecognized
  | DiscoveryRecorded
  | PhaseChanged
  | XiaoouPointed
  | XiaoouHalfStepProposed
  | UndoApplied
  | RedoApplied;
```

示例：

```json
{
  "type": "groups_merged",
  "eventId": "evt_018",
  "revision": 8,
  "actor": "child",
  "sourceGroupIds": ["ten_a", "ten_b"],
  "resultGroupId": "group_20",
  "unitIds": ["unit_01", "unit_02", "…"],
  "valueBefore": [10, 10],
  "valueAfter": 20
}
```

### 6.4 规则引擎入口

```ts
function applyCommand(
  state: Readonly<WorldState>,
  envelope: Readonly<CommandEnvelope>,
): CommandResult;
```

执行顺序固定：

1. 校验 schema 与 revision；
2. 找到命令涉及实体；
3. 校验当前 phase 是否允许；
4. 校验单位集合；
5. 计算新状态；
6. 检查所有不变量；
7. 生成语义事件；
8. revision 加一；
9. 推导场景 transition，并将其变成待执行 `SystemCommand`；
10. 逐个用同一管线执行系统命令及不变量检查；
11. 生成纯表现层 effects 并返回。

任何一步失败，返回旧状态。

---

## 7. 不变量

每次命令成功后必须全部成立：

### 7.1 单位唯一

```ts
allReferencedUnitIds.length === new Set(allReferencedUnitIds).size
```

### 7.2 单位有来源

每个 `UnitId` 都存在于 `state.units`，且 source 合法。

### 7.3 总量守恒

- `arrival` 至 `bridge_running`：世界总量恒为 26；
- `WorldUnitAdded(add_27th_block)` 之后：总量恒为 27；
- 只有该世界事件可以改变总量。

### 7.4 合并守恒

合并结果单位集合等于所有输入集合的并集。

### 7.5 拆分守恒

拆分两组互不相交，并集等于原组。

### 7.6 桥梁一致

桥面 slot 中的单位不能同时存在于材料组中。

### 7.7 锁定真实性

桥梁只有等长才能 `locked = true`。

### 7.8 小欧关键步骤限制

小欧不能：

- 执行完成 `26 → 13 + 13` 的最后一次转移；
- 接受自己的幽灵方案；
- 连续成功执行两次数学命令；
- 移动孩子正在拖拽的实体；
- 通过世界事件生成普通材料。

这些限制必须在规则层校验，不能只写在 prompt。

孩子当前拖拽属于客户端瞬时 `InteractionState`，不写入数学
`WorldState`。Controller 在拖拽开始时创建 entity lease；小欧候选生成器
读取 lease 并排除该实体。命令提交时仍以 revision 和 owner 校验为最终事实。

### 7.9 十个成组

- 值为 10 只是事实，不强制改变表征；
- 相邻、对齐的 10 个单位可以产生 `ten_bar` 吸附候选；
- 孩子完成靠拢后，系统通过 `change_representation` 转为十条；
- 拆十条仍是普通 `split_group`，总量与 UnitId 不变；
- 小欧不能为了剧情强制成组。

### 7.10 归属与装置一致

- 每个 `state.units` 中的单位必须恰好有一个 `unitOwner`；
- owner 必须指向存在的 group、bridge 或 device；
- owner 指向 group 时，该单位必须且只能出现在该 group 的索引；
- owner 指向 bridge 时，该单位必须且只能出现在该 bridge slots；
- owner 指向 transport 时，该单位必须且只能出现在 transport unitIds；
- 所有 container 索引的并集必须等于 `state.units` 全集；
- vehicle `running` 时两桥必须 locked；
- bridges locked 时必须等长、处于允许 phase，且任务要求的全部单位已上桥；
- odd_variant 开始前 vehicle 必须 stopped、bridges 必须 unlocked。

### 7.11 撤销事务

每个事件必须携带：

- `commandId`；
- `transactionId`；
- `causedByEventId`（若为派生系统事件）；
- `revision`。

一个用户命令及其同步派生系统命令属于同一 transaction。undo/redo 以
transaction 为最小单位：

- `UndoApplied.targetTransactionId`；
- `RedoApplied.targetTransactionId`；
- 事件日志只追加，不删除；
- 延迟到动画完成后的系统命令形成独立 transaction，并引用原 cause；
- 已产生不可逆外部观察的 `add_27th_block` 不开放普通儿童撤销；
- replay reducer 必须从纯事件日志确定性重建 undo 与 redo 栈。

---

## 8. 思考轨迹与推导图

“行动轨迹就是证明”不能直接使用鼠标坐标。系统需要两层记录：

### 8.1 原始交互层

仅用于调试，不作为数学证明：

- pointer down/up；
- 拖拽路径；
- 命中对象；
- 相机状态；
- 动画时间。

### 8.2 语义事件层

用于数学理解：

- 选择了哪几个数量组；
- 合并了哪些单位；
- 从哪一组拿走多少；
- 两边长度如何变化；
- 哪个不变量被观察到。

### 8.3 推导图

```ts
interface DerivationNode {
  id: string;
  expression: MathExpression;
  unitPartition: UnitId[][];
  eventIds: string[];
}

interface DerivationEdge {
  from: string;
  to: string;
  operation:
    | "associate"
    | "merge"
    | "split"
    | "transfer"
    | "equal_partition"
    | "add_one";
  preserves: ("total" | "equality" | "unit_identity")[];
}
```

示例：

```text
[10] + [10] + [6]
  -- merge(first, second), preserves total -->
[20] + [6]
  -- merge, preserves total -->
[26]
  -- equal_partition -->
[13] = [13]
  -- add_one -->
[13] ≠ [14]
```

### 8.4 轨迹归一化

以下操作应归为同一种数学步骤：

- 拖动一组 10 靠近另一组 10；
- 先把两组排齐再靠近；
- 选择两组后点击组合；
- 一次移动整组或分几次移动后完成组合。

归一化基于最终单位分区和语义事件，不基于像素轨迹。

---

## 9. 三条策略识别

策略识别是确定性的纯函数：

```ts
function recognizeStrategy(events: SemanticEvent[]): StrategyMatch[];
```

### 9.1 策略 A：先合并两个十

条件：

- 初始阶段首次形成值大于 10 的新组；
- 该组单位来源恰好是 `ten_a ∪ ten_b`；
- 结果值为 20。

输出：

```json
{
  "strategy": "combine_complete_tens",
  "evidence": ["evt_012"],
  "mirrorKey": "found_two_complete_tens"
}
```

### 9.2 策略 B：先得到 16

条件：

- 首次形成的大组由 `six` 与任一 `ten` 构成；
- 值为 16。

### 9.3 策略 C：给 6 补成 10

条件：

- 从任一初始十组拆出 4；
- 这 4 个单位随后与初始 6 合并；
- 形成值为 10 的组；
- 事件顺序允许中间有移动和对齐。

### 9.4 未知合法路径

规则引擎不应因无法命名策略而阻止操作：

- 数学合法则继续；
- `strategy = "unclassified_valid"`；
- 小欧只描述事实，不编造方法名；
- 事件进入匿名测试数据，供后续增加识别器。

---

## 10. 场景状态机

状态机负责节奏，不负责判断数学真假。

### 10.1 arrival

世界：

- 三堆材料 10、10、6；
- 远处桥梁停机；
- 小欧在场但不操作。

进入条件：创建会话。  
离开条件：孩子首次 focus 或 move。  
小欧：最多一句“这些材料有点乱，我们先整理一下？”

### 10.2 organize

世界：

- 孩子可以移动、排齐、合并和拆分；
- 关注对象有轻微呼吸光；
- 不出现算式。

离开条件：

- 孩子形成任意有意义的新分组；
- 或直接开始向桥梁分配。

### 10.3 compose

世界：

- 数量结构自动吸附；
- 值只在结构形成后短暂显现；
- 推导轨迹开始生成。

离开条件：

- 所有 26 个单位形成一个可分配整体；
- 或孩子直接把 26 个单位分配到桥上。

不得强迫先得到单一 `26` 组。

### 10.4 split_bridges

世界：

- 两条桥轨道展开；
- 所有材料仍在现场；
- 桥头随长度产生实际错位；
- 孩子可以来回调整。

离开条件：

- 两桥各 13；
- 规则引擎发出 `BridgesLocked`。

### 10.5 bridge_running

世界：

- 桥梁锁定；
- 小车运行；
- 保留孩子的材料结构与轨迹；
- 不出现结算页。

自动世界事件：

- 运输装置产生一个来源明确的新单位；
- 发出 `WorldUnitAdded`；
- 转入 `odd_variant`。

### 10.6 odd_variant

世界：

- 总量 27；
- 两桥一边 13、一边 14，或仍待分配；
- 桥无法同时锁定；
- 小欧只问“多了一块，现在还能让两边一样吗？”

完成条件：

- 孩子通过操作或语言表达“不行”“会多一个”或等价观察；
- 或尝试所有合理分配后停下观察。

### 10.7 reflection

世界：

- 可回放一条孩子自己的轨迹；
- 小欧镜像方法；
- 不给星级评分。

输出：

- 孩子采用的策略；
- 关键不变量；
- 孩子的原话；
- 是否主动修正；
- 是否尝试第二条路径。

---

## 11. 交互设计

### 11.1 画面

- 横屏优先；
- 固定正交斜俯视；
- 工坊占主要区域；
- 无常驻任务列表；
- 无常驻聊天框；
- 一个角落保留撤销；
- 语音入口只在需要表达时出现；
- 小欧字幕单次尽量不超过一行。

### 11.2 选取和拖拽

- 点击：聚焦一个组；
- 直接拖动组：整组拿起；
- 聚焦后点“拆开把手”：进入拆分，不使用与整组拖动冲突的长按手势；
- 拖动拆分线：选择数量；松手确认；拖回原位或双指/系统返回取消；
- 靠近兼容目标：轻微吸附；
- 放到桥槽：按槽位排布；
- 不合法目标：回弹，不弹框。

触控手势状态机：

```text
idle
  → pointer_down(entity)
  → pending_drag（移动容差 8 px）
  → dragging_group（超过容差）
  → dropped / cancelled

focused_group
  → pointer_down(split_handle)
  → choosing_split
  → split_preview(count)
  → committed / cancelled
```

约束：

- 不用 hover；
- 不用长按同时承担选择、拖拽和拆分；
- `setPointerCapture` 后必须处理 `pointercancel` 和 `lostpointercapture`；
- 页面不可因拖拽滚动或缩放；
- 拆分数量有视觉刻度、单位轮廓和即时预览；
- 手势阈值集中配置并通过真机测试，不散落魔法数字。

### 11.3 组粒度

首期不能要求孩子逐块搬 26 次。

必须支持：

- 整组移动；
- 组内拿出指定数量；
- 十条自动成组；
- 桥上连续槽位自动铺设；
- 按住组后通过可视分割线选择拆出数量。

### 11.4 数学透镜

触发条件：

- 拿起数量组；
- 两组接近；
- 靠近桥梁；
- 对比两条桥。

效果：

- 背景轻微弱化；
- 相关对象轮廓增强；
- 吸附目标显示；
- 数量只在结构形成后出现；
- 相等关系通过桥头对齐表现。

不是一个可点击模式按钮。

### 11.5 撤销

- 每个成功语义命令是一个撤销单元；
- 拖拽中的连续坐标不是多个撤销步骤；
- 小欧动作同样可撤销；
- 世界事件“第 27 块到来”不可被普通撤销，但可在回放中查看；
- 撤销后策略识别与推导图重新计算。

---

## 12. 世界效果协议

规则引擎只产生语义效果描述，渲染层负责动画：

```ts
type WorldEffect = {
  effectId: string;
  afterEffectId?: string;
} & (
  | { type: "snap"; entityIds: string[]; anchor: SemanticAnchor }
  | { type: "return"; entityId: string; anchor: SemanticAnchor }
  | { type: "pulse"; entityIds: string[]; strength: "soft" | "strong" }
  | { type: "show_value"; entityId: string; value: number; durationMs: number }
  | { type: "bridge_tilt"; left: number; right: number }
  | { type: "bridge_lock" }
  | { type: "vehicle_run" }
  | { type: "ghost_path"; proposalId: string; command: WorldCommand }
  | { type: "xiaoou_point"; entityIds: string[] }
);
```

每个 effect 有幂等 `effectId`。渲染层完成动画后回报：

```ts
interface EffectCompleted {
  effectId: string;
  renderedRevision: number;
}
```

它只推进表现层队列，不修改数学状态。刷新后：

- state 是最终事实；
- 未完成 effect 可以从当前 state 重新生成短动画或直接完成；
- 已完成 effect ID 不重复播放；
- 等待动画的系统 transition 通过明确 `afterEffectId` 调度；
- 小车运行和第 27 块到来不得依靠脆弱的 `setTimeout`。

动画门控采用两阶段调度：

1. 普通命令执行并返回 effect；
2. 若 transition 声明 `afterEffectId`，对应 `SystemCommand` 进入
   `pendingSystemCommands`，本轮不执行；
3. `EffectCompleted` 只更新表现层调度器；
4. 调度器随后以新的 `expectedRevision` 提交该 `SystemCommand`；
5. `SystemCommand` 仍完整经过 `applyCommand` 和不变量检查；
6. 同一 effect 完成回报和同一 system command ID 都是幂等的；
7. 刷新恢复时，根据 state 与 pending command 判断重播动画或安全提交，
   不能重复创建第 27 块。

---

## 13. 小欧确定性介入策略

首期先实现无 LLM 的介入状态机，保证产品在模型不可用时仍成立。

### 13.1 输入

```ts
interface InterventionInput {
  phase: WorldState["phase"];
  recentEvents: SemanticEvent[];
  elapsedWithoutMeaningfulEventMs: number;
  repeatedRejectedCommands: number;
  currentFocus: string[];
  recognizedStrategies: StrategyMatch[];
  xiaoouLastActionRevision: number;
}
```

### 13.2 输出

```ts
type Intervention =
  | { kind: "stay_silent" }
  | { kind: "point"; entityIds: string[] }
  | { kind: "half_step"; proposalId: string; preview: ProposalPreview }
  | { kind: "mirror"; mirrorKey: string; evidenceEventIds: string[] }
  | { kind: "ask"; copyKey: string; entityIds: string[] }
  | { kind: "offer_replay"; eventIds: string[] };
```

半步和幽灵方案都不是数学命令：

```ts
interface ProposalPreview {
  entityIds: string[];
  suggestedCommand: WorldCommand;
  visualTarget: SemanticAnchor;
  expiresAtRevision: number;
}
```

- 预览只存在 `InteractionState.proposals`；
- 小欧停在吸附发生前，不改变 owner、group 或 bridge；
- 孩子拖动预览实体表示修改；
- 孩子把实体送入合法目标后，Controller 才提交自己的命令；
- `accept_proposal` 会重新验证 revision 和命令；
- 推开、撤销或产生新 revision 会使旧 proposal 失效。

### 13.3 提示阶梯

1. 无语言环境提示；
2. 指向或对象呼吸光；
3. 小欧做半步；
4. 一个可通过动作回答的问题。

升级条件以“无有意义语义事件”为准，不以鼠标静止为准。

### 13.4 强制限制

- 孩子刚完成有效动作后，先保持安静；
- 小欧不能连续执行两个 `half_step`；
- 小欧不能碰持有 child interaction lease 的实体；
- 小欧不能执行 phase 的完成命令；
- 每次只聚焦一组关系；
- 语言复制只能引用规则引擎和策略识别器提供的事实。

---

## 14. AI 导演

### 14.1 接入顺序

AI 在确定性介入策略稳定后接入。它负责：

- 从允许的介入候选中选一个；
- 将 `mirrorKey` 转成自然短句；
- 从受检参数范围内选择下一轮变体；
- 判断是否值得保持安静。

AI 不负责：

- 判断命令是否合法；
- 计算总量；
- 判断桥是否等长；
- 直接生成 Three.js 坐标；
- 创建任意实体；
- 修改 `WorldState`；
- 决定操作是否“正确”。

### 14.2 AI 输入快照

```json
{
  "scenario": "bridge_26",
  "phase": "compose",
  "revision": 12,
  "groups": [
    {"id": "group_20", "value": 20, "sources": ["ten_a", "ten_b"]},
    {"id": "six", "value": 6, "sources": ["six"]}
  ],
  "bridges": {"left": 0, "right": 0, "locked": false},
  "recent_events": [
    {"type": "groups_merged", "values": [10, 10, 20]}
  ],
  "strategies": ["combine_complete_tens"],
  "allowed_interventions": [
    {"kind": "stay_silent"},
    {"kind": "mirror", "mirrorKey": "found_two_complete_tens"}
  ]
}
```

不发送：

- 原始坐标流；
- 未展示给孩子的“标准答案”；
- 可让模型绕过场景限制的任意工具。

### 14.3 AI 输出

```json
{
  "intent": "mirror",
  "candidate_id": "mirror_found_two_complete_tens",
  "utterance": "你先找到了两个完整的十。",
  "evidence_event_ids": ["evt_012"]
}
```

服务端校验：

- `candidate_id` 必须来自输入候选；
- evidence 必须存在；
- utterance 长度受限；
- 禁止出现“正确、错误、答案是、应该分成 13”；
- 失败时退回模板文案或保持安静。

### 14.4 受检导演工具

```text
director_stay_silent()
director_point(entity_ids)
director_choose_half_step(candidate_id)
director_mirror(strategy_id)
director_ask(copy_key)
```

这些工具只选择系统已经生成的候选，不能携带任意世界补丁。

首个垂直切片不开放通用 `propose_variant`。唯一变体是场景内写死并受检的
`add_27th_block` 系统 transition。未来的 `6、6、10` 等反例必须先成为有
对象来源、规则和测试的 `ScenarioVariantDefinition`，才能进入候选集。

---

## 15. API

### 15.1 创建会话

```http
POST /api/v2/sessions
```

请求：

```json
{"scenario":"bridge_26","supported_scenario_versions":[1],"consent_token":""}
```

响应：

```json
{
  "session_id":"v2_s_...",
  "session_token":"一次显示的高熵 token",
  "scenario_version":1,
  "initial_snapshot":{},
  "initial_state_hash":"...",
  "director_enabled":true
}
```

### 15.2 追加事件

```http
POST /api/v2/sessions/{id}/events
```

请求：

```json
{
  "request_id":"req_...",
  "base_revision":12,
  "scenario_version":1,
  "state_hash":"...",
  "commands":[...],
  "effect_receipts":[...],
  "events":[...]
}
```

后端执行两层校验：

- `request_id` 幂等，重复提交返回第一次结果；
- revision 连续；
- schema 合法且 scenario version 一致；
- hash 链连续；
- 单次事件数量有上限。
- 服务端以已审计 snapshot 为起点，重新执行每个 `CommandEnvelope`；
- 逐命令校验 actor 权限，客户端不得提交 `actor=world`；
- 延迟 SystemCommand 只能由已知 `effect_receipt` 触发，服务端按场景规则自行生成；
- 服务端生成的事件必须与客户端附带 events 逐字段一致；
- 重放结果必须得到相同数学投影 hash；
- 任一失败则事务回滚并返回 `409 invalid_command_log`。

FastAPI 启动一个长驻 Node validator worker，通过逐行 JSON 协议调用
`v2/tools/replay-session.ts` 的构建产物；不能为每个请求重新启动 Node 进程。
worker 不可用时事件写入返回 `503`，客户端保留本地队列，数学世界仍可离线玩，
但不会把未经审计的记录交给 AI 导演。

snapshot 与 events 在一个事务内提交。revision 冲突返回当前 revision 和
最新 snapshot token，客户端必须恢复后重试，不能盲目覆盖。

### 15.3 请求导演决策

```http
POST /api/v2/sessions/{id}/director
```

请求是压缩后的语义快照。响应为受检 `DirectorIntent`。

请求携带：

- `base_revision`；
- `state_hash`；
- `candidate_set_id`；
- 客户端观察到的候选列表（只用于诊断）。

服务端不能信任客户端快照或候选。它必须从已审计 session snapshot 调用同一
TypeScript 确定性介入策略重新生成候选，保存短期
`candidate_set_id + revision + state_hash`，再交给 LLM 选择。

响应必须回传这三个字段。执行前客户端重新检查：

- revision 未变化；
- candidate 仍存在；
- evidence 未被撤销；
- entity 未被锁定或占用。

任一不满足即静默丢弃旧响应，必要时重新请求，不能在新世界状态上套用旧建议。

### 15.4 会话恢复

```http
GET /api/v2/sessions/{id}
```

返回最近 snapshot 和其后的事件。客户端通过 reducer 重建状态。

### 15.5 导出回放

```http
GET /api/v2/sessions/{id}/replay
```

只导出语义事件和场景版本，不导出儿童录音。

### 15.6 会话访问控制

- 创建会话仍需通过共享门禁；
- 响应返回 256-bit `session_token`，浏览器存入 sessionStorage，不写 URL；
- 后续读写使用 `Authorization: Bearer <session_token>`；
- 服务端只保存 token hash；
- 恢复、导出和删除都要求 token；
- 家长在已解锁门禁下可显式轮换 token；
- token 不跨 V1/V2 使用，不作为 telemetry ID；
- 删除会话后 token 立即失效。

---

## 16. 持久化与隐私

### 16.1 Event sourcing

- 语义事件为主记录；
- 每 20 个事件或 phase 切换保存 snapshot；
- snapshot 包含 state hash；
- 恢复时重放后续事件；
- 场景规则必须带版本号。

`state_hash` 默认只覆盖数学投影：units、owner、groups、bridges、phase 和
derivation，不覆盖 revision、history、redo、动画及导演状态。因此：

- 普通命令后数学 hash 改变；
- undo 后数学 hash 等于被撤销命令之前；
- event log hash 仍是追加式，`UndoApplied` 不删除历史；
- replay reducer 根据 `UndoApplied/RedoApplied.targetTransactionId` 恢复数学投影。

### 16.2 录音

- 默认只在内存中完成 ASR；
- 不持久化原始录音；
- 只保留识别后的文字；
- 儿童测试若需录音，必须通过独立家长同意开关。

数据生命周期：

- `child_name` 不进入 V2 API；
- 默认会话使用匿名随机 ID；
- 识别文字与事件保留 30 天后自动删除；
- 家长可通过会话管理页立即删除；
- consent token 只记录同意范围与版本，不包含姓名；
- 导出和读取会话必须通过与门禁绑定的会话密钥；
- telemetry 与可恢复会话分库存储，不能通过匿名 ID反查；
- 儿童测试结束后按研究同意书执行更短保留策略。

### 16.3 匿名指标

```ts
interface V2TelemetryEvent {
  sessionAnonId: string;
  scenarioVersion: number;
  type:
    | "first_meaningful_action"
    | "self_correction"
    | "strategy_recognized"
    | "hint_level_used"
    | "bridge_locked"
    | "odd_variant_observed"
    | "session_abandoned";
  revision: number;
  payload: Record<string, number | string | boolean>;
}
```

不得记录：

- 姓名；
- 完整 IP；
- 原始语音；
- 自由聊天全文；
- 可识别孩子身份的图片。

---

## 17. 内容定义格式

场景必须数据驱动，但首期不做通用可视化编辑器。

```ts
interface ScenarioDefinition {
  id: "bridge_26";
  version: 1;
  initialWorld: InitialWorldDefinition;
  allowedCommandsByPhase: Record<string, WorldCommand["type"][]>;
  invariants: InvariantId[];
  devices: DeviceDefinition[];
  transitions: TransitionRule[];
  strategyDetectors: StrategyDetectorId[];
  interventionPolicy: InterventionPolicyDefinition;
  copy: Record<string, string>;
}
```

新增场景不得通过 prompt 手写数学规则，必须：

1. 定义对象；
2. 定义合法命令；
3. 定义不变量；
4. 定义装置条件；
5. 定义 phase transition；
6. 定义策略识别；
7. 编写属性测试和至少三条完整路径。

---

## 18. 性能预算

首期目标设备：近年的平板和桌面浏览器。

- 首屏压缩资源不超过 4 MB，不含按需音频；
- 同屏可交互体素不超过 200；
- 稳态目标 60 FPS，低端设备不得持续低于 30 FPS；
- pointer 到拖拽反馈小于一帧；
- 数学命令执行为同步纯函数，通常小于 5 ms；
- 小欧 AI 延迟不能阻塞世界操作；
- AI 未返回时孩子仍可继续操作；
- 场景内存预算 250 MB；
- 纹理优先使用图集和程序化材质；
- 单位块使用 `InstancedMesh`。

---

## 19. 可访问性与输入方式

- 鼠标与触控都必须支持；
- 精确拖动目标至少 44 px；
- 不依赖颜色作为唯一反馈；
- 数量结构同时使用位置、轮廓和轻微声音；
- 支持关闭动画与声音；
- 支持键盘选择、移动、撤销的开发模式；
- 文本和语音不是完成数学操作的必要条件；
- 语音石为可选输入，不是关卡门槛。

---

## 20. 测试策略

### 20.1 领域单元测试

覆盖每种命令：

- 合并成功/失败；
- 拆分边界；
- 单位重复拒绝；
- 锁定对象拒绝；
- bridge slot 占用；
- revision 冲突；
- undo/redo；
- phase 权限。

### 20.2 属性测试

使用 fast-check 生成随机合法命令序列：

```text
对任意成功命令序列：
- UnitId 永不重复；
- 除 add_27th_block 外总量不变；
- undo 后状态 hash 等于命令前；
- merge 后集合并集不变；
- split 后两集合互斥且并集不变；
- locked bridge 必定等长；
- replay(events) 得到同一 state hash。
```

### 20.3 场景黄金路径

每条路径都从初始状态运行到 `odd_variant`：

1. `10 + 10 → 20; 20 + 6 → 26; 13 + 13`
2. `6 + 10 → 16; 16 + 10 → 26; 13 + 13`
3. `ten_a(10) → remainder_a(6) + taken_a(4); original_six(6) + taken_a(4) → 10; ...; 13 + 13`

额外测试：

- 直接向桥上分配而不先合并为 26；
- 12 + 14 后自主调整为 13 + 13；
- 多次拆分与重组；
- 无法分类但数学合法的路径；
- 第 27 块后遍历所有分配都不能锁定。

### 20.4 策略识别测试

- 中间插入移动事件仍能识别；
- 撤销后不保留已撤销策略；
- 相同结果不同过程不被误判为同一策略；
- 未知路径不编造策略名。

### 20.5 导演测试

- 小欧不连续做两个半步；
- 小欧不执行最后一步；
- 孩子有新动作后导演保持安静；
- AI 返回非法 candidate 时拒绝；
- AI 超时不阻塞操作；
- 文案不出现答案、正确/错误评判；
- 世界变化必须再次通过规则引擎。

### 20.6 浏览器 E2E

- 横屏平板视口；
- 触控拖拽；
- 整组移动；
- 分割组；
- 吸附；
- 桥头反馈；
- 撤销；
- 刷新恢复；
- 离线/AI 故障；
- 低帧率模式；
- 语音权限拒绝。

### 20.7 视觉回归

固定相机与随机种子，保存：

- 初始工坊；
- 两个十吸附；
- 20 + 6；
- 12/14 不等长桥；
- 13/13 锁定桥；
- 27 奇数局面；
- 小欧半步和幽灵方案。

---

## 21. 儿童测试脚本

测试人员不解释数学目标，只说：

> “这是一个还没运行起来的工坊，你看看想做什么。”

记录：

1. 第一次有意义操作前发生了什么；
2. 是否先读字还是先碰对象；
3. 是否理解整组移动；
4. 是否根据吸附改变动作；
5. 遇到 12/14 时是否主动调整；
6. 小欧第一次介入发生在哪；
7. 小欧做半步后是否自然接手；
8. 是否尝试第二条方法；
9. 第 27 块出现后的第一反应；
10. 是否能用自己的话描述一个方法。

测试后访谈只问开放问题：

- “刚才桥为什么动了？”
- “你是怎么整理这些方块的？”
- “为什么最后这块放哪边都不一样？”
- “如果重新来一次，你还会这么做吗？”

不问：

- “你学会加法结合律了吗？”
- “26 是奇数还是偶数？”
- “正确答案是什么？”

---

## 22. 实施切片

每个切片必须独立可运行，并通过退出门槛后再进入下一个。

### Slice 0：交互技术探针

**目标：** 验证低龄儿童是否能在固定斜俯视中拿起、整组移动、拆分和放置。

**只做：**

- 正交相机；
- 26 个实例化方块；
- 三个组；
- 桌面和触控 picking；
- 整组拖拽；
- 简单拆分；
- 桥槽吸附；
- 无 AI、无小欧、无算式。

**文件：**

- 创建 `v2/package.json`、Vite 与测试骨架；
- 创建最小、仅供探针使用的 `InteractionPrototypeState`；
- 创建 `v2/apps/web/src/scene/*`
- 不在本切片决定正式数学领域 schema。

**退出门槛：**

- 平板触控稳定；
- 不误触相机；
- 孩子无需文字能移动一整组；
- 26 块不需要逐块搬运；
- 4×4 以上目标区域仍容易命中。

失败时优先改输入方式，不进入 AI 开发。

### Slice 1：数学领域内核

**目标：** 无渲染、无 AI 地完成确定性规则。

**任务：**

1. 定义 Unit、Group、Bridge、WorldState；
2. 定义命令与事件；
3. 实现 `applyCommand`；
4. 实现所有不变量；
5. 实现 state hash；
6. 实现 undo/redo；
7. 实现 replay；
8. 编写属性测试。

**退出门槛：**

- 10,000 组随机命令序列不破坏不变量；
- 三条黄金路径通过；
- replay hash 稳定；
- 规则包不依赖浏览器和 AI。

### Slice 2：规则驱动的桥梁工坊

**目标：** 渲染只订阅数学状态和 effects。

**任务：**

1. 构建工坊场景；
2. 将 Three.js 对象绑定 entity ID；
3. 拖拽生成命令；
4. 成功结果播放 snap/merge 动画；
5. 失败结果回弹；
6. 两桥长度驱动桥头位置；
7. 锁定后运行小车；
8. 加入撤销。

**退出门槛：**

- 渲染层无直接 state mutation；
- 12/14、13/13 的世界反馈一眼可区分；
- 动画中断后可从 state 重建；
- 从内存中的 state snapshot 重建画面不产生重复单位。

### Slice 3：状态机与连续世界

**目标：** 完整运行 26 到 27，不出现结算页。

**任务：**

1. 实现七个 phase；
2. phase 只限制当下可用动作，不规定标准顺序；
3. 结构形成后生长数值；
4. 生成第 27 块的来源和动画；
5. 27 局面保持可操作；
6. 建立 scenario version。

**退出门槛：**

- 三条策略均能到达 27；
- 可以跳过“先组成一个 26”；
- 27 只通过受检世界事件出现；
- 不重新加载页面。

### Slice 4：语义轨迹与策略识别

**目标：** 系统理解过程，不只理解结果。

**任务：**

1. 语义事件归一化；
2. 推导图；
3. 三条策略识别器；
4. 未分类合法路径；
5. 轨迹回放；
6. 动作到算式；
7. 撤销后重新推导。

**退出门槛：**

- 三种路径生成不同镜像结果；
- 相同最终 26 不覆盖过程差异；
- 回放不依赖原始坐标；
- 算式中的每一步都有事件证据。

### Slice 5：无 AI 小欧

**目标：** 用确定性策略验证共同玩家是否有价值。

**任务：**

1. 小欧实体；
2. 指向；
3. 半步；
4. 幽灵方案；
5. 模板化方法镜像；
6. 三层提示；
7. 小欧规则层限制。

确定性介入先实现为
`v2/packages/bridge-26/src/intervention.ts` 纯 TypeScript，不依赖 V2 API，
也不在 Python 重写数学规则。Slice 6 的 FastAPI 只负责 AI 候选选择。

**退出门槛：**

- 去掉小欧后，测试者能感知体验差异；
- 小欧不抢操作；
- 小欧半步后孩子自然接手；
- 小欧不会完成最后一步；
- 模型断网不影响本切片。

### Slice 6：AI 导演

**目标：** AI 提升介入自然度，不改变数学可靠性。

**任务：**

1. FastAPI V2 路由；
2. DirectorIntent schema；
3. 候选生成；
4. 模型选择候选；
5. 文案约束与过滤；
6. 超时和非法输出回退；
7. 事件持久化；
8. SSE/异步导演响应。

**退出门槛：**

- AI 无法提出候选之外的世界动作；
- 非法输出 100% 被拒绝；
- AI 断开时体验可继续；
- 小欧语言比模板更自然但不更啰嗦；
- 不出现数学事实错误。

### Slice 7：语音石与思考报告

**目标：** 语音只补充孩子表达，不成为推进门槛。

**任务：**

1. 接入现有 SenseVoice；
2. 语音石按住说话；
3. 识别文字可清空和编辑；
4. 孩子原话与策略证据关联；
5. 家长侧只显示方法和尝试，不做分数评价；
6. 原始录音默认不落盘。

**退出门槛：**

- 不说话也能完成整个场景；
- ASR 错误不改变数学状态；
- 孩子原话不会被改写成系统结论；
- 家长报告可追溯到语义事件。

---

## 23. 首批任务清单

### Task 1：建立 V2 workspace

**文件：**

- `v2/package.json`
- `v2/tsconfig.json`
- `v2/vite.config.ts`
- `v2/apps/web/index.html`
- `v2/apps/web/src/main.ts`

**验收：**

- `npm run dev` 打开 `/v2/`；
- `npm test` 可运行纯 TypeScript 测试；
- V1 无任何资产和样式变化。

### Task 1A：交互技术探针

**文件：**

- `v2/apps/web/src/scene/renderer.ts`
- `v2/apps/web/src/scene/camera.ts`
- `v2/apps/web/src/scene/picking.ts`
- `v2/apps/web/src/scene/drag.ts`

**验收：**

- 不通过文本按钮完成整组移动；
- 拆分把手与整组拖动无手势冲突；
- pointer cancel 不丢对象；
- 触控不滚动页面；
- 固定镜头能看清两桥和材料区。

Task 1A 通过后才冻结正式领域交互命令；原 Task 6 合并进本任务，不再重复。

### Task 2：领域 schema

**文件：**

- `v2/packages/domain/src/types.ts`
- `v2/packages/domain/src/commands.ts`
- `v2/packages/domain/src/events.ts`
- `v2/tests/fixtures/bridge-26-initial.ts`

**验收：**

- 初始 fixture 精确包含 26 个唯一单位；
- 10、10、6 来源可追溯；
- schema 可 JSON 序列化。

### Task 3：不变量先行

**文件：**

- `v2/packages/domain/src/invariants.ts`
- `v2/tests/properties/invariants.test.ts`

**验收：**

- 手工构造重复单位、缺失来源、不等长锁定均被拒绝；
- 属性测试运行。

### Task 4：命令引擎

**文件：**

- `v2/packages/domain/src/engine.ts`
- `v2/packages/domain/src/replay.ts`
- `v2/packages/domain/src/hash.ts`

**验收：**

- merge/split/transfer/place/undo/redo；
- 每次成功命令产生语义事件；
- 失败保持原 state hash。

### Task 5：26 号场景规则

**文件：**

- `v2/packages/bridge-26/src/scenario.ts`
- `v2/packages/bridge-26/src/phases.ts`
- `v2/packages/bridge-26/src/transitions.ts`
- `v2/tests/scenarios/bridge-26-paths.test.ts`

**验收：**

- 三条路径与直接上桥路径通过；
- 13/13 锁定；
- 12/14 不锁定；
- 第 27 块后不能锁定。

### Task 6：Three.js 正式场景接入

**文件：**

- `v2/apps/web/src/scene/renderer.ts`
- `v2/apps/web/src/scene/camera.ts`
- `v2/apps/web/src/scene/picking.ts`
- `v2/apps/web/src/scene/drag.ts`

**验收：**

- 使用 Task 1A 已验证手势；
- 每个可交互 Mesh 绑定 entity ID；
- 手势只生成 CommandEnvelope；
- 正式场景不再使用 prototype state。

### Task 7：Controller 隔离

**文件：**

- `v2/apps/web/src/controller/world-controller.ts`

**验收：**

- 所有拖拽最终只 dispatch 命令；
- Three.js 对象没有数学真值字段；
- state 重建可恢复完整画面。

### Task 8：桥梁装置

**文件：**

- `v2/packages/bridge-26/src/devices.ts`
- `v2/apps/web/src/scene/animations.ts`

**验收：**

- 长度差驱动真实桥头错位；
- 锁定动画只响应 `BridgesLocked`；
- 小车只响应 `VehicleStarted`。

### Task 9：推导和策略

**文件：**

- `v2/packages/domain/src/derivation.ts`
- `v2/packages/bridge-26/src/strategy.ts`

**验收：**

- 事件可生成三条不同推导；
- 未知路径仍继续；
- undo 后证据同步消失。

### Task 10：确定性小欧

**文件：**

- `v2/packages/bridge-26/src/intervention.ts`
- `v2/apps/web/src/controller/director-controller.ts`
- `v2/packages/bridge-26/src/copy.ts`

**验收：**

- 无模型运行；
- 提示阶梯正确；
- 行为协议有自动测试。

### Task 11：AI 导演

**文件：**

- `server/v2/director_contract.py`
- `server/v2/director.py`
- `server/v2/prompts.py`
- `server/v2/api.py`
- `tests/test_v2_director.py`

**验收：**

- 只选候选；
- 失败回退；
- 数学状态不在模型输出中；
- V1 API 不变。

### Task 12：会话与回放

**文件：**

- `server/v2/persistence.py`
- `v2/apps/web/src/controller/session-controller.ts`
- `tests/test_v2_persistence.py`

**验收：**

- 刷新恢复；
- hash 链校验；
- schema version 迁移入口；
- 可导出匿名语义回放。

---

## 24. 发布门禁

V2 不能仅因“能运行”就向儿童开放。必须依次通过：

### Gate A：数学正确

- 属性测试通过；
- 黄金路径通过；
- 不变量无例外；
- AI 关闭仍正确。

### Gate B：操作可懂

- 首次测试者无需口头说明能移动材料；
- 整组、拆分、放桥均可发现；
- 误操作可恢复；
- 观察者能区分数学卡住和控制卡住。

### Gate C：世界反馈成立

- 去文字测试通过；
- 12/14 与 13/13 的差别不依赖字幕；
- 第 27 块制造的新矛盾可被看见。

### Gate D：小欧不夺权

- 小欧介入次数足够少；
- 半步不完成关键步骤；
- 孩子可以拒绝幽灵方案；
- 小欧描述有事件证据。

### Gate E：真实儿童验证

- 至少出现自主修正；
- 至少有孩子尝试非演示路径；
- 至少有孩子能描述自己的方法；
- 若多数孩子只玩拖拽而未观察关系，停止扩场景，先修数学因果。

---

## 25. 主要风险与工程对策

### 风险：体素外观掩盖数学

对策：

- 固定箱庭；
- 数学对象视觉一致；
- 不做收集与装饰奖励；
- 每个动画必须对应语义事件；
- 执行替换测试。

### 风险：3D 操作比数学难

对策：

- 正交相机；
- 自动吸附；
- 大命中区域；
- 整组操作；
- Slice 0 先测控制，不先写 AI。

### 风险：只支持三条脚本路径

对策：

- 规则引擎接受任意合法单位分区；
- 策略识别失败不阻断；
- 将未知合法路径纳入测试语料。

### 风险：规则和渲染不一致

对策：

- 单向数据流；
- 渲染只消费 state/effects；
- 动画结束不产生数学事实；
- state hash 重建视觉回归。

### 风险：AI 重新变成老师

对策：

- 候选式输出；
- 默认 `stay_silent`；
- 行为限制放规则层；
- 单句长度限制；
- 介入有语义证据。

### 风险：行动轨迹无法解释

对策：

- 原始交互与语义事件分层；
- 用单位分区归一化；
- 每个算式边必须引用事件；
- 无法解释时不生成策略名称。

### 风险：第 26 到 27 的剧情是硬编码表演

对策：

- 第 27 块必须有 source；
- 通过受检 `WorldUnitAdded`；
- 27 后仍使用同一分配和桥梁规则；
- 不为剧情修改等长规则。

---

## 26. 尚需产品确认的决策

这些问题不阻塞领域内核，但必须在视觉切片前决定：

1. 小欧首期是体素角色、光球还是机械助手；
2. 桥梁为何必须两边等长的世界因果如何表现；
3. 两条桥是并行承重轨、双车同步轨，还是桥的左右两侧；
4. 第 27 块从哪里来，是否会让孩子误以为可无限取材料；
5. 语音石在完成操作前是否出现；
6. 数值浮现的时机和持续时间；
7. 孩子是否可直接拆十条，还是先学习整组；
8. 场景是否需要轻量角色行走，或完全采用直接操控；
9. 家长报告是否属于首个公开版本；
10. 现有“体素原型”是否在另一个仓库，技术栈是什么。

其中第 2 项必须先制作动效原型验证。若孩子无法仅凭世界理解“两边等长才能运行”，桥梁主题需要调整，不能用字幕补救机制本身。

---

## 27. 开工顺序

严格按以下顺序：

1. 冻结 V1；
2. 找到并审计现有体素原型（若存在）；
3. 完成 Slice 0 交互探针；
4. 与儿童或非项目成员做无文字操作测试；
5. 完成 TypeScript 领域模型和不变量；
6. 运行三条黄金路径与属性测试；
7. 将规则接入体素渲染；
8. 完成 26 → 27 连续世界；
9. 完成语义轨迹和策略识别；
10. 先上确定性小欧；
11. 完成共同玩家测试；
12. 最后接 AI 导演；
13. AI 稳定后再接语音和家长报告；
14. 首个微世界通过发布门禁后，才规划第二个世界。

不得并行铺开多个数学微世界，也不得先建设开放地图。

---

## 28. 最终验收场景

一个从未见过产品的孩子进入工坊：

1. 看见 10、10、6 三堆材料和未运行的装置；
2. 不读说明也愿意触碰材料；
3. 用任一合法方法重新组合；
4. 世界真实地表现数量结构；
5. 小欧只在必要时指向或做半步；
6. 孩子亲手完成关键合并；
7. 两桥因 12/14 不对齐；
8. 孩子调整为 13/13；
9. 桥锁定，小车运行；
10. 第 27 块进入同一世界；
11. 孩子发现无法让两边完全一样；
12. 系统能回放她自己的方法，而不是展示标准答案；
13. 小欧用一句有证据的话镜像她的策略；
14. 整个过程没有答题框、红叉、结算页或 AI 数学裁决。

达到这一点，V2 的核心假设才算被验证。

