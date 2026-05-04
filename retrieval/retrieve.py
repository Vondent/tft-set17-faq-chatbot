"""
RAG retrieval: query Pinecone and answer with Groq via LangChain.
"""

import os
from pinecone import Pinecone
from fastembed import TextEmbedding
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

load_dotenv()

PINECONE_INDEX = "tft-set-17-faq-chatbot"
CHAT_MODEL = "llama-3.3-70b-versatile"
N_RESULTS = 5
SCORE_THRESHOLD = 0.3

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

_embed_model = TextEmbedding("sentence-transformers/all-MiniLM-L6-v2")
_llm = ChatGroq(model=CHAT_MODEL, temperature=0)


def _embed(text: str) -> list[float]:
    return list(_embed_model.embed([text]))[0].tolist()


def get_index():
    pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
    return pc.Index(PINECONE_INDEX)


def retrieve(index, query: str, n: int = N_RESULTS) -> tuple[list[str], float]:
    vec = _embed(query)
    results = index.query(vector=vec, top_k=n, include_metadata=True)
    docs = [m.metadata["text"] for m in results.matches if "text" in m.metadata]
    best_score = max((m.score for m in results.matches), default=0.0)
    return docs, best_score


def answer(query: str, index=None) -> str:
    if index is None:
        index = get_index()

    chunks, best_score = retrieve(index, query)
    context_is_useful = best_score > SCORE_THRESHOLD

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

    return _llm.invoke(messages).content


if __name__ == "__main__":
    import sys
    q = " ".join(sys.argv[1:]) or "What does Infinity Edge do?"
    print(answer(q))
