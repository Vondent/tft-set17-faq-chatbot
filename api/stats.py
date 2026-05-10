import re
from collections import Counter
from pathlib import Path

PROCESSED_DIR = Path("data/processed")


def _parse_blocks(filename):
    path = PROCESSED_DIR / filename
    with open(path, encoding="utf-8") as f:
        content = f.read()
    blocks = []
    for block in content.split("---"):
        block = block.strip()
        if not block or block.startswith("#"):
            continue
        data = {}
        for line in block.split("\n"):
            if ":" in line:
                key, _, val = line.partition(":")
                data[key.strip()] = val.strip()
        if data:
            blocks.append(data)
    return blocks


def parse_champions():
    champions = []
    for data in _parse_blocks("champions.txt"):
        if "Champion" not in data or "Cost" not in data:
            continue
        try:
            traits = [t.strip() for t in data.get("Traits", "").split(",") if t.strip()]
            champions.append({
                "name": data["Champion"],
                "cost": int(data["Cost"]),
                "traits": traits,
            })
        except ValueError:
            pass
    return champions


def parse_comps():
    path = PROCESSED_DIR / "comps.txt"
    with open(path, encoding="utf-8") as f:
        content = f.read()
    comps = []
    pattern = r"^([SABC]) Tier — (.+?): avg placement ([\d.]+), Top 4: ([\d.]+)%"
    for line in content.splitlines():
        m = re.match(pattern, line.strip())
        if m:
            comps.append({
                "tier": m.group(1),
                "name": m.group(2),
                "avg_placement": float(m.group(3)),
                "top4_rate": float(m.group(4)),
            })
    return comps


def parse_items():
    items = []
    for data in _parse_blocks("items.txt"):
        if "Item" not in data or "Category" not in data:
            continue
        items.append({
            "name": data["Item"],
            "category": data["Category"],
            "tier_rating": data.get("Tier Rating"),
        })
    return items


def parse_augments():
    augments = []
    for data in _parse_blocks("augments.txt"):
        if "Augment" not in data or "Tier" not in data:
            continue
        m = re.search(r"\((\w+)\)", data["Tier"])
        rarity = m.group(1) if m else data["Tier"]
        augments.append({
            "name": data["Augment"],
            "rarity": rarity,
            "tier_rating": data.get("Tier Rating"),
        })
    return augments


def get_stats():
    champions = parse_champions()
    comps = parse_comps()
    items = parse_items()
    augments = parse_augments()

    cost_dist = Counter(c["cost"] for c in champions)
    cost_distribution = [{"cost": k, "count": v} for k, v in sorted(cost_dist.items())]

    all_traits = [t for c in champions for t in c["traits"]]
    trait_frequency = [
        {"trait": t, "count": c}
        for t, c in Counter(all_traits).most_common(15)
    ]

    top_comps = sorted(comps, key=lambda x: x["avg_placement"])[:15]

    tier_order = ["S", "A", "B", "C"]
    tier_dist = Counter(c["tier"] for c in comps)
    comp_tier_distribution = [
        {"tier": t, "count": tier_dist.get(t, 0)} for t in tier_order
    ]

    combined_items = [i for i in items if i["category"] == "Combined" and i["tier_rating"]]
    rating_order = ["S", "A", "B", "C"]
    item_tier_dist = Counter(i["tier_rating"] for i in combined_items)
    item_tier_distribution = [
        {"rating": r, "count": item_tier_dist.get(r, 0)} for r in rating_order
    ]

    rarity_order = ["Silver", "Gold", "Prismatic"]
    augment_tier_by_rarity = {}
    for rarity in rarity_order:
        rated = [a for a in augments if a["rarity"] == rarity and a["tier_rating"]]
        dist = Counter(a["tier_rating"] for a in rated)
        augment_tier_by_rarity[rarity] = {r: dist.get(r, 0) for r in rating_order}

    return {
        "cost_distribution": cost_distribution,
        "trait_frequency": trait_frequency,
        "top_comps": top_comps,
        "comp_tier_distribution": comp_tier_distribution,
        "item_tier_distribution": item_tier_distribution,
        "augment_tier_by_rarity": augment_tier_by_rarity,
        "scatter_comps": [
            {"name": c["name"], "avg_placement": c["avg_placement"], "top4_rate": c["top4_rate"], "tier": c["tier"]}
            for c in comps
        ],
    }