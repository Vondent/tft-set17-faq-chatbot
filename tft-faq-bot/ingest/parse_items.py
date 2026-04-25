"""
Parse the raw 'New Items' section from op.gg into clean, structured records.

Input:  data/raw/opgg/new_items.txt
Output: data/processed/items.txt

Three categories:
  - Psionic items  — equippable by any ally, bonus at 4 Psionic units
  - Command Mods   — granted by Sona (Commander trait) every 2 rounds
  - Emblems        — grant the holder a trait
"""

import os

INPUT_FILE = "data/raw/opgg/new_items.txt"
OUTPUT_FILE = "data/processed/items.txt"

SECTION_MARKERS = {"Psionic", "Commander", "Emblems"}
NOISE_CUTOFF = "New Arenas"

SKIP_LINES = {
    "New Items",
    "Gain Psionic items that can be equipped to any ally.",
    "Build around new origin and class emblems to open up more combinations.",
}


def load_lines(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        raw = f.read().splitlines()

    # Skip the source/section header block at the top
    start = 0
    for i, line in enumerate(raw):
        if line.startswith("Section:"):
            start = i + 2
            break

    lines = []
    for line in raw[start:]:
        if line.strip() == NOISE_CUTOFF:
            break
        lines.append(line.strip())

    return [l for l in lines if l]  # drop blank lines


def split_sections(lines):
    sections = {"Psionic": [], "Commander": [], "Emblems": []}
    current = None
    for line in lines:
        if line in SECTION_MARKERS:
            current = line
            continue
        if current:
            sections[current].append(line)
    return sections


def parse_psionic(lines):
    items = []
    i = 0
    while i < len(lines):
        line = lines[i]

        # Skip count lines ("5 items") and known boilerplate
        if line in SKIP_LINES or (line[0].isdigit() and line.endswith("items")):
            i += 1
            continue

        # A Psionic item name is any line that isn't a description marker
        if not line.startswith("At (4):") and line != "Recommended users:":
            name = line
            i += 1
            desc_parts = []
            at4 = ""
            recommended = ""

            while i < len(lines):
                l = lines[i]
                if l in SKIP_LINES or (l[0].isdigit() and l.endswith("items")):
                    i += 1
                    continue
                if l.startswith("At (4):"):
                    at4 = l[len("At (4): "):]
                    i += 1
                elif l == "Recommended users:":
                    i += 1
                    if i < len(lines):
                        recommended = lines[i]
                        i += 1
                    break
                elif not l.startswith("At (4):"):
                    desc_parts.append(l)
                    i += 1
                else:
                    break

            items.append({
                "name": name,
                "description": " ".join(desc_parts),
                "at4_bonus": at4,
                "recommended": recommended,
            })
        else:
            i += 1

    return items


def parse_command_mods(lines):
    items = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("Command Mod:"):
            name = line
            desc = lines[i + 1] if i + 1 < len(lines) else ""
            items.append({"name": name, "description": desc})
            i += 2
        else:
            i += 1
    return items


def parse_emblems(lines):
    items = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.endswith("Emblem"):
            name = line
            desc = lines[i + 1] if i + 1 < len(lines) else ""
            trait = name[: -len(" Emblem")]
            items.append({"name": name, "trait": trait, "description": desc})
            i += 2
        else:
            i += 1
    return items


def format_psionic(item):
    lines = [
        f"Item: {item['name']}",
        f"Category: Psionic",
        f"Effect: {item['description']}",
    ]
    if item["at4_bonus"]:
        lines.append(f"At (4) Bonus: {item['at4_bonus']}")
    if item["recommended"]:
        lines.append(f"Recommended: {item['recommended']}")
    return "\n".join(lines)


def format_command_mod(item):
    return "\n".join([
        f"Item: {item['name']}",
        f"Category: Commander",
        f"Effect: {item['description']}",
    ])


def format_emblem(item):
    return "\n".join([
        f"Item: {item['name']}",
        f"Category: Emblem",
        f"Grants Trait: {item['trait']}",
        f"Effect: {item['description']}",
    ])


def run():
    if not os.path.exists(INPUT_FILE):
        print(f"Input file not found: {INPUT_FILE}")
        print("Run the OP.GG scraper first to generate it.")
        return

    lines = load_lines(INPUT_FILE)
    sections = split_sections(lines)

    psionic_items = parse_psionic(sections["Psionic"])
    command_mods = parse_command_mods(sections["Commander"])
    emblems = parse_emblems(sections["Emblems"])

    print(f"Parsed: {len(psionic_items)} Psionic items, "
          f"{len(command_mods)} Command Mods, "
          f"{len(emblems)} Emblems")

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("# TFT Set 17 — New Items\n\n")

        f.write("## Psionic Items\n")
        f.write("Equippable by any ally. Holders with 4 Psionic units unlock the At (4) bonus.\n\n")
        for item in psionic_items:
            f.write(format_psionic(item))
            f.write("\n\n---\n\n")

        f.write("## Command Mods (Commander Trait)\n")
        f.write("Sona grants a random Command Mod every 2 rounds. Mods last 2 player combats even if unequipped.\n\n")
        for item in command_mods:
            f.write(format_command_mod(item))
            f.write("\n\n---\n\n")

        f.write("## Emblems\n")
        f.write("Each emblem grants the holder its corresponding trait.\n\n")
        for item in emblems:
            f.write(format_emblem(item))
            f.write("\n\n---\n\n")

    print(f"Saved to {OUTPUT_FILE}")

    print("\n--- Preview ---")
    if psionic_items:
        print(format_psionic(psionic_items[0]))
        print()
    if command_mods:
        print(format_command_mod(command_mods[0]))
        print()
    if emblems:
        print(format_emblem(emblems[0]))


if __name__ == "__main__":
    run()