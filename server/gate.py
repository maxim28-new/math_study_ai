"""公网访问验证码。默认 maxim；校验通过后发签名 cookie。"""

from __future__ import annotations

import hmac
import hashlib
from typing import Optional

COOKIE_NAME = "xiaoou_gate"
COOKIE_MAX_AGE = 30 * 24 * 3600
PUBLIC_PATHS = frozenset({"/gate.html", "/api/unlock", "/api/health"})
_UNLOCK_PAYLOAD = b"xiaoou-unlocked"


def sign_cookie(access_code: str) -> str:
    return hmac.new(
        access_code.encode("utf-8"), _UNLOCK_PAYLOAD, hashlib.sha256
    ).hexdigest()


def cookie_valid(access_code: str, value: Optional[str]) -> bool:
    if not access_code or not value:
        return False
    expected = sign_cookie(access_code)
    return hmac.compare_digest(value, expected)


def codes_match(given: str, expected: str) -> bool:
    a = (given or "").strip().encode("utf-8")
    b = (expected or "").encode("utf-8")
    if len(a) != len(b):
        hmac.compare_digest(b, b)
        return False
    return hmac.compare_digest(a, b)


def is_public_path(path: str) -> bool:
    return path in PUBLIC_PATHS


def request_unlocked(access_code: str, cookie_value: Optional[str], header_code: str) -> bool:
    if not access_code:
        return True
    if cookie_valid(access_code, cookie_value):
        return True
    return codes_match(header_code, access_code)
