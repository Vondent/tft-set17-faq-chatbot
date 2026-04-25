"""
RAG retrieval: query ChromaDB and answer with Qwen via Ollama.
"""

import chromadb
from chromadb import EmbeddingFunction, Embeddings
from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage

CHROMA_DIR = "embeddings/chroma_db"
COLLECTION_NAME = "tft_set17"
EMBED_MODEL = "nomic-embed-text"
CHAT_MODEL = "qwen2.5"
N_RESULTS = 5

SYSTEM_PROMPT = """You are a TFT (Teamfight Tactics) Set 17 expert assistant.
Answer questions using only the provided context. Be concise and accurate.
If the context doesn't contain enough information to answer, say so."""


class OllamaEmbeddingFunction(EmbeddingFunction):
    def __init__(self, model: str):
        self._model = OllamaEmbeddings(model=model)

    def __call__(self, input: list[str]) -> Embeddings:
        return self._model.embed_documents(input)


def get_collection():
    ef = OllamaEmbeddingFunction(EMBED_MODEL)
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    return client.get_collection(COLLECTION_NAME, embedding_function=ef)


def retrieve(collection, query: str, n: int = N_RESULTS) -> list[str]:
    results = collection.query(query_texts=[query], n_results=n)
    return results["documents"][0]


def answer(query: str, collection=None) -> str:
    if collection is None:
        collection = get_collection()

    chunks = retrieve(collection, query)
    context = "\n\n---\n\n".join(chunks)

    llm = ChatOllama(model=CHAT_MODEL, temperature=0)
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"Context:\n{context}\n\nQuestion: {query}"),
    ]
    response = llm.invoke(messages)
    return response.content


if __name__ == "__main__":
    import sys
    q = " ".join(sys.argv[1:]) or "What does Infinity Edge do?"
    print(answer(q))
