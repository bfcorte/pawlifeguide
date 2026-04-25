#!/usr/bin/env python3
"""
show_pending.py — Lista artigos pendentes de reescrita pelo Claude Code.
Uso: python scripts/show_pending.py
"""
import json
from datetime import datetime
from pathlib import Path

today = datetime.now().strftime("%Y-%m-%d")
draft_dir = Path(f"articles/draft/{today}")

if not draft_dir.exists():
    print(f"Nenhum draft encontrado para hoje ({today})")
    exit(0)

drafts = sorted(draft_dir.glob("*_meta.json"))
if not drafts:
    print("Nenhum draft pendente.")
    exit(0)

published_slugs = {p.name for p in Path("blog/posts").iterdir() if p.is_dir()}

pending = []
for meta_path in drafts:
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    slug = meta.get("slug", "")
    if slug not in published_slugs:
        pending.append(meta)

if not pending:
    print("Todos os artigos de hoje ja foram publicados.")
    exit(0)

print(f"\nARTIGOS PENDENTES — {today}")
print("=" * 60)
for m in pending:
    print(f"\nSlug   : {m.get('slug')}")
    print(f"Keyword: {m.get('primary_keyword')}")
    print(f"Angulo : {m.get('angle')}")
    print(f"Titulo : {m.get('title')}")
    print("-" * 60)

print(f"\nTotal: {len(pending)} artigo(s) esperando reescrita pelo Claude Code.")
print("Abra o Claude Code e diga: 'escreve os artigos de hoje'")
