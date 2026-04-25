"""
Scrapes mobalytics.gg/tft/augments for Set 17 augment data across all three tiers.

URLs:
  https://mobalytics.gg/tft/augments?tier=1  (Silver)
  https://mobalytics.gg/tft/augments?tier=2  (Gold)
  https://mobalytics.gg/tft/augments?tier=3  (Prismatic)

Saves each tier as a separate .txt file in data/raw/mobalytics/.
Run from the tft-faq-bot/ directory.
"""

import os
import re
import time
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

OUTPUT_DIR = "data/raw/mobalytics"

TIERS = {
    1: "Silver",
    2: "Gold",
    3: "Prismatic",
}

BASE_URL = "https://mobalytics.gg/tft/augments?tier={tier}"


def clean_text(text):
    text = re.sub(r"\n{3,}", "\n\n", text)
    lines = [line.rstrip() for line in text.splitlines()]
    return "\n".join(lines).strip()


def scroll_to_bottom(page):
    """Scroll incrementally to force lazy-loaded content to render."""
    page.evaluate("""
        async () => {
            await new Promise((resolve) => {
                let totalHeight = 0;
                const distance = 800;
                const timer = setInterval(() => {
                    const scrollHeight = document.body.scrollHeight;
                    window.scrollBy(0, distance);
                    totalHeight += distance;
                    if (totalHeight >= scrollHeight) {
                        clearInterval(timer);
                        resolve();
                    }
                }, 300);
            });
        }
    """)
    page.wait_for_timeout(3000)


def scrape_tier(page, tier_num, tier_name):
    url = BASE_URL.format(tier=tier_num)
    print(f"\n[Tier {tier_num} — {tier_name}] Loading {url} ...")

    try:
        page.goto(url, wait_until="networkidle", timeout=45000)
    except Exception as e:
        print(f"  Slow load, continuing: {e}")

    # Wait for augment cards to appear — Mobalytics renders into article/card elements
    try:
        page.wait_for_selector("[class*='augment'], [class*='card'], article", timeout=15000)
    except Exception:
        print("  Selector wait timed out — proceeding anyway")

    print("  Scrolling to load all augments...")
    scroll_to_bottom(page)

    # Scroll back to top and do a second pass to catch any deferred content
    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_timeout(1000)
    scroll_to_bottom(page)

    html = page.content()
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup.find_all(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    main = soup.find("main") or soup.find("body")
    if not main:
        print("  Could not find main content area")
        return None

    raw_text = main.get_text(separator="\n", strip=True)
    cleaned = clean_text(raw_text)

    print(f"  Extracted {len(cleaned):,} characters")
    return cleaned


def save_tier(tier_num, tier_name, content):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filename = f"augments_tier{tier_num}_{tier_name.lower()}.txt"
    filepath = os.path.join(OUTPUT_DIR, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"Source: {BASE_URL.format(tier=tier_num)}\n")
        f.write(f"Tier: {tier_num} ({tier_name})\n\n")
        f.write(content)

    print(f"  Saved: {filepath}")
    return filepath


def run():
    saved = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1400, "height": 900},
        )
        page = context.new_page()

        for tier_num, tier_name in TIERS.items():
            content = scrape_tier(page, tier_num, tier_name)
            if content:
                path = save_tier(tier_num, tier_name, content)
                saved.append(path)
            else:
                print(f"  Scrape failed for tier {tier_num}")
            time.sleep(2)

        browser.close()

    print(f"\n--- Done ---")
    print(f"Saved {len(saved)} files:")
    for path in saved:
        print(f"  {path}")
    print(f"\nNext step: run parse_augments.py to structure the raw data.")


if __name__ == "__main__":
    run()