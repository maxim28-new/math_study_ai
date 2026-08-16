# 语义画板 v2 实施计划

日期：2026-08-15  
状态：实施中  
目标：题目、教学动作和画板共享同一个数学模型；错误图宁可不显示，也不靠关键词猜图。

## 1. 问题

当前 `xiaoou-draw` 让模型直接选择 `dots`、`stairs`、`bars` 等渲染类型。它把三件事耦合在一起：

1. 题目研究的数学对象；
2. 当前教学步骤想让孩子做什么；
3. 最终用什么技术画出来。

因此“罐子按层累加”和“青蛙跳台阶”都可能命中 `stairs`。关键词补丁只能改变误画方向，不能判断数学语义。

## 2. 决策

新增版本化的语义画板协议：

```text
作者题卡
  → semantic_board（数学语义）
  → 确定性编译与校验
  → 专用组件
      ├─ HTML/CSS
      ├─ Konva/Canvas
      └─ 少量 SVG（仅适合矢量路径的静态图）
```

- 模型不能输出 DOM、Canvas、Konva 或 SVG 代码。
- 渲染技术不是题卡字段，由前端组件注册表决定。
- `diagram` 仅用于旧卡兼容；新语义卡优先使用 `semantic_board`。
- 删除“看到台阶/小山就强制改图”的服务端和前端逻辑。
- 语义无效或组件不支持时显示无图安全状态，不退回猜测图。

## 3. 协议 v2

公共字段：

```json
{
  "schema": 2,
  "kind": "layer_sum | path_count",
  "purpose": "explore",
  "reveal": "..."
}
```

### `layer_sum`

```json
{
  "schema": 2,
  "kind": "layer_sum",
  "layers": [1, 2, 3, 4, 5],
  "item": "罐",
  "ask": "total",
  "purpose": "count_layers",
  "reveal": "items_without_total"
}
```

不变量：

- 1–10 层，每层 1–20 个对象；
- `ask` 第一版只允许 `total`；
- 画出所有对象但不写总数；
- 由 `LayerPileBoard`（DOM/CSS）渲染。

### `path_count`

```json
{
  "schema": 2,
  "kind": "path_count",
  "start": 0,
  "target": 2,
  "moves": [1, 2],
  "ask": "number_of_paths",
  "purpose": "explore_choices",
  "reveal": "rules_only"
}
```

不变量：

- `start < target`，跨度最多 12；
- `moves` 为去重后的正整数，且不能超过跨度；
- 初始只显示状态和允许跳法，不预画全部路线；
- 孩子可按允许步长操作，已找到的路线才被记录；
- 由 `PathBoard`（Konva + DOM 控件）渲染。

## 4. 服务端

新增 `server/board.py`：

- `normalize_semantic_board(raw)`：按判别联合清洗；
- `validate_semantic_board(board)`：检查数值和揭示策略；
- 未知 `kind`、额外危险取值或不完整数据返回 `None`。

更新作者卡：

- 作者提示词明确数学语义与渲染类型的区别；
- 对分层物体题使用 `layer_sum`；
- 对走法/路径数题使用 `path_count`；
- 不适用时 `semantic_board` 为 `null`，继续使用现有受支持图；
- 标准化后有语义画板时以它为准，清空 `diagram`；
- 题卡 guidance 把语义模型交给陪练，并禁止陪练另选图形类型。

## 5. 前端

新增：

- `web/board/state.js`：协议解析、占位 DOM 和公共句柄；
- `web/board/layer-pile.js`：DOM/CSS 分层物体组件；
- `web/board/path-board.js`：Konva 路径组件。

统一句柄：

```js
{
  destroy(),
  freeze(),
  getSnapshot(),
  apply(action)
}
```

`mountFromCard()` 优先挂载语义画板。现有静态 SVG 和吸附格子只作为旧卡路径。

## 6. 教学动作

第一版只允许组件内部产生确定性状态：

- `layer_sum`：观察和数数，不显示答案；
- `path_count`：执行 `move(n)`、重置当前路线、记录到达目标的路线。

组件将盘面快照以系统说明附在孩子下一条消息后，陪练可据此追问。模型不能直接改写底层场景。

后续版本再加入受限的 `semantic-board-action` 工具，让陪练只调用题卡允许的动作。

## 7. 安全与测试

- Python：协议清洗、边界、不支持类型、作者卡优先级、无关键词强转。
- Node：协议解析和路径状态机。
- 前端回归：三类脚本加载顺序、DOM/Konva 组件注册、旧图兼容。
- 手机：至少覆盖 360×640、393×852、430×932 的截图回归。
- 语义校验失败：不画图；不得回退为 `dots` 或 `stairs`。

## 8. 本次交付边界

本次完成协议骨架、`layer_sum`、`path_count`、作者/陪练接线和旧关键词补丁删除。其余数学模型在相同协议上逐个增加，不再扩展万能绘图器。
