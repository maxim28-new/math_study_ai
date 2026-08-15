"""语义画板 v2：先校验数学模型，再由前端选择专用渲染组件。"""

from __future__ import annotations

from typing import Any


SCHEMA_VERSION = 2
SUPPORTED_KINDS = ("layer_sum", "path_count")


def _int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
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
