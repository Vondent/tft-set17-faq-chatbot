"""
FastAPI backend for TFT Set 17 FAQ chatbot.
Run from the chatbot/ directory:
  uvicorn api.main:app --host 0.0.0.0 --port 8000
"""

import logging
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, StringConstraints

from retrieval.retrieve import answer, get_index

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.index = get_index()
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
    try:
        result = answer(req.question, index=request.app.state.index)
    except Exception:
        logger.exception("Error processing question: %s", req.question)
        raise HTTPException(status_code=500, detail="Something went wrong. Please try again.")
    return AskResponse(answer=result)


@app.get("/health")
async def health():
    return {"status": "ok"}