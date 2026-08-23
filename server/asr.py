"""把孩子说的话转成文字。

默认走本机 faster-whisper，避免云端往返。云端 Qwen-ASR 只作兜底。
"""

from __future__ import annotations

import asyncio
import base64
import logging
import os
import subprocess
import sys
import tempfile
import threading
import wave
from typing import Any

import httpx

from .config import is_local_asr_model, settings

log = logging.getLogger(__name__)

MAX_AUDIO_BYTES = 4 * 1024 * 1024
_MIN_WAV_SECONDS = 0.25

_model = None
_model_lock = threading.Lock()
_preload_started = False


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


def build_transcribe_payload(audio_bytes: bytes, mime: str, model: str) -> dict:
    return {
        "model": model,
        "stream": False,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_audio",
                        "input_audio": {"data": build_data_uri(audio_bytes, mime)},
                    }
                ],
            }
        ],
        "asr_options": {"language": "zh", "enable_itn": True},
    }


def _running_under_tests() -> bool:
    if os.getenv("XIAO_OU_SKIP_ASR_PRELOAD", "").strip().lower() in {"1", "true", "yes", "on"}:
        return True
    return "unittest" in sys.modules or "pytest" in sys.modules


def _suffix_for_mime(mime: str) -> str:
    kind = (mime or "").split(";")[0].strip().lower()
    return {
        "audio/webm": ".webm",
        "audio/ogg": ".ogg",
        "audio/mp4": ".m4a",
        "audio/mpeg": ".mp3",
        "audio/wav": ".wav",
        "audio/x-wav": ".wav",
        "audio/wave": ".wav",
        "audio/aac": ".aac",
        "audio/3gpp": ".3gp",
    }.get(kind, ".webm")


def audio_to_wav_path(audio_bytes: bytes, mime: str = "audio/webm") -> str:
    """把浏览器录音转成 16kHz 单声道 wav，调用方负责删除返回路径。"""
    if not audio_bytes:
        raise ValueError("没有听到声音，再说一次吧。")
    src = tempfile.NamedTemporaryFile(suffix=_suffix_for_mime(mime), delete=False)
    dst = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    src_path, dst_path = src.name, dst.name
    try:
        src.write(audio_bytes)
        src.close()
        dst.close()
        cmd = [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            src_path,
            "-ac",
            "1",
            "-ar",
            "16000",
            "-c:a",
            "pcm_s16le",
            dst_path,
        ]
        proc = subprocess.run(cmd, capture_output=True, timeout=20)
        if proc.returncode != 0 or not os.path.isfile(dst_path) or os.path.getsize(dst_path) < 44:
            raise ValueError("这段声音小欧听不了，再说一次吧。")
        return dst_path
    except FileNotFoundError as exc:
        raise ValueError("小欧这边还没接上耳朵。") from exc
    except subprocess.TimeoutExpired as exc:
        raise ValueError("这段话有点长，分开说给小欧听吧。") from exc
    finally:
        try:
            os.unlink(src_path)
        except OSError:
            pass
        if os.path.isfile(dst_path) and os.path.getsize(dst_path) < 44:
            try:
                os.unlink(dst_path)
            except OSError:
                pass


def _wav_duration_seconds(path: str) -> float:
    try:
        with wave.open(path, "rb") as handle:
            frames = handle.getnframes()
            rate = handle.getframerate() or 1
            return frames / float(rate)
    except Exception:
        return 0.0


def _ensure_model():
    global _model
    if _model is not None:
        return _model
    with _model_lock:
        if _model is not None:
            return _model
        from faster_whisper import WhisperModel

        _model = WhisperModel(
            settings.asr_whisper_size,
            device="cpu",
            compute_type="int8",
        )
        return _model


def start_preload() -> None:
    """服务启动后在后台把模型装进内存，避免孩子第一次开口再等。"""
    global _preload_started
    if _preload_started or _running_under_tests():
        return
    if not is_local_asr_model(settings.asr_model):
        return
    _preload_started = True

    def _load() -> None:
        try:
            _ensure_model()
            log.info("local whisper ready (%s)", settings.asr_whisper_size)
        except Exception:
            log.exception("local whisper preload failed")

    threading.Thread(target=_load, name="asr-preload", daemon=True).start()


def _transcribe_local(audio_bytes: bytes, mime: str) -> str:
    wav_path = audio_to_wav_path(audio_bytes, mime)
    try:
        if _wav_duration_seconds(wav_path) < _MIN_WAV_SECONDS:
            return ""
        model = _ensure_model()
        segments, _info = model.transcribe(
            wav_path,
            language="zh",
            beam_size=1,
            best_of=1,
            temperature=0.0,
            vad_filter=True,
            condition_on_previous_text=False,
            initial_prompt="数学课，中文。",
        )
        return "".join(segment.text for segment in segments).strip()
    finally:
        try:
            os.unlink(wav_path)
        except OSError:
            pass


async def _transcribe_cloud(audio_bytes: bytes, mime: str, model: str) -> str:
    if not model or not settings.api_key:
        raise ValueError("还没有配置语音听写。")
    payload = build_transcribe_payload(audio_bytes, mime, model)
    headers = {
        "Authorization": f"Bearer {settings.api_key}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
        resp = await client.post(settings.chat_endpoint, json=payload, headers=headers)
        resp.raise_for_status()
        return extract_transcript(resp.json())


async def transcribe_audio(audio_bytes: bytes, mime: str = "audio/webm") -> str:
    if not settings.asr_model:
        raise ValueError("还没有配置语音听写。")
    if is_local_asr_model(settings.asr_model):
        try:
            return await asyncio.to_thread(_transcribe_local, audio_bytes, mime)
        except ValueError:
            raise
        except Exception:
            log.exception("local whisper failed")
            fallback = settings.asr_cloud_fallback
            if fallback and settings.api_key:
                try:
                    return await _transcribe_cloud(audio_bytes, mime, fallback)
                except Exception:
                    log.exception("cloud asr fallback failed")
            raise ValueError("小欧没听清，稍后再试一次。")
    return await _transcribe_cloud(audio_bytes, mime, settings.asr_model)
