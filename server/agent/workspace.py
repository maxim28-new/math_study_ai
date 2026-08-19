"""Math Workspace：对象、关系、版本与可见投影。"""

from __future__ import annotations

import copy
import json
import uuid
from typing import Any

from . import validators as V
from .. import lesson as lesson_state


def _empty_visibility() -> dict[str, list[str]]:
    return {"hidden": [], "emphasis": [], "marked": []}


def _empty_child_model() -> dict[str, Any]:
    return {
        "accepted_claims": [],
        "current_conjecture": "",
        "last_misconception": "",
        "focus_question": "",
    }


def new_id(prefix: str = "ws") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def clone(workspace: dict[str, Any]) -> dict[str, Any]:
    return copy.deepcopy(workspace)


def bump(workspace: dict[str, Any]) -> dict[str, Any]:
    workspace["version"] = int(workspace.get("version") or 0) + 1
    return workspace


def normalize_visibility(raw: Any) -> dict[str, list[str]]:
    vis = raw if isinstance(raw, dict) else {}
    out = _empty_visibility()
    for key in out:
        values = vis.get(key) or []
        if isinstance(values, list):
            out[key] = [item for item in values if isinstance(item, str) and item][:V.MAX_OBJECTS]
    return out


def from_dict(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    ws_id = V.clip_text(raw.get("id"), 80)
    version = V.as_int(raw.get("version"))
    objects = raw.get("objects")
    if not ws_id or version is None or version < 1 or not isinstance(objects, list):
        return None
    if len(objects) > V.MAX_OBJECTS:
        return None
    clean_objects: list[dict[str, Any]] = []
    seen: set[str] = set()
    for obj in objects:
        if not isinstance(obj, dict):
            return None
        oid = V.clip_text(obj.get("id"), 40)
        otype = V.clip_text(obj.get("type"), 24)
        if not oid or oid in seen or otype not in V.OBJECT_TYPES:
            return None
        seen.add(oid)
        attrs = obj.get("attrs") if isinstance(obj.get("attrs"), dict) else {}
        clean_objects.append({"id": oid, "type": otype, "attrs": copy.deepcopy(attrs)})
    relations = raw.get("relations") if isinstance(raw.get("relations"), list) else []
    clean_relations = []
    for rel in relations[:V.MAX_OBJECTS]:
        if not isinstance(rel, dict):
            continue
        rid = V.clip_text(rel.get("id"), 40)
        rtype = V.clip_text(rel.get("type"), 32)
        ids = rel.get("object_ids") if isinstance(rel.get("object_ids"), list) else []
        if not rid or rtype not in V.RELATION_TYPES:
            continue
        clean_relations.append({
            "id": rid,
            "type": rtype,
            "object_ids": [V.clip_text(i, 40) for i in ids if isinstance(i, str)][:V.MAX_OBJECTS],
            "attrs": copy.deepcopy(rel.get("attrs")) if isinstance(rel.get("attrs"), dict) else {},
        })
    problem = raw.get("problem") if isinstance(raw.get("problem"), dict) else {}
    view = raw.get("view") if isinstance(raw.get("view"), dict) else {}
    return {
        "id": ws_id,
        "version": version,
        "problem": copy.deepcopy(problem),
        "objects": clean_objects,
        "relations": clean_relations,
        "claims": [c for c in (raw.get("claims") or []) if isinstance(c, dict)][:40],
        "conjectures": [c for c in (raw.get("conjectures") or []) if isinstance(c, dict)][:40],
        "visibility": normalize_visibility(raw.get("visibility")),
        "view": {
            "representation": V.clip_text(view.get("representation"), 32) or "tiles",
            "camera": V.clip_text(view.get("camera"), 16) or "fit",
        },
        "child_model": {
            **_empty_child_model(),
            **(raw.get("child_model") if isinstance(raw.get("child_model"), dict) else {}),
        },
    }


def next_object_id(workspace: dict[str, Any], prefix: str) -> str:
    existing = {obj["id"] for obj in workspace.get("objects") or []}
    n = 1
    while f"{prefix}_{n}" in existing:
        n += 1
    return f"{prefix}_{n}"


def replace_relation(
    workspace: dict[str, Any],
    rtype: str,
    object_ids: list[str],
    attrs: dict[str, Any] | None = None,
) -> None:
    relations = [
        rel for rel in workspace.get("relations") or []
        if not (isinstance(rel, dict) and rel.get("type") == rtype)
    ]
    relations.append({
        "id": f"rel_{rtype}",
        "type": rtype,
        "object_ids": object_ids,
        "attrs": attrs or {},
    })
    workspace["relations"] = relations


def refresh_square_relation(workspace: dict[str, Any]) -> dict[str, Any]:
    check = V.forms_square(workspace)
    ids = [obj["id"] for obj in V.tiles(workspace, placed_only=True)]
    if check["ok"]:
        replace_relation(workspace, "forms_square", ids, {"side": check["side"]})
    else:
        workspace["relations"] = [
            rel for rel in workspace.get("relations") or []
            if not (isinstance(rel, dict) and rel.get("type") == "forms_square")
        ]
    return check


def visible_objects(workspace: dict[str, Any]) -> list[dict[str, Any]]:
    hidden = set(V.visibility_ids(workspace, "hidden"))
    return [obj for obj in workspace.get("objects") or [] if obj.get("id") not in hidden]


def visible_snapshot(workspace: dict[str, Any]) -> dict[str, Any]:
    vis_objects = visible_objects(workspace)
    hidden = set(V.visibility_ids(workspace, "hidden"))
    check = V.forms_square({"objects": vis_objects, "visibility": {"hidden": []}})
    representation = (workspace.get("view") or {}).get("representation") or "tiles"
    item = V.clip_text((workspace.get("problem") or {}).get("item"), 8) or "块"
    snapshot: dict[str, Any] = {
        "id": workspace.get("id"),
        "version": workspace.get("version"),
        "representation": representation,
        "objects": vis_objects,
        "visibility": normalize_visibility(workspace.get("visibility")),
        "view": workspace.get("view") or {},
        "tile_count": len([obj for obj in vis_objects if obj.get("type") == "tile"]),
        "shape": check["shape"],
        "side": check["side"],
        "item": item,
        "marked": [oid for oid in V.visibility_ids(workspace, "marked") if oid not in hidden],
        "emphasis": [oid for oid in V.visibility_ids(workspace, "emphasis") if oid not in hidden],
    }
    return snapshot


def inspect_payload(workspace: dict[str, Any], *, visible_only: bool = False) -> dict[str, Any]:
    if visible_only:
        hidden = set(V.visibility_ids(workspace, "hidden"))
        objects = visible_objects(workspace)
        relations = [
            rel for rel in workspace.get("relations") or []
            if isinstance(rel, dict) and not hidden.intersection(rel.get("object_ids") or [])
        ]
        return {
            "version": workspace.get("version"),
            "objects": objects,
            "relations": relations,
            "visibility": normalize_visibility(workspace.get("visibility")),
            "view": workspace.get("view"),
            "visible_snapshot": visible_snapshot(workspace),
        }
    return {
        "version": workspace.get("version"),
        "problem": workspace.get("problem"),
        "objects": workspace.get("objects"),
        "relations": workspace.get("relations"),
        "claims": workspace.get("claims"),
        "conjectures": workspace.get("conjectures"),
        "visibility": workspace.get("visibility"),
        "view": workspace.get("view"),
        "child_model": workspace.get("child_model"),
        "visible_snapshot": visible_snapshot(workspace),
    }


def _seed_shell(ws_id: str, topic: str, card: dict[str, Any], representation: str) -> dict[str, Any]:
    board = card.get("board") if isinstance(card.get("board"), dict) else {}
    model = board.get("model") if isinstance(board.get("model"), dict) else {}
    return {
        "id": ws_id,
        "version": 1,
        "problem": {
            "topic": topic,
            "goal": V.clip_text(card.get("insight"), 200),
            "hook": V.clip_text(card.get("hook"), 200),
            "givens": [],
            "board_kind": V.clip_text(board.get("kind"), 32),
            "item": V.clip_text(model.get("item"), 8) or "块",
            "first_question": V.clip_text(card.get("first_question"), 200),
            "allowed_layers": [],
            "insight_key": lesson_state.insight_key_of(card),
            "allowed_views": lesson_state.allowed_views_of(card, representation),
        },
        "objects": [],
        "relations": [],
        "claims": [],
        "conjectures": [],
        "visibility": _empty_visibility(),
        "view": {"representation": representation, "camera": "fit"},
        "child_model": _empty_child_model(),
    }


def seed_from_card(card: dict[str, Any] | None, topic: str, workspace_id: str | None = None) -> dict[str, Any]:
    card = card if isinstance(card, dict) else {}
    board = card.get("board") if isinstance(card.get("board"), dict) else {}
    kind = V.clip_text(board.get("kind"), 32)
    ws_id = V.clip_text(workspace_id, 80) or new_id("ws")
    model = board.get("model") if isinstance(board.get("model"), dict) else {}

    if kind == "layer_sum":
        layers = model.get("layers") if isinstance(model.get("layers"), list) else []
        parsed = [n for n in (V.as_int(x) for x in layers) if n and 1 <= n <= 20]
        ws = _seed_shell(ws_id, topic, card, "tiles")
        ws["problem"]["allowed_layers"] = parsed
        ws["problem"]["item"] = V.clip_text(model.get("item"), 8) or "块"
        if V.is_odd_square_layers(parsed):
            ws["objects"] = [{
                "id": "tile_1",
                "type": "tile",
                "attrs": {"gx": 0, "gy": 0, "layer": 1, "pending": False},
            }]
            ws["visibility"]["marked"] = ["tile_1"]
            refresh_square_relation(ws)
            return ws
        first = parsed[0] if parsed else 1
        objects = []
        for i in range(first):
            objects.append({
                "id": f"tile_{i + 1}",
                "type": "tile",
                "attrs": {"gx": i, "gy": 0, "layer": 1, "pending": False},
            })
        ws["objects"] = objects
        ws["view"]["representation"] = "layer_pile"
        return ws

    if kind == "geometry_compass":
        ws = _seed_shell(ws_id, topic, card, "geometry_compass")
        roles = ("compass", "center", "radius", "intersection", "segment", "equilateral")
        types = ("group", "point", "segment", "point", "segment", "group")
        ws["objects"] = [
            {"id": role, "type": types[i], "attrs": {"role": role}}
            for i, role in enumerate(roles)
        ]
        return ws

    if kind == "color_sequence":
        ws = _seed_shell(ws_id, topic, card, "color_sequence")
        ws["objects"] = [{"id": "pattern", "type": "group", "attrs": {"role": "pattern"}}]
        return ws

    if kind == "path_count":
        ws = _seed_shell(ws_id, topic, card, "path_count")
        ws["objects"] = [{"id": "path_board", "type": "group", "attrs": {"role": "path"}}]
        return ws

    if kind == "snap_grid":
        ws = _seed_shell(ws_id, topic, card, "snap_grid")
        ws["objects"] = [{"id": "grid", "type": "group", "attrs": {"role": "snap_grid"}}]
        return ws

    ws = _seed_shell(ws_id, topic, card, kind or "static")
    ws["objects"] = [{"id": "figure", "type": "group", "attrs": {"role": "figure"}}]
    return ws


def matches_card(workspace: dict[str, Any] | None, card: dict[str, Any] | None) -> bool:
    if not isinstance(workspace, dict) or not isinstance(card, dict):
        return False
    problem = workspace.get("problem") if isinstance(workspace.get("problem"), dict) else {}
    board = card.get("board") if isinstance(card.get("board"), dict) else {}
    if V.clip_text(problem.get("hook"), 200) != V.clip_text(card.get("hook"), 200):
        return False
    return V.clip_text(problem.get("board_kind"), 32) == V.clip_text(board.get("kind"), 32)


def resolve_workspace(
    stored: dict[str, Any] | None,
    client: dict[str, Any] | None,
    card: dict[str, Any] | None,
    topic: str,
) -> dict[str, Any]:
    client_ws = from_dict(client)
    stored_ws = from_dict(stored)
    if client_ws and matches_card(client_ws, card):
        if stored_ws and stored_ws.get("id") == client_ws.get("id") and stored_ws["version"] > client_ws["version"]:
            return stored_ws
        return client_ws
    if stored_ws and matches_card(stored_ws, card):
        return stored_ws
    return seed_from_card(card, topic)


def reset_to_seed(workspace: dict[str, Any], card: dict[str, Any] | None, topic: str) -> dict[str, Any]:
    seeded = seed_from_card(card, topic, workspace.get("id"))
    seeded["version"] = int(workspace.get("version") or 1) + 1
    return seeded


def to_json(workspace: dict[str, Any]) -> str:
    return json.dumps(workspace, ensure_ascii=False)
