"""The owner's own test of every agent (backend/myself.py).

What has to hold for its verdicts to mean anything: every stage talks to the
model under test and no other, candidates running side by side never swap
models, and the material it feeds them is the app's own — not a copy that
drifted.
"""

from __future__ import annotations

import asyncio
import json

import httpx
import pytest

import myself
from app import brain, config, reading


def _openrouter(reply):
    """A stand-in for OpenRouter: records what was sent, answers `reply(body)`."""
    sent: list[dict] = []

    def handle(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        sent.append(body)
        return httpx.Response(200, json={
            "choices": [{"message": {"content": reply(body)}, "finish_reason": "stop"}],
            "usage": {"cost": 0.01},
        })

    return httpx.AsyncClient(transport=httpx.MockTransport(handle)), sent


@pytest.fixture
def routed(monkeypatch):
    monkeypatch.setattr(brain, "think", myself._think)
    monkeypatch.setattr(brain, "generate_text", myself._generate_text)

    def install(reply):
        client, sent = _openrouter(reply)
        monkeypatch.setattr(myself, "_client", client)
        return sent

    return install


def test_the_warm_up_is_read_from_the_app_rather_than_copied():
    """A second copy of the warm-up beside the Swift one would drift on the
    first edit, and the reading would then judge a conversation the app does
    not have."""
    steps = myself.warm_up()
    assert steps[0]["say"] == "Как вас зовут?"
    assert len(steps) == 8
    # The two answers the server also needs on their own — exactly one each.
    assert sum(s["country"] for s in steps) == 1
    assert sum(s["age"] for s in steps) == 1
    gender = next(s for s in steps if "мужчина или женщина" in s["say"])
    assert gender["options"] == ["Мужчина", "Женщина", "Иначе"]


def test_the_reading_goes_to_the_model_under_test_with_the_apps_own_prompt(routed):
    sent = routed(lambda body: json.dumps(
        {"register": "коротко", "would_reach_them": "тихий"}, ensure_ascii=False))

    entry = asyncio.run(myself._one(
        "кто-то", "vendor/model", lambda: reading.read_person("мне двадцать, живу один")))

    assert entry["error"] is None
    assert entry["result"]["register"] == "коротко"
    assert entry["cost"] == 0.01
    [body] = sent
    assert body["model"] == "vendor/model"
    assert body["messages"][0]["content"] == reading._READING_SYSTEM
    assert "мне двадцать, живу один" in body["messages"][1]["content"]
    # The app's depth is kept; only the ceiling is raised, so a model that
    # thinks longer than Claude is not cut off mid-answer.
    assert body["reasoning"] == {"effort": config.READING_EFFORT}
    assert body["max_tokens"] >= 20_000


def test_candidates_side_by_side_never_swap_models(routed):
    """They run at once, in one event loop. A global «current model» would
    hand the second one's answers to the first."""
    routed(lambda body: body["model"])

    async def both():
        return await asyncio.gather(*(
            myself._one(m, m, lambda: brain.generate_text("s", "u"))
            for m in ("a/one", "b/two", "c/three")
        ))

    for entry in asyncio.run(both()):
        assert entry["result"] == entry["model"]


def test_a_failing_provider_costs_one_line_not_the_stage(routed):
    routed(lambda body: "")  # an empty answer is a failure, never a result
    entry = asyncio.run(myself._one("x", "x/y", lambda: brain.generate_text("s", "u")))
    assert entry["result"] is None
    assert "пустой ответ" in entry["error"]


def test_the_mix_takes_five_from_each_in_turn():
    a = [f"a{i}" for i in range(10)]
    b = [f"b{i}" for i in range(10)]
    assert myself.mixed(a, b) == ["a0", "b0", "a1", "b1", "a2", "b2", "a3", "b3", "a4", "b4"]


def test_the_scribe_reads_only_the_chosen_voice():
    paper = (
        "# Прослушивание\n\nшапка\n"
        "\n---\n\n## Ты: привет\n"
        "\n**А**  (1.0 с)\n\nздорово\n"
        "\n**Б**  (1.2 с)\n\nну привет\nкак ты\n"
        "\n---\n\n## Ты: устал\n"
        "\n**А**  (0.9 с)\n\nотдохни\n"
        "\n**Б**  (1.1 с)\n\nот чего?\n"
    )
    assert myself.exchanges(paper, "Б") == [("привет", "ну привет\nкак ты"),
                                           ("устал", "от чего?")]
