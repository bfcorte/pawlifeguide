#!/usr/bin/env python3
"""
Publisher — Converts ready articles to HTML and publishes to blog/.
Usage: python scripts/publisher.py --slug "best-dog-food"
"""

import json
import re
import argparse
import logging
import subprocess
from datetime import datetime
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("logs/activity.log"), logging.StreamHandler()],
)
log = logging.getLogger(__name__)


def load_config() -> dict:
    return json.loads(Path("config.json").read_text())


def find_ready_article(slug: str) -> tuple[Path, Path]:
    ready_files = list(Path("articles/ready").glob(f"{slug}*.md"))
    if not ready_files:
        raise FileNotFoundError(f"No ready article for slug: {slug}")
    article_path = ready_files[0]
    meta_path = Path(str(article_path).replace(".md", "_meta.json"))
    return article_path, meta_path


def md_to_html(content: str) -> str:
    try:
        import markdown
        return markdown.markdown(
            content,
            extensions=["tables", "fenced_code", "toc", "nl2br"],
        )
    except ImportError:
        # Fallback: basic conversion
        html = content
        html = re.sub(r"^# (.+)$", r"<h1>\1</h1>", html, flags=re.MULTILINE)
        html = re.sub(r"^## (.+)$", r"<h2>\1</h2>", html, flags=re.MULTILINE)
        html = re.sub(r"^### (.+)$", r"<h3>\1</h3>", html, flags=re.MULTILINE)
        html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html)
        html = re.sub(r"\*(.+?)\*", r"<em>\1</em>", html)
        html = re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2">\1</a>', html)
        html = re.sub(r"\n\n", r"</p><p>", html)
        return f"<p>{html}</p>"


def build_adsense_slot(slot_name: str, config: dict) -> str:
    slot_code = config["seo"]["adsense_slots"].get(slot_name, "")
    if slot_code:
        return f'<div class="ad-slot" id="ad-{slot_name}" data-slot="{slot_name}">{slot_code}</div>'
    return f'<!-- ADSENSE SLOT: {slot_name} -->\n<div class="ad-slot" id="ad-{slot_name.replace("_","-")}" data-slot="{slot_name}">[ADSENSE_{slot_name.upper()}_CODE_HERE]</div>'


def build_article_html(content_html: str, meta: dict, config: dict) -> str:
    identity = config["blog_identity"]
    seo = config["seo"]
    url = identity["url"]
    slug = meta["slug"]
    title = meta["title"]
    description = meta["meta_description"]
    canonical = f"{url}/posts/{slug}/"
    ga_id = seo.get("google_analytics_id", "")
    primary_color = identity.get("primary_color", "#F97316")
    accent_color = identity.get("accent_color", "#1E3A5F")

    ga_snippet = ""
    if ga_id:
        ga_snippet = f"""<!-- Google tag (gtag.js) -->
    <script async src="https://www.googletagmanager.com/gtag/js?id={ga_id}"></script>
    <script>
      window.dataLayer = window.dataLayer || [];
      function gtag(){{dataLayer.push(arguments);}}
      gtag('js', new Date());
      gtag('config', '{ga_id}');
    </script>"""

    adsense_pub = seo.get("adsense_publisher_id", "")
    adsense_snippet = ""
    if adsense_pub:
        adsense_snippet = f'<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={adsense_pub}" crossorigin="anonymous"></script>'

    schema = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title,
        "description": description,
        "author": {"@type": "Organization", "name": identity["name"]},
        "publisher": {"@type": "Organization", "name": identity["name"], "url": url},
        "datePublished": meta.get("created_at", datetime.now().isoformat()),
        "dateModified": datetime.now().isoformat(),
        "mainEntityOfPage": {"@type": "WebPage", "@id": canonical},
    }

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} | {identity['name']}</title>
  <meta name="description" content="{description}">
  <link rel="canonical" href="{canonical}">
  <meta property="og:title" content="{title}">
  <meta property="og:description" content="{description}">
  <meta property="og:url" content="{canonical}">
  <meta property="og:type" content="article">
  <meta property="og:site_name" content="{identity['name']}">
  <meta name="twitter:card" content="summary_large_image">
  <link rel="stylesheet" href="../../assets/css/style.css">
  <script type="application/ld+json">{json.dumps(schema)}</script>
  {ga_snippet}
  {adsense_snippet}
</head>
<body>
  <header class="site-header">
    <div class="container">
      <a href="../../index.html" class="logo">{identity['name']}</a>
      <p class="tagline">{identity['tagline']}</p>
      <nav>
        <a href="../../index.html">Home</a>
        <a href="../../category/index.html">Categories</a>
        <a href="../../about.html">About</a>
      </nav>
    </div>
  </header>

  <!-- ADSENSE SLOT: header -->
  {build_adsense_slot('header', config)}

  <main class="container article-layout">
    <article class="post-content">
      <nav class="breadcrumb">
        <a href="../../index.html">Home</a> &rsaquo;
        <a href="../../category/{meta.get('category','pets')}/index.html">{meta.get('category','Pets').title()}</a> &rsaquo;
        <span>{title}</span>
      </nav>

      <div class="article-meta">
        <time datetime="{meta.get('created_at','')[:10]}">{datetime.now().strftime('%B %d, %Y')}</time>
        &bull; {meta.get('reading_time','5 min')} read
        &bull; {meta.get('word_count',0):,} words
      </div>

      <!-- ADSENSE SLOT: after-intro (highest RPM) -->
      {build_adsense_slot('content_top', config)}

      {content_html}

      <!-- ADSENSE SLOT: mid-article -->
      {build_adsense_slot('content_mid', config)}

    </article>

    <aside class="sidebar">
      <div class="sidebar-widget">
        <h3>Top Picks</h3>
        <p>Our most recommended products this month.</p>
        <a href="../../index.html" class="btn-outline">See All Picks</a>
      </div>

      <!-- ADSENSE SLOT: sidebar sticky -->
      {build_adsense_slot('sidebar', config)}
    </aside>
  </main>

  <!-- ADSENSE SLOT: before footer -->
  {build_adsense_slot('footer', config)}

  <footer class="site-footer">
    <div class="container">
      <p>&copy; {datetime.now().year} {identity['name']} &mdash; {identity['tagline']}</p>
      <p class="disclaimer">
        {identity['name']} is a participant in the Amazon Services LLC Associates Program,
        an affiliate advertising program designed to provide a means for sites to earn
        advertising fees by advertising and linking to Amazon.com.
      </p>
      <nav class="footer-nav">
        <a href="../../privacy.html">Privacy Policy</a>
        <a href="../../disclaimer.html">Affiliate Disclaimer</a>
        <a href="../../contact.html">Contact</a>
      </nav>
    </div>
  </footer>

  <script src="../../assets/js/main.js"></script>
</body>
</html>"""


def update_homepage(meta: dict, config: dict) -> None:
    index_path = Path("blog/index.html")
    if not index_path.exists():
        log.warning("index.html not found — skipping homepage update")
        return

    content = index_path.read_text(encoding="utf-8")
    slug = meta["slug"]
    title = meta["title"]
    description = meta["meta_description"]
    category = meta.get("category", "pets")
    date_str = datetime.now().strftime("%B %d, %Y")

    card_html = f"""
    <!-- POST: {slug} -->
    <article class="post-card">
      <div class="post-card-body">
        <span class="category-badge">{category.title()}</span>
        <h2><a href="posts/{slug}/index.html">{title}</a></h2>
        <p>{description}</p>
        <div class="post-meta">
          <time>{date_str}</time>
          &bull; {meta.get('reading_time','5 min')} read
        </div>
        <a href="posts/{slug}/index.html" class="btn-read-more">Read More →</a>
      </div>
    </article>"""

    marker = "<!-- POSTS_START -->"
    if marker in content:
        content = content.replace(marker, marker + card_html)
        index_path.write_text(content, encoding="utf-8")
        log.info("Homepage updated with new post card")
    else:
        log.warning("POSTS_START marker not found in index.html")


def update_sitemap(meta: dict, config: dict) -> None:
    sitemap_path = Path("blog/sitemap.xml")
    url = config["blog_identity"]["url"]
    slug = meta["slug"]
    date_str = datetime.now().strftime("%Y-%m-%d")

    entry = f"""  <url>
    <loc>{url}/posts/{slug}/</loc>
    <lastmod>{date_str}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>"""

    if sitemap_path.exists():
        content = sitemap_path.read_text(encoding="utf-8")
        content = content.replace("</urlset>", entry + "\n</urlset>")
        sitemap_path.write_text(content, encoding="utf-8")
        log.info("Sitemap updated")


CATEGORY_ICONS = {
    "dogs": "🐕", "dog": "🐕",
    "cats": "🐈", "cat": "🐈",
    "fish": "🐠", "aquarium": "🐠", "aquário": "🐠",
    "birds": "🐦", "bird": "🐦",
    "small-pets": "🐹", "hamster": "🐹", "rabbit": "🐰",
    "reptiles": "🦎", "reptile": "🦎",
    "horses": "🐴", "horse": "🐴",
    "guides": "📖", "guide": "📖",
    "health": "💊", "nutrition": "🥗", "food": "🍖",
    "training": "🎓", "grooming": "✂️",
    "pets": "🐾",
}


def get_category_icon(category: str) -> str:
    key = category.lower().replace(" ", "-")
    for k, icon in CATEGORY_ICONS.items():
        if k in key:
            return icon
    return "🐾"


def ensure_category_page(category: str, config: dict) -> None:
    """Create category page if it doesn't exist, and update categories index."""
    slug = category.lower().strip().replace(" ", "-")
    cat_dir = Path(f"blog/category/{slug}")
    cat_dir.mkdir(parents=True, exist_ok=True)
    cat_page = cat_dir / "index.html"
    url = config["blog_identity"]["url"]
    icon = get_category_icon(slug)

    if not cat_page.exists():
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{category.title()} — PawLife Guide</title>
  <meta name="description" content="Best tips and product reviews for {category.lower()} owners. Curated by PawLife Guide.">
  <link rel="canonical" href="{url}/category/{slug}/">
  <link rel="stylesheet" href="../../assets/css/style.css">
  <script async src="https://www.googletagmanager.com/gtag/js?id={config['seo']['google_analytics_id']}"></script>
  <script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','{config['seo']['google_analytics_id']}');</script>
</head>
<body>
  <header class="site-header">
    <div class="container">
      <a href="../../index.html" class="logo">PawLife Guide</a>
      <p class="tagline">The best tips and products for your pet</p>
      <nav>
        <a href="../../index.html">Home</a>
        <a href="../index.html">Categories</a>
        <a href="../../about.html">About</a>
      </nav>
    </div>
  </header>
  <div class="container" style="padding:48px 0 80px;">
    <div style="margin-bottom:32px;">
      <a href="../index.html" style="color:#F97316; font-size:0.9rem;">← All Categories</a>
    </div>
    <h1 style="font-size:2.2rem; font-weight:800; margin-bottom:8px;">{icon} {category.title()}</h1>
    <p style="color:#64748B; margin-bottom:48px;">All articles about {category.lower()}.</p>
    <div class="posts-grid">
      <!-- CATEGORY_POSTS_START -->
    </div>
  </div>
  <footer class="site-footer">
    <div class="container">
      <p><strong style="color:white;">PawLife Guide</strong></p>
      <p class="disclaimer">PawLife Guide is a participant in the Amazon Services LLC Associates Program.</p>
      <nav class="footer-nav">
        <a href="../../privacy.html">Privacy Policy</a>
        <a href="../../disclaimer.html">Affiliate Disclaimer</a>
        <a href="../../contact.html">Contact</a>
      </nav>
    </div>
  </footer>
  <script src="../../assets/js/main.js"></script>
</body>
</html>"""
        cat_page.write_text(html, encoding="utf-8")
        log.info(f"Created category page: {cat_page}")

    # Add post card to category page
    return slug


def update_category_page(category_slug: str, meta: dict) -> None:
    """Inject post card into the category page."""
    cat_page = Path(f"blog/category/{category_slug}/index.html")
    if not cat_page.exists():
        return
    content = cat_page.read_text(encoding="utf-8")
    slug = meta["slug"]
    title = meta["title"]
    description = meta["meta_description"]
    date_str = datetime.now().strftime("%B %d, %Y")

    card = f"""
      <!-- POST: {slug} -->
      <article class="post-card">
        <div class="post-card-body">
          <h2><a href="../../posts/{slug}/index.html">{title}</a></h2>
          <p>{description}</p>
          <div class="post-meta"><time>{date_str}</time> &bull; {meta.get('reading_time','5 min')} read</div>
          <a href="../../posts/{slug}/index.html" class="btn-read-more">Read More →</a>
        </div>
      </article>"""

    marker = "<!-- CATEGORY_POSTS_START -->"
    if marker in content:
        content = content.replace(marker, marker + card)
        cat_page.write_text(content, encoding="utf-8")


def update_categories_index(category: str, config: dict) -> None:
    """Add category card to the main categories index if not already present."""
    index_path = Path("blog/category/index.html")
    if not index_path.exists():
        return
    content = index_path.read_text(encoding="utf-8")
    slug = category.lower().strip().replace(" ", "-")
    url = config["blog_identity"]["url"]
    icon = get_category_icon(slug)

    marker = f"<!-- CAT: {slug} -->"
    if marker in content:
        return  # already listed

    card = f"""
      {marker}
      <a href="{slug}/index.html" style="display:block; background:white; border:1px solid #E2E8F0; border-radius:12px; padding:28px; text-align:center; text-decoration:none; transition:all 0.25s; color:#1A1A2E;"
         onmouseover="this.style.boxShadow='0 8px 32px rgba(249,115,22,0.15)';this.style.borderColor='#FED7AA'"
         onmouseout="this.style.boxShadow='';this.style.borderColor='#E2E8F0'">
        <div style="font-size:2.5rem; margin-bottom:12px;">{icon}</div>
        <strong style="font-size:1.05rem;">{category.title()}</strong>
      </a>"""

    insert_marker = "<!-- CATEGORIES_END -->"
    if insert_marker in content:
        content = content.replace(insert_marker, card + "\n      " + insert_marker)
        index_path.write_text(content, encoding="utf-8")
        log.info(f"Added '{category}' to categories index")


def update_feed(meta: dict, config: dict) -> None:
    feed_path = Path("blog/feed.xml")
    url = config["blog_identity"]["url"]
    slug = meta["slug"]
    title = meta["title"]
    description = meta["meta_description"]
    pub_date = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0000")

    entry = f"""  <item>
    <title><![CDATA[{title}]]></title>
    <link>{url}/posts/{slug}/</link>
    <description><![CDATA[{description}]]></description>
    <pubDate>{pub_date}</pubDate>
    <guid>{url}/posts/{slug}/</guid>
  </item>"""

    if feed_path.exists():
        content = feed_path.read_text(encoding="utf-8")
        content = content.replace("</channel>", entry + "\n</channel>")
        feed_path.write_text(content, encoding="utf-8")
        log.info("RSS feed updated")


def publish(slug: str) -> dict:
    config = load_config()
    article_path, meta_path = find_ready_article(slug)

    content = article_path.read_text(encoding="utf-8")
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {"slug": slug}

    content_html = md_to_html(content)
    article_html = build_article_html(content_html, meta, config)

    post_dir = Path(f"blog/posts/{slug}")
    post_dir.mkdir(parents=True, exist_ok=True)
    post_path = post_dir / "index.html"
    post_path.write_text(article_html, encoding="utf-8")
    log.info(f"Published: {post_path}")

    update_homepage(meta, config)
    update_sitemap(meta, config)
    update_feed(meta, config)

    # Auto-create and update category pages
    category = meta.get("category", "pets")
    cat_slug = ensure_category_page(category, config)
    update_category_page(cat_slug, meta)
    update_categories_index(category, config)

    # Move to published
    published_log = {
        "slug": slug,
        "title": meta.get("title", ""),
        "published_at": datetime.now().isoformat(),
        "post_url": f"{config['blog_identity']['url']}/posts/{slug}/",
    }
    Path(f"articles/published/{slug}_log.json").write_text(
        json.dumps(published_log, indent=2)
    )

    # Git push if auto_push enabled
    if config["publishing"].get("auto_push", True):
        try:
            subprocess.run(["git", "add", "."], check=True)
            subprocess.run(
                ["git", "commit", "-m", f"Post: {meta.get('title', slug)}"],
                check=True,
            )
            subprocess.run(["git", "push"], check=True)
            log.info("Git push successful")
            published_log["pushed"] = True
        except subprocess.CalledProcessError as e:
            log.error(f"Git push failed: {e}")
            published_log["pushed"] = False

    with open("logs/activity.log", "a") as f:
        f.write(
            f"{datetime.now()} | PUBLISHED | {slug} | {meta.get('title','')}\n"
        )

    return published_log


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--slug", required=True)
    args = parser.parse_args()

    result = publish(args.slug)
    print(json.dumps(result))
