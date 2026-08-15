"""FastAPI 后端：对外提供网页、配置信息和一个流式的对话接口。

对话接口把孩子的消息连同"启发式教学系统提示词"一起发给大模型，
再把模型逐字返回的内容用 SSE（服务器推送事件）实时转发给网页。
"""

from __future__ import annotations

import json
from typing import Any, AsyncGenerator, Optional, Union

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import asr
from . import author
from . import config as teaching_config
from .config import WEB_DIR, settings
from . import gate
from . import tutor

app = FastAPI(title="小欧 · 启发式数学老师")

# 允许微信小程序、GitHub Pages 等跨域调用 API（密钥仍在服务端 .env）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def require_access_code(request, call_next):
    """未输入验证码时，页面跳转到门禁，接口返回 401。"""
    if request.method == "OPTIONS":
        return await call_next(request)
    access_code = teaching_config.settings.access_code
    path = request.url.path
    if gate.request_unlocked(
        access_code,
        request.cookies.get(gate.COOKIE_NAME),
        request.headers.get("x-access-code", ""),
    ) or gate.is_public_path(path):
        return await call_next(request)
    if request.method == "GET" and (
        path == "/" or path.endswith(".html") or "text/html" in request.headers.get("accept", "")
    ):
        return RedirectResponse(url="/gate.html", status_code=302)
    return JSONResponse({"ok": False, "error": "请先输入验证码"}, status_code=401)


@app.middleware("http")
async def disable_frontend_cache(request, call_next):
    response = await call_next(request)
    path = request.url.path
    if path == "/" or path.endswith((".html", ".css", ".js")):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        response.headers["Pragma"] = "no-cache"
    return response


class Message(BaseModel):
    role: str
    # content 既可能是纯文字，也可能是多模态数组（含图片）——兼容 OpenAI 多模态格式。
    content: Union[str, list[dict[str, Any]]]


class ChatRequest(BaseModel):
    messages: list[Message] = Field(default_factory=list)
    topic: str = tutor.DEFAULT_TOPIC_KEY
    level: str = tutor.DEFAULT_LEVEL
    child_name: str = ""
    mode: str = tutor.DEFAULT_MODE
    # 探索模式下点"出个新题"：追加一条出题指令给模型（不进入前端展示的历史）。
    kickoff: bool = False
    # 思考模式：前端可按请求覆盖 .env 默认值（None=沿用默认）。
    thinking: Optional[bool] = None
    show_reasoning: Optional[bool] = None
    card: Optional[dict[str, Any]] = None


class UnlockRequest(BaseModel):
    code: str = ""


@app.post("/api/unlock")
def unlock(req: UnlockRequest, request: Request, response: Response):
    access_code = teaching_config.settings.access_code
    if not access_code:
        return {"ok": True}
    ip = gate.client_ip(request)
    if gate.unlock_limiter.blocked(ip):
        return JSONResponse(
            {"ok": False, "error": "试得太勤了，请稍后再试"},
            status_code=429,
        )
    if not gate.codes_match(req.code, access_code):
        gate.unlock_limiter.fail(ip)
        return JSONResponse({"ok": False, "error": "验证码不对"}, status_code=401)
    gate.unlock_limiter.success(ip)
    forwarded_https = request.headers.get("x-forwarded-proto", "").lower() == "https"
    response.set_cookie(
        gate.COOKIE_NAME,
        gate.sign_cookie(access_code),
        max_age=gate.COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=request.url.scheme == "https" or forwarded_https,
        path="/",
    )
    return {"ok": True}


@app.get("/api/health")
def health() -> dict:
    """小程序 / 运维探测：确认服务在线且密钥已配置。"""
    return {"ok": True, "configured": settings.is_configured}


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
        "modes": tutor.get_modes_payload(),
        "default_mode": tutor.DEFAULT_MODE,
        "quick_actions": tutor.QUICK_ACTIONS,
        "pipeline": settings.pipeline,
        "vision_enabled": settings.photo_enabled,
        "thinking_enabled": settings.thinking_enabled,
        "show_reasoning": settings.show_reasoning,
        "voice_enabled": settings.voice_enabled,
        "author_engines": author.engine_payloads(),
        "default_author": settings.author_engine,
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


async def _transcribe(client: httpx.AsyncClient, content: list) -> str:
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
    headers = {
        "Authorization": f"Bearer {settings.vision_api_key}",
        "Content-Type": "application/json",
    }
    resp = await client.post(settings.vision_chat_endpoint, json=payload, headers=headers)
    resp.raise_for_status()
    data = resp.json()
    return (data["choices"][0]["message"]["content"] or "").strip()


async def _yield_stream_chunks(resp, show_reasoning: bool) -> AsyncGenerator[str, None]:
    """把 OpenAI 兼容流式响应解析成 SSE 事件。"""
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
            yield _sse({"reasoning_delta": reasoning_piece})
        piece = delta.get("content")
        if piece:
            yield _sse({"delta": piece})


async def _prepare_split_messages(
    client: httpx.AsyncClient, messages: list[Message]
) -> tuple[list[dict], str | None]:
    """split 模式：OCR 转写图片为文字，返回教学消息列表与最新转写文本。"""
    teaching_messages: list[dict] = []
    latest_transcript: str | None = None
    for m in messages:
        if isinstance(m.content, list) and any(
            isinstance(p, dict) and p.get("type") == "image_url" for p in m.content
        ):
            if not settings.is_vision_configured:
                raise ValueError(
                    "还没有配置视觉模型，暂时不能拍照读题。"
                    "请在 .env 里填写 LLM_VISION_BASE_URL、LLM_VISION_API_KEY、LLM_VISION_MODEL"
                    "（可以和文字模型用不同服务商，例如文字用 DeepSeek、OCR 用通义 qwen-vl-plus）。"
                    "或者改用 LLM_PIPELINE=unified，用一个多模态模型（如 qwen3.7-plus）包办全部。"
                )
            try:
                transcript = await _transcribe(client, m.content)
            except httpx.HTTPError as exc:
                raise ValueError(
                    f"读取照片时出错（视觉模型 {settings.vision_model} @ {settings.vision_base_url}）：{exc}。"
                    "请检查 LLM_VISION_BASE_URL / LLM_VISION_API_KEY / LLM_VISION_MODEL 是否正确。"
                ) from exc
            latest_transcript = transcript
            typed = " ".join(
                p.get("text", "") for p in m.content if isinstance(p, dict) and p.get("type") == "text"
            ).strip()
            combined = "（这是从我作业照片里读出来的题目）\n" + transcript
            if typed:
                combined = typed + "\n\n" + combined
            teaching_messages.append({"role": m.role, "content": combined})
        else:
            teaching_messages.append(m.model_dump())
    return teaching_messages, latest_transcript


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

    system_prompt = tutor.build_system_prompt(
        req.topic, req.level, req.child_name, req.mode, req.card
    )
    text_headers = {
        "Authorization": f"Bearer {settings.api_key}",
        "Content-Type": "application/json",
    }

    # 思考模式：请求可覆盖 .env 默认；开启时默认展示思考过程。
    thinking_on = settings.thinking_enabled if req.thinking is None else req.thinking
    if req.show_reasoning is not None:
        show_reasoning = req.show_reasoning
    elif req.thinking is not None:
        show_reasoning = thinking_on  # 前端明确开了思考 → 默认展示
    else:
        show_reasoning = settings.show_reasoning
    thinking_extras = teaching_config.thinking_request_extras(
        settings.base_url, settings.model, thinking_on, settings.reasoning_effort
    )

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(120.0)) as client:
            if settings.is_unified:
                # unified 模式：多模态模型直接看图+教学，不经过 OCR。
                teaching_messages = [m.model_dump() for m in req.messages]
            else:
                # split 模式：视觉模型 OCR → 文字模型教学。
                try:
                    teaching_messages, latest_transcript = await _prepare_split_messages(
                        client, req.messages
                    )
                except ValueError as exc:
                    yield _sse({"error": str(exc)})
                    yield _sse({"done": True})
                    return
                if latest_transcript:
                    yield _sse({"transcript": latest_transcript})

            # 探索模式点"出个新题"：临时追加一条出题指令（不进入前端展示的历史）。
            if req.kickoff and req.mode == "explore":
                kickoff = tutor.EXPLORE_KICKOFF_WITH_CARD if req.card else tutor.EXPLORE_KICKOFF
                teaching_messages = teaching_messages + [
                    {"role": "user", "content": kickoff}
                ]

            payload = {
                "model": settings.model,
                "stream": True,
                "temperature": 0.7,
                "messages": [{"role": "system", "content": system_prompt}] + teaching_messages,
                **thinking_extras,
            }
            async with client.stream(
                "POST", settings.chat_endpoint, json=payload, headers=text_headers
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

                async for chunk in _yield_stream_chunks(resp, show_reasoning):
                    yield chunk
    except httpx.HTTPError as exc:
        yield _sse({"error": f"连接大模型时出错：{exc}"})

    yield _sse({"done": True})


class AuthorRequest(BaseModel):
    topic: str = tutor.DEFAULT_TOPIC_KEY
    level: str = tutor.DEFAULT_LEVEL
    engine: str = ""
    recent: list[str] = Field(default_factory=list)


@app.post("/api/author")
async def author_card(req: AuthorRequest) -> JSONResponse:
    try:
        card = await author.author_problem(req.topic, req.level, req.recent, req.engine or None)
    except ValueError as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)
    except httpx.HTTPError:
        return JSONResponse({"ok": False, "error": "出题大脑这会儿有点忙，再试一次。"}, status_code=502)
    return JSONResponse({"ok": True, "card": card})


class TranscribeRequest(BaseModel):
    audio: str = ""
    mime: str = "audio/webm"


@app.post("/api/transcribe")
async def transcribe_voice(req: TranscribeRequest) -> JSONResponse:
    raw = asr.decode_audio_payload(req.audio)
    if not raw:
        return JSONResponse({"ok": False, "error": "没有听到声音，再说一次吧。"}, status_code=400)
    if len(raw) > asr.MAX_AUDIO_BYTES:
        return JSONResponse({"ok": False, "error": "这段话有点长，分开说给小欧听吧。"}, status_code=413)
    if not settings.voice_enabled:
        return JSONResponse({"ok": False, "error": "小欧这边还没接上耳朵。"}, status_code=400)
    try:
        text = await asr.transcribe_audio(raw, req.mime or "audio/webm")
    except httpx.HTTPError:
        return JSONResponse({"ok": False, "error": "小欧没听清，稍后再试一次。"}, status_code=502)
    except ValueError as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)
    if not text:
        return JSONResponse({"ok": False, "error": "刚才没听清，再说一次吧。"}, status_code=400)
    return JSONResponse({"ok": True, "text": text})


@app.post("/api/chat")
async def chat(req: ChatRequest) -> StreamingResponse:
    return StreamingResponse(
        _stream_reply(req),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/")
def index() -> RedirectResponse:
    # 换 URL，避免浏览器继续用已经打开的旧桌面页。
    return RedirectResponse(url="/index.html?v=activity-stage", status_code=302)


# 其余静态资源（css / js）
app.mount("/", StaticFiles(directory=WEB_DIR), name="static")
