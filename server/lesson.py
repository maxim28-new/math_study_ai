"""探索课状态：台阶厚度、发现芯片、削薄指令。孩子看不见 insight。"""

from __future__ import annotations

import hashlib
import re
from typing import Any

RUNGS = ("do", "see", "why")
KEY_RE = re.compile(r"^[a-z][a-z0-9_]{2,47}$")
SHRINK_MESSAGE = "太难了"
REGULARITY_ASK = "你总结出什么规律了吗？"
MAX_SAID = 80
WINDOW = 8
_SHRINK_PREFIXES = ("太难了", "再小一点", "再说简单点")

SEED_INSIGHT_KEYS = {
    "糖果店的糖装在托盘里": "place_value_bundle_ten",
    "水果摊的橙子堆成一座小山": "pair_ends_multiply",
    "要给礼物盒扎蝴蝶结": "common_measure_gcd",
    "停车场里停着12辆小汽车": "compare_then_total",
    "哥哥有8张贴纸": "equalize_by_half_diff",
    "小青蛙在台阶上跳格子": "enumerate_by_large_move",
    "魔术师心里藏了一个数": "undo_last_operation",
    "两只仓鼠要把 10 块饼干": "same_both_sides",
    "货架每层都摆同样多的罐头": "repeated_add_is_multiply",
    "妹妹穿花环": "remainder_in_cycle",
    "小青蛙练习跳台阶": "last_jump_recurrence",
    "超市仓库里，罐头摆成一座小楼梯": "pair_ends_or_level",
    "野餐带来的12颗软糖": "equal_share_of_pile",
    "分一板15小块的巧克力": "compare_unit_pieces",
    "妈妈用穿12颗珠的丝带": "bigger_denominator_smaller_unit",
    "木匠爷爷从不用尺子量边": "equal_radii_equilateral",
    "手工课上，一张长方形彩纸": "diagonal_halves_rectangle",
    "公园要铺一只蝴蝶图案的地砖": "reflection_equal_distance",
}


def empty_lesson() -> dict[str, Any]:
    return {"rung": "do", "shrinks": 0, "view": "", "discoveries": []}


def insight_key_of(data: dict[str, Any] | None) -> str:
    data = data if isinstance(data, dict) else {}
    raw = str(data.get("insight_key") or "").strip()
    if KEY_RE.fullmatch(raw):
        return raw
    hook = str(data.get("hook") or "")
    for prefix, key in SEED_INSIGHT_KEYS.items():
        if hook.startswith(prefix):
            return key
    src = str(data.get("insight") or hook or "idea")
    digest = hashlib.sha1(src.encode("utf-8")).hexdigest()[:10]
    return f"idea_{digest}"


def allowed_views_of(data: dict[str, Any] | None, default: str = "") -> list[str]:
    data = data if isinstance(data, dict) else {}
    views: list[str] = []
    raw = data.get("allowed_views")
    if isinstance(raw, list):
        for item in raw:
            name = str(item or "").strip()[:32]
            if name and name not in views:
                views.append(name)
    fallback = str(default or "").strip()[:32]
    if fallback and fallback not in views:
        views.insert(0, fallback)
    return views


def _clip_int(value: Any, lo: int, hi: int, default: int) -> int:
    try:
        n = int(value)
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, n))


def normalize_discovery(item: Any, topic: str = "") -> dict[str, str] | None:
    if not isinstance(item, dict):
        return None
    key = str(item.get("insight_key") or "").strip()
    said = str(item.get("child_said") or "").strip()
    if not KEY_RE.fullmatch(key) or not said:
        return None
    if leaks_insight(said, str(item.get("insight") or "")):
        return None
    return {
        "insight_key": key,
        "child_said": said[:MAX_SAID],
        "topic": str(item.get("topic") or topic or "").strip(),
    }


def normalize_lesson(raw: Any) -> dict[str, Any]:
    src = raw if isinstance(raw, dict) else {}
    rung = str(src.get("rung") or "do").strip()
    if rung not in RUNGS:
        rung = "do"
    discoveries: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in src.get("discoveries") or []:
        row = normalize_discovery(item, str(src.get("topic") or ""))
        if not row or row["insight_key"] in seen:
            continue
        seen.add(row["insight_key"])
        discoveries.append(row)
    return {
        "rung": rung,
        "shrinks": _clip_int(src.get("shrinks"), 0, 3, 0),
        "view": str(src.get("view") or "").strip()[:32],
        "discoveries": discoveries,
    }


def reset_for_new_card(lesson: Any) -> dict[str, Any]:
    current = normalize_lesson(lesson)
    return {
        "rung": "do",
        "shrinks": 0,
        "view": "",
        "discoveries": current["discoveries"],
    }


def apply_shrink(lesson: Any) -> dict[str, Any]:
    current = normalize_lesson(lesson)
    shrinks = current["shrinks"]
    rung = current["rung"]
    if shrinks <= 0:
        current["shrinks"] = 1
        return current
    if shrinks == 1:
        if rung == "why":
            current["rung"] = "see"
        elif rung == "see":
            current["rung"] = "do"
        current["shrinks"] = 2
        return current
    current["shrinks"] = 3
    return current


def _fold(text: str) -> str:
    return re.sub(r"\s+", "", str(text or ""))


def leaks_insight(text: str, insight: str) -> bool:
    folded_text = _fold(text)
    folded_insight = _fold(insight)
    if not folded_text or not folded_insight:
        return False
    if folded_text in folded_insight or folded_insight in folded_text:
        return True
    if len(folded_insight) >= WINDOW:
        for i in range(0, len(folded_insight) - WINDOW + 1):
            if folded_insight[i : i + WINDOW] in folded_text:
                return True
    return False


def harvest_discovery(
    claim: dict[str, Any] | None,
    child_said: str,
    insight: str,
    insight_key: str,
    topic: str = "",
) -> dict[str, str] | None:
    if not isinstance(claim, dict) or not claim.get("accepted_by_child"):
        return None
    if not KEY_RE.fullmatch(str(insight_key or "")):
        return None
    said = str(child_said or "").strip()
    statement = str(claim.get("statement") or "").strip()
    text = said if said and not leaks_insight(said, insight) else ""
    if not text and statement and not leaks_insight(statement, insight):
        text = statement
    if not text:
        return None
    return normalize_discovery(
        {"insight_key": insight_key, "child_said": text, "topic": topic},
        topic,
    )


_QUOTED = re.compile(r"[「『'\"“]([^」』'\"”]{2,16})[」』'\"”]")
_WORD = re.compile(r"[^\w\u4e00-\u9fff]+")


def _compact(text: str) -> str:
    return _WORD.sub("", _fold(text))


def looks_like_misconception(said: str, card: dict[str, Any] | None) -> bool:
    if not isinstance(card, dict):
        return False
    compact_said = _compact(said)
    for item in card.get("misconceptions") or []:
        raw = str(item or "")
        if leaks_insight(said, raw):
            return True
        for core in _QUOTED.findall(raw):
            compact_core = _compact(core)
            if compact_core and re.search(r"\d", compact_core) and compact_core in compact_said:
                return True
    return False


def is_shrink_talk(text: str) -> bool:
    said = str(text or "").strip()
    return any(said == prefix or said.startswith(prefix) for prefix in _SHRINK_PREFIXES)


def accept_regularity(
    said: str,
    card: dict[str, Any] | None,
    topic: str = "",
) -> dict[str, str] | None:
    text = str(said or "").strip()
    if len(text) < 4 or is_shrink_talk(text):
        return None
    insight = str((card or {}).get("insight") or "")
    if leaks_insight(text, insight):
        return None
    if looks_like_misconception(text, card):
        return None
    key = insight_key_of(card)
    return normalize_discovery(
        {"insight_key": key, "child_said": text, "topic": topic or str((card or {}).get("topic") or "")},
        topic,
    )


def merge_discovery(lesson: Any, discovery: dict[str, str] | None) -> dict[str, Any]:
    current = normalize_lesson(lesson)
    row = normalize_discovery(discovery)
    if not row:
        return current
    kept = [item for item in current["discoveries"] if item["insight_key"] != row["insight_key"]]
    kept.append(row)
    current["discoveries"] = kept
    return current


def ladder_ask(card: dict[str, Any] | None, rung: str) -> str:
    if not isinstance(card, dict):
        return ""
    for row in card.get("ladder") or []:
        if isinstance(row, dict) and str(row.get("rung") or "") == rung:
            return str(row.get("ask") or "").strip()
    return ""


def discovery_prompt_block(lesson: dict[str, Any], card: dict[str, Any] | None) -> str:
    key = insight_key_of(card)
    topic = str((card or {}).get("topic") or "")
    lines: list[str] = []
    for item in normalize_lesson(lesson)["discoveries"]:
        if item["insight_key"] != key:
            continue
        if topic and item["topic"] and item["topic"] != topic:
            continue
        if leaks_insight(item["child_said"], str((card or {}).get("insight") or "")):
            continue
        lines.append(item["child_said"])
    if not lines:
        return ""
    said = "；".join(lines)
    return (
        "孩子已经用自己的话说过（可以点名引用，不要改写成题卡洞见，也不要宣读 insight）："
        f"{said}。"
    )


def shrink_prompt_block(
    lesson: dict[str, Any],
    card: dict[str, Any] | None,
    event: str = "",
) -> str:
    if str(event or "") != "shrink":
        return ""
    current = normalize_lesson(lesson)
    shrinks = current["shrinks"]
    rung = current["rung"]
    ask = ladder_ask(card, rung)
    ask_line = f"当前层（{rung}）台阶问法：{ask}" if ask else f"当前层是 {rung}。"
    views = allowed_views_of(card, current["view"])
    other = [name for name in views if name and name != current["view"]]
    if shrinks <= 1:
        return (
            f"本轮孩子说「太难了」（第 1 档）。{ask_line}"
            "留在这一层，把问句削短、换成她能上手的一小步。可以高亮一个对象。"
            "不要跳到 why，不要问规律，不要说出洞见或答案。"
        )
    if shrinks == 2:
        return (
            f"本轮孩子说「太难了」（第 2 档）。{ask_line}"
            "问句再削短。已在 do 就再削，并可以动一次画板让她看清。"
            "不要给答案，不要问有没有规律，不要跳到 why。"
        )
    if other:
        names = "、".join(other)
        return (
            f"本轮孩子说「太难了」（第 3 档，到顶）。{ask_line}"
            f"不要给答案。用一句话问要不要换成另一种看法（允许：{names}）；"
            "孩子同意再调用 board_switch_view。不要口头假装已经换图。"
        )
    return (
        f"本轮孩子说「太难了」（第 3 档，到顶）。{ask_line}"
        "不要给答案。用更小的数字问同一件事，例如 8 和 4 改成 6 和 2。"
    )


def lesson_guidance(
    lesson: Any,
    card: dict[str, Any] | None,
    event: str = "",
) -> str:
    current = normalize_lesson(lesson)
    ask = ladder_ask(card, current["rung"])
    parts = [
        "# 本堂课的台阶（孩子看不到这段标题）",
        f"- 当前层：{current['rung']}；削薄次数：{current['shrinks']}。",
        "- 孩子还在手上这一层，就还问手上的事；他自己跨上去了，再走下一层。",
        "- 永远不要把题卡里的「要发现的道理」念给孩子听。只有他自己说出口的话才能点名引用。",
    ]
    if ask:
        parts.append(f"- 这一层建议问：{ask}")
    found = discovery_prompt_block(current, card)
    if found:
        parts.append(f"- {found}")
    shrink = shrink_prompt_block(current, card, event)
    if shrink:
        parts.append(shrink)
    return "\n".join(parts)
