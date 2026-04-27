"""
RAG retrieval: query ChromaDB and answer with Qwen via Ollama.
"""

import re
import chromadb
from chromadb import EmbeddingFunction, Embeddings
from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage

CHROMA_DIR = "embeddings/chroma_db"
COLLECTION_NAME = "tft_set17"
EMBED_MODEL = "nomic-embed-text"
CHAT_MODEL = "qwen2.5"
N_RESULTS = 5

# Cosine distance threshold: below this = good context, above = truly off-topic.
# nomic-embed-text normalized vectors sit in [0, 1]. Set high (0.8) so we only
# skip context for questions that are genuinely unrelated to TFT (e.g. "recipe for pasta").
# Vague on-topic questions like "what items are good" still score ~0.5-0.6 and
# should receive context rather than fall back to Qwen's (often wrong) training data.
DISTANCE_THRESHOLD = 0.8

SYSTEM_PROMPT_WITH_CONTEXT = """You are a TFT (Teamfight Tactics) Set 17 expert assistant.
Answer questions using ONLY the provided context. Be concise and accurate.
If the context mentions the item, champion, or mechanic by name, always explain it even if the description is brief.
Only say you don't have information if the topic is completely absent from the context.

STRICT RULES — violations will give the user wrong information:
- ONLY name items, champions, traits, and augments that appear VERBATIM in the context.
- If an item or champion name is not in the context, do NOT mention it. Do not invent names.
- Items like "Health Potion", "Boots of Speed", "Amplifying Tome", "Doran's Blade" are NOT in TFT Set 17. Never mention them.
- TFT Set 17 component items are ONLY: B.F. Sword, Chain Vest, Frying Pan, Giant's Belt, Needlessly Large Rod, Negatron Cloak, Recurve Bow, Sparring Gloves, Spatula, Tear of the Goddess.
- If you are unsure whether something exists in Set 17, do not mention it.

When the context contains patch notes (buffs, nerfs, changes), you may reason about meta implications:
- Which traits or champions became stronger or weaker based on the changes
- Which item or augment combinations are more or less viable now
- Which playstyles or comps are likely to rise or fall in priority
Always frame meta inferences clearly as reasoning from the patch changes, not established facts.
Example: "Sorcerers lost attack speed at 6, so carry-focused Sorcerer comps are likely weaker — caster builds around X may be better." """

SYSTEM_PROMPT_NO_CONTEXT = """You are a TFT (Teamfight Tactics) Set 17 expert assistant.
No relevant context was found in your knowledge base for this question.
IMPORTANT: Do NOT answer from general TFT knowledge. Items, champions, traits, and mechanics are
completely different between sets — answering from memory of other sets will give wrong information.
If you cannot answer confidently using only Set 17 knowledge, say:
"I don't have enough Set 17 data to answer that reliably. Try asking about a specific item, champion, or trait." """


class OllamaEmbeddingFunction(EmbeddingFunction):
    def __init__(self, model: str):
        self._model = OllamaEmbeddings(model=model)

    def __call__(self, input: list[str]) -> Embeddings:
        return self._model.embed_documents(input)


def get_collection():
    ef = OllamaEmbeddingFunction(EMBED_MODEL)
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    return client.get_collection(COLLECTION_NAME, embedding_function=ef)


_STOPWORDS = {
    "what", "does", "do", "how", "is", "the", "a", "an", "can", "tell",
    "me", "about", "explain", "describe", "give", "i", "you", "your",
    "my", "which", "where", "when", "who", "why", "please", "help",
    "and", "or", "in", "on", "at", "to", "for", "of", "with", "it",
    "this", "that", "these", "those", "has", "have", "are", "be", "been",
    "will", "would", "could", "should", "get",
    "work", "works", "working", "happen", "happens", "use", "used",
    "like", "look", "looks", "mean", "means", "effect", "effects",
}


def _keywords(query: str) -> list[str]:
    words = re.findall(r"[a-zA-Z']+", query)
    return [w.title() for w in words if w.lower() not in _STOPWORDS and len(w) > 2]


def retrieve(collection, query: str, n: int = N_RESULTS) -> tuple[list[str], float]:
    """Returns (docs, best_distance). best_distance is the lowest (best) score found."""
    vector_results = collection.query(
        query_texts=[query],
        n_results=n,
        include=["documents", "distances"],
    )
    docs = list(vector_results["documents"][0])
    distances = list(vector_results["distances"][0])
    seen_ids = set(vector_results["ids"][0])
    best_distance = min(distances) if distances else 1.0

    # Keyword fallback: search document text directly for named entities
    keywords = _keywords(query)
    if keywords:
        filters = [{"$contains": kw} for kw in keywords]
        where_doc = {"$and": filters} if len(filters) > 1 else filters[0]
        try:
            kw_results = collection.query(
                query_texts=[query],
                n_results=n,
                where_document=where_doc,
                include=["documents", "distances"],
            )
            for doc, doc_id, dist in zip(
                kw_results["documents"][0],
                kw_results["ids"][0],
                kw_results["distances"][0],
            ):
                if doc_id not in seen_ids:
                    docs.append(doc)
                    seen_ids.add(doc_id)
                    best_distance = min(best_distance, dist)
        except Exception:
            pass

    return docs, best_distance


def answer(query: str, collection=None) -> str:
    if collection is None:
        collection = get_collection()

    chunks, best_distance = retrieve(collection, query)
    context_is_useful = best_distance < DISTANCE_THRESHOLD

    llm = ChatOllama(model=CHAT_MODEL, temperature=0)

    if context_is_useful:
        context = "\n\n---\n\n".join(chunks)
        messages = [
            SystemMessage(content=SYSTEM_PROMPT_WITH_CONTEXT),
            HumanMessage(content=f"Context:\n{context}\n\nQuestion: {query}"),
        ]
    else:
        messages = [
            SystemMessage(content=SYSTEM_PROMPT_NO_CONTEXT),
            HumanMessage(content=query),
        ]

    response = llm.invoke(messages)
    return response.content


if __name__ == "__main__":
    import sys
    q = " ".join(sys.argv[1:]) or "What does Infinity Edge do?"
    print(answer(q))
