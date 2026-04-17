#!/usr/bin/env python3
"""
Amazon Product Finder — Finds products via PAAPI and injects product cards.
Usage: python scripts/amazon_finder.py --slug "best-dog-food-2025-04-17"
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

PRODUCT_CARD_TEMPLATE = """<div class="product-card">
  <img src="{img_url}" alt="{name}" loading="lazy" width="200">
  <div class="product-info">
    <h4>{name}</h4>
    <div class="stars">{"★" * int(rating)}{"☆" * (5 - int(rating))} {rating} ({reviews:,} reviews)</div>
    <p class="product-desc">{benefit}</p>
    <span class="badge-prime">✓ Prime</span>
    <a href="https://amazon.com/dp/{asin}?tag={associate_tag}"
       class="btn-amazon"
       target="_blank"
       rel="nofollow sponsored noopener">
      Check Price on Amazon →
    </a>
  </div>
</div>"""


def load_config() -> dict:
    return json.loads(Path("config.json").read_text())


def build_product_card(product: dict, associate_tag: str) -> str:
    rating = product.get("rating", 4.5)
    stars = "★" * int(rating) + "☆" * (5 - int(rating))
    reviews = product.get("reviews", 0)

    return f"""<div class="product-card">
  <img src="{product.get('image', '')}" alt="{product['name']}" loading="lazy" width="200">
  <div class="product-info">
    <h4>{product['name']}</h4>
    <div class="stars">{stars} {rating} ({reviews:,} reviews)</div>
    <p class="product-desc">{product.get('benefit', 'Top-rated by pet owners.')}</p>
    <span class="badge-prime">✓ Prime</span>
    <a href="https://amazon.com/dp/{product['asin']}?tag={associate_tag}"
       class="btn-amazon"
       target="_blank"
       rel="nofollow sponsored noopener">
      Check Price on Amazon →
    </a>
  </div>
</div>"""


def search_products_paapi(search_terms: list[str], config: dict) -> list[dict]:
    """Search Amazon via PAAPI. Falls back to placeholder if keys not set."""
    api_config = config["apis"]

    if api_config["amazon_access_key"] == "YOUR_AMAZON_ACCESS_KEY":
        log.warning("Amazon PAAPI keys not configured. Using placeholder products.")
        return get_placeholder_products(search_terms[0] if search_terms else "pet product")

    try:
        from paapi5_python_sdk.api.default_api import DefaultApi
        from paapi5_python_sdk.models.partner_type import PartnerType
        from paapi5_python_sdk.models.search_items_request import SearchItemsRequest
        from paapi5_python_sdk.models.search_items_resource import SearchItemsResource
        import paapi5_python_sdk

        host = "webservices.amazon.com"
        region = "us-east-1"

        api = DefaultApi(
            access_key=api_config["amazon_access_key"],
            secret_key=api_config["amazon_secret_key"],
            host=host,
            region=region,
        )

        resources = [
            SearchItemsResource.ITEMINFO_TITLE,
            SearchItemsResource.OFFERS_LISTINGS_PRICE,
            SearchItemsResource.IMAGES_PRIMARY_MEDIUM,
            SearchItemsResource.CUSTOMERREVIEWS_COUNT,
            SearchItemsResource.CUSTOMERREVIEWS_STARRATING,
        ]

        products = []
        for term in search_terms[:3]:
            request = SearchItemsRequest(
                partner_tag=api_config["amazon_associate_tag"],
                partner_type=PartnerType.ASSOCIATES,
                keywords=term,
                search_index="PetSupplies",
                item_count=3,
                resources=resources,
            )
            response = api.search_items(request)
            if response.search_result and response.search_result.items:
                for item in response.search_result.items:
                    try:
                        rating = float(item.customer_reviews.star_rating.value) if item.customer_reviews else 4.5
                        reviews = int(item.customer_reviews.count) if item.customer_reviews else 0
                        if rating < 4.2 or reviews < 150:
                            continue
                        price_str = ""
                        if item.offers and item.offers.listings:
                            price_str = item.offers.listings[0].price.display_amount
                        products.append({
                            "asin": item.asin,
                            "name": item.item_info.title.display_value,
                            "rating": rating,
                            "reviews": reviews,
                            "image": item.images.primary.medium.url if item.images else "",
                            "price": price_str,
                            "benefit": f"Top-rated {term} loved by pet owners.",
                        })
                    except Exception as e:
                        log.warning(f"Error parsing product: {e}")
                        continue
        return products[:6]

    except ImportError:
        log.warning("paapi5_python_sdk not installed. Using placeholder products.")
        return get_placeholder_products(search_terms[0] if search_terms else "pet product")
    except Exception as e:
        log.error(f"PAAPI error: {e}")
        return get_placeholder_products(search_terms[0] if search_terms else "pet product")


def get_placeholder_products(keyword: str) -> list[dict]:
    """Returns placeholder products when PAAPI is not configured."""
    return [
        {
            "asin": "B000000001",
            "name": f"Top Rated {keyword.title()} — Editor's Choice",
            "rating": 4.7,
            "reviews": 2840,
            "image": "https://via.placeholder.com/200x200?text=Product+1",
            "benefit": "Loved by thousands of pet owners. Excellent quality and durability.",
        },
        {
            "asin": "B000000002",
            "name": f"Best Budget {keyword.title()} — Great Value",
            "rating": 4.4,
            "reviews": 1250,
            "image": "https://via.placeholder.com/200x200?text=Product+2",
            "benefit": "Perfect balance of quality and affordability. Prime eligible.",
        },
        {
            "asin": "B000000003",
            "name": f"Premium {keyword.title()} — Professional Grade",
            "rating": 4.8,
            "reviews": 890,
            "image": "https://via.placeholder.com/200x200?text=Product+3",
            "benefit": "Premium choice for pet owners who want the absolute best.",
        },
    ]


def inject_products(slug: str, config: dict) -> str:
    """Find draft article, inject product cards, move to ready."""
    draft_files = list(Path("articles/draft").glob(f"{slug}*.md"))
    if not draft_files:
        log.error(f"No draft found for slug: {slug}")
        raise FileNotFoundError(f"Draft not found: {slug}")

    draft_path = draft_files[0]
    meta_path = Path(str(draft_path).replace(".md", "_meta.json"))

    content = draft_path.read_text(encoding="utf-8")
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}

    search_terms = meta.get("amazon_searches", [slug.replace("-", " ")])
    products = search_products_paapi(search_terms, config)

    associate_tag = config["apis"]["amazon_associate_tag"]
    product_index = 0

    def replace_card(match):
        nonlocal product_index
        if product_index < len(products):
            card = build_product_card(products[product_index], associate_tag)
            product_index += 1
            return card
        return ""

    content = re.sub(r"\[PRODUCT_CARD\]", replace_card, content)

    ready_path = Path(f"articles/ready/{draft_path.name}")
    ready_path.write_text(content, encoding="utf-8")

    if meta_path.exists():
        meta["status"] = "ready"
        meta["products_injected"] = len(products)
        Path(f"articles/ready/{meta_path.name}").write_text(json.dumps(meta, indent=2))

    log.info(f"Injected {product_index} products into {ready_path}")
    return str(ready_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--slug", required=True)
    args = parser.parse_args()

    config = load_config()
    ready_path = inject_products(args.slug, config)
    print(json.dumps({"ready_path": ready_path}))
