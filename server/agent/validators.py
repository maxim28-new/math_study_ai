"""数学关系与工作区一致性校验。"""

from __future__ import annotations

from typing import Any


MAX_OBJECTS = 80
MAX_TILES = 64
MAX_TILE_SIDE = 8
MAX_TEXT = 200
WRITE_TOOLS_PER_TURN = 3
MAX_TOOL_ROUNDS = 4


OBJECT_TYPES = {
    "tile",
    "point",
    "segment",
    "circle",
    "number",
    "interval",
    "bar",
    "sequence_item",
    "group",
}

RELATION_TYPES = {
    "equal_length",
    "same_group",
    "ordered_before",
    "contains",
    "intersects",
    "adjacent",
    "forms_rectangle",
    "forms_square",
    "sum_of",
}

ARRANGE_LAYOUTS = {"row", "grid", "outer_ring"}


def as_int(value: Any) -> int | None:
    if isinstance(value, bool) or value is None or value == "":
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str) and value.strip().lstrip("-").isdigit():
        return int(value.strip())
    return None


def clip_text(value: Any, limit: int = MAX_TEXT) -> str:
    return str(value or "").strip()[:limit]


def object_map(workspace: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for obj in workspace.get("objects") or []:
        if isinstance(obj, dict) and isinstance(obj.get("id"), str) and obj["id"]:
            out[obj["id"]] = obj
    return out


def tiles(workspace: dict[str, Any], *, placed_only: bool = False) -> list[dict[str, Any]]:
    found = []
    hidden = set(visibility_ids(workspace, "hidden"))
    for obj in workspace.get("objects") or []:
        if not isinstance(obj, dict) or obj.get("type") != "tile":
            continue
        if obj.get("id") in hidden:
            continue
        attrs = obj.get("attrs") if isinstance(obj.get("attrs"), dict) else {}
        if placed_only and (as_int(attrs.get("gx")) is None or as_int(attrs.get("gy")) is None):
            continue
        found.append(obj)
    return found


def visibility_ids(workspace: dict[str, Any], key: str) -> list[str]:
    vis = workspace.get("visibility") if isinstance(workspace.get("visibility"), dict) else {}
    raw = vis.get(key) or []
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, str) and item]


def pending_tile_ids(workspace: dict[str, Any]) -> list[str]:
    ids = []
    for obj in tiles(workspace, placed_only=False):
        attrs = obj.get("attrs") if isinstance(obj.get("attrs"), dict) else {}
        if attrs.get("pending") or as_int(attrs.get("gx")) is None:
            ids.append(str(obj["id"]))
    return ids


def refs_exist(workspace: dict[str, Any], ids: list[str]) -> str | None:
    known = object_map(workspace)
    for oid in ids:
        if oid not in known:
            return f"unknown_object:{oid}"
    return None


def tile_positions(tile_objs: list[dict[str, Any]]) -> list[tuple[int, int]] | None:
    positions: list[tuple[int, int]] = []
    seen: set[tuple[int, int]] = set()
    for obj in tile_objs:
        attrs = obj.get("attrs") if isinstance(obj.get("attrs"), dict) else {}
        gx = as_int(attrs.get("gx"))
        gy = as_int(attrs.get("gy"))
        if gx is None or gy is None:
            return None
        pos = (gx, gy)
        if pos in seen:
            return None
        seen.add(pos)
        positions.append(pos)
    return positions


def square_side(tile_objs: list[dict[str, Any]]) -> int | None:
    positions = tile_positions(tile_objs)
    if positions is None:
        return None
    n = len(positions)
    if n <= 0:
        return None
    side = int(n ** 0.5)
    if side * side != n or side > MAX_TILE_SIDE:
        return None
    xs = [p[0] for p in positions]
    ys = [p[1] for p in positions]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    if max_x - min_x != side - 1 or max_y - min_y != side - 1:
        return None
    expected = {(min_x + x, min_y + y) for x in range(side) for y in range(side)}
    if set(positions) != expected:
        return None
    return side


def forms_square(workspace: dict[str, Any]) -> dict[str, Any]:
    pending = pending_tile_ids(workspace)
    placed = tiles(workspace, placed_only=True)
    if pending:
        return {
            "ok": False,
            "type": "forms_square",
            "tile_count": len(placed),
            "side": 0,
            "shape": "pending",
            "pending": len(pending),
        }
    side = square_side(placed)
    return {
        "ok": side is not None,
        "type": "forms_square",
        "tile_count": len(placed),
        "side": side or 0,
        "shape": "square" if side else "other",
    }


def is_odd_square_layers(layers: Any) -> bool:
    if not isinstance(layers, list) or len(layers) < 2:
        return False
    parsed = [as_int(n) for n in layers]
    return all(n is not None and n == 2 * i + 1 for i, n in enumerate(parsed))
