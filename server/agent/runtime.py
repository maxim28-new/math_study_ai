"""有上限的 Tutor Agent loop：观察 → 工具 → 校验 → 再说话。"""

from __future__ import annotations

import json
from typing import Any, AsyncGenerator

import httpx

from . import skills
from . import store
from . import tools
from . import validators as V
from . import workspace as WS
from .. import tutor
from .. import config as teaching_config
from ..config import settings


class ToolsUnsupportedError(RuntimeError):
    """当前模型接口不接受 function tools，调用方应回退到纯文字流。"""


def _assistant_record(message: dict[str, Any]) -> dict[str, Any]:
    record: dict[str, Any] = {"role": "assistant"}
    if message.get("content"):
        record["content"] = message.get("content")
    elif message.get("tool_calls"):
        record["content"] = None
    if message.get("tool_calls"):
        record["tool_calls"] = message["tool_calls"]
    return record


def _tool_record(call: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    fn = call.get("function") if isinstance(call.get("function"), dict) else {}
    return {
        "role": "tool",
        "tool_call_id": call.get("id") or "",
        "name": fn.get("name") or "unknown",
        "content": json.dumps(result, ensure_ascii=False),
    }


async def _iter_model_stream(resp, show_reasoning: bool) -> AsyncGenerator[dict[str, Any], None]:
    async for line in resp.aiter_lines():
        if not line or not line.startswith("data:"):
            continue
        data = line[len("data:"):].strip()
        if data == "[DONE]":
            break
        try:
            chunk = json.loads(data)
        except json.JSONDecodeError:
            continue
        choices = chunk.get("choices") or []
        if not choices:
            continue
        delta = choices[0].get("delta") or {}
        reasoning_piece = delta.get("reasoning_content")
        if reasoning_piece and show_reasoning:
            yield {"reasoning_delta": reasoning_piece}
        piece = delta.get("content")
        if piece:
            yield {"delta": piece}


def _parse_message(data: dict[str, Any]) -> dict[str, Any]:
    choices = data.get("choices") or []
    if not choices:
        return {}
    message = choices[0].get("message") if isinstance(choices[0], dict) else {}
    return message if isinstance(message, dict) else {}


async def _complete(client: httpx.AsyncClient, headers: dict[str, str], payload: dict[str, Any]) -> dict[str, Any]:
    resp = await client.post(settings.chat_endpoint, json=payload, headers=headers)
    detail = resp.text[:400]
    if resp.status_code == 400 and "tool" in detail.lower():
        raise ToolsUnsupportedError(detail)
    if resp.status_code != 200:
        raise httpx.HTTPStatusError(
            f"大模型接口返回错误（{resp.status_code}）。{detail}",
            request=resp.request,
            response=resp,
        )
    return resp.json()


def build_agent_prompt(
    topic: str,
    level: str,
    child_name: str,
    mode: str,
    card: dict[str, Any] | None,
    seen_terms: list[str],
    workspace: dict[str, Any],
    lesson: dict[str, Any] | None = None,
    lesson_event: str = "",
) -> str:
    base = tutor.build_system_prompt(
        topic, level, child_name, mode, card, seen_terms, agent=True,
        lesson=lesson, lesson_event=lesson_event,
    )
    visible = WS.visible_snapshot(workspace)
    compact = {
        "version": visible.get("version"),
        "representation": visible.get("representation"),
        "tile_count": visible.get("tile_count"),
        "shape": visible.get("shape"),
        "side": visible.get("side"),
        "item": visible.get("item"),
        "occupancy": visible.get("occupancy"),
        "row_counts": visible.get("row_counts"),
        "tray_left": visible.get("tray_left"),
        "objects": [
            {"id": obj.get("id"), "type": obj.get("type"), "attrs": obj.get("attrs")}
            for obj in visible.get("objects") or []
        ],
        "marked": visible.get("marked"),
        "emphasis": visible.get("emphasis"),
        "allowed_layers": (workspace.get("problem") or {}).get("allowed_layers") or [],
        "path_model": visible.get("path_model"),
        "sequence_count": visible.get("sequence_count"),
    }
    return (
        f"{base}\n\n{skills.SKILL_CATALOG}\n\n"
        "# 当前孩子看得见的工作区\n"
        "下面是程序校验后的可见状态。说话只能引用这些对象。\n"
        f"```json\n{json.dumps(compact, ensure_ascii=False)}\n```\n"
    )


async def run_tutor_agent(
    *,
    client: httpx.AsyncClient,
    headers: dict[str, str],
    teaching_messages: list[dict[str, Any]],
    topic: str,
    level: str,
    child_name: str,
    mode: str,
    card: dict[str, Any] | None,
    seen_terms: list[str],
    client_workspace: dict[str, Any] | None,
    thinking_on: bool,
    show_reasoning: bool,
    lesson: dict[str, Any] | None = None,
    lesson_event: str = "",
) -> AsyncGenerator[dict[str, Any], None]:
    stored = store.get((client_workspace or {}).get("id") if isinstance(client_workspace, dict) else None)
    workspace = WS.resolve_workspace(stored, client_workspace, card, topic)
    system_prompt = build_agent_prompt(
        topic, level, child_name, mode, card, seen_terms, workspace,
        lesson=lesson, lesson_event=lesson_event,
    )
    messages: list[dict[str, Any]] = [{"role": "system", "content": system_prompt}]
    messages.extend(teaching_messages)

    tool_extras = teaching_config.thinking_request_extras(
        settings.base_url, settings.model, False, settings.reasoning_effort
    )
    speak_extras = teaching_config.thinking_request_extras(
        settings.base_url, settings.model, thinking_on, settings.reasoning_effort
    )

    yield {"agent_status": "observe"}
    write_count = 0
    patches: list[dict[str, Any]] = []
    final_text = None
    tool_used = False

    for _round in range(V.MAX_TOOL_ROUNDS):
        payload = {
            "model": settings.model,
            "stream": False,
            "temperature": 0.4,
            "messages": messages,
            "tools": tools.TOOL_SCHEMAS,
            "tool_choice": "auto",
            **tool_extras,
        }
        data = await _complete(client, headers, payload)
        message = _parse_message(data)
        calls = message.get("tool_calls") if isinstance(message.get("tool_calls"), list) else []
        content = message.get("content") if isinstance(message.get("content"), str) else ""
        if not calls:
            final_text = content
            break
        tool_used = True
        messages.append(_assistant_record(message))
        for call in calls:
            if not isinstance(call, dict):
                continue
            fn = call.get("function") if isinstance(call.get("function"), dict) else {}
            name = str(fn.get("name") or "")
            if tools.is_write_tool(name) and write_count >= V.WRITE_TOOLS_PER_TURN:
                result = {"ok": False, "error": "write_limit"}
            else:
                result = tools.execute_tool(name, workspace, fn.get("arguments"))
                if result.get("ok") and tools.is_write_tool(name):
                    write_count += 1
                    patches.append({
                        "tool": name,
                        "created": result.get("created") or result.get("arranged") or result.get("emphasized"),
                        "version": workspace.get("version"),
                    })
            messages.append(_tool_record(call, result))
        if write_count >= V.WRITE_TOOLS_PER_TURN:
            messages.append({
                "role": "user",
                "content": "（工具已经执行完毕。现在只对孩子说一句自然语言，不要再调用工具，也不要描述失败的动作。）",
            })
            break

    store.put(workspace)
    yield {
        "workspace": workspace,
        "board_patch": {"version": workspace.get("version"), "ops": patches} if patches else None,
        "workspace_snapshot": WS.visible_snapshot(workspace),
    }

    if final_text:
        yield {"delta": final_text}
        return

    speak_messages = messages
    if tool_used:
        speak_messages = messages + [{
            "role": "user",
            "content": "（现在只对孩子说一句。不要调用工具，不要输出 JSON，不要提起工具或工作区这些词。）",
        }]
    payload = {
        "model": settings.model,
        "stream": True,
        "temperature": 0.7,
        "messages": speak_messages,
        "tools": tools.TOOL_SCHEMAS,
        "tool_choice": "none",
        **speak_extras,
    }
    async with client.stream("POST", settings.chat_endpoint, json=payload, headers=headers) as resp:
        if resp.status_code != 200:
            detail = (await resp.aread()).decode("utf-8", "ignore")
            yield {
                "error": (
                    f"大模型接口返回错误（{resp.status_code}）。"
                    f"请检查密钥、模型名和接口地址是否正确。\n{detail[:400]}"
                )
            }
            return
        async for event in _iter_model_stream(resp, show_reasoning):
            yield event
