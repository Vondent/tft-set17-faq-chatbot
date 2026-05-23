"""
FastAPI backend for TFT Set 17 FAQ chatbot.
Run from the chatbot/ directory:
  uvicorn api.main:app --host 0.0.0.0 --port 8000
"""

import logging
import re
from collections import OrderedDict
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, StringConstraints

from retrieval.graph import build_graph, run_graph
from retrieval.retrieve import get_index
from api.stats import get_stats

logger = logging.getLogger(__name__)

CACHE_MAX_SIZE = 500


def _cache_key(query: str) -> str:
    return re.sub(r"\s+", " ", query.lower().strip())


@asynccontextmanager
async def lifespan(app: FastAPI):
    index = get_index()
    app.state.index = index
    app.state.graph = build_graph(index)
    app.state.cache = OrderedDict()
    yield


app = FastAPI(title="TFT Set 17 FAQ", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "GET"],
    allow_headers=["Content-Type"],
)


class AskRequest(BaseModel):
    question: Annotated[str, StringConstraints(min_length=1, max_length=500, strip_whitespace=True)]


class AskResponse(BaseModel):
    answer: str


@app.post("/ask", response_model=AskResponse)
async def ask(req: AskRequest, request: Request):
    cache = request.app.state.cache
    key = _cache_key(req.question)

    if key in cache:
        return JSONResponse({"answer": cache[key]}, headers={"X-Cache": "HIT"})

    try:
        result, _ = run_graph(req.question, request.app.state.graph)
    except Exception:
        logger.exception("Error processing question: %s", req.question)
        raise HTTPException(status_code=500, detail="Something went wrong. Please try again.")

    if len(cache) >= CACHE_MAX_SIZE:
        cache.popitem(last=False)
    cache[key] = result

    return AskResponse(answer=result)


@app.get("/stats")
async def stats():
    try:
        return get_stats()
    except Exception:
        logger.exception("Error generating stats")
        raise HTTPException(status_code=500, detail="Could not load stats.")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/debug/cache")
async def debug_cache(request: Request):
    cache = request.app.state.cache
    return {"size": len(cache), "keys": list(cache.keys())[:20]}