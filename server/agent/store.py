"""进程内 workspace 缓存。刷新后可由客户端 snapshot 恢复。"""

from __future__ import annotations

from collections import OrderedDict
from typing import Any

_MAX = 200
_store: OrderedDict[str, dict[str, Any]] = OrderedDict()


def get(workspace_id: str | None) -> dict[str, Any] | None:
    if not workspace_id or workspace_id not in _store:
        return None
    _store.move_to_end(workspace_id)
    return _store[workspace_id]


def put(workspace: dict[str, Any]) -> None:
    ws_id = str(workspace.get("id") or "")
    if not ws_id:
        return
    _store[ws_id] = workspace
    _store.move_to_end(ws_id)
    while len(_store) > _MAX:
        _store.popitem(last=False)
