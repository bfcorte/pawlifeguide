#!/usr/bin/env python3
"""
Ads Manager — Installs Google AdSense codes across all blog HTML files.
Usage: python scripts/ads_manager.py --mode auto --code "<script>...</script>"
       python scripts/ads_manager.py --mode slot --slot content_top --code "<script>...</script>"
       python scripts/ads_manager.py --status
"""

import json
import re
import argparse
import logging
import subprocess
from pathlib import Path
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("logs/activity.log"), logging.StreamHandler()],
)
log = logging.getLogger(__name__)

SLOT_PLACEHOLDERS = {
    "header": "[ADSENSE_HEADER_CODE_HERE]",
    "content_top": "[ADSENSE_CONTENT_TOP_CODE_HERE]",
    "content_mid": "[ADSENSE_CONTENT_MID_CODE_HERE]",
    "sidebar": "[ADSENSE_SIDEBAR_CODE_HERE]",
    "footer": "[ADSENSE_FOOTER_CODE_HERE]",
}


def load_config() -> dict:
    return json.loads(Path("config.json").read_text())


def save_config(config: dict) -> None:
    Path("config.json").write_text(json.dumps(config, indent=2))


def get_html_files() -> list[Path]:
    return list(Path("blog").rglob("*.html"))


def extract_publisher_id(code: str) -> str | None:
    match = re.search(r"ca-pub-\d+", code)
    return match.group(0) if match else None


def install_auto_ads(code: str) -> int:
    """Install auto ads script in <head> of all HTML files."""
    config = load_config()
    html_files = get_html_files()
    updated = 0

    pub_id = extract_publisher_id(code)
    if pub_id:
        config["seo"]["adsense_publisher_id"] = pub_id
        config["seo"]["adsense_installed"] = True

    for path in html_files:
        content = path.read_text(encoding="utf-8")
        if "pagead2.googlesyndication.com" in content:
            continue  # already installed
        if "</head>" in content:
            content = content.replace("</head>", f"  {code}\n</head>")
            path.write_text(content, encoding="utf-8")
            updated += 1

    save_config(config)
    log.info(f"Auto ads installed in {updated} files")
    return updated


def install_slot(slot_name: str, code: str) -> int:
    """Replace placeholder for a specific slot in all HTML files."""
    config = load_config()
    placeholder = SLOT_PLACEHOLDERS.get(slot_name)
    if not placeholder:
        log.error(f"Unknown slot: {slot_name}")
        return 0

    html_files = get_html_files()
    updated = 0

    for path in html_files:
        content = path.read_text(encoding="utf-8")
        if placeholder in content:
            content = content.replace(placeholder, code)
            path.write_text(content, encoding="utf-8")
            updated += 1

    config["seo"]["adsense_slots"][slot_name] = code
    if not config["seo"]["adsense_installed"]:
        all_slots_filled = all(
            config["seo"]["adsense_slots"].get(s) for s in SLOT_PLACEHOLDERS
        )
        if all_slots_filled:
            config["seo"]["adsense_installed"] = True
    save_config(config)

    log.info(f"Slot '{slot_name}' installed in {updated} files")
    return updated


def show_status() -> None:
    config = load_config()
    seo = config["seo"]
    identity = config["blog_identity"]
    slots = seo.get("adsense_slots", {})
    html_files = get_html_files()

    articles_with_ads = sum(
        1 for f in html_files
        if "pagead2" in f.read_text(encoding="utf-8") or
           any(slots.get(s) for s in SLOT_PLACEHOLDERS)
    )

    print(f"""
📊 AdSense Status — {identity['name']}

  Installed:     {'✅ Yes' if seo.get('adsense_installed') else '❌ No'}
  Publisher ID:  {seo.get('adsense_publisher_id') or '⚠️  Not configured'}

  Slots:
    Header (728×90):          {'✅ installed' if slots.get('header') else '⬜ empty'}
    After intro (336×280):    {'✅ installed' if slots.get('content_top') else '⬜ empty'}
    Mid-article (336×280):    {'✅ installed' if slots.get('content_mid') else '⬜ empty'}
    Sidebar (300×600):        {'✅ installed' if slots.get('sidebar') else '⬜ empty'}
    Before footer (728×90):   {'✅ installed' if slots.get('footer') else '⬜ empty'}

  HTML files: {len(html_files)} total
""")


def git_push_ads() -> None:
    config = load_config()
    if not config["publishing"].get("auto_push", True):
        return
    try:
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", "ads: install AdSense codes"], check=True)
        subprocess.run(["git", "push"], check=True)
        log.info("Git push successful")
    except subprocess.CalledProcessError as e:
        log.error(f"Git push failed: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["auto", "slot", "status"], default="status")
    parser.add_argument("--code", default="")
    parser.add_argument("--slot", default="")
    args = parser.parse_args()

    if args.mode == "status":
        show_status()
    elif args.mode == "auto":
        count = install_auto_ads(args.code)
        print(f"✅ Auto ads installed in {count} files")
        git_push_ads()
    elif args.mode == "slot":
        if not args.slot:
            print("Error: --slot required for slot mode")
            exit(1)
        count = install_slot(args.slot, args.code)
        print(f"✅ Slot '{args.slot}' installed in {count} files")
