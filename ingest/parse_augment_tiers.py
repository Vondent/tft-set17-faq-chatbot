"""
Reads augments_tierlist.json and updates data/processed/augments.txt
with a "Tier Rating: S/A/B/C" line for each augment, sourced from the
"All" stage entries (overall meta ranking).

Existing Tier Rating lines are updated in-place; new ones are inserted
after the "Tier: N (Name)" line.

Run from the chatbot/ directory.
"""

import json
import os
import re

TIERLIST_PATH = os.path.join("data", "raw", "augments_tierlist.json")
AUGMENTS_PATH = os.path.join("data", "processed", "augments.txt")

# IDs that can't be auto-derived from camelCase splitting alone.
# Maps the ID suffix (after stripping TFT prefix) -> exact display name in augments.txt.
# Use None to explicitly skip IDs with no matching entry in the file.
MANUAL_MAPPING = {
    # Champion carry augments (display name is the champion's augment name)
    "NasusCarry": "Bonk!",
    "AatroxCarry": "Stellar Combo",
    "PoppyCarry": "Termeepnal Velocity",
    "PykeCarry": "Contract Killer",
    "JaxCarry": "Reach for the Stars",
    "IvernMinionCarry": None,  # not in file
    # Commander_ prefix augments
    "Commander_RollingForDays": "Rolling For Days I",
    "Commander_PartialAscension": "Partial Ascension",
    "Commander_TeamingUp1": "Teaming Up",
    "Commander_Ascension": "Ascension",
    # Renamed / non-obvious
    "AnimaSquad_Commander": "Anima Commander",
    "MagicRollMinus": "Slightly Magic Roll",
    "MagicRoll": "A Magic Roll",
    "GoodForSomethingSilver": "Good For Something I",
    "EarlyLearning": "Early Learnings",
    "GainGold": "Gain 21 Gold",
    "ArcaneViktory": "Arcane Viktor-y",
    "UltraRapidFire": "U.R.F",
    "NoScoutNoPivot": "NO SCOUT NO PIVOT",
    "Reinfourcement": "ReinFOURcement",
    "Buildabud": "Build a Bud",
    "MinMaxer": "Min-Max",
    "TinyButDeadly": "Tiny, but Deadly",
    "Calltochaos": "Call to Chaos",
    # Jeweled Lotus versions
    "JeweledLotus": "Jeweled Lotus I",
    "GreaterJeweledLotus": "Jeweled Lotus II",
    # Baron's Lair has an apostrophe
    "TheBaronsLair": "Baron's Lair",
    # Trait Tree
    "TraitTree": "The Trait Tree",
    "TraitTreePlus": "The Trait Tree+",
    # Worth the Wait variants
    "WorthTheWaitGold": "Worth the Wait",
    "WorthTheWaitPrismatic": "Worth the Wait II",
    # Band of Thieves variants (number suffix ≠ Roman numeral in name)
    "BandOfThieves1": "Band of Thieves",
    "BandOfThieves2": "Band of Thieves II",
    "BandOfThieves2Plus": "Band of Thieves II+",
    "BandOfThieves2PlusPlus": "Band of Thieves II++",
    # Slammin' has an apostrophe
    "Slammin": "Slammin'",
    "Slammin_Plus": "Slammin'+",
    # Tiniest Titan (Plus suffix is part of the ID, not the name)
    "TiniestTitanPlus": "Tiniest Titan",
    # Pandora's Items (apostrophe + number variant)
    "PandorasItems2": "Pandora's Items II",
    "PandorasBench": "Pandora's Bench",
    # Urf's (apostrophe)
    "UrfsGambit": "Urf's Gambit",
    "UrfsGrabBag2": "Urf's Grab Bag",
    # Bronze For Life (number → Roman numeral mismatch)
    "BronzeForLife2": "Bronze For Life II",
    # Exclusive Customization II
    "ExclusiveCustomization2": "Exclusive Customization II",
    # Display name differs slightly from derived form
    "BirthdayPresents": "Birthday Present",
    "CyberneticImplants2": "Cybernetic Implants",
    "Trifecta1": "Trifecta I",
    "Trifecta2": "Trifecta II",
    # IDs that use digit suffixes where the display name uses Roman numerals
    "BestFriends1": "Best Friends I",
    "BestFriends2": "Best Friends II",
    "ClimbTheLadder1": "Climb The Ladder I",
    "ClimbTheLadder2": "Climb The Ladder II",
    "MakeshiftArmor1": "Makeshift Armor I",
    "MakeshiftArmor2": "Makeshift Armor II",
    "Electrocharge1": "Electrocharge I",
    "Electrocharge2": "Electrocharge II",
    "SecondWind1": "Second Wind",
    "SecondWind2": "Second Wind II",
    "ChargeTransfer1": "Charge Transfer I",
    "ChargeTransfer2": "Charge Transfer II",
    "GroupHug1": "Group Hug I",
    "GroupHug2": "Group Hug II",
    "ItemGrabBag1": "Item Grab Bag",
    "OneTwosThree": "One Two Three",
    "HealingOrbsI": "Healing Orbs I",
    "HealingOrbsII": "Healing Orbs II",
    # Not present in the augments.txt file
    "ForceOfNature": None,
    "GachaAddict": None,
    "ThriftShop": None,
    "BuildingACollectionPlusPlus": None,
    "ArmyBuilding": None,
    "BardPlaybook1": None,
    "LongTimeCrafting": None,
    "Diversify1": None,
    "Waverider": None,
    "GuardbreakerSpirit": None,
    "Unforgotten": None,
    "HomeCooking": None,
    "FuriousBlows": None,
    "JustSlayer": None,
    "TheVidalion": None,
    "WarmogsBuckle": None,
    "MirroredMonetization": None,
    "Dhampyr1": None,
    "Dhampyr2": None,
    "TheDarkinBlade": None,
    "MarksMan": None,
    "Distancing": None,
    "ComponentQuestSword": None,
    "ComponentQuestTear": None,
    "ComponentQuestRod": None,
    "ComponentQuestBow": None,
    "ComponentQuestGlove": None,
    "BloodBank": None,
    "HyperRoll": None,
    "ForgeRod": None,
    "ForgeSword": None,
    "LearningFromExperience2": None,
    "RollTheDice": None,
    "AwakenedSoul": None,
    "PowerUp": None,
    "TradeSector2": None,
    "PandorasRadiantBox": None,
    "MuseumHeist": None,
    "TragicalBlade": None,
    "DeadlierCaps": "Deadlier Caps",
}


def extract_id_suffix(augment_id: str) -> str:
    match = re.match(r"TFT\d*_Augment_(.*)", augment_id)
    return match.group(1) if match else augment_id


def derive_display_name(id_suffix: str) -> str:
    """Auto-derive a display name from an ID suffix via camelCase splitting."""
    name = re.sub(r"PlusPlus$", "++", id_suffix)
    name = re.sub(r"Plus$", "+", name)
    name = name.replace("_", " ")
    name = re.sub(r"([a-z])([A-Z])", r"\1 \2", name)
    name = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", name)
    return name.strip()


def normalize(s: str) -> str:
    # Keep alphanumeric and '+' so "Branching Out" and "Branching Out+" stay distinct.
    return re.sub(r"[^a-z0-9+]", "", s.lower())


def build_tier_lookup(tierlist: list) -> dict:
    """Return {normalized_display_name: tier_rating} using 'All' stage entries only."""
    lookup = {}
    for entry in tierlist:
        if entry.get("stage") != "All":
            continue
        for tier_rating, augment_ids in entry.get("tier", {}).items():
            for augment_id in augment_ids:
                suffix = extract_id_suffix(augment_id)
                if suffix in MANUAL_MAPPING:
                    display = MANUAL_MAPPING[suffix]
                    if display is None:
                        continue
                else:
                    display = derive_display_name(suffix)
                lookup[normalize(display)] = tier_rating
    return lookup


def update_augments_file(augments_path: str, tier_lookup: dict):
    with open(augments_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    output = []
    matched, skipped = 0, []
    i = 0

    while i < len(lines):
        line = lines[i]
        output.append(line)

        if line.startswith("Augment: "):
            name = line[len("Augment: "):].strip()
            rating = tier_lookup.get(normalize(name))
            i += 1

            # Consume the Tier: line
            if i < len(lines) and lines[i].startswith("Tier: "):
                output.append(lines[i])
                i += 1

                # If a Tier Rating line already exists, update or remove it
                if i < len(lines) and lines[i].startswith("Tier Rating: "):
                    if rating:
                        output.append(f"Tier Rating: {rating}\n")
                        matched += 1
                    # If no rating found, drop the existing line (stale data)
                    i += 1
                    continue

                # Insert new Tier Rating line
                if rating:
                    output.append(f"Tier Rating: {rating}\n")
                    matched += 1
                else:
                    skipped.append(name)

            continue

        i += 1

    with open(augments_path, "w", encoding="utf-8") as f:
        f.writelines(output)

    print(f"Updated {matched} augments with tier ratings.")
    if skipped:
        print(f"\nNo tier data found for {len(skipped)} augments (not in current meta tier list):")
        for name in skipped:
            print(f"  - {name}")


def main():
    with open(TIERLIST_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    tierlist = data["augments_tierlists"]
    tier_lookup = build_tier_lookup(tierlist)
    print(f"Built tier lookup with {len(tier_lookup)} entries.")

    update_augments_file(AUGMENTS_PATH, tier_lookup)
    print("\nDone. augments.txt updated.")


if __name__ == "__main__":
    main()
