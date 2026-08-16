"""版本化数学画板协议。

V3 是探索题卡的唯一输出协议；V2 和 xiaoou-draw 仅保留为旧会话适配入口。
"""

from __future__ import annotations

from typing import Any


SCHEMA_VERSION = 2
SUPPORTED_KINDS = ("layer_sum", "path_count")
BOARD_SCHEMA_VERSION = 3
BOARD_KINDS = (
    "layer_sum",
    "path_count",
    "snap_grid",
    "static_diagram",
    "geometry_compass",
    "color_sequence",
)
COLOR_SEQUENCE_COLORS = ("red", "blue", "yellow", "green", "orange", "purple")
COLOR_SEQUENCE_LABELS = {
    "red": "红",
    "blue": "蓝",
    "yellow": "黄",
    "green": "绿",
    "orange": "橙",
    "purple": "紫",
}
ITEM_MEASURES = {"花": "朵", "珠": "颗", "块": "块"}
STATIC_DIAGRAM_TYPES = (
    "dots",
    "stairs",
    "square_layers",
    "square_steps",
    "square_compare",
    "numberline",
    "bars",
)


def _int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _bounded_text(value: Any, limit: int, default: str = "") -> str:
    text = str(value or "").strip()
    return (text or default)[:limit]


def _normalize_static_diagram(raw: Any) -> dict[str, Any] | None:
    """校验旧静态图参数；V3 只把它当成受控的确定性视图。"""
    if not isinstance(raw, dict):
        return None
    kind = str(raw.get("type") or "")
    caption = _bounded_text(raw.get("caption"), 80)
    if kind == "dots":
        rows, cols = _int(raw.get("rows")), _int(raw.get("cols"))
        if rows is None or cols is None or not 1 <= rows <= 8 or not 1 <= cols <= 8:
            return None
        return {
            "type": kind,
            "rows": rows,
            "cols": cols,
            "newLastRowCol": bool(raw.get("newLastRowCol", False)),
            "caption": caption,
        }
    if kind == "stairs":
        rows = _int(raw.get("rows"))
        if rows is None or not 1 <= rows <= 8:
            return None
        return {"type": kind, "rows": rows, "caption": caption}
    if kind in ("square_layers", "square_steps"):
        size_key = "max" if kind == "square_steps" else "size"
        size = _int(raw.get(size_key))
        if size is None or not 1 <= size <= 8:
            return None
        result: dict[str, Any] = {"type": kind, size_key: size, "caption": caption}
        if kind == "square_layers":
            highlight_raw = raw.get("highlight", "none")
            if highlight_raw == "none":
                result["highlight"] = "none"
            else:
                highlight = _int(highlight_raw)
                if highlight is None or not 1 <= highlight <= size:
                    return None
                result["highlight"] = highlight
        else:
            highlight = _int(raw.get("highlight", size))
            if highlight is None or not 1 <= highlight <= size:
                return None
            result["highlight"] = highlight
        return result
    if kind == "square_compare":
        start, end = _int(raw.get("from")), _int(raw.get("to"))
        if start is None or end is None or not 1 <= start < end <= 8:
            return None
        return {"type": kind, "from": start, "to": end, "caption": caption}
    if kind == "numberline":
        start, end = _int(raw.get("from")), _int(raw.get("to"))
        if start is None or end is None or start >= end or end - start > 30:
            return None
        marks_raw = raw.get("marks") or []
        if not isinstance(marks_raw, list) or len(marks_raw) > 12:
            return None
        marks: list[int] = []
        for value in marks_raw:
            mark = _int(value)
            if mark is None or not start <= mark <= end:
                return None
            if mark not in marks:
                marks.append(mark)
        return {"type": kind, "from": start, "to": end, "marks": marks, "caption": caption}
    if kind == "bars":
        items_raw = raw.get("items")
        if not isinstance(items_raw, list) or not 1 <= len(items_raw) <= 6:
            return None
        items: list[dict[str, Any]] = []
        for row in items_raw:
            if not isinstance(row, dict):
                return None
            value = _int(row.get("value"))
            label = _bounded_text(row.get("label"), 12)
            if value is None or not 1 <= value <= 100 or not label:
                return None
            items.append({"label": label, "value": value})
        return {"type": kind, "items": items, "caption": caption}
    return None


def _normalize_task(raw: Any, action: str, ask: str) -> dict[str, str] | None:
    if not isinstance(raw, dict):
        return None
    if str(raw.get("action") or "") != action or str(raw.get("ask") or "") != ask:
        return None
    return {
        "action": action,
        "ask": ask,
        "prompt": _bounded_text(raw.get("prompt"), 200),
    }


def normalize_board_v3(raw: Any) -> dict[str, Any] | None:
    """把 V3 判别联合标准化；任何未知能力均 fail closed。"""
    if not isinstance(raw, dict) or _int(raw.get("schema")) != BOARD_SCHEMA_VERSION:
        return None
    kind = str(raw.get("kind") or "")
    model = raw.get("model")
    task = raw.get("task")
    view = raw.get("view")
    if not isinstance(model, dict) or not isinstance(view, dict):
        return None

    if kind == "layer_sum":
        legacy = normalize_semantic_board(
            {
                "schema": 2,
                "kind": kind,
                "layers": model.get("layers"),
                "item": model.get("item"),
                "ask": task.get("ask") if isinstance(task, dict) else None,
                "reveal": view.get("reveal"),
            }
        )
        normalized_task = _normalize_task(task, "count", "total")
        if not legacy or not normalized_task:
            return None
        return {
            "schema": BOARD_SCHEMA_VERSION,
            "kind": kind,
            "model": {"layers": legacy["layers"], "item": legacy["item"]},
            "task": normalized_task,
            "view": {"reveal": "items_without_total"},
        }

    if kind == "path_count":
        legacy = normalize_semantic_board(
            {
                "schema": 2,
                "kind": kind,
                "start": model.get("start"),
                "target": model.get("target"),
                "moves": model.get("moves"),
                "ask": task.get("ask") if isinstance(task, dict) else None,
                "reveal": view.get("reveal"),
            }
        )
        normalized_task = _normalize_task(task, "enumerate", "number_of_paths")
        if not legacy or not normalized_task:
            return None
        return {
            "schema": BOARD_SCHEMA_VERSION,
            "kind": kind,
            "model": {
                "start": legacy["start"],
                "target": legacy["target"],
                "moves": legacy["moves"],
            },
            "task": normalized_task,
            "view": {"reveal": "rules_only"},
        }

    if kind == "snap_grid":
        rows, cols, tray = _int(model.get("rows")), _int(model.get("cols")), _int(model.get("tray"))
        normalized_task = _normalize_task(task, "arrange", "observe")
        if (
            rows is None
            or cols is None
            or tray is None
            or not 1 <= rows <= 8
            or not 1 <= cols <= 8
            or not 0 <= tray <= 64
            or not normalized_task
            or str(view.get("reveal") or "") != "empty_grid_and_tiles"
        ):
            return None
        return {
            "schema": BOARD_SCHEMA_VERSION,
            "kind": kind,
            "model": {"rows": rows, "cols": cols, "tray": tray},
            "task": normalized_task,
            "view": {"reveal": "empty_grid_and_tiles"},
        }

    if kind == "static_diagram":
        diagram = _normalize_static_diagram(model.get("diagram"))
        normalized_task = _normalize_task(task, "observe", "notice")
        if not diagram or not normalized_task or str(view.get("reveal") or "") != "model_only":
            return None
        return {
            "schema": BOARD_SCHEMA_VERSION,
            "kind": kind,
            "model": {"diagram": diagram},
            "task": normalized_task,
            "view": {"reveal": "model_only"},
        }

    if kind == "color_sequence":
        unit_raw = model.get("unit")
        count = _int(model.get("count"))
        item = _bounded_text(model.get("item"), 4, "花")
        normalized_task = _normalize_task(task, "predict", "color_at_end")
        reveal = str(view.get("reveal") or "")
        if (
            not isinstance(unit_raw, list)
            or not 2 <= len(unit_raw) <= 4
            or count is None
            or not 3 <= count <= 10
            or count < len(unit_raw)
            or any(str(color) not in COLOR_SEQUENCE_COLORS for color in unit_raw)
            or not item
            or not normalized_task
            or reveal not in ("hide_last", "all")
        ):
            return None
        return {
            "schema": BOARD_SCHEMA_VERSION,
            "kind": kind,
            "model": {
                "item": item,
                "unit": [str(color) for color in unit_raw],
                "count": count,
            },
            "task": normalized_task,
            "view": {"reveal": reveal},
        }

    if kind == "geometry_compass":
        labels = model.get("labels")
        normalized_task = _normalize_task(task, "construct", "compare_three_sides")
        if (
            str(model.get("construction") or "") != "equilateral_triangle"
            or not isinstance(labels, list)
            or len(labels) != 3
            or any(not _bounded_text(label, 2) for label in labels)
            or len(set(str(label) for label in labels)) != 3
            or not normalized_task
            or str(view.get("reveal") or "") != "stepwise"
        ):
            return None
        return {
            "schema": BOARD_SCHEMA_VERSION,
            "kind": kind,
            "model": {
                "construction": "equilateral_triangle",
                "labels": [_bounded_text(label, 2) for label in labels],
            },
            "task": normalized_task,
            "view": {"reveal": "stepwise"},
        }
    return None


def validate_board_v3(board: Any) -> str | None:
    normalized = normalize_board_v3(board)
    if normalized is None:
        return "V3 画板类型或参数不受支持"
    if normalized != board:
        return "V3 画板尚未标准化"
    return None


def _normalize_layer_sum(raw: dict[str, Any]) -> dict[str, Any] | None:
    values = raw.get("layers")
    if not isinstance(values, list) or not 1 <= len(values) <= 10:
        return None
    layers: list[int] = []
    for value in values:
        n = _int(value)
        if n is None or not 1 <= n <= 20:
            return None
        layers.append(n)
    if str(raw.get("ask") or "") != "total":
        return None
    reveal = str(raw.get("reveal") or "items_without_total")
    if reveal != "items_without_total":
        return None
    item = str(raw.get("item") or "块").strip()[:4] or "块"
    return {
        "schema": SCHEMA_VERSION,
        "kind": "layer_sum",
        "layers": layers,
        "item": item,
        "ask": "total",
        "purpose": "count_layers",
        "reveal": reveal,
    }


def _normalize_path_count(raw: dict[str, Any]) -> dict[str, Any] | None:
    start = _int(raw.get("start"))
    target = _int(raw.get("target"))
    if start is None or target is None or start < 0 or target <= start or target - start > 12:
        return None
    values = raw.get("moves")
    if not isinstance(values, list) or not 1 <= len(values) <= 4:
        return None
    moves: list[int] = []
    span = target - start
    for value in values:
        n = _int(value)
        if n is None or n <= 0 or n > span:
            return None
        if n not in moves:
            moves.append(n)
    if not moves or str(raw.get("ask") or "") != "number_of_paths":
        return None
    reveal = str(raw.get("reveal") or "rules_only")
    if reveal != "rules_only":
        return None
    return {
        "schema": SCHEMA_VERSION,
        "kind": "path_count",
        "start": start,
        "target": target,
        "moves": sorted(moves),
        "ask": "number_of_paths",
        "purpose": "explore_choices",
        "reveal": reveal,
    }


def normalize_semantic_board(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    if _int(raw.get("schema")) != SCHEMA_VERSION:
        return None
    kind = str(raw.get("kind") or "")
    if kind == "layer_sum":
        return _normalize_layer_sum(raw)
    if kind == "path_count":
        return _normalize_path_count(raw)
    return None


def validate_semantic_board(board: Any) -> str | None:
    if not isinstance(board, dict):
        return "语义画板不是对象"
    normalized = normalize_semantic_board(board)
    if normalized is None:
        return "语义画板类型或参数不受支持"
    if normalized != board:
        return "语义画板尚未标准化"
    return None


def first_question_for_board(board: dict[str, Any]) -> str:
    """由已校验的数学模型生成当前画板对应的问题，避免题目数字与画板漂移。"""
    if board.get("kind") == "layer_sum":
        counts = "、".join(str(n) for n in board["layers"])
        item = str(board.get("item") or "块")
        return f"从上到下每层分别有 {counts} {item}，这些层一共有多少{item}？"
    if board.get("kind") == "path_count":
        moves = [f"{n} 级" for n in board["moves"]]
        move_text = "、".join(moves[:-1]) + ("或" if len(moves) > 1 else "") + moves[-1]
        return (
            f"从第 {board['start']} 级出发，每次只能跳 {move_text}，"
            f"到第 {board['target']} 级一共有几种不同走法？"
        )
    return ""


def board_v3_from_legacy(
    semantic: Any = None,
    representation: str = "none",
    diagram: Any = None,
    prompt: str = "",
) -> dict[str, Any] | None:
    """读取旧题卡时一次性转换；新作者不应再输出旧字段。"""
    v2 = normalize_semantic_board(semantic)
    if semantic is not None and v2 is None:
        return None
    if v2 and v2["kind"] == "layer_sum":
        return normalize_board_v3(
            {
                "schema": 3,
                "kind": "layer_sum",
                "model": {"layers": v2["layers"], "item": v2["item"]},
                "task": {"action": "count", "ask": "total", "prompt": prompt},
                "view": {"reveal": "items_without_total"},
            }
        )
    if v2 and v2["kind"] == "path_count":
        return normalize_board_v3(
            {
                "schema": 3,
                "kind": "path_count",
                "model": {
                    "start": v2["start"],
                    "target": v2["target"],
                    "moves": v2["moves"],
                },
                "task": {"action": "enumerate", "ask": "number_of_paths", "prompt": prompt},
                "view": {"reveal": "rules_only"},
            }
        )
    if representation == "snap_grid":
        if not isinstance(diagram, dict) or str(diagram.get("type") or "") != "snap_grid":
            return None
        return normalize_board_v3(
            {
                "schema": 3,
                "kind": "snap_grid",
                "model": {
                    "rows": diagram.get("rows"),
                    "cols": diagram.get("cols"),
                    "tray": diagram.get("tray"),
                },
                "task": {"action": "arrange", "ask": "observe", "prompt": prompt},
                "view": {"reveal": "empty_grid_and_tiles"},
            }
        )
    if representation in STATIC_DIAGRAM_TYPES:
        if not isinstance(diagram, dict) or str(diagram.get("type") or "") != representation:
            return None
        return normalize_board_v3(
            {
                "schema": 3,
                "kind": "static_diagram",
                "model": {"diagram": diagram},
                "task": {"action": "observe", "ask": "notice", "prompt": prompt},
                "view": {"reveal": "model_only"},
            }
        )
    return None


def first_question_for_v3(board: dict[str, Any]) -> str:
    normalized = normalize_board_v3(board)
    if not normalized:
        return ""
    kind = normalized["kind"]
    model = normalized["model"]
    if kind == "layer_sum":
        return first_question_for_board(
            {
                "kind": kind,
                "layers": model["layers"],
                "item": model["item"],
            }
        )
    if kind == "path_count":
        return first_question_for_board(
            {
                "kind": kind,
                "start": model["start"],
                "target": model["target"],
                "moves": model["moves"],
            }
        )
    if kind == "geometry_compass":
        a, b, p = model["labels"]
        return (
            f"保持圆规宽度等于线段 {a}{b}，分别以 {a} 和 {b} 为圆心画圆。"
            f"两个圆的交点记作 {p}，你觉得 {p}{a}、{p}{b} 和 {a}{b} 谁更长，还是一样长？"
        )
    if kind == "color_sequence":
        unit = "、".join(COLOR_SEQUENCE_LABELS[color] for color in model["unit"])
        measure = ITEM_MEASURES.get(model["item"], "个")
        return (
            f"这些{model['item']}按{unit}重复排队。"
            f"第{model['count']}{measure}会是什么颜色？"
        )
    return normalized["task"]["prompt"]


def expand_color_sequence(unit: list[str], count: int) -> list[str]:
    return [unit[index % len(unit)] for index in range(count)]


def upgrade_legacy_pattern_board(board: dict[str, Any] | None) -> dict[str, Any] | None:
    """把找规律被误写成的单色点阵，收成真正带颜色的序列。"""
    if not isinstance(board, dict) or board.get("kind") != "static_diagram":
        return board
    model = board.get("model") if isinstance(board.get("model"), dict) else {}
    diagram = model.get("diagram") if isinstance(model.get("diagram"), dict) else {}
    task = board.get("task") if isinstance(board.get("task"), dict) else {}
    if str(diagram.get("type") or "") != "dots" or _int(diagram.get("rows")) != 1:
        return board
    blob = f"{diagram.get('caption') or ''} {task.get('prompt') or ''}"
    if "红" not in blob or "蓝" not in blob:
        return board
    count = _int(diagram.get("cols")) or 6
    if not 3 <= count <= 10:
        count = 6
    upgraded = normalize_board_v3(
        {
            "schema": BOARD_SCHEMA_VERSION,
            "kind": "color_sequence",
            "model": {"item": "花", "unit": ["red", "red", "blue"], "count": count},
            "task": {
                "action": "predict",
                "ask": "color_at_end",
                "prompt": _bounded_text(task.get("prompt"), 200),
            },
            "view": {"reveal": "hide_last"},
        }
    )
    return upgraded or board
