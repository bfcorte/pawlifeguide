#!/usr/bin/env python3
"""
Keyword Selector — Picks the best available keyword with rotation logic.
Usage: python scripts/keyword_selector.py --topic "pets"
Outputs JSON to stdout.
"""

import json
import argparse
import logging
from datetime import datetime
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("logs/activity.log"), logging.StreamHandler()],
)
log = logging.getLogger(__name__)

ANGLES = [
    "listicle", "how-to", "comparison", "single-review",
    "buyers-guide", "budget", "premium", "seasonal",
]


def select_keyword(topic: str) -> dict | None:
    kw_file = Path(f"keywords/{topic.replace(' ', '_')}_keywords.json")
    if not kw_file.exists():
        log.error(f"Keyword file not found: {kw_file}")
        return None

    data = json.loads(kw_file.read_text())
    month = datetime.now().month

    # Slugs já publicados — nunca repetir
    published_slugs = {d.name for d in Path("blog/posts").iterdir() if d.is_dir()} if Path("blog/posts").exists() else set()

    candidates = []

    for kw in data["keywords"]:
        # Verifica se o slug gerado desta keyword já está publicado
        kw_slug = kw["keyword"].lower().strip().replace(" ", "-")
        if any(kw_slug in pub or pub in kw_slug for pub in published_slugs):
            continue

        history = kw.get("used_history", [])

        if not history:
            candidates.append({**kw, "priority": 1, "new_angle": kw["article_angle"]})
            continue

        last = max(history, key=lambda x: x["used_at"])
        days = (datetime.now() - datetime.fromisoformat(last["used_at"])).days
        used_angles = [h["angle"] for h in history]
        free_angles = [a for a in ANGLES if a not in used_angles]

        if kw.get("seasonal_month") == month:
            angle = free_angles[0] if free_angles else ANGLES[0]
            candidates.append({**kw, "priority": 2, "new_angle": angle})
        elif days >= 365:
            candidates.append({**kw, "priority": 3, "new_angle": "annual_update"})
        elif days >= 90 and free_angles:
            candidates.append({**kw, "priority": 4, "new_angle": free_angles[0]})

    if not candidates:
        log.warning("No candidates available — refresh needed.")
        return None

    candidates.sort(key=lambda x: (x["priority"], -x["score"]))
    selected = candidates[0]
    log.info(
        f"Selected: '{selected['keyword']}' | "
        f"angle: {selected['new_angle']} | "
        f"priority: {selected['priority']}"
    )
    return selected


def mark_used(topic: str, keyword: str, angle: str, slug: str) -> None:
    kw_file = Path(f"keywords/{topic.replace(' ', '_')}_keywords.json")
    data = json.loads(kw_file.read_text())
    for kw in data["keywords"]:
        if kw["keyword"] == keyword:
            kw["used_history"].append(
                {
                    "used_at": datetime.now().date().isoformat(),
                    "slug": slug,
                    "angle": angle,
                    "performance_30d": {"views": 0, "clicks": 0},
                }
            )
            break
    kw_file.write_text(json.dumps(data, indent=2))
    log.info(f"Marked '{keyword}' as used with angle '{angle}' → {slug}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", required=True)
    args = parser.parse_args()

    result = select_keyword(args.topic)
    if result:
        print(json.dumps(result))
    else:
        exit(1)
