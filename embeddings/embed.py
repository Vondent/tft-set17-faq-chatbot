"""
Build ChromaDB vector store from processed TFT data files.
Run from the chatbot/ directory:
  tft-faq-bot/venv/Scripts/python embeddings/embed.py

Requires GOOGLE_API_KEY in environment or .env file.
"""

import os
import re
import chromadb
from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2
from dotenv import load_dotenv

load_dotenv()

PROCESSED_DIR = "data/processed"
CHROMA_DIR = "embeddings/chroma_db"
COLLECTION_NAME = "tft_set17"


def parse_file(filepath):
    source = os.path.basename(filepath).replace(".txt", "")
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    if source.startswith("patch_"):
        return _chunk_patch(content, source)
    return _chunk_standard(content, source)


def _chunk_standard(content, source):
    chunks = []
    for block in content.split("---"):
        block = block.strip()
        if not block:
            continue
        lines = [l for l in block.split("\n") if l.strip()]
        if all(l.startswith("#") for l in lines):
            continue
        meta = _extract_meta(block, source)
        chunks.append((block, meta))
    return chunks


def _chunk_patch(content, source):
    chunks = []
    for section in re.split(r"(?m)^(?=##\s)", content):
        section = section.strip()
        if not section.startswith("##"):
            continue
        heading = section.split("\n", 1)[0].lstrip("#").strip()
        chunks.append((section, {"source": source, "name": heading, "category": "patch_notes"}))
    return chunks


def _extract_meta(block, source):
    meta = {"source": source, "name": "", "category": ""}
    for line in block.split("\n")[:8]:
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key, val = key.strip().lower(), val.strip()
        if key in ("champion", "item", "augment", "trait", "comp", "term"):
            meta["name"] = val
        elif key in ("category", "tier", "type", "cost"):
            meta["category"] = val
    return meta


def run():
    ef = ONNXMiniLM_L6_V2()
    client = chromadb.PersistentClient(path=CHROMA_DIR)

    try:
        client.delete_collection(COLLECTION_NAME)
        print("Rebuilding collection from scratch.")
    except Exception:
        pass
    collection = client.create_collection(COLLECTION_NAME, embedding_function=ef)

    all_docs, all_meta, all_ids = [], [], []
    uid = 0

    for fname in sorted(os.listdir(PROCESSED_DIR)):
        if not fname.endswith(".txt"):
            continue
        chunks = parse_file(os.path.join(PROCESSED_DIR, fname))
        print(f"  {fname}: {len(chunks)} chunks")
        for text, meta in chunks:
            all_docs.append(text)
            all_meta.append(meta)
            all_ids.append(f"doc_{uid}")
            uid += 1

    print(f"\nEmbedding {len(all_docs)} total chunks...")
    # Gemini embedding API: batch conservatively to avoid rate limits
    batch_size = 20
    for i in range(0, len(all_docs), batch_size):
        collection.add(
            documents=all_docs[i:i + batch_size],
            metadatas=all_meta[i:i + batch_size],
            ids=all_ids[i:i + batch_size],
        )
        print(f"  {min(i + batch_size, len(all_docs))}/{len(all_docs)}")

    print(f"\nDone. {len(all_docs)} chunks in collection '{COLLECTION_NAME}'.")


if __name__ == "__main__":
    run()
