#!/usr/bin/env python3
"""
rewrite_article.py — Rewrites the editorial body of an existing blog post.

Preserves: HTML head, header, breadcrumb, article-meta, adsense slots,
           sidebar, footer, AND all existing product-card divs.

Usage:
  python scripts/rewrite_article.py --slug best-cat-food-indoor-cats \
      --content articles/draft/rewrite_best-cat-food.md

Or from Python:
  from scripts.rewrite_article import rewrite_post_body
  rewrite_post_body("best-cat-food-indoor-cats", new_html_body)
"""

import re
import sys
import argparse
import markdown
from pathlib import Path


def extract_product_cards(html: str) -> list[str]:
    """Extract all <div class="product-card">...</div> blocks from HTML."""
    cards = []
    pattern = re.compile(
        r'<div class="product-card">.*?</div>\s*</div>',
        re.DOTALL,
    )
    for m in pattern.finditer(html):
        cards.append(m.group(0))
    return cards


def md_to_html(md_text: str) -> str:
    """Convert markdown to HTML using python-markdown."""
    return markdown.markdown(
        md_text,
        extensions=["tables", "fenced_code", "toc"],
        extension_configs={"toc": {"permalink": False}},
    )


def inject_cards(html_body: str, cards: list[str]) -> str:
    """Replace [PRODUCT_CARD] markers in html_body with the actual card HTML."""
    for card in cards:
        html_body = html_body.replace("[PRODUCT_CARD]", card, 1)
    # Remove any leftover [PRODUCT_CARD] markers (shouldn't happen)
    html_body = html_body.replace("<p>[PRODUCT_CARD]</p>", "")
    return html_body


def rewrite_post_body(slug: str, new_body_md: str) -> bool:
    """
    Rewrites the article body of blog/posts/{slug}/index.html.
    Preserves product cards, adsense slots, head, header, footer.
    new_body_md: full markdown for the new article body
                 (including # Title, intro, product [PRODUCT_CARD] markers, FAQ, etc.)
    Returns True on success.
    """
    post_path = Path(f"blog/posts/{slug}/index.html")
    if not post_path.exists():
        print(f"ERROR: {post_path} not found", file=sys.stderr)
        return False

    html = post_path.read_text(encoding="utf-8")

    # 1. Extract existing product cards (we'll re-inject them)
    cards = extract_product_cards(html)
    if not cards:
        print(f"WARNING: No product cards found in {slug} — body will have no products", file=sys.stderr)

    # 2. Convert new markdown body to HTML
    new_body_html = md_to_html(new_body_md)

    # 3. Inject product cards at [PRODUCT_CARD] positions
    new_body_html = inject_cards(new_body_html, cards)

    # 4. Extract title from first <h1> in new body
    h1_match = re.search(r"<h1[^>]*>(.*?)</h1>", new_body_html, re.DOTALL)
    new_title = h1_match.group(1).strip() if h1_match else None

    # 5. Find the article body region in the original HTML
    # Region starts after: <div class="ad-slot" id="ad-content-top" ...>
    # Region ends before:  <!-- ADSENSE SLOT: mid-article -->
    start_pattern = re.compile(
        r'(<div class="ad-slot" id="ad-content-top"[^>]*>(?:</div>)?)\s*\n',
        re.DOTALL,
    )
    end_pattern = re.compile(
        r'\s*<!-- ADSENSE SLOT: mid-article -->',
        re.DOTALL,
    )

    start_match = start_pattern.search(html)
    end_match = end_pattern.search(html)

    if not start_match or not end_match:
        print(f"ERROR: Could not find article body markers in {slug}", file=sys.stderr)
        return False

    body_start = start_match.end()
    body_end = end_match.start()

    new_html = (
        html[:body_start]
        + "\n\n      "
        + new_body_html
        + "\n\n      "
        + html[body_end:]
    )

    # 6. Update <title> tag and meta description if we have a new title
    if new_title:
        # Update <title>
        new_html = re.sub(
            r"<title>[^<]+</title>",
            f"<title>{new_title} | PawLife Guide</title>",
            new_html,
        )
        # Update og:title
        new_html = re.sub(
            r'(<meta property="og:title" content=")[^"]*(")',
            rf"\g<1>{new_title}\g<2>",
            new_html,
        )
        # Update twitter:title if present
        new_html = re.sub(
            r'(<meta name="twitter:title" content=")[^"]*(")',
            rf"\g<1>{new_title}\g<2>",
            new_html,
        )
        # Update schema headline
        # JSON-LD is inline, parse carefully
        def update_schema(m):
            try:
                import json
                schema = json.loads(m.group(1))
                schema["headline"] = new_title
                schema["description"] = schema.get("description", "")
                return f'<script type="application/ld+json">{json.dumps(schema, ensure_ascii=False)}</script>'
            except Exception:
                return m.group(0)

        new_html = re.sub(
            r'<script type="application/ld\+json">(.*?)</script>',
            update_schema,
            new_html,
            flags=re.DOTALL,
        )

    # 7. Fix "best best" in meta description
    new_html = re.sub(r"\bbest best\b", "best", new_html, flags=re.IGNORECASE)

    post_path.write_text(new_html, encoding="utf-8")
    print(f"Rewritten: {post_path} ({len(cards)} product cards preserved)")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Rewrite article body preserving product cards")
    parser.add_argument("--slug", required=True, help="Post slug (directory name under blog/posts/)")
    parser.add_argument("--content", required=True, help="Path to markdown file with new article content")
    args = parser.parse_args()

    md_content = Path(args.content).read_text(encoding="utf-8")
    success = rewrite_post_body(args.slug, md_content)
    sys.exit(0 if success else 1)
