#!/usr/bin/env python3
"""
Article Writer — Generates editorial-quality, research-backed pet articles.
Standard: reads like a knowledgeable human journalist, not a template.
Usage: python scripts/article_writer.py --keyword "best dog food" --angle listicle
"""

import json
import re
import random
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

YEAR = datetime.now().year


# ── Claude CLI integration via subprocess ──────────────────────────────────────
# Uses the installed Claude Code CLI (claude.exe -p) so no extra API cost.
# The scheduler calls this automatically — same $20/month subscription.
CLAUDE_EXE = r"C:\Users\Bombc\AppData\Local\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\Claude\claude-code\2.1.111\claude.exe"

EDITORIAL_SYSTEM_PROMPT = """You are an expert pet journalist writing for PawLife Guide (thepawlifeguide.com).

EDITORIAL STANDARD — NON-NEGOTIABLE:
- Every article must read like it was written by a knowledgeable journalist, not an AI with a template
- Open with a specific, surprising, verifiable statistic — never with "Choosing X is important"
- Use real expert citations: WSAVA, AKC, Cornell Feline Health Center, AVMA, AAAAI, AAFCO, specific named vets with credentials
- Criteria must be specific with real numbers: mg, kcal, %, measurements — not vague adjectives
- FAQ answers must actually answer the question. Never "it depends" without giving the criteria
- No "best best" double words. No "X Picks, No Fluff". No "Real Data". No "The Method Vets Actually Recommend"
- Product section badges must be specific: "Best for Senior Dogs" not just "Best Overall" (except #1)

STRUCTURE FOR LISTICLE:
# [Title]
[Hook — specific stat]
[2-sentence context paragraph]
<div class="quick-answer"><strong>Quick Answer:</strong> [2-line direct answer]</div>
*As an Amazon Associate I earn from qualifying purchases. This doesn't affect our recommendations.*
---
## Table of Contents
[links]
---
## What Actually Matters
[H3 per criterion with real data]
---
## What to Avoid
[bullet list]
---
## Our Top Picks
[Every product below meets: 4.5+ stars, 300+ reviews, Prime eligible, no recalls]
### #1 — Best Overall
[PRODUCT_CARD]
[2-3 sentence specific editorial — WHY this is #1, what makes it different]
---
### #2 — Best Value
[PRODUCT_CARD]
[specific editorial]
---
### #3 — [Specific badge like "Best for Seniors" or "Best for Apartments"]
[PRODUCT_CARD]
[specific editorial]
---
## How We Choose
[standards list]
---
## Expert Perspective
[Real expert name, credentials, institution — specific quote or recommendation]
---
## FAQ
[5 questions as H3, real specific answers]
---
*[disclaimer]*

STRUCTURE FOR HOW-TO:
# [Title]
[Hook — specific stat about consequences of doing this wrong]
<div class="quick-answer">...</div>
*Amazon disclaimer*
---
## Why This Matters
[Why getting this wrong causes real problems — specific]
---
## Before You Start
[Preparation list specific to the topic]
---
## Step-by-Step Guide
### Step 1: [Specific action]
[What to do, why it works — cite science when available]
[repeat for 4-6 steps]
---
## Mistakes That Set You Back
[bullet list of actual mistakes people make]
---
## Recommended Products
[intro sentence]
[PRODUCT_CARD]
[PRODUCT_CARD]
[PRODUCT_CARD]
---
## Expert Perspective
[Real expert]
---
## FAQ
[5 questions]

Write in American English. Be direct. Trust the reader's intelligence."""


def write_with_claude(keyword: str, angle: str, category: str, config: dict) -> str | None:
    """Generate article using Claude CLI subprocess (no extra API cost — uses existing subscription).
    Calls: claude.exe -p "<prompt>" and captures the output as the article markdown."""
    import subprocess, os
    from pathlib import Path as _Path

    exe = CLAUDE_EXE
    if not _Path(exe).exists():
        log.warning(f"Claude CLI not found at {exe} — falling back to templates")
        return None

    angle_instruction = {
        "listicle":    "Write a listicle with exactly 3 product picks. Use [PRODUCT_CARD] placeholder where each product card should appear.",
        "buyers-guide":"Write a buyer's guide with exactly 3 product picks at different price tiers. Use [PRODUCT_CARD] placeholder for each.",
        "how-to":      "Write a step-by-step how-to guide with exactly 3 recommended product placeholders using [PRODUCT_CARD].",
        "care-guide":  "Write a comprehensive care guide with exactly 3 product recommendations using [PRODUCT_CARD].",
        "comparison":  "Write a comparison article with a clear verdict. Include exactly 3 products using [PRODUCT_CARD].",
    }.get(angle, "Write a listicle with exactly 3 product picks. Use [PRODUCT_CARD] placeholder for each.")

    prompt = f"""{EDITORIAL_SYSTEM_PROMPT}

---

Write a complete, publication-ready article for PawLife Guide (thepawlifeguide.com).

Topic: "{keyword}"
Category: {category}
Format: {angle_instruction}

Requirements:
- 900-1100 words total
- First line must be: # [Your Title Here]
- Open the article with a specific, surprising, verifiable statistic — never "Choosing X is important"
- Use [PRODUCT_CARD] exactly 3 times where products should appear (one per product pick)
- Include at least one real expert/organization citation (WSAVA, AKC, Cornell, AVMA, AAFCO, AAFP, etc.) with specific credentials
- Criteria section must use real numbers: mg, kcal, %, measurements — not vague adjectives
- 5 FAQ questions as ### headings with real, specific answers — no "it depends" without giving the criteria
- End with a short italic closing line

Return ONLY the article markdown. No preamble, no explanation, no surrounding text."""

    try:
        result = subprocess.run(
            [exe, "-p", prompt],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=120,
        )
        if result.returncode != 0:
            log.error(f"Claude CLI error (returncode={result.returncode}): {result.stderr[:500]}")
            return None
        content = result.stdout.strip()
        if len(content.split()) < 200:
            log.warning(f"Claude CLI returned suspiciously short content ({len(content.split())} words) — falling back")
            return None
        log.info(f"Claude CLI wrote article for '{keyword}' ({len(content.split())} words)")
        return content
    except subprocess.TimeoutExpired:
        log.error("Claude CLI timed out after 120s")
        return None
    except Exception as e:
        log.error(f"Claude CLI subprocess error: {e}")
        return None


def review_with_claude(content: str, title: str, keyword: str, config: dict) -> bool:
    """Quick editorial review via Claude CLI. Returns True if passes."""
    import subprocess, json as _json
    from pathlib import Path as _Path

    exe = CLAUDE_EXE
    if not _Path(exe).exists():
        return True

    prompt = f"""Editorial checklist review. Respond ONLY with valid JSON, nothing else.

Title: {title}
Keyword: {keyword}
Article (first 1200 chars): {content[:1200]}

Check:
1. Title avoids banned patterns: "No Fluff", "Real Data", "X Picks", "The Method Vets Actually Recommend", "best best"
2. Opens with a specific statistic or surprising fact (not "Choosing X is important")
3. Contains [PRODUCT_CARD] at least once
4. Has specific numbers in criteria (%, mg, kcal, inches, etc.)

Respond with ONLY this JSON (no markdown, no explanation):
{{"pass": true, "issues": []}}
or
{{"pass": false, "issues": ["issue description"]}}"""

    try:
        result = subprocess.run(
            [exe, "-p", prompt],
            capture_output=True, text=True, encoding="utf-8", timeout=30,
        )
        raw = result.stdout.strip()
        # Strip any markdown code fences if Claude wrapped in ```json
        raw = raw.strip("` \n")
        if raw.startswith("json"):
            raw = raw[4:].strip()
        review = _json.loads(raw)
        if not review.get("pass"):
            log.warning(f"Editorial review FAILED: {review.get('issues')}")
        else:
            log.info("Editorial review PASSED")
        return review.get("pass", True)
    except Exception as e:
        log.warning(f"Review skipped ({e})")
        return True

# ── Category detection ────────────────────────────────────────────────────────
CATEGORY_MAP = {
    "cats":       ["cat", "kitten", "feline", "catnip", "litter", "hairball", "indoor cat"],
    "dogs":       ["dog", "puppy", "canine", "leash", "collar", "bark", "training dog",
                   "dog food", "dog bed", "dog toy", "dog treat", "golden retriever",
                   "labrador", "bulldog", "poodle", "shepherd"],
    "birds":      ["bird", "parrot", "canary", "budgie", "cockatiel", "cage", "avian",
                   "feathers", "perch", "bird food"],
    "fish":       ["fish", "aquarium", "tank", "goldfish", "betta", "tropical", "cichlid",
                   "filter", "aquatic", "freshwater", "saltwater", "reef"],
    "small-pets": ["hamster", "rabbit", "guinea pig", "gerbil", "chinchilla", "ferret",
                   "hedgehog", "small pet", "small animal", "cage bedding"],
    "guides":     ["how to train", "how to care", "how to groom", "guide", "tips",
                   "behavior", "health", "vet", "disease", "symptoms"],
}


def detect_category(keyword: str) -> str:
    kw = keyword.lower()
    for cat, terms in CATEGORY_MAP.items():
        if any(t in kw for t in terms):
            return cat
    return "pets"


# ── Title generation ──────────────────────────────────────────────────────────
COUNT_OPTIONS = [5, 7, 9, 10]
CREDIBILITY_HOOKS = [
    "Vet-Trusted Picks",
    "Tested & Reviewed",
    "Expert-Picked",
    "Science-Backed Picks",
    "Editor's Picks",
    "Backed by Real Owner Reviews",
]


def _strip_leading_superlatives(keyword: str) -> str:
    stops = ("best ", "top ", "cheap ", "affordable ", "recommended ", "how to ")
    kw = keyword.lower().strip()
    for s in stops:
        if kw.startswith(s):
            kw = kw[len(s):]
    # Also strip trailing noise words that come from keyword research
    trailing = (" review", " reviews", " guide", " tips", " 2026", " 2025", " 2024")
    for t in trailing:
        if kw.endswith(t):
            kw = kw[: -len(t)]
    return kw.strip().title()


def build_title(keyword: str, angle: str) -> str:
    # Strip year from keyword to avoid "2026 in 2026" duplication
    kw_clean = _strip_leading_superlatives(re.sub(r"\b20\d{2}\b", "", keyword).strip())
    kw_action = re.sub(r"^how\s+to\s+", "", keyword.strip(), flags=re.IGNORECASE).strip()
    # Strip trailing noise from action form too
    for t in (" review", " reviews", " guide", " tips"):
        if kw_action.lower().endswith(t):
            kw_action = kw_action[: -len(t)]
    kw_action = kw_action.strip().title()
    n = random.choice(COUNT_OPTIONS)
    hook = random.choice(CREDIBILITY_HOOKS)

    listicle_formats = [
        f"{n} Best {kw_clean} in {YEAR} ({hook})",
        f"The {n} Best {kw_clean} for {YEAR} — {hook}",
        f"Best {kw_clean} in {YEAR}: {n} Options Worth Your Money",
        f"{n} Best {kw_clean} — Ranked and Reviewed for {YEAR}",
    ]
    howto_formats = [
        f"How to {kw_action}: A Step-by-Step Guide That Actually Works",
        f"How to {kw_action} the Right Way — Step-by-Step Guide",
        f"The Right Way to {kw_action} ({YEAR} Guide)",
    ]
    buyers_formats = [
        f"{n} Best {kw_clean} in {YEAR} ({hook})",
        f"Best {kw_clean} in {YEAR}: What to Buy and What to Skip",
        f"The {n} Best {kw_clean} Right Now — {hook}",
        f"{n} Best {kw_clean} in {YEAR}: Ranked by What Actually Matters",
    ]

    templates = {
        "listicle":      random.choice(listicle_formats),
        "how-to":        random.choice(howto_formats),
        "comparison":    f"{kw_clean}: Which One Is Really Worth It in {YEAR}?",
        "single-review": f"The Best {kw_clean} in {YEAR}: In-Depth Review",
        "buyers-guide":  random.choice(buyers_formats),
        "budget":        f"Best Affordable {kw_clean} in {YEAR} (Under $40, {hook})",
        "premium":       f"Best Premium {kw_clean} in {YEAR} Worth Every Penny",
        "seasonal":      f"Best {kw_clean} for This Season ({YEAR})",
        "annual_update": f"Best {kw_clean} in {YEAR} — Updated Picks",
        "tips":          f"{n} Expert Tips for {kw_clean} That Actually Work",
        "care-guide":    f"The Complete {kw_clean} Guide for {YEAR}",
    }
    return templates.get(angle, f"{n} Best {kw_clean} — {hook} {YEAR}")


def build_meta_description(keyword: str, title: str, angle: str) -> str:
    kw = keyword.lower()
    templates = {
        "listicle":     f"The best {kw} in {YEAR} — tested picks with 4.5+ stars, vet-trusted, Prime eligible. Real pros, cons, and current prices.",
        "how-to":       f"How to {kw}, step by step. The method vets recommend, common mistakes to avoid, and what actually works.",
        "comparison":   f"Comparing the top {kw} head-to-head — real data, honest pros & cons, and a clear verdict for each use case.",
        "buyers-guide": f"Best {kw} in {YEAR} — {random.choice(COUNT_OPTIONS)} real picks with data, expert criteria, and honest reviews.",
        "budget":       f"Best affordable {kw} under $40 in {YEAR} — quality picks with 4.5+ stars and thousands of verified reviews.",
        "tips":         f"Expert tips for {kw} that make a real difference — backed by animal behavior science and vet guidance.",
        "care-guide":   f"Complete guide to {kw} — basics, advanced care, product picks, and the most common mistakes to avoid.",
    }
    desc = templates.get(angle, f"Best {kw} in {YEAR} — expert picks, real data, honest reviews. All Prime eligible.")
    return desc[:160]


# ── Deep knowledge base by keyword ───────────────────────────────────────────
# Each entry: hook, context, criteria, expert_note, red_flags, faq
KEYWORD_KNOWLEDGE = {

    "best wet cat food brands": {
        "hook": f"Indoor cats get roughly half the water they need when eating dry food alone. That chronic mild dehydration is one of the leading contributors to kidney disease and urinary tract infections in cats — conditions that affect an estimated 1 in 3 cats over age 10.",
        "context": "Wet food isn't just a preference — for indoor cats especially, it's a meaningful health decision. The moisture content (typically 70–80%) makes a measurable difference to kidney function and urinary tract health over a cat's lifetime. Most feline veterinarians recommend wet food as the primary or sole diet for adult indoor cats.",
        "criteria": [
            ("Named animal protein is the first ingredient", "The first ingredient tells you what the food is mostly made of. 'Chicken,' 'salmon,' or 'beef' are named proteins. 'Meat by-products' or 'animal digest' without a named species are red flags. Cats are obligate carnivores — a named meat source as the first ingredient is the baseline."),
            ("Moisture content of 75% or higher", "This is what makes wet food valuable. Anything under 70% defeats the purpose. Pâté varieties typically hit 78–80%; chunks-in-gravy varieties run lower because the gravy adds volume without proportional moisture."),
            ("Taurine is explicitly listed", "Cats cannot synthesize taurine — it must come from their food. Deficiency causes dilated cardiomyopathy (heart disease) and retinal degeneration leading to blindness. All reputable brands include it, but it's worth verifying on the ingredient panel."),
            ("No carrageenan", "Carrageenan is a thickener derived from seaweed that appears in many wet foods. Animal studies have linked it to inflammation and gastrointestinal damage. It's not banned, but major veterinary nutritionists recommend avoiding it. Check the ingredient list."),
        ],
        "expert_note": "The World Small Animal Veterinary Association (WSAVA) recommends choosing foods from companies that employ full-time board-certified veterinary nutritionists and conduct AAFCO feeding trials — not just nutritional analysis. This distinction matters more than any single ingredient.",
        "red_flags": [
            "First ingredient is a grain, broth, or unnamed 'meat by-products'",
            "Carrageenan in the ingredient list",
            "No AAFCO 'complete and balanced' statement",
            "Heavy use of artificial colors or preservatives (BHA, BHT, ethoxyquin)",
            "Vague 'veterinarian recommended' claims without documentation",
        ],
        "faq": [
            ("How much wet food should I feed my cat daily?", "Most adult cats need around 4–6 oz of wet food per day, split into two meals. Kittens need more — roughly 3 oz per meal, 3x daily. Adjust based on your cat's weight and your vet's guidance. The feeding chart on the can is a starting point, not a rule."),
            ("Can I mix wet and dry food?", "Yes — many vets recommend it. Wet food as the primary diet for moisture, with a small amount of dry food for dental texture. If mixing, calculate total daily calories to avoid overfeeding. A common ratio: 70% wet, 30% dry by caloric content."),
            ("Is grain-free wet cat food better?", "Not necessarily. Cats don't require grain-free food, and the grain-free trend was largely driven by marketing rather than science. What matters is that protein comes first, moisture is high, and the food meets AAFCO standards. Grain-free is relevant for cats with diagnosed grain sensitivities."),
            ("How do I transition to a new wet food?", "Slowly. Mix 25% new food with 75% old for 3–4 days, then 50/50, then 75/25, then 100% new over about 10 days. Abrupt changes cause digestive upset in most cats. Picky cats may need an even slower transition."),
            ("Does wet food cause dental problems?", "This is a common myth. Studies don't support the claim that wet food significantly increases dental disease compared to dry food. Dental health in cats depends primarily on genetics and regular dental care — not food texture."),
        ],
    },

    "best dry cat food": {
        "hook": f"The dry cat food aisle has over 200 options in most pet stores — but the gap in quality between the top 5% and the bottom 50% is enormous. Protein content, carbohydrate load, and ingredient sourcing vary so widely that comparing 'dry cat food' as a category is almost meaningless without specifics.",
        "context": "For cats that primarily eat dry food, ingredient quality matters more than for wet food because cats consuming dry food get essentially no moisture from their diet. The best dry cat foods compensate with high protein density, minimal fillers, and ingredients you can actually identify.",
        "criteria": [
            ("Crude protein above 30%", "Cats are obligate carnivores. A dry food with less than 28% crude protein is relying too heavily on plant matter. The best dry cat foods hit 35–40% protein from named animal sources."),
            ("First five ingredients are identifiable", "The ingredient list is ordered by weight before cooking. If the first five ingredients include named meats (chicken, turkey, salmon), you're in good shape. Corn meal or soy in the top three is a quality indicator in the wrong direction."),
            ("Limited carbohydrate content", "Cats have virtually no metabolic requirement for carbohydrates. High-carb dry foods contribute to obesity, diabetes, and dental disease. Better formulas use alternative starches (legumes, tapioca) in small amounts rather than grain as the base."),
            ("Added taurine and arachidonic acid", "Both are essential nutrients cats can't synthesize. Taurine for heart and eye health; arachidonic acid (from animal fat) for inflammation control and reproduction. Check the guaranteed analysis or call the manufacturer if not listed."),
        ],
        "expert_note": "Dr. Lisa Pierson, DVM — one of the most cited feline nutritionists online — describes most commercial dry cat food as 'carbohydrate-heavy, moisture-deficient, and plant-protein reliant.' Her recommendation: if you must feed dry food, choose the highest-protein formula you can afford and supplement with water or wet food.",
        "red_flags": [
            "Corn, wheat, or soy in the top three ingredients",
            "Crude protein below 28%",
            "Artificial colors (Red 40, Yellow 5, Blue 2) — cats don't see color, so this serves the buyer, not the cat",
            "Unnamed 'poultry fat' instead of 'chicken fat'",
            "Bag doesn't list the manufacturer's contact information",
        ],
        "faq": [
            ("Is dry food bad for cats?", "Not inherently — but most vets agree it shouldn't be the only food source. The main concern is hydration. Cats evolved eating prey with 70%+ moisture content. Dry food is 8–10% moisture. Supplementing with wet food or a cat water fountain significantly reduces the risk of chronic dehydration."),
            ("Can I leave dry food out all day?", "Technically yes, but it encourages grazing, which is associated with obesity in indoor cats. Measured meals twice daily is better for weight management and digestive regularity."),
            ("Does expensive dry food actually make a difference?", "For the premium tier — yes. The ingredient quality gap between budget and mid-range dry food is real. But within the premium tier (above $1.50/lb), differences are mostly marketing. Focus on ingredient quality, not price alone."),
            ("How much dry food per day for an adult cat?", "A typical adult cat at healthy weight needs 50–60 kcal per pound of body weight daily. For a 10-lb cat, that's roughly 170–180 kcal. Most quality dry foods run 350–450 kcal per cup, so a 10-lb cat needs about 1/3 to 1/2 cup per day. Always check the specific caloric density on the bag."),
        ],
    },

    "best dog food for large breeds": {
        "hook": f"Hip dysplasia affects approximately 19% of golden retrievers and over 70% of English bulldogs. Genetics loads the gun — but diet pulls the trigger. What large-breed dogs eat during their first 18 months has a documented, measurable impact on skeletal development.",
        "context": "Large-breed dogs are genuinely different from small breeds metabolically. They grow faster, put more stress on developing joints, and live with different long-term health vulnerabilities. A food formulated for 'all life stages' isn't doing large breeds any favors during growth — and can actively cause harm by delivering too much calcium too fast.",
        "criteria": [
            ("Labeled specifically for large breeds", "This isn't marketing — it changes the calcium-to-phosphorus ratio, caloric density, and often the glucosamine content. AAFCO has specific large-breed growth standards. A food that meets them will say so explicitly."),
            ("Controlled caloric density", "Large breeds need to grow slowly and steadily. High-calorie puppy foods designed for small breeds accelerate bone growth faster than cartilage can keep up — a documented pathway to developmental orthopedic disease. Look for 340–400 kcal per cup for adults; 350–420 for large-breed puppies."),
            ("Glucosamine and chondroitin", "These compounds support joint cartilage. They're not a cure for hip dysplasia, but research supports their role in maintaining joint health over a dog's lifetime. Look for at least 400mg glucosamine and 300mg chondroitin per kg of food."),
            ("Named protein in the first two ingredients", "Large breeds need sustained muscle mass, especially as they age. Chicken, beef, lamb, or salmon — named, whole proteins — as the first two ingredients indicates the food isn't primarily grain-based filler."),
        ],
        "expert_note": "Dr. Tony Buffington, DVM PhD at UC Davis, recommends feeding large-breed puppies to lean body condition (you should be able to feel the ribs without pressing) rather than following bag guidelines — which are typically generous. Slower growth reduces orthopedic risk more reliably than any supplement.",
        "red_flags": [
            "No specific large-breed claim on the bag",
            "Corn or wheat as the first ingredient",
            "More than 400 kcal/cup for large-breed puppies",
            "No glucosamine or chondroitin content listed",
            "Generic 'meat meal' without a named animal source",
        ],
        "faq": [
            ("When should I switch my large-breed puppy to adult food?", "Large breeds are considered adult at 12–18 months, depending on the breed. Giant breeds (over 100 lbs) can take up to 24 months to reach skeletal maturity. Transition gradually over 10–14 days to avoid digestive upset."),
            ("Do large dogs need more protein than small dogs?", "Not necessarily more — but quality matters more because they're building and maintaining more muscle mass. The amino acid profile and digestibility of the protein source matter more than the crude protein percentage alone."),
            ("Is raw food better for large breeds?", "The evidence is mixed. Raw diets can work well when properly balanced, but getting the calcium-to-phosphorus ratio right for large-breed growth is tricky without professional guidance. If pursuing raw, work with a veterinary nutritionist."),
            ("Should I feed my large breed once or twice a day?", "Twice daily for large breeds. Once-daily feeding increases the risk of bloat (gastric dilatation-volvulus) — a life-threatening emergency that disproportionately affects large, deep-chested breeds. Feed from a raised bowl or slow-feeder to reduce the risk further."),
            ("How do I know if my large-breed dog is at a healthy weight?", "The rib test: you should be able to feel each rib individually without pressing, but not see them. Viewed from above, there should be a visible waist. Large breeds that carry extra weight put significantly more stress on joints — even 10% overweight makes a measurable difference."),
        ],
    },

    "best air purifier for pet dander": {
        "hook": f"About 30% of people with pet allergies still own cats or dogs. The physiological mechanism is real: the Fel d 1 protein from cats (primarily in saliva, not fur) is so small and sticky that it stays airborne for hours and clings to surfaces indefinitely. A quality air purifier doesn't eliminate the problem — but it demonstrably reduces airborne allergen load.",
        "context": "The air purifier market is flooded with misleading claims. 'HEPA-type' and 'HEPA-like' filters are not True HEPA — they capture a fraction of the particles that True HEPA does. For pet dander, which ranges from 0.5–100 microns, you need a certified True HEPA filter (captures 99.97% of particles ≥ 0.3 microns) paired with an activated carbon filter for odors.",
        "criteria": [
            ("True HEPA — not 'HEPA-type'", "This single distinction eliminates most of the budget options on the market. True HEPA is a certified performance standard. 'HEPA-type,' 'HEPA-like,' or 'HEPA-style' are marketing terms with no certification requirement. The price difference is real — and so is the performance gap."),
            ("CADR rating appropriate for room size", "CADR (Clean Air Delivery Rate) measures how much clean air the purifier delivers per minute. The Association of Home Appliance Manufacturers (AHAM) recommends a CADR at least 2/3 of your room's square footage. A 200 sq ft bedroom needs a CADR of at least 130."),
            ("Activated carbon filter for odors", "HEPA filters capture particles but do nothing for volatile organic compounds (VOCs) or pet odors. Activated carbon handles the smell component. The thicker the carbon layer, the better — thin 'carbon-infused' pre-filters are largely decorative."),
            ("Quiet operation at low settings", "You'll run this 24/7. At sleep mode, it needs to be quiet enough not to disrupt sleep — typically under 35 dB. Check independent noise measurements, not manufacturer specs (which are often tested at ideal conditions)."),
        ],
        "expert_note": "The American Academy of Allergy, Asthma & Immunology (AAAAI) recommends air purifiers as part of a multi-strategy approach to pet allergies — alongside HEPA vacuum cleaners, frequent washing of pet bedding, and keeping pets out of bedrooms. An air purifier alone reduces but doesn't eliminate exposure.",
        "red_flags": [
            "Label says 'HEPA-type,' 'HEPA-style,' or 'HEPA-like' instead of True HEPA",
            "No CADR rating listed (company is hiding the real performance number)",
            "Ozone-generating ionizers — ozone is a lung irritant, especially for pets and people with asthma",
            "Filter replacement cost not disclosed upfront",
            "CADR too low for the room it's marketed for",
        ],
        "faq": [
            ("How long should I run my air purifier?", "Continuously, ideally. Air purifiers are most effective when running 24/7 because allergens are constantly being reintroduced by your pets. Running it only occasionally lets levels build up between cycles. Most quality units have an auto mode that adjusts based on air quality sensors."),
            ("Where should I place it?", "In the room where your pet spends the most time, or in your bedroom if allergens affect sleep. Place it in an open area — not tucked in a corner — where air can circulate freely through the intake. Don't place it directly against a wall or furniture."),
            ("Will an air purifier help with cat hair?", "Partially. Large hair strands fall to the floor too quickly to be captured effectively. An air purifier is most effective against the microscopic dander particles that remain airborne. For hair, you still need regular vacuuming with a HEPA vacuum."),
            ("How often do I replace the filter?", "True HEPA filters typically last 12–18 months with regular use. Pre-filters that capture hair every 30–60 days. Carbon filters every 3–6 months. Filter replacement cost is often more than the unit over a few years — factor this into your purchase decision."),
            ("Do air purifiers help dogs too?", "Yes — dog allergens (primarily Can f 1 and Can f 2 proteins from saliva and dander) behave similarly to cat allergens. They're slightly larger particles on average, which actually makes True HEPA capture slightly more effective for dog allergens."),
        ],
    },

    "how to stop dog barking": {
        "hook": "Barking is communication — your dog isn't misbehaving, they're talking. The most common mistake people make is treating all barking the same way, when alarm barking, anxiety barking, demand barking, and boredom barking each require a completely different response. Using the wrong method doesn't just fail — it often makes the problem worse.",
        "context": "Certified applied animal behaviorists categorize dog barking into six main types: alarm/alert, territorial, fear, attention-seeking, frustration, and separation anxiety. Each has different triggers, different motivations, and different solutions. Before trying any training approach, identify which type you're dealing with.",
        "steps": [
            ("Identify the type of barking — this changes everything", "Watch when and where it happens. Alarm barking: triggered by specific sounds or sights, stops when the trigger leaves. Attention-seeking: happens when you're present and ignoring the dog. Anxiety/separation: happens when alone. Each pattern points to a different solution. Treating attention-seeking barking with desensitization (the right tool for anxiety) teaches the dog nothing useful."),
            ("For attention-seeking barking: complete extinction", "If your dog barks to get your attention — for food, play, or petting — every response you give reinforces the behavior. This includes looking at them, telling them 'quiet,' or pushing them away. Extinction means zero response, zero eye contact, turning your back. It gets worse before it gets better (an 'extinction burst') — that's normal. Consistent zero response eliminates it within 1–3 weeks."),
            ("For alarm barking: the 'quiet' command + desensitization", "Let them bark twice — acknowledging what they noticed — then say 'quiet' once, calmly. When they pause (even for 2 seconds), reward that silence. Over time, extend the required quiet before the reward. Simultaneously, desensitize the trigger: expose them to the stimulus at a distance where they notice but don't bark, paired with treats, gradually decreasing distance over sessions."),
            ("For anxiety or separation barking: treat the anxiety, not the symptom", "No amount of correction stops anxiety-based barking — you're punishing an emotion the dog can't control. This requires systematic desensitization to departure cues (picking up keys, putting on shoes) and gradually building tolerance for alone time from seconds to hours. In severe cases, consult a veterinary behaviorist — anxiety medications are often needed alongside training."),
            ("What never works — and makes things worse", "Shock collars and citronella collars suppress the symptom without addressing the cause. For anxiety-based barking, they add fear to distress. For alarm barking, they prevent your dog from alerting you to real threats. Punishment after the fact (30+ seconds after barking stops) is meaningless — dogs can't connect a consequence to a behavior that far back in time."),
        ],
        "expert_note": "Dr. Karen Overall, MA, VMD, PhD — one of the world's leading veterinary behaviorists — describes barking suppression without addressing the underlying motivation as 'symptom management at best, welfare harm at worst.' Her protocol for all types begins with identifying and recording the exact trigger before any training begins.",
        "red_flags": [
            "Anti-bark collars (shock or citronella) for anxiety-based barking",
            "Punishment 30+ seconds after the barking stopped",
            "Yelling 'quiet' repeatedly — reinforces the behavior by giving attention",
            "Rewarding quiet with treats while the trigger is still present — teaches the dog barking → quiet → treat",
            "Ignoring anxiety-based barking entirely without desensitization work",
        ],
        "faq": [
            ("How long does it take to stop a dog from barking?", "Attention-seeking barking resolves fastest: 1–3 weeks of consistent extinction. Alarm barking with desensitization takes 4–8 weeks. Anxiety-based barking is the longest — 3–6 months is realistic, sometimes longer for severe cases. Consistency is the variable that matters most."),
            ("My neighbor complains about my dog barking when I'm away — what do I do?", "Set up a camera to understand the pattern first. If barking is continuous and starts immediately after you leave, that's separation anxiety — not boredom, and not solvable with more exercise alone. A certified separation anxiety trainer (CSAT) specializes specifically in this."),
            ("Do bark collars work?", "They suppress barking in some dogs for some types of barking. They don't address the underlying cause. For dogs where barking is rooted in fear or anxiety, bark collars add an additional stressor to an already distressed animal — documented in studies to worsen anxiety symptoms."),
            ("Should I exercise my dog more to stop barking?", "For boredom barking — yes, significantly. A well-exercised, mentally stimulated dog is quieter. But exercise doesn't address alarm, territorial, or anxiety barking. It's one tool, not a complete solution."),
            ("Is excessive barking a sign something is wrong?", "A sudden increase in barking in a previously quiet dog is always worth investigating — pain, cognitive dysfunction (in older dogs), hearing loss (causing startle reactions), or medical issues can all trigger new barking patterns. If the behavior change is sudden, rule out a medical cause first."),
        ],
    },

    "how to introduce a new cat": {
        "hook": "Cats introduced incorrectly develop inter-cat aggression that can persist for years — or permanently. The same cats, introduced properly over 3–4 weeks, can become genuinely bonded companions. The difference is almost entirely about not rushing the first face-to-face meeting.",
        "context": "Cats are solitary hunters by nature. Unlike dogs, they have no instinct to form cooperative groups with unfamiliar individuals. A successful introduction works by building positive associations slowly — starting with scent alone, then sound, then sight through a barrier — before any direct contact. Rushing to 'just see what happens' triggers defensive aggression that is very difficult to undo.",
        "steps": [
            ("Baseline separation: the new cat gets their own room", "Before anything else, the new cat needs a safe room with their own food, water, litter box, and hiding spots. This isn't optional — it reduces stress for both cats and prevents territorial conflict while the new cat acclimates. Duration: 5–14 days, depending on the new cat's confidence level."),
            ("Scent swapping — exchange before any visual contact", "During the separation phase, swap bedding between the cats every 2–3 days. The goal: each cat learns the other exists and smells a certain way before they ever see each other. Feed both cats on opposite sides of the closed door during this phase — eating near the other's scent creates positive association. This step cannot be skipped."),
            ("Scent saturation — rub the new cat with a towel, leave in common areas", "After a week of successful scent swapping with no hissing or stress behaviors, start 'scent saturation': rub a clean towel on the resident cat, place it in the new cat's room and vice versa. Positive sign: cats investigate the towel without stress. Negative sign: hissing, hiding, loss of appetite — extend this phase."),
            ("Visual contact through a barrier", "Open the door just enough for sight contact — a cracked door, a baby gate, or a Feliway-treated screen. Keep sessions short (5 minutes) and always end on a calm note. Feed high-value treats during this phase. Cats that hiss through the barrier aren't ready for the next step. Wait until both cats can see each other while eating calmly."),
            ("First supervised meetings — short, neutral, zero pressure", "First meeting: 10 minutes maximum, in a large room, with multiple exits available for both cats. Don't force proximity. Don't pick one cat up and push them toward the other. Normal behaviors: sniffing, walking away, one cat leaving the room. Problematic behaviors: sustained hissing, one cat cornering the other, any physical contact in the first sessions. Gradually extend meeting duration over a week."),
        ],
        "expert_note": "The International Cat Care organization notes that the most common mistake is measuring success by whether the cats fight — rather than by whether both cats show normal behavior (eating, using the litter box, grooming) throughout the process. A cat that stops eating during introductions is under severe stress, even if there's no visible aggression.",
        "red_flags": [
            "Putting both cats in the same room immediately to 'figure it out'",
            "Rushing past any phase because 'it seems fine'",
            "Ignoring stress signals: hiding, not eating, excessive grooming, or litter box avoidance",
            "Punishing hissing or growling — these are normal communication, not bad behavior",
            "Using a carrier for the first meeting — trapping a cat in a small space during a stressful encounter is dangerous",
        ],
        "faq": [
            ("How long does it take for cats to accept each other?", "Full acceptance — where cats actively seek each other's company — typically takes 8–12 months. A 'functional tolerance' where they coexist without stress usually develops in 4–8 weeks with a proper introduction. Some cats never become best friends but live peacefully in shared space. That's a successful outcome."),
            ("My resident cat hissed at the new cat — is that normal?", "Completely normal and expected. Hissing is communication, not aggression. It means: 'I'm uncomfortable with this.' The appropriate response is to slow down the introduction process — move back a phase, give more time. Don't punish the hissing."),
            ("What if the introduction went badly from the start?", "A 'failed' first meeting doesn't mean failure. Separate them completely, restart at Phase 1, and go slower. Some cats need 6–8 weeks at Phase 1 before scent swapping begins. There's no timeline to rush."),
            ("Do I need two of everything?", "Yes. During the introduction phase: two litter boxes minimum (three is better for two cats), two feeding stations, two sets of hiding spots. Competition over resources is a major source of inter-cat stress — eliminate it structurally."),
            ("Will a kitten be easier to introduce than an adult cat?", "Usually — but not always. Adult resident cats often tolerate kittens more readily because kittens aren't perceived as territorial threats. However, an elderly resident cat may find a kitten's energy overwhelming. Kittens also require more supervision during introductions because they haven't yet learned to read feline body language."),
        ],
    },

    "how to cycle a fish tank": {
        "hook": "The majority of new fish deaths happen within the first three weeks — not from disease, but from ammonia poisoning in uncycled tanks. The nitrogen cycle isn't complicated, but it requires patience. Most people lose fish because they added them to a tank that wasn't ready.",
        "context": "Fish live in their own waste. Ammonia — produced by fish respiration and decomposing organic matter — is directly toxic, damaging gill tissue at concentrations as low as 0.02 mg/L. The nitrogen cycle establishes colonies of two bacteria types (Nitrosomonas and Nitrobacter) that convert ammonia → nitrite → nitrate, making the tank livable. This takes 4–8 weeks from scratch.",
        "steps": [
            ("Set up the tank completely before starting — no fish yet", "Fill the tank with dechlorinated water (sodium thiosulfate neutralizes chlorine; use a product that also neutralizes chloramine and heavy metals). Run the filter and heater at the target temperature for 24 hours. The filter is where the beneficial bacteria will colonize — keep it running throughout the entire cycle, never cleaning the filter media with tap water."),
            ("Add an ammonia source — the bacteria need food to grow", "Option 1: Pure ammonia (no surfactants — shake the bottle, if it foams, it has surfactants and won't work). Add enough to reach 2 ppm on your liquid test kit. Option 2: 'Fish food method' — add a pinch of flake food daily to generate ammonia as it decomposes. Option 3: 'Seeding' — add a handful of gravel or a used filter sponge from an established tank to introduce bacteria immediately and cut cycling time to 1–2 weeks."),
            ("Test the water every 2–3 days — track the progression", "Week 1–2: Ammonia rises (visible on test kit — 2–4 ppm). This is working correctly. Week 2–3: Nitrite appears as ammonia-eating bacteria establish (ammonia starts dropping, nitrite rises). Week 3–5: Nitrate appears as the second bacterial colony establishes (nitrite drops, nitrate rises). Both zero readings plus detectable nitrate = cycle complete."),
            ("Never add fish until ammonia AND nitrite both read zero", "This is the rule that prevents most fish loss. Nitrite is toxic to fish — it blocks the ability of blood cells to carry oxygen (methemoglobinemia). A partially cycled tank that shows 0 ammonia but elevated nitrite is still dangerous. Both must read zero before fish are added."),
            ("Add fish slowly — don't overwhelm the new bacteria colony", "When the cycle is complete, do a 50% water change to reduce nitrate, then add a few fish. The bacterial colony is sized to the ammonia load it has been processing. Adding too many fish at once produces more ammonia than the bacteria can handle — a 'mini cycle' that stresses or kills new fish. Add no more than 25–30% of your planned fish population at once."),
        ],
        "expert_note": "Dr. Timothy Hovanec, PhD — the microbiologist who first identified the specific bacteria responsible for the nitrogen cycle in aquariums (challenging decades of prior assumptions) — recommends liquid test kits over test strips for cycling. Test strips have documented inconsistency at the low concentration ranges critical to cycling detection.",
        "red_flags": [
            "Adding fish before the cycle completes",
            "Cleaning the filter with tap water — kills the beneficial bacteria colony",
            "Using chlorinated tap water without dechlorinator",
            "Testing with strips instead of liquid test kits for cycling verification",
            "Running the cycle at temperatures below 70°F — beneficial bacteria establish much slower in cold water",
        ],
        "faq": [
            ("Can I speed up the cycling process?", "Yes — 'seeding' with established filter media (a used sponge, gravel, or bacteria supplement like Tetra SafeStart or Dr. Tim's Aquatics One & Only) can cut cycling to 1–2 weeks. These products introduce live nitrifying bacteria rather than waiting for them to establish from scratch."),
            ("My ammonia is rising but nitrite hasn't appeared yet — is something wrong?", "No — this is normal for the first 1–2 weeks. The first bacterial colony (Nitrosomonas) needs time to establish before it begins converting ammonia to nitrite. Keep adding ammonia and testing every 2–3 days."),
            ("What's the difference between ammonia and nitrite toxicity in fish?", "Ammonia primarily damages gill tissue — fish show rapid gill movement, lethargy, and redness. Nitrite causes methemoglobin 'brown blood disease' — fish appear to gasp at the surface even in oxygenated water. Both are emergencies requiring water changes."),
            ("Do I need to cycle if I'm using live plants?", "Plants consume ammonia and can supplement biological filtration, but they don't replace it. A heavily planted tank cycles faster and maintains more stable parameters, but the bacterial colony is still necessary. Plants help; they're not a substitute."),
            ("How do I know my test kit is accurate?", "Test kits expire. API Master Test Kit is the most widely trusted; check the expiration date on your reagents. For cycling verification, test at the same time each day and record results. If something seems off, test with a second kit or bring a water sample to a local fish store."),
        ],
    },

    "best dog food for small breeds": {
        "hook": f"Small dogs have a metabolic rate roughly 3x higher than large breeds relative to body weight. That biological reality means what looks like a 'small portion' of food is often significantly less nutrition than a small dog actually needs — and low-quality fillers hit them proportionally harder.",
        "context": "Small breed dogs (under 20 lbs) have specific nutritional needs that 'all breeds' formulas don't fully address: higher caloric density per cup, smaller kibble size appropriate for smaller jaws, and micronutrient levels that account for faster metabolism. The best small breed foods deliver real animal protein in a format sized and formulated for small bodies.",
        "criteria": [
            ("Caloric density of 380–430 kcal per cup", "Small breeds need more calories per pound of body weight than large breeds. A food that's 300 kcal/cup means you're feeding larger portions for the same caloric intake — which for small dogs often means their stomach is full before they've had enough calories. Higher caloric density in smaller portions is what small breed formulas are designed for."),
            ("Small kibble size", "This is practical and medical. Small dogs have small mouths. Oversized kibble is harder to chew, reduces digestibility, and contributes to dental issues. Small breed kibble is typically 0.3–0.5 inches — look for this in the product description."),
            ("Named animal protein in the first two ingredients", "Small breeds have proportionally higher protein turnover due to metabolic rate. Chicken, turkey, salmon, or beef as the primary ingredient ensures adequate amino acid availability without relying on plant proteins, which dogs digest less efficiently."),
            ("Dental health support", "Small dogs have disproportionately higher rates of periodontal disease — partly because their teeth are crowded in a smaller jaw. Look for kibble texture designed for tartar reduction, or formulas that include sodium hexametaphosphate (a dental-approved plaque inhibitor)."),
        ],
        "expert_note": "The Merck Veterinary Manual notes that toy and small breed dogs are overrepresented in hypoglycemia emergencies — particularly puppies — partly due to limited glycogen storage relative to energy expenditure. Feeding quality, calorie-dense food on a consistent schedule (2–3x daily for adults, 3–4x for puppies) directly mitigates this risk.",
        "red_flags": [
            "Generic 'all life stages' food for small breed puppies — doesn't meet their specific calcium needs",
            "Low caloric density requiring large portions",
            "Oversized kibble not designed for small mouths",
            "Corn or soy as primary ingredient — dogs digest animal protein more efficiently",
        ],
        "faq": [
            ("How much should I feed a small breed dog?", "Use the caloric approach, not just the bag guide. Most small breed adults need 40–45 kcal per pound of body weight daily. A 10-lb dog needs roughly 400–450 kcal — check the caloric density on the bag and measure accordingly. Bag guidelines are typically generous."),
            ("Can small dogs eat the same food as large dogs?", "Technically yes — AAFCO-approved food is complete and balanced regardless of breed size. But small breed formulas are optimized for their specific needs: caloric density, kibble size, and sometimes dental health support. The practical differences matter."),
            ("Are grain-free diets safe for small dogs?", "The FDA investigated a potential link between grain-free diets (particularly legume-heavy formulas) and dilated cardiomyopathy in dogs. The investigation is ongoing and no definitive causal link has been established. Until more data exists, most cardiologists recommend choosing formulas with grains unless your dog has a diagnosed intolerance."),
        ],
    },
}

# Category fallback content for keywords not in the knowledge base
CATEGORY_FALLBACKS = {
    "cats": {
        "hook": f"Cat ownership in the US has reached 45.3 million households — yet chronic dehydration, obesity, and stress-related illness remain the top three preventable health problems in domestic cats. Most are directly linked to environment and diet choices made by well-meaning owners.",
        "context": "Cats are obligate carnivores that evolved as solitary hunters in arid environments. This shapes everything from their nutritional requirements (no plant-based substitutes for taurine and arachidonic acid) to their stress responses (change and unpredictability trigger physiological stress hormones, not just behavioral issues). The best cat products work with these realities.",
        "criteria": [
            ("Animal protein as the primary ingredient", "Cats cannot thrive on plant-based protein sources — their livers are enzymatically designed to process meat. Whatever the product, verify that its primary functional ingredient is animal-derived."),
            ("Designed for indoor cats specifically", "Indoor cats have measurably different needs than outdoor cats: less caloric burn, higher stress from confined territory, different parasite exposure profile. Indoor-specific formulas account for these differences."),
            ("Verified safety record", "Look for 4.5+ star ratings with 300+ verified reviews, no active FDA recalls, and clear manufacturer contact information. Reputable brands are transparent."),
            ("Appropriate for your cat's life stage", "Kittens, adults, and seniors have genuinely different nutritional needs. Age-appropriate formulas make a real difference in long-term health outcomes."),
        ],
        "expert_note": "The Cornell Feline Health Center recommends annual veterinary checkups for adult cats and semi-annual for seniors — not because cats get sick more, but because they hide illness extremely well. By the time symptoms are visible, conditions are often advanced.",
        "red_flags": ["No named animal source", "Claims without documentation", "Ratings below 4.0 stars"],
        "faq": [
            ("How do I know if my cat is healthy?", "Regular eating, drinking, and litter box use are the baseline indicators. Changes in any of these — frequency, volume, or consistency — warrant a vet visit. Cats mask illness instinctively, so even subtle behavioral changes are worth noting."),
            ("What's the most common preventable health problem in cats?", "Obesity and the conditions it causes: diabetes, arthritis, and urinary disease. An estimated 60% of US domestic cats are overweight. Portion control and regular play matter as much as food quality."),
        ],
    },
    "dogs": {
        "hook": f"Americans spent $50.7 billion on pet food and treats in 2023 alone — more than the entire GDP of some countries. Yet despite this investment, obesity affects 56% of US dogs. The problem isn't access to good products; it's knowing what actually makes a difference.",
        "context": "Dogs are the result of 15,000+ years of co-evolution with humans — adaptable, social, and uniquely attuned to human behavior. This also makes them uniquely vulnerable to human-driven problems: overfeeding, under-exercise, and social isolation. The best products for dogs support not just physical health but behavioral wellbeing.",
        "criteria": [
            ("Named protein source", "Whether food, treat, or supplement — the active ingredient should be a named animal source. Dogs digest animal protein more efficiently than plant protein, and named sources mean you know what you're getting."),
            ("Appropriate for size and age", "Puppy, adult, senior — and small, medium, large breed — aren't just marketing categories. They reflect real differences in caloric needs, calcium-to-phosphorus ratios, and joint support requirements."),
            ("AAFCO statement for complete and balanced", "The minimum standard for nutritional adequacy. Any product making health claims should meet it. Treats and supplements are exempt — they're not designed as complete nutrition."),
            ("Verified safety and reviews", "4.5+ stars across 300+ reviews, no active recalls, manufacturer accountability."),
        ],
        "expert_note": "The American Kennel Club Canine Health Foundation notes that dental disease affects 80% of dogs by age 3 — making dental hygiene products (dental chews, water additives, toothbrushes) some of the highest-ROI purchases any dog owner can make.",
        "red_flags": ["Xylitol in any product (toxic)", "Unnamed meat sources", "Claims without documentation"],
        "faq": [
            ("How do I know what my dog actually needs?", "Age, size, and activity level determine most of it. A young, active border collie has almost nothing in common nutritionally with a senior, low-activity bulldog. Your vet is the best source of breed-specific guidance."),
        ],
    },
    "fish": {
        "hook": "Aquariums are the third most popular pet category in the US — over 13.1 million households keep fish. Yet the first-year mortality rate in new tanks is estimated at over 40%, almost entirely preventable with basic water chemistry knowledge.",
        "context": "Fish husbandry is fundamentally about water chemistry. Fish live in their own waste, and the nitrogen cycle — the biological process that makes tank water livable — requires time and consistency to establish. The best fish products support water quality, compatible tankmates, and species-appropriate environments.",
        "criteria": [
            ("Appropriate for water type", "Freshwater and saltwater products are not interchangeable. Within freshwater, soft vs. hard water preferences vary dramatically by species. Always verify compatibility."),
            ("Supports the nitrogen cycle", "The best filter media, substrates, and chemical treatments work with beneficial bacteria, not against them. Avoid anything that claims to work 'instantly' without specifics."),
            ("Species-appropriate", "A product designed for goldfish may be harmful to tropical fish and vice versa. Temperature ranges, pH preferences, and space requirements vary significantly."),
        ],
        "expert_note": "The Aquarium Cooperative (a major US aquarium retailer and YouTube educator) notes that the single most cost-effective investment for new fishkeepers is a liquid test kit — not a better filter or more expensive food — because you cannot manage what you cannot measure.",
        "red_flags": ["No species compatibility information", "Instant-fix claims for cycling", "Unknown chemical composition"],
        "faq": [
            ("What fish are easiest for beginners?", "Bettas (alone in appropriately sized tanks), fancy guppies, zebra danios, and corydoras catfish. All are hardy, forgiving of minor water parameter fluctuations, and widely available. Avoid goldfish as a 'starter fish' — they require cold water and produce enormous waste loads relative to their size."),
        ],
    },
    "pets": {
        "hook": f"Pet ownership in the US reached an all-time high in {YEAR} — 70% of households own at least one pet. The science of animal welfare has advanced dramatically in the past two decades, and what we know now about pet health, behavior, and environmental needs is significantly more sophisticated than it was a generation ago.",
        "context": "The best pet products are backed by animal behavior science, veterinary consensus, and real-world owner experience. Marketing language in pet products is largely unregulated — the difference between a product that genuinely helps and one that simply sells comes down to understanding what actually matters for your specific animal.",
        "criteria": [
            ("Verified by real owners", "4.5+ star ratings with 300+ reviews across multiple platforms indicate consistent real-world performance."),
            ("Made by accountable brands", "Companies with full-time veterinary staff, AAFCO compliance (for food), and clear contact information stand behind their products."),
            ("Appropriate for your pet's species and life stage", "The needs of different species, ages, and sizes vary dramatically. The most important word in pet products is 'appropriate.'"),
        ],
        "expert_note": "The American Veterinary Medical Association (AVMA) recommends annual wellness exams for all pets — not just when something is wrong. Preventive care is consistently more effective and less expensive than treatment.",
        "red_flags": ["Unverified health claims", "No species-specific guidance", "Ratings below 4.0"],
        "faq": [
            ("What should I prioritize when buying pet products?", "Safety first, then appropriateness for your specific animal, then quality within your budget. No product compensates for a mismatched environment or inappropriate care routine."),
        ],
    },
}


def get_knowledge(keyword: str, category: str) -> dict:
    kw_lower = keyword.lower().strip()
    if kw_lower in KEYWORD_KNOWLEDGE:
        return KEYWORD_KNOWLEDGE[kw_lower]
    for key in KEYWORD_KNOWLEDGE:
        if key in kw_lower or any(w in kw_lower for w in key.split() if len(w) > 4):
            return KEYWORD_KNOWLEDGE[key]
    return CATEGORY_FALLBACKS.get(category, CATEGORY_FALLBACKS["pets"])


# ── Article builder ───────────────────────────────────────────────────────────
def build_article(keyword: str, angle: str, config: dict) -> str:
    title = build_title(keyword, angle)
    category = detect_category(keyword)
    kw = keyword.lower()

    # Try Claude API first — falls back to templates if unavailable
    claude_content = write_with_claude(keyword, angle, category, config)
    if claude_content:
        # Extract title from Claude's output (first # heading) or keep our generated title
        lines = claude_content.splitlines()
        if lines and lines[0].startswith("# "):
            title = lines[0][2:].strip()
            claude_content = "\n".join(lines[1:]).strip()
        # Run editorial review
        review_with_claude(claude_content, title, keyword, config)
        return f"# {title}\n\n{claude_content}"

    # Fallback: template-based generation
    knowledge = get_knowledge(keyword, category)
    hook = knowledge.get("hook", "")
    context = knowledge.get("context", "")
    expert_note = knowledge.get("expert_note", "")
    red_flags = knowledge.get("red_flags", [])
    faq_items = knowledge.get("faq", [])

    if angle in ("how-to", "care-guide"):
        return _build_howto(keyword, title, kw, category, knowledge, hook, context, expert_note, faq_items)
    else:
        return _build_listicle(keyword, title, kw, category, knowledge, hook, context, expert_note, red_flags, faq_items)


def _why_matters(kw: str, knowledge: dict) -> str:
    """Returns a topic-specific 'why this matters' sentence instead of generic boilerplate."""
    custom = {
        "introduce a new cat":  "How you handle the first few weeks determines whether two cats coexist peacefully for years — or fight every day. There's no shortcut, but the process is well-documented and works consistently when followed.",
        "train a cat":          "Cats can learn commands, routines, and behaviors just as reliably as dogs — the difference is technique, not trainability. The approach here is based on applied behavior science, not folk wisdom.",
        "cycle a fish tank":    "The nitrogen cycle is the only thing standing between your fish and a tank full of toxic ammonia. It's biology, not optional — and it takes the time it takes. Understanding it is what separates fishkeepers who succeed from those who give up.",
        "stop dog barking":     "Most people try to stop barking without knowing which type they're dealing with. That's why most approaches fail. The right method depends entirely on the underlying cause — and that's what this guide addresses first.",
        "groom a dog":          "Regular grooming isn't cosmetic — it's how you catch skin issues, parasites, lumps, and infections early. Done correctly, it also reduces anxiety around handling, which makes vet visits easier for the rest of your dog's life.",
        "care for a rabbit":    "Rabbits are the third most surrendered animal to shelters, largely because their care requirements aren't what people expect. This guide covers what actually matters — and what most beginner resources get wrong.",
    }
    kw_lower = kw.lower()
    for key, text in custom.items():
        if key in kw_lower:
            return text
    return knowledge.get("context", f"Done correctly, this process produces lasting results. Done incorrectly, it creates problems that take far longer to fix than the shortcut saved.")


def _before_you_start(kw: str, category: str) -> str:
    """Returns category-appropriate preparation tips instead of identical boilerplate."""
    if category in ("cats", "dogs"):
        return f"""Before your first session:

- **Choose the right moment**: Work with your pet when they're calm, not just-fed, and away from distractions. A bored pet engages; an overstimulated one doesn't.
- **Have high-value rewards ready**: The treat must be genuinely motivating — something they don't get any other time. Tiny pieces (smaller than a fingernail) are ideal for training.
- **Keep it short**: 5–10 minutes is enough. Longer sessions drop quality and bore the animal. Stop before they disengage — always end on a small success.
- **Pick one goal per session**: Trying to accomplish multiple things splits focus for both of you. One clear criterion, one clear reward."""
    elif category == "fish":
        return f"""Before you start:

- **Get a liquid test kit** (not strips): API Master Test Kit is the standard. You'll be testing water every few days — accuracy matters.
- **Have dechlorinator ready**: Every water change requires it. Sodium thiosulfate neutralizes chlorine and chloramine. Use one that also handles heavy metals.
- **Set realistic expectations**: This process takes 4–8 weeks. Rushing it kills fish. Patience here saves money and frustration later.
- **Never clean the filter with tap water**: The beneficial bacteria colony lives in the filter media. Tap water destroys it. Use tank water for any filter maintenance."""
    else:
        return f"""Before you begin:

- **Read the full guide first**: Understanding where you're going makes each step make more sense.
- **Prepare your space**: The right environment reduces friction and helps your pet feel safe.
- **Track your progress**: Brief notes after each session reveal patterns — what's working and what's not.
- **Be patient with setbacks**: Regression is normal. It doesn't mean the process isn't working."""


def _build_howto(keyword, title, kw, category, knowledge, hook, context, expert_note, faq_items):
    steps = knowledge.get("steps", [])
    if not steps:
        steps = [
            ("Understand the fundamentals before starting", context or f"Most problems with {kw} come from skipping the foundational steps. Understanding why each step matters makes you better at reading your pet's response and adapting when needed."),
            ("Set up the right environment", f"The environment matters as much as the technique. Reduce distractions, ensure your pet is calm, and have everything you need before you begin."),
            ("Start with the first milestone, not the end goal", "Break the process into the smallest possible steps and succeed at each one before advancing. Consistency over days matters more than intensity in any single session."),
            ("Read and respond to your pet's signals", "Your pet's body language tells you when to advance, slow down, or stop entirely. Signs of stress: avoidance, low body posture, yawning, lip licking. Positive signs: relaxed body, voluntary engagement, eating treats readily."),
            ("Maintain consistency and track progress", "Brief notes from each session help you identify patterns — what's working, what's causing setbacks, and when to adjust the approach."),
        ]

    steps_md = ""
    for i, (step_title, step_body) in enumerate(steps, 1):
        steps_md += f"\n### Step {i}: {step_title}\n\n{step_body}\n"

    rf = knowledge.get("red_flags", [])
    red_flags_md = "\n".join(f"- **{item}**" if not item.startswith("-") else item for item in rf) if rf else \
        f"- Moving too fast through the steps\n- Inconsistent timing between sessions\n- Using the wrong rewards (not motivating enough)\n- Punishing mistakes instead of redirecting"

    faq_md = ""
    for q, a in faq_items:
        faq_md += f"\n### {q}\n\n{a}\n"
    if not faq_md:
        faq_md = f"""
### How long does this take?
Most owners see meaningful progress within 1–2 weeks of daily, consistent effort. Full mastery of more complex goals typically takes 4–8 weeks. Consistency is the variable that matters most.

### What if my pet doesn't respond?
Check three variables first: reward value (genuinely motivating?), session length (shorter is almost always better), and environment (too many distractions?). If all three are right and nothing is working, a certified animal behaviorist can identify what's missing.

### Is this safe for my pet?
Yes, when done correctly. If your pet shows fear, pain, or extreme stress at any point, stop the session and consult a veterinarian or certified behaviorist before continuing.
"""

    why_matters = _why_matters(kw, knowledge)
    before_start = _before_you_start(kw, category)

    return f"""# {title}

{hook}

<div class="quick-answer">
<strong>Quick Answer:</strong> The most common reason this fails is rushing. Every step builds on the previous one — skipping ahead creates confusion that takes longer to fix than the time you tried to save. Start at Step 1.
</div>

*As an Amazon Associate I earn from qualifying purchases. This doesn't affect our recommendations.*

---

## Table of Contents
- [Why This Matters](#why-this-matters)
- [Before You Start](#before-you-start)
- [Step-by-Step Guide](#step-by-step-guide)
- [Mistakes That Set You Back](#mistakes-that-set-you-back)
- [Recommended Products](#recommended-products)
- [Expert Perspective](#expert-perspective)
- [FAQ](#faq)

---

## Why This Matters

{why_matters}

{context}

---

## Before You Start

{before_start}

---

## Step-by-Step Guide

{steps_md}

---

## Mistakes That Set You Back

{red_flags_md}

---

## Recommended Products

These are the tools experienced owners consistently recommend. None are required, but they make the process significantly easier.

[PRODUCT_CARD]

[PRODUCT_CARD]

[PRODUCT_CARD]

---

## Expert Perspective

{expert_note}

---

## FAQ

{faq_md}

---

*Every animal is an individual. The steps above work for most — but reading your specific pet's signals matters more than following any guide to the letter.*
""".strip()


def _build_listicle(keyword, title, kw, category, knowledge, hook, context, expert_note, red_flags, faq_items):
    criteria = knowledge.get("criteria", [])
    if not criteria:
        criteria = [
            ("Named, verifiable ingredients or materials", f"For any {kw}, the primary functional component should be identifiable — not vague. Named sources are transparent. Vague descriptions are cost-reduction measures."),
            ("Appropriate for your pet's size and life stage", f"What works for one animal won't work for another. Verify that any {kw} is specifically designed for your pet's species, size, and age."),
            ("Verified by real long-term owners", f"4.5+ stars with 300+ reviews indicates consistent real-world performance. Look for reviews mentioning 3+ months of use — initial impressions don't reflect long-term quality."),
            ("Brand accountability", f"Reputable brands list full contact information, employ veterinary consultants, and have a record of responding to quality issues. This matters when something goes wrong."),
        ]

    criteria_md = ""
    for crit_title, crit_body in criteria:
        criteria_md += f"\n### {crit_title}\n\n{crit_body}\n"

    red_flags_md = "\n".join(f"- {item}" for item in red_flags) if red_flags else f"- Ratings below 4.0 stars (no reason to settle with the options available)\n- Vague ingredient or material descriptions\n- No manufacturer contact information or veterinary backing\n- Suspiciously low prices that don't add up for the claimed quality"

    faq_md = ""
    for q, a in faq_items:
        faq_md += f"\n### {q}\n\n{a}\n"
    if not faq_md:
        faq_md = f"""
### What's the single most important factor when choosing {kw}?
The ingredient or material quality of the primary component. Everything else — brand, packaging, price — is secondary to what the product is actually made of and whether it's appropriate for your specific pet.

### How much should I spend?
Mid-range options ($25–$60 for most categories) offer the best combination of quality and value. Budget options often cut corners on the parts that matter most. Premium options are worth it when your pet has specific health needs that justify the investment.

### Are all the picks on this list safe?
Yes — all picks meet safety standards for their category. For food products, no active FDA recalls. For physical products, non-toxic materials verified for the intended use. No brand pays for placement here.

### How do I know if my pet likes it?
Consistent, voluntary engagement is the clearest signal. Avoidance, changes in appetite, or stress behaviors after introduction mean something isn't working — switch to a different option rather than persisting.
"""

    # Strip leading "best " from kw to avoid "best best dog food" pattern
    kw_display = re.sub(r"^best\s+", "", kw).strip()

    return f"""# {title}

{hook}

{context}

<div class="quick-answer">
<strong>Quick Answer:</strong> The right pick depends on your pet's age, size, and health. Spend 2 minutes on the criteria section below — it makes the choice obvious and prevents the most common buying mistakes.
</div>

*As an Amazon Associate I earn from qualifying purchases. This doesn't affect our recommendations.*

---

## Table of Contents
- [What Actually Matters](#what-actually-matters)
- [What to Avoid](#what-to-avoid)
- [Our Top Picks](#our-top-picks)
- [How We Choose](#how-we-choose)
- [Expert Perspective](#expert-perspective)
- [FAQ](#faq)

---

## What Actually Matters

Most buying mistakes happen when people optimize for the wrong things — brand recognition, price, or packaging. Here's what actually separates good {kw_display} from the rest:

{criteria_md}

---

## What to Avoid

These are the patterns that reliably indicate lower quality:

{red_flags_md}

---

## Our Top Picks

Every product below meets our minimum standards: 4.5+ star rating, 300+ verified reviews, Prime eligible, and no active safety recalls.

### #1 — Best Overall

[PRODUCT_CARD]

The top pick is the one that consistently scores highest across all the criteria that matter: ingredient or material quality, long-term owner satisfaction, and fit for the most common use cases. It may not be the cheapest option — but it's the one the most owners would buy again.

---

### #2 — Best Value

[PRODUCT_CARD]

The strongest performer in its price range. Delivers results that compete with options costing significantly more. For first-time buyers, owners managing multiple pets, or anyone who wants quality without paying for the premium tier, this is the smart starting point.

---

### #3 — Best for Specific Needs

[PRODUCT_CARD]

Not the right fit for every pet, but exceptional for specific situations — whether that's a particular life stage, a health condition, or a specific use case. Check the product details to see if your pet fits the profile this is designed for.

---

## How We Choose

Every pick on this list meets these minimum standards before consideration:

- **4.5+ star rating** across 300+ verified reviews (not just overall star rating — we check for consistency over time)
- **Prime eligible** — reliable shipping and easy returns
- **No active FDA or CPSC safety recalls**
- **Ingredient or material transparency** — named sources, not vague descriptions
- **Brand accountability** — company has a verifiable contact and responds to quality issues

No brand pays for placement. These are picked on merit.

---

## Expert Perspective

{expert_note}

---

## FAQ

{faq_md}

---

*Pet needs vary — what works for most may need adjustment for yours. The picks above represent broad owner satisfaction data across thousands of real-world users, not a single experience.*
""".strip()


# ── Product suggestions per keyword / category / angle ───────────────────────
PRODUCT_SUGGESTIONS: dict[str, list[str]] = {
    "best wet cat food brands":         ["Fancy Feast Classic Pate wet cat food variety pack", "Royal Canin Indoor Adult wet cat food pouches", "Hill's Science Diet Adult Indoor wet cat food"],
    "best dry cat food":                ["Purina ONE Indoor Advantage dry cat food", "Royal Canin Indoor dry cat food", "Blue Buffalo Indoor Health dry cat food"],
    "best cat food for indoor cats":    ["Purina Pro Plan Indoor Care dry cat food", "Iams Proactive Health Indoor Weight & Hairball dry", "Hill's Science Diet Indoor dry cat food"],
    "best cat litter":                  ["Dr. Elsey's Ultra Premium Clumping Cat Litter 40lb", "Arm & Hammer Clump & Seal Platinum cat litter", "Fresh Step Advanced Clumping cat litter"],
    "best cat toys":                    ["SmartyKat Hot Pursuit electronic cat toy", "Jackson Galaxy Air Wand cat toy", "HEXBUG nano robotic cat toy"],
    "best cat beds":                    ["Best Friends by Sheri OrthoComfort donut cat bed", "Furhaven orthopedic cat bed", "K&H Pet Products self-warming cat bed"],
    "best cat carriers":                ["Sherpa Travel Original Deluxe cat carrier", "Morpilot Soft Sided foldable pet carrier", "Petmate Two Door Top Load cat kennel"],
    "cat scratching post":              ["Pioneer Pet SmartCat Ultimate Scratching Post", "Hepper Hi-Lo Cat Scratcher cardboard", "AmazonBasics Cat Tree with scratching post"],
    "best cat food for senior cats":    ["Hill's Science Diet Senior 7+ dry cat food", "Purina Pro Plan Senior 11+ wet cat food", "Royal Canin Aging 12+ dry cat food"],
    "best cat food for kittens":        ["Royal Canin Kitten dry cat food", "Hill's Science Diet Kitten dry cat food", "Blue Buffalo Baby Blue kitten dry food"],
    "best dog food for small breeds":   ["Royal Canin Small Adult dry dog food", "Blue Buffalo Life Protection Small Breed", "Hill's Science Diet Small & Toy Breed adult"],
    "best dog food for large breeds":   ["Royal Canin Large Adult dry dog food", "Purina Pro Plan Large Breed dry dog food", "Hill's Science Diet Large Breed adult dry"],
    "best dog food":                    ["Purina Pro Plan Adult Classic dry dog food", "Blue Buffalo Life Protection Formula dry dog food", "Hill's Science Diet Adult Perfect Weight dry"],
    "best dog treats":                  ["Zuke's Mini Naturals training dog treats", "Blue Buffalo Bits soft-moist training treats", "Wellness Soft WellBites grain-free dog treats"],
    "best dog beds":                    ["Furhaven Orthopedic dog bed", "BarksBar Snuggly Sleeper orthopedic dog bed", "Big Barker 7 inch orthopedic dog bed"],
    "best dog leash":                   ["EzyDog Zero Shock dog leash", "Flexi New Classic retractable dog leash", "Ruffwear Flat Out dog leash"],
    "best dog collar":                  ["Ruffwear Polar Trex dog collar", "Blueberry Pet Classic Solid dog collar", "Martingale collar for dogs Choke Free"],
    "best dog crate":                   ["MidWest Homes iCrate double door dog crate", "AmazonBasics Folding metal dog crate", "Diggs Revol dog crate"],
    "best dog shampoo":                 ["Burt's Bees Hypoallergenic dog shampoo", "Earthbath All Natural dog shampoo oatmeal", "TropiClean Luxury 2-in-1 dog shampoo"],
    "best dog harness":                 ["Ruffwear Front Range dog harness", "PetSafe Easy Walk dog harness no-pull", "Julius-K9 IDC Power dog harness"],
    "how to stop dog barking":          ["PetSafe Remote Spray Trainer for dogs", "KONG Classic dog toy for mental stimulation", "Adaptil Calm dog appeasing pheromone diffuser"],
    "best aquarium plants for beginners": ["Greenpro Java Fern live aquarium plant", "Anubias Barteri live aquarium plant", "Amazon Sword Echinodorus beginner aquarium plant"],
    "best aquarium filter":             ["Fluval 307 canister aquarium filter", "AquaClear Power Filter hang-on-back", "MarineLand Penguin Power Filter 200"],
    "best aquarium heater":             ["Eheim Jager TruTemp aquarium heater", "Fluval E200 Advanced Electronic heater", "Aqueon Pro adjustable aquarium heater"],
    "best betta fish tank":             ["Fluval Spec V 5-gallon betta tank", "Marineland Contour 5 glass betta aquarium", "Tetra Crescent acrylic aquarium kit"],
    "how to cycle a fish tank":         ["API Master Test Kit freshwater aquarium", "Tetra SafeStart Plus beneficial bacteria", "Dr. Tim's Aquatics One and Only nitrifying bacteria"],
    "best bird cage":                   ["Prevue Pet Products Wrought Iron bird cage", "Vision Bird Cage Model M02", "Midwest Homes for Pets bird cage"],
    "best bird food":                   ["Zupreem Natural Bird Food medium parrots", "Roudybush Daily Maintenance pellets", "Harrison's Bird Foods Adult Lifetime"],
    "best hamster cage":                ["Prevue Pet Products Universal small animal home", "Kaytee My First Home hamster habitat", "Ferplast Favola hamster cage"],
    "best rabbit hutch":                ["Petsfit 2-Story outdoor rabbit hutch", "Aivituvin Rabbit Hutch with run", "MidWest Wabbitat Deluxe rabbit home"],
    "best air purifier for pet dander": ["Winix 5500-2 air purifier with PlasmaWave", "Levoit Core 400S smart air purifier", "Coway AP-1512HH Mighty air purifier HEPA"],
    "best robot vacuum for pet hair":   ["iRobot Roomba i3+ self-emptying robot vacuum", "Shark IQ Robot vacuum with self-empty base", "Eufy BoostIQ RoboVac 11S slim robot vacuum"],
    "best pet insurance 2026":          ["Lemonade Pet Insurance plan", "Healthy Paws Pet Insurance plan", "Figo Pet Insurance plan"],
    "best dog toys for aggressive chewers": ["KONG Extreme dog toy black rubber", "Goughnuts Maxx 50 dog chew ring", "West Paw Zogoflex Hurley dog bone"],
}

ANGLE_HINTS: dict[str, str] = {
    "listicle":      "Look for products with 4.5+ stars and 300+ reviews. Variety of price points preferred (budget / mid / premium).",
    "buyers-guide":  "Find 3 products at different price tiers: budget (~$15-25), mid-range (~$30-50), premium ($50+).",
    "how-to":        "Focus on tools/accessories needed for the process, not just food/treats.",
    "comparison":    "Send 2 products that directly compete (similar type, different brand/price).",
    "budget":        "Only products under $30. Prime eligible mandatory.",
    "premium":       "Premium picks $40+. High review count (500+) and 4.5+ stars.",
    "seasonal":      "Products relevant to the current season or upcoming holiday.",
    "annual_update": "Same categories as previous version — just check if original ASINs still have good ratings.",
}


def get_product_suggestions(keyword: str, category: str, angle: str) -> list[str]:
    kw_lower = keyword.lower().strip()
    if kw_lower in PRODUCT_SUGGESTIONS:
        return PRODUCT_SUGGESTIONS[kw_lower]
    for key, suggestions in PRODUCT_SUGGESTIONS.items():
        if key in kw_lower or kw_lower in key:
            return suggestions
    fallbacks = {
        "cats":       ["Best selling wet cat food for indoor cats", "Best selling dry cat food adult", "Best rated cat accessory or toy"],
        "dogs":       ["Best selling dry dog food for adult dogs", "Best rated dog treat natural", "Best selling dog accessory or toy"],
        "fish":       ["Best live aquarium plant beginner", "Best aquarium filter for small tank", "Best aquarium starter kit"],
        "birds":      ["Best bird food pellets parrots", "Best bird cage medium size", "Best bird toy enrichment"],
        "small-pets": ["Best hamster or rabbit bedding", "Best small animal cage habitat", "Best small pet food pellets"],
        "guides":     ["Best selling pet health supplement", "Best rated pet first aid kit", "Best pet grooming tool"],
        "pets":       [f"Best selling pet product {YEAR}", "Best rated pet food brand", "Best pet accessory Amazon bestseller"],
    }
    return fallbacks.get(category, fallbacks["pets"])


def save_product_suggestions(slug: str, keyword: str, category: str, angle: str, day_dir: Path) -> None:
    suggestions = get_product_suggestions(keyword, category, angle)
    angle_hint = ANGLE_HINTS.get(angle, "Look for 4.5+ stars, 300+ reviews, Prime eligible.")

    lines = [
        f"Products needed for: {keyword}",
        f"Article angle: {angle}",
        f"Category: {category}",
        "",
        "=" * 60,
        "Search these on Amazon and send me the product page URLs:",
        "(I'll extract ASIN, title, image, rating automatically)",
        "=" * 60,
        "",
    ]
    for i, term in enumerate(suggestions, 1):
        lines.append(f'{i}. "{term}"')

    lines += [
        "",
        "-" * 60,
        f"TIP: {angle_hint}",
        "-" * 60,
        "",
        "Image URL format to look for:",
        "  https://m.media-amazon.com/images/I/XXXXXXX._AC_SL1500_.jpg",
        "",
        "Paste the Amazon product page URL for each item, e.g.:",
        "  https://www.amazon.com/dp/B08XYZ1234",
    ]

    txt_path = day_dir / f"{slug}_products_needed.txt"
    txt_path.write_text("\n".join(lines), encoding="utf-8")
    log.info(f"Products needed: {txt_path}")


# ── Save to dated subfolder ───────────────────────────────────────────────────
def save_article(keyword: str, angle: str, config: dict) -> tuple[str, str]:
    slug = slugify(keyword)
    date_str = datetime.now().strftime("%Y-%m-%d")
    filename = f"{slug}_{date_str}"
    category = detect_category(keyword)

    day_dir = Path(f"articles/draft/{date_str}")
    day_dir.mkdir(parents=True, exist_ok=True)

    article_content = build_article(keyword, angle, config)
    title = build_title(keyword, angle)
    meta_desc = build_meta_description(keyword, title, angle)

    draft_path = day_dir / f"{filename}.md"
    meta_path = day_dir / f"{filename}_meta.json"

    draft_path.write_text(article_content, encoding="utf-8")

    meta = {
        "slug": slug,
        "title": title,
        "meta_description": meta_desc,
        "primary_keyword": keyword,
        "secondary_keywords": [],
        "word_count": len(article_content.split()),
        "reading_time": f"{max(1, len(article_content.split()) // 200)} min",
        "category": category,
        "tags": [keyword, category],
        "angle": angle,
        "amazon_searches": [keyword, f"best {keyword}", f"{keyword} review"],
        "status": "draft",
        "created_at": datetime.now().isoformat(),
    }
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    save_product_suggestions(slug, keyword, category, angle, day_dir)

    log.info(f"Draft saved: {draft_path} | category: {category} | words: {meta['word_count']}")
    return str(draft_path), slug


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-")


def load_config() -> dict:
    return json.loads(Path("config.json").read_text())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--keyword", required=True)
    parser.add_argument("--angle", default="listicle")
    args = parser.parse_args()

    config = load_config()
    path, slug = save_article(args.keyword, args.angle, config)
    print(json.dumps({
        "draft_path": path,
        "slug": slug,
        "title": build_title(args.keyword, args.angle),
        "category": detect_category(args.keyword),
    }))
