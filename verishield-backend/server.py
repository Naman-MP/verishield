"""Local text analysis API for the VeriShield Chrome extension."""

from __future__ import annotations

import re
from functools import lru_cache
from threading import Lock

from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

MODEL_ID = "openai-community/roberta-base-openai-detector"
MAX_HTML_CHARS = 30_000
MAX_TEXT_CHARS = 12_000
MIN_WORDS = 30
_inference_lock = Lock()

app = FastAPI(title="VeriShield Local API", version="0.1.0")


class VerifyRequest(BaseModel):
    html: str = Field(min_length=1, max_length=MAX_HTML_CHARS)


class VerifyResponse(BaseModel):
    status: str
    ai_probability: float | None
    model_confidence: float | None
    word_count: int
    method: str
    model: str | None
    detail: str


def extract_text_from_elements(raw_html: str) -> str:
    """Keep article-like copy and discard page chrome and executable content."""
    soup = BeautifulSoup(raw_html, "html.parser")
    for tag in soup.select(".verishield-root, .verishield-hud"):
        tag.decompose()
    for tag in soup.find_all(
        ["script", "style", "nav", "aside", "footer", "header", "form", "button", "svg", "noscript"]
    ):
        tag.decompose()

    blocks = [node.get_text(" ", strip=True) for node in soup.find_all(["p", "h1", "h2", "h3", "blockquote", "li"])]
    meaningful = [block for block in blocks if len(block.split()) >= 4]
    text = " ".join(meaningful) if meaningful else soup.get_text(" ", strip=True)
    return re.sub(r"\s+", " ", text).strip()[:MAX_TEXT_CHARS]


@lru_cache(maxsize=1)
def _load_model():
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    try:
        # Prefer a complete local cache, avoiding network checks on later runs.
        tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, local_files_only=True)
        model = AutoModelForSequenceClassification.from_pretrained(
            MODEL_ID, local_files_only=True, use_safetensors=True
        )
    except OSError:
        tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
        model = AutoModelForSequenceClassification.from_pretrained(MODEL_ID, use_safetensors=True)
    model.eval()
    return torch, tokenizer, model


def _predict(text: str) -> tuple[float, float]:
    # Model loading and CPU inference are serialized to avoid memory spikes.
    with _inference_lock:
        torch, tokenizer, model = _load_model()
        encoded = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
        with torch.inference_mode():
            probabilities = torch.softmax(model(**encoded).logits, dim=-1)[0]
        fake_index = next(
            (index for index, label in model.config.id2label.items() if label.lower() == "fake"),
            None,
        )
        if fake_index is None:
            raise RuntimeError("Model has no Fake class")
        ai_probability = float(probabilities[int(fake_index)])
        return ai_probability, float(probabilities.max())


@app.get("/health")
def health():
    return {"status": "ok", "model": MODEL_ID, "loaded": _load_model.cache_info().currsize > 0}


@app.post("/verify", response_model=VerifyResponse)
async def verify(request: VerifyRequest):
    from starlette.concurrency import run_in_threadpool

    text = extract_text_from_elements(request.html)
    word_count = len(text.split())
    if word_count < MIN_WORDS:
        return VerifyResponse(
            status="insufficient_text",
            ai_probability=None,
            model_confidence=None,
            word_count=word_count,
            method="none",
            model=None,
            detail=f"At least {MIN_WORDS} words are needed for analysis.",
        )

    try:
        probability, confidence = await run_in_threadpool(_predict, text)
    except Exception as exc:
        # The extension can show its clearly labelled local heuristic if the model
        # is unavailable (for example, on first run without a model download).
        raise HTTPException(status_code=503, detail="Text model unavailable") from exc

    return VerifyResponse(
        status="analyzed",
        ai_probability=round(probability * 100, 1),
        model_confidence=round(confidence * 100, 1),
        word_count=word_count,
        method="model",
        model=MODEL_ID,
        detail="GPT-2 detector estimate; this is not proof of authorship or accuracy.",
    )
