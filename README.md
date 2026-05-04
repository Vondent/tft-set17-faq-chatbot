# TFT Set 17 FAQ Chatbot

A full-stack RAG (Retrieval-Augmented Generation) chatbot for Teamfight Tactics Set 17. Ask questions in plain English about champions, items, augments, traits, meta comps, and patch notes — no SQL or game knowledge required.

**Live demo:** [tft-set17-faq-chatbot.vercel.app](https://tft-set17-faq-chatbot.vercel.app/)

---

## Project Overview

The chatbot works in three stages:

1. **Ingest** — scrapers collect raw game data from multiple sources and parsers transform it into structured text chunks
2. **Embed** — each chunk is embedded into a ChromaDB vector store using ONNX sentence embeddings
3. **Retrieve & Answer** — at query time, a hybrid search (vector similarity + keyword matching) retrieves the most relevant chunks, which are passed as context to Groq's LLaMA 3.3 70B to generate a grounded answer

---

## Tech Stack

| Layer | Technology | Purpose |
| --- | --- | --- |
| LLM | Groq (LLaMA 3.3 70B) | Answer generation |
| Orchestration | LangChain | LLM prompt chaining |
| Vector store | ChromaDB | Semantic document retrieval |
| Embeddings | ONNX MiniLM-L6-v2 | Lightweight local sentence embeddings |
| Backend | FastAPI + Uvicorn | REST API (`/ask` endpoint) |
| Frontend | HTML / CSS / JS | Static chat UI |
| Scraping | Playwright, BeautifulSoup | Dynamic and static web scraping |
| Hosting | Render (backend), Vercel (frontend) | Cloud deployment |

---

## Data Sources

The knowledge base is built from game data scraped across 4+ sources:

- **Champions** — name, cost, traits, ability descriptions, and recommended items for each unit in Set 17
- **Items** — all component and combined items with descriptions, stat bonuses, and S/A/B/C tier ratings
- **Augments** — all silver, gold, and prismatic augments with descriptions and tier ratings
- **Traits** — all origin and class synergies with breakpoint effects
- **Meta Comps** — top-ranked competitive compositions with unit lists, trait activations, item builds, and average placement stats from high-elo games
- **Patch Notes** — Set 17 patch changes with buff/nerf summaries

Raw data is scraped into `data/raw/` (gitignored) and processed into structured `.txt` files in `data/processed/`.

---

## File Structure

```text
chatbot/
├── api/
│   └── main.py                      # FastAPI backend — /ask POST endpoint, /health GET
├── app/
│   └── app.py                       # Streamlit UI (local dev only)
├── data/
│   └── processed/                   # Knowledge base fed into ChromaDB
│       ├── augments.txt
│       ├── champions.txt
│       ├── class_synergies.txt
│       ├── comps.txt
│       ├── glossary.txt
│       ├── items.txt
│       ├── origin_synergies.txt
│       └── patch_17.1.txt
├── embeddings/
│   ├── embed.py                     # Builds ChromaDB collection from processed files
│   └── chroma_db/                   # Pre-built vector store (committed to repo)
├── frontend/
│   └── index.html                   # Static chat UI deployed to Vercel
├── ingest/
│   ├── opgg_scraper.py              # Scrapes champion + synergy data
│   ├── mobalytics_augment_scraper.py
│   ├── mobalytics_item_scraper.py
│   ├── metatft_comps_scraper.py     # Intercepts MetaTFT API via Playwright
│   ├── tftacademy_tierlist_scraper.py
│   ├── tftacademy_item_tierlist_scraper.py
│   ├── parse_augments.py
│   ├── parse_augment_tiers.py
│   ├── parse_champions.py
│   ├── parse_comps.py
│   ├── parse_items_full.py
│   ├── parse_item_tiers.py
│   ├── parse_patch_notes.py
│   └── parse_synergies.py
├── retrieval/
│   └── retrieve.py                  # Hybrid retrieval + Groq LLM answer
├── render.yaml                      # Render deploy config
├── requirements.txt                 # Production dependencies
├── requirements-dev.txt             # Dev dependencies (scraping, Streamlit)
└── vercel.json                      # Vercel deploy config
```

---


## Updating the Knowledge Base

After running any ingest scripts, re-embed and commit the updated vector store:

```bash
tft-faq-bot/venv/Scripts/python embeddings/embed.py
git add embeddings/chroma_db/
git commit -m "Update knowledge base"
git push
```

### Augment tier list

```bash
tft-faq-bot/venv/Scripts/python ingest/tftacademy_tierlist_scraper.py
tft-faq-bot/venv/Scripts/python ingest/parse_augment_tiers.py
```

### Item tier list

```bash
tft-faq-bot/venv/Scripts/python ingest/tftacademy_item_tierlist_scraper.py
tft-faq-bot/venv/Scripts/python ingest/parse_item_tiers.py
```

### Meta comps

```bash
tft-faq-bot/venv/Scripts/python ingest/metatft_comps_scraper.py
tft-faq-bot/venv/Scripts/python ingest/parse_comps.py
```

### Champions, items, synergies, patch notes

```bash
tft-faq-bot/venv/Scripts/python ingest/opgg_scraper.py
tft-faq-bot/venv/Scripts/python ingest/mobalytics_augment_scraper.py
tft-faq-bot/venv/Scripts/python ingest/mobalytics_item_scraper.py
tft-faq-bot/venv/Scripts/python ingest/parse_augments.py
tft-faq-bot/venv/Scripts/python ingest/parse_champions.py
tft-faq-bot/venv/Scripts/python ingest/parse_items_full.py
tft-faq-bot/venv/Scripts/python ingest/parse_synergies.py
tft-faq-bot/venv/Scripts/python ingest/parse_patch_notes.py
```
