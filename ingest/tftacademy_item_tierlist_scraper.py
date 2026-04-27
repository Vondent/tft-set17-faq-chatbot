"""
Fetches TFT item tier list data from the TFT Academy API and saves raw JSON.

API: https://tftacademy.com/api/tierlist/items
Returns tier ratings (S/A/B/C) per item, broken down by type:
  - craftables: Combined items
  - radiants:   Radiant items
  - ornns:      Artifact (Ornn) items
  - emblems:    Emblem items

Output: data/raw/items_tierlist.json
Run from the chatbot/ directory.
"""

import json
import os
import urllib.request

API_URL = "https://tftacademy.com/api/tierlist/items"
OUTPUT_PATH = os.path.join("data", "raw", "items_tierlist.json")


def fetch():
    print(f"Fetching {API_URL} ...")
    req = urllib.request.Request(
        API_URL,
        headers={"User-Agent": "Mozilla/5.0"},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode())
    print(f"  Received {len(data.get('items_tierlists', []))} tier list entries.")
    return data


def save(data):
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"  Saved: {OUTPUT_PATH}")


if __name__ == "__main__":
    data = fetch()
    save(data)
    print(f"\nNext step: run parse_item_tiers.py to update items.txt.")
