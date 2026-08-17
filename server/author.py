"""出题作者：强模型先写出一张题卡，小欧再按卡陪练。"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import httpx

from . import config as teaching_config
from . import board as semantic_board
from .config import settings
from . import tutor

AUTHOR_ENGINES = ("deepseek", "glm")

LADDER_RUNGS = ("do", "see", "why")
REPRESENTATIONS = {"board_v3"}
GENERATED_SEED_PATH = Path(__file__).resolve().parents[1] / "data" / "seed_catalog.json"

AUTHOR_PROMPT = """你是小欧的「出题作者」，不是老师。孩子看不到你。你只输出一张 JSON 题卡，不要讲解、不要 Markdown 前言。

# 目标
出一道有意思、有深度的探索题。
- 有意思：能动手或能猜，故事具体，答案不能一眼看完。
- 有深度：同一道理有三层台阶——手上（做）、眼里（看出规律）、嘴里（说出为什么并接到一条公理）。
- 换主题必须换学具和故事。除非道理就是「连续奇数相加得平方数」，否则禁止用「9 块摆正方形」当第一问。

# 本堂课
- 主题：{topic_name}（key={topic_key}）
- 难度：{level_desc}
- 本主题公理：
{axioms_block}
- 出题灵感（只取精神，不要讲历史）：
{inspirations_block}
- 最近出过、请避开的钩子：{recent_block}

# 数学画板 V3
题卡必须给出一个 board。你只描述数学模型、孩子任务和揭示方式，绝不能发明 type、steps、
SVG、Canvas、Konva、坐标或画图代码。

board 只允许下面六种严格结构，字段名和值都不要改：
1. 分层求和：
{{"schema":3,"kind":"layer_sum","model":{{"layers":[1,2,3,4],"item":"罐"}},"task":{{"action":"count","ask":"total","prompt":"数一数每层，再想一共多少罐。"}},"view":{{"reveal":"items_without_total"}}}}
2. 枚举走法：
{{"schema":3,"kind":"path_count","model":{{"start":0,"target":4,"moves":[1,2]}},"task":{{"action":"enumerate","ask":"number_of_paths","prompt":"试着走到第4级，找出不同走法。"}},"view":{{"reveal":"rules_only"}}}}
3. 拖方块：
{{"schema":3,"kind":"snap_grid","model":{{"rows":2,"cols":3,"tray":6}},"task":{{"action":"arrange","ask":"observe","prompt":"把6块放进格子，看看会变成什么。"}},"view":{{"reveal":"empty_grid_and_tiles"}}}}
4. 受控静态数学图：
{{"schema":3,"kind":"static_diagram","model":{{"diagram":{{"type":"numberline","from":0,"to":10,"marks":[3,7],"caption":"3和7在数轴上"}}}},"task":{{"action":"observe","ask":"notice","prompt":"观察两个数的位置，你发现什么？"}},"view":{{"reveal":"model_only"}}}}
静态 diagram.type 只能是 dots、stairs、square_layers、square_steps、square_compare、numberline、bars。
5. 尺规作正三角形（只适用于研究两圆交点和三边相等）：
{{"schema":3,"kind":"geometry_compass","model":{{"construction":"equilateral_triangle","labels":["A","B","P"]}},"task":{{"action":"construct","ask":"compare_three_sides","prompt":"按顺序画两个圆，再比较三条边。"}},"view":{{"reveal":"stepwise"}}}}
6. 颜色规律排队：
{{"schema":3,"kind":"color_sequence","model":{{"item":"花","unit":["red","red","blue"],"count":6}},"task":{{"action":"predict","ask":"color_at_end","prompt":"按规律想下一朵的颜色。"}},"view":{{"reveal":"hide_last"}}}}
颜色只能是 red、blue、yellow、green、orange、purple。

按题意选择：
- 分层物体合计用 layer_sum；连续奇数 1、3、5 围成正方形时，view.reveal 必须是 stepwise。
- 允许步长的走法用 path_count。
- 需要孩子摆方块用 snap_grid。
- 数轴、线段图、点阵和正方形变化用 static_diagram。
- 几何主题优先出“两圆交点作正三角形”，使用 geometry_compass。
- 找规律、按颜色重复排队必须用 color_sequence，禁止用单色 dots 代替花朵或珠子。
- 不允许 board=null，不允许输出旧 semantic_board 或 diagram 顶层字段。
- board 必须描述第一问的同一个规模；程序会按已校验 board 统一第一问。

# 只输出这个 JSON
{{
  "topic": "{topic_key}",
  "hook": "一句具体情景",
  "insight": "孩子最后要自己发现的那一个道理",
  "axiom": "对准的一条公理",
  "board": {{"schema":3,"kind":"...","model":{{}},"task":{{}},"view":{{}}}},
  "first_question": "只有一句，口语，不泄底",
  "ladder": [
    {{"rung":"do","ask":"手上这一层问什么"}},
    {{"rung":"see","ask":"眼里这一层问什么"}},
    {{"rung":"why","ask":"嘴里这一层问什么"}}
  ],
  "misconceptions": ["孩子可能怎么误会"]
}}
"""


def extract_json_object(text: str) -> dict[str, Any] | None:
    raw = (text or "").strip()
    if not raw:
        return None
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
    if fence:
        raw = fence.group(1).strip()
    start = raw.find("{")
    end = raw.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        data = json.loads(raw[start : end + 1])
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def is_nine_square(card: dict[str, Any]) -> bool:
    board = card.get("board") if isinstance(card.get("board"), dict) else {}
    if board.get("kind") != "snap_grid":
        return False
    model = board.get("model") if isinstance(board.get("model"), dict) else {}
    try:
        cols = int(model.get("cols") or 0)
        rows = int(model.get("rows") or 0)
        tray = int(model.get("tray") or 0)
    except (TypeError, ValueError):
        return False
    return cols == 3 and rows == 3 and tray == 9


def _allows_nine_square(card: dict[str, Any], topic: str) -> bool:
    if topic != "arithmetic":
        return False
    blob = " ".join(
        str(card.get(k) or "") for k in ("insight", "hook", "first_question", "axiom")
    )
    return any(token in blob for token in ("平方", "奇数", "包一圈"))


def validate_card(card: dict[str, Any], topic: str) -> str | None:
    if not card or card.get("topic") != topic:
        return "题卡主题不对"
    if not str(card.get("first_question") or "").strip():
        return "没有第一问"
    if not str(card.get("insight") or "").strip():
        return "没有要发现的道理"
    ladder = card.get("ladder")
    if not isinstance(ladder, list) or len(ladder) < 3:
        return "台阶不够三层"
    if card.get("representation") != "board_v3":
        return "题卡没有使用 V3 画板"
    board = card.get("board")
    if semantic_board.validate_board_v3(board):
        return "V3 画板不合格"
    if card.get("semantic_board") is not None or card.get("diagram") is not None:
        return "V3 题卡不能混用旧画板字段"
    if is_nine_square(card) and not _allows_nine_square(card, topic):
        return "不要用 9 块摆正方形当第一问"
    return None


def normalize_card(data: dict[str, Any] | None, topic: str) -> dict[str, Any] | None:
    if not isinstance(data, dict):
        return None
    ladder_in = data.get("ladder")
    ladder: list[dict[str, str]] = []
    if isinstance(ladder_in, list):
        for i, row in enumerate(ladder_in[:3]):
            if isinstance(row, dict):
                ladder.append(
                    {
                        "rung": str(row.get("rung") or LADDER_RUNGS[i]),
                        "ask": str(row.get("ask") or "").strip(),
                    }
                )
    raw_board = data.get("board")
    if raw_board is not None:
        board = semantic_board.normalize_board_v3(raw_board)
    else:
        board = semantic_board.board_v3_from_legacy(
            data.get("semantic_board"),
            str(data.get("representation") or "none").strip(),
            data.get("diagram"),
            str(data.get("first_question") or "").strip(),
        )
    if board is None:
        return None
    board = semantic_board.upgrade_legacy_pattern_board(board)
    first_question = semantic_board.first_question_for_v3(board)
    if not first_question:
        first_question = str(data.get("first_question") or "").strip()
    card = {
        "topic": str(data.get("topic") or topic).strip() or topic,
        "hook": str(data.get("hook") or "").strip(),
        "insight": str(data.get("insight") or "").strip(),
        "axiom": str(data.get("axiom") or "").strip(),
        "representation": "board_v3",
        "board": board,
        "semantic_board": None,
        "diagram": None,
        "first_question": first_question,
        "ladder": ladder,
        "misconceptions": [
            str(x).strip()
            for x in (data.get("misconceptions") or [])
            if str(x).strip()
        ][:4],
    }
    if validate_card(card, topic):
        return None
    return card


SEED_VARIANTS: dict[str, list[dict[str, Any]]] = {
    "arithmetic": [
        {
            "hook": "一圈一圈围成正方形",
            "insight": "连续奇数一层一层加在外面，会围成越来越大的正方形",
            "axiom": "把两堆合在一起数，就是加法；无论先数哪一堆，结果都一样。",
            "board": {
                "schema": 3,
                "kind": "layer_sum",
                "model": {"layers": [1, 3, 5], "item": "积木"},
                "task": {
                    "action": "count",
                    "ask": "total",
                    "prompt": "一层一层往外加，看看会不会围成正方形。",
                },
                "view": {"reveal": "stepwise"},
            },
            "ladder": [
                {"rung": "do", "ask": "先数最中间有几块。"},
                {"rung": "see", "ask": "外面加上 3 块以后，是不是正方形？每边几块？"},
                {"rung": "why", "ask": "再加一圈 5 块，为什么还是正方形？"},
            ],
            "misconceptions": ["把 1、3、5 一次性倒成一座塔，而不是一圈一圈围"],
        },
        {
            "hook": "罐子小山一层一层往下加",
            "insight": "每一层都比上一层多 1，把看见的层加起来就是总数",
            "axiom": "把两堆合在一起数，就是加法；无论先数哪一堆，结果都一样。",
            "board": {
                "schema": 3,
                "kind": "layer_sum",
                "model": {"layers": [1, 2, 3, 4], "item": "罐"},
                "task": {
                    "action": "count",
                    "ask": "total",
                    "prompt": "数一数每层，再想一共多少罐。",
                },
                "view": {"reveal": "items_without_total"},
            },
            "ladder": [
                {"rung": "do", "ask": "先数最上面一层有几罐。"},
                {"rung": "see", "ask": "每一层比上一层多几罐？"},
                {"rung": "why", "ask": "为什么把各层加起来就是全部？"},
            ],
            "misconceptions": ["只数最底下一层，忘了上面还有"],
        },
        {
            "hook": "六块积木能铺满小格子吗",
            "insight": "一样大的方块铺进格子，铺满时块数就是格子数",
            "axiom": "数是用来数东西的：每个东西数一次，不多不少。",
            "board": {
                "schema": 3,
                "kind": "snap_grid",
                "model": {"rows": 2, "cols": 3, "tray": 6},
                "task": {
                    "action": "arrange",
                    "ask": "observe",
                    "prompt": "把 6 块放进格子，看看会变成什么。",
                },
                "view": {"reveal": "empty_grid_and_tiles"},
            },
            "ladder": [
                {"rung": "do", "ask": "先放进一块，数数空着几格。"},
                {"rung": "see", "ask": "全部放进去以后，块数和格子数一样吗？"},
                {"rung": "why", "ask": "为什么铺满时不用再数一遍格子？"},
            ],
            "misconceptions": ["以为格子比积木多，就一定铺不满"],
        },
    ],
    "wordproblems": [
        {
            "hook": "小明和小红分糖",
            "insight": "多出来的那一截，就是两人相差的数量",
            "axiom": "'一共''还剩''每份''平均''多几''少几'这些词，是在提示我该合起来、拿走、平分还是比较。",
            "board": {
                "schema": 3,
                "kind": "static_diagram",
                "model": {
                    "diagram": {
                        "type": "bars",
                        "items": [{"label": "小明", "value": 8}, {"label": "小红", "value": 5}],
                        "caption": "谁的糖更多？多的是哪一截？",
                    }
                },
                "task": {
                    "action": "observe",
                    "ask": "notice",
                    "prompt": "小明有 8 颗糖，小红有 5 颗，多的到底是哪一段？",
                },
                "view": {"reveal": "model_only"},
            },
            "ladder": [
                {"rung": "do", "ask": "先在图上指一指，哪一段是两人都有的？"},
                {"rung": "see", "ask": "多出来的那截有几颗？"},
                {"rung": "why", "ask": "为什么用减法就能找到这一截？"},
            ],
            "misconceptions": ["把两人的糖加起来，当成相差的数量"],
        },
        {
            "hook": "小华排队买面包",
            "insight": "前面的人加上自己，才是他在队伍里的位置",
            "axiom": "先把题目读懂：它到底告诉了我什么？又在问我什么？用自己的话说一遍。",
            "board": {
                "schema": 3,
                "kind": "static_diagram",
                "model": {
                    "diagram": {
                        "type": "numberline",
                        "from": 0,
                        "to": 10,
                        "marks": [3, 8],
                        "caption": "从 3 走到 8，中间过了几步？",
                    }
                },
                "task": {
                    "action": "observe",
                    "ask": "notice",
                    "prompt": "小华前面有 3 个人，队伍一共 8 人，他后面还有几人？",
                },
                "view": {"reveal": "model_only"},
            },
            "ladder": [
                {"rung": "do", "ask": "先在数轴上指出 3 和 8。"},
                {"rung": "see", "ask": "从 3 到 8 要走几格？"},
                {"rung": "why", "ask": "为什么不能把 8 减 3 以后再随便减一个人？"},
            ],
            "misconceptions": ["忘了小华自己也占一个位置"],
        },
        {
            "hook": "两箱苹果差多少",
            "insight": "先对齐较短的那一段，多出来的才是相差",
            "axiom": "'一共''还剩''每份''平均''多几''少几'这些词，是在提示我该合起来、拿走、平分还是比较。",
            "board": {
                "schema": 3,
                "kind": "static_diagram",
                "model": {
                    "diagram": {
                        "type": "bars",
                        "items": [{"label": "大箱", "value": 12}, {"label": "小箱", "value": 7}],
                        "caption": "大箱比小箱多的是哪一截？",
                    }
                },
                "task": {
                    "action": "observe",
                    "ask": "notice",
                    "prompt": "大箱 12 个苹果，小箱 7 个，多的是哪一段？",
                },
                "view": {"reveal": "model_only"},
            },
            "ladder": [
                {"rung": "do", "ask": "先比一比两条谁更长。"},
                {"rung": "see", "ask": "多出来的那截是几个？"},
                {"rung": "why", "ask": "为什么比较多少时要先对齐较短的一段？"},
            ],
            "misconceptions": ["把 12 和 7 加起来当成相差"],
        },
    ],
    "geometry": [
        {
            "hook": "圆规的宽度不变，也能画出正三角形",
            "insight": "同一个圆上的点到圆心一样远，两圆交点到两个圆心都等于半径",
            "axiom": "以任意一点为圆心、任意长为半径，可以画一个圆。",
            "board": {
                "schema": 3,
                "kind": "geometry_compass",
                "model": {"construction": "equilateral_triangle", "labels": ["A", "B", "P"]},
                "task": {
                    "action": "construct",
                    "ask": "compare_three_sides",
                    "prompt": "按顺序画两个圆，再比较三条边。",
                },
                "view": {"reveal": "stepwise"},
            },
            "ladder": [
                {"rung": "do", "ask": "先把圆规夹成线段 AB 那么宽。"},
                {"rung": "see", "ask": "交点 P 到 A、B 的距离分别是多少？"},
                {"rung": "why", "ask": "为什么 PA、PB、AB 一定一样长？"},
            ],
            "misconceptions": ["以为交点离两个圆心可以不一样远"],
        },
        {
            "hook": "篱笆桩 C 和 D 也能围出正三角形",
            "insight": "半径相等时，交点到两个圆心的距离都等于那条给定的边",
            "axiom": "以任意一点为圆心、任意长为半径，可以画一个圆。",
            "board": {
                "schema": 3,
                "kind": "geometry_compass",
                "model": {"construction": "equilateral_triangle", "labels": ["C", "D", "Q"]},
                "task": {
                    "action": "construct",
                    "ask": "compare_three_sides",
                    "prompt": "按顺序画两个圆，再比较三条边。",
                },
                "view": {"reveal": "stepwise"},
            },
            "ladder": [
                {"rung": "do", "ask": "先夹住 CD，再分别以 C、D 为圆心画圆。"},
                {"rung": "see", "ask": "交点 Q 到 C、到 D，哪一段更长？"},
                {"rung": "why", "ask": "为什么换了字母，三条边仍然一样长？"},
            ],
            "misconceptions": ["觉得换了点的名字，道理就变了"],
        },
        {
            "hook": "绳子两端 M、N，第三点在哪儿",
            "insight": "两圆相交的点，正好让三条边都等于绳子的长度",
            "axiom": "任意两点之间，可以画一条直线段。",
            "board": {
                "schema": 3,
                "kind": "geometry_compass",
                "model": {"construction": "equilateral_triangle", "labels": ["M", "N", "R"]},
                "task": {
                    "action": "construct",
                    "ask": "compare_three_sides",
                    "prompt": "按顺序画两个圆，再比较三条边。",
                },
                "view": {"reveal": "stepwise"},
            },
            "ladder": [
                {"rung": "do", "ask": "先把绳子当成线段 MN。"},
                {"rung": "see", "ask": "交点 R 出现以后，你看见几条一样长的边？"},
                {"rung": "why", "ask": "为什么不用尺子量，也能知道三边相等？"},
            ],
            "misconceptions": ["以为一定要用尺子量，才能说相等"],
        },
    ],
    "algebra": [
        {
            "hook": "天平两边要一样重",
            "insight": "两边同时做一样的事，天平仍然平衡",
            "axiom": "等式就像一架平衡的天平，两边一样重。",
            "board": {
                "schema": 3,
                "kind": "static_diagram",
                "model": {
                    "diagram": {
                        "type": "bars",
                        "items": [{"label": "左边", "value": 7}, {"label": "右边", "value": 7}],
                        "caption": "两边一样重。如果两边都拿走 2，还会平吗？",
                    }
                },
                "task": {
                    "action": "observe",
                    "ask": "notice",
                    "prompt": "天平两边都是 7。两边同时拿走 2，还会平吗？",
                },
                "view": {"reveal": "model_only"},
            },
            "ladder": [
                {"rung": "do", "ask": "先用手比一比，两边都拿走 2，还剩几？"},
                {"rung": "see", "ask": "两边剩的还一样多吗？"},
                {"rung": "why", "ask": "为什么两边做同一件事，平衡不会被破坏？"},
            ],
            "misconceptions": ["只在一边拿走，还以为天平仍会平"],
        },
        {
            "hook": "两边都加上同一袋豆子",
            "insight": "两边同时加上同样多的东西，等式仍然成立",
            "axiom": "两边同时做完全一样的事（都加、都减、都乘、都除以同一个数），天平依然平衡。",
            "board": {
                "schema": 3,
                "kind": "static_diagram",
                "model": {
                    "diagram": {
                        "type": "bars",
                        "items": [{"label": "左边", "value": 4}, {"label": "右边", "value": 4}],
                        "caption": "两边都是 4。两边再各加 3，还会平吗？",
                    }
                },
                "task": {
                    "action": "observe",
                    "ask": "notice",
                    "prompt": "天平两边都是 4。两边同时再放上 3，还会平吗？",
                },
                "view": {"reveal": "model_only"},
            },
            "ladder": [
                {"rung": "do", "ask": "先算一边 4 加 3 是多少。"},
                {"rung": "see", "ask": "另一边做同样的加法，结果一样吗？"},
                {"rung": "why", "ask": "为什么加的是同一袋，天平不会歪？"},
            ],
            "misconceptions": ["以为加上东西后天平一定会歪"],
        },
        {
            "hook": "右边轻了，怎样才能重新平",
            "insight": "差几就补几，两边才能重新一样重",
            "axiom": "等式就像一架平衡的天平，两边一样重。",
            "board": {
                "schema": 3,
                "kind": "static_diagram",
                "model": {
                    "diagram": {
                        "type": "bars",
                        "items": [{"label": "左边", "value": 9}, {"label": "右边", "value": 5}],
                        "caption": "左边 9，右边 5。右边还要放几才平？",
                    }
                },
                "task": {
                    "action": "observe",
                    "ask": "notice",
                    "prompt": "左边 9，右边 5，右边还要放几才能平？",
                },
                "view": {"reveal": "model_only"},
            },
            "ladder": [
                {"rung": "do", "ask": "先指一指哪一边更长。"},
                {"rung": "see", "ask": "短的那一边差几？"},
                {"rung": "why", "ask": "为什么补上相差的数量，两边就会平？"},
            ],
            "misconceptions": ["把 9 和 5 加起来当成要补的数"],
        },
    ],
    "fractions": [
        {
            "hook": "一块饼切成两半和四份",
            "insight": "切的份数变了，但拿走的饼可以还是一样多",
            "axiom": "分子分母同时乘或除以同一个数，分数的大小不变（还是同样多的饼）。",
            "board": {
                "schema": 3,
                "kind": "static_diagram",
                "model": {
                    "diagram": {
                        "type": "bars",
                        "items": [{"label": "一半", "value": 2}, {"label": "四份里的两份", "value": 2}],
                        "caption": "这两种切法，拿走的饼一样多吗？",
                    }
                },
                "task": {
                    "action": "observe",
                    "ask": "notice",
                    "prompt": "一块饼切成 2 份拿 1 份，和切成 4 份拿 2 份，哪个更多？",
                },
                "view": {"reveal": "model_only"},
            },
            "ladder": [
                {"rung": "do", "ask": "先把饼画成一样长的两条，标出拿走的部分。"},
                {"rung": "see", "ask": "两条上涂黑的长度一样吗？"},
                {"rung": "why", "ask": "为什么份数变了，拿走的却可以一样多？"},
            ],
            "misconceptions": ["看到 4 份里拿 2 份，就觉得一定比一半多"],
        },
        {
            "hook": "巧克力掰成三份和六份",
            "insight": "把每份再对切，拿走的份数也跟着加倍，总量不变",
            "axiom": "同一个东西，切的份数越多，每一份就越小。",
            "board": {
                "schema": 3,
                "kind": "static_diagram",
                "model": {
                    "diagram": {
                        "type": "bars",
                        "items": [{"label": "三份里一份", "value": 2}, {"label": "六份里两份", "value": 2}],
                        "caption": "1/3 和 2/6 谁更大？",
                    }
                },
                "task": {
                    "action": "observe",
                    "ask": "notice",
                    "prompt": "巧克力切成 3 份拿 1 份，和切成 6 份拿 2 份，哪个更多？",
                },
                "view": {"reveal": "model_only"},
            },
            "ladder": [
                {"rung": "do", "ask": "先把两条画得一样长。"},
                {"rung": "see", "ask": "涂黑的两段一样长吗？"},
                {"rung": "why", "ask": "为什么份数变多了，拿走的却可以一样？"},
            ],
            "misconceptions": ["只看分母变大，就说巧克力变少了"],
        },
        {
            "hook": "两杯果汁谁更满",
            "insight": "比较分数前，要先想它们是不是同样大小的一杯",
            "axiom": "比较或相加分数前，要先把它们切成一样大的份。",
            "board": {
                "schema": 3,
                "kind": "static_diagram",
                "model": {
                    "diagram": {
                        "type": "bars",
                        "items": [{"label": "甲杯", "value": 3}, {"label": "乙杯", "value": 2}],
                        "caption": "两杯一样大。甲杯更满一些吗？",
                    }
                },
                "task": {
                    "action": "observe",
                    "ask": "notice",
                    "prompt": "两杯一样大，甲杯装到 3 格，乙杯装到 2 格，谁更满？",
                },
                "view": {"reveal": "model_only"},
            },
            "ladder": [
                {"rung": "do", "ask": "先确认两杯是一样大的。"},
                {"rung": "see", "ask": "哪一条涂得更长？"},
                {"rung": "why", "ask": "为什么杯子一样大，才能直接比格子？"},
            ],
            "misconceptions": ["杯子不一样大，也直接比格子"],
        },
    ],
    "reasoning": [
        {
            "hook": "花朵颜色的规律",
            "insight": "先多看几个例子再猜，再用下一个去验证",
            "axiom": "找规律时，先多列几个具体例子，再猜规律，最后想办法验证。",
            "board": {
                "schema": 3,
                "kind": "color_sequence",
                "model": {"item": "花", "unit": ["red", "red", "blue"], "count": 6},
                "task": {
                    "action": "predict",
                    "ask": "color_at_end",
                    "prompt": "按红、红、蓝的规律排下去，第六朵会是什么颜色？",
                },
                "view": {"reveal": "hide_last"},
            },
            "ladder": [
                {"rung": "do", "ask": "先把前五朵的颜色按顺序说出来。"},
                {"rung": "see", "ask": "每几朵重复一次？"},
                {"rung": "why", "ask": "你怎么证明第六朵一定是这个颜色，而不是猜的？"},
            ],
            "misconceptions": ["只看最后一朵的前一朵，就猜下一个"],
        },
        {
            "hook": "珠子蓝黄蓝黄地排",
            "insight": "两个一组重复时，位置的单双能帮我们判断颜色",
            "axiom": "找规律时，先多列几个具体例子，再猜规律，最后想办法验证。",
            "board": {
                "schema": 3,
                "kind": "color_sequence",
                "model": {"item": "珠", "unit": ["blue", "yellow"], "count": 5},
                "task": {
                    "action": "predict",
                    "ask": "color_at_end",
                    "prompt": "按蓝、黄的规律排下去，第五颗会是什么颜色？",
                },
                "view": {"reveal": "hide_last"},
            },
            "ladder": [
                {"rung": "do", "ask": "先说出前四颗的颜色。"},
                {"rung": "see", "ask": "第 1、3 颗是不是同一种颜色？"},
                {"rung": "why", "ask": "为什么第五颗会跟第一颗一样？"},
            ],
            "misconceptions": ["以为会突然换成第三种颜色"],
        },
        {
            "hook": "一次可以走 1 级或 2 级",
            "insight": "把不同走法都试一遍，不要漏掉，也不要重复算",
            "axiom": "举一个反例，就能推翻一句'所有……都……'的话。",
            "board": {
                "schema": 3,
                "kind": "path_count",
                "model": {"start": 0, "target": 4, "moves": [1, 2]},
                "task": {
                    "action": "enumerate",
                    "ask": "number_of_paths",
                    "prompt": "试着走到第 4 级，找出不同走法。",
                },
                "view": {"reveal": "rules_only"},
            },
            "ladder": [
                {"rung": "do", "ask": "先走一步看看能到哪。"},
                {"rung": "see", "ask": "有没有两种走法最后都到 4？"},
                {"rung": "why", "ask": "怎样知道自己没有漏掉一种走法？"},
            ],
            "misconceptions": ["把同一种走法的左右顺序当成两种"],
        },
    ],
}


def _materialize_seed(topic: str, raw: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "topic": topic,
        "hook": raw.get("hook"),
        "insight": raw.get("insight"),
        "axiom": raw.get("axiom"),
        "board": raw.get("board"),
        "ladder": raw.get("ladder"),
        "misconceptions": raw.get("misconceptions") or ["只看表面数字，没先画出来"],
        "first_question": raw.get("first_question") or "",
    }
    card = normalize_card(payload, topic)
    if card:
        return card
    board = semantic_board.normalize_board_v3(raw.get("board"))
    return {
        "topic": topic,
        "hook": str(raw.get("hook") or ""),
        "insight": str(raw.get("insight") or ""),
        "axiom": str(raw.get("axiom") or ""),
        "representation": "board_v3",
        "board": board,
        "semantic_board": None,
        "diagram": None,
        "first_question": semantic_board.first_question_for_v3(board or {}) if board else "",
        "ladder": raw.get("ladder") or [],
        "misconceptions": raw.get("misconceptions") or [],
    }


def seed_variants(topic: str) -> list[dict[str, Any]]:
    topic = topic if topic in SEED_VARIANTS else "arithmetic"
    catalog = generated_seed_catalog()
    source = (catalog.get("topics") or {}).get(topic) if catalog else None
    raws = source if isinstance(source, list) and len(source) == 3 else SEED_VARIANTS[topic]
    return [_materialize_seed(topic, raw) for raw in raws]


def seed_cards_payload() -> dict[str, list[dict[str, Any]]]:
    return {key: seed_variants(key) for key in SEED_VARIANTS}


def generated_seed_catalog() -> dict[str, Any]:
    """只接受 GLM Author Agent 产出的完整 6×3 目录；损坏时安全退回内置题。"""
    try:
        payload = json.loads(GENERATED_SEED_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if (
        not isinstance(payload, dict)
        or payload.get("schema") != 1
        or payload.get("generator") != "author-agent"
        or payload.get("author_model") != "glm-5.3"
    ):
        return {}
    topics = payload.get("topics")
    if not isinstance(topics, dict) or set(topics) != set(SEED_VARIANTS):
        return {}
    for topic, raws in topics.items():
        if not isinstance(raws, list) or len(raws) != 3:
            return {}
        cards = [_materialize_seed(topic, raw) for raw in raws]
        if any(validate_card(card, topic) for card in cards):
            return {}
    return payload


def seed_catalog_meta() -> dict[str, Any]:
    payload = generated_seed_catalog()
    if not payload:
        return {"source": "builtin", "author_model": "", "generated_at": ""}
    return {
        "source": payload.get("generator"),
        "author_model": payload.get("author_model"),
        "tutor_model": payload.get("tutor_model"),
        "generated_at": payload.get("generated_at"),
    }


def seed_card(
    topic: str,
    level: str = "middle",
    recent: list[str] | None = None,
) -> dict[str, Any]:
    del level  # 种子题按主题分，不按年级改画板。
    cards = seed_variants(topic)
    recent_hooks = [str(item).strip() for item in (recent or []) if str(item).strip()]
    unused = [card for card in cards if card.get("hook") not in recent_hooks]
    if unused:
        return unused[0]
    return cards[len(recent_hooks) % len(cards)]


def build_author_prompt(topic_key: str, level: str, recent: list[str]) -> str:
    topic = tutor.TOPICS_BY_KEY.get(topic_key, tutor.TOPICS_BY_KEY[tutor.DEFAULT_TOPIC_KEY])
    level_desc = tutor.LEVELS.get(level, tutor.LEVELS[tutor.DEFAULT_LEVEL])
    return AUTHOR_PROMPT.format(
        topic_name=topic.name,
        topic_key=topic.key,
        level_desc=level_desc,
        axioms_block="\n".join(f"  - {a}" for a in topic.axioms),
        inspirations_block="\n".join(f"  - {s}" for s in topic.inspirations),
        recent_block="、".join(recent[:8]) if recent else "（还没有）",
    )


def card_guidance(card: dict[str, Any]) -> str:
    ladder = card.get("ladder") or []
    steps = "\n".join(
        f"  - {row.get('rung')}: {row.get('ask')}" for row in ladder if isinstance(row, dict)
    )
    misses = "、".join(card.get("misconceptions") or []) or "（未列出）"
    board = card.get("board")
    board_kind = board.get("kind") if isinstance(board, dict) else "unknown"
    board_rule = (
        f"- 数学画板活动：{board_kind}\n"
        "- 画板已经由程序按已校验题卡挂好。你只输出孩子能听懂的自然语言，绝不输出或复述"
        "任何 JSON、xiaoou-draw、schema、kind、SVG、Canvas、Konva 或画图步骤。"
        "根据孩子的操作和盘面快照继续追问，不要在文字里提前列完答案。"
    )
    opening_rule = "现在先用第一问开场；不要重复描述画板代码，画板已经在孩子面前。"
    return f"""# 本堂课的题卡（孩子看不到）
你只教下面这张卡。不要另出一道题，不要把课拖回「9 块摆正方形」，除非这张卡的道理就是平方数/奇数包一圈。
- 钩子：{card.get("hook")}
- 要发现的道理：{card.get("insight")}
- 对准的公理：{card.get("axiom")}
{board_rule}
- 第一问：{card.get("first_question")}
- 三层台阶：
{steps}
- 孩子可能的误会（不要直接说破）：{misses}

{opening_rule}孩子还在手上这一层，就还问手上的事；他自己跨上去了，再走下一层。"""


def resolve_engine(requested: str | None) -> str:
    engine = (requested or settings.author_engine or "glm").strip().lower()
    if engine not in AUTHOR_ENGINES:
        engine = "glm"
    return engine


def engine_ready(engine: str) -> bool:
    if engine == "glm":
        return bool(settings.zhipu_api_key)
    return bool(settings.deepseek_api_key)


def engine_payloads() -> list[dict[str, Any]]:
    return [
        {"key": "glm", "name": "GLM-5.3", "ready": engine_ready("glm")},
        {"key": "deepseek", "name": "DeepSeek V4 Pro", "ready": engine_ready("deepseek")},
    ]


def _author_client_conf(engine: str) -> tuple[str, str, str]:
    if engine == "glm":
        return (
            settings.zhipu_base_url.rstrip("/") + "/chat/completions",
            settings.zhipu_api_key,
            settings.zhipu_model,
        )
    return (
        settings.deepseek_base_url.rstrip("/") + "/chat/completions",
        settings.deepseek_api_key,
        settings.deepseek_model,
    )


async def request_author_card(
    topic: str,
    level: str,
    recent: list[str],
    engine: str,
    timeout: float = 120.0,
) -> dict[str, Any]:
    endpoint, api_key, model = _author_client_conf(engine)
    if not api_key:
        raise ValueError("还没有接上出题大脑的密钥。")
    extras = teaching_config.thinking_request_extras(
        endpoint, model, True, settings.author_reasoning_effort
    )
    payload = {
        "model": model,
        "stream": False,
        "temperature": 0.8,
        "messages": [
            {"role": "system", "content": build_author_prompt(topic, level, recent)},
            {"role": "user", "content": "请只输出题卡 JSON。"},
        ],
        **extras,
    }
    if engine == "deepseek":
        payload["response_format"] = {"type": "json_object"}
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=httpx.Timeout(timeout)) as client:
        resp = await client.post(endpoint, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
    content = ""
    try:
        content = data["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, TypeError):
        content = ""
    card = normalize_card(extract_json_object(content), topic)
    if not card:
        raise ValueError("出题大脑没有吐出合格的题卡。")
    return card


async def author_problem(
    topic: str,
    level: str,
    recent: list[str] | None = None,
    engine: str | None = None,
) -> dict[str, Any]:
    topic = topic if topic in tutor.TOPICS_BY_KEY else tutor.DEFAULT_TOPIC_KEY
    level = level if level in tutor.LEVELS else tutor.DEFAULT_LEVEL
    recent = [str(x).strip() for x in (recent or []) if str(x).strip()]
    chosen = resolve_engine(engine)
    if not engine_ready(chosen) and chosen == "glm" and engine_ready("deepseek"):
        chosen = "deepseek"
    last_error = "出题失败"
    if engine_ready(chosen):
        try:
            return await request_author_card(topic, level, recent, chosen)
        except (httpx.HTTPError, ValueError) as exc:
            last_error = str(exc)
    if engine_ready(chosen):
        return seed_card(topic, level, recent)
    raise ValueError(last_error if last_error else "还没有接上出题大脑。")
