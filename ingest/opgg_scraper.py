"""
Scrapes op.gg/tft/set/17 for set-wide reference data:
- Gods (Set 17 mechanic)
- Origin synergies
- Class synergies
- Unique synergies
- Champions
- Augments
- Items

Saves each section as a separate .txt file so they can be embedded independently.
"""

import os
import re
import time
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

OUTPUT_DIR = "data/raw/opgg"
URL = "https://op.gg/tft/set/17"

# Section headers we expect on the page — used for splitting content
SECTION_HEADERS = [
    "TFT 17 GODS",
    "New Set 17 Origin Synergies",
    "New Set 17 Class Synergies",
    "New Set 17 Unique Synergies",
    "New Champions",
    "New Augments",
    "New Items",
]


def clean_text(text):
    """Collapse whitespace and strip blank lines."""
    # remove runs of 3+ newlines
    text = re.sub(r"\n{3,}", "\n\n", text)
    # remove trailing whitespace on each line
    lines = [line.rstrip() for line in text.splitlines()]
    # drop empty leading/trailing lines, keep single empties between paragraphs
    cleaned = "\n".join(lines).strip()
    return cleaned


def sanitize_filename(name):
    """Make a section name safe for a filename."""
    name = name.replace(" ", "_")
    name = re.sub(r"[^A-Za-z0-9_\-]", "", name)
    return name.lower()


def split_into_sections(full_text):
    """
    Split the full page text into sections based on known headers.
    Returns a dict: {section_name: section_text}.
    """
    sections = {}

    # Find positions of each header in the text
    positions = []
    for header in SECTION_HEADERS:
        idx = full_text.find(header)
        if idx != -1:
            positions.append((idx, header))

    positions.sort()

    if not positions:
        return {"full_page": full_text}

    # Slice the text between header positions
    for i, (start, header) in enumerate(positions):
        end = positions[i + 1][0] if i + 1 < len(positions) else len(full_text)
        section_text = full_text[start:end].strip()
        sections[header] = section_text

    return sections


def scrape_opgg(page, url):
    """Load the page and extract its text content."""
    print(f"Loading {url}...")

    try:
        page.goto(url, wait_until="networkidle", timeout=45000)
    except Exception as e:
        print(f"  Initial load slow, continuing anyway: {e}")

    # The page is long and lazy-loads sections as you scroll.
    # Scroll to the bottom in chunks to force everything to render.
    print("  Scrolling to load all content...")
    page.evaluate("""
        async () => {
            await new Promise((resolve) => {
                let totalHeight = 0;
                const distance = 600;
                const timer = setInterval(() => {
                    const scrollHeight = document.body.scrollHeight;
                    window.scrollBy(0, distance);
                    totalHeight += distance;
                    if (totalHeight >= scrollHeight) {
                        clearInterval(timer);
                        resolve();
                    }
                }, 250);
            });
        }
    """)
    page.wait_for_timeout(3000)  # let final content settle

    html = page.content()
    soup = BeautifulSoup(html, "html.parser")

    # Strip noise
    for tag in soup.find_all(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    # Grab the main content area
    main = soup.find("main") or soup.find("body")
    if not main:
        print("  Could not find main content")
        return None

    raw_text = main.get_text(separator="\n", strip=True)
    cleaned = clean_text(raw_text)

    print(f"  Got {len(cleaned)} characters total")
    return cleaned


def save_section(name, content, url):
    """Save a section as its own .txt file."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    filename = f"{sanitize_filename(name)}.txt"
    filepath = os.path.join(OUTPUT_DIR, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"Source: {url}\n")
        f.write(f"Section: {name}\n\n")
        f.write(content)

    print(f"  Saved: {filepath} ({len(content)} chars)")


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1400, "height": 900},
        )
        page = context.new_page()

        full_text = scrape_opgg(page, URL)
        browser.close()

    if not full_text:
        print("Scrape failed - no content returned.")
        return

    print("\nSplitting into sections...")
    sections = split_into_sections(full_text)

    print(f"Found {len(sections)} sections:\n")
    for name in sections:
        print(f"  - {name}")

    print()
    for name, content in sections.items():
        save_section(name, content, URL)

    print(f"\n--- Done ---")
    print(f"Saved {len(sections)} section files to {OUTPUT_DIR}/")


if __name__ == "__main__":
    run()