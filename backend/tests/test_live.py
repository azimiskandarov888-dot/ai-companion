"""The live channel (live.py): heard while speaking, answered before quite
finished — and still exactly the same turn as every other path: the vows, the
watcher, the farewell, the body, the remembering.

Deepgram, the brain and the voice are all stand-ins here; the line to the phone
is the real WebSocket. What is pinned is everything that would otherwise only
show up in front of somebody: a guess that leaves a trace, a friend who hears
himself, an alarm that comes after the words instead of before them.
"""

from __future__ import annotations

import asyncio
import json
import queue
import time
from contextlib import contextmanager
from types import SimpleNamespace

import anyio
import pytest
from fastapi.testclient import TestClient

from app import (allowance, body, brain, companion, config, db, hearing, identity, learn, live,
                 main, meeting, memory, safety, tts, vow)

TOKEN = "live-token-0123456789-abcdefghij"
UID = identity.user_id_from_token(TOKEN)
REAL_EARS = hearing.Ears


def turn(event: str, text: str = "", end: float = 1.0) -> dict:
    """A Flux TurnInfo message."""
    words = [{"word": w, "end": end} for w in text.split()]
    return {"type": "TurnInfo", "event": event, "transcript": text, "words": words}


class FakeEars:
    """Flux, answered by the test: what it heard, and what it says back."""

    made: list[FakeEars] = []

    def __init__(self, keyterms=()) -> None:
        self.keyterms = keyterms
        self.heard: list[bytes] = []
        self.inbox: queue.Queue = queue.Queue()
        self.ends = 0
        self.closed = False

    @classmethod
    async def open(cls, keyterms=()):
        ears = cls(keyterms)
        cls.made.append(ears)
        return ears

    async def hear(self, pcm: bytes) -> None:
        self.heard.append(bytes(pcm))

    async def finished(self) -> None:
        self.ends += 1

    async def close(self) -> None:
        self.closed = True

    async def events(self):
        while True:
            try:
                item = self.inbox.get_nowait()
            except queue.Empty:
                await asyncio.sleep(0.005)
                continue
            if item is None:
                return
            yield item

    def send(self, *messages: dict) -> None:
        for message in messages:
            self.inbox.put(message)


class FakeBrain:
    def __init__(self) -> None:
        self.replies = ["Привет. Рад тебя слышать, как прошёл день?"]
        self.whole_text = "Сегодня в Ташкенте тепло, около двадцати градусов."
        self.calls: list[list] = []
        self.whole_calls: list[dict] = []
        self.cancelled = 0
        self.delay = 0.0

    async def stream(self, history, system_stable, system_variable=""):
        self.calls.append(history)
        text = self.replies.pop(0) if len(self.replies) > 1 else self.replies[0]
        try:
            for i in range(1, len(text) + 1, 4):
                if self.delay:
                    await asyncio.sleep(self.delay)
                yield text[:i]
            yield text
        except asyncio.CancelledError:
            self.cancelled += 1
            raise

    async def whole(self, history, system_stable, system_variable="", *, fresh_info=False):
        self.whole_calls.append({"history": history, "fresh_info": fresh_info})
        return self.whole_text


class FakeVoice:
    def __init__(self) -> None:
        self.texts: list[str] = []
        self.delay = 0.0

    async def stream(self, text, voice=None):
        self.texts.append(text)
        for part in (b"AB", b"CD"):
            if self.delay:
                await asyncio.sleep(self.delay)
            yield 16000, part


class Closed(Exception):
    pass


class Line:
    """The phone's end of the WebSocket, with a timeout on every wait."""

    def __init__(self, ws) -> None:
        self.ws = ws
        self.messages: list[dict] = []
        self.audio: list[bytes] = []

    def get(self, timeout: float = 5.0):
        async def one():
            with anyio.fail_after(timeout):
                return await self.ws._send_rx.receive()   # receive() has no timeout

        message = self.ws.portal.call(one)
        if message["type"] == "websocket.close":
            raise Closed(message.get("code"))
        if message.get("bytes") is not None:
            self.audio.append(message["bytes"])
            return None
        parsed = json.loads(message["text"])
        self.messages.append(parsed)
        return parsed

    def expect(self, kind: str, timeout: float = 5.0) -> dict:
        deadline = time.monotonic() + timeout
        while True:
            got = self.get(max(0.05, deadline - time.monotonic()))
            if got is not None and got.get("kind") == kind:
                return got

    def kinds(self) -> list[str]:
        return [m["kind"] for m in self.messages]

    def says(self) -> list[str]:
        return [m["text"] for m in self.messages if m["kind"] == "say"]

    def ears(self) -> FakeEars:
        return FakeEars.made[-1]


def wait_until(condition, timeout: float = 3.0) -> None:
    deadline = time.monotonic() + timeout
    while not condition():
        if time.monotonic() > deadline:
            raise AssertionError("waited in vain")
        time.sleep(0.01)


@pytest.fixture
def env(monkeypatch):
    FakeEars.made.clear()
    monkeypatch.setattr(hearing, "Ears", FakeEars)
    mind, voice = FakeBrain(), FakeVoice()
    monkeypatch.setattr(brain, "stream_reply", mind.stream)
    monkeypatch.setattr(brain, "generate_reply", mind.whole)
    monkeypatch.setattr(tts, "stream", voice.stream)

    async def quiet(*args, **kwargs):
        return None

    monkeypatch.setattr(learn, "learn_from_conversation", quiet)
    monkeypatch.setattr(live, "_ECHO_TAIL", 0.0)
    with TestClient(main.app) as client:
        yield SimpleNamespace(client=client, mind=mind, voice=voice)


@contextmanager
def talk(env, *, hello: bool = False, duplex: bool = False, token: str = TOKEN, headers=None):
    with env.client.websocket_connect("/api/live", headers=dict(headers or {})) as ws:
        start = {"type": "start", "hello": hello, "duplex": duplex}
        if token:
            start["token"] = token
        ws.send_json(start)
        line = Line(ws)
        line.expect("ready")
        yield line


def roles() -> list[str]:
    return [t["role"] for t in memory.recent_turns(UID)]


# ── an ordinary turn ────────────────────────────────────────────────────────

def test_a_turn_is_heard_answered_and_kept_once(env):
    with talk(env) as line:
        line.ears().send(turn("StartOfTurn", "привет"), turn("Update", "привет как дела"),
                         turn("EndOfTurn", "привет как дела"))
        heard = line.expect("heard")
        done = line.expect("done")
    assert heard["transcript"] == "привет как дела"
    assert "hearing" in line.kinds()                       # captions as they spoke
    assert " ".join(line.says()) == "Привет. Рад тебя слышать, как прошёл день?"
    assert line.audio                                        # his voice went out
    assert done["reply"] == "Привет. Рад тебя слышать, как прошёл день?"
    assert memory.recent_turns(UID) == [
        {"role": "user", "content": "привет как дела"},
        {"role": "assistant", "content": done["reply"]},
    ]
    assert len(env.mind.calls) == 1
    assert env.mind.calls[0][-1] == {"role": "user", "content": "привет как дела"}


def test_his_name_is_a_word_the_ears_are_told_to_expect(env):
    with talk(env) as line:
        pass
    assert line.ears().keyterms and line.ears().keyterms[0]


# ── drafts ──────────────────────────────────────────────────────────────────

def test_a_draft_begun_on_a_guess_becomes_the_answer(env):
    with talk(env) as line:
        line.ears().send(turn("StartOfTurn", "я сегодня"), turn("EagerEndOfTurn", "я сегодня гулял"))
        wait_until(lambda: len(env.mind.calls) == 1)
        assert memory.recent_turns(UID) == []               # a guess writes nothing
        line.ears().send(turn("EndOfTurn", "я сегодня гулял"))
        heard = line.expect("heard")
        line.expect("done")
    assert heard["timing"]["draft_reused"] is True
    assert len(env.mind.calls) == 1                           # written once, not twice
    assert roles() == ["user", "assistant"]


def test_a_draft_they_talked_past_leaves_no_trace(env):
    env.mind.delay = 0.05
    with talk(env) as line:
        ears = line.ears()
        ears.send(turn("StartOfTurn", "я вот"), turn("EagerEndOfTurn", "я вот думаю"))
        wait_until(lambda: len(env.mind.calls) == 1)
        ears.send(turn("TurnResumed", "я вот думаю купить"))
        wait_until(lambda: env.mind.cancelled == 1)
        assert memory.recent_turns(UID) == []
        ears.send(turn("EagerEndOfTurn", "я вот думаю купить собаку"),
                  turn("EndOfTurn", "я вот думаю купить собаку"))
        line.expect("done")
    assert len(env.mind.calls) == 2
    assert memory.recent_turns(UID)[0]["content"] == "я вот думаю купить собаку"


def _recalled(memory_id: int) -> int:
    with db.connect() as conn:
        return conn.execute("SELECT recall_count FROM memories WHERE id=?",
                            (memory_id,)).fetchone()["recall_count"]


def test_a_draft_prompt_is_the_one_the_turn_gets_and_writes_nothing(monkeypatch):
    """The draft is built BEFORE their line is written, the answer after — and
    they must be the same prompt, or a kept draft would be answering a
    different conversation. And building it must touch nothing."""
    monkeypatch.setattr(memory.random, "random", lambda: 1.0)   # no resurfacing roll
    memory.log_turn(UID, "user", "раньше было")
    memory.log_turn(UID, "assistant", "да, помню")
    story = memory.add_memory(UID, "story", "ездили на рыбалку на Иссык-Куль")

    marks: list = []
    drafted = asyncio.run(main._assemble(UID, "а помнишь рыбалку", pending=True, marks=marks))
    assert drafted[4] is None                                   # nobody set to watch
    assert [t["content"] for t in memory.recent_turns(UID)] == ["раньше было", "да, помню"]
    assert _recalled(story) == 0 and marks                      # recalled on paper only

    logged = asyncio.run(main._assemble(UID, "а помнишь рыбалку"))
    assert drafted[:4] == logged[:4]


def test_committing_a_draft_writes_what_it_held_back():
    memory.log_turn(UID, "user", "раньше было")
    story = memory.add_memory(UID, "story", "ездили на рыбалку")

    async def draft_then_commit():
        marks: list = []
        await main._assemble(UID, "а помнишь", pending=True, marks=marks)
        watcher = main._commit(UID, "а помнишь", marks)
        await watcher

    asyncio.run(draft_then_commit())
    assert memory.recent_turns(UID)[-1] == {"role": "user", "content": "а помнишь"}
    assert _recalled(story) == 1


def test_only_somebodys_line_can_be_a_draft():
    with pytest.raises(ValueError):
        asyncio.run(main._assemble(UID, None, pending=True))


# ── he does not hear himself; over headphones he can be interrupted ─────────

def test_he_does_not_hear_himself(env):
    env.voice.delay = 0.1
    with talk(env) as line:
        ears = line.ears()
        ears.send(turn("EndOfTurn", "расскажи что нибудь"))
        line.expect("say")
        line.ws.send_bytes(b"\x01\x02" * 40)
        wait_until(lambda: any(len(f) == 80 for f in ears.heard))
        assert [f for f in ears.heard if len(f) == 80][-1] == bytes(80)
        line.expect("done")
        line.ws.send_json({"type": "played"})
        time.sleep(0.05)
        line.ws.send_bytes(b"\x01\x02" * 40)
        wait_until(lambda: [f for f in ears.heard if len(f) == 80][-1] != bytes(80))


def test_over_headphones_talking_over_him_stops_him(env):
    env.mind.replies = ["Первое предложение тут. Второе предложение тоже тут. Третье предложение тоже."]
    env.voice.delay = 0.15
    with talk(env, duplex=True) as line:
        line.ears().send(turn("EndOfTurn", "ну давай"))
        line.expect("say")
        line.expect("say")                         # the first piece is out
        line.ears().send(turn("StartOfTurn", "подожди"))
        line.expect("interrupted")
        wait_until(lambda: roles()[-1:] == ["assistant"])
    kept = memory.recent_turns(UID)[-1]["content"]
    assert kept == "Первое предложение тут."        # what got out, nothing more


def test_somebody_who_goes_on_before_he_answers_is_answered_once(env):
    env.mind.delay = 0.05
    with talk(env) as line:
        ears = line.ears()
        ears.send(turn("EndOfTurn", "ну вот"))
        line.expect("heard")
        wait_until(lambda: len(env.mind.calls) == 1)
        ears.send(turn("StartOfTurn", "и ещё"))
        line.expect("interrupted")
        ears.send(turn("EndOfTurn", "и ещё одно хотел сказать"))
        line.expect("done")
    assert roles() == ["user", "user", "assistant"]


# ── the same turn as everywhere else ────────────────────────────────────────

def test_danger_puts_up_the_button_before_the_words(env, monkeypatch):
    async def danger(user_id, said):
        return {"level": "danger", "kind": "body", "what": "упал"}

    monkeypatch.setattr(safety, "look", danger)
    with talk(env) as line:
        line.ears().send(turn("EndOfTurn", "я упал и не могу встать"))
        done = line.expect("done")
    kinds = line.kinds()
    last_say = max(i for i, k in enumerate(kinds) if k == "say")
    assert kinds.index("alarm") < last_say
    alarm = next(m for m in line.messages if m["kind"] == "alarm")["alarm"]
    assert alarm["danger"] == "body" and alarm["numbers"]
    assert "103" in done["reply"] and done["farewell"] is False


def test_a_goodbye_ends_the_conversation(env):
    env.mind.replies = [f"Ну давай, до завтра. {companion.FAREWELL_MARKER}"]
    with talk(env) as line:
        line.ears().send(turn("EndOfTurn", "ну всё пока"))
        done = line.expect("done")
    assert done["farewell"] is True
    assert companion.FAREWELL_MARKER not in done["reply"]
    assert all(companion.FAREWELL_MARKER not in text for text in line.says())


def test_his_cough_is_heard_and_never_shown(env):
    env.mind.replies = [f"Доброе утро. {body.MARK_COUGH} Как спалось?"]
    with talk(env) as line:
        line.ears().send(turn("EndOfTurn", "доброе утро"))
        done = line.expect("done")
    assert any(body.MARK_COUGH in text for text in env.voice.texts)   # the voice gets it
    assert all("//" not in text for text in line.says())              # the phone never does
    assert done["reply"] == "Доброе утро. Как спалось?"
    assert memory.recent_turns(UID)[-1]["content"] == "Доброе утро. Как спалось?"


def test_what_he_never_says_is_never_said(env, monkeypatch):
    noted: list[str] = []
    monkeypatch.setattr(vow, "note", lambda user_id, slip, said: noted.append(slip))
    env.mind.replies = ["Ну здравствуй. Я всего лишь программа. Как спалось-то?"]
    with talk(env) as line:
        line.ears().send(turn("EndOfTurn", "ты кто вообще"))
        done = line.expect("done")
    assert not any("программа" in text for text in env.voice.texts)
    assert "программа" not in done["reply"]
    assert noted == [vow.MACHINE]


# ── asleep, spent, a television ─────────────────────────────────────────────

def _raw(env):
    return env.client.websocket_connect("/api/live")


def test_somebody_he_dozed_off_on_hears_him_say_so(env):
    allowance._asleep.add(UID)
    with _raw(env) as ws:
        ws.send_json({"type": "start", "token": TOKEN})
        said = Line(ws).expect("asleep")
    assert said["reply"] == allowance._line("asleep")
    assert env.voice.texts                                  # in his own voice


def test_a_spent_day_is_a_goodnight(env):
    allowance.spend(UID, config.DAILY_SECONDS + 1)
    with _raw(env) as ws:
        ws.send_json({"type": "start", "token": TOKEN})
        said = Line(ws).expect("daily_limit")
    assert said["reply"] == allowance._line("spent")


def test_a_television_still_puts_him_to_sleep(env):
    allowance._stray[UID] = allowance.DOZE_AFTER_STRAY_TURNS - 1
    with talk(env) as line:
        line.ears().send(turn("EndOfTurn", "ага"))
        line.expect("asleep")
    assert env.mind.calls == []


# ── looking something up; saying hello ──────────────────────────────────────

def test_a_question_about_the_world_is_looked_up_out_loud(env):
    asked = "какая сейчас погода в ташкенте"
    with talk(env) as line:
        line.ears().send(turn("EagerEndOfTurn", asked))
        time.sleep(0.05)
        assert env.mind.calls == [] and env.mind.whole_calls == []   # no search on a guess
        line.ears().send(turn("EndOfTurn", asked))
        done = line.expect("done")
    says = line.says()
    assert says[0] in live._FILLERS
    assert env.mind.whole_calls[0]["fresh_info"] is True
    assert done["reply"].startswith(says[0]) and "двадцати" in done["reply"]


def test_he_greets_a_stranger_first(env):
    env.mind.replies = ["Привет. Я тут сижу, чай пью."]
    with talk(env, hello=True) as line:
        done = line.expect("done")
    assert env.mind.calls[0] == [{"role": "user", "content": meeting.HELLO}]
    assert memory.recent_turns(UID) == [{"role": "assistant", "content": done["reply"]}]


def test_no_hello_for_somebody_he_knows(env):
    memory.log_turn(UID, "user", "привет")
    with talk(env, hello=True):
        time.sleep(0.1)
    assert env.mind.calls == []


# ── the line itself ─────────────────────────────────────────────────────────

def test_without_live_ears_it_says_so(env, monkeypatch):
    monkeypatch.setattr(hearing, "Ears", REAL_EARS)
    with _raw(env) as ws:
        ws.send_json({"type": "start", "token": TOKEN})
        said = Line(ws).expect("trouble")
    assert "DEEPGRAM_API_KEY" in said["detail"]


def test_ears_that_drop_mid_conversation_are_said(env):
    """A dropped line to Deepgram fails whichever task touches it first — here
    the one sending the microphone, not the one listening — and the phone is
    told why rather than just hung up on (it used to be, silently)."""
    with talk(env) as line:
        async def gone(pcm):
            raise ConnectionError("Deepgram went away")

        line.ears().hear = gone
        line.ws.send_bytes(bytes(hearing.CHUNK))
        said = line.expect("trouble")
    assert "Deepgram went away" in said["detail"]


def test_ears_that_hang_up_are_said(env):
    with talk(env) as line:
        line.ears().send(None)   # the line ends without a word
        said = line.expect("trouble")
    assert "closed the line" in said["detail"]


def test_a_second_window_replaces_the_first(env):
    with talk(env) as first:
        with talk(env):
            first.expect("replaced")


def test_a_quiet_line_is_kept_open_with_silence(env, monkeypatch):
    monkeypatch.setattr(live, "_FILL_AFTER", 0.01)
    monkeypatch.setattr(live, "_FILL", 0.02)
    with talk(env) as line:
        wait_until(lambda: len(line.ears().heard) >= 3)
    assert all(frame == bytes(len(frame)) for frame in line.ears().heard)


def test_nobody_there_closes_the_line(env, monkeypatch):
    monkeypatch.setattr(config, "LIVE_IDLE_SECONDS", 0.1)
    with talk(env) as line:
        line.expect("idle")


def test_done_talking_ends_the_turn_now(env):
    with talk(env) as line:
        line.ws.send_json({"type": "done_talking"})
        wait_until(lambda: line.ears().ends == 1)


def test_a_caller_who_never_says_start_is_hung_up_on(env):
    with _raw(env) as ws:
        ws.send_json({"type": "hello"})
        said = Line(ws).get()
    assert said["kind"] == "trouble"


def test_the_header_says_who_it_is_when_there_is_one(env):
    other = identity.user_id_from_token("Bearer another-person-token-123456")
    with talk(env, token="", headers={"Authorization": "Bearer another-person-token-123456"}) as line:
        line.ears().send(turn("EndOfTurn", "привет"))
        line.expect("done")
    assert [t["role"] for t in memory.recent_turns(other)] == ["user", "assistant"]
    assert memory.recent_turns(UID) == []
