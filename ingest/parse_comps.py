"""
Parses MetaTFT comp data into readable text for the chatbot knowledge base.

Inputs:  data/raw/metatft_comps_data.json
         data/raw/metatft_comps_stats.json
         data/raw/metatft_lookup_items.json
         data/raw/metatft_lookup_traits.json
Output:  data/processed/comps.txt

Run from the chatbot/ directory.
"""

import json
import os
import re

RAW_DIR = os.path.join("data", "raw")
CHAMPIONS_FILE = os.path.join("data", "processed", "champions.txt")
OUTPUT_FILE = os.path.join("data", "processed", "comps.txt")
MIN_GAMES = 1000  # skip tiny sample comps


def load(filename):
    with open(os.path.join(RAW_DIR, filename), encoding="utf-8") as f:
        return json.load(f)


def camel_split(s):
    s = re.sub(r"([a-z])([A-Z])", r"\1 \2", s)
    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", s)
    return s.strip()


def build_item_lookup(items_data):
    """apiName -> display name."""
    lookup = {}
    for item in items_data.get("items", []):
        api = item.get("apiName") or item.get("id", "")
        name = item.get("en_name") or item.get("name", "")
        if api and name:
            lookup[api] = name
    return lookup


def build_trait_lookup(trait_map):
    """Internal trait ID -> display name (invert the mapping)."""
    return {v: k.replace("-", " ").title() for k, v in trait_map.items()}


def load_champion_traits(filepath):
    """Parse champions.txt -> {normalized_name: [trait, ...]}"""
    lookup = {}
    current = None
    with open(filepath, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("Champion: "):
                current = line[len("Champion: "):]
            elif line.startswith("Traits: ") and current:
                traits = [t.strip() for t in line[len("Traits: "):].split(",")]
                key = re.sub(r"[^a-z0-9]", "", current.lower())
                lookup[key] = traits
                current = None
    return lookup


def count_traits(unit_names, champion_traits):
    """Count how many units in the comp have each trait."""
    counts = {}
    for name in unit_names:
        key = re.sub(r"[^a-z0-9]", "", name.lower())
        for trait in champion_traits.get(key, []):
            counts[trait] = counts.get(trait, 0) + 1
    return counts


UNIT_NAME_OVERRIDES = {
    "TFT17_Belveth":  "Bel'Veth",
    "TFT17_Chogath":  "Cho'Gath",
    "TFT17_RekSai":   "Rek'Sai",
    "TFT17_Leblanc":  "LeBlanc",
    "TFT17_Nunu":     "Nunu & Willump",
}


def unit_display(unit_id):
    """TFT17_Viktor -> Viktor, TFT17_IvernMinion -> Ivern Minion."""
    if unit_id in UNIT_NAME_OVERRIDES:
        return UNIT_NAME_OVERRIDES[unit_id]
    name = re.sub(r"^TFT\d*_", "", unit_id)
    return camel_split(name)


def item_display(item_id, item_lookup):
    if item_id in item_lookup:
        return item_lookup[item_id]
    name = re.sub(r"^TFT\d*_Item_(?:Artifact_|PsyOps_|AnimaSquad\w*_)?", "", item_id)
    return camel_split(name)


def parse_traits(traits_string, trait_lookup):
    """'TFT17_DarkStar_3, TFT17_APTrait_2' -> ['Dark Star (3)', 'Replicator (2)']"""
    traits = []
    for part in traits_string.split(", "):
        part = part.strip()
        if not part:
            continue
        segments = part.rsplit("_", 1)
        if len(segments) == 2 and segments[1].isdigit():
            trait_id, count = segments[0], segments[1]
        else:
            trait_id, count = part, "?"
        name = trait_lookup.get(trait_id) or camel_split(re.sub(r"^TFT\d*_", "", trait_id))
        traits.append(f"{name} ({count})")
    return traits


SKIP_UNITS = {"Summon", "Minion"}

def parse_units(units_string):
    units = [unit_display(u.strip()) for u in units_string.split(",") if u.strip()]
    return [u for u in units if u not in SKIP_UNITS]


def comp_name(name_array, trait_lookup):
    """Return '[Trait] [Unit]' from the highest-scoring trait and unit in the name array."""
    units  = [e for e in name_array if e.get("type") == "unit"]
    traits = [e for e in name_array if e.get("type") == "trait"]
    unit_name  = unit_display(max(units,  key=lambda e: e.get("score", 0))["name"]) if units  else ""
    trait_name = trait_lookup.get(max(traits, key=lambda e: e.get("score", 0))["name"], "") if traits else ""
    if trait_name and unit_name:
        return f"{trait_name} {unit_name}"
    return unit_name or trait_name or "Unknown"


def comp_tier(avg):
    if avg <= 4.20:
        return "S"
    if avg <= 4.35:
        return "A"
    if avg <= 4.50:
        return "B"
    return "C"


def top4_rate(places):
    """places = [1st, 2nd, 3rd, 4th, 5th, 6th, 7th, 8th, total]"""
    if len(places) < 9 or places[8] == 0:
        return None
    return sum(places[:4]) / places[8]


def format_comp(data_entry, stats_entry, item_lookup, trait_lookup, champion_traits):
    name = comp_name(data_entry.get("name", []), trait_lookup)
    overall = data_entry.get("overall", {})
    avg = overall.get("avg")
    count = overall.get("count", 0)

    units = parse_units(data_entry.get("units_string", ""))
    trait_counts = count_traits(units, champion_traits)
    traits = [f"{t} ({n})" for t, n in sorted(trait_counts.items(), key=lambda x: -x[1])]

    top4 = None
    if stats_entry:
        places = stats_entry.get("places", [])
        top4 = top4_rate(places)

    tier = comp_tier(avg) if avg is not None else "?"
    lines = [f"Comp: {name}", f"Tier: {tier}"]
    if avg is not None:
        lines.append(f"Average Placement: {avg:.2f}")
    if top4 is not None:
        lines.append(f"Top 4 Rate: {top4 * 100:.1f}%")
    lines.append(f"Games Sampled: {count:,}")
    lines.append(f"Units: {', '.join(units)}")
    if traits:
        lines.append(f"Traits: {', '.join(traits)}")

    builds = data_entry.get("builds", [])
    shown = 0
    for build in sorted(builds, key=lambda b: b.get("score", 0), reverse=True):
        if shown >= 3:
            break
        unit = unit_display(build.get("unit", ""))
        items = [item_display(i, item_lookup) for i in build.get("buildName", []) if i]
        if not items:
            continue
        build_avg = build.get("avg")
        avg_str = f" (avg {build_avg:.2f})" if build_avg else ""
        lines.append(f"{unit} build{avg_str}: {', '.join(items)}")
        shown += 1

    return "\n".join(lines)


def run():
    comps_data = load("metatft_comps_data.json")
    comps_stats = load("metatft_comps_stats.json")
    items_data = load("metatft_lookup_items.json")
    trait_map = load("metatft_lookup_traits.json")

    item_lookup = build_item_lookup(items_data)
    trait_lookup = build_trait_lookup(trait_map)
    champion_traits = load_champion_traits(CHAMPIONS_FILE)

    # Index stats by cluster ID
    stats_list = comps_stats.get("results", comps_stats)
    stats_by_cluster = {str(e.get("cluster", "")): e for e in stats_list if isinstance(e, dict)}

    results = comps_data.get("results", {})
    cluster_details = results.get("data", {}).get("cluster_details", {})
    games_by_cluster = results.get("games", {})

    # Attach game stats into each comp entry
    entries = []
    for cluster_id, entry in cluster_details.items():
        game_stats = games_by_cluster.get(str(cluster_id), [{}])
        stats = game_stats[0] if game_stats else {}
        entry["overall"] = stats
        entries.append(entry)

    # Filter and sort by average placement ascending (lower = better)
    valid = [
        e for e in entries
        if e.get("overall", {}).get("count", 0) >= MIN_GAMES
    ]
    valid.sort(key=lambda e: e.get("overall", {}).get("avg", 9))

    print(f"Writing {len(valid)} comps (filtered from {len(entries)} total)...")

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("# TFT Set 17 — Meta Comps\n")
        f.write("Comps sorted by average placement (lower is better). ")
        f.write("Data from high-elo games (Platinum+).\n\n")

        # Summary block — single chunk for ranking/comparison queries
        f.write("## Comp Rankings Summary\n")
        f.write("Use this to answer questions like 'best comps', 'top comps', 'strongest comps', or 'highest placement'.\n\n")
        for entry in valid:
            name = comp_name(entry.get("name", []), trait_lookup)
            avg = entry.get("overall", {}).get("avg")
            tier = comp_tier(avg) if avg is not None else "?"
            stats = stats_by_cluster.get(str(entry.get("Cluster", "")))
            top4 = top4_rate(stats.get("places", [])) if stats else None
            top4_str = f", Top 4: {top4 * 100:.1f}%" if top4 is not None else ""
            avg_str = f"{avg:.2f}" if avg is not None else "?"
            f.write(f"{tier} Tier — {name}: avg placement {avg_str}{top4_str}\n")

        f.write("\n---\n\n")

        for entry in valid:
            cluster = str(entry.get("Cluster", ""))
            stats = stats_by_cluster.get(cluster)
            block = format_comp(entry, stats, item_lookup, trait_lookup, champion_traits)
            f.write(block)
            f.write("\n\n---\n\n")

    print(f"Saved to {OUTPUT_FILE}")
    print("\n--- Preview (first 3 comps) ---")
    for entry in valid[:3]:
        stats = stats_by_cluster.get(str(entry.get("Cluster", "")))
        print(format_comp(entry, stats, item_lookup, trait_lookup, champion_traits))
        print()


if __name__ == "__main__":
    run()
