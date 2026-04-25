"""
Scrapes mobalytics.gg/tft/items/* for Set 17 item stats across all categories.

Saves each page as a separate .txt file in data/raw/mobalytics/items/.
Run from the tft-faq-bot/ directory.
"""

import os
import re
import time
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

OUTPUT_DIR = "data/raw/mobalytics/items"

PAGES = [
    ("components",   "https://mobalytics.gg/tft/items"),
    ("combined",     "https://mobalytics.gg/tft/items/combined"),
    ("anima_squad",  "https://mobalytics.gg/tft/items/anima-squad"),
    ("psionic",      "https://mobalytics.gg/tft/items/psionic"),
    ("radiant",      "https://mobalytics.gg/tft/items/radiant"),
    ("elusive",      "https://mobalytics.gg/tft/items/elusive"),
    ("consumables",  "https://mobalytics.gg/tft/items/consumables"),
    ("artifacts",    "https://mobalytics.gg/tft/items/artifacts"),
]


def clean_text(text):
    text = re.sub(r"\n{3,}", "\n\n", text)
    lines = [line.rstrip() for line in text.splitlines()]
    return "\n".join(lines).strip()


def scroll_to_bottom(page):
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


def scrape_page(page, slug, url):
    print(f"\n[{slug}] Loading {url} ...")

    try:
        page.goto(url, wait_until="networkidle", timeout=45000)
    except Exception as e:
        print(f"  Slow load, continuing: {e}")

    try:
        page.wait_for_selector("[class*='item'], [class*='card'], article", timeout=15000)
    except Exception:
        print("  Selector wait timed out — proceeding anyway")

    print("  Scrolling to load all content...")
    scroll_to_bottom(page)
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


def save_page(slug, url, content):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filepath = os.path.join(OUTPUT_DIR, f"{slug}.txt")

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"Source: {url}\n")
        f.write(f"Category: {slug}\n\n")
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

        for slug, url in PAGES:
            content = scrape_page(page, slug, url)
            if content:
                path = save_page(slug, url, content)
                saved.append((slug, path))
            else:
                print(f"  Scrape failed for {slug}")
            time.sleep(2)

        browser.close()

    print(f"\n--- Done ---")
    print(f"Saved {len(saved)} files:")
    for slug, path in saved:
        print(f"  [{slug}] {path}")


if __name__ == "__main__":
    run()