"""Brain wiring: the web-search tool, caching, and call timeouts.

The timeout tests exist because of a real incident: on a degraded connection,
the Anthropic SDK's own default read timeout (600s) let the backend sit
silently for minutes while the phone had already given up in 25-30s — which
looks, from the outside, exactly like the app freezing, with no error
anywhere to explain it. See the long comment above _LIVE_REPLY_TIMEOUT in
brain.py for the full account.
"""

from __future__ import annotations

import asyncio

from app import brain

# --------------------------------------------------------------------------- #
# A minimal stand-in for the Anthropic SDK, just enough to see what a call
# was asked to do. Real network behaviour (what a timeout actually causes) is
# the SDK's to get right; ours is only "did we ask for one, and for how long".
# --------------------------------------------------------------------------- #
class _Block:
    def __init__(self, text: str):
        self.type = "text"
        self.text = text


class _Message:
    def __init__(self, text: str, stop_reason: str = "end_turn"):
        self.content = [_Block(text)]
        self.stop_reason = stop_reason


class _FakeStream:
    def __init__(self, message: _Message | None, events: list[_Block]):
        self._message = message
        self._events = events

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        return False

    async def get_final_message(self):
        return self._message

    def __aiter__(self):
        return self._aiter()

    async def _aiter(self):
        for event in self._events:
            yield event


class _FakeMessages:
    def __init__(self, message: _Message | None = None, events: list[_Block] | None = None):
        self.calls: list[dict] = []
        self._message = message
        self._events = events or []

    def stream(self, **kwargs):
        self.calls.append(kwargs)
        return _FakeStream(self._message, self._events)


class _FakeClient:
    def __init__(self, message: _Message | None = None, events: list[_Block] | None = None):
        self.messages = _FakeMessages(message, events)


def test_web_search_tool_configured():
    tool = brain._WEB_SEARCH_TOOL
    assert tool["name"] == "web_search"
    assert tool["type"].startswith("web_search_")
    # Capped so one question can't spiral into many searches.
    assert tool["max_uses"] >= 1


def test_search_only_when_the_world_is_asked_about():
    """The tool is attached per-turn, not always: its mere availability invites
    the model to consider it, and a search turn costs seconds of silence."""
    assert brain.wants_fresh_info("Какая сегодня погода?")
    assert brain.wants_fresh_info("что там в новостях?")
    assert brain.wants_fresh_info("Какой курс доллара?")
    # Ordinary warm talk — including HIS weather stories — stays offline.
    assert not brain.wants_fresh_info("Доброе утро!")
    assert not brain.wants_fresh_info("расскажи про свою молодость")
    assert not brain.wants_fresh_info("сыграем в города?")


def test_stable_head_is_cached_and_variable_tail_is_not():
    blocks = brain._system_blocks("КТО ТЫ: Фёдор", "Сегодня праздник")
    assert blocks[0]["cache_control"] == {"type": "ephemeral"}
    assert "Фёдор" in blocks[0]["text"]
    assert "cache_control" not in blocks[1]
    assert "праздник" in blocks[1]["text"]
    # Nothing variable → nothing after the cached head (an empty block would
    # be a pointless cache-buster).
    assert len(brain._system_blocks("КТО ТЫ", "")) == 1


# --------------------------------------------------------------------------- #
# Timeouts: the live conversation is bounded, deep writing is not
# --------------------------------------------------------------------------- #
def test_generate_reply_is_bounded(monkeypatch):
    """A person is standing there waiting. A stalled connection to Claude
    must fail within seconds, not the SDK's own 600-second default."""
    fake = _FakeClient(message=_Message("Привет."))
    monkeypatch.setattr(brain, "_get_client", lambda: fake)

    asyncio.run(brain.generate_reply([{"role": "user", "content": "привет"}], "КТО ТЫ"))

    assert fake.messages.calls[0]["timeout"] == brain._LIVE_REPLY_TIMEOUT


def test_stream_reply_is_bounded_too(monkeypatch):
    """The streaming path goes through the same SDK mechanics and needs the
    same stall protection — a hung connection here freezes mid-sentence."""
    fake = _FakeClient(events=[_Block("Привет"), _Block(" мир")])
    monkeypatch.setattr(brain, "_get_client", lambda: fake)

    async def drain():
        return [chunk async for chunk in brain.stream_reply(
            [{"role": "user", "content": "привет"}], "КТО ТЫ"
        )]

    assert asyncio.run(drain()) == ["Привет", "Привет мир"]
    assert fake.messages.calls[0]["timeout"] == brain._LIVE_REPLY_TIMEOUT


def test_generate_text_has_no_bound_by_default(monkeypatch):
    """Creating a friend and rewriting the diary are deliberately slow — up to
    30-40s is documented as fine — and must never be cut short by a live-chat
    ceiling that has nothing to do with them."""
    fake = _FakeClient(message=_Message("текст"))
    monkeypatch.setattr(brain, "_get_client", lambda: fake)

    asyncio.run(brain.generate_text("system", "user"))

    assert "timeout" not in fake.messages.calls[0]


def test_generate_text_honours_an_explicit_bound(monkeypatch):
    """intake.py passes one: /api/intake/next has a real 25s ceiling on the
    phone, and a stuck call there is what a frozen onboarding screen is."""
    fake = _FakeClient(message=_Message("текст"))
    monkeypatch.setattr(brain, "_get_client", lambda: fake)

    asyncio.run(brain.generate_text("system", "user", timeout=18.0))

    assert fake.messages.calls[0]["timeout"] == 18.0


def test_an_explicit_none_never_reaches_the_sdk_as_a_literal_timeout(monkeypatch):
    """The bug this fix almost shipped with. To httpx, `timeout=None` means
    'never time out' — stricter than even the SDK's 600s default, and the
    opposite of what a Python default of None is supposed to mean here. `None`
    must make the kwarg vanish, not hand it to the SDK as a real value."""
    fake = _FakeClient(message=_Message("текст"))
    monkeypatch.setattr(brain, "_get_client", lambda: fake)

    asyncio.run(brain.generate_text("system", "user", timeout=None))

    assert "timeout" not in fake.messages.calls[0]


def test_think_defaults_to_a_bound_reading_timeout(monkeypatch):
    """The reading is deliberately the slowest call in the app, but it was
    left with NO bound at all — and a dead connection during it could hang
    for the SDK's own 600s while /api/companion/create's client had already
    given up in a fraction of that. Bounding it generously turns a wasted
    wait into a graceful degrade: matchmaker already continues without a
    reading that fails, so a fast, clear failure here means the friend still
    arrives instead of the whole creation hanging for nothing."""
    fake = _FakeClient(message=_Message("текст"))
    monkeypatch.setattr(brain, "_get_client", lambda: fake)

    asyncio.run(brain.think("system", "user"))

    assert fake.messages.calls[0]["timeout"] == brain._READING_TIMEOUT


def test_think_none_never_reaches_the_sdk_as_a_literal_timeout(monkeypatch):
    """The exact same care as generate_text, for the same reason: httpx reads
    a literal `timeout=None` as 'never', not 'use the default'."""
    fake = _FakeClient(message=_Message("текст"))
    monkeypatch.setattr(brain, "_get_client", lambda: fake)

    asyncio.run(brain.think("system", "user", timeout=None))

    assert "timeout" not in fake.messages.calls[0]


def test_the_live_timeout_is_a_real_bound_well_under_a_client_ceiling():
    """Below every client-side ceiling in the app (30s /api/talk, 25s
    /api/intake/next, 12s the background-voice intent) and well above normal
    Haiku latency (a couple of seconds) — it should only ever fire on a
    genuine stall."""
    assert 10.0 <= brain._LIVE_REPLY_TIMEOUT <= 22.0


def test_the_creation_budget_actually_fits_under_the_phones_ceiling():
    """The bug, pinned at the level it actually happened: reading (unbounded)
    + two more calls (unbounded) vs. a 40s client timeout had no reason to
    ever reliably fit — and didn't, on a real phone, on a real attempt.

    This doesn't re-derive BackendClient.swift's 120s (Python can't read
    Swift), but it fixes the number here and requires it stay documented and
    consistent: matchmaker._STAGE_TIMEOUT appears twice in a normal run (ten
    strangers, one deep-write attempt) and up to three times if the deep
    write is retried once. If either budget grows without the other, this is
    where that mismatch should get caught before it reaches a phone again.
    """
    from app import matchmaker

    normal = brain._READING_TIMEOUT + 2 * matchmaker._STAGE_TIMEOUT
    worst = brain._READING_TIMEOUT + 3 * matchmaker._STAGE_TIMEOUT
    # The client's own ceiling — see BackendClient.swift createCompanion.
    client_ceiling = 200.0

    assert normal < client_ceiling, (
        "a normal, non-retried creation can now exceed the phone's patience "
        "again — raise the client timeout or shrink a stage budget"
    )
    # Even the absolute worst case (reading AND the retried deep write both
    # run to their full bound) should stay under the client's ceiling — so
    # the SERVER's own bounded, clearly-logged failure always gets a chance
    # to be reported, rather than the client giving up first on a blind
    # timer with no idea which stage was actually the problem.
    assert worst < client_ceiling


def test_persona_lives_in_the_stable_half():
    """The caching boundary: WHO he is must be byte-identical every turn, and
    everything that shifts (memory, occasions) must stay out of it — otherwise
    the cache misses every turn and silently buys nothing."""
    from app import companion

    stable, variable = companion.build_system_parts(
        persona_block="ТЫ — Фёдор.",
        elder_facts="Внучку зовут Аня.",
        memory_context="Вчера говорили о рыбалке.",
    )
    assert "Фёдор" in stable
    assert "рыбалке" not in stable
    assert "Аня" in variable
    assert "рыбалке" in variable
