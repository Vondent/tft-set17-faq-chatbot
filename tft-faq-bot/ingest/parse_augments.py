"""
Parse raw Mobalytics augment files into a single clean structured file.

Inputs:  data/raw/mobalytics/augments_tier1_silver.txt
         data/raw/mobalytics/augments_tier2_gold.txt
         data/raw/mobalytics/augments_tier3_prismatic.txt
Output:  data/processed/augments.txt

Each augment in the raw files follows a strict 3-line pattern:
  <Name>
  <tier number>
  <description>
"""

import os
import re

INPUTS = [
    ("data/raw/mobalytics/augments_tier1_silver.txt",    1, "Silver"),
    ("data/raw/mobalytics/augments_tier2_gold.txt",      2, "Gold"),
    ("data/raw/mobalytics/augments_tier3_prismatic.txt", 3, "Prismatic"),
]
OUTPUT_FILE = "data/processed/augments.txt"

SKIP_LINES = {
    "Use your favourite features in-game with our Desktop App",
    "Augments",
    (
        "All TFT Augments in Set 17 organized into three tiers. Choosing the right augments "
        "can really impact the course of your game. Make sure to know how they work and the "
        "order they may appear."
    ),
}

TEMPLATE_RE = re.compile(r"\{\{[^}]+\}\}")


def clean_description(text):
    text = TEMPLATE_RE.sub("", text)
    return " ".join(text.split()).strip()


def load_augments(filepath, tier_num, tier_name):
    with open(filepath, "r", encoding="utf-8") as f:
        lines = [l.strip() for l in f.readlines()]

    # Skip source/tier header block
    start = 0
    for i, line in enumerate(lines):
        if line.startswith("Tier:"):
            start = i + 1
            break
    lines = lines[start:]

    augments = []
    i = 0
    while i < len(lines):
        line = lines[i]

        if not line or line in SKIP_LINES:
            i += 1
            continue

        # Augment entry: name line followed by tier digit followed by description
        if (
            i + 2 < len(lines)
            and lines[i + 1] == str(tier_num)
            and lines[i + 2]
            and lines[i + 2] not in SKIP_LINES
        ):
            name = line
            description = clean_description(lines[i + 2])
            augments.append({
                "name": name,
                "tier_num": tier_num,
                "tier_name": tier_name,
                "description": description,
            })
            i += 3
        else:
            i += 1

    return augments


def format_augment(aug):
    return "\n".join([
        f"Augment: {aug['name']}",
        f"Tier: {aug['tier_num']} ({aug['tier_name']})",
        f"Description: {aug['description']}",
    ])


def run():
    all_augments = []
    for filepath, tier_num, tier_name in INPUTS:
        if not os.path.exists(filepath):
            print(f"Missing: {filepath} — run the scraper first")
            continue
        augments = load_augments(filepath, tier_num, tier_name)
        print(f"  Tier {tier_num} ({tier_name}): {len(augments)} augments")
        all_augments.extend(augments)

    print(f"Total: {len(all_augments)} augments\n")

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("# TFT Set 17 — Augments\n\n")

        for tier_num, tier_name in [(1, "Silver"), (2, "Gold"), (3, "Prismatic")]:
            tier_augs = [a for a in all_augments if a["tier_num"] == tier_num]
            f.write(f"## {tier_name} Augments (Tier {tier_num})\n\n")
            for aug in tier_augs:
                f.write(format_augment(aug))
                f.write("\n\n---\n\n")

    print(f"Saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    run()