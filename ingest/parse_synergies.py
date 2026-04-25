"""
Parse raw class/origin synergy files from op.gg into clean, structured records.

Input:  data/raw/opgg/new_set_17_class_synergies.txt
        data/raw/opgg/new_set_17_origin_synergies.txt  (same format)
Output: data/processed/class_synergies.txt
        data/processed/origin_synergies.txt

The raw files are heavily fragmented — breakpoints split as ( N ) across three
lines, inline keywords (Lucky, Precision) on their own lines, trailing punctuation
as lone characters. This parser reassembles everything into readable records.
"""

import os
import re

JOBS = [
    (
        "data/raw/opgg/new_set_17_class_synergies.txt",
        "data/processed/class_synergies.txt",
        "Class",
    ),
    (
        "data/raw/opgg/new_set_17_origin_synergies.txt",
        "data/processed/origin_synergies.txt",
        "Origin",
    ),
]

# All known trait names — used as section anchors.
CLASS_TRAITS = {
    "Commander", "Divine Duelist", "Galaxy Hunter", "Gun Goddess", "Party Animal",
    "Bastion", "Brawler", "Challenger", "Conduit", "Fateweaver",
    "Marauder", "Replicator", "Rogue", "Shepherd", "Sniper", "Vanguard", "Voyager",
}

ORIGIN_TRAITS = {
    "Anima", "Arbiter", "Bulwark", "Dark Lady", "Dark Star", "Doomer",
    "Eradicator", "Factory New", "Mecha", "Meeple", "N.O.V.A.", "Oracle",
    "Primordian", "Psionic", "Redeemer", "Space Groove", "Stargazer",
    "Timebreaker", "Arcana",
}

# Lines that are lone punctuation or noise to drop
PUNCT_ONLY = re.compile(r"^[.,;]$")


def load_lines(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        raw = f.read().splitlines()

    # Skip the Source/Section header block
    start = 0
    for i, line in enumerate(raw):
        if line.startswith("Section:"):
            start = i + 2
            break

    return [l.strip() for l in raw[start:] if l.strip()]


def split_into_trait_blocks(lines, known_traits):
    """Return dict of {trait_name: [lines_in_block]}."""
    blocks = {}
    current = None
    for line in lines:
        if line in known_traits:
            current = line
            blocks[current] = []
        elif current is not None:
            blocks[current].append(line)
    return blocks


def parse_block(lines):
    """
    Parse one trait's lines into (description, breakpoints).
    breakpoints = list of (level, value_string)
    """
    # Reassemble fragmented lines: lone punctuation, inline keywords, and
    # continuation fragments (starting with |, ,, ;, +, or lowercase) get
    # merged into the previous line.
    merged = []
    for line in lines:
        if PUNCT_ONLY.match(line):
            # trailing period/comma — drop it
            continue
        if merged and (
            line.startswith("|")
            or line.startswith(",")
            or line.startswith(";")
            or line.startswith("+")
            or (line[0].islower() and not line.startswith("per"))
        ):
            # continuation of previous value
            sep = " " if not line.startswith(";") else ""
            merged[-1] = merged[-1] + sep + line
        elif merged and re.match(r"^[A-Z][a-z]+$", line) and not any(
            c.isdigit() for c in line
        ):
            # Single capitalized word with no digits (e.g. "Precision", "Lucky",
            # "Bia", "Bayin") — likely an inline keyword; append to previous line
            merged[-1] = merged[-1] + " " + line
        elif line == "per hex":
            if merged:
                merged[-1] = merged[-1] + " per hex"
        else:
            merged.append(line)

    # Now parse description (before first breakpoint) and breakpoints
    description_parts = []
    breakpoints = []
    i = 0

    while i < len(merged):
        line = merged[i]
        # Detect breakpoint: "(" alone
        if line == "(":
            if i + 2 < len(merged) and merged[i + 2] == ")":
                level = merged[i + 1]
                i += 3
                # Collect value lines until next breakpoint or end
                value_parts = []
                while i < len(merged) and merged[i] != "(":
                    value_parts.append(merged[i])
                    i += 1
                value = " ".join(value_parts).strip()
                # Clean up stray trailing period
                value = value.rstrip(".")
                breakpoints.append((level, value))
            else:
                i += 1
        else:
            description_parts.append(line)
            i += 1

    description = " ".join(description_parts).strip().rstrip(".")
    return description, breakpoints


def format_trait(name, trait_type, description, breakpoints):
    lines = [
        f"Trait: {name}",
        f"Type: {trait_type}",
        f"Description: {description}",
    ]
    if breakpoints:
        tiers = "/".join(b[0] for b in breakpoints)
        lines.append(f"Breakpoints: {tiers}")
        for level, value in breakpoints:
            lines.append(f"  ({level}): {value}")
    return "\n".join(lines)


def process_file(input_path, output_path, trait_type, known_traits):
    if not os.path.exists(input_path):
        print(f"Not found: {input_path} — skipping")
        return

    lines = load_lines(input_path)
    blocks = split_into_trait_blocks(lines, known_traits)

    print(f"Parsing {input_path}: found {len(blocks)} traits")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"# TFT Set 17 — {trait_type} Synergies\n\n")
        for name, block_lines in blocks.items():
            description, breakpoints = parse_block(block_lines)
            f.write(format_trait(name, trait_type, description, breakpoints))
            f.write("\n\n---\n\n")

    print(f"Saved to {output_path}")


def run():
    process_file(
        "data/raw/opgg/new_set_17_class_synergies.txt",
        "data/processed/class_synergies.txt",
        "Class",
        CLASS_TRAITS,
    )
    process_file(
        "data/raw/opgg/new_set_17_origin_synergies.txt",
        "data/processed/origin_synergies.txt",
        "Origin",
        ORIGIN_TRAITS,
    )


if __name__ == "__main__":
    run()