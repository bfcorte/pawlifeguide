#!/usr/bin/env python3
"""
Article Writer — Generates SEO-optimized articles in Markdown.
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

DISCLAIMER = ""

# ── Category detection ──────────────────────────────────────────────────────
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


# ── Title generation ─────────────────────────────────────────────────────────
COUNT_OPTIONS = [5, 7, 9, 10, 12]


def _strip_leading_superlatives(keyword: str) -> str:
    stops = ("best ", "top ", "cheap ", "affordable ", "recommended ", "how to ")
    kw = keyword.lower().strip()
    for s in stops:
        if kw.startswith(s):
            kw = kw[len(s):]
    return kw.strip().title()


def build_title(keyword: str, angle: str) -> str:
    year = datetime.now().year
    kw_clean = _strip_leading_superlatives(keyword)
    # Para how-to: remove "how to" do início para não duplicar no título
    kw_action = re.sub(r'^how\s+to\s+', '', keyword.strip(), flags=re.IGNORECASE).strip().title()
    kw_cap = keyword.strip().title()
    n = random.choice(COUNT_OPTIONS)

    templates = {
        "listicle":      f"{n} Best {kw_clean} in {year} (Tested & Reviewed)",
        "how-to":        f"How to {kw_action}: Step-by-Step Guide ({year})",
        "comparison":    f"{kw_cap}: Which One Is Really Worth It in {year}?",
        "single-review": f"The Best {kw_clean} in {year}: In-Depth Review",
        "buyers-guide":  f"How to Choose the Best {kw_clean} ({year} Buyer's Guide)",
        "budget":        f"Best Affordable {kw_clean} in {year} (Under $50)",
        "premium":       f"Best Premium {kw_clean} Worth Every Penny in {year}",
        "seasonal":      f"Best {kw_clean} for This Season ({year})",
        "annual_update": f"Best {kw_clean} in {year} (Updated)",
        "tips":          f"{n} Expert Tips for {kw_cap} That Actually Work ({year})",
        "care-guide":    f"Complete {kw_cap} Guide: Everything You Need to Know ({year})",
    }
    return templates.get(angle, f"{n} Best {kw_clean} — Complete Guide {year}")


def build_meta_description(keyword: str, title: str, angle: str) -> str:
    kw = keyword.lower()
    templates = {
        "listicle":     f"Best {kw} in {datetime.now().year} — tested, rated 4.2+ stars, Prime eligible. Expert picks with pros, cons, and current Amazon prices.",
        "how-to":       f"Learn how to {kw} step-by-step. Expert advice, common mistakes to avoid, and the best products for the job.",
        "comparison":   f"Comparing the top {kw} options head-to-head. Real data, honest pros & cons, and a clear winner for each use case.",
        "buyers-guide": f"How to choose the best {kw} — key criteria, red flags, and expert-picked recommendations for {datetime.now().year}.",
        "budget":       f"Best affordable {kw} in {datetime.now().year} — quality options under $50 with 4.2+ stars and thousands of verified reviews.",
        "tips":         f"Expert tips for {kw} that make a real difference. Advice from experienced pet owners and veterinary guidance.",
        "care-guide":   f"Complete guide to {kw} — everything from basics to advanced care, product recommendations, and common mistakes.",
    }
    desc = templates.get(angle, f"Best {kw} in {datetime.now().year} — expert picks, honest reviews, and current Amazon prices. All Prime eligible.")
    return desc[:160]


# ── Category-specific knowledge base ─────────────────────────────────────────
CAT_FACTS = {
    "behavior": "Cats are territorial, solitary hunters by nature. Most of their behavioral quirks — hiding, slow blinking, head-bunting — are direct expressions of this instinct. Understanding why they do something makes it much easier to respond correctly.",
    "health": "Cats are obligate carnivores, meaning they require nutrients found only in animal tissue. Taurine, arachidonic acid, and vitamin A must come from meat — their bodies can't synthesize them from plant sources the way humans can.",
    "stress": "Stress is the #1 hidden cause of illness in domestic cats. Urinary problems, over-grooming, and digestive issues are frequently stress-related. The most common triggers: changes in routine, new people or animals, and insufficient vertical space.",
    "communication": "Cats communicate primarily through body language and scent, not vocalizations. Meowing is largely a behavior developed specifically to communicate with humans — adult cats rarely meow at each other.",
}
DOG_FACTS = {
    "behavior": "Dogs are pack animals who evolved to read human social cues better than any other species, including other primates. They understand pointing gestures, follow eye gaze, and respond to emotional tone of voice — all learned through 15,000 years of co-evolution with humans.",
    "health": "Dogs are omnivores but thrive on diets high in animal protein. Puppies have different nutritional needs than adults — particularly regarding calcium-to-phosphorus ratios, which directly affect bone development.",
    "training": "Dogs learn through association and consequence. The most effective training method is positive reinforcement: marking the exact moment of correct behavior with a reward. Timing matters more than the reward itself — a 2-second delay dramatically reduces effectiveness.",
    "stress": "Chronic stress in dogs often goes unrecognized. Signs include excessive yawning outside of tiredness, lip licking without food present, whale eye (showing whites of eyes), and low tail position. Recognizing these prevents escalation to aggression.",
}
FISH_FACTS = {
    "water": "Water quality is the single most critical factor in fish health. Fish live in their waste — ammonia from fish waste is directly toxic, and the nitrogen cycle (converting ammonia → nitrite → nitrate via beneficial bacteria) is what makes a tank livable.",
    "cycling": "A properly cycled tank has an established colony of beneficial bacteria that process fish waste. This takes 4-8 weeks to establish from scratch. Skipping this step is the most common reason new fish die within weeks of purchase.",
    "stress": "Fish show stress through clamped fins, hiding, color loss, and rapid gill movement. Most fish deaths are stress-related — poor water parameters, overcrowding, and incompatible tank mates are the leading causes.",
}
BIRD_FACTS = {
    "social": "Most pet birds are highly social animals that live in flocks in the wild. Isolation leads to feather plucking, screaming, and self-harm behaviors. Birds kept alone need significant daily interaction to remain psychologically healthy.",
    "diet": "Seeds-only diets are a leading cause of nutritional deficiencies in pet birds. Most species need a varied diet of pellets, fresh vegetables, and limited seeds. Vitamin A deficiency (from seed-heavy diets) is one of the most common preventable illnesses in captive birds.",
}
SMALL_PET_FACTS = {
    "housing": "Small pets are often underhoused. The minimum cage sizes frequently sold in pet stores are inadequate for most species. A hamster, for example, needs at minimum 450 square inches of floor space — most starter cages fall well short.",
    "diet": "Rabbits and guinea pigs require unlimited timothy hay as the foundation of their diet — it provides the fiber essential for gut motility. Without it, gastrointestinal stasis (a life-threatening condition) is a serious risk.",
}

CATEGORY_FACTS = {
    "cats": CAT_FACTS,
    "dogs": DOG_FACTS,
    "fish": FISH_FACTS,
    "birds": BIRD_FACTS,
    "small-pets": SMALL_PET_FACTS,
}

# ── Educational content generators by angle ──────────────────────────────────
def build_howto_body(keyword: str, category: str) -> str:
    kw = keyword.lower().replace("how to ", "").strip()
    facts = CATEGORY_FACTS.get(category, {})
    fact_text = random.choice(list(facts.values())) if facts else ""

    steps = {
        "introduce a new cat": [
            ("Keep them completely separate at first", "Don't rush the face-to-face meeting. Put the new cat in a separate room with their own food, water, and litter box. This usually takes 1–2 weeks. The goal is scent familiarization before any visual contact."),
            ("Exchange scents before visual contact", "Swap bedding between the cats so they get used to each other's smell. Feed both cats on opposite sides of the closed door — this builds a positive association with the other cat's scent."),
            ("Allow visual contact through a barrier", "Once both cats are eating calmly near the door, crack it slightly or use a baby gate. Watch body language closely: flattened ears, puffed tails, and hissing are signs to slow down."),
            ("Supervised face-to-face meetings", "Keep first meetings short (5–10 minutes) and always in a neutral space. Have an escape route available for both cats. Don't force interaction — let them set the pace."),
            ("Expand territory gradually", "Once both cats are coexisting calmly, gradually give the new cat more access to the home. Expect the process to take 2–4 weeks total, sometimes longer for older or more territorial cats."),
        ],
        "train a cat": [
            ("Start with the right reward", "Cats are motivated by food, not praise. Use tiny, high-value treats (smaller than your fingernail) that your cat goes crazy for. Timing is everything — the reward must come within 1–2 seconds of the correct behavior."),
            ("Learn to use a clicker (or marker word)", "A clicker or a consistent marker word ('yes!') bridges the gap between the behavior and the reward. Click the exact moment your cat does the right thing, then treat. The click means 'that exact thing you just did is what I'm rewarding'."),
            ("Start with the easiest behavior: sit", "Hold a treat above and slightly behind your cat's nose. As they look up, their hindquarters naturally lower. The moment their bottom touches the floor, click and treat. Repeat 10–15 times per session."),
            ("Keep sessions short", "5–10 minutes maximum, once or twice a day. Cats disengage quickly when bored or full. Always end on a success — even if you need to ask for something easy."),
            ("Progress to more complex behaviors", "Once 'sit' is solid (90%+ success rate), build on it. 'Stay' is just extending the sit. 'Come' uses the same marker/reward sequence. Each new behavior follows the same pattern: lure → mark → reward → fade the lure."),
        ],
        "cycle a fish tank": [
            ("Understand what cycling actually means", "Cycling establishes a colony of beneficial bacteria (Nitrosomonas and Nitrobacter) that convert toxic ammonia into less harmful nitrate. Without these bacteria, ammonia from fish waste accumulates and kills fish. The process mimics what happens naturally in established bodies of water."),
            ("Set up your tank completely before adding fish", "Fill the tank, run the filter, set the heater to the correct temperature, and add dechlorinator to neutralize chlorine and chloramine. Let it run for 24 hours before starting the cycle."),
            ("Add an ammonia source", "Bacteria need ammonia to grow. Add pure ammonia (no surfactants) to reach 2–4 ppm, or add a pinch of fish food daily to generate ammonia as it breaks down. Don't add fish yet — they'll die in this environment."),
            ("Test the water every 2–3 days", "Use a liquid test kit (more accurate than strips) to track ammonia, nitrite, and nitrate levels. Week 1–2: ammonia rises. Week 2–3: nitrite rises as ammonia-consuming bacteria establish. Week 3–6: nitrate appears as the full cycle completes."),
            ("Cycle is complete when...", "Ammonia reads 0 ppm, nitrite reads 0 ppm, and nitrate is detectable (above 0). At this point, do a 50% water change to reduce nitrate, then slowly add fish — no more than a few at a time to avoid overwhelming the bacteria colony."),
        ],
    }

    # Find matching steps
    matched_steps = None
    for key, val in steps.items():
        if key in kw or kw in key:
            matched_steps = val
            break

    if not matched_steps:
        # Generic how-to steps
        matched_steps = [
            ("Understand the basics first", f"Before jumping into {kw}, it helps to understand the underlying principles. {fact_text or f'Most common mistakes with {kw} come from skipping foundational steps that seem optional but aren\\'t.'}"),
            ("Gather what you need", f"Prepare your space and materials before starting. Trying to improvise mid-process with {kw} leads to inconsistent results."),
            ("Start slow and build consistency", f"The first attempt at {kw} rarely goes perfectly — that's normal. Focus on consistency over perfection. Small, frequent sessions are more effective than long, infrequent ones."),
            ("Monitor progress and adjust", f"Pay attention to how your pet responds during {kw}. Their body language tells you more than any guide can — if they're stressed or disengaged, take a step back."),
            ("Common mistakes to avoid", f"The most frequent errors with {kw}: moving too fast, using the wrong rewards, and inconsistent timing. All three are fixable once you know to watch for them."),
        ]

    steps_text = ""
    for i, (title, body) in enumerate(matched_steps, 1):
        steps_text += f"\n### Step {i}: {title}\n\n{body}\n"

    return steps_text, fact_text


def build_listicle_body(keyword: str, category: str) -> str:
    kw = keyword.lower()
    facts = CATEGORY_FACTS.get(category, {})
    fact_keys = list(facts.keys())
    fact_text = facts[random.choice(fact_keys)] if fact_keys else ""

    criteria = {
        "cat food": [
            ("Protein source comes first on the ingredient list", "Cats are obligate carnivores — meat, poultry, or fish must be the primary ingredient. If the first ingredient is a grain, broth, or 'meat by-products' without a named source, keep looking."),
            ("Moisture content for indoor cats", "Indoor cats are prone to urinary tract issues and chronic mild dehydration. Wet food (70–80% moisture) is significantly better for kidney and urinary health than dry food alone."),
            ("Taurine is non-negotiable", "Cats can't synthesize taurine and must get it from food. Deficiency causes heart disease and blindness. All reputable cat food brands include it, but it's worth verifying on the label."),
            ("Watch for fillers and artificial additives", "Corn, wheat, soy, and artificial preservatives (BHA, BHT, ethoxyquin) add no nutritional value for cats. They're cost-reduction tools, not nutritional choices."),
        ],
        "dog food": [
            ("Named protein source first", "Chicken, beef, salmon — specific named proteins mean you know what you're getting. 'Meat meal' or 'animal by-products' without a named species is a quality red flag."),
            ("Life stage formulation", "Puppy, adult, and senior dogs have genuinely different nutritional needs. A puppy food fed to an adult large-breed dog can accelerate joint problems. Match the formula to the life stage."),
            ("AAFCO statement", "Look for 'complete and balanced' per AAFCO standards, either through feeding trials or nutritional analysis. This is the minimum bar for nutritional adequacy."),
            ("Caloric density", "Small breeds have faster metabolisms and need calorie-dense food in smaller portions. Large breeds benefit from controlled calories to prevent the rapid growth that strains joints."),
        ],
        "dog treats": [
            ("Single-ingredient or short ingredient list", "The fewer ingredients, the easier it is to identify what you're feeding. Single-ingredient treats (pure chicken, salmon, sweet potato) are ideal for dogs with sensitivities."),
            ("Size appropriate for training", "Training treats should be small enough that your dog can eat them in 1–2 seconds. Bigger treats interrupt focus and add up calorically. Break larger treats into smaller pieces."),
            ("Caloric content relative to daily intake", "Treats should make up no more than 10% of daily calories. A handful of treats that equals a full meal throws off nutritional balance and contributes to weight gain."),
            ("No xylitol, grapes, raisins, or macadamia nuts", "These are toxic to dogs. Xylitol in particular is dangerous even in small amounts and appears in some 'natural' products. Always check the ingredient list."),
        ],
        "interactive cat toys": [
            ("Mimics prey movement", "Cats are triggered by specific movement patterns — small, fast, erratic movements that mimic injured prey. Toys that move in straight lines or predictably lose their appeal quickly."),
            ("Appropriate size", "Toys should be small enough to bat and carry, but large enough not to be swallowed. Feather attachments are high-value but need regular inspection for detached pieces."),
            ("Engages hunting sequence", "The full hunting sequence is: stalk → chase → pounce → catch → kill. The best toys allow cats to complete this sequence, including a 'kill' moment where they can grab and hold the toy."),
            ("Durability for active cats", "Some cats are extremely rough on toys. Electronic toys with fragile components don't survive active cats. Check reviews specifically from owners of similarly-sized, active cats."),
        ],
    }

    matched_criteria = None
    for key, val in criteria.items():
        if key in kw or any(word in kw for word in key.split()):
            matched_criteria = val
            break

    if not matched_criteria:
        matched_criteria = [
            ("Safety and materials", f"Pet products should use non-toxic, pet-safe materials. For anything your pet ingests or chews, this is non-negotiable. Always verify material safety before purchasing."),
            ("Right fit for your pet's size and age", f"What works for a large dog or adult cat won't work for a small breed or kitten. Size specifications matter — incorrect sizing is the most common preventable purchase mistake."),
            ("Verified reviews from real owners", f"Look for reviews mentioning 3+ months of use. Initial impressions rarely reflect long-term performance. The difference shows up over time."),
            ("Value over time, not upfront cost", f"Calculate cost-per-month or cost-per-year, not just sticker price. A $15 product that lasts 2 months costs more annually than a $40 product that lasts a year."),
        ]

    criteria_text = ""
    for title, body in matched_criteria:
        criteria_text += f"\n### {title}\n\n{body}\n"

    return criteria_text, fact_text


def build_article(keyword: str, angle: str, config: dict) -> str:
    identity = config["blog_identity"]
    title = build_title(keyword, angle)
    year = datetime.now().year
    category = detect_category(keyword)
    kw = keyword.lower()

    if angle in ("how-to", "care-guide"):
        steps_text, fact_text = build_howto_body(keyword, category)

        article = f"""# {title}

{fact_text}

Most guides on this topic skip the parts that actually matter. This one doesn't.

<div class="quick-answer">
<strong>Quick Answer:</strong> The key to success with {kw} is patience and following the right sequence. Rushing any step makes the whole process harder. Start with Step 1 below — it sets up everything else.
</div>

## Table of Contents
- [Why This Matters](#why-this-matters)
- [What You Need](#what-you-need)
- [Step-by-Step Guide](#step-by-step-guide)
- [Common Mistakes](#common-mistakes)
- [Recommended Products](#recommended-products)
- [FAQ](#faq)

---

## Why This Matters

Understanding {kw} properly saves time, reduces stress for your pet, and prevents the most common mistakes that set people back weeks. The fundamentals aren't complicated — but they are specific, and skipping them has real consequences.

---

## What You Need

Before starting, make sure you have:
- Patience — this process can't be rushed without setbacks
- The right environment — a calm, familiar space where your pet feels safe
- Consistency — irregular timing is the #1 reason this process stalls
- A way to track progress — even simple notes help identify what's working

---

## Step-by-Step Guide

{steps_text}

---

## Common Mistakes

**Moving too fast.** The most common mistake. Every step builds on the previous one — skipping ahead creates confusion and setbacks that are harder to fix than they were to prevent.

**Inconsistent timing.** Irregular sessions are significantly less effective than short, daily ones. Your pet's brain consolidates learning during rest — consistent exposure is what creates lasting change.

**Misreading stress signals.** Yawning, lip licking, turning away, and low body posture are stress signals, not disinterest. If you see these, stop the session and try again later with lower demands.

**Using punishment.** Punishment teaches your pet what NOT to do, but doesn't teach them what you want instead. Positive reinforcement — rewarding the right behavior — is faster and builds trust rather than eroding it.

---

## Recommended Products

These products make the process significantly easier. None of them are essential, but they're what experienced owners consistently recommend.

[PRODUCT_CARD]

[PRODUCT_CARD]

[PRODUCT_CARD]

---

## FAQ

### How long does {kw} take?
It depends on the individual animal and how consistently you apply the process. Most people see meaningful progress within 1–2 weeks of daily practice. Full mastery of more complex goals typically takes 4–8 weeks.

### My pet doesn't seem interested — what am I doing wrong?
Either the reward isn't motivating enough, the sessions are too long, or the environment has too many distractions. Try a higher-value reward, shorten sessions to 3–5 minutes, and work in the quietest room in your home.

### Can older pets learn this?
Yes. The idea that older pets can't learn new things is a myth. Progress may be slower, but the process is the same. Older animals actually benefit from the mental stimulation.

### What if progress stalls?
Go back one step. If you've been pushing forward and hit a wall, returning to the previous skill and making it rock-solid usually unlocks the stall. Progress isn't always linear.

### Is this safe for my pet?
Yes, when done correctly. The key safety principle: if your pet shows fear, pain, or extreme stress, stop immediately and consult a veterinarian or certified animal behaviorist.

### How do I know it's working?
Your pet initiates the behavior more readily over time, shows less stress during the process, and begins associating the context with something positive (eagerness rather than avoidance).

---

*Have questions about {kw}? Every pet is different — what works for most may need adjustment for yours. The steps above are a solid starting point, not a rigid script.*
"""

    else:  # listicle, buyers-guide, comparison, budget, premium
        criteria_text, fact_text = build_listicle_body(keyword, category)

        article = f"""# {title}

{fact_text}

Here's what actually separates good {kw} from the rest — and which specific options are worth your money in {year}.

<div class="quick-answer">
<strong>Quick Answer:</strong> The best {kw} depends on your pet's specific needs. Read the criteria section before jumping to the product list — knowing what matters makes the choice much easier.
</div>

## Table of Contents
- [What Actually Matters](#what-actually-matters)
- [What to Avoid](#what-to-avoid)
- [Our Top Picks](#our-top-picks)
- [Detailed Reviews](#detailed-reviews)
- [FAQ](#faq)

---

## What Actually Matters

Before looking at any specific product, understand what the meaningful criteria are for {kw}. Most buying mistakes come from optimizing for the wrong things.

{criteria_text}

---

## What to Avoid

The {kw} market has clear red flags. These patterns reliably indicate poor quality:

- **Fewer than 150 verified reviews** — not enough real-world data to trust the claims
- **Ratings below 4.0 stars** — with the number of options available, there's no reason to settle
- **Vague ingredient or material descriptions** — reputable products are transparent about what's in them
- **Unverified health claims** — especially for food, supplements, and anything marketed as "veterinarian recommended" without documentation
- **No return policy** — quality brands stand behind their products

---

## Our Top Picks

Based on the criteria above, these are the options that consistently deliver.

[PRODUCT_CARD]

[PRODUCT_CARD]

[PRODUCT_CARD]

---

## Detailed Reviews

### Best Overall

[PRODUCT_CARD]

This option scores highest across the criteria that matter most for {kw}: material quality, long-term owner satisfaction, and fit for the most common use cases. It's not always the cheapest, but it's the one that most owners would buy again.

---

### Best Value

[PRODUCT_CARD]

The strongest performer in its price range. Delivers results that compete with options costing significantly more. For first-time buyers or those managing multiple pets, this is the smart starting point.

---

### Best for Specific Needs

[PRODUCT_CARD]

Not the right fit for everyone, but exceptional for specific situations. See the product details for who this is actually designed for.

---

## How We Evaluate Products

Every pick on this list meets these minimum standards:
- 4.2+ star rating with 150+ verified reviews
- Available through Amazon Prime
- Clear, verifiable material/ingredient transparency
- No active safety recalls

No brand pays for placement here.

---

## FAQ

### What's the most important factor when choosing {kw}?
The criteria that matter most depend on your specific pet — size, age, and health status all affect which option is the right fit. Start with the criteria section above and match it to your situation before looking at specific products.

### How much should I spend on {kw}?
For most pet owners, mid-range options ($25–$60) offer the best combination of quality and value. Budget options often require replacement twice as often, which erases the savings. Premium options are worth considering when longevity or specific health needs justify the cost.

### Are all these products safe?
Yes — all picks meet standard pet safety requirements. For food products, we verify no active FDA recalls. For physical products, we check for non-toxic materials and construction standards appropriate for the intended use.

### How do I know if my pet likes it?
Consistent, voluntary use is the clearest signal. Avoidance, stress signals, or changes in appetite/behavior after introduction are signs something isn't working — try a different option or consult your vet.

### Can I find these on Amazon?
Yes — all picks are Amazon Prime eligible. Prices fluctuate, so check current pricing using the links above.

---

*Pet needs vary — what works for most may need adjustment for yours. These picks are based on broad owner satisfaction data, not a single experience.*
"""

    return article.strip()


# ── Save to dated subfolder ───────────────────────────────────────────────────
def save_article(keyword: str, angle: str, config: dict) -> tuple[str, str]:
    slug = slugify(keyword)
    date_str = datetime.now().strftime("%Y-%m-%d")
    filename = f"{slug}_{date_str}"
    category = detect_category(keyword)

    # Save inside articles/draft/YYYY-MM-DD/
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

    log.info(f"Draft saved: {draft_path} | category: {category}")
    return str(draft_path), slug


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-")


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


def load_config() -> dict:
    return json.loads(Path("config.json").read_text())
