"""离线 Author Agent：生成、校验、批评并试教一组三张种子题卡。"""

from __future__ import annotations

import json
import re
from difflib import SequenceMatcher
from typing import Any

import httpx

from . import author
from . import config as teaching_config
from . import tutor
from .agent import runtime as tutor_runtime
from .agent import workspace as WS
from .config import settings


MAX_AUTHOR_ROUNDS = 6
CATALOG_VERSION = 1


SUBMIT_BATCH_TOOL = {
    "type": "function",
    "function": {
        "name": "author_submit_seed_batch",
        "description": (
            "提交当前主题的三张候选种子题。程序会逐张校验题卡和画板，并检查三题是否只是换字母、"
            "数字或故事皮肤。未通过时，根据工具返回的问题修订整组后重新提交。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "candidates": {
                    "type": "array",
                    "minItems": 3,
                    "maxItems": 3,
                    "items": {
                        "type": "object",
                        "properties": {
                            "concept_key": {
                                "type": "string",
                                "description": "英文短标识，表示这道题独有的数学发现，不是场景名",
                            },
                            "card": {"type": "object"},
                        },
                        "required": ["concept_key", "card"],
                    },
                }
            },
            "required": ["candidates"],
        },
    },
}


def _compact(text: Any) -> str:
    return re.sub(r"[\W_]+", "", str(text or "").lower())


def _similarity(left: Any, right: Any) -> float:
    a, b = _compact(left), _compact(right)
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def _scrub_board(value: Any, key: str = "") -> Any:
    """比较数学结构时忽略字母标签和展示文案，但保留数量与结构。"""
    if isinstance(value, dict):
        return {
            k: _scrub_board(v, k)
            for k, v in sorted(value.items())
            if k not in {"prompt", "caption", "labels"}
        }
    if isinstance(value, list):
        return [_scrub_board(item, key) for item in value]
    return value


def _board_fingerprint(card: dict[str, Any]) -> str:
    board = card.get("board") if isinstance(card.get("board"), dict) else {}
    return json.dumps(_scrub_board(board), ensure_ascii=False, sort_keys=True)


def validate_seed_batch(topic: str, candidates: Any) -> dict[str, Any]:
    """Author Agent 的确定性工具：校验三卡、画板可挂载和明显重复。"""
    if not isinstance(candidates, list) or len(candidates) != 3:
        return {"ok": False, "issues": ["必须一次提交恰好三张候选题卡"]}

    cards: list[dict[str, Any]] = []
    concepts: list[str] = []
    issues: list[str] = []
    for index, candidate in enumerate(candidates, 1):
        if not isinstance(candidate, dict):
            issues.append(f"第 {index} 项不是对象")
            continue
        concept = _compact(candidate.get("concept_key"))
        if not concept:
            issues.append(f"第 {index} 题缺少 concept_key")
        concepts.append(concept)
        card = author.normalize_card(candidate.get("card"), topic)
        if not card:
            issues.append(f"第 {index} 题未通过题卡或 BoardSpec V3 校验")
            continue
        board_kind = card["board"]["kind"]
        if board_kind == "color_sequence" and topic != "reasoning":
            issues.append(
                f"第 {index} 题用 color_sequence 时，程序第一问只会问颜色规律，"
                f"不能承载 {topic} 主题的目标洞见"
            )
            continue
        if board_kind == "geometry_compass" and topic != "geometry":
            issues.append(f"第 {index} 题的尺规正三角形画板只能用于 geometry")
            continue
        workspace = WS.seed_from_card(card, topic, f"author_preview_{topic}_{index}")
        if WS.from_dict(workspace) is None:
            issues.append(f"第 {index} 题无法挂载为 Tutor Agent 工作区")
            continue
        cards.append(card)

    if len(set(concepts)) != 3:
        issues.append("三题的 concept_key 必须代表三个不同的数学发现")
    if len(cards) == 3:
        fingerprints = [_board_fingerprint(card) for card in cards]
        for left in range(3):
            for right in range(left + 1, 3):
                pair = f"第 {left + 1}、{right + 1} 题"
                if fingerprints[left] == fingerprints[right]:
                    issues.append(f"{pair}的数学画板结构相同，只换了标签或文案")
                if _similarity(cards[left]["hook"], cards[right]["hook"]) >= 0.72:
                    issues.append(f"{pair}的情景钩子过于相似")
                if _similarity(cards[left]["insight"], cards[right]["insight"]) >= 0.66:
                    issues.append(f"{pair}要发现的数学道理过于相似")

    if issues:
        return {"ok": False, "issues": issues}
    return {
        "ok": True,
        "cards": cards,
        "concept_keys": concepts,
        "preview": [
            {
                "hook": card["hook"],
                "insight": card["insight"],
                "board_kind": card["board"]["kind"],
                "first_question": card["first_question"],
            }
            for card in cards
        ],
    }


def build_batch_prompt(topic_key: str, level: str) -> str:
    topic = tutor.TOPICS_BY_KEY[topic_key]
    single_contract = author.build_author_prompt(topic_key, level, [])
    return f"""{single_contract}

# 本次是种子题组任务（优先于上面的“单卡”措辞）
你不是提交一题，而是为同一个主题设计一组恰好三题，并调用 author_submit_seed_batch。
每个 candidate 包含 concept_key 和 card；card 使用上面的单卡格式。

这三题会长期并排作为固定种子题，用来测试你作为 Author Agent 的能力：
1. 三题必须让孩子发现三个实质不同的数学道理，不能把同一道题只换字母、数字、人物或物品。
2. concept_key 必须标识数学发现，例如 place_value、triangle_angle_sum，不得写 story_1、variant_b。
3. 三题的第一步操作和画板也应尽量不同；同一 BoardSpec 只换 labels 会被程序拒绝。
4. 每题都必须严格属于“{topic.name}”，适合当前难度，并可由 Tutor Agent 沿 do/see/why 三层试教。
5. 先在心里比较整组三题，再调用工具提交。工具拒绝后，必须根据 issues 修订整组并再次提交。

不要在 content 中输出题卡；请调用 author_submit_seed_batch。"""


def _message(data: dict[str, Any]) -> dict[str, Any]:
    choices = data.get("choices") or []
    if not choices or not isinstance(choices[0], dict):
        return {}
    message = choices[0].get("message")
    return message if isinstance(message, dict) else {}


def _tool_args(call: dict[str, Any]) -> dict[str, Any]:
    fn = call.get("function") if isinstance(call.get("function"), dict) else {}
    raw = fn.get("arguments")
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _assistant_record(message: dict[str, Any]) -> dict[str, Any]:
    return {
        "role": "assistant",
        "content": message.get("content"),
        "tool_calls": message.get("tool_calls") or [],
    }


def _tool_record(call: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    return {
        "role": "tool",
        "tool_call_id": call.get("id") or "",
        "name": "author_submit_seed_batch",
        "content": json.dumps(result, ensure_ascii=False),
    }


async def _post_author(payload: dict[str, Any], timeout: float = 300.0) -> dict[str, Any]:
    endpoint, api_key, _model = author._author_client_conf("glm")
    if not api_key:
        raise ValueError("GLM-5.3 密钥未配置")
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    last_error: Exception | None = None
    for _attempt in range(2):
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(timeout)) as client:
                response = await client.post(endpoint, headers=headers, json=payload)
                response.raise_for_status()
                return response.json()
        except (httpx.ReadTimeout, httpx.ConnectTimeout, httpx.RemoteProtocolError) as exc:
            last_error = exc
    raise last_error or RuntimeError("GLM-5.3 请求失败")


async def review_seed_batch(topic: str, cards: list[dict[str, Any]]) -> dict[str, Any]:
    """GLM 作者批评器：抓程序难以识别的“同题换皮”和不可教问题。"""
    _endpoint, _api_key, model = author._author_client_conf("glm")
    extras = teaching_config.thinking_request_extras(
        settings.zhipu_base_url,
        model,
        True,
        settings.author_reasoning_effort,
    )
    payload = {
        "model": model,
        "stream": False,
        "temperature": 0.1,
        "messages": [
            {
                "role": "system",
                "content": (
                    "你是小欧题库的严格主编。检查同主题三题是否在数学洞见、孩子操作和推理路径上"
                    "实质不同，并检查画板、第一问、三层台阶是否一致可教。只换字母、数字、人物、"
                    "物品或同义改写必须判重复。尤其要检查：孩子回答程序统一后的 first_question，"
                    "是否会自然走向 insight；如果第一问只在问颜色、计数或摆放，而目标洞见另有其事，"
                    "必须拒绝。只输出 JSON："
                    '{"approved":true|false,"issues":["..."],"duplicate_pairs":[[1,2]]}。'
                ),
            },
            {
                "role": "user",
                "content": f"主题：{topic}\n候选题：\n{json.dumps(cards, ensure_ascii=False)}",
            },
        ],
        **extras,
    }
    data = await _post_author(payload)
    content = _message(data).get("content") or ""
    review = author.extract_json_object(content)
    if not isinstance(review, dict):
        return {"approved": False, "issues": ["主编没有返回可解析的审核 JSON"], "duplicate_pairs": []}
    return {
        "approved": bool(review.get("approved")),
        "issues": [str(item) for item in (review.get("issues") or []) if str(item).strip()][:12],
        "duplicate_pairs": review.get("duplicate_pairs") or [],
    }


async def generate_topic_seed_batch(
    topic: str,
    level: str = "middle",
    max_rounds: int = MAX_AUTHOR_ROUNDS,
) -> dict[str, Any]:
    """运行 GLM-5.3 Author Agent，直到工具和主编同时通过。"""
    if topic not in tutor.TOPICS_BY_KEY:
        raise ValueError(f"unknown topic: {topic}")
    _endpoint, _api_key, model = author._author_client_conf("glm")
    extras = teaching_config.thinking_request_extras(
        settings.zhipu_base_url,
        model,
        True,
        settings.author_reasoning_effort,
    )
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": build_batch_prompt(topic, level)},
        {"role": "user", "content": "请设计整组三题并调用提交工具。"},
    ]
    transcript: list[dict[str, Any]] = []

    for round_number in range(1, max_rounds + 1):
        payload = {
            "model": model,
            "stream": False,
            "temperature": 0.75 if round_number == 1 else 0.45,
            "messages": messages,
            "tools": [SUBMIT_BATCH_TOOL],
            "tool_choice": "auto",
            **extras,
        }
        data = await _post_author(payload)
        message = _message(data)
        calls = message.get("tool_calls") if isinstance(message.get("tool_calls"), list) else []
        call = next(
            (
                item
                for item in calls
                if isinstance(item, dict)
                and isinstance(item.get("function"), dict)
                and item["function"].get("name") == "author_submit_seed_batch"
            ),
            None,
        )
        if call is None:
            result = {"ok": False, "issues": ["必须调用 author_submit_seed_batch，不要只写文字"]}
            messages.append({"role": "assistant", "content": message.get("content") or ""})
            messages.append({"role": "user", "content": json.dumps(result, ensure_ascii=False)})
            transcript.append({"round": round_number, "tool": result})
            continue

        result = validate_seed_batch(topic, _tool_args(call).get("candidates"))
        messages.append(_assistant_record(message))
        messages.append(_tool_record(call, result))
        transcript.append({"round": round_number, "tool": result})
        if not result.get("ok"):
            continue

        review = await review_seed_batch(topic, result["cards"])
        transcript[-1]["review"] = review
        if review.get("approved"):
            return {
                "topic": topic,
                "model": model,
                "rounds": round_number,
                "cards": result["cards"],
                "concept_keys": result["concept_keys"],
                "review": review,
                "transcript": transcript,
            }
        messages.append(
            {
                "role": "user",
                "content": (
                    "主编审核未通过。请修订整组三题后再次调用提交工具："
                    + json.dumps(review, ensure_ascii=False)
                ),
            }
        )

    summary = [
        {
            "round": row.get("round"),
            "tool_ok": (row.get("tool") or {}).get("ok"),
            "tool_issues": (row.get("tool") or {}).get("issues") or [],
            "review": row.get("review") or {},
        }
        for row in transcript
    ]
    raise ValueError(
        f"{topic}: Author Agent 在 {max_rounds} 轮内未生成合格题组；"
        + json.dumps(summary, ensure_ascii=False)
    )


async def probe_tutor_card(card: dict[str, Any], level: str = "middle") -> dict[str, Any]:
    """用现有 Tutor Agent 真正跑一次开场，确认题卡可挂载、可发问且无协议泄漏。"""
    headers = {"Authorization": f"Bearer {settings.api_key}", "Content-Type": "application/json"}
    text = ""
    workspace = None
    errors: list[str] = []
    async with httpx.AsyncClient(timeout=httpx.Timeout(120.0)) as client:
        async for event in tutor_runtime.run_tutor_agent(
            client=client,
            headers=headers,
            teaching_messages=[{"role": "user", "content": tutor.EXPLORE_KICKOFF_WITH_CARD}],
            topic=card["topic"],
            level=level,
            child_name="",
            mode="explore",
            card=card,
            seen_terms=[],
            client_workspace=None,
            thinking_on=False,
            show_reasoning=False,
        ):
            if event.get("delta"):
                text += str(event["delta"])
            if event.get("workspace"):
                workspace = event["workspace"]
            if event.get("error"):
                errors.append(str(event["error"]))
    forbidden = ("```", "schema", "xiaoou-draw", '"kind"')
    if any(token in text for token in forbidden):
        errors.append("Tutor Agent 开场泄漏了内部协议")
    if not text.strip():
        errors.append("Tutor Agent 没有产生孩子可见开场")
    if not isinstance(workspace, dict) or WS.from_dict(workspace) is None:
        errors.append("Tutor Agent 没有返回有效工作区")
    return {
        "ok": not errors,
        "opening": text.strip(),
        "workspace_kind": (workspace or {}).get("problem", {}).get("board_kind"),
        "errors": errors,
    }
