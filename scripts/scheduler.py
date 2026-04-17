#!/usr/bin/env python3
"""
Scheduler — Runs the daily blog pipeline at 08:00 AM.
Usage: python scripts/scheduler.py
       python scripts/scheduler.py &  (background)
"""

import json
import logging
import subprocess
import sys
from datetime import datetime
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/scheduler.log"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)


def load_config() -> dict:
    return json.loads(Path("config.json").read_text())


def daily_post_job() -> None:
    log.info("=" * 50)
    log.info("DAILY POST JOB STARTED")
    config = load_config()
    topic = config["blog_identity"]["topic"]

    try:
        kw_file = Path(f"keywords/{topic.replace(' ', '_')}_keywords.json")
        needs_refresh = True

        if kw_file.exists():
            data = json.loads(kw_file.read_text())
            expires = datetime.fromisoformat(data["expires_at"])
            if datetime.now() < expires:
                needs_refresh = False
                log.info(f"Keywords valid until {expires.date()}")

        if needs_refresh:
            log.info("Running keyword research (PyTrends)...")
            r = subprocess.run(
                [sys.executable, "scripts/keyword_research.py", "--topic", topic],
                capture_output=True,
                text=True,
                timeout=300,
            )
            if r.returncode != 0:
                log.error(f"Research failed: {r.stderr}")
                return

        r = subprocess.run(
            [sys.executable, "scripts/keyword_selector.py", "--topic", topic],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if r.returncode != 0:
            log.warning("No keywords available — running refresh")
            subprocess.run(
                [sys.executable, "scripts/keyword_research.py", "--topic", topic, "--force"],
                timeout=300,
            )
            return

        selected = json.loads(r.stdout)
        log.info(f"Keyword: {selected['keyword']}")
        log.info(f"Angle: {selected['new_angle']}")

        pipeline = subprocess.run(
            [
                sys.executable,
                "scripts/run_pipeline.py",
                "--keyword", selected["keyword"],
                "--angle", selected["new_angle"],
            ],
            capture_output=True,
            text=True,
            timeout=600,
        )

        if pipeline.returncode == 0:
            out = json.loads(pipeline.stdout)
            log.info(f"SUCCESS — Draft: {out['draft_path']}")
            log.info(f"Title: {out['title']}")
            log.info("Awaiting /publish command")

            with open("logs/activity.log", "a") as f:
                f.write(
                    f"{datetime.now()} | DRAFT READY | "
                    f"{out['slug']} | {out['title']}\n"
                )
        else:
            log.error(f"Pipeline error: {pipeline.stderr}")

    except Exception as e:
        log.error(f"Scheduler error: {e}", exc_info=True)


def monthly_refresh() -> None:
    log.info("MONTHLY KEYWORD REFRESH")
    config = load_config()
    topic = config["blog_identity"]["topic"]
    kw_file = Path(f"keywords/{topic.replace(' ', '_')}_keywords.json")

    if kw_file.exists():
        archive = Path(
            f"keywords/archive/"
            f"{topic.replace(' ', '_')}_{datetime.now().strftime('%Y%m')}.json"
        )
        archive.parent.mkdir(exist_ok=True)
        kw_file.rename(archive)
        log.info(f"Archived keywords to {archive}")

    subprocess.run(
        [sys.executable, "scripts/keyword_research.py", "--topic", topic, "--force"],
        timeout=300,
    )
    log.info("Monthly refresh complete")


if __name__ == "__main__":
    try:
        from apscheduler.schedulers.blocking import BlockingScheduler
        from apscheduler.triggers.cron import CronTrigger
    except ImportError:
        log.error("apscheduler not installed. Run: pip install apscheduler")
        sys.exit(1)

    config = load_config()
    schedule_hour = config["publishing"].get("schedule_hour", 8)

    scheduler = BlockingScheduler()

    scheduler.add_job(
        daily_post_job,
        CronTrigger(hour=schedule_hour, minute=0),
        id="daily_post",
        name="Daily Blog Post",
    )
    scheduler.add_job(
        monthly_refresh,
        CronTrigger(day=1, hour=max(0, schedule_hour - 1), minute=0),
        id="monthly_refresh",
        name="Monthly Keyword Refresh",
    )

    log.info(f"Scheduler running. Daily posts at {schedule_hour:02d}:00.")
    log.info("Press Ctrl+C to stop.")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        log.info("Scheduler stopped.")
