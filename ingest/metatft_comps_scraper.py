"""
Fetches TFT comp data from the MetaTFT API and saves raw JSON files.

Endpoints:
  comps_data:  https://api-hc.metatft.com/tft-comps-api/comps_data?queue=1100
  comps_stats: https://api-hc.metatft.com/tft-comps-api/comps_stats?queue=1100&...
  item_lookup: https://data.metatft.com/lookups/TFTSet17_latest_en_us.json
  trait_map:   https://data.metatft.com/lookups/trait_mapping.json

Output: data/raw/metatft_*.json
Run from the chatbot/ directory.
"""

import json
import os
import urllib.request

OUTPUT_DIR = os.path.join("data", "raw")

ENDPOINTS = [
    (
        "metatft_comps_data.json",
        "https://api-hc.metatft.com/tft-comps-api/comps_data?queue=1100",
    ),
    (
        "metatft_comps_stats.json",
        (
            "https://api-hc.metatft.com/tft-comps-api/comps_stats"
            "?queue=1100&patch=current&days=3"
            "&rank=CHALLENGER,DIAMOND,EMERALD,GRANDMASTER,MASTER,PLATINUM"
            "&permit_filter_adjustment=true"
        ),
    ),
    (
        "metatft_lookup_items.json",
        "https://data.metatft.com/lookups/TFTSet17_latest_en_us.json",
    ),
    (
        "metatft_lookup_traits.json",
        "https://data.metatft.com/lookups/trait_mapping.json",
    ),
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
}


def fetch(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


def save(filename, data):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"  Saved: {path}")
    return path


if __name__ == "__main__":
    for filename, url in ENDPOINTS:
        print(f"Fetching {url[:60]}...")
        data = fetch(url)
        save(filename, data)
    print("\nNext step: run parse_comps.py to build comps.txt.")
