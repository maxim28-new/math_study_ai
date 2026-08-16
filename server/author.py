"""出题作者：强模型先写出一张题卡，小欧再按卡陪练。"""

from __future__ import annotations

import json
import re
from typing import Any

import httpx

from . import config as teaching_config
from . import board as semantic_board
from .config import settings
from . import tutor

AUTHOR_ENGINES = ("deepseek", "glm")

LADDER_RUNGS = ("do", "see", "why")
REPRESENTATIONS = {"board_v3"}

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
- 分层物体合计用 layer_sum；允许步长的走法用 path_count。
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


def seed_card(topic: str, level: str = "middle") -> dict[str, Any]:
    seeds = {
        "arithmetic": {
            "hook": "1 加到 10 有点慢",
            "insight": "首尾配对以后，每一对都一样多",
            "axiom": "把两堆合在一起数，就是加法；无论先数哪一堆，结果都一样。",
            "representation": "numberline",
            "diagram": {"type": "numberline", "from": 1, "to": 10, "marks": [1, 10], "caption": "1 和 10 能凑成一对吗？"},
            "first_question": "从 1 加到 10，有没有比一个一个加更快的办法？",
            "ladder": [
                {"rung": "do", "ask": "你先试试 1 配 10、2 配 9，每对是多少？"},
                {"rung": "see", "ask": "这样的对一共有几对？"},
                {"rung": "why", "ask": "为什么每一对都会一样多？"},
            ],
        },
        "wordproblems": {
            "hook": "小明和小红分糖",
            "insight": "多出来的那一截，就是两人相差的数量",
            "axiom": "'一共''还剩''每份''平均''多几''少几'这些词，是在提示我该合起来、拿走、平分还是比较。",
            "representation": "bars",
            "diagram": {
                "type": "bars",
                "items": [{"label": "小明", "value": 8}, {"label": "小红", "value": 5}],
                "caption": "谁的糖更多？多的是哪一截？",
            },
            "first_question": "小明有 8 颗糖，小红有 5 颗，多的到底是哪一段？",
            "ladder": [
                {"rung": "do", "ask": "先在图上指一指，哪一段是两人都有的？"},
                {"rung": "see", "ask": "多出来的那截有几颗？"},
                {"rung": "why", "ask": "为什么用减法就能找到这一截？"},
            ],
        },
        "geometry": {
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
            "first_question": "保持圆规宽度不变，两个圆的交点能帮我们得到三条一样长的边吗？",
            "ladder": [
                {"rung": "do", "ask": "先把圆规夹成线段 AB 那么宽。"},
                {"rung": "see", "ask": "交点 P 到 A、B 的距离分别是多少？"},
                {"rung": "why", "ask": "为什么 PA、PB、AB 一定一样长？"},
            ],
        },
        "algebra": {
            "hook": "天平两边要一样重",
            "insight": "两边同时做一样的事，天平仍然平衡",
            "axiom": "等式就像一架平衡的天平，两边一样重。",
            "representation": "bars",
            "diagram": {
                "type": "bars",
                "items": [{"label": "左边", "value": 7}, {"label": "右边", "value": 7}],
                "caption": "两边一样重。如果两边都拿走 2，还会平吗？",
            },
            "first_question": "天平两边都是 7。两边同时拿走 2，还会平吗？",
            "ladder": [
                {"rung": "do", "ask": "先用手比一比，两边都拿走 2，还剩几？"},
                {"rung": "see", "ask": "两边剩的还一样多吗？"},
                {"rung": "why", "ask": "为什么两边做同一件事，平衡不会被破坏？"},
            ],
        },
        "fractions": {
            "hook": "一块饼切成两半和四份",
            "insight": "切的份数变了，但拿走的饼可以还是一样多",
            "axiom": "分子分母同时乘或除以同一个数，分数的大小不变（还是同样多的饼）。",
            "representation": "bars",
            "diagram": {
                "type": "bars",
                "items": [{"label": "一半", "value": 2}, {"label": "四份里的两份", "value": 2}],
                "caption": "这两种切法，拿走的饼一样多吗？",
            },
            "first_question": "一块饼切成 2 份拿 1 份，和切成 4 份拿 2 份，哪个更多？",
            "ladder": [
                {"rung": "do", "ask": "先把饼画成一样长的两条，标出拿走的部分。"},
                {"rung": "see", "ask": "两条上涂黑的长度一样吗？"},
                {"rung": "why", "ask": "为什么份数变了，拿走的却可以一样多？"},
            ],
        },
        "reasoning": {
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
            "first_question": "红红蓝、红红蓝……第六朵会是什么颜色？",
            "ladder": [
                {"rung": "do", "ask": "先把前五朵的颜色按顺序说出来。"},
                {"rung": "see", "ask": "每几朵重复一次？"},
                {"rung": "why", "ask": "你怎么证明第六朵一定是这个颜色，而不是猜的？"},
            ],
        },
    }
    base = seeds.get(topic) or seeds["arithmetic"]
    legacy_representation = str(base.get("representation") or "")
    legacy_diagram = base.get("diagram")
    board = base.get("board") or semantic_board.board_v3_from_legacy(
        None,
        legacy_representation,
        legacy_diagram,
        str(base.get("first_question") or ""),
    )
    card = {
        "topic": topic if topic in seeds else "arithmetic",
        "misconceptions": ["只看表面数字，没先画出来"],
        "representation": "board_v3",
        "board": board,
        "semantic_board": None,
        "diagram": None,
        **base,
    }
    card["representation"] = "board_v3"
    card["board"] = board
    card["semantic_board"] = None
    card["diagram"] = None
    card["first_question"] = semantic_board.first_question_for_v3(board) or str(
        base.get("first_question") or ""
    )
    if topic not in seeds:
        card["topic"] = "arithmetic"
    return card


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


async def request_author_card(topic: str, level: str, recent: list[str], engine: str) -> dict[str, Any]:
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
    async with httpx.AsyncClient(timeout=httpx.Timeout(50.0)) as client:
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
        return seed_card(topic, level)
    raise ValueError(last_error if last_error else "还没有接上出题大脑。")
