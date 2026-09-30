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

def test_the_voice_is_luna_and_the_watcher_stays_on_claude():
    if "CHAT_MODEL" not in os.environ:
        assert config.CHAT_MODEL == LUNA
    assert brain.via_openrouter(LUNA)
    assert not brain.via_openrouter("claude-haiku-4-5")
    # The watcher has its own default. Following the voice, it would have gone
    # to a Claude client that cannot call it — and safety.look never raises,
    # so it would have answered «no danger» to everybody, quietly.
    if "SAFETY_MODEL" not in os.environ:
        assert not brain.via_openrouter(config.SAFETY_MODEL)


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
