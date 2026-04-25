"""
Parse raw TFT patch note files into clean, structured change logs.
Cross-references champion changes against the baseline champions.txt.

Input:   data/raw/Teamfight_Tactics_patch_*.txt
Output:  data/processed/patch_<version>.txt

Run from the tft-faq-bot/ directory.
Usage:   python ingest/parse_patch_notes.py [patch_file]
         (omit argument to process all patch files in data/raw/)
"""

import os
import re
import glob
import sys

CHAMPIONS_FILE = "data/processed/champions.txt"
RAW_DIR = "data/raw"
OUTPUT_DIR = "data/processed"

SECTION_MAP = {
    "AUGMENTS": "Augments — Removed",
    "TRAITS": "Trait Changes",
    "CHAMPIONS": "Champion Changes",
    "EMBLEMS": "Emblem Changes",
    "BUG FIXES": "Bug Fixes",
    "AUGMENT CYCLING: REMOVED": "Augments — Cycling Removed",
    "RETURNING AUGMENTS": "Returning Augments",
    "AUGMENTS ADJUSTED: SILVER": "Augments Adjusted — Silver",
    "AUGMENTS ADJUSTED: GOLD": "Augments Adjusted — Gold",
    "AUGMENTS ADJUSTED: PRISMATIC": "Augments Adjusted — Prismatic",
    "ITEMS": "Item Changes",
    "RADIANT ITEMS": "Radiant Item Changes",
    "NEW ARTIFACTS": "New Artifacts",
    "ADJUSTED ARTIFACTS": "Artifact Changes",
}


def load_champion_baseline(filepath):
    """Build a lookup dict: champion_name -> {cost, traits, ability}."""
    if not os.path.exists(filepath):
        return {}

    baseline = {}
    current = {}
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("Champion:"):
                current = {"name": line[len("Champion:"):].strip()}
            elif line.startswith("Cost:") and current:
                current["cost"] = line[len("Cost:"):].strip()
            elif line.startswith("Traits:") and current:
                current["traits"] = line[len("Traits:"):].strip()
            elif line.startswith("Ability:") and current:
                current["ability"] = line[len("Ability:"):].strip()
            elif line == "---" and current.get("name"):
                baseline[current["name"].lower()] = current
                current = {}
    return baseline


def rejoin_split_arrows(lines):
    """
    The scraper emits a lone '⇒' line when a stat change spans multiple HTML
    elements.  Only rejoin if the following line looks like a numeric
    continuation (new stat value) — not a new item/champion/augment name.
    Drop orphan arrows where the new value was filtered out by the scraper.
    """
    result = []
    i = 0
    while i < len(lines):
        if lines[i].strip() == "⇒":
            if result and i + 1 < len(lines):
                nxt = lines[i + 1].strip()
                # Join only if next line starts with a digit, %, or lowercase
                # (i.e. it's a continuation value, not a new entry name)
                if nxt and (nxt[0].isdigit() or nxt[0] == "%" or nxt[0].islower()):
                    prev = result.pop()
                    result.append(f"{prev} ⇒ {nxt}")
                    i += 2
                    continue
            # Orphan arrow — drop it
            i += 1
        else:
            result.append(lines[i])
            i += 1
    return result


def classify_change(line):
    """Return (BUFF|NERF|REMOVED|REWORKED|FIXED|neutral) for a change line."""
    if "Removed" in line:
        return "REMOVED"
    if "REWORKED" in line or "Reworked" in line:
        return "REWORKED"
    if line.strip().startswith("Fixed"):
        return "FIXED"
    if "⇒" not in line:
        return ""

    # Extract old and new numeric values and compare
    parts = line.split("⇒")
    if len(parts) != 2:
        return ""

    old_nums = re.findall(r"[\d.]+", parts[0])
    new_nums = re.findall(r"[\d.]+", parts[1])

    if not old_nums or not new_nums:
        return ""

    # Compare first numeric value as a heuristic
    try:
        old_val = float(old_nums[-1])
        new_val = float(new_nums[0])
        if new_val > old_val:
            return "BUFF"
        if new_val < old_val:
            return "NERF"
    except ValueError:
        pass
    return ""


def parse_raw_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        lines = [l.rstrip() for l in f.readlines()]

    # Extract metadata
    url = ""
    title = ""
    for line in lines[:5]:
        if line.startswith("URL:"):
            url = line[4:].strip()
        elif line.startswith("Title:"):
            title = line[6:].strip()

    # Strip header
    content_lines = [l for l in lines if not l.startswith("URL:") and not l.startswith("Title:")]
    content_lines = rejoin_split_arrows(content_lines)

    # Split into sections
    sections = {}
    current_section = None
    for line in content_lines:
        stripped = line.strip()
        if stripped.startswith("## "):
            section_key = stripped[3:].strip()
            current_section = section_key
            sections[current_section] = []
        elif current_section is not None and stripped:
            sections[current_section].append(stripped)

    return url, title, sections


def format_change_line(line, baseline, section_key):
    tag = classify_change(line)
    tag_str = f" [{tag}]" if tag else ""

    # For champion section, prepend context from baseline
    if section_key == "CHAMPIONS":
        # Try to match champion name at start of line
        for name, data in baseline.items():
            display = data["name"]
            if line.lower().startswith(name):
                traits = data.get("traits", "")
                cost = data.get("cost", "")
                context = f"  Cost {cost} — {traits}" if cost and traits else ""
                return f"- {line}{tag_str}{context}"
    return f"- {line}{tag_str}"


def write_processed(url, title, sections, baseline, output_path):
    # Extract version from title e.g. "Teamfight Tactics patch 17.1"
    version_match = re.search(r"(\d+\.\d+)", title)
    version = version_match.group(1) if version_match else "unknown"

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"# TFT Patch {version} — Balance Changes\n")
        f.write(f"Source: {url}\n\n")

        for raw_key, display_name in SECTION_MAP.items():
            entries = sections.get(raw_key, [])
            if not entries:
                continue

            f.write(f"## {display_name}\n\n")
            for line in entries:
                f.write(format_change_line(line, baseline, raw_key))
                f.write("\n")
            f.write("\n")


def process_file(filepath, baseline):
    url, title, sections = parse_raw_file(filepath)

    version_match = re.search(r"(\d+[._]\d+)", os.path.basename(filepath))
    version = version_match.group(1).replace("_", ".") if version_match else "unknown"

    output_path = os.path.join(OUTPUT_DIR, f"patch_{version}.txt")
    write_processed(url, title, sections, baseline, output_path)
    print(f"Processed: {filepath} -> {output_path}")
    return output_path


def run():
    baseline = load_champion_baseline(CHAMPIONS_FILE)
    print(f"Loaded {len(baseline)} champions from baseline\n")

    if len(sys.argv) > 1:
        files = [sys.argv[1]]
    else:
        files = sorted(glob.glob(os.path.join(RAW_DIR, "Teamfight_Tactics_patch_*.txt")))

    if not files:
        print(f"No patch files found in {RAW_DIR}/")
        return

    for filepath in files:
        process_file(filepath, baseline)


if __name__ == "__main__":
    run()