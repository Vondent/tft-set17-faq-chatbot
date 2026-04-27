"""
Reads items_tierlist.json and updates data/processed/items.txt
with a "Tier Rating: S/A/B/C" line for each item after its Description.

Covers craftables, radiants, and artifact (ornn) types.
Later entries in the JSON overwrite earlier ones (most recent wins).

Run from the chatbot/ directory.
"""

import json
import os
import re

TIERLIST_PATH = os.path.join("data", "raw", "items_tierlist.json")
ITEMS_PATH = os.path.join("data", "processed", "items.txt")

# Maps full item ID -> display name in items.txt, or None to skip.
# Only needed for IDs where camelCase auto-derivation fails.
MANUAL_MAPPING = {
    # Emblem IDs that don't match the Set 17 emblem names — skip them.
    "TFT17_Item_SummonTraitEmblemItem": None,
    "TFT17_Item_FlexTraitEmblemItem":   None,
    "TFT17_Item_DRXEmblemItem":         None,
    "TFT17_Item_PulsefireEmblemItem":   None,
}


def camel_split(s):
    s = re.sub(r"([a-z])([A-Z])", r"\1 \2", s)
    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", s)
    return s.strip()


def derive_display_name(item_id):
    # Artifact items: TFT_Item_Artifact_X
    m = re.match(r"TFT\d*_Item_Artifact_(.*)", item_id)
    if m:
        return camel_split(m.group(1))

    # Emblem items: TFT_Item_XEmblemItem
    m = re.match(r"TFT\d*_Item_(.+?)EmblemItem", item_id)
    if m:
        return camel_split(m.group(1)) + " Emblem"

    # Generic: TFT_Item_X or TFT5_Item_X etc.
    m = re.match(r"TFT\d*_Item_(.*)", item_id)
    if m:
        suffix = m.group(1)
        if suffix.endswith("Radiant"):
            base = suffix[: -len("Radiant")]
            return "Radiant " + camel_split(base)
        return camel_split(suffix)

    return None


def normalize(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def build_tier_lookup(tierlist):
    """Return {normalized_display_name: tier_rating}. Later entries overwrite earlier."""
    lookup = {}
    for entry in tierlist:
        for tier_rating, item_ids in entry.get("tier", {}).items():
            for item_id in item_ids:
                if item_id in MANUAL_MAPPING:
                    display = MANUAL_MAPPING[item_id]
                    if display is None:
                        continue
                else:
                    display = derive_display_name(item_id)
                    if display is None:
                        continue
                lookup[normalize(display)] = tier_rating
    return lookup


def update_items_file(items_path, tier_lookup):
    with open(items_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    output = []
    matched, skipped = 0, []
    current_item = None
    i = 0

    while i < len(lines):
        line = lines[i]
        output.append(line)

        if line.startswith("Item: "):
            current_item = line[len("Item: "):].strip()
            i += 1
            continue

        if line.startswith("Description: ") and current_item:
            rating = tier_lookup.get(normalize(current_item))
            i += 1

            # If a Tier Rating line already exists, update or drop it
            if i < len(lines) and lines[i].startswith("Tier Rating: "):
                if rating:
                    output.append(f"Tier Rating: {rating}\n")
                    matched += 1
                i += 1
                current_item = None
                continue

            # Insert new Tier Rating line
            if rating:
                output.append(f"Tier Rating: {rating}\n")
                matched += 1
            else:
                skipped.append(current_item)
            current_item = None
            continue

        i += 1

    with open(items_path, "w", encoding="utf-8") as f:
        f.writelines(output)

    print(f"Updated {matched} items with tier ratings.")
    if skipped:
        print(f"\nNo tier data for {len(skipped)} items (not in current meta tier list):")
        for name in skipped:
            print(f"  - {name}")


def main():
    with open(TIERLIST_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    tierlist = data["items_tierlists"]
    tier_lookup = build_tier_lookup(tierlist)
    print(f"Built tier lookup with {len(tier_lookup)} entries.")

    update_items_file(ITEMS_PATH, tier_lookup)
    print("\nDone. items.txt updated.")


if __name__ == "__main__":
    main()
