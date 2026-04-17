# PawLife Guide

> The best tips and products for your pet

**URL:** https://bfcorte.github.io/pawlifeguide  
**Niche:** Pets  
**Amazon Tag:** pawguidebf-20

---

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run full pipeline for a new article
python scripts/run_pipeline.py --keyword "best dog food for apartments" --angle listicle

# Start daily scheduler (runs at 08:00 AM)
python scripts/scheduler.py &
```

## Commands (via Claude)

| Command | Description |
|---|---|
| `/blog [topic]` | Full pipeline: research → article → products |
| `/publish [slug]` | Publish article + git push |
| `/ads [code]` | Install Google AdSense |
| `/ads status` | Show ad slots status |
| `/status` | Pipeline dashboard |
| `/refresh-keywords` | Force new PyTrends search |

## Structure

```
blog-pets/
├── config.json          ← Blog identity and API keys
├── scripts/             ← Python automation
├── keywords/            ← Keyword research cache
├── articles/            ← Draft → Ready → Published
├── blog/                ← Static HTML site (GitHub Pages)
├── templates/           ← HTML templates
└── logs/                ← Activity and scheduler logs
```

## Setup GitHub Pages

1. Go to github.com/bfcorte/pawlifeguide
2. Settings → Pages
3. Source: Deploy from branch → main → / (root)
4. Save — site live in ~2 minutes
