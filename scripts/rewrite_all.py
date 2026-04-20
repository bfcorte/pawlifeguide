#!/usr/bin/env python3
"""
Rewrite all published articles with the new editorial standard.
Extracts existing product cards, regenerates content, re-injects cards.
Usage: python scripts/rewrite_all.py
"""
import sys, os, json, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pathlib import Path
from datetime import datetime
from article_writer import build_article, build_title, build_meta_description, detect_category, slugify
from publisher import build_article_html, md_to_html, build_adsense_slot, load_config

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("Installing beautifulsoup4...")
    os.system("pip install beautifulsoup4 -q")
    from bs4 import BeautifulSoup

SLUG_MAP = {
    "best-aquarium-plants-for-beginners": ("best aquarium plants for beginners", "listicle"),
    "best-cat-food-indoor-cats":          ("best cat food for indoor cats",       "listicle"),
    "best-dog-food-for-small-breeds":     ("best dog food for small breeds",      "listicle"),
    "best-dog-treats-for-training":       ("best dog treats for training",        "listicle"),
    "best-interactive-cat-toys":          ("best interactive cat toys",           "listicle"),
    "best-pets-for-apartments":           ("best pets for apartments",            "listicle"),
    "best-wet-cat-food-brands":           ("best wet cat food brands",            "listicle"),
    "how-to-cycle-a-fish-tank":           ("how to cycle a fish tank",            "how-to"),
    "how-to-introduce-a-new-cat":         ("how to introduce a new cat",          "how-to"),
    "how-to-train-a-cat":                 ("how to train a cat",                  "how-to"),
}


def extract_unique_cards(html_path: Path) -> list[str]:
    """Extract up to 3 unique product cards from existing HTML."""
    soup = BeautifulSoup(html_path.read_text(encoding="utf-8"), "html.parser")
    cards = soup.find_all("div", class_="product-card")
    seen_asins = set()
    unique = []
    for card in cards:
        link = card.find("a", class_="btn-amazon")
        asin = None
        if link and link.get("href"):
            m = re.search(r"/dp/([A-Z0-9]{10})", link["href"])
            if m:
                asin = m.group(1)
        if asin and asin in seen_asins:
            continue
        if asin:
            seen_asins.add(asin)
        unique.append(str(card))
        if len(unique) == 3:
            break
    return unique


def inject_cards(html_body: str, cards: list[str]) -> str:
    """Replace [PRODUCT_CARD] placeholders with actual card HTML."""
    for card in cards:
        html_body = html_body.replace("<p>[PRODUCT_CARD]</p>", card, 1)
    # Remove any remaining placeholders
    html_body = html_body.replace("<p>[PRODUCT_CARD]</p>", "")
    return html_body


def rewrite(slug: str, keyword: str, angle: str, config: dict) -> bool:
    html_path = Path(f"blog/posts/{slug}/index.html")
    if not html_path.exists():
        print(f"  SKIP — not found: {html_path}")
        return False

    print(f"  Extracting cards from {slug}...")
    cards = extract_unique_cards(html_path)
    print(f"  Found {len(cards)} unique product card(s)")

    print(f"  Generating new content for: {keyword} [{angle}]...")
    md_content = build_article(keyword, angle, config)
    title = build_title(keyword, angle)
    meta_desc = build_meta_description(keyword, title, angle)
    category = detect_category(keyword)
    word_count = len(md_content.split())

    # Convert markdown to HTML
    body_html = md_to_html(md_content)

    # Inject product cards
    body_html = inject_cards(body_html, cards)

    meta = {
        "slug": slug,
        "title": title,
        "meta_description": meta_desc,
        "primary_keyword": keyword,
        "secondary_keywords": [],
        "word_count": word_count,
        "reading_time": f"{max(1, word_count // 200)} min",
        "category": category,
        "tags": [keyword, category],
        "angle": angle,
        "status": "published",
        "created_at": datetime.now().isoformat(),
    }

    full_html = build_article_html(body_html, meta, config)
    html_path.write_text(full_html, encoding="utf-8")
    print(f"  ✓ Rewritten: {slug} ({word_count} words)")
    return True


def main():
    config = load_config()
    posts_dir = Path("blog/posts")
    success = 0

    for slug, (keyword, angle) in SLUG_MAP.items():
        print(f"\n[{slug}]")
        if rewrite(slug, keyword, angle, config):
            success += 1

    # Git commit
    print(f"\nAll done. {success}/{len(SLUG_MAP)} articles rewritten.")
    print("Committing...")
    os.system('git add blog/posts/')
    os.system('git commit -m "Rewrite: all articles upgraded to editorial v2 standard — real data, vet citations, journalist voice"')
    os.system('git push')
    print("Pushed.")

if __name__ == "__main__":
    main()
