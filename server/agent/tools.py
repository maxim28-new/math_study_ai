"""受控数学工具：schema、执行器、权限与失败回滚。"""

from __future__ import annotations

import json
from typing import Any, Callable

from . import validators as V
from . import workspace as WS

WRITE_TOOLS = {
    "board_highlight",
    "board_hide",
    "board_reveal",
    "board_add_tiles",
    "board_arrange",
    "board_group",
    "lesson_record_conjecture",
    "lesson_record_claim",
    "lesson_mark_child_acceptance",
    "board_switch_view",
}

READ_TOOLS = {
    "workspace_inspect",
    "workspace_inspect_visible",
    "math_check_claim",
}


def _fn(name: str, description: str, properties: dict[str, Any], required: list[str] | None = None) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required or [],
            },
        },
    }


TOOL_SCHEMAS: list[dict[str, Any]] = [
    _fn(
        "workspace_inspect",
        "读取完整数学工作区（含题目约束）。孩子看不见隐藏对象；提问时请改用 workspace_inspect_visible。",
        {},
    ),
    _fn(
        "workspace_inspect_visible",
        "读取孩子当前真正看见的对象、关系和形状。说话前应以此为准。",
        {},
    ),
    _fn(
        "math_check_claim",
        "检查一个可计算的数学关系是否成立。claim 可以是 forms_square，或 {type, equals, object_ids}。",
        {
            "claim": {
                "description": "forms_square，或 {type: forms_square|tile_count, equals?: number}",
            }
        },
        ["claim"],
    ),
    _fn(
        "board_highlight",
        "高亮若干已有对象，吸引注意。不改变数学事实。传入空列表可取消高亮。",
        {
            "object_ids": {"type": "array", "items": {"type": "string"}},
            "style": {"type": "string", "enum": ["focus"]},
        },
    ),
    _fn(
        "board_hide",
        "隐藏若干已有对象，孩子将看不见它们。",
        {"object_ids": {"type": "array", "items": {"type": "string"}}},
        ["object_ids"],
    ),
    _fn(
        "board_reveal",
        "重新显示被隐藏的对象。",
        {"object_ids": {"type": "array", "items": {"type": "string"}}},
        ["object_ids"],
    ),
    _fn(
        "board_add_tiles",
        "添加若干尚未摆好位置的积木。随后通常再调用 board_arrange。",
        {
            "count": {"type": "integer", "minimum": 1, "maximum": 16},
            "group_id": {"type": "string"},
        },
        ["count"],
    ),
    _fn(
        "board_arrange",
        "按有限布局摆放积木。outer_ring 把未摆好的积木围在当前正方形外面，补成更大的正方形。",
        {
            "object_ids": {"type": "array", "items": {"type": "string"}},
            "layout": {"type": "string", "enum": ["row", "grid", "outer_ring"]},
            "constraints": {
                "type": "object",
                "properties": {
                    "around": {"type": "string"},
                    "target_shape": {"type": "string", "enum": ["square"]},
                },
            },
        },
        ["layout"],
    ),
    _fn(
        "board_group",
        "把已有对象编成一组，便于之后一起引用。",
        {
            "object_ids": {"type": "array", "items": {"type": "string"}},
            "group_id": {"type": "string"},
        },
        ["object_ids"],
    ),
    _fn(
        "lesson_record_conjecture",
        "记下孩子的猜想，状态为 conjectured，不是已证明。",
        {
            "statement": {"type": "string"},
            "object_ids": {"type": "array", "items": {"type": "string"}},
        },
        ["statement"],
    ),
    _fn(
        "lesson_record_claim",
        "记下一条结论。可计算关系会先校验；不能自动验证的标为 proposed。",
        {
            "statement": {"type": "string"},
            "based_on": {"type": "array", "items": {"type": "string"}},
        },
        ["statement"],
    ),
    _fn(
        "lesson_mark_child_acceptance",
        "标记孩子已经认可某条 claim 或 conjecture。",
        {"claim_id": {"type": "string"}},
        ["claim_id"],
    ),
    _fn(
        "board_switch_view",
        "把当前数学对象换成题卡允许的另一种看法。只能用 allowed_views 里的 id。失败时不要假装已经换图。",
        {"view_id": {"type": "string"}},
        ["view_id"],
    ),
]


def _ok(workspace: dict[str, Any], **extra: Any) -> dict[str, Any]:
    snap = WS.visible_snapshot(workspace)
    payload = {
        "ok": True,
        "workspace_version": workspace.get("version"),
        "visible_snapshot": {
            "tile_count": snap["tile_count"],
            "shape": snap["shape"],
            "side": snap["side"],
            "marked": snap["marked"],
            "representation": snap["representation"],
        },
    }
    payload.update(extra)
    return payload


def _fail(error: str, **extra: Any) -> dict[str, Any]:
    payload = {"ok": False, "error": error}
    payload.update(extra)
    return payload


def _id_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [V.clip_text(item, 40) for item in value if isinstance(item, str) and V.clip_text(item, 40)][:V.MAX_OBJECTS]


def _expected_version(args: dict[str, Any], workspace: dict[str, Any]) -> str | None:
    expected = V.as_int(args.get("expected_workspace_version"))
    if expected is None:
        return None
    current = V.as_int(workspace.get("version"))
    if current is not None and expected != current:
        return "version_conflict"
    return None


def inspect(workspace: dict[str, Any], args: dict[str, Any]) -> dict[str, Any]:
    return _ok(workspace, data=WS.inspect_payload(workspace, visible_only=False))


def inspect_visible(workspace: dict[str, Any], args: dict[str, Any]) -> dict[str, Any]:
    return _ok(workspace, data=WS.inspect_payload(workspace, visible_only=True))


def check_claim(workspace: dict[str, Any], args: dict[str, Any]) -> dict[str, Any]:
    claim = args.get("claim")
    kind = ""
    equals = None
    if isinstance(claim, str):
        kind = V.clip_text(claim, 32)
    elif isinstance(claim, dict):
        kind = V.clip_text(claim.get("type") or claim.get("claim"), 32)
        equals = V.as_int(claim.get("equals"))
    if kind == "forms_square":
        result = V.forms_square(workspace)
        return _ok(workspace, claim=result)
    if kind == "tile_count":
        count = len(V.tiles(workspace, placed_only=True))
        result = {"ok": equals is None or count == equals, "type": "tile_count", "tile_count": count, "equals": equals}
        return _ok(workspace, claim=result)
    return _fail("unsupported_claim", claim=claim)


def highlight(workspace: dict[str, Any], args: dict[str, Any]) -> dict[str, Any]:
    ids = _id_list(args.get("object_ids"))
    if ids:
        missing = V.refs_exist(workspace, ids)
        if missing:
            return _fail(missing)
    workspace.setdefault("visibility", WS.normalize_visibility(workspace.get("visibility")))
    workspace["visibility"]["emphasis"] = ids
    WS.bump(workspace)
    return _ok(workspace, emphasized=ids)


def hide(workspace: dict[str, Any], args: dict[str, Any]) -> dict[str, Any]:
    ids = _id_list(args.get("object_ids"))
    if not ids:
        return _fail("object_ids_required")
    missing = V.refs_exist(workspace, ids)
    if missing:
        return _fail(missing)
    vis = workspace.setdefault("visibility", WS.normalize_visibility(workspace.get("visibility")))
    hidden = list(dict.fromkeys((vis.get("hidden") or []) + ids))
    vis["hidden"] = hidden
    vis["emphasis"] = [oid for oid in vis.get("emphasis") or [] if oid not in ids]
    vis["marked"] = [oid for oid in vis.get("marked") or [] if oid not in ids]
    WS.bump(workspace)
    return _ok(workspace, hidden=ids)


def reveal(workspace: dict[str, Any], args: dict[str, Any]) -> dict[str, Any]:
    ids = _id_list(args.get("object_ids"))
    if not ids:
        return _fail("object_ids_required")
    missing = V.refs_exist(workspace, ids)
    if missing:
        return _fail(missing)
    vis = workspace.setdefault("visibility", WS.normalize_visibility(workspace.get("visibility")))
    vis["hidden"] = [oid for oid in vis.get("hidden") or [] if oid not in ids]
    WS.bump(workspace)
    return _ok(workspace, revealed=ids)


def add_tiles(workspace: dict[str, Any], args: dict[str, Any]) -> dict[str, Any]:
    count = V.as_int(args.get("count"))
    if count is None or count < 1 or count > 16:
        return _fail("count_range")
    current = V.tiles(workspace, placed_only=False)
    if len(current) + count > V.MAX_TILES:
        return _fail("too_many_tiles")
    if len(workspace.get("objects") or []) + count > V.MAX_OBJECTS:
        return _fail("too_many_objects")
    created: list[str] = []
    placed = V.tiles(workspace, placed_only=True)
    layer = (V.square_side(placed) or 0) + 1
    group_id = V.clip_text(args.get("group_id"), 40)
    for _ in range(count):
        oid = WS.next_object_id(workspace, "tile")
        workspace.setdefault("objects", []).append({
            "id": oid,
            "type": "tile",
            "attrs": {"gx": None, "gy": None, "layer": layer, "pending": True},
        })
        created.append(oid)
    if group_id:
        existing = V.object_map(workspace).get(group_id)
        if existing and existing.get("type") == "group":
            members = existing.setdefault("attrs", {}).setdefault("members", [])
            members.extend(created)
        else:
            workspace["objects"].append({
                "id": group_id if group_id not in V.object_map(workspace) else WS.next_object_id(workspace, "group"),
                "type": "group",
                "attrs": {"members": created},
            })
    vis = workspace.setdefault("visibility", WS.normalize_visibility(workspace.get("visibility")))
    vis["marked"] = created
    WS.bump(workspace)
    return _ok(workspace, created=created, created_ids=created)


def _place(workspace: dict[str, Any], oid: str, gx: int, gy: int, layer: int) -> None:
    obj = V.object_map(workspace)[oid]
    attrs = obj.setdefault("attrs", {})
    attrs["gx"] = gx
    attrs["gy"] = gy
    attrs["layer"] = layer
    attrs["pending"] = False


def arrange(workspace: dict[str, Any], args: dict[str, Any]) -> dict[str, Any]:
    layout = V.clip_text(args.get("layout"), 24)
    if layout not in V.ARRANGE_LAYOUTS:
        return _fail("unknown_layout")
    ids = _id_list(args.get("object_ids")) or V.pending_tile_ids(workspace)
    if not ids:
        return _fail("no_tiles_to_arrange")
    missing = V.refs_exist(workspace, ids)
    if missing:
        return _fail(missing)
    for oid in ids:
        obj = V.object_map(workspace)[oid]
        if obj.get("type") != "tile":
            return _fail(f"not_a_tile:{oid}")

    if layout == "row":
        for i, oid in enumerate(ids):
            _place(workspace, oid, i, 0, 1)
        vis = workspace.setdefault("visibility", WS.normalize_visibility(workspace.get("visibility")))
        vis["marked"] = ids
        WS.refresh_square_relation(workspace)
        WS.bump(workspace)
        return _ok(workspace, arranged=ids, layout=layout)

    if layout == "grid":
        n = len(ids)
        side = int(n ** 0.5)
        if side * side != n or side < 1 or side > V.MAX_TILE_SIDE:
            return _fail("grid_requires_square_count")
        for i, oid in enumerate(ids):
            _place(workspace, oid, i % side, i // side, side)
        vis = workspace.setdefault("visibility", WS.normalize_visibility(workspace.get("visibility")))
        vis["marked"] = ids
        WS.refresh_square_relation(workspace)
        WS.bump(workspace)
        return _ok(workspace, arranged=ids, layout=layout, side=side)

    # outer_ring
    placed = [obj for obj in V.tiles(workspace, placed_only=True) if obj["id"] not in ids]
    side = V.square_side(placed)
    if side is None:
        return _fail("outer_ring_needs_current_square")
    needed = 2 * side + 1
    if len(ids) != needed:
        return _fail("outer_ring_count", needed=needed, got=len(ids))
    allowed = (workspace.get("problem") or {}).get("allowed_layers") or []
    if allowed and needed not in allowed:
        return _fail("layer_not_in_problem", needed=needed, allowed=allowed)
    positions: list[tuple[int, int]] = [(side, y) for y in range(side)]
    positions.extend((x, side) for x in range(side + 1))
    for oid, (gx, gy) in zip(ids, positions):
        _place(workspace, oid, gx, gy, side + 1)
    vis = workspace.setdefault("visibility", WS.normalize_visibility(workspace.get("visibility")))
    vis["marked"] = ids
    check = WS.refresh_square_relation(workspace)
    WS.bump(workspace)
    created_relations = ["rel_forms_square"] if check.get("ok") else []
    return _ok(workspace, arranged=ids, layout=layout, side=check.get("side") or 0, created_relations=created_relations)


def group(workspace: dict[str, Any], args: dict[str, Any]) -> dict[str, Any]:
    ids = _id_list(args.get("object_ids"))
    if not ids:
        return _fail("object_ids_required")
    missing = V.refs_exist(workspace, ids)
    if missing:
        return _fail(missing)
    group_id = V.clip_text(args.get("group_id"), 40) or WS.next_object_id(workspace, "group")
    known = V.object_map(workspace)
    if group_id in known:
        obj = known[group_id]
        if obj.get("type") != "group":
            return _fail("group_id_taken")
        obj.setdefault("attrs", {})["members"] = ids
    else:
        workspace.setdefault("objects", []).append({
            "id": group_id,
            "type": "group",
            "attrs": {"members": ids},
        })
    WS.replace_relation(workspace, "same_group", [group_id, *ids], {"group_id": group_id})
    WS.bump(workspace)
    return _ok(workspace, group_id=group_id, members=ids)


def record_conjecture(workspace: dict[str, Any], args: dict[str, Any]) -> dict[str, Any]:
    statement = V.clip_text(args.get("statement"))
    if not statement:
        return _fail("statement_required")
    ids = _id_list(args.get("object_ids"))
    if ids:
        missing = V.refs_exist(workspace, ids)
        if missing:
            return _fail(missing)
    item = {
        "id": f"conj_{len(workspace.get('conjectures') or []) + 1}",
        "statement": statement,
        "object_ids": ids,
        "status": "conjectured",
    }
    workspace.setdefault("conjectures", []).append(item)
    workspace.setdefault("child_model", {})["current_conjecture"] = statement
    WS.bump(workspace)
    return _ok(workspace, conjecture=item)


def record_claim(workspace: dict[str, Any], args: dict[str, Any]) -> dict[str, Any]:
    statement = V.clip_text(args.get("statement"))
    if not statement:
        return _fail("statement_required")
    based_on = _id_list(args.get("based_on"))
    square = V.forms_square(workspace)
    status = "proposed"
    if "正方形" in statement or "square" in statement.lower():
        status = "observed" if square["ok"] else "proposed"
    item = {
        "id": f"claim_{len(workspace.get('claims') or []) + 1}",
        "statement": statement,
        "based_on": based_on,
        "status": status,
        "accepted_by_child": False,
    }
    workspace.setdefault("claims", []).append(item)
    WS.bump(workspace)
    return _ok(workspace, claim=item)


def mark_child_acceptance(workspace: dict[str, Any], args: dict[str, Any]) -> dict[str, Any]:
    claim_id = V.clip_text(args.get("claim_id"), 40)
    if not claim_id:
        return _fail("claim_id_required")
    for item in (workspace.get("claims") or []) + (workspace.get("conjectures") or []):
        if isinstance(item, dict) and item.get("id") == claim_id:
            item["accepted_by_child"] = True
            accepted = workspace.setdefault("child_model", {}).setdefault("accepted_claims", [])
            if claim_id not in accepted:
                accepted.append(claim_id)
            WS.bump(workspace)
            return _ok(workspace, claim_id=claim_id)
    return _fail("unknown_claim")


def switch_view(workspace: dict[str, Any], args: dict[str, Any]) -> dict[str, Any]:
    view_id = V.clip_text(args.get("view_id"), 32)
    if not view_id:
        return _fail("view_id_required")
    problem = workspace.get("problem") if isinstance(workspace.get("problem"), dict) else {}
    allowed = problem.get("allowed_views") if isinstance(problem.get("allowed_views"), list) else []
    names = [str(item).strip() for item in allowed if str(item).strip()]
    current = ""
    view = workspace.get("view") if isinstance(workspace.get("view"), dict) else {}
    current = str(view.get("representation") or "")
    if not names:
        names = [current] if current else []
    if view_id not in names:
        return _fail("view_not_allowed", view_id=view_id, allowed=names)
    workspace.setdefault("view", {})
    workspace["view"]["representation"] = view_id
    WS.bump(workspace)
    return _ok(workspace, view_id=view_id)


EXECUTORS: dict[str, Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]] = {
    "workspace_inspect": inspect,
    "workspace_inspect_visible": inspect_visible,
    "math_check_claim": check_claim,
    "board_highlight": highlight,
    "board_hide": hide,
    "board_reveal": reveal,
    "board_add_tiles": add_tiles,
    "board_arrange": arrange,
    "board_group": group,
    "lesson_record_conjecture": record_conjecture,
    "lesson_record_claim": record_claim,
    "lesson_mark_child_acceptance": mark_child_acceptance,
    "board_switch_view": switch_view,
}


def parse_arguments(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw.strip():
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        return data if isinstance(data, dict) else {}
    return {}


def execute_tool(name: str, workspace: dict[str, Any], arguments: Any) -> dict[str, Any]:
    if name not in EXECUTORS:
        return _fail("unknown_tool", tool=name)
    args = parse_arguments(arguments)
    unknown = [key for key in args if key not in {"expected_workspace_version", "idempotency_key"}
               and key not in _allowed_keys(name)]
    if unknown:
        return _fail("unknown_field", fields=unknown)
    conflict = _expected_version(args, workspace)
    if conflict:
        return _fail(conflict, workspace_version=workspace.get("version"))
    draft = workspace if name in READ_TOOLS else WS.clone(workspace)
    result = EXECUTORS[name](draft, args)
    if result.get("ok") and name in WRITE_TOOLS:
        workspace.clear()
        workspace.update(draft)
    return result


def _allowed_keys(name: str) -> set[str]:
    schema = next((item["function"]["parameters"]["properties"] for item in TOOL_SCHEMAS if item["function"]["name"] == name), {})
    return set(schema.keys())


def add_next_odd_ring(workspace: dict[str, Any]) -> dict[str, Any]:
    """孩子按钮与测试共用：等价于 add_tiles(2k+1) + arrange(outer_ring)。"""
    draft = WS.clone(workspace)
    placed = V.tiles(draft, placed_only=True)
    side = V.square_side(placed)
    if side is None:
        return _fail("outer_ring_needs_current_square")
    count = 2 * side + 1
    added = add_tiles(draft, {"count": count})
    if not added.get("ok"):
        return added
    arranged = arrange(draft, {"layout": "outer_ring"})
    if not arranged.get("ok"):
        return arranged
    workspace.clear()
    workspace.update(draft)
    arranged["workspace"] = workspace
    return arranged


def is_write_tool(name: str) -> bool:
    return name in WRITE_TOOLS
