"""
Corrective RAG (CRAG) pipeline using LangGraph.

Flow:
  retrieve → grade_documents
    ├─ relevant docs found  → generate → grade_answer → END
    │                                          └─ hallucinating + retries left → rewrite → retrieve
    └─ no relevant docs + retries left → rewrite → retrieve
                        + max retries  → generate (no-context fallback) → END
"""

from typing_extensions import TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from langgraph.graph import END, StateGraph

from retrieval.retrieve import (
    SYSTEM_PROMPT_NO_CONTEXT,
    SYSTEM_PROMPT_WITH_CONTEXT,
    retrieve,
)

MAX_RETRIES = 1

_gen_llm   = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)
_grade_llm = ChatGroq(model="llama-3.1-8b-instant",    temperature=0)


# ── State ─────────────────────────────────────────────────────────────────────

class GraphState(TypedDict):
    question:           str
    documents:          list[str]
    relevant_documents: list[str]
    answer:             str
    hallucination:      str   # "yes" | "no" | "skip"
    retries:            int


# ── Graph factory ─────────────────────────────────────────────────────────────

def build_graph(index):
    """Build and compile the CRAG graph, closing over the Pinecone index."""

    def retrieve_node(state: GraphState) -> dict:
        docs, _ = retrieve(index, state["question"])
        return {"documents": docs, "relevant_documents": []}

    def grade_documents_node(state: GraphState) -> dict:
        relevant = []
        for doc in state["documents"]:
            result = _grade_llm.invoke([
                SystemMessage(content=(
                    "You are grading whether a TFT (Teamfight Tactics) document is relevant "
                    "to a question. Reply with exactly 'yes' or 'no' and nothing else."
                )),
                HumanMessage(content=f"Question: {state['question']}\n\nDocument:\n{doc}"),
            ])
            if result.content.strip().lower().startswith("y"):
                relevant.append(doc)
        return {"relevant_documents": relevant}

    def rewrite_query_node(state: GraphState) -> dict:
        result = _grade_llm.invoke([
            SystemMessage(content=(
                "Rewrite the TFT question below to improve vector search retrieval. "
                "Be more specific — include the exact item, champion, trait, or augment name. "
                "Return only the rewritten question, nothing else."
            )),
            HumanMessage(content=state["question"]),
        ])
        return {
            "question": result.content.strip(),
            "retries":  state.get("retries", 0) + 1,
        }

    def generate_node(state: GraphState) -> dict:
        relevant = state.get("relevant_documents", [])
        if relevant:
            context  = "\n\n---\n\n".join(relevant)
            messages = [
                SystemMessage(content=SYSTEM_PROMPT_WITH_CONTEXT),
                HumanMessage(content=f"Context:\n{context}\n\nQuestion: {state['question']}"),
            ]
        else:
            messages = [
                SystemMessage(content=SYSTEM_PROMPT_NO_CONTEXT),
                HumanMessage(content=state["question"]),
            ]
        return {"answer": _gen_llm.invoke(messages).content}

    def grade_answer_node(state: GraphState) -> dict:
        relevant = state.get("relevant_documents", [])
        if not relevant:
            return {"hallucination": "skip"}  # no context to grade against
        context = "\n\n---\n\n".join(relevant)
        result  = _grade_llm.invoke([
            SystemMessage(content=(
                "You are checking whether a TFT answer is grounded in the provided context. "
                "Return 'yes' if every claim in the answer is supported by the context, "
                "'no' if the answer contains unsupported or invented information. "
                "Reply with exactly 'yes' or 'no' and nothing else."
            )),
            HumanMessage(content=f"Context:\n{context}\n\nAnswer:\n{state['answer']}"),
        ])
        return {"hallucination": result.content.strip().lower()}

    # ── Routing ───────────────────────────────────────────────────────────────

    def route_after_grading(state: GraphState) -> str:
        if state.get("relevant_documents"):
            return "generate"
        if state.get("retries", 0) < MAX_RETRIES:
            return "rewrite"
        return "generate"  # max retries — fall through to no-context generation

    def route_after_answer(state: GraphState) -> str:
        h = state.get("hallucination", "yes")
        if h == "no" and state.get("retries", 0) < MAX_RETRIES:
            return "rewrite"
        return END

    # ── Build ─────────────────────────────────────────────────────────────────

    g = StateGraph(GraphState)
    g.add_node("retrieve",        retrieve_node)
    g.add_node("grade_documents", grade_documents_node)
    g.add_node("rewrite",         rewrite_query_node)
    g.add_node("generate",        generate_node)
    g.add_node("grade_answer",    grade_answer_node)

    g.set_entry_point("retrieve")
    g.add_edge("retrieve", "grade_documents")
    g.add_conditional_edges(
        "grade_documents", route_after_grading,
        {"generate": "generate", "rewrite": "rewrite"},
    )
    g.add_edge("rewrite", "retrieve")
    g.add_edge("generate", "grade_answer")
    g.add_conditional_edges(
        "grade_answer", route_after_answer,
        {"rewrite": "rewrite", END: END},
    )

    return g.compile()


def run_graph(question: str, graph) -> tuple[str, list[str]]:
    """Invoke the CRAG graph and return (answer, relevant_chunks)."""
    result = graph.invoke({
        "question":           question,
        "documents":          [],
        "relevant_documents": [],
        "answer":             "",
        "hallucination":      "",
        "retries":            0,
    })
    return result["answer"], result["relevant_documents"]
