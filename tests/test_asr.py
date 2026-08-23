"""服务端听写：把孩子说的话转成文字。"""

from __future__ import annotations

import io
import os
import shutil
import unittest
import wave
from dataclasses import replace

from fastapi.testclient import TestClient

from server.app import app
from server.asr import (
    MAX_AUDIO_BYTES,
    audio_to_wav_path,
    build_data_uri,
    build_transcribe_payload,
    clean_transcript,
    extract_transcript,
)
from server.config import is_local_asr_model, normalize_asr_model, settings


def _silence_wav(seconds: float = 0.4) -> bytes:
    frames = int(16000 * seconds)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(16000)
        handle.writeframes(b"\x00\x00" * frames)
    return buf.getvalue()


class AsrHelperTests(unittest.TestCase):
    def test_build_data_uri(self):
        uri = build_data_uri(b"abc", "audio/webm")
        self.assertTrue(uri.startswith("data:audio/webm;base64,"))

    def test_extract_transcript_from_chat_completions(self):
        data = {"choices": [{"message": {"content": "  三乘三等于九  "}}]}
        self.assertEqual(extract_transcript(data), "三乘三等于九")

    def test_extract_transcript_from_dashscope_output(self):
        data = {"output": {"text": "我卡住了"}}
        self.assertEqual(extract_transcript(data), "我卡住了")

    def test_extract_transcript_empty(self):
        self.assertEqual(extract_transcript({}), "")

    def test_payload_is_user_audio_only(self):
        payload = build_transcribe_payload(b"abc", "audio/webm", "qwen3-asr-flash")
        self.assertEqual([m["role"] for m in payload["messages"]], ["user"])
        self.assertEqual(payload["messages"][0]["content"][0]["type"], "input_audio")

    def test_clean_transcript_strips_sensevoice_tags(self):
        self.assertEqual(clean_transcript("<|zh|><|NEUTRAL|>三加五"), "三加五")
        self.assertEqual(clean_transcript("  格子  "), "格子")

    def test_default_asr_is_local(self):
        self.assertEqual(normalize_asr_model(None), "local")
        self.assertEqual(normalize_asr_model(""), "local")
        self.assertEqual(normalize_asr_model("off"), "")
        self.assertEqual(normalize_asr_model("qwen3-asr-flash"), "qwen3-asr-flash")
        self.assertTrue(is_local_asr_model("local"))
        self.assertTrue(is_local_asr_model("faster-whisper"))
        self.assertFalse(is_local_asr_model("qwen3-asr-flash"))

    def test_voice_enabled_local_does_not_need_cloud_key(self):
        local = replace(settings, asr_model="local", api_key="")
        self.assertTrue(local.voice_enabled)
        cloud = replace(settings, asr_model="qwen3-asr-flash", api_key="")
        self.assertFalse(cloud.voice_enabled)
        off = replace(settings, asr_model="")
        self.assertFalse(off.voice_enabled)

    def test_ffmpeg_rewrites_wav_to_16k_mono(self):
        if not shutil.which("ffmpeg"):
            self.skipTest("ffmpeg not installed")
        wav_path = audio_to_wav_path(_silence_wav(0.4), "audio/wav")
        try:
            with wave.open(wav_path, "rb") as handle:
                self.assertEqual(handle.getnchannels(), 1)
                self.assertEqual(handle.getframerate(), 16000)
        finally:
            os.unlink(wav_path)


class AsrHttpTests(unittest.TestCase):
    def setUp(self):
        from server.gate import reset_unlock_limiter
        reset_unlock_limiter()
        self.client = TestClient(app, follow_redirects=False)

    def test_transcribe_requires_gate(self):
        resp = self.client.post("/api/transcribe", json={"audio": "YQ==", "mime": "audio/webm"})
        self.assertEqual(resp.status_code, 401)

    def test_transcribe_rejects_empty_after_unlock(self):
        self.client.post("/api/unlock", json={"code": "maxim"})
        resp = self.client.post("/api/transcribe", json={"audio": "", "mime": "audio/webm"})
        self.assertEqual(resp.status_code, 400)

    def test_max_audio_bytes_is_bounded(self):
        self.assertLessEqual(MAX_AUDIO_BYTES, 8 * 1024 * 1024)


if __name__ == "__main__":
    unittest.main()
