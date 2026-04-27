#!/usr/bin/env python3
"""
rewrite_all.py — Reescreve todos os 26 artigos com a nova filosofia editorial.
Conteúdo em primeiro lugar. Produto como consequência natural do artigo.
Usage: python scripts/rewrite_all.py
"""
import sys, os, re, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pathlib import Path
from datetime import datetime
from article_writer import write_with_claude, detect_category, load_config
from rewrite_article import rewrite_post_body

# Mapeamento completo: slug → (keyword, angle)
SLUG_MAP = {
    "best-air-purifier-for-pet-dander-2025": ("best air purifier for pet dander",      "listicle"),
    "best-aquarium-plants-for-beginners":     ("best aquarium plants for beginners",    "listicle"),
    "best-automatic-cat-feeders":             ("best automatic cat feeders",            "listicle"),
    "best-cat-food-indoor-cats":              ("best cat food for indoor cats",         "listicle"),
    "best-cat-litter-for-apartments":         ("best cat litter for apartments",        "listicle"),
    "best-dog-crates-for-home":               ("best dog crates for home",              "listicle"),
    "best-dog-food-brands-2026":              ("best dog food brands",                  "listicle"),
    "best-dog-food-for-large-breeds":         ("best dog food for large breeds",        "listicle"),
    "best-dog-food-for-small-breeds":         ("best dog food for small breeds",        "listicle"),
    "best-dog-toys-for-aggressive-chewers":   ("best dog toys for aggressive chewers",  "listicle"),
    "best-dog-treats-for-training":           ("best dog treats for training",          "listicle"),
    "best-interactive-cat-toys":              ("best interactive cat toys",             "listicle"),
    "best-invisible-fence-for-dogs":          ("best invisible fence for dogs",         "listicle"),
    "best-no-pull-dog-harness":               ("best no pull dog harness",              "listicle"),
    "best-pet-insurance-2026":                ("best pet insurance",                    "listicle"),
    "best-pets-for-apartments":               ("best pets for apartments",              "listicle"),
    "best-wet-cat-food-brands":               ("best wet cat food brands",              "listicle"),
    "cat-scratching-post-review":             ("cat scratching post",                   "listicle"),
    "how-to-care-for-a-cockatiel":            ("how to care for a cockatiel",           "how-to"),
    "how-to-care-for-a-guinea-pig":           ("how to care for a guinea pig",          "how-to"),
    "how-to-cycle-a-fish-tank":               ("how to cycle a fish tank",              "how-to"),
    "how-to-introduce-a-new-cat":             ("how to introduce a new cat",            "how-to"),
    "how-to-keep-fish-tank-clean":            ("how to keep fish tank clean",           "how-to"),
    "how-to-stop-dog-barking":                ("how to stop dog barking",               "how-to"),
    "how-to-train-a-cat":                     ("how to train a cat",                    "how-to"),
    "how-to-train-a-dog-to-sit":              ("how to train a dog to sit",             "how-to"),
}


def main():
    config = load_config()
    total = len(SLUG_MAP)
    results = {"ok": [], "fail": []}

    draft_dir = Path(f"articles/drafts/rewrite_{datetime.now().strftime('%Y-%m-%d')}")
    draft_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"Reescrevendo {total} artigos — filosofia: conteúdo primeiro")
    print(f"{'='*60}\n")

    for i, (slug, (keyword, angle)) in enumerate(SLUG_MAP.items(), 1):
        category = detect_category(keyword)

        # Pula artigos já reescritos nesta sessão
        draft_file = draft_dir / f"{slug}.md"
        if draft_file.exists():
            print(f"[{i:02d}/{total}] {slug} — JA FEITO, pulando")
            results["ok"].append(slug)
            continue

        print(f"[{i:02d}/{total}] {slug}")
        print(f"       keyword: '{keyword}' | angle: {angle}")

        # Gera novo conteúdo via Claude CLI
        try:
            new_md = write_with_claude(keyword, angle, category, config)
        except Exception as e:
            print(f"       ERRO Claude: {e}")
            results["fail"].append(slug)
            continue

        if not new_md:
            print(f"       FAIL Claude nao retornou conteudo")
            results["fail"].append(slug)
            continue

        words = len(new_md.split())
        print(f"       Claude: {words} palavras")

        # Salva markdown de referência
        (draft_dir / f"{slug}.md").write_text(new_md, encoding="utf-8")

        # Reescreve o HTML preservando product cards existentes
        try:
            ok = rewrite_post_body(slug, new_md)
            if ok:
                print(f"       OK Reescrito")
                results["ok"].append(slug)
            else:
                print(f"       FAIL Falha ao reescrever HTML")
                results["fail"].append(slug)
        except Exception as e:
            print(f"       ERRO HTML: {e}")
            results["fail"].append(slug)

        print()

    # Relatório
    print(f"\n{'='*60}")
    print(f"CONCLUÍDO: {len(results['ok'])}/{total} reescritos")
    if results["fail"]:
        print(f"Falhas: {results['fail']}")

    # Git commit + push
    if results["ok"]:
        print("\nFazendo git commit + push...")
        try:
            subprocess.run(["git", "add", "blog/posts/", str(draft_dir)], check=True)
            msg = f"Rewrite: conteudo-primeiro — {len(results['ok'])} artigos com nova filosofia editorial"
            subprocess.run(["git", "commit", "-m", msg], check=True)
            subprocess.run(["git", "push"], check=True)
            print("Push concluído.")
        except subprocess.CalledProcessError as e:
            print(f"Git push falhou: {e}")

    return results


if __name__ == "__main__":
    main()
