"""Embeddings for semantic memory recall.

We reuse the OpenAI key (already needed for Whisper) with a small, multilingual
embedding model — it handles Russian well. Similarity is plain cosine in Python,
which is instant at one-person scale (a few thousand memories at most).

If no OpenAI key is set, embeddings are simply unavailable and memory falls back
to recency-based recall — the companion still works.
"""

from __future__ import annotations

import math

from openai import AsyncOpenAI

from . import config

_client: AsyncOpenAI | None = None


def available() -> bool:
    return bool(config.OPENAI_API_KEY)


def _get_client() -> AsyncOpenAI:
    global _client
    if not config.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not set — embeddings unavailable.")
    if _client is None:
        _client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
    return _client


async def embed(text: str) -> list[float]:
    """Return the embedding vector for a piece of text."""
    client = _get_client()
    resp = await client.embeddings.create(
        model=config.EMBEDDING_MODEL,
        input=text[:8000],
        dimensions=config.EMBEDDING_DIM,
    )
    return list(resp.data[0].embedding)


def cosine(a: list[float] | None, b: list[float] | None) -> float:
    """Cosine similarity of two vectors (0.0 if either is missing/degenerate)."""
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)
