#!/usr/bin/env python3
"""
Scheduler — Cria 3 rascunhos por dia: 08:00, 12:00, 16:00.
Auto-publica caso o usuário não publique manualmente: 09:00, 13:00, 17:00.
Uso: python scripts/scheduler.py
     python scripts/scheduler.py &  (background)
"""

import json
import logging
import shutil
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


def _activity(line: str) -> None:
    with open("logs/activity.log", "a", encoding="utf-8") as f:
        f.write(f"{datetime.now()} | {line}\n")


# ─────────────────────────────────────────────────────────────
# DRAFT CREATION  (08:00 / 12:00 / 16:00)
# ─────────────────────────────────────────────────────────────

def daily_post_job(slot: int = 1) -> None:
    """Cria um rascunho. slot=1/2/3 para os três horários diários."""
    log.info("=" * 50)
    log.info(f"DRAFT JOB — slot {slot}/3")
    config = load_config()
    topic = config["blog_identity"]["topic"]
    today = datetime.now().strftime("%Y-%m-%d")

    try:
        kw_file = Path(f"keywords/{topic.replace(' ', '_')}_keywords.json")
        needs_refresh = True

        if kw_file.exists():
            data = json.loads(kw_file.read_text())
            expires = datetime.fromisoformat(data["expires_at"])
            if datetime.now() < expires:
                needs_refresh = False
                log.info(f"Keywords válidas até {expires.date()}")

        if needs_refresh:
            log.info("Rodando keyword research (PyTrends)...")
            r = subprocess.run(
                [sys.executable, "scripts/keyword_research.py", "--topic", topic],
                capture_output=True, text=True, timeout=300,
            )
            if r.returncode != 0:
                log.error(f"Research falhou: {r.stderr}")
                return

        r = subprocess.run(
            [sys.executable, "scripts/keyword_selector.py", "--topic", topic],
            capture_output=True, text=True, timeout=60,
        )

        if r.returncode != 0:
            log.warning("Sem keywords disponíveis — rodando refresh")
            subprocess.run(
                [sys.executable, "scripts/keyword_research.py", "--topic", topic, "--force"],
                timeout=300,
            )
            return

        selected = json.loads(r.stdout)
        log.info(f"Keyword: {selected['keyword']}")
        log.info(f"Ângulo: {selected['new_angle']}")

        pipeline = subprocess.run(
            [
                sys.executable, "scripts/run_pipeline.py",
                "--keyword", selected["keyword"],
                "--angle", selected["new_angle"],
            ],
            capture_output=True, text=True, timeout=600,
        )

        if pipeline.returncode == 0:
            out = json.loads(pipeline.stdout)
            log.info(f"Rascunho criado: {out['draft_path']}")
            log.info(f"Título: {out['title']}")
            _activity(f"DRAFT READY (slot {slot}) | {out['slug']} | {out['title']}")
        else:
            log.error(f"Pipeline error: {pipeline.stderr}")

    except Exception as e:
        log.error(f"Erro no scheduler: {e}", exc_info=True)


# ─────────────────────────────────────────────────────────────
# AUTO-PUBLISH  (09:00 / 13:00 / 17:00)
# ─────────────────────────────────────────────────────────────

def auto_publish_drafts(slot: int = 1) -> None:
    """
    Publica automaticamente os rascunhos do dia que ainda não foram publicados.
    Chamado 1 hora após cada job de criação (09:00, 13:00, 17:00).
    Só publica se config.json → publishing.auto_publish = true.
    """
    config = load_config()
    if not config.get("publishing", {}).get("auto_publish", False):
        log.info(f"Auto-publish desativado (slot {slot}) — aguardando revisão manual.")
        return

    log.info("=" * 50)
    log.info(f"AUTO-PUBLISH — slot {slot}/3")
    today = datetime.now().strftime("%Y-%m-%d")

    draft_dir = Path(f"articles/draft/{today}")
    ready_dir = Path(f"articles/ready/{today}")
    pub_dir   = Path(f"articles/published/{today}")

    if not draft_dir.exists():
        log.info("Nenhum rascunho encontrado para hoje.")
        return

    # Slugs já publicados hoje
    published_slugs: set[str] = set()
    if pub_dir.exists():
        for f in pub_dir.glob("*_log.json"):
            published_slugs.add(f.stem.replace("_log", ""))

    # Também verifica blog/posts/ para evitar duplicatas
    for f in Path("blog/posts").iterdir() if Path("blog/posts").exists() else []:
        if f.is_dir():
            published_slugs.add(f.name)

    # Encontra os .md de draft pendentes
    drafts = sorted(draft_dir.glob("*.md"))
    if not drafts:
        log.info("Nenhum .md no draft de hoje.")
        return

    published_count = 0
    for md_path in drafts:
        # Extrai slug do nome do arquivo: slug_YYYY-MM-DD.md
        slug = md_path.stem.split("_")[0] if "_" in md_path.stem else md_path.stem

        if slug in published_slugs:
            log.info(f"Já publicado — pulando: {slug}")
            continue

        meta_path = md_path.parent / (md_path.stem + "_meta.json")
        if not meta_path.exists():
            log.warning(f"Meta não encontrado para {slug} — pulando.")
            continue

        # Copia para ready/
        ready_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(md_path, ready_dir / md_path.name)
        shutil.copy2(meta_path, ready_dir / meta_path.name)
        log.info(f"Copiado para ready: {slug}")

        # Publica
        result = subprocess.run(
            [sys.executable, "scripts/publisher.py", "--slug", slug],
            capture_output=True, text=True, timeout=120,
        )

        if result.returncode == 0:
            log.info(f"Publicado com sucesso: {slug}")
            _activity(f"AUTO-PUBLISHED (slot {slot}) | {slug}")
            published_count += 1
            published_slugs.add(slug)
        else:
            log.error(f"Falha ao publicar {slug}: {result.stderr}")
            _activity(f"AUTO-PUBLISH FAILED | {slug} | {result.stderr[:200]}")

    if published_count == 0:
        log.info("Nenhum rascunho novo para publicar neste slot.")
    else:
        log.info(f"{published_count} artigo(s) publicado(s) automaticamente.")


# ─────────────────────────────────────────────────────────────
# MONTHLY REFRESH
# ─────────────────────────────────────────────────────────────

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
        log.info(f"Keywords arquivadas em {archive}")

    subprocess.run(
        [sys.executable, "scripts/keyword_research.py", "--topic", topic, "--force"],
        timeout=300,
    )
    log.info("Refresh mensal concluído.")


# ─────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    try:
        from apscheduler.schedulers.blocking import BlockingScheduler
        from apscheduler.triggers.cron import CronTrigger
    except ImportError:
        log.error("apscheduler não instalado. Execute: pip install apscheduler")
        sys.exit(1)

    config = load_config()
    schedule_hour = config["publishing"].get("schedule_hour", 8)

    scheduler = BlockingScheduler()

    # ── Criação de rascunhos ──────────────────────────────────
    scheduler.add_job(
        lambda: daily_post_job(slot=1),
        CronTrigger(hour=8, minute=0),
        id="draft_1", name="Draft Slot 1 (08:00)",
    )
    scheduler.add_job(
        lambda: daily_post_job(slot=2),
        CronTrigger(hour=12, minute=0),
        id="draft_2", name="Draft Slot 2 (12:00)",
    )
    scheduler.add_job(
        lambda: daily_post_job(slot=3),
        CronTrigger(hour=16, minute=0),
        id="draft_3", name="Draft Slot 3 (16:00)",
    )

    # ── Auto-publicação (1h após cada criação) ─────────────────
    scheduler.add_job(
        lambda: auto_publish_drafts(slot=1),
        CronTrigger(hour=9, minute=0),
        id="autopub_1", name="Auto-Publish Slot 1 (09:00)",
    )
    scheduler.add_job(
        lambda: auto_publish_drafts(slot=2),
        CronTrigger(hour=13, minute=0),
        id="autopub_2", name="Auto-Publish Slot 2 (13:00)",
    )
    scheduler.add_job(
        lambda: auto_publish_drafts(slot=3),
        CronTrigger(hour=17, minute=0),
        id="autopub_3", name="Auto-Publish Slot 3 (17:00)",
    )

    # ── Refresh mensal ────────────────────────────────────────
    scheduler.add_job(
        monthly_refresh,
        CronTrigger(day=1, hour=7, minute=0),
        id="monthly_refresh", name="Monthly Keyword Refresh (01 07:00)",
    )

    log.info("Scheduler iniciado.")
    log.info("  Rascunhos:    08:00 | 12:00 | 16:00")
    log.info("  Auto-publish: 09:00 | 13:00 | 17:00  (se auto_publish=true)")
    log.info("  Pressione Ctrl+C para parar.")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        log.info("Scheduler parado.")
