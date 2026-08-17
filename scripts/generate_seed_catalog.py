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


DEFAULT_OUTPUT = ROOT / "data" / "seed_catalog.json"


async def generate(output: Path, *, tutor_probe: bool) -> None:
    topics: dict[str, list[dict]] = {}
    reports: dict[str, dict] = {}
    for topic in tutor.TOPICS:
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
        if tutor_probe:
            for index, card in enumerate(cards, 1):
                print(f"[tutor]  {topic.key} #{index}: probing kickoff", flush=True)
                probe = await author_agent.probe_tutor_card(card)
                topic_report["tutor_probes"].append(probe)
                if not probe["ok"]:
                    raise RuntimeError(
                        f"{topic.key} #{index}: Tutor Agent probe failed: {probe['errors']}"
                    )
        topics[topic.key] = cards
        reports[topic.key] = topic_report

    payload = {
        "schema": author_agent.CATALOG_VERSION,
        "generator": "author-agent",
        "author_model": "glm-5.3",
        "tutor_model": tutor.settings.model,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "topics": topics,
        "reports": reports,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    temp = output.with_suffix(output.suffix + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(output)
    print(f"[done] wrote {sum(len(cards) for cards in topics.values())} cards to {output}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--skip-tutor-probe", action="store_true")
    args = parser.parse_args()
    asyncio.run(generate(args.output, tutor_probe=not args.skip_tutor_probe))


if __name__ == "__main__":
    main()
