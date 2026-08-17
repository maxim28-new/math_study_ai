#!/usr/bin/env python3
"""用 Author Agent + Tutor Agent 生成并验收 6×3 固定种子题。"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from server import author_agent, tutor  # noqa: E402
from server.config import settings  # noqa: E402


DEFAULT_OUTPUT = ROOT / "data" / "seed_catalog.json"


def write_checkpoint(
    output: Path,
    topics: dict[str, list[dict]],
    reports: dict[str, dict],
    *,
    complete: bool,
) -> None:
    payload = {
        "schema": author_agent.CATALOG_VERSION,
        "generator": "author-agent",
        "author_model": "glm-5.3",
        "tutor_model": settings.model,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "complete": complete,
        "topics": topics,
        "reports": reports,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    temp = output.with_suffix(output.suffix + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(output)


async def generate(
    output: Path,
    *,
    tutor_probe: bool,
    regenerate_topics: set[str] | None = None,
) -> None:
    topics: dict[str, list[dict]] = {}
    reports: dict[str, dict] = {}
    try:
        previous = json.loads(output.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        previous = {}
    if (
        isinstance(previous, dict)
        and previous.get("generator") == "author-agent"
        and previous.get("author_model") == "glm-5.3"
    ):
        topics = previous.get("topics") if isinstance(previous.get("topics"), dict) else {}
        reports = previous.get("reports") if isinstance(previous.get("reports"), dict) else {}
    for topic in regenerate_topics or set():
        topics.pop(topic, None)
        reports.pop(topic, None)

    for topic in tutor.TOPICS:
        cards = topics.get(topic.key) if isinstance(topics.get(topic.key), list) else []
        topic_report = reports.get(topic.key) if isinstance(reports.get(topic.key), dict) else {}
        probes = (
            topic_report.get("tutor_probes")
            if isinstance(topic_report.get("tutor_probes"), list)
            else []
        )
        if len(cards) == 3 and (not tutor_probe or len(probes) == 3):
            print(f"[resume] {topic.key}: using completed checkpoint", flush=True)
            continue
        if len(cards) != 3:
            print(f"[author] {topic.key}: generating three cards", flush=True)
            result = await author_agent.generate_topic_seed_batch(topic.key)
            cards = result["cards"]
            topic_report = {
                "model": result["model"],
                "rounds": result["rounds"],
                "concept_keys": result["concept_keys"],
                "review": result["review"],
                "tutor_probes": [],
            }
            topics[topic.key] = cards
            reports[topic.key] = topic_report
            write_checkpoint(output, topics, reports, complete=False)
            print(f"[checkpoint] saved {topic.key} author batch", flush=True)
        else:
            print(f"[resume] {topic.key}: author batch already saved", flush=True)

        if tutor_probe:
            probes = topic_report.setdefault("tutor_probes", [])
            for index, card in enumerate(cards[len(probes):], len(probes) + 1):
                print(f"[tutor]  {topic.key} #{index}: probing kickoff", flush=True)
                probe = await author_agent.probe_tutor_card(card)
                probes.append(probe)
                if not probe["ok"]:
                    raise RuntimeError(
                        f"{topic.key} #{index}: Tutor Agent probe failed: {probe['errors']}"
                    )
                write_checkpoint(output, topics, reports, complete=False)
        print(f"[checkpoint] saved {topic.key}", flush=True)

    write_checkpoint(output, topics, reports, complete=True)
    print(f"[done] wrote {sum(len(cards) for cards in topics.values())} cards to {output}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--skip-tutor-probe", action="store_true")
    parser.add_argument(
        "--regenerate-topic",
        action="append",
        choices=[topic.key for topic in tutor.TOPICS],
        default=[],
    )
    args = parser.parse_args()
    asyncio.run(
        generate(
            args.output,
            tutor_probe=not args.skip_tutor_probe,
            regenerate_topics=set(args.regenerate_topic),
        )
    )


if __name__ == "__main__":
    main()
