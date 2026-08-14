"""公网访问验证码。默认 maxim；校验通过后发带过期时间的签名 cookie。"""

from __future__ import annotations

import hashlib
import hmac
import time
from collections import defaultdict
from typing import Optional

COOKIE_NAME = "xiaoou_gate"
COOKIE_MAX_AGE = 30 * 24 * 3600
PUBLIC_PATHS = frozenset({"/gate.html", "/api/unlock", "/api/health"})
UNLOCK_FAIL_LIMIT = 5
UNLOCK_WINDOW_S = 60
_UNLOCK_PREFIX = "xiaoou-unlocked"


def sign_cookie(
    access_code: str, now: Optional[int] = None, max_age: int = COOKIE_MAX_AGE
) -> str:
    exp = int(now if now is not None else time.time()) + max_age
    digest = hmac.new(
        access_code.encode("utf-8"),
        f"{_UNLOCK_PREFIX}|{exp}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{exp}.{digest}"


def cookie_valid(
    access_code: str, value: Optional[str], now: Optional[int] = None
) -> bool:
    if not access_code or not value or "." not in value:
        return False
    exp_s, digest = value.split(".", 1)
    try:
        exp = int(exp_s)
    except ValueError:
        return False
    if exp < int(now if now is not None else time.time()):
        return False
    expected = hmac.new(
        access_code.encode("utf-8"),
        f"{_UNLOCK_PREFIX}|{exp}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(digest, expected)


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


class UnlockLimiter:
    def __init__(self, max_fails: int = UNLOCK_FAIL_LIMIT, window_s: int = UNLOCK_WINDOW_S):
        self.max_fails = max_fails
        self.window_s = window_s
        self._fails: dict[str, list[float]] = defaultdict(list)

    def reset(self) -> None:
        self._fails.clear()

    def _prune(self, ip: str, now: float) -> list[float]:
        kept = [t for t in self._fails[ip] if now - t < self.window_s]
        self._fails[ip] = kept
        return kept

    def blocked(self, ip: str, now: Optional[float] = None) -> bool:
        stamp = time.time() if now is None else now
        return len(self._prune(ip, stamp)) >= self.max_fails

    def fail(self, ip: str, now: Optional[float] = None) -> None:
        stamp = time.time() if now is None else now
        self._prune(ip, stamp)
        self._fails[ip].append(stamp)

    def success(self, ip: str) -> None:
        self._fails.pop(ip, None)


unlock_limiter = UnlockLimiter()


def reset_unlock_limiter() -> None:
    unlock_limiter.reset()


def client_ip(request) -> str:
    forwarded = (request.headers.get("x-forwarded-for") or "").split(",")[0].strip()
    if forwarded:
        return forwarded
    if request.client and request.client.host:
        return request.client.host
    return "unknown"
