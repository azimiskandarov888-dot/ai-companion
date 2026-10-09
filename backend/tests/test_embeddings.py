"""Memory by meaning, through OpenRouter (app/embeddings.py).

It waited for an OpenAI key nobody had, so recall by meaning was silently off.
Pinned here: the one key there is, ONE host for every vector, nothing kept,
the person's words marked as a query — and a vector that is always the size
the stored ones are.
"""

from __future__ import annotations

import asyncio
import json
import math

import httpx

from app import brain, config, embeddings


def _router(monkeypatch, vector):
    sent: list[dict] = []

    def answer(request: httpx.Request) -> httpx.Response:
        sent.append({"path": request.url.path, **json.loads(request.content)})
        return httpx.Response(200, json={"data": [{"embedding": vector}]})

    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(brain, "_router_loop", None)
    monkeypatch.setattr(brain, "_router", httpx.AsyncClient(
        base_url=brain.ROUTER_URL, transport=httpx.MockTransport(answer)))
    return sent


def test_it_needs_only_the_key_the_owner_has(monkeypatch):
    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "test-key")
    assert "/" in config.EMBEDDING_MODEL and embeddings.available()


def test_one_host_nothing_kept_and_the_query_says_what_it_is(monkeypatch):
    sent = _router(monkeypatch, [0.6, 0.8])
    asyncio.run(embeddings.embed("внучка опять не звонит", query=True))
    asyncio.run(embeddings.embed("внучка Маша звонит по воскресеньям"))
    query, note = sent
    assert query["path"].endswith("/embeddings")
    assert query["provider"] == {"order": [config.EMBEDDING_PROVIDER], "allow_fallbacks": False,
                                 "zdr": True}
    assert query["input"].startswith("Instruct:") and query["input"].endswith("не звонит")
    assert note["input"] == "внучка Маша звонит по воскресеньям"


def test_a_host_that_ignores_the_size_still_gives_a_vector_of_the_size_kept(monkeypatch):
    _router(monkeypatch, [3.0] * 4096)
    vector = asyncio.run(embeddings.embed("что-то"))
    assert len(vector) == config.EMBEDDING_DIM
    assert math.isclose(sum(x * x for x in vector), 1.0)
