#!/usr/bin/env python3
"""
SEO Optimizer — Validates and auto-fixes SEO issues in ready articles.
Usage: python scripts/seo_optimizer.py --slug "best-dog-food-2025-04-17"
"""

import json
import re
import argparse
import logging
from pathlib import Path
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("logs/activity.log"), logging.StreamHandler()],
)
log = logging.getLogger(__name__)

ADSENSE_SLOTS = ["header", "content_top", "content_mid", "sidebar", "footer"]


def load_config() -> dict:
    return json.loads(Path("config.json").read_text())


def check_title(content: str, keyword: str) -> dict:
    title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    if not title_match:
        return {"pass": False, "issue": "No H1 title found"}
    title = title_match.group(1)
    length = len(title)
    has_keyword = keyword.lower() in title.lower()
    if not has_keyword:
        return {"pass": False, "issue": f"Keyword '{keyword}' not in title"}
    if length < 30 or length > 70:
        return {"pass": False, "issue": f"Title length {length} (should be 30-70)"}
    return {"pass": True, "value": title}


def check_word_count(content: str) -> dict:
    words = len(content.split())
    return {
        "pass": words >= 1800,
        "value": words,
        "issue": f"Only {words} words (minimum 1800)" if words < 1800 else None,
    }


def check_quick_answer(content: str) -> dict:
    has_qa = "quick-answer" in content.lower() or "quick answer" in content.lower()
    return {"pass": has_qa, "issue": "Missing Quick Answer box" if not has_qa else None}


def check_disclaimer(content: str) -> dict:
    has_disclaimer = "amazon associate" in content.lower()
    return {
        "pass": has_disclaimer,
        "issue": "Missing Amazon disclaimer" if not has_disclaimer else None,
    }


def check_faq(content: str) -> dict:
    faq_headers = re.findall(r"^###\s+.+\?", content, re.MULTILINE)
    count = len(faq_headers)
    return {
        "pass": count >= 5,
        "value": count,
        "issue": f"Only {count} FAQ questions (minimum 5)" if count < 5 else None,
    }


def check_h2_count(content: str) -> dict:
    h2s = re.findall(r"^##\s+.+$", content, re.MULTILINE)
    count = len(h2s)
    return {
        "pass": 4 <= count <= 10,
        "value": count,
        "issue": f"{count} H2 sections (should be 4-10)" if not (4 <= count <= 10) else None,
    }


def generate_schema(meta: dict, config: dict) -> str:
    url = config["blog_identity"]["url"]
    return json.dumps(
        {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": meta.get("title", ""),
            "description": meta.get("meta_description", ""),
            "author": {
                "@type": "Organization",
                "name": config["blog_identity"]["name"],
            },
            "publisher": {
                "@type": "Organization",
                "name": config["blog_identity"]["name"],
                "url": url,
            },
            "datePublished": meta.get("created_at", datetime.now().isoformat()),
            "dateModified": datetime.now().isoformat(),
            "mainEntityOfPage": {
                "@type": "WebPage",
                "@id": f"{url}/posts/{meta.get('slug', '')}",
            },
        },
        indent=2,
    )


def run_checks(slug: str) -> dict:
    config = load_config()
    ready_files = list(Path("articles/ready").rglob(f"{slug}*.md"))
    if not ready_files:
        log.error(f"No ready article found for: {slug}")
        raise FileNotFoundError(f"Article not found: {slug}")

    article_path = ready_files[0]
    meta_path = Path(str(article_path).replace(".md", "_meta.json"))
    content = article_path.read_text(encoding="utf-8")
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    keyword = meta.get("primary_keyword", slug.replace("-", " "))

    checks = {
        "title": check_title(content, keyword),
        "word_count": check_word_count(content),
        "quick_answer": check_quick_answer(content),
        "disclaimer": check_disclaimer(content),
        "faq": check_faq(content),
        "h2_count": check_h2_count(content),
    }

    passed = sum(1 for c in checks.values() if c.get("pass"))
    total = len(checks)
    score = int((passed / total) * 100)

    report = {
        "slug": slug,
        "keyword": keyword,
        "score": score,
        "passed": passed,
        "total": total,
        "checks": checks,
        "schema_json_ld": generate_schema(meta, config),
        "generated_at": datetime.now().isoformat(),
    }

    report_path = Path(f"articles/ready/{slug}_seo_report.json")
    report_path.write_text(json.dumps(report, indent=2))
    log.info(f"SEO score: {score}/100 ({passed}/{total} checks passed)")

    for check_name, result in checks.items():
        if not result.get("pass"):
            log.warning(f"  FAIL [{check_name}]: {result.get('issue', 'Unknown issue')}")

    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--slug", required=True)
    args = parser.parse_args()

    report = run_checks(args.slug)
    print(json.dumps({"seo_score": report["score"], "passed": report["passed"], "total": report["total"]}))
