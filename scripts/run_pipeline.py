#!/usr/bin/env python3
"""
Full Pipeline — Keyword → Article → Products → SEO check.
Usage: python scripts/run_pipeline.py --keyword "best dog food" --angle listicle
Outputs JSON to stdout.
"""

import json
import argparse
import logging
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("logs/activity.log"), logging.StreamHandler()],
)
log = logging.getLogger(__name__)

# Add scripts dir to path
sys.path.insert(0, str(Path(__file__).parent))

from article_writer import save_article, build_title, load_config
from amazon_finder import inject_products
from seo_optimizer import run_checks


def run_pipeline(keyword: str, angle: str) -> dict:
    config = load_config()

    log.info(f"Pipeline start — keyword: '{keyword}' | angle: {angle}")

    # Step 1: Write article
    log.info("Step 1/3: Writing article...")
    draft_path, slug = save_article(keyword, angle, config)
    title = build_title(keyword, angle)
    log.info(f"Draft: {draft_path}")

    # Step 2: Inject Amazon products
    log.info("Step 2/3: Finding Amazon products...")
    try:
        ready_path = inject_products(slug, config)
        log.info(f"Ready: {ready_path}")
    except Exception as e:
        log.error(f"Product injection failed: {e}")
        ready_path = draft_path  # continue without products

    # Step 3: SEO check
    log.info("Step 3/3: Running SEO optimizer...")
    try:
        seo_report = run_checks(slug)
        seo_score = seo_report["score"]
        log.info(f"SEO score: {seo_score}/100")
    except Exception as e:
        log.error(f"SEO check failed: {e}")
        seo_score = 0

    result = {
        "slug": slug,
        "title": title,
        "keyword": keyword,
        "angle": angle,
        "draft_path": draft_path,
        "ready_path": str(ready_path),
        "seo_score": seo_score,
        "status": "ready",
    }

    with open("logs/activity.log", "a") as f:
        f.write(
            f"{__import__('datetime').datetime.now()} | PIPELINE DONE | "
            f"{slug} | SEO: {seo_score}/100\n"
        )

    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--keyword", required=True)
    parser.add_argument("--angle", default="listicle")
    args = parser.parse_args()

    result = run_pipeline(args.keyword, args.angle)
    print(json.dumps(result))
