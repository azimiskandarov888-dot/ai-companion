"""Embeddings for semantic memory recall.

THROUGH OPENROUTER SINCE 2026-10-09 (docs/MODELS-RESEARCH-2026-10-09.md): it
used to reach OpenAI's text-embedding-3-small with an OpenAI key that nobody
had — so recall by meaning was silently off, and he took the newest stories
instead of the right ones. Now an id with a «/» goes to OpenRouter's
embeddings endpoint on the one key there is. The model is Qwen3-Embedding-8B:
the best Russian similarity of any model an API serves (ruMTEB: 71.4 average,
78.2 retrieval, 79.3 similarity — text-embedding-3-small scores 60.1 on the
Russian retrieval task, below a free small model), $0.01 a million tokens,
under a cent a person a month.

Every vector comes from ONE host (config.EMBEDDING_PROVIDER, no fallbacks):
vectors that are compared must come from the same place, and two hosts of the
same model can differ (one serves it at fp8). Zero retention, like every
background call. Changing the model means embedding the stored notes again —
a fraction of a cent for thousands.

A bare id («text-embedding-3-small») still goes to OpenAI as before. With
neither key, embeddings are simply unavailable and memory falls back to
recency-based recall — the companion still works. Similarity is plain cosine
in Python, which is instant at one-person scale.
"""

from __future__ import annotations

import math

from . import config

_client = None

#: Qwen3-Embedding wants the QUERY to say what it is for — not the stored
#: note; without it, retrieval loses 1–5% (its model card). In English, as the
#: model's authors recommend even for other languages.
_QUERY = "Instruct: Find what this person said before that relates to these words\nQuery: "


def _routed() -> bool:
    return "/" in (config.EMBEDDING_MODEL or "")


def available() -> bool:
    return bool(config.OPENROUTER_API_KEY if _routed() else config.OPENAI_API_KEY)


def _get_client():
    global _client
    if not config.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not set — embeddings unavailable.")
    if _client is None:
        from openai import AsyncOpenAI   # only on the OpenAI road

        _client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
    return _client


def fit(vector: list[float], size: int) -> list[float]:
    """At most `size` numbers, unit length. A host that ignores `dimensions`
    sends the whole vector; Qwen3's are made to be cut (Matryoshka), so the
    head is kept and scaled back to unit length — and every stored vector
    stays the size it was."""
    head = list(vector[:size]) if size and len(vector) > size else list(vector)
    norm = math.sqrt(sum(x * x for x in head))
    return [x / norm for x in head] if norm else head


async def embed(text: str, *, query: bool = False) -> list[float]:
    """The embedding of a piece of text. `query`: these are the person's
    words to search WITH, not a note to keep."""
    if _routed():
        return await _through_router(text, query=query)
    client = _get_client()
    resp = await client.embeddings.create(
        model=config.EMBEDDING_MODEL,
        input=text[:8000],
        dimensions=config.EMBEDDING_DIM,
    )
    return list(resp.data[0].embedding)


async def _through_router(text: str, *, query: bool) -> list[float]:
    from . import brain   # local: brain never needs this module

    asked = (_QUERY if query and "qwen3-embedding" in config.EMBEDDING_MODEL else "") + text[:8000]
    provider: dict = {"order": [config.EMBEDDING_PROVIDER], "allow_fallbacks": False}
    if config.BACKGROUND_ZDR:
        provider["zdr"] = True
    r = await brain._get_router().post("/embeddings", json={
        "model": config.EMBEDDING_MODEL,
        "input": asked,
        "dimensions": config.EMBEDDING_DIM,
        "provider": provider,
    })
    if r.status_code != 200:
        raise brain._router_failed(r.status_code, r.text)
    return fit(r.json()["data"][0]["embedding"], config.EMBEDDING_DIM)


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
