#!/usr/bin/env python3
"""
Keyword Research — PyTrends (free)
Usage: python scripts/keyword_research.py --topic "pets" [--force]
"""

import json
import time
import random
import argparse
import logging
from datetime import datetime, timedelta
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/activity.log"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)


def load_config() -> dict:
    return json.loads(Path("config.json").read_text())


def detect_trend(series) -> str:
    if len(series) < 8:
        return "STABLE"
    recent = series[-4:].mean()
    older = series[-8:-4].mean()
    if older == 0:
        return "STABLE"
    change = (recent - older) / older
    if change > 0.15:
        return "RISING"
    if change < -0.15:
        return "FALLING"
    return "STABLE"


def detect_season(series) -> int | None:
    if series.empty:
        return None
    return int(series.idxmax().month)


def calculate_score(interest: int, intent: str, trend: str) -> int:
    score = interest * 0.5
    if intent == "COMMERCIAL":
        score *= 1.4
    if trend == "RISING":
        score = min(100, score * 1.15)
    elif trend == "FALLING":
        score *= 0.8
    return int(min(100, score))


def suggest_angle(term: str, intent: str) -> str:
    if intent == "COMMERCIAL":
        return "listicle"
    term_lower = term.lower()
    if term_lower.startswith("how"):
        return "how-to"
    if " vs " in term_lower:
        return "comparison"
    if "best" in term_lower or "top" in term_lower:
        return "listicle"
    if "guide" in term_lower or "choose" in term_lower:
        return "buyers-guide"
    return "how-to"


def generate_amazon_terms(term: str) -> list[str]:
    base = term.replace("best ", "").replace("top ", "").replace(" guide", "")
    return [base, f"best {base}", f"{base} recommended"]


def generate_variations(topic: str, identity: dict) -> list[str]:
    prefixes = [
        "best", "top", "how to", "what is the best",
        "affordable", "cheap", "recommended", "beginner",
    ]
    suffixes = [
        "for beginners", "guide", "review", "tips",
        "2025", "vs", "for home", "that work",
    ]
    base = [topic]
    base += [f"{p} {topic}" for p in prefixes]
    base += [f"{topic} {s}" for s in suffixes]
    for cat in identity.get("amazon_categories", [])[:3]:
        base += [f"best {cat}", f"{cat} guide", f"{cat} review"]
    return list(set(base))[:50]


def deduplicate(keywords: list[dict]) -> list[dict]:
    seen = set()
    unique = []
    for kw in keywords:
        key = kw["keyword"].lower().strip()
        if key not in seen:
            seen.add(key)
            unique.append(kw)
    return unique


def quick_entry(query: str, intent: str) -> dict:
    return {
        "keyword": query,
        "interest_score": 10,
        "trend": "RISING",
        "intent": intent,
        "score": 15,
        "seasonal_month": None,
        "related_rising": [],
        "article_angle": suggest_angle(query, intent),
        "amazon_search_terms": generate_amazon_terms(query),
        "used_history": [],
    }


def research_keywords(topic: str, config: dict, force: bool = False) -> dict:
    try:
        from pytrends.request import TrendReq
    except ImportError:
        log.error("pytrends not installed. Run: pip install pytrends")
        raise

    kw_file = Path(f"keywords/{topic.replace(' ', '_')}_keywords.json")

    if kw_file.exists() and not force:
        data = json.loads(kw_file.read_text())
        expires = datetime.fromisoformat(data["expires_at"])
        if datetime.now() < expires:
            log.info(f"Using cached keywords (valid until {expires.date()})")
            return data

    identity = config["blog_identity"]
    base_terms = generate_variations(topic, identity)
    all_keywords: list[dict] = []

    commercial_words = [
        "best", "top", "review", "buy",
        "cheap", "affordable", "vs", "for", "recommended",
    ]

    pytrends = TrendReq(hl="en-US", tz=300)

    for term in base_terms:
        try:
            time.sleep(random.uniform(2.5, 4.5))
            pytrends.build_payload([term], cat=0, timeframe="today 12-m", geo="US")
            interest = pytrends.interest_over_time()

            if interest.empty or term not in interest.columns:
                continue

            avg = int(interest[term].mean())
            trend = detect_trend(interest[term])
            intent = (
                "COMMERCIAL"
                if any(w in term.lower() for w in commercial_words)
                else "INFORMATIONAL"
            )
            score = calculate_score(avg, intent, trend)

            try:
                related = pytrends.related_queries()
                rising = related.get(term, {}).get("rising")
            except Exception:
                rising = None

            all_keywords.append(
                {
                    "keyword": term,
                    "interest_score": avg,
                    "trend": trend,
                    "intent": intent,
                    "score": score,
                    "seasonal_month": detect_season(interest[term]),
                    "related_rising": (
                        rising["query"].tolist()[:5] if rising is not None else []
                    ),
                    "article_angle": suggest_angle(term, intent),
                    "amazon_search_terms": generate_amazon_terms(term),
                    "used_history": [],
                }
            )

            if rising is not None:
                for _, row in rising.head(3).iterrows():
                    all_keywords.append(quick_entry(row["query"], intent))

        except Exception as e:
            log.warning(f"PyTrends error for '{term}': {e}")
            time.sleep(10)
            continue

    unique = deduplicate(all_keywords)
    sorted_kw = sorted(unique, key=lambda x: x["score"], reverse=True)

    result = {
        "topic": topic,
        "niche": identity["niche"],
        "generated_at": datetime.now().isoformat(),
        "expires_at": (datetime.now() + timedelta(days=30)).isoformat(),
        "total_keywords": len(sorted_kw),
        "keywords": sorted_kw,
    }

    kw_file.parent.mkdir(exist_ok=True)
    kw_file.write_text(json.dumps(result, indent=2))
    log.info(f"Saved {len(sorted_kw)} keywords to {kw_file}")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", required=True)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    config = load_config()
    result = research_keywords(args.topic, config, force=args.force)
    print(f"Done: {result['total_keywords']} keywords saved.")
