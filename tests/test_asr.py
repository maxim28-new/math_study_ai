"""服务端听写：把孩子说的话转成文字。"""

from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from server.app import app
from server.asr import MAX_AUDIO_BYTES, build_data_uri, build_transcribe_payload, extract_transcript


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
