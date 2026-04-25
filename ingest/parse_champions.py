"""
Parse the raw 'New Champions' section from op.gg into clean, structured
champion records.

Input:  data/raw/opgg/new_champions.txt
Output: data/processed/champions.txt

Strategy: Use known traits as anchors. The line BEFORE the first trait of
each champion is the champion name, and the line right after that name is
the cost (1-5).
"""

import os
import re

INPUT_FILE = "data/raw/opgg/new_champions.txt"
OUTPUT_FILE = "data/processed/champions.txt"

KNOWN_TRAITS = {
    # Origins
    "Anima", "Arbiter", "Bulwark", "Dark Lady", "Dark Star", "Doomer",
    "Eradicator", "Factory New", "Mecha", "Meeple", "N.O.V.A.", "Oracle",
    "Primordian", "Psionic", "Redeemer", "Space Groove", "Stargazer",
    "Timebreaker", "Arcana",
    # Classes
    "Bastion", "Brawler", "Challenger", "Commander", "Conduit",
    "Divine Duelist", "Fateweaver", "Galaxy Hunter", "Gun Goddess",
    "Marauder", "Party Animal", "Replicator", "Rogue", "Shepherd",
    "Sniper", "Vanguard", "Voyager",
}

# Phrases that look like champion names but aren't
NOT_CHAMPIONS = {
    "Cost", "Origin Synergy", "Class Synergy", "New Champions",
    "Choose Trait",
}


def normalize_text(text):
    text = text.replace("\u2019", "'")
    text = text.replace("\u2018", "'")
    return text


def find_filter_end(lines):
    """
    The page starts with a filter UI listing all traits. We need to skip past it.
    The actual champion data begins after the LAST occurrence of a class synergy
    name in the filter (we use 'Voyager' as our anchor since it's typically last).
    """
    # find all positions of trait names appearing twice (filter + actual champion)
    # the filter section ends after we see the full list of class synergies
    last_voyager = -1
    for i, line in enumerate(lines):
        if line.strip() == "Voyager":
            last_voyager = i

    # the filter has Voyager listed once near the top
    # actual champion data starts right after that
    if last_voyager >= 0:
        # find the first occurrence (which is the filter)
        for i in range(last_voyager + 1):
            if lines[i].strip() == "Voyager":
                return i + 1
    return 0


def parse_champions(text):
    text = normalize_text(text)
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    # skip past the filter UI at the top
    start = find_filter_end(lines)
    lines = lines[start:]

    champions = []
    i = 0
    while i < len(lines):
        line = lines[i]

        # Look for the pattern: <champion name> -> <cost 1-5> -> <trait>
        # A champion name is anything that's NOT a trait/keyword and is followed
        # by a single-digit cost (1-5) and then a trait.
        if (line not in KNOWN_TRAITS
                and line not in NOT_CHAMPIONS
                and i + 2 < len(lines)
                and lines[i + 1] in {"1", "2", "3", "4", "5"}
                and (lines[i + 2] in KNOWN_TRAITS or lines[i + 2] == "Choose Trait")):

            name = line
            cost = lines[i + 1]
            i += 2

            # collect traits
            traits = []
            while i < len(lines) and (lines[i] in KNOWN_TRAITS or lines[i] == "Choose Trait"):
                if lines[i] != "Choose Trait":  # skip the 'Choose Trait' marker
                    traits.append(lines[i])
                i += 1

            # ability name = first non-trait line
            if i >= len(lines):
                break
            ability_name = lines[i]
            i += 1

            # ability type
            ability_type = ""
            mana = ""
            if i < len(lines) and lines[i] in {"Active", "Passive"}:
                ability_type = lines[i]
                i += 1

                # mana might be split: "30" "/" "90" or all on one line "30 / 90"
                if ability_type == "Active":
                    mana_parts = []
                    while i < len(lines) and re.match(r"^[\d\.\s/]+$", lines[i]):
                        mana_parts.append(lines[i])
                        i += 1
                    mana_str = "".join(mana_parts).replace(" ", "")
                    if "/" in mana_str:
                        parts = mana_str.split("/")
                        mana = f"{parts[0]} / {parts[1]}"
                    elif mana_str:
                        mana = mana_str

            # description = everything until the next champion starts
            desc_lines = []
            while i < len(lines):
                # next champion detection: current line is a candidate name
                # AND next line is a cost AND line after that is a trait
                if (i + 2 < len(lines)
                        and lines[i] not in KNOWN_TRAITS
                        and lines[i] not in NOT_CHAMPIONS
                        and lines[i + 1] in {"1", "2", "3", "4", "5"}
                        and (lines[i + 2] in KNOWN_TRAITS or lines[i + 2] == "Choose Trait")
                        # and the candidate looks like a name, not a stat
                        and not re.match(r"^[\d\.\s/\[\]\(\)%]+$", lines[i])
                        and len(lines[i]) < 30):
                    break
                desc_lines.append(lines[i])
                i += 1

            description = " ".join(desc_lines)
            description = re.sub(r"\s+", " ", description).strip()
            # tidy bracket spacing: "[ 300 / 375 / 575 ]" -> "[300/375/575]"
            description = re.sub(r"\[\s+", "[", description)
            description = re.sub(r"\s+\]", "]", description)
            description = re.sub(r"\s*/\s*", "/", description.replace("[", "[ ").replace("]", " ]"))
            description = re.sub(r"\(\s*\)", "", description).strip()
            description = re.sub(r"\s+", " ", description)

            champions.append({
                "name": name,
                "cost": cost,
                "traits": traits,
                "ability_name": ability_name,
                "ability_type": ability_type,
                "mana": mana,
                "description": description,
            })
        else:
            i += 1

    return champions


def format_champion(champ):
    lines = [
        f"Champion: {champ['name']}",
        f"Cost: {champ['cost']}",
        f"Traits: {', '.join(champ['traits']) if champ['traits'] else 'None'}",
        f"Ability: {champ['ability_name']}",
    ]
    if champ['ability_type']:
        lines.append(f"Type: {champ['ability_type']}")
    if champ['mana']:
        lines.append(f"Mana: {champ['mana']}")
    if champ['description']:
        lines.append(f"Description: {champ['description']}")
    return "\n".join(lines)


def run():
    if not os.path.exists(INPUT_FILE):
        print(f"Input file not found: {INPUT_FILE}")
        print("Run the OP.GG scraper first to generate it.")
        return

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        text = f.read()

    print(f"Parsing {INPUT_FILE}...")
    champions = parse_champions(text)
    print(f"Found {len(champions)} champions.\n")

    if champions:
        print("--- Preview (first 2 champions) ---")
        for c in champions[:2]:
            print(format_champion(c))
            print()

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for champ in champions:
            f.write(format_champion(champ))
            f.write("\n\n---\n\n")

    print(f"Saved structured champions to {OUTPUT_FILE}")


if __name__ == "__main__":
    run()