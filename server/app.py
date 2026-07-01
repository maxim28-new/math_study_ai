"""FastAPI 后端：对外提供网页、配置信息和一个流式的对话接口。

对话接口把孩子的消息连同"启发式教学系统提示词"一起发给大模型，
再把模型逐字返回的内容用 SSE（服务器推送事件）实时转发给网页。
"""

from __future__ import annotations

import json
from typing import Any, AsyncGenerator, Union

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
    # content 既可能是纯文字，也可能是多模态数组（含图片）——兼容 OpenAI 多模态格式。
    content: Union[str, list[dict[str, Any]]]


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
        # 是否允许拍照/上传题目（已配置密钥即开放；能否真正读图取决于所选模型是否支持视觉）。
        "vision_enabled": settings.is_configured,
    }


def _messages_have_image(messages: list[Message]) -> bool:
    for m in messages:
        if isinstance(m.content, list):
            for part in m.content:
                if isinstance(part, dict) and part.get("type") == "image_url":
                    return True
    return False


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


async def _transcribe(client: httpx.AsyncClient, content: list, headers: dict) -> str:
    """用视觉模型把一条含图片的消息"读"成纯文字（OCR 环节，绝不解题）。"""
    payload = {
        "model": settings.vision_model,
        "stream": False,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": tutor.TRANSCRIBE_PROMPT},
            {"role": "user", "content": content},
        ],
    }
    resp = await client.post(settings.chat_endpoint, json=payload, headers=headers)
    resp.raise_for_status()
    data = resp.json()
    return (data["choices"][0]["message"]["content"] or "").strip()


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
    headers = {
        "Authorization": f"Bearer {settings.api_key}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(120.0)) as client:
            # 第一步（OCR）：把带图片的消息先用视觉模型转写成文字，
            # 之后的"教学"环节永远交给文字模型，风格才一致、也不丢信息给弱模型去解。
            teaching_messages: list[dict] = []
            latest_transcript: str | None = None
            for m in req.messages:
                if isinstance(m.content, list) and any(
                    isinstance(p, dict) and p.get("type") == "image_url" for p in m.content
                ):
                    try:
                        transcript = await _transcribe(client, m.content, headers)
                    except httpx.HTTPError as exc:
                        yield _sse(
                            {
                                "error": f"读取照片时出错（视觉模型 {settings.vision_model}）：{exc}。请确认视觉模型支持看图、且接口地址/密钥正确。"
                            }
                        )
                        yield _sse({"done": True})
                        return
                    latest_transcript = transcript
                    # 保留孩子原本可能打的文字说明
                    typed = " ".join(
                        p.get("text", "") for p in m.content if isinstance(p, dict) and p.get("type") == "text"
                    ).strip()
                    combined = "（这是从我作业照片里读出来的题目）\n" + transcript
                    if typed:
                        combined = typed + "\n\n" + combined
                    teaching_messages.append({"role": m.role, "content": combined})
                else:
                    teaching_messages.append(m.model_dump())

            # 把"读到的题目"回传给前端，方便家长核对；OCR 读错时可以直接打字纠正。
            if latest_transcript:
                yield _sse({"transcript": latest_transcript})

            # 第二步（教学）：文字模型登场，做全部的苏格拉底式引导。
            payload = {
                "model": settings.model,
                "stream": True,
                "temperature": 0.7,
                "messages": [{"role": "system", "content": system_prompt}] + teaching_messages,
            }
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
