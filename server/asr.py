"""把孩子说的话转成文字（Qwen-ASR / OpenAI 兼容 chat completions）。"""

from __future__ import annotations

import base64
from typing import Any

import httpx

from .config import settings

MAX_AUDIO_BYTES = 4 * 1024 * 1024


def build_data_uri(raw: bytes, mime: str) -> str:
    kind = (mime or "audio/webm").split(";")[0].strip() or "audio/webm"
    encoded = base64.b64encode(raw).decode("ascii")
    return f"data:{kind};base64,{encoded}"


def decode_audio_payload(audio: str) -> bytes:
    raw = (audio or "").strip()
    if not raw:
        return b""
    if raw.startswith("data:") and "," in raw:
        raw = raw.split(",", 1)[1]
    try:
        return base64.b64decode(raw, validate=False)
    except Exception:
        return b""


def extract_transcript(data: dict[str, Any]) -> str:
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        content = None
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict):
                text = part.get("text")
                if text:
                    parts.append(str(text))
        return "".join(parts).strip()

    output = data.get("output")
    if isinstance(output, dict):
        text = output.get("text")
        if text:
            return str(text).strip()
    return ""


async def transcribe_audio(audio_bytes: bytes, mime: str = "audio/webm") -> str:
    if not settings.asr_model or not settings.api_key:
        raise ValueError("还没有配置语音听写。")
    payload = {
        "model": settings.asr_model,
        "stream": False,
        "messages": [
            {
                "role": "system",
                "content": "把孩子说的话听写成简体中文。这是数学课上的对话，数字和加减乘除请写清楚。",
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_audio",
                        "input_audio": {"data": build_data_uri(audio_bytes, mime)},
                    }
                ],
            },
        ],
        "asr_options": {"language": "zh", "enable_itn": True},
    }
    headers = {
        "Authorization": f"Bearer {settings.api_key}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
        resp = await client.post(settings.chat_endpoint, json=payload, headers=headers)
        resp.raise_for_status()
        return extract_transcript(resp.json())
