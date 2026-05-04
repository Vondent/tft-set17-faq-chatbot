# TFT Set 17 FAQ Chatbot

A full-stack RAG (Retrieval-Augmented Generation) chatbot for Teamfight Tactics Set 17. Ask questions in plain English about champions, items, augments, traits, meta comps, and patch notes.

**Live demo:** [tft-set17-faq-chatbot.vercel.app](https://tft-set17-faq-chatbot.vercel.app/)

---

## How It Works

The chatbot operates in three stages:

1. **Ingest** — Playwright and BeautifulSoup scrapers collect raw game data from multiple sources; parsers transform it into structured text chunks
2. **Embed** — each chunk is embedded using FastEmbed (MiniLM-L6-v2) and upserted into a Pinecone vector index
3. **Retrieve & Answer** — at query time, the top-5 most semantically similar chunks are retrieved from Pinecone and passed as context to Groq's LLaMA 3.3 70B, which generates a grounded answer

---

## Tech Stack

| Layer | Technology | Purpose |
| --- | --- | --- |
| LLM | Groq (LLaMA 3.3 70B) | Answer generation |
| Orchestration | LangChain | Prompt chaining |
| Vector store | Pinecone | Managed cloud vector search |
| Embeddings | FastEmbed (MiniLM-L6-v2) | Lightweight ONNX sentence embeddings |
| Backend | FastAPI + Uvicorn | REST API |
| Frontend | HTML / CSS / JS | Static chat UI |
| Scraping | Playwright, BeautifulSoup | Dynamic and static web scraping |
| Hosting | Render (backend), Vercel (frontend) | Cloud deployment |

---

## Data

The knowledge base covers 686 chunks across 6 categories, scraped from 4+ sources including op.gg, Mobalytics, MetaTFT, and TFT Academy.

| Category | What was collected | How |
| --- | --- | --- |
| **Champions** | Name, cost, traits, ability descriptions, recommended items for all Set 17 units | BeautifulSoup static scrape of op.gg |
| **Items** | All component and combined items with descriptions, stats, and S/A/B/C tier ratings | BeautifulSoup scrape of Mobalytics + TFT Academy tier list |
| **Augments** | All silver, gold, and prismatic augments with descriptions and tier ratings | BeautifulSoup scrape of Mobalytics + TFT Academy tier list |
| **Traits** | All origin and class synergies with breakpoint effects | BeautifulSoup static scrape of op.gg |
| **Meta Comps** | Top-ranked compositions with unit lists, trait activations, item builds, and placement stats | Playwright headless browser intercepting MetaTFT's internal API |
| **Patch Notes** | Set 17 patch changes with buff/nerf summaries | BeautifulSoup static scrape |

**Playwright** was used specifically for MetaTFT because the composition data is loaded dynamically via JavaScript after page load — a static scraper cannot access it. All other sources were scraped with **BeautifulSoup** against server-rendered HTML.

Raw data is saved to `data/raw/` and processed into structured `.txt` files in `data/processed/` by a set of dedicated parser scripts in `ingest/`.
