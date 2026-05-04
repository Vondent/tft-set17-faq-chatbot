"""
Build Pinecone vector store from processed TFT data files.
Run from the chatbot/ directory:
  tft-faq-bot/venv/Scripts/python embeddings/embed.py
"""

import os
import re
from pinecone import Pinecone
from fastembed import TextEmbedding
from dotenv import load_dotenv

load_dotenv()

PROCESSED_DIR = "data/processed"
PINECONE_INDEX = "tft-set-17-faq-chatbot"


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
        lines = [line for line in block.split("\n") if line.strip()]
        if all(line.startswith("#") for line in lines):
            continue
        chunks.append((block, _extract_meta(block, source)))
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
    pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
    index = pc.Index(PINECONE_INDEX)
    embed_model = TextEmbedding("sentence-transformers/all-MiniLM-L6-v2")

    all_docs, all_meta, all_ids = [], [], []

    for fname in sorted(os.listdir(PROCESSED_DIR)):
        if not fname.endswith(".txt"):
            continue
        chunks = parse_file(os.path.join(PROCESSED_DIR, fname))
        print(f"  {fname}: {len(chunks)} chunks")
        for text, meta in chunks:
            all_docs.append(text)
            all_meta.append(meta)
            all_ids.append(f"doc_{len(all_ids)}")

    print(f"\nEmbedding {len(all_docs)} total chunks...")
    batch_size = 100
    for i in range(0, len(all_docs), batch_size):
        batch_docs = all_docs[i:i + batch_size]
        batch_meta = all_meta[i:i + batch_size]
        batch_ids = all_ids[i:i + batch_size]

        vectors = list(embed_model.embed(batch_docs))

        index.upsert(vectors=[
            {"id": id_, "values": vec.tolist(), "metadata": {**meta, "text": doc}}
            for id_, vec, doc, meta in zip(batch_ids, vectors, batch_docs, batch_meta)
        ])
        print(f"  {min(i + batch_size, len(all_docs))}/{len(all_docs)}")

    print(f"\nDone. {len(all_docs)} chunks upserted to '{PINECONE_INDEX}'.")


if __name__ == "__main__":
    run()
