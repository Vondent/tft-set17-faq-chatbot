import os
import re
import time
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

OUTPUT_DIR = "data/raw"

# Sections we care about — everything else gets dropped
BALANCE_SECTIONS = {
    "AUGMENTS",
    "TRAITS",
    "CHAMPIONS",
    "ITEMS",
    "EMBLEMS",
    "ARTIFACTS",
    "RADIANT ITEMS",
    "ADJUSTED ARTIFACTS",
    "NEW ARTIFACTS",
    "AUGMENTS ADJUSTED: SILVER",
    "AUGMENTS ADJUSTED: GOLD",
    "AUGMENTS ADJUSTED: PRISMATIC",
    "RETURNING AUGMENTS",
    "AUGMENT CYCLING: REMOVED",
    "BUG FIXES",
}


def generate_patch_urls(start_set, start_patch, end_set, end_patch):
    """Auto-generate patch URLs from a starting point up to a ceiling."""
    urls = []
    current_set = start_set
    current_patch = start_patch

    while (current_set < end_set) or (current_set == end_set and current_patch <= end_patch):
        url = (
            f"https://teamfighttactics.leagueoflegends.com/en-us/news/game-updates/"
            f"teamfight-tactics-patch-{current_set}-{current_patch}/"
        )
        urls.append(url)

        current_patch += 1
        if current_patch > 10:
            current_set += 1
            current_patch = 1

    return urls


def url_exists(url):
    """Quick HEAD check - cheap way to skip non-existent patches."""
    try:
        res = requests.head(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        return res.status_code == 200
    except requests.RequestException:
        return False


def is_balance_line(line):
    """Heuristic: does this line look like an actual balance change?"""
    # lines with stat changes usually contain these symbols
    if "⇒" in line or "=>" in line:
        return True
    # "X Removed" or "X Reworked" style lines
    if re.search(r"\b(Removed|Reworked|REWORKED)\b", line):
        return True
    # bug fix lines typically start with "Fixed"
    if line.strip().startswith("Fixed"):
        return True
    return False


def is_section_header(line):
    """Is this line a section header we care about?"""
    stripped = line.strip().upper()
    return stripped in BALANCE_SECTIONS


def filter_balance_changes(raw_text):
    """
    Parse the scraped text and keep only:
    - Section headers we care about (AUGMENTS, CHAMPIONS, etc.)
    - Lines that look like actual balance changes (have ⇒, "Removed", "Fixed", etc.)
    Drops all dev commentary and fluff.
    """
    lines = raw_text.splitlines()
    output = []
    current_section = None
    in_relevant_section = False

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        if not line:
            i += 1
            continue

        # check if this is a section header
        if is_section_header(line):
            current_section = line.upper()
            in_relevant_section = True
            output.append(f"\n## {current_section}")
            i += 1
            continue

        # if we're in a relevant section, keep balance-looking lines
        if in_relevant_section:
            # stat changes often span multiple lines:
            #   "Jax Shield: 400/500/675 AP"
            #   "⇒"
            #   "400/500/625 AP"
            # so we stitch them back together
            if i + 2 < len(lines):
                next_line = lines[i + 1].strip()
                line_after = lines[i + 2].strip()
                if next_line == "⇒":
                    combined = f"{line} ⇒ {line_after}"
                    output.append(combined)
                    i += 3
                    continue

            if is_balance_line(line):
                output.append(line)

        i += 1

    return "\n".join(output).strip()


def scrape_patch_note(page, url):
    """Use a headless browser to load the page and scrape the full rendered content."""
    print(f"  Scraping: {url}")

    try:
        page.goto(url, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(2000)
    except Exception as e:
        print(f"  Failed to load page: {e}")
        return None

    html = page.content()
    soup = BeautifulSoup(html, "html.parser")

    title = soup.find("h1")
    title_text = title.get_text(strip=True) if title else url.split("/")[-2]

    article = (
        soup.find("article") or
        soup.find("main") or
        soup.find("div", class_=lambda c: c and "article" in c.lower())
    )

    if not article:
        print("  Could not find article body")
        return None

    for tag in article.find_all(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    raw_text = article.get_text(separator="\n", strip=True)

    # filter down to only balance changes
    filtered = filter_balance_changes(raw_text)

    if not filtered:
        print("  Filter produced empty result - skipping")
        return None

    print(f"  Got {len(filtered)} characters of balance changes - '{title_text}'")
    return {"title": title_text, "url": url, "content": filtered}


def save_patch_note(patch):
    """Save a patch note as a .txt file."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    filename = (
        patch["title"]
        .replace(" ", "_")
        .replace("/", "-")
        .replace(":", "")
        .replace("?", "")
        + ".txt"
    )
    filepath = os.path.join(OUTPUT_DIR, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"URL: {patch['url']}\n")
        f.write(f"Title: {patch['title']}\n")
        f.write(patch["content"])

    print(f"  Saved: {filepath}")


def run():
    print("Generating patch URLs...")
    urls = generate_patch_urls(start_set=17, start_patch=1, end_set=17, end_patch=24)
    print(f"Checking {len(urls)} potential patch URLs...\n")

    valid_urls = []
    for url in urls:
        if url_exists(url):
            print(f"  Found: {url}")
            valid_urls.append(url)
        else:
            print(f"  Skipping (not found): {url}")
        time.sleep(0.3)

    if not valid_urls:
        print("\nNo valid URLs found.")
        return

    print(f"\nStarting browser for {len(valid_urls)} patch notes...\n")

    success = 0
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        for url in valid_urls:
            patch = scrape_patch_note(page, url)
            if patch:
                save_patch_note(patch)
                success += 1
            time.sleep(1)

        browser.close()

    print(f"\n--- Done ---")
    print(f"Saved: {success} patch notes")
    print(f"Check your {OUTPUT_DIR}/ folder for the filtered balance changes.")


if __name__ == "__main__":
    run()