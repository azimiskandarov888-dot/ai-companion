"""Speaking while still thinking — the seconds taken out of every silence.

A turn used to be three waits laid end to end: hear it all, think it all, say
it all, and only then send anything. These tests pin the two properties that
make overlapping them safe:

  · nothing that has been spoken is ever revised — it may already have been
    heard;
  · not one character of what he said goes missing at a seam.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app import brain, identity, learn, main, memory, stt, tts

TOKEN = "aVerYlOngRandomLookingTokenFromTheKeychain_0123456789"
AUTH = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/x-ndjson"}
UID = identity.user_id_from_token(TOKEN)

REPLY = "Доброе утро. Как спалось? Мне сегодня снилось море, не знаю почему."


# --------------------------------------------------------------------------- #
# Where a reply gets cut
# --------------------------------------------------------------------------- #
def _as_it_arrives(text: str, step: int = 1) -> list[str]:
    """What the endpoint would actually speak, given text arriving in pieces."""
    said, committed, first = [], 0, True
    for i in range(step, len(text) + step, step):
        tail = text[:i][committed:]
        cut = tts.ready_split(tail, first=first)
        if cut:
            said.append(tail[:cut].strip())
            committed += cut
            first = False
    rest = text[committed:].strip()
    if rest:
        said.append(rest)
    return said


def test_the_first_piece_is_as_early_as_a_sentence_allows():
    """The whole win. «Доброе утро.» in one second beats a balanced paragraph
    in five, because the second one is a silence somebody sits through."""
    said = _as_it_arrives("Доброе утро. " + "Потом ещё много слов. " * 8)
    assert said[0] == "Доброе утро."
    assert len(said) > 2


def test_nothing_is_lost_at_a_seam():
    for text in (
        REPLY,
        "Да.",
        "Ну что ты. Конечно помню, как же.",
        "Помнишь, у А. С. Пушкина было — «мороз и солнце»? Вот сегодня ровно так.",
        "а" * 900,
        "Одно очень длинное предложение, в котором он всё говорит и говорит, "
        "не ставя точку, потому что так люди и правда иногда говорят, особенно "
        "когда им давно не с кем было поговорить, и слова копились",
    ):
        chunks = tts.speakable_chunks(text)
        assert "".join(chunks).replace(" ", "") == text.replace(" ", "")
        assert all(c.strip() for c in chunks)


def test_a_short_tail_never_becomes_a_lone_word_after_a_pause():
    chunks = tts.speakable_chunks("Я думал об этом целый день, знаешь. Да.")
    assert chunks[-1].endswith("Да.")
    assert chunks[-1] != "Да."


def test_what_is_ready_only_ever_grows():
    """The safety property. A piece handed to the voice cannot be taken back,
    so the split point must never move backwards as more text arrives."""
    previous = 0
    for i in range(1, len(REPLY) + 1):
        cut = tts.ready_split(REPLY[:i], first=True)
        assert cut >= previous, f"split went backwards at {i}"
        previous = cut


def test_an_unfinished_sentence_is_never_spoken():
    # No whitespace after the full stop yet → it might still be «т. д.»
    assert tts.ready_split("Доброе утро.", first=True) == 0
    # …and once something follows it, exactly that sentence is ready.
    cut = tts.ready_split("Доброе утро. ", first=True)
    assert "Доброе утро. "[:cut].strip() == "Доброе утро."


# --------------------------------------------------------------------------- #
# The endpoint
# --------------------------------------------------------------------------- #
@pytest.fixture
def client(monkeypatch):
    async def fake_stream(history, system_stable, system_variable=""):
        # Delivered a few characters at a time, the way tokens actually arrive.
        for i in range(1, len(REPLY) + 1, 7):
            yield REPLY[:i]
        yield REPLY

    async def fake_tts(text):
        return b"MP3:" + text.encode("utf-8")

    monkeypatch.setattr(brain, "stream_reply", fake_stream)
    monkeypatch.setattr(tts, "synthesize", fake_tts)
    monkeypatch.setattr(tts, "configured", lambda: True)
    async def heard(*a, **k):
        return "доброе утро"

    async def fake_learn(user_id, user_text, reply):
        LEARNED.append((user_id, user_text, reply))

    LEARNED.clear()
    monkeypatch.setattr(stt, "transcribe", heard)
    monkeypatch.setattr(learn, "learn_from_exchange", fake_learn)
    with TestClient(main.app) as c:
        yield c


#: What the background learner was handed, so the tests can check it ran at all.
LEARNED: list[tuple[str, str, str]] = []


def _talk(client, headers):
    r = client.post(
        "/api/talk",
        files={"audio": ("a.webm", b"somebytes", "audio/webm")},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    return r


def _lines(response) -> list[dict]:
    return [json.loads(line) for line in response.text.splitlines() if line.strip()]


def test_he_speaks_in_pieces_and_they_reassemble(client):
    events = _lines(_talk(client, AUTH))

    assert events[0] == {"kind": "heard", "transcript": "доброе утро"}
    assert events[-1]["kind"] == "done"

    said = [e for e in events if e["kind"] == "say"]
    assert len(said) >= 2, "one piece means nothing was overlapped"
    # The first piece is short — that IS the latency win.
    assert said[0]["text"] == "Доброе утро."
    # …and every character arrives, in order, exactly once.
    assert " ".join(s["text"] for s in said) == REPLY
    assert events[-1]["reply"] == REPLY


def test_every_piece_carries_its_own_audio(client):
    import base64

    for event in _lines(_talk(client, AUTH)):
        if event["kind"] == "say":
            audio = base64.b64decode(event["audio_base64"])
            assert audio == b"MP3:" + event["text"].encode("utf-8")


def test_the_whole_exchange_is_remembered_once(client):
    """He is remembered as having said ONE thing, not five fragments — the
    seams are a delivery detail and have no business in his memory."""
    _talk(client, AUTH)
    turns = [t["content"] for t in memory.recent_turns(UID)]
    assert turns == ["доброе утро", REPLY]

    # …and the background learner still runs after a streamed turn. It is
    # added to the task list from inside the generator, which is late enough
    # to be worth pinning: get this wrong and he stops learning entirely, in
    # complete silence.
    assert LEARNED == [(UID, "доброе утро", REPLY)]


def test_a_client_that_did_not_ask_for_a_stream_gets_the_old_shape(client, monkeypatch):
    """Every build that predates streaming, plus the browser page and curl."""
    async def whole_reply(history, s, v="", *, fresh_info=False):
        return REPLY

    monkeypatch.setattr(brain, "generate_reply", whole_reply)
    r = _talk(client, {"Authorization": f"Bearer {TOKEN}"})
    body = r.json()
    assert body["reply"] == REPLY
    assert body["transcript"] == "доброе утро"
    assert body["audio_base64"]


def test_a_failure_mid_sentence_does_not_lose_what_was_already_said(client, monkeypatch):
    """Once his voice is in the room a 503 is no longer available — the status
    line is long gone. He says what he managed and the phone keeps it."""
    async def dies_halfway(history, s, v=""):
        yield "Доброе утро. "
        yield "Доброе утро. Как спал"
        raise RuntimeError("Fish Audio said no")

    monkeypatch.setattr(brain, "stream_reply", dies_halfway)
    events = _lines(_talk(client, AUTH))

    assert [e["text"] for e in events if e["kind"] == "say"] == ["Доброе утро."]
    assert any(e["kind"] == "trouble" for e in events)
    assert events[-1]["kind"] == "done"


def test_without_a_voice_the_pieces_still_arrive_for_the_phone_to_speak(
    client, monkeypatch
):
    monkeypatch.setattr(tts, "configured", lambda: False)
    events = _lines(_talk(client, AUTH))
    said = [e for e in events if e["kind"] == "say"]
    assert said and all(e["audio_base64"] == "" for e in said)
    assert events[-1]["voice"] == "client"


def test_a_question_about_the_world_is_not_streamed(client, monkeypatch):
    """Web search runs several rounds and the answer can still change after the
    search returns — by which time half of it would already have been said."""
    async def whole_reply(history, s, v="", *, fresh_info=False):
        assert fresh_info is True
        return "Сегодня обещали дождь."

    async def heard(*a, **k):
        return "какая сегодня погода?"

    monkeypatch.setattr(stt, "transcribe", heard)
    monkeypatch.setattr(brain, "generate_reply", whole_reply)

    r = _talk(client, AUTH)
    assert r.headers["content-type"].startswith("application/json")
    assert r.json()["reply"] == "Сегодня обещали дождь."


def test_the_stream_still_counts_against_the_day(client):
    from app import allowance

    _talk(client, AUTH)
    assert allowance.used_today(UID) > 0


def test_the_voice_never_holds_up_the_writing(client, monkeypatch):
    """The subtle one, and the first version got it wrong.

    Reading a token, then going off to synthesise the sentence it completed,
    then coming back for the next token, looks like streaming and is not: an
    async generator only advances when it is asked to, so every half-second
    spent waiting on the voice is a half-second in which Claude is not being
    read. Writing and speaking serialise and most of the win evaporates.

    Writing must therefore be able to finish while the first sentence is still
    at the voice. If this test fails, the two have been put back on one thread
    of control and the turn has quietly got slower.
    """
    import asyncio

    order: list[str] = []

    async def writing(history, s, v=""):
        for i in range(1, len(REPLY) + 1, 7):
            await asyncio.sleep(0)
            yield REPLY[:i]
        yield REPLY
        order.append("finished writing")

    async def slow_voice(text):
        await asyncio.sleep(0.05)
        order.append("finished speaking")
        return b"MP3"

    monkeypatch.setattr(brain, "stream_reply", writing)
    monkeypatch.setattr(tts, "synthesize", slow_voice)

    _talk(client, AUTH)

    assert order[0] == "finished writing", (
        f"the voice blocked the model: {order}"
    )
    assert order.count("finished speaking") >= 2
