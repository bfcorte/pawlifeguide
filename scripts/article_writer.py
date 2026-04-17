#!/usr/bin/env python3
"""
Article Writer — Generates SEO-optimized articles in Markdown.
Usage: python scripts/article_writer.py --keyword "best dog food" --angle listicle
"""

import json
import re
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

DISCLAIMER = (
    "*As an Amazon Associate I earn from qualifying purchases. "
    "This doesn't affect our recommendations.*\n\n"
)


def load_config() -> dict:
    return json.loads(Path("config.json").read_text())


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-")


def build_title(keyword: str, angle: str) -> str:
    year = datetime.now().year
    kw_cap = keyword.title()

    templates = {
        "listicle": f"7 Best {kw_cap} in {year} (Tested & Reviewed)",
        "how-to": f"How to Choose the Best {kw_cap}: Complete Guide ({year})",
        "comparison": f"Best {kw_cap} Compared: Which One Is Worth It in {year}?",
        "single-review": f"The Best {kw_cap} in {year}: In-Depth Review",
        "buyers-guide": f"How to Choose the Best {kw_cap} ({year} Buyer's Guide)",
        "budget": f"Best Affordable {kw_cap} in {year} (Under $50)",
        "premium": f"Best Premium {kw_cap} Worth Every Penny in {year}",
        "seasonal": f"Best {kw_cap} for This Season ({year})",
        "annual_update": f"Best {kw_cap} in {year} (Updated)",
    }
    return templates.get(angle, f"Best {kw_cap} — Complete Guide {year}")


def build_meta_description(keyword: str, title: str) -> str:
    desc = (
        f"Looking for the best {keyword.lower()}? "
        f"We tested the top options so you don't have to. "
        f"See our expert picks and save time. Check prices on Amazon."
    )
    return desc[:160]


def build_article(keyword: str, angle: str, config: dict) -> str:
    identity = config["blog_identity"]
    title = build_title(keyword, angle)
    year = datetime.now().year

    intro_hooks = {
        "listicle": f"Finding the right {keyword.lower()} can feel overwhelming — there are hundreds of options and the reviews online are all over the place.",
        "how-to": f"Choosing the best {keyword.lower()} isn't as simple as picking the first result on Amazon. The wrong choice can cost you time, money, and frustration.",
        "comparison": f"Two products, one decision. We break down the most popular {keyword.lower()} options side by side so you know exactly which one fits your situation.",
        "buyers-guide": f"Before spending your money on {keyword.lower()}, there are a few key things you need to know. Most people skip these — and regret it.",
        "budget": f"You don't have to spend a fortune to get a great {keyword.lower()}. We found the best affordable options that actually deliver.",
        "premium": f"When only the best will do, {keyword.lower()} choices matter. We found the premium options that are genuinely worth the investment.",
        "seasonal": f"The right {keyword.lower()} makes all the difference this season. Here are the top picks that pet owners love right now.",
        "annual_update": f"We've updated our {keyword.lower()} recommendations for {year} with new products, current prices, and fresh reviews.",
    }

    hook = intro_hooks.get(angle, intro_hooks["listicle"])

    article = f"""# {title}

{DISCLAIMER}

{hook}

After spending hours researching and testing, we've narrowed down the best options for {identity['target_audience'].lower()}. Whether you're a first-time pet owner or a seasoned pro, this guide has you covered.

<div class="quick-answer">
<strong>Quick Answer:</strong> The best {keyword.lower()} in {year} is one that balances quality, safety, and value. Our top pick is highly rated by thousands of pet owners and available on Amazon Prime. See our #1 recommendation below.
</div>

## Table of Contents
- [Why This Matters](#why-this-matters)
- [Our Top Picks](#our-top-picks)
- [What to Look For](#what-to-look-for)
- [Detailed Reviews](#detailed-reviews)
- [Comparison Table](#comparison-table)
- [FAQ](#faq)
- [Final Verdict](#final-verdict)

---

## Why This Matters

Choosing the right {keyword.lower()} directly impacts your pet's health, comfort, and happiness. With so many options on the market, it's easy to end up with something that looks good but underdelivers.

We've done the research so you don't have to. Every pick on this list has:
- A rating of **4.2 stars or higher** on Amazon
- **150+ verified reviews** from real pet owners
- **Amazon Prime** eligibility for fast, free shipping
- Proven track record of quality and safety

---

## Our Top Picks

Here's a quick overview before we dive into the details.

[PRODUCT_CARD]

[PRODUCT_CARD]

[PRODUCT_CARD]

---

## What to Look For

Before buying, consider these key factors:

### 1. Safety & Materials
Always check that the product uses pet-safe, non-toxic materials. Look for certifications where applicable.

### 2. Size & Fit
What works for a large dog may not suit a small cat. Always check the size guide before ordering.

### 3. Durability
Pets can be rough on their gear. Read reviews specifically mentioning how long the product lasts.

### 4. Value for Money
Price alone doesn't determine quality. The best {keyword.lower()} balances cost and performance — not just the cheapest or most expensive option.

### 5. Ease of Use
The easier it is for you to use, the more consistently your pet will benefit from it.

---

## Detailed Reviews

### 1. Best Overall

[PRODUCT_CARD]

**Why we love it:** This option consistently earns top marks from pet owners for its combination of quality, durability, and price. Thousands of {identity['target_audience'].lower().replace('us readers interested in ', '')} owners swear by it.

**Pros:**
- High quality materials
- Easy to clean
- Comes in multiple sizes
- Ships fast with Prime

**Cons:**
- Slightly pricier than budget alternatives
- May take a few days for pets to adjust

**Best for:** Most pet owners looking for a reliable, well-reviewed option.

> *Prices change frequently — check current deals on Amazon.*

---

### 2. Best Budget Option

[PRODUCT_CARD]

**Why we love it:** You don't have to break the bank for quality. This pick delivers excellent value at a fraction of the cost of premium options.

**Best for:** First-time pet owners or those on a budget.

---

### 3. Best Premium Option

[PRODUCT_CARD]

**Why we love it:** If you want the absolute best, this is it. Premium materials, exceptional durability, and top-rated by professionals.

**Best for:** Pet owners who want the very best, no compromises.

---

## Comparison Table

| Product | Rating | Price Range | Best For |
|---|---|---|---|
| Option 1 | ★★★★★ | $$ | Overall best |
| Option 2 | ★★★★☆ | $ | Budget buyers |
| Option 3 | ★★★★★ | $$$ | Premium choice |
| Option 4 | ★★★★☆ | $$ | Specific use |
| Option 5 | ★★★★☆ | $$ | Alternatives |

---

## FAQ

### What is the best {keyword.lower()} for beginners?
For beginners, we recommend starting with our top pick — it's easy to use, well-reviewed, and covers the most common needs. It's the #1 choice in {year} among new pet owners.

### How much should I spend on {keyword.lower()}?
You don't need to spend a fortune. A budget of $20–$50 will get you a solid option. Our budget pick delivers excellent value in that range.

### Is it safe to buy {keyword.lower()} on Amazon?
Yes, as long as you stick to verified products with strong reviews. All picks in this guide have 150+ verified reviews and 4.2+ star ratings.

### How often should I replace {keyword.lower()}?
It depends on the product and how much wear it gets. As a general rule, inspect it monthly and replace when you see signs of wear, damage, or reduced effectiveness.

### What should I avoid when buying {keyword.lower()}?
Avoid products with no reviews, vague material descriptions, or ratings below 4 stars. Also watch out for suspiciously cheap options with no brand recognition.

### Are there any {keyword.lower()} options that work for multiple pets?
Yes — several of our picks are versatile enough to work for both dogs and cats. Check the product description for compatibility.

### Where can I find the best deals on {keyword.lower()}?
Amazon is consistently the best place for deals, especially if you have Prime. Prices change frequently, so check the link for current pricing.

---

## Final Verdict

After testing and researching dozens of options, our top recommendation for the best {keyword.lower()} in {year} remains the **#1 pick** at the top of this list. It hits the sweet spot between quality, affordability, and ease of use.

If you're on a budget, the **budget option** won't let you down. And if money is no object, the **premium pick** is worth every penny.

No matter which you choose, all the products on this list are tried, tested, and trusted by {identity['target_audience'].lower()}.

**Ready to buy?** Check current prices and availability on Amazon using the links above — and don't forget to check if Prime shipping is available in your area.

---

*As an Amazon Associate I earn from qualifying purchases. Prices are accurate at time of publication but may change.*
"""

    return article.strip()


def save_article(keyword: str, angle: str, config: dict) -> tuple[str, str]:
    slug = slugify(keyword)
    date_str = datetime.now().strftime("%Y-%m-%d")
    filename = f"{slug}_{date_str}"

    article_content = build_article(keyword, angle, config)
    title = build_title(keyword, angle)
    meta_desc = build_meta_description(keyword, title)

    draft_path = Path(f"articles/draft/{filename}.md")
    meta_path = Path(f"articles/draft/{filename}_meta.json")

    draft_path.write_text(article_content, encoding="utf-8")

    meta = {
        "slug": slug,
        "title": title,
        "meta_description": meta_desc,
        "primary_keyword": keyword,
        "secondary_keywords": [],
        "word_count": len(article_content.split()),
        "reading_time": f"{max(1, len(article_content.split()) // 200)} min",
        "category": config["blog_identity"]["niche"],
        "tags": [keyword, config["blog_identity"]["niche"]],
        "angle": angle,
        "amazon_searches": [keyword, f"best {keyword}", f"{keyword} recommended"],
        "status": "draft",
        "created_at": datetime.now().isoformat(),
    }
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    log.info(f"Draft saved: {draft_path}")
    return str(draft_path), slug


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--keyword", required=True)
    parser.add_argument("--angle", default="listicle")
    args = parser.parse_args()

    config = load_config()
    path, slug = save_article(args.keyword, args.angle, config)
    print(json.dumps({"draft_path": path, "slug": slug, "title": build_title(args.keyword, args.angle)}))
