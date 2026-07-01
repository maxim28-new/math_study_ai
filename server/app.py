"""FastAPI 后端：对外提供网页、配置信息和一个流式的对话接口。

对话接口把孩子的消息连同"启发式教学系统提示词"一起发给大模型，
再把模型逐字返回的内容用 SSE（服务器推送事件）实时转发给网页。
"""

from __future__ import annotations

import json
from typing import AsyncGenerator

import httpx
from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .config import WEB_DIR, settings
from . import tutor

app = FastAPI(title="小欧 · 启发式数学老师")


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[Message] = Field(default_factory=list)
    topic: str = tutor.DEFAULT_TOPIC_KEY
    level: str = tutor.DEFAULT_LEVEL
    child_name: str = ""


@app.get("/api/config")
def get_config() -> dict:
    """网页启动时读取：是否已配置密钥、有哪些主题 / 难度 / 快捷按钮。"""
    return {
        "configured": settings.is_configured,
        "model": settings.model if settings.is_configured else "",
        "topics": tutor.get_topics_payload(),
        "levels": [
            {"key": k, "desc": v} for k, v in tutor.LEVELS.items()
        ],
        "default_topic": tutor.DEFAULT_TOPIC_KEY,
        "default_level": tutor.DEFAULT_LEVEL,
        "quick_actions": tutor.QUICK_ACTIONS,
    }


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


async def _stream_reply(req: ChatRequest) -> AsyncGenerator[str, None]:
    if not settings.is_configured:
        yield _sse(
            {
                "error": (
                    "还没有连接大模型。请把项目里的 .env.example 复制成 .env，"
                    "填入你的 API 密钥后重新启动，就能和小欧对话啦。"
                )
            }
        )
        yield _sse({"done": True})
        return

    system_prompt = tutor.build_system_prompt(req.topic, req.level, req.child_name)
    payload = {
        "model": settings.model,
        "stream": True,
        "temperature": 0.7,
        "messages": [{"role": "system", "content": system_prompt}]
        + [m.model_dump() for m in req.messages],
    }
    headers = {
        "Authorization": f"Bearer {settings.api_key}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(120.0)) as client:
            async with client.stream(
                "POST", settings.chat_endpoint, json=payload, headers=headers
            ) as resp:
                if resp.status_code != 200:
                    detail = (await resp.aread()).decode("utf-8", "ignore")
                    yield _sse(
                        {
                            "error": f"大模型接口返回错误（{resp.status_code}）。请检查密钥、模型名和接口地址是否正确。\n{detail[:400]}"
                        }
                    )
                    yield _sse({"done": True})
                    return

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
                    piece = delta.get("content")
                    if piece:
                        yield _sse({"delta": piece})
    except httpx.HTTPError as exc:
        yield _sse({"error": f"连接大模型时出错：{exc}"})

    yield _sse({"done": True})


@app.post("/api/chat")
async def chat(req: ChatRequest) -> StreamingResponse:
    return StreamingResponse(
        _stream_reply(req),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/")
def index() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


# 其余静态资源（css / js）
app.mount("/", StaticFiles(directory=WEB_DIR), name="static")
