"""
FastAPI backend for TFT Set 17 FAQ chatbot.
Run from the chatbot/ directory:
  uvicorn api.main:app --host 0.0.0.0 --port 8000
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from retrieval.retrieve import answer, get_collection

_collection = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _collection
    _collection = get_collection()
    yield


app = FastAPI(title="TFT Set 17 FAQ", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST"],
    allow_headers=["Content-Type"],
)


class AskRequest(BaseModel):
    question: str


class AskResponse(BaseModel):
    answer: str


@app.post("/ask", response_model=AskResponse)
async def ask(req: AskRequest):
    q = req.question.strip()
    if not q:
        raise HTTPException(status_code=400, detail="question must not be empty")
    try:
        result = answer(q, collection=_collection)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return AskResponse(answer=result)


@app.get("/health")
async def health():
    return {"status": "ok"}
