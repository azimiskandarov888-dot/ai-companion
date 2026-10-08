"""The owner's own test of every agent (backend/myself.py).

What has to hold for its verdicts to mean anything: every stage talks to the
model under test and no other, candidates running side by side never swap
models, and the material it feeds them is the app's own — his real talks with
his shadow, through the app's own prompts and road — not a copy that drifted.
"""

from __future__ import annotations

import asyncio
import json

import httpx
import pytest

import myself
from app import brain, config, memory, persona, reading, shaping, young


def _openrouter(reply):
    """A stand-in for OpenRouter: records what was sent, streams `reply(body)`."""
    sent: list[dict] = []

    def handle(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        sent.append(body)
        chunks = [{"choices": [{"delta": {"content": reply(body)}, "finish_reason": "stop"}]},
                  {"choices": [], "usage": {"cost": 0.01}}]
        stream = "".join(f"data: {json.dumps(c, ensure_ascii=False)}\n\n" for c in chunks)
        return httpx.Response(200, content=(stream + "data: [DONE]\n\n").encode("utf-8"),
                              headers={"content-type": "text/event-stream"})

    return httpx.AsyncClient(base_url=brain.ROUTER_URL, transport=httpx.MockTransport(handle)), sent


@pytest.fixture
def routed(monkeypatch):
    monkeypatch.setattr(brain, "think", myself._think)
    monkeypatch.setattr(brain, "generate_text", myself._generate_text)
    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(brain, "_router_loop", None)

    def install(reply):
        client, sent = _openrouter(reply)
        monkeypatch.setattr(brain, "_router", client)
        return sent

    return install


def test_the_reading_goes_to_the_model_under_test_with_the_apps_own_prompt(routed):
    sent = routed(lambda body: json.dumps(
        {"register": "коротко", "would_reach_them": "тихий"}, ensure_ascii=False))

    entry = asyncio.run(myself._one(
        "кто-то", "vendor/model", lambda: reading.read_talks("ЧЕЛОВЕК: мне двадцать, живу один")))

    assert entry["error"] is None
    assert entry["result"]["register"] == "коротко"
    assert entry["cost"] == 0.01
    [body] = sent
    assert body["model"] == "vendor/model"
    assert body["messages"][0]["content"] == reading._TALKS_SYSTEM
    assert "мне двадцать, живу один" in body["messages"][1]["content"]
    # The app's depth and the app's road — only the model is the candidate's.
    assert body["reasoning"] == {"effort": config.READING_EFFORT}
    assert body["max_tokens"] >= 32_000


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


def test_the_scribe_sees_every_exchange_and_his_own_first_hello():
    """What he says about himself is the writer's law — including in the hello
    he says before the person has said a word."""
    talks = [[{"role": "assistant", "content": "Привет. Как день?"},
              {"role": "user", "content": "нормально"},
              {"role": "assistant", "content": "А у меня тут дождь."}],
             [{"role": "user", "content": "снова я"},
              {"role": "assistant", "content": "Рад."}]]
    assert myself.exchanges(talks) == [("—", "Привет. Как день?"),
                                       ("нормально", "А у меня тут дождь."),
                                       ("снова я", "Рад.")]


def test_the_shadow_he_becomes_is_held_for_the_owner_and_starts_from_nothing(monkeypatch):
    """«Совсем заново»: the previous friend goes with everything that was; and
    while the owner tests, the app does not write him first."""
    monkeypatch.setattr(myself, "_save", lambda *a, **k: None)
    uid = myself._me()
    persona.save_persona(uid, {"name": "Старый", "personality": "был"})
    memory.log_turn(uid, "user", "старый разговор")
    stranger = {"name": "Лукас", "gender": "мужской", "age": "16 лет",
                "home": "Лиссабон, Португалия", "doing": "учится", "now": "экзамены"}
    record = {"pick": "А", "door": {"name": "Азим", "age": "15", "country": "Узбекистан",
                                    "wants": ""},
              "entries": [{"label": "А", "result": [stranger]}]}
    myself._become_shadow(record)

    who = persona.load_persona(uid)
    assert persona.is_shadow(who) and who["_held"] and who["name"] == "Лукас"
    assert not shaping.waiting(uid)
    assert young.of(uid) == young.TEEN
    assert memory.recent_turns(uid) == []
    assert "Азим" in memory.facts_context(uid)


def test_the_stages_read_his_real_talks_as_the_app_does(monkeypatch):
    uid = myself._me()
    persona.save_persona(uid, {"name": "Лукас", "shadow": True})
    memory.log_turn(uid, "assistant", "Привет.")
    memory.log_turn(uid, "user", "привет, я из Ташкента")
    _uid, said = myself._talked()
    assert said == shaping.transcript(uid, "Лукас")
    assert "ЧЕЛОВЕК: привет, я из Ташкента" in said and "ЛУКАС: Привет." in said
