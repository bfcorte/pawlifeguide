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
    t = term.lower()
    if t.startswith("how to"):
        return "how-to"
    if " vs " in t or " or " in t:
        return "comparison"
    if "guide" in t or "choose" in t or "what to look":
        return "buyers-guide"
    if "tip" in t or "trick" in t:
        return "tips"
    if "care for" in t or "care guide" in t:
        return "care-guide"
    if "best" in t or "top" in t or "review" in t:
        # Vary between listicle and buyers-guide for commercial terms
        import random
        return random.choice(["listicle", "listicle", "buyers-guide"])
    if intent == "COMMERCIAL":
        return "listicle"
    return random.choice(["how-to", "tips", "care-guide"])


def generate_amazon_terms(term: str) -> list[str]:
    base = term.replace("best ", "").replace("top ", "").replace(" guide", "")
    return [base, f"best {base}", f"{base} recommended"]


def generate_variations(topic: str, identity: dict) -> list[str]:
    """Generate a broad, diverse set of keywords covering all pet types and content formats."""
    year = datetime.now().year

    # ── Pet-specific seed topics ─────────────────────────────────────────────
    pet_seeds = {
        "cats": [
            f"best cat food for indoor cats",
            f"best cat litter for apartments",
            f"best interactive cat toys",
            f"how to train a cat",
            f"how to reduce cat shedding",
            f"best cat beds {year}",
            f"cat hairball remedies",
            f"best wet cat food brands",
            f"how to introduce a new cat",
            f"best automatic cat feeders",
            f"cat scratching post review",
            f"best cat carriers for travel",
        ],
        "dogs": [
            f"best dog food for large breeds",
            f"best dog food for small breeds",
            f"best dog toys for aggressive chewers",
            f"how to train a dog to sit",
            f"how to stop dog barking",
            f"best dog beds for joint pain",
            f"best no-pull dog harness",
            f"best dog crates for home",
            f"dog separation anxiety tips",
            f"best dog treats for training",
            f"best dog shampoo for shedding",
            f"best invisible fence for dogs",
            f"how to groom a dog at home",
            f"best dog food brands {year}",
        ],
        "birds": [
            f"best bird cages for parrots",
            f"best bird food for parakeets",
            f"how to train a parrot to talk",
            f"best bird perches review",
            f"how to care for a cockatiel",
            f"best bird toys for budgies",
            f"bird cage cleaning tips",
        ],
        "fish": [
            f"best aquarium filter for beginners",
            f"best fish tank setup guide",
            f"how to cycle a fish tank",
            f"best betta fish tanks",
            f"best tropical fish for beginners",
            f"aquarium plants for beginners",
            f"best aquarium heater review",
            f"how to keep fish tank clean",
        ],
        "small-pets": [
            f"best hamster cages {year}",
            f"best rabbit hutches for indoors",
            f"how to care for a guinea pig",
            f"best bedding for hamsters",
            f"guinea pig food guide",
            f"best rabbit food brands",
            f"how to bond with your rabbit",
        ],
        "general": [
            f"best pet insurance {year}",
            f"how to pet-proof your home",
            f"best pet cameras for home",
            f"best pet travel carriers",
            f"how to introduce pets to each other",
            f"pet first aid kit essentials",
            f"how to reduce pet allergies at home",
            f"best air purifier for pet dander",
            f"how to remove pet odor from carpet",
        ],
    }

    base = []
    for pet_type, seeds in pet_seeds.items():
        base.extend(seeds)

    # ── Topic-based additions from the niche ─────────────────────────────────
    base += [topic, f"best {topic}", f"{topic} guide", f"how to {topic}"]

    return list(dict.fromkeys(base))[:60]  # deduplicate, cap at 60


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


def build_static_fallback(topic: str, config: dict) -> dict:
    """Gera keywords a partir dos seeds estáticos quando PyTrends falha."""
    identity = config["blog_identity"]
    base_terms = generate_variations(topic, identity)
    commercial_words = ["best", "top", "review", "buy", "cheap", "affordable", "vs", "recommended"]
    keywords = []
    for term in base_terms:
        intent = "COMMERCIAL" if any(w in term.lower() for w in commercial_words) else "INFORMATIONAL"
        score = 60 if intent == "COMMERCIAL" else 35
        keywords.append({
            "keyword": term,
            "interest_score": score,
            "trend": "STABLE",
            "intent": intent,
            "score": score,
            "seasonal_month": None,
            "related_rising": [],
            "article_angle": suggest_angle(term, intent),
            "amazon_search_terms": generate_amazon_terms(term),
            "used_history": [],
        })
    keywords.sort(key=lambda x: x["score"], reverse=True)
    return {
        "topic": topic,
        "niche": identity["niche"],
        "generated_at": datetime.now().isoformat(),
        "expires_at": (datetime.now() + timedelta(days=7)).isoformat(),
        "total_keywords": len(keywords),
        "keywords": keywords,
        "source": "static_fallback",
    }


def research_keywords(topic: str, config: dict, force: bool = False) -> dict:
    kw_file = Path(f"keywords/{topic.replace(' ', '_')}_keywords.json")

    if kw_file.exists() and not force:
        data = json.loads(kw_file.read_text())
        expires = datetime.fromisoformat(data["expires_at"])
        if datetime.now() < expires:
            log.info(f"Using cached keywords (valid until {expires.date()})")
            return data

    # Tenta PyTrends com timeout curto por termo
    try:
        from pytrends.request import TrendReq
        pytrends_available = True
    except ImportError:
        log.warning("pytrends not installed — using static fallback")
        pytrends_available = False

    identity = config["blog_identity"]
    base_terms = generate_variations(topic, identity)
    all_keywords: list[dict] = []
    pytrends_failures = 0

    commercial_words = ["best", "top", "review", "buy", "cheap", "affordable", "vs", "for", "recommended"]

    if pytrends_available:
        pytrends = TrendReq(hl="en-US", tz=300)
        for term in base_terms:
            if pytrends_failures >= 5:
                log.warning("5 falhas consecutivas — usando fallback estático para o restante")
                break
            try:
                time.sleep(random.uniform(2.5, 4.5))
                pytrends.build_payload([term], cat=0, timeframe="today 12-m", geo="US")
                interest = pytrends.interest_over_time()
                if interest.empty or term not in interest.columns:
                    continue
                avg = int(interest[term].mean())
                trend = detect_trend(interest[term])
                intent = "COMMERCIAL" if any(w in term.lower() for w in commercial_words) else "INFORMATIONAL"
                score = calculate_score(avg, intent, trend)
                try:
                    related = pytrends.related_queries()
                    rising = related.get(term, {}).get("rising")
                except Exception:
                    rising = None
                all_keywords.append({
                    "keyword": term,
                    "interest_score": avg,
                    "trend": trend,
                    "intent": intent,
                    "score": score,
                    "seasonal_month": detect_season(interest[term]),
                    "related_rising": (rising["query"].tolist()[:5] if rising is not None else []),
                    "article_angle": suggest_angle(term, intent),
                    "amazon_search_terms": generate_amazon_terms(term),
                    "used_history": [],
                })
                pytrends_failures = 0
                if rising is not None:
                    for _, row in rising.head(3).iterrows():
                        all_keywords.append(quick_entry(row["query"], intent))
            except Exception as e:
                log.warning(f"PyTrends error for '{term}': {e}")
                pytrends_failures += 1
                time.sleep(10)
                continue

    # Se PyTrends não retornou nada, usa fallback estático
    if not all_keywords:
        log.warning("PyTrends não retornou dados — usando seeds estáticos como fallback")
        result = build_static_fallback(topic, config)
        kw_file.parent.mkdir(exist_ok=True)
        kw_file.write_text(json.dumps(result, indent=2))
        log.info(f"Saved {result['total_keywords']} keywords (static fallback) to {kw_file}")
        return result

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
