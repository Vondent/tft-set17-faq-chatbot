"""
Parse all Mobalytics item pages into a single comprehensive items.txt.

Uses explicit item name lists as anchors to avoid misidentifying description
fragments as item names (the Mobalytics pages inline numbers in <span> tags,
causing heavy fragmentation).

Run from the tft-faq-bot/ directory.
"""

import os
import re

OUTPUT_FILE = "data/processed/items.txt"
RAW_DIR = "data/raw/mobalytics/items"

TEMPLATE_RE = re.compile(r"\{\{[^}]+\}\}")

# ── Known item names by category ──────────────────────────────────────────────

COMPONENT_NAMES = [
    "B.F. Sword", "Chain Vest", "Frying Pan", "Giant's Belt",
    "Needlessly Large Rod", "Negatron Cloak", "Recurve Bow",
    "Sparring Gloves", "Spatula", "Tear of the Goddess",
]

COMBINED_NAMES = [
    "Adaptive Helm", "Archangel's Staff", "Bloodthirster", "Blue Buff",
    "Bramble Vest", "Crownguard", "Deathblade", "Dragon's Claw",
    "Edge of Night", "Evenshroud", "Gargoyle Stoneplate", "Giant Slayer",
    "Guinsoo's Rageblade", "Hand of Justice", "Hextech Gunblade",
    "Infinity Edge", "Ionic Spark", "Jeweled Gauntlet", "Kraken's Fury",
    "Last Whisper", "Morellonomicon", "Nashor's Tooth", "Protector's Vow",
    "Quicksilver", "Rabadon's Deathcap", "Red Buff", "Spear of Shojin",
    "Spirit Visage", "Steadfast Heart", "Sterak's Gage", "Striker's Flail",
    "Sunfire Cape", "Tactician's Cape", "Tactician's Crown", "Tactician's Shield",
    "Thief's Gloves", "Titan's Resolve", "Void Staff", "Warmog's Armor",
]

EMBLEM_NAMES = [
    "Arbiter Emblem", "Bastion Emblem", "Brawler Emblem", "Challenger Emblem",
    "Dark Star Emblem", "Marauder Emblem", "Meeple Emblem", "N.O.V.A. Emblem",
    "Primordian Emblem", "Rogue Emblem", "Shepherd Emblem", "Space Groove Emblem",
    "Stargazer Emblem", "Timebreaker Emblem", "Vanguard Emblem", "Voyager Emblem",
]

PSIONIC_NAMES = [
    "Biomatter Preserver", "Drone Uplink", "Malware Matrix",
    "Sympathetic Implant", "Target-Lock Optics",
]

ANIMA_NAMES = [
    "Animapocalypse", "Battle Bunny Crossbow", "Broken Prototype",
    "Bunny Prime Ballista", "Cyclonic Slicers", "Deep Freeze",
    "Echoing Batblades", "Evolved Embershot", "Guiding Hex",
    "Iceblast Armor", "Leaky Prototype", "Leonine Lamentation",
    "Lioness's Lament", "Omniweapon", "OwO Blaster", "Radiant Field",
    "Rocket Swarm", "Savage Slicer", "Searing Shortbow", "Solar Eclipse",
    "Sparking Prototype", "Tentacle Slam", "The Annihilator",
    "Unceasing Cyclone", "UwU Blaster", "Vayne's Chromablades",
]

RADIANT_NAMES = [
    "Radiant Adaptive Helm", "Radiant Archangel's Staff", "Radiant Bloodthirster",
    "Radiant Blue Buff", "Radiant Bramble Vest", "Radiant Crownguard",
    "Radiant Deathblade", "Radiant Dragon's Claw", "Radiant Edge of Night",
    "Radiant Evenshroud", "Radiant Gargoyle's Stoneplate", "Radiant Giant Slayer",
    "Radiant Guinsoo's Rageblade", "Radiant Hand of Justice",
    "Radiant Hextech Gunblade", "Radiant Infinity Edge", "Radiant Ionic Spark",
    "Radiant Jeweled Gauntlet", "Radiant Kraken's Fury", "Radiant Last Whisper",
    "Radiant Morellonomicon", "Radiant Nashor's Tooth", "Radiant Protector's Vow",
    "Radiant Quicksilver", "Radiant Rabadon's Deathcap", "Radiant Red Buff",
    "Radiant Spear of Shojin", "Radiant Spirit Visage", "Radiant Steadfast Heart",
    "Radiant Sterak's Gage", "Radiant Striker's Flail", "Radiant Sunfire Cape",
    "Radiant Thiefs Gloves", "Radiant Titan's Resolve", "Radiant Void Staff",
    "Radiant Warmog's Armor",
]

ARTIFACT_NAMES = [
    "Aegis of Dawn", "Aegis of Dusk", "Ahri's Aura", "Blighting Jewel",
    "Cappa Juice", "Dawncore", "Deathfire Grasp", "Death's Defiance",
    "Ekko's Patience", "Eternal Pact", "Evelynn's Instinct", "Fishbones",
    "Flickerblade", "Gambler's Blade", "Gold Collector", "Hellfire Hatchet",
    "Horizon Focus", "Hullcrusher", "Indomitable Gauntlet", "Infinity Force",
    "Innervating Locket", "Kayle's Exaltation", "Kayle's Radiant Exaltation",
    "Lesser Mirrored Persona", "Lich Bane", "Lightshield Crest",
    "Luden's Tempest", "Manazane", "Mending Echoes", "Mirrored Persona",
    "Mittens", "Mogul's Mail", "Prowler's Claw", "Rapid Firecannon",
    "Seeker's Armguard", "Shadow Puppet", "Silvermere Dawn", "Sniper's Focus",
    "Soraka's Miracle", "Spectral Cutlass", "Statikk Shiv",
    "Suspicious Trench Coat", "Talisman Of Ascension", "The Darkin Aegis",
    "The Darkin Bow", "The Darkin Scythe", "The Darkin Staff",
    "Thresh's Lantern", "Titanic Hydra", "Trickster's Glass",
    "Unending Despair", "Varus's Obsession", "Void Gauntlet",
    "Wit's End", "Yasuo's Bladework", "Zhonya's Paradox",
]

ELUSIVE_NAMES = [
    "Anima Tech Emblem", "Anomaly", "Crown of Demacia",
    "Psionic Emblem", "Sniper Emblem",
]

CONSUMABLE_NAMES = [
    "Champion Duplicator", "Lesser Champion Duplicator",
    "Magnetic Remover", "Reforger",
]

PSIONIC_AT4 = {
    "Drone Uplink":        "If the holder is Psionic, gain an additional mini-drone that repeats 20% of damage.",
    "Malware Matrix":      "If the holder is Psionic, every 3rd attack cleaves, dealing 75 physical damage to nearby enemies.",
    "Biomatter Preserver": "If the holder is Psionic, they gain 22% increased healing from all sources.",
    "Sympathetic Implant": "If the holder is Psionic, their abilities deal 20% of their ability damage as true damage instead.",
    "Target-Lock Optics":  "If the holder is Psionic, they heal 12% of their max Health whenever their target dies.",
}

COMMAND_MODS = [
    ("Command Mod: Exhaust",     "Command a unit's attacks to Burn, Wound, and Chill."),
    ("Command Mod: Doublestrike","Command a unit to have a 25% chance to attack twice when attacking."),
    ("Command Mod: Analyze",     "Command a unit to grant you 1 XP every 3 seconds it is alive during player combat."),
    ("Command Mod: Brace",       "Command a unit to gain a 20% Health shield for 8 seconds at the start of combat."),
    ("Command Mod: Transmute",   "Command a unit to drop 2 gold each time it kills an enemy during player combat."),
    ("Command Mod: Disrupt",     "Command a unit to Stun enemies within 3 hexes for 1 second when it dies."),
    ("Command Mod: Optimize",    "Command a unit to reduce their mana cost by 15%."),
    ("Command Mod: Fabricate",   "Command a unit to gain a temporary recommended item at the start of combat."),
]

COMPONENT_STATS = {
    "B.F. Sword":           "+10% Attack Damage",
    "Chain Vest":           "+20 Armor",
    "Frying Pan":           "...why else would it be here?",
    "Giant's Belt":         "+150 Health",
    "Needlessly Large Rod": "+10 Ability Power",
    "Negatron Cloak":       "+20 Magic Resist",
    "Recurve Bow":          "+10% Attack Speed",
    "Sparring Gloves":      "+20 Critical Strike Chance",
    "Spatula":              "It must do something...",
    "Tear of the Goddess":  "+1 Mana Regen",
}


def load_lines(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        lines = [l.strip() for l in f.readlines()]
    start = 0
    for i, line in enumerate(lines):
        if line.startswith("Category:"):
            start = i + 1
            break
    return lines[start:]


def extract_items(lines, known_names, all_boundaries=None):
    """Split raw lines into {name: [desc_lines]} using known_names as anchors.
    all_boundaries extends the stop-set so adjacent sections don't bleed in."""
    name_set = set(known_names)
    stop_set = name_set | set(all_boundaries or [])
    items = {name: [] for name in known_names}
    current = None
    for line in lines:
        if line in stop_set:
            current = line if line in name_set else None
        elif current is not None and line:
            items[current].append(line)
    return items


def reconstruct(lines):
    """Merge number fragments back into surrounding description text."""
    out = ""
    for i, line in enumerate(lines):
        line = TEMPLATE_RE.sub("", line).strip()
        if not line:
            continue

        is_num = bool(re.match(r'^-?[\d.]+$', line))
        starts_pct = line.startswith('%')

        starts_ordinal = line[:3] in ("rd ", "st ", "nd ", "th ") or line in ("rd", "st", "nd", "th")

        if is_num:
            # Always space before the number; the % handler below removes the
            # space between the number and any following % unit.
            out = out.rstrip() + " " + line
        elif starts_pct:
            out = out.rstrip() + line
        elif starts_ordinal:
            out = out.rstrip() + line
        elif line[0].islower():
            out = out.rstrip() + " " + line
        else:
            out = (out + " " + line).lstrip() if out else line

    # Clean up
    out = re.sub(r" {2,}", " ", out)
    # Remove trailing stat-tracker fragments
    out = re.sub(
        r"\s*(Gold (?:generated|dropped|collected) this game:|Ally Healing:|"
        r"Gold Collected:.*|Hats:.*|Damage increases based on Stage\.?|"
        r"Unique - only \d+ per champion|Can't be Reforged.*|"
        r"Traits of champions.*)\s*",
        " ", out
    )
    out = re.sub(r" {2,}", " ", out).strip()
    return out


def fmt(name, category, description, extra=None):
    lines = [
        f"Item: {name}",
        f"Category: {category}",
        f"Description: {description}",
    ]
    if extra:
        lines.append(extra)
    return "\n".join(lines)


def run():
    all_lines = {}
    for slug in ["components", "combined", "psionic", "anima_squad",
                 "radiant", "artifacts", "elusive", "consumables"]:
        path = os.path.join(RAW_DIR, f"{slug}.txt")
        if os.path.exists(path):
            all_lines[slug] = load_lines(path)
        else:
            print(f"  Missing: {path}")
            all_lines[slug] = []

    combined_lines = all_lines["combined"]
    all_combined = COMBINED_NAMES + EMBLEM_NAMES  # shared boundary set

    parsed = {
        "component":   extract_items(all_lines["components"],  COMPONENT_NAMES),
        "combined":    extract_items(combined_lines, COMBINED_NAMES, all_combined),
        "emblem":      extract_items(combined_lines, EMBLEM_NAMES,   all_combined),
        "psionic":     extract_items(all_lines["psionic"],      PSIONIC_NAMES),
        "anima":       extract_items(all_lines["anima_squad"],  ANIMA_NAMES),
        "radiant":     extract_items(all_lines["radiant"],      RADIANT_NAMES),
        "artifact":    extract_items(all_lines["artifacts"],    ARTIFACT_NAMES),
        "elusive":     extract_items(all_lines["elusive"],      ELUSIVE_NAMES),
        "consumable":  extract_items(all_lines["consumables"],  CONSUMABLE_NAMES),
    }

    for cat, items in parsed.items():
        print(f"  {cat}: {sum(1 for v in items.values() if v or True)} items")

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("# TFT Set 17 — Items\n\n")

        f.write("## Component Items\n\n")
        for name in COMPONENT_NAMES:
            stat = COMPONENT_STATS.get(name, "")
            f.write(fmt(name, "Component", stat))
            f.write("\n\n---\n\n")

        f.write("## Combined Items\n\n")
        for name in COMBINED_NAMES:
            desc = reconstruct(parsed["combined"].get(name, []))
            f.write(fmt(name, "Combined", desc))
            f.write("\n\n---\n\n")

        f.write("## Emblem Items\n")
        f.write("Each emblem grants the holder its corresponding trait.\n\n")
        for name in EMBLEM_NAMES:
            desc = reconstruct(parsed["emblem"].get(name, []))
            trait = name.replace(" Emblem", "")
            f.write(fmt(name, "Emblem", desc))
            f.write(f"\nGrants Trait: {trait}")
            f.write("\n\n---\n\n")

        f.write("## Psionic Items\n")
        f.write("Equippable by any ally. Holders with 4 Psionic units unlock the At (4) bonus.\n\n")
        for name in PSIONIC_NAMES:
            desc = reconstruct(parsed["psionic"].get(name, []))
            at4 = PSIONIC_AT4.get(name, "")
            extra = f"At (4) Bonus: {at4}" if at4 else None
            f.write(fmt(name, "Psionic", desc, extra))
            f.write("\n\n---\n\n")

        f.write("## Anima Squad Items\n")
        f.write("Special items associated with the Anima trait.\n\n")
        for name in ANIMA_NAMES:
            desc = reconstruct(parsed["anima"].get(name, []))
            f.write(fmt(name, "Anima Squad", desc))
            f.write("\n\n---\n\n")

        f.write("## Radiant Items\n")
        f.write("Upgraded versions of Combined items.\n\n")
        for name in RADIANT_NAMES:
            desc = reconstruct(parsed["radiant"].get(name, []))
            f.write(fmt(name, "Radiant", desc))
            f.write("\n\n---\n\n")

        f.write("## Artifacts\n")
        f.write("Obtainable via Portable Forge, Apotheotic Forge, or Forged in Strength augments.\n\n")
        for name in ARTIFACT_NAMES:
            desc = reconstruct(parsed["artifact"].get(name, []))
            f.write(fmt(name, "Artifact", desc))
            f.write("\n\n---\n\n")

        f.write("## Elusive / Non-Craftable Items\n\n")
        for name in ELUSIVE_NAMES:
            desc = reconstruct(parsed["elusive"].get(name, []))
            f.write(fmt(name, "Elusive", desc))
            f.write("\n\n---\n\n")

        f.write("## Consumables\n\n")
        for name in CONSUMABLE_NAMES:
            desc = reconstruct(parsed["consumable"].get(name, []))
            f.write(fmt(name, "Consumable", desc))
            f.write("\n\n---\n\n")

        f.write("## Command Mods (Commander Trait)\n")
        f.write("Sona grants a random Command Mod every 2 rounds. Mods last 2 player combats even if unequipped.\n\n")
        for name, desc in COMMAND_MODS:
            f.write(fmt(name, "Command Mod", desc))
            f.write("\n\n---\n\n")

    print(f"\nSaved to {OUTPUT_FILE}")


if __name__ == "__main__":
    run()