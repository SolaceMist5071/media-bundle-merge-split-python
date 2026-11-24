"""Executable service boundary for a privacy-first media handoff."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from infrai_media import InfraiClient


def deliver_visit(client: InfraiClient, visit: dict[str, Any]) -> dict[str, Any]:
    visit_id = str(visit["visit_id"])
    groups = visit["page_groups"]
    if not visit["inputs"] or not groups:
        raise ValueError("a visit needs inputs and page_groups")
    merged = client.merge(list(visit["inputs"]), f"merge:{visit_id}")
    ranges = [[group[0], group[-1]] for group in groups]
    split = client.split(merged["data"]["url"], ranges, f"split:{visit_id}")
    queued = client.queue_publish(
        "creator-media-delivery",
        {"visit_id": visit_id, "split": split["data"], "group_count": len(groups)},
        f"queue:{visit_id}",
    )
    return {"visit_id": visit_id, "group_count": len(groups), "queued": queued["data"]}


def main() -> None:
    parser = argparse.ArgumentParser(description="Merge, split, and queue a media visit")
    parser.add_argument("--input", required=True, type=Path)
    args = parser.parse_args()
    visit = json.loads(args.input.read_text(encoding="utf-8"))
    print(json.dumps(deliver_visit(InfraiClient(), visit), indent=2))


if __name__ == "__main__":
    main()
