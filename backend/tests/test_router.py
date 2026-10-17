"""The voice through OpenRouter — GPT-5.6 Luna since 2026-09-28.

Chosen on 24 rehearsed first meetings (docs/VOICE-MODELS-REHEARSAL.md), and
sent the same prompt, history and length limit it was chosen on. Pinned here is
everything that would otherwise first show up in front of somebody: the shape
of the call, how a stream is read, what happens at the length limit, the glitch
the rehearsals caught, and an empty account named for what it is.
"""

from __future__ import annotations

import asyncio
import json
import os

import httpx
import pytest

from app import brain, config

LUNA = "openai/gpt-5.6-luna"
GEMMA = "google/gemma-4-31b-it"
HEARD = [{"role": "user", "content": "привет"}]


def _delta(text: str, finish: str | None = None) -> dict:
    return {"choices": [{"delta": {"content": text}, "finish_reason": finish}]}


def _sse(*chunks: dict, done: bool = True) -> bytes:
    """An OpenRouter stream as it comes: a keep-alive comment, data lines, [DONE]."""
    lines = [": OPENROUTER PROCESSING", ""]
    for chunk in chunks:
        lines += [f"data: {json.dumps(chunk, ensure_ascii=False)}", ""]
    if done:
        lines += ["data: [DONE]", ""]
    return "\n".join(lines).encode("utf-8")


class _OpenRouter:
    """OpenRouter, answered here: every request body kept, one answer given."""

    def __init__(self) -> None:
        self.sent: list[dict] = []
        self.status = 200
        self.body = _sse(_delta("Привет."), _delta("", "stop"))

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.sent.append(json.loads(request.content))
        return httpx.Response(self.status, content=self.body,
                              headers={"content-type": "text/event-stream"})


@pytest.fixture
def router(monkeypatch):
    answer = _OpenRouter()
    monkeypatch.setattr(config, "CHAT_MODEL", LUNA)
    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(brain, "_router", httpx.AsyncClient(
        base_url=brain.ROUTER_URL, transport=httpx.MockTransport(answer)))
    return answer


def _reply(**kw) -> str:
    return asyncio.run(brain.generate_reply(HEARD, "КТО ТЫ", "СЕГОДНЯ", **kw))


def _streamed() -> list[str]:
    async def drain():
        return [text async for text in brain.stream_reply(HEARD, "КТО ТЫ", "СЕГОДНЯ")]
    return asyncio.run(drain())


# ── who is speaking ─────────────────────────────────────────────────────────

def test_the_voice_is_gemma_and_the_watcher_has_a_model_of_its_own():
    """Gemma 4 since 2026-10-02 — the owner's ear, four blind conversations
    (config.CHAT_MODEL). The router tests below talk to Luna on purpose: what
    they pin is how a reply is sent and read, whoever the model is."""
    if "CHAT_MODEL" not in os.environ:
        assert config.CHAT_MODEL == GEMMA
    assert brain.via_openrouter(GEMMA) and brain.via_openrouter(LUNA)
    assert not brain.via_openrouter("claude-haiku-4-5")
    # The watcher has its own default, never the voice's: chosen by a labelled
    # crisis set, not by whoever happens to talk. It once followed the voice
    # onto a client that could not call it — and safety.look never raises, so
    # it would have answered «no danger» to everybody, quietly. Now every road
    # is callable (below), and the separation is about choice, not plumbing.
    if "SAFETY_MODEL" not in os.environ:
        assert config.SAFETY_MODEL != config.CHAT_MODEL


def test_each_model_goes_to_its_own_fastest_place(monkeypatch):
    """OpenAI's places serve only OpenAI's models. Gemma has a measured order
    of its own: asked to sort by latency, OpenRouter sent her to SiliconFlow —
    first words in 2.0–3.5 s, against 0.33–0.45 s at ModelRun (2026-10-03) —
    and one host for the whole conversation keeps its prompt cache warm."""
    monkeypatch.setattr(config, "CHAT_PROVIDERS", [])
    assert brain._where(LUNA)["order"][0] == "openai/fast"
    assert brain._where(GEMMA) == {"order": config.CHAT_PROVIDERS_FOR[GEMMA], "allow_fallbacks": True}
    assert brain._where(GEMMA)["order"][0] == "modelrun/fp4"
    # A model nobody has measured: the fastest place right now.
    assert brain._where("mistralai/some-new-model") == {"sort": "latency", "allow_fallbacks": True}
    # An order set by hand is an order for any model, still with fallbacks.
    monkeypatch.setattr(config, "CHAT_PROVIDERS", ["deepinfra"])
    assert brain._where(GEMMA) == {"order": ["deepinfra"], "allow_fallbacks": True}


def test_he_reads_ahead_what_the_next_reply_will_begin_with(router):
    """brain.prewarm: the instructions and the conversation so far, in the same
    order and to the same host as the reply that follows, so the host can
    reuse what it read — one token, nobody waiting on it."""
    history = [{"role": "assistant", "content": "Привет. Как день?"},
               {"role": "user", "content": "Нормально."},
               {"role": "assistant", "content": "А чем занимался?"}]
    router.body = json.dumps({"choices": [{"message": {"content": "О"}}]}).encode()
    asyncio.run(brain.prewarm(history, "КТО ТЫ"))
    [sent] = router.sent
    assert sent["max_tokens"] == 1 and sent["stream"] is False
    assert sent["messages"][0] == {"role": "system", "content": "КТО ТЫ"}
    assert sent["messages"][1:-1] == [{"role": "user", "content": "…"}, *history]
    assert sent["messages"][-1] == {"role": "user", "content": "…"}
    assert sent["provider"] == brain._where(config.CHAT_MODEL)
    # …and a host that is down costs nothing but the warm-up.
    router.status = 500
    asyncio.run(brain.prewarm(history, "КТО ТЫ"))


# ── what he is sent ─────────────────────────────────────────────────────────

def test_he_is_sent_what_the_meetings_were_rehearsed_on(router):
    _reply()
    [sent] = router.sent
    assert sent["model"] == LUNA
    assert sent["max_tokens"] == config.MAX_REPLY_TOKENS
    # The character first (cached with the conversation after it); what is true
    # now LAST, right before the answer, where a model that does not stop to
    # think still reads it.
    assert sent["messages"] == [
        {"role": "system", "content": "КТО ТЫ"},
        {"role": "user", "content": "привет"},
        {"role": "system", "content": "СЕГОДНЯ"},
    ]
    assert "plugins" not in sent


def test_he_goes_to_the_fastest_place_and_does_not_think_first(router):
    """Left to itself OpenRouter chose where to send him: first words in 1.46 s,
    against 0.79 s from OpenAI's fast tier (median of three, 2026-09-29) — and
    Luna now and then reasoned silently for a second before saying anything."""
    _reply()
    sent = router.sent[0]
    assert sent["provider"]["order"][0] == "openai/fast"
    assert sent["provider"]["allow_fallbacks"] is True     # slower, never silent
    assert sent["reasoning"] == {"effort": "none"}


def test_an_empty_tail_adds_nothing():
    sent = brain._router_body(HEARD, "КТО ТЫ", "  ")
    assert sent["messages"] == [{"role": "system", "content": "КТО ТЫ"}, *HEARD]


def test_a_question_about_the_world_searches_and_is_asked_not_to_cite(router):
    """Everything he writes is read aloud, and a link read aloud is an address."""
    _reply(fresh_info=True)
    [plugin] = router.sent[0]["plugins"]
    assert plugin["id"] == "web"
    assert plugin["max_results"] == 3
    assert "без ссылок" in plugin["search_prompt"]


def test_the_model_searches_for_itself(router):
    """OpenRouter's default for OpenAI, kept on purpose: asked the weather in
    Tashkent, it had today's, where Exa's pages had a different day's."""
    _reply(fresh_info=True)
    assert "engine" not in router.sent[0]["plugins"][0]


def test_a_source_it_cites_anyway_is_taken_out(router):
    """Seen on the first real search turn: «…грозы. ([nuz.uz](https://…))»."""
    router.body = _sse(_delta(
        "В горах возможны грозы. ([nuz.uz](https://nuz.uz/2026/09/28/p/?utm_source=openai))"
        "\n\nПишут в [Газете](https://gazeta.uz/x), что тепло. "
        "И форум идёт ([a.uz](https://a.uz/1), [b.uz](https://b.uz/2))."), _delta("", "stop"))
    assert _reply(fresh_info=True) == (
        "В горах возможны грозы.\n\nПишут в Газете, что тепло. И форум идёт.")


# ── how the answer is read ──────────────────────────────────────────────────

def test_the_stream_is_read_as_it_is_written(router):
    router.body = _sse(_delta("Доброе "), _delta("утро."), _delta(" Как спалось?"),
                       _delta("", "stop"))
    assert _streamed() == ["Доброе ", "Доброе утро.", "Доброе утро. Как спалось?"]


def test_the_whole_reply_is_read_off_a_stream_too(router):
    """So the live timeout stays a stall detector, as on the Claude path: a
    search that is slow but working keeps sending, and is never cut off for it."""
    router.body = _sse(_delta("Доброе "), _delta("утро. "), _delta("", "stop"))
    assert _reply() == "Доброе утро."
    assert router.sent[0]["stream"] is True


def test_a_reply_cut_off_by_the_limit_ends_on_its_last_whole_sentence(router):
    router.body = _sse(_delta("Море успокаивает. "), _delta("Можно фантазировать с цвет"),
                       _delta("", "length"))
    assert _reply() == "Море успокаивает."
    # Streamed, the last value is SHORTER: the unfinished tail is never spoken.
    assert _streamed()[-1] == "Море успокаивает."


def test_a_word_from_another_alphabet_is_never_said(router):
    """The rehearsals caught Luna ending a reply «…видно особенно ясно.АҞӘА»
    (Abkhaz) — and, later, «…ожидание разгрузки.อ่านข้อความเต็ม» (Thai)."""
    router.body = _sse(_delta("…видно особенно ясно."), _delta("АҞ"), _delta("ӘА"),
                       _delta("", "stop"))
    assert _reply() == "…видно особенно ясно."
    assert all("Ҟ" not in text and "Ә" not in text for text in _streamed())
    assert brain.without_glitches("…ожидание разгрузки.อ่านข้อความเต็ม") == "…ожидание разгрузки."
    assert brain.without_glitches("Да 你好 ладно.") == "Да  ладно."
    assert brain.without_glitches("Ну مرحبا!") == "Ну !"


def test_russian_latin_and_numbers_are_left_alone():
    ordinary = ("Ёлка, YouTube и «Щёлково» — в 2026 году, ё-моё. Играю в Riders "
                "Republic и Stardew Valley. Café, naïve, 25°C, №5, ½, x², вне́шний.")
    assert brain.without_glitches(ordinary) == ordinary


def test_a_scrap_of_markup_is_never_said(router):
    """Without reasoning the voice glued «>xpath» onto a sentence (2026-09-30)
    — and the voice would have read it out. What is glued to a code character
    goes; his body's //МАРКЕРЫ// stay."""
    router.body = _sse(_delta("Ноги, наверное, уже гудят."), _delta(">x"), _delta("path"),
                       _delta("", "stop"))
    assert _reply() == "Ноги, наверное, уже гудят."
    assert all("xpath" not in text and ">" not in text for text in _streamed())
    assert brain.without_glitches("Ну давай, до завтра. //КОНЕЦ//") == "Ну давай, до завтра. //КОНЕЦ//"
    assert brain.without_glitches("Кхм //КАШЕЛЬ// ну вот.>xp дальше") == "Кхм //КАШЕЛЬ// ну вот. дальше"


def test_a_lone_receipt_at_the_head_of_a_reply_is_never_said(router):
    """«Понял, Азим.» opened the reply the owner called robotic (2026-09-30). It
    is held back while it could still be one — so no piece of it is ever cut off
    and spoken — and taken off once more follows."""
    router.body = _sse(_delta("Понял"), _delta(", Азим"), _delta(". "), _delta("Программу"),
                       _delta(" пишешь?"), _delta("", "stop"))
    streamed = _streamed()
    assert streamed[-1] == "Программу пишешь?"
    assert all("Понял" not in text for text in streamed)
    router.body = _sse(_delta("Понятно."), _delta("", "stop"))
    assert _streamed() == ["Понятно."]                         # nothing else to say: said
    assert brain.without_receipt("Понимаю, как тебе тяжело.") == "Понимаю, как тебе тяжело."
    assert brain.without_receipt("Ясно, что ничего не ясно.") == "Ясно, что ничего не ясно."


# ── when it goes wrong ─────────────────────────────────────────────────────

def test_an_empty_account_is_named_for_what_it_is(router):
    """OpenRouter's own words for it send you to shorten a prompt that is fine."""
    router.status = 402
    router.body = b'{"error":{"message":"Prompt tokens limit exceeded"}}'
    with pytest.raises(RuntimeError, match="кончились деньги"):
        _reply()


def test_an_error_in_the_middle_of_a_stream_is_not_taken_for_the_end(router):
    router.body = _sse(_delta("Доброе "), {"error": {"message": "provider down"}}, done=False)
    with pytest.raises(RuntimeError, match="provider down"):
        _streamed()


def test_a_line_from_a_finished_loop_is_not_reused(monkeypatch):
    """A tool that runs asyncio.run twice must not be handed a connection from
    the first, dead loop — but within one loop the line is kept."""
    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(brain, "_router", None)
    monkeypatch.setattr(brain, "_router_loop", None)

    async def twice():
        return brain._get_router(), brain._get_router()

    first, second = asyncio.run(twice())
    assert first is second

    async def once():
        return brain._get_router()

    assert asyncio.run(once()) is not first


def test_the_line_is_watched_for_stalls_and_the_key_is_named(monkeypatch):
    monkeypatch.setattr(brain, "_router", None)
    monkeypatch.setattr(config, "OPENROUTER_API_KEY", None)
    with pytest.raises(RuntimeError, match="OPENROUTER_API_KEY"):
        brain._get_router()
    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "test-key")
    assert brain._get_router().timeout.read == brain._LIVE_REPLY_TIMEOUT


# ── the background agents' road (2026-10-08) ────────────────────────────────
#
# The reader, the writer, the scribe, his week, the diary and the watcher go
# through OpenRouter when their id has a «/». Before, they had Anthropic's road
# only, and the owner's machine has no Anthropic key: every one of them quietly
# did nothing — the watcher answered «no danger» to everybody.

AGENTS = ("BRAIN_MODEL", "SCRIBE_MODEL", "READING_MODEL", "WRITER_MODEL", "INTAKE_MODEL", "SAFETY_MODEL")


@pytest.fixture
def background(monkeypatch):
    answer = _OpenRouter()
    answer.body = _sse(_delta('{"facts": '), _delta("[]}"), _delta("", "stop"),
                       {"choices": [], "usage": {"cost": 0.0123}})
    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(brain, "_router_loop", None)
    monkeypatch.setattr(brain, "_router", httpx.AsyncClient(
        base_url=brain.ROUTER_URL, transport=httpx.MockTransport(answer)))
    return answer


def test_every_agent_can_be_called_on_the_one_key_the_owner_has(monkeypatch):
    """Only OPENROUTER_API_KEY in .env — the owner's machine — and nothing may
    quietly do nothing."""
    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "test-key")
    for name in AGENTS:
        if name not in os.environ and not (name == "BRAIN_MODEL" and "ANTHROPIC_MODEL" in os.environ):
            assert brain.can_call(getattr(config, name)), name


def test_a_key_is_asked_of_the_road_the_model_takes(monkeypatch):
    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "test-key")
    assert brain.can_call("anthropic/claude-opus-5")
    assert not brain.can_call("claude-opus-5")          # Anthropic's road, no key for it
    monkeypatch.setattr(config, "OPENROUTER_API_KEY", None)
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "test-key")
    assert brain.can_call("claude-opus-5")
    assert not brain.can_call("anthropic/claude-opus-5")


def test_a_background_call_goes_to_openrouter_as_it_was_asked(background):
    said = asyncio.run(brain.generate_text("КАК ВЕСТИ ПАМЯТЬ", "ЧТО СКАЗАНО",
                                           max_tokens=120, model="anthropic/claude-sonnet-5"))
    assert said == '{"facts": []}'
    sent = background.sent[0]
    assert sent["model"] == "anthropic/claude-sonnet-5"
    assert sent["messages"] == [{"role": "system", "content": "КАК ВЕСТИ ПАМЯТЬ"},
                                {"role": "user", "content": "ЧТО СКАЗАНО"}]
    # Not asked to think — the scribe must not (it invents 2–3× more), and the
    # watcher has no second to spare. Room enough for a model that thinks anyway.
    assert "reasoning" not in sent
    assert sent["max_tokens"] >= 4_000
    assert sent["stream"] is True


def test_thinking_through_openrouter_keeps_its_effort_and_room_for_the_answer(background):
    asyncio.run(brain.think("ЧИТАЙ", "ЕГО СЛОВА", model="anthropic/claude-opus-5", effort="max",
                            max_tokens=8000))
    sent = background.sent[0]
    # As asked: OpenRouter offers Opus up to «max» (catalogue, 2026-10-09). It
    # used to be folded into «high», and xhigh could never be tested.
    assert sent["reasoning"] == {"effort": "max"}
    # A writer that thought well and was cut off before the closing brace would
    # lose a person for nothing of its own.
    assert sent["max_tokens"] >= 32_000
    # …but ten one-line strangers at «low» are not asked to have room for a
    # novel: a ceiling the balance cannot cover is refused outright (402).
    asyncio.run(brain.generate_text("A", "B", model="anthropic/claude-opus-5", effort="low",
                                    max_tokens=2000))
    assert 2000 < background.sent[1]["max_tokens"] <= 8_000


def test_what_each_call_cost_is_counted_for_whoever_asked(background):
    """The owner's test prints the real price of every candidate — from here."""
    async def two_calls():
        brain.bill.set(spent := {})
        await brain.generate_text("A", "B", model="z-ai/glm-5.3")
        await brain.generate_text("A", "B", model="z-ai/glm-5.3")
        return spent

    spent = asyncio.run(two_calls())
    assert spent == {"cost": pytest.approx(0.0246), "calls": 2}
    assert brain.bill.get() is None          # nobody else's calls were billed to it


def test_an_empty_account_stops_a_background_agent_in_the_same_words(background):
    background.status = 402
    background.body = b'{"error": {"message": "This request requires more credits"}}'
    with pytest.raises(RuntimeError, match="пополни"):
        asyncio.run(brain.generate_text("A", "B", model="anthropic/claude-opus-5"))


def test_an_empty_answer_is_a_failure_not_a_silent_nothing(background):
    """Every agent already survives a failed call — the reading is skipped, the
    batch waits for the next turn. An empty string would instead be taken as
    an answer: a friend written from nothing, a batch marked read."""
    background.body = _sse(_delta("", "length"))
    with pytest.raises(RuntimeError, match="пустой ответ"):
        asyncio.run(brain.think("A", "B", model="anthropic/claude-opus-5"))


def test_every_background_call_asks_that_nothing_be_kept(background):
    """A person's own talk, and the reading of them — the most private thing
    the app holds. Every model the app or the test uses has such a route."""
    asyncio.run(brain.generate_text("A", "B", model="anthropic/claude-haiku-5.5"))
    assert background.sent[0]["provider"] == {"zdr": True}


def test_thinking_switched_off_is_said_in_each_vendors_words(background):
    """Left alone, Sonnet 5 thinks at «high» and Haiku 5.5 at «medium» before
    every answer — for the scribe, dearer and more invented."""
    for model in ("anthropic/claude-haiku-5.5", "openai/gpt-5.4-nano", "deepseek/deepseek-v4.1-flash"):
        asyncio.run(brain.generate_text("A", "B", model=model, effort="none"))
    claude, gpt, deepseek = (sent["reasoning"] for sent in background.sent)
    assert claude == {"enabled": False} and deepseek == {"enabled": False}
    assert gpt == {"effort": "none"}
    assert all(sent["max_tokens"] <= 4_000 for sent in background.sent)   # no room to think bought


def test_a_model_that_must_think_is_asked_once_more_at_a_level_it_takes(background):
    """GLM-5.3 and Gemini 3.8 Flash cannot switch thinking off; Kimi K3 has no
    «xhigh». A 400 about it is not the end of the call."""
    answers = iter([
        (400, b'{"error":{"message":"Reasoning is mandatory for this model"}}'),
        (200, _sse(_delta("ok"), _delta("", "stop"))),
    ])

    def answer(request):
        background.sent.append(json.loads(request.content))
        status, body = next(answers)
        return httpx.Response(status, content=body, headers={"content-type": "text/event-stream"})

    brain._router = httpx.AsyncClient(base_url=brain.ROUTER_URL, transport=httpx.MockTransport(answer))
    assert asyncio.run(brain.generate_text("A", "B", model="z-ai/glm-5.3", effort="none")) == "ok"
    assert background.sent[0]["reasoning"] == {"enabled": False}
    assert background.sent[1]["reasoning"] == {"effort": "low"}


@pytest.mark.parametrize("stream", [False, True])
def test_moderation_is_told_apart_from_any_other_failure(background, stream):
    """Every Anthropic and OpenAI model on OpenRouter is moderated, and what it
    stops is the heaviest thing a person says: the watcher and the scribe must
    be able to ask somebody else — so a refusal has a name of its own, whether
    it comes as a 403 or inside a stream that began «200 OK»."""
    if stream:
        background.body = _sse({"error": {"code": 403, "message": "flagged"}}, done=False)
    else:
        background.status = 403
        background.body = b'{"error":{"code":403,"message":"Input was flagged","metadata":{"reasons":["self-harm"]}}}'
    with pytest.raises(brain.Refused):
        asyncio.run(brain.generate_text("A", "B", model="anthropic/claude-haiku-4.5", effort="none"))
