"""后台出题任务：客户端断开后服务端仍继续想题。"""

from __future__ import annotations

import logging
import time
import uuid
from collections import OrderedDict
from typing import Any

from . import author
from . import tutor

log = logging.getLogger("xiaoou.author")

JOB_TIMEOUT_SEC = 120.0
JOB_TTL_SEC = 15 * 60
_MAX_JOBS = 80

_jobs: OrderedDict[str, dict[str, Any]] = OrderedDict()
_pending_key: dict[tuple[str, str], str] = {}


def reset() -> None:
    _jobs.clear()
    _pending_key.clear()


def _prune(now: float | None = None) -> None:
    stamp = time.time() if now is None else now
    stale = [job_id for job_id, job in _jobs.items() if stamp - float(job.get("created_at") or 0) > JOB_TTL_SEC]
    for job_id in stale:
        job = _jobs.pop(job_id, None)
        if not job:
            continue
        key = (job.get("topic"), job.get("level"))
        if _pending_key.get(key) == job_id:
            _pending_key.pop(key, None)


def create(topic: str, level: str, recent: list[str] | None, engine: str | None) -> dict[str, Any]:
    _prune()
    topic = topic if topic in tutor.TOPICS_BY_KEY else tutor.DEFAULT_TOPIC_KEY
    level = level if level in tutor.LEVELS else tutor.DEFAULT_LEVEL
    recent = [str(item).strip() for item in (recent or []) if str(item).strip()]
    chosen = author.resolve_engine(engine)
    key = (topic, level)
    existing_id = _pending_key.get(key)
    if existing_id and existing_id in _jobs and _jobs[existing_id].get("status") == "pending":
        return _jobs[existing_id]
    job_id = "job_" + uuid.uuid4().hex[:16]
    job = {
        "id": job_id,
        "status": "pending",
        "topic": topic,
        "level": level,
        "engine": chosen,
        "recent": recent,
        "card": None,
        "fallback": False,
        "error": "",
        "created_at": time.time(),
        "running": False,
    }
    _jobs[job_id] = job
    _jobs.move_to_end(job_id)
    _pending_key[key] = job_id
    while len(_jobs) > _MAX_JOBS:
        old_id, old = _jobs.popitem(last=False)
        old_key = (old.get("topic"), old.get("level"))
        if _pending_key.get(old_key) == old_id:
            _pending_key.pop(old_key, None)
    return job


def get(job_id: str) -> dict[str, Any] | None:
    _prune()
    return _jobs.get(job_id)


def public_view(job: dict[str, Any]) -> dict[str, Any]:
    status = job.get("status")
    if status == "running":
        status = "pending"
    out: dict[str, Any] = {
        "ok": True,
        "job_id": job.get("id"),
        "status": status,
        "fallback": bool(job.get("fallback")),
    }
    if job.get("status") == "done" and job.get("card"):
        out["card"] = job["card"]
        out["engine"] = "seed" if job.get("fallback") else (job.get("engine") or "")
    if job.get("error"):
        out["error"] = job["error"]
    return out


async def run_job(job_id: str) -> None:
    job = _jobs.get(job_id)
    if not job or job.get("status") != "pending" or job.get("running"):
        return
    job["running"] = True
    topic = str(job.get("topic") or tutor.DEFAULT_TOPIC_KEY)
    level = str(job.get("level") or tutor.DEFAULT_LEVEL)
    recent = list(job.get("recent") or [])
    engine = str(job.get("engine") or "")
    log.info("author job %s start topic=%s engine=%s", job_id, topic, engine)
    card = None
    fallback = False
    error = ""
    try:
        try:
            if author.engine_ready(engine):
                card = await author.request_author_card(
                    topic, level, recent, engine, timeout=JOB_TIMEOUT_SEC
                )
            else:
                error = "还没有接上出题大脑的密钥。"
        except Exception as exc:
            error = str(exc)
            log.info("author job %s glm failed: %s", job_id, error[:200])
        if card is None:
            card = author.seed_card(topic, level, recent)
            fallback = True
        job["card"] = card
        job["fallback"] = fallback
        job["error"] = error if fallback else ""
        job["status"] = "done"
        key = (topic, level)
        if _pending_key.get(key) == job_id:
            _pending_key.pop(key, None)
        log.info("author job %s done fallback=%s hook=%s", job_id, fallback, (card or {}).get("hook"))
    finally:
        job["running"] = False
