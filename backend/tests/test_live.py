"""The live channel (live.py): heard while speaking, answered before quite
finished — and still exactly the same turn as every other path: the vows, the
watcher, the farewell, the body, the remembering.

The ears, the brain and the voice are all stand-ins here; the line to the phone
is the real WebSocket. What is pinned is everything that would otherwise only
show up in front of somebody: a guess that leaves a trace, a friend who hears
himself, an alarm that comes after the words instead of before them.
"""

from __future__ import annotations

import array
import asyncio
import json
import queue
import time
from contextlib import contextmanager
from types import SimpleNamespace

import anyio
import pytest
from fastapi.testclient import TestClient

from app import (allowance, aloud, body, brain, companion, config, db, first_sound, gate, hearing,
                 identity, learn, live, main, meeting, memory, persona, safety, tts, vow)

TOKEN = "live-token-0123456789-abcdefghij"
UID = identity.user_id_from_token(TOKEN)
REAL_EARS = hearing.Ears


def turn(event: str, text: str = "", end: float = 1.0) -> dict:
    """A TurnInfo message, as the ears give it (hearing.Turns)."""
    words = [{"word": w, "end": end} for w in text.split()]
    return {"type": "TurnInfo", "event": event, "transcript": text, "words": words}


def voice_frame(db: float = -20.0) -> bytes:
    """80 ms of a voice-loud tone — what the gate lets through (gate.py)."""
    import math
    amp = 32767 * 10 ** (db / 20) * math.sqrt(2)
    return array.array("h", [int(amp * math.sin(2 * math.pi * 220 * i / 16000))
                             for i in range(1280)]).tobytes()


VOICE = voice_frame()


class FakeEars:
    """The ears, answered by the test: what they heard, and what they say back."""

    made: list[FakeEars] = []

    def __init__(self, keyterms=(), hold=None) -> None:
        self.keyterms = keyterms
        self.hold = hold
        self.heard: list[bytes] = []
        self.inbox: queue.Queue = queue.Queue()
        self.ends = 0
        self.closed = False

    @classmethod
    async def open(cls, keyterms=(), hold=None):
        ears = cls(keyterms, hold)
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

    async def stream(self, history, system_stable, system_variable="", **_):
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
        #: …and before its first sound only: a voice takes a moment to begin.
        self.first_delay = 0.0

    async def stream(self, text, voice=None):
        self.texts.append(text)
        if self.first_delay:
            await asyncio.sleep(self.first_delay)
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
    # The stand-in voice streams, as Fish does; a voice that makes each piece
    # whole keeps more of them in the making (test_a_whole_voice_*).
    monkeypatch.setattr(tts, "streams", lambda: True)
    monkeypatch.setattr(tts, "slow_start", lambda: False)

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


def test_he_is_told_their_words_were_heard_and_may_be_misheard(monkeypatch):
    """Flux heard «бассейн» as «Басанин» and «Азим» as «Азима», and he said
    «Басанин» back and «ты исчезла» to the owner (2026-09-30). Every live
    draft is told the words were HEARD; the text path is not."""
    async def run():
        heard = await main._assemble(UID, "но басанин это не море", pending=True, marks=[], by_ear=True)
        typed = await main._assemble(UID, "но бассейн это не море", pending=True, marks=[])
        return heard[1], typed[1]

    heard, typed = asyncio.run(run())
    assert companion.BY_EAR in heard and companion.BY_EAR not in typed
    assert "не по имени" in companion.BY_EAR and "вслух не повторяй" in companion.BY_EAR


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
    """Without headphones his own voice comes back into the microphone: the
    ears get silence in its place (with the gate on, nothing at all — gate.py);
    the person's voice after him reaches them."""
    env.voice.delay = 0.1
    with talk(env) as line:
        ears = line.ears()
        ears.send(turn("EndOfTurn", "расскажи что нибудь"))
        line.expect("say")
        line.ws.send_bytes(VOICE)                 # his own voice, coming back
        line.ws.send_bytes(VOICE)
        time.sleep(0.05)
        assert VOICE not in ears.heard
        line.expect("done")
        line.ws.send_json({"type": "played"})
        time.sleep(0.4)                           # the room's echo dies away (_ECHO_TAIL)
        line.ws.send_bytes(VOICE)                 # and now it is the person
        wait_until(lambda: VOICE in ears.heard)


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


def test_he_can_be_interrupted_by_default(env):
    """What the owner liked in ChatGPT's voice (2026-09-30): talk, and it
    stops and listens. A phone that says nothing about it gets that."""
    with env.client.websocket_connect("/api/live") as ws:
        ws.send_json({"type": "start", "token": TOKEN})
        Line(ws).expect("ready")
        assert live._open[UID].duplex is True
    with talk(env, duplex=False) as line:
        assert live._open[UID].duplex is False


def test_an_older_person_is_given_longer_to_finish_a_thought(env, monkeypatch):
    """A thought broken off waits for the rest of it before he nudges them on —
    longer when they are older (the owner, 2026-10-14: «в зависимости от
    возраста»; hearing.py)."""
    monkeypatch.setattr(live.young, "is_elder", lambda user_id: False)
    monkeypatch.setattr(live.voices, "years", lambda who: 30)
    with talk(env) as line:
        assert line.ears().hold == config.HOLD_UNFINISHED
    monkeypatch.setattr(live.young, "is_elder", lambda user_id: True)
    with talk(env) as line:
        assert line.ears().hold == config.HOLD_UNFINISHED_OLDER
    assert config.HOLD_UNFINISHED_OLDER > config.HOLD_UNFINISHED


def test_his_own_voice_back_from_the_speaker_does_not_stop_him(env):
    """Without headphones his voice comes back into the open microphone, and
    what echo cancellation misses Flux hears as HIS words. Those — and an
    «угу» — neither stop him nor become a turn of theirs."""
    env.mind.replies = ["Море сегодня тихое, ветер почти улёгся. А у тебя как погода, тепло ли?"]
    env.voice.delay = 0.15
    with talk(env, duplex=True) as line:
        line.ears().send(turn("EndOfTurn", "как там у тебя"))
        line.expect("say")
        line.ears().send(turn("StartOfTurn", "море сегодня"), turn("Update", "море сегодня тихое"),
                         turn("EndOfTurn", "морю сегодня тихо"))
        line.ears().send(turn("StartOfTurn", "угу"), turn("EndOfTurn", "угу"))
        done = line.expect("done")
        assert "interrupted" not in line.kinds()
    assert done["reply"].startswith("Море сегодня тихое")
    assert len(env.mind.calls) == 1                     # nothing of his was answered
    assert [t["role"] for t in memory.recent_turns(UID)] == ["user", "assistant"]


def test_somebody_talking_over_him_stops_him_without_headphones(env):
    env.mind.replies = ["Первое предложение тут. Второе предложение тоже тут. Третье предложение тоже."]
    env.voice.delay = 0.15
    with talk(env, duplex=True) as line:
        line.ears().send(turn("EndOfTurn", "ну давай"))
        line.expect("say")
        line.ears().send(turn("StartOfTurn", "первое"))          # his own word: nothing
        line.ears().send(turn("Update", "первое а я вот хотел"))  # theirs: he stops
        line.expect("interrupted")
        line.ears().send(turn("EndOfTurn", "а я вот хотел сказать"))
        line.expect("heard")
    assert env.mind.calls[-1][-1]["content"] == "а я вот хотел сказать"


@pytest.mark.parametrize("heard, over", [
    ("море сегодня тихое", False),          # his words
    ("морю сегодня тихо", False),           # his words, heard in other endings
    ("угу", False), ("ага да", False),     # listening, not taking the turn
    ("", False),
    ("подожди", True), ("стоп", True),     # a stop word, however short
    ("а я вот", False),                    # nothing of theirs long enough yet
    ("а я вот хотел", True),               # one long word of their own
    ("мне надо идти", True),               # two of their own
])
def test_what_is_heard_over_him_is_told_apart(heard, over):
    said = ["Море сегодня тихое, ветер почти улёгся."]
    assert live.talks_over(heard, said) is over


@pytest.mark.parametrize("heard, theirs", [
    # the tail of his echo glued to what they say next (seen live, 2026-09-30)
    ("Ветер почти улёгся. Я водителем работаю.", "Я водителем работаю."),
    ("Море сегодня -- Подожди, я не договорил.", "Подожди, я не договорил."),
    ("море а я вот хотел", "а я вот хотел"),          # their «а я» is kept
    ("а я вот хотел сказать", "а я вот хотел сказать"),
    ("море сегодня тихое", ""),                       # none of it theirs
])
def test_his_echo_is_taken_off_the_start_of_their_turn(heard, theirs):
    said = ["Море сегодня тихое, ветер почти улёгся."]
    assert live.their_part(heard, said) == theirs


def test_his_echo_ending_after_he_stopped_is_still_his(env):
    """The ears decide a turn is over a second or so after the room goes
    quiet — by which time he has stopped. A turn that BEGAN over his voice is
    judged as possibly his voice to its end: in the worst room (no echo
    cancellation at all) his own «После работы усталость» came back as the
    person's turn, and he answered it (2026-09-30)."""
    env.mind.replies = ["После работы усталость честная. Отдохни."]
    with talk(env, duplex=True) as line:
        line.ears().send(turn("EndOfTurn", "устал немного"))
        line.expect("done")
        session = live._open[UID]
        session._playing_until = time.monotonic() + 0.3      # still in the room
        line.ears().send(turn("StartOfTurn", "после работы"))
        wait_until(lambda: session._over_him)
        session._playing_until = 0.0                         # …and now he has stopped
        line.ears().send(turn("EagerEndOfTurn", "после работы усталость честная"),
                         turn("EndOfTurn", "после работы усталость честная"))
        time.sleep(0.2)
    assert len(env.mind.calls) == 1                           # not answered
    assert [t["role"] for t in memory.recent_turns(UID)] == ["user", "assistant"]


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


def test_his_goodbye_does_not_hang_up_on_somebody_still_talking(env, monkeypatch):
    """His goodbye is his reading of the moment, and without reasoning the
    voice misread «Домой сразу. Спать.» and a plain answer about school as
    goodbyes (2026-09-29/30). The line used to close 1.5 s after it played.
    Somebody who carries on is answered, and the line stays open after."""
    monkeypatch.setattr(live, "_FAREWELL_GRACE", 0.5)
    env.mind.replies = [f"Ну, отдыхай тогда. {companion.FAREWELL_MARKER}",
                        "Конечно, рассказывай.", "Слушаю."]
    with talk(env) as line:
        line.ears().send(turn("EndOfTurn", "домой сразу спать"))
        assert line.expect("done")["farewell"] is True
        line.ears().send(turn("StartOfTurn", "а"), turn("EndOfTurn", "а знаешь что было"))
        done = line.expect("done")
        assert done["reply"] == "Конечно, рассказывай." and done["farewell"] is False
        time.sleep(0.8)                  # longer than the grace: still open
        line.ears().send(turn("EndOfTurn", "ну так вот"))
        assert line.expect("done")["reply"] == "Слушаю."


def test_after_his_goodbye_a_quiet_line_closes(env, monkeypatch):
    monkeypatch.setattr(live, "_FAREWELL_GRACE", 0.1)
    env.mind.replies = [f"Ну давай, до завтра. {companion.FAREWELL_MARKER}"]
    with talk(env) as line:
        line.ears().send(turn("EndOfTurn", "ну всё пока"))
        line.expect("done")
        with pytest.raises(Closed):
            line.expect("nothing more", timeout=3)


def test_he_says_it_aloud_and_is_remembered_as_he_meant_it(env, monkeypatch):
    """The owner: too perfect is fake — so the voice gets a hesitation where a
    speaker would make one (aloud.py). The phone is shown what it hears; what
    is remembered, and read back later, is what he meant."""
    # Five times the shipped rate: certain to stumble, so the test is not a coin.
    monkeypatch.setattr(aloud, "CHANCE", 5.0)
    meant = "Ого. Мне это всегда казалось каким-то фокусом, если честно."
    env.mind.replies = [meant]
    with talk(env) as line:
        line.ears().send(turn("EndOfTurn", "я писал программу"))
        done = line.expect("done")
    heard = " ".join(line.says())
    assert heard != meant and "каким-то" in heard
    assert any("каким-то" in text and text not in meant for text in env.voice.texts)
    assert done["reply"] == meant
    assert memory.recent_turns(UID)[-1]["content"] == meant


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
    assert "SONIOX_API_KEY" in said["detail"]


def test_ears_that_drop_mid_conversation_are_said(env):
    """A dropped line to the ears fails whichever task touches it first — here
    the one sending the microphone, not the one listening — and the phone is
    told why rather than just hung up on (it used to be, silently)."""
    with talk(env) as line:
        async def gone(pcm):
            raise ConnectionError("the ears went away")

        line.ears().hear = gone
        line.ws.send_bytes(VOICE)
        said = line.expect("trouble")
    assert "the ears went away" in said["detail"]


def test_ears_that_hang_up_are_said(env):
    with talk(env) as line:
        line.ears().send(None)   # the line ends without a word
        said = line.expect("trouble")
    assert "closed the line" in said["detail"]


def test_a_second_window_replaces_the_first(env):
    with talk(env) as first:
        with talk(env):
            first.expect("replaced")


def test_a_quiet_phone_is_filled_with_silence(env, monkeypatch):
    """The ears end a turn by hearing the pause, and Soniox hangs up after 20 s
    without audio: a phone gone quiet is filled with silence. Soniox bills
    the whole stream, so the silence costs nothing more."""
    monkeypatch.setattr(live, "_FILL", 0.02)
    monkeypatch.setattr(live, "_FILL_AFTER", 0.05)
    with talk(env) as line:
        wait_until(lambda: len(line.ears().heard) >= 3)
    assert all(frame == bytes(int(16000 * 0.02) * 2) for frame in line.ears().heard)


def test_with_the_gate_a_quiet_line_is_kept_open_on_a_beat_of_silence(env, monkeypatch):
    """For ears that bill the audio they are sent (Deepgram did): 80 ms every
    few seconds between turns (gate.KEEPALIVE_EVERY), not a stream."""
    monkeypatch.setattr(config, "LIVE_GATE", True)
    monkeypatch.setattr(live, "_FILL", 0.02)
    monkeypatch.setattr(gate, "KEEPALIVE_EVERY", 0.05)
    with talk(env) as line:
        wait_until(lambda: len(line.ears().heard) >= 3)
    beats = line.ears().heard
    assert all(frame == bytes(len(frame)) for frame in beats)
    assert all(len(frame) == int(16000 * gate.KEEPALIVE) * 2 for frame in beats)


def test_with_the_gate_only_their_voice_reaches_the_ears(env, monkeypatch):
    """The room is not sent; their voice is, with the second before it."""
    monkeypatch.setattr(config, "LIVE_GATE", True)
    quiet = voice_frame(-70.0)
    with talk(env) as line:
        for _ in range(20):
            line.ws.send_bytes(quiet)              # a quiet room, 1.6 s
        time.sleep(0.1)
        assert line.ears().heard == []
        line.ws.send_bytes(VOICE)
        wait_until(lambda: VOICE in line.ears().heard)
        heard = line.ears().heard
        # The second before it went too — and no more of the room than that.
        assert heard[-1] == VOICE
        assert gate.PREROLL - 0.1 <= heard.count(quiet) * 0.08 <= gate.PREROLL


def test_with_the_gate_a_turn_is_heard_to_its_end_pause_and_all(env, monkeypatch):
    """The ears end a turn by HEARING the pause — so the pause must reach them."""
    monkeypatch.setattr(config, "LIVE_GATE", True)
    quiet = voice_frame(-70.0)
    with talk(env) as line:
        ears = line.ears()
        line.ws.send_bytes(VOICE)
        ears.send(turn("StartOfTurn", "я"))
        wait_until(lambda: VOICE in ears.heard)
        time.sleep(0.05)
        for _ in range(12):
            line.ws.send_bytes(quiet)              # a long pause, mid-turn: 0.96 s
        wait_until(lambda: ears.heard.count(quiet) == 12)
        ears.send(turn("EndOfTurn", "я"))
        time.sleep(gate.AFTER_END + 0.1)
        for _ in range(12):
            line.ws.send_bytes(quiet)              # quiet after the turn: the gate closes
        time.sleep(0.1)
        # The first of them still goes — it is the one that closes it — the rest do not.
        assert ears.heard.count(quiet) == 13


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


# ── his first sound (first_sound.py) ────────────────────────────────────────

def his_voice() -> str | None:
    """The voice this person's companion speaks in — what his sounds are made in."""
    return tts.voice_for(persona.load_persona(UID))


#: His sounds in the tests: 0.4 s each at 16 kHz, each its own bytes.
MM, HM, BR, DA, NU = (tag * 6400 for tag in (b"MM", b"HM", b"BR", b"DA", b"NU"))


@pytest.fixture
def sounds(monkeypatch, env):
    """His sounds, made — the stand-in voice would make them as bytes too, but
    then which bytes are which would be guesswork."""
    # As long as the real ones, so that there is a moment to say them in
    # before his words (live._VOICE_TAKES) — and his words take a moment too.
    for text, pcm in (("М-м…", MM), ("Хм…", HM), (first_sound.BREATH, BR),
                      ("Да…", DA), ("Ну…", NU)):
        first_sound._made[(his_voice(), text)] = [(16000, pcm)]
    # His breath at the end of every turn, unless a test says otherwise.
    always = {kind: (1.0, 0.0) for kind in first_sound.SHARES}
    monkeypatch.setattr(first_sound, "SHARES", always)
    monkeypatch.setattr(first_sound, "SHARES_OLDER", always)
    env.voice.first_delay = 0.8    # his words take a moment to come, as they do
    monkeypatch.setattr(first_sound, "CHANCE_IN_PAUSE", 1.0)
    monkeypatch.setattr(first_sound, "LATE", None)


def _shares(monkeypatch, breath: float, word: float) -> None:
    """The end of every turn gets his breath, a word or nothing as told —
    whatever his age (first_sound.SHARES_OLDER)."""
    shares = {kind: (breath, word) for kind in first_sound.SHARES}
    monkeypatch.setattr(first_sound, "SHARES", shares)
    monkeypatch.setattr(first_sound, "SHARES_OLDER", shares)


def pull_until(line, condition, timeout: float = 3.0) -> None:
    """Read what the phone is sent until `condition` holds."""
    deadline = time.monotonic() + timeout
    while not condition():
        if time.monotonic() > deadline:
            raise AssertionError("waited in vain")
        try:
            line.get(0.05)
        except TimeoutError:
            pass


def breath_heard(line) -> bytes:
    """His breath as the phone was sent it — in pieces (live._Breath), before
    his first word (the stand-in voice's «AB»)."""
    first_word = line.audio.index(b"AB") if b"AB" in line.audio else len(line.audio)
    return b"".join(line.audio[:first_word])


def after_heard(line) -> list[str]:
    heard = line.kinds().index("heard")
    return [m["text"] for m in line.messages[heard:] if m["kind"] == "say"]


def test_he_gives_voice_at_once_and_it_is_not_what_he_said(env, sounds):
    """The owner, 2026-10-02: «сделай чтобы он сразу подавал голос» — and,
    2026-10-08, most of the time with a breath. A person answers about 0.2 s
    after the other stops; his words take longer."""
    with talk(env) as line:
        line.ears().send(turn("StartOfTurn", "я сегодня"), turn("EndOfTurn", "я сегодня в школе был"))
        line.expect("heard")
        done = line.expect("done")
    says = after_heard(line)
    assert says[0] == "(вдох)"                             # first, before any word
    assert BR[:400] in breath_heard(line)
    assert " ".join(says[1:]) == "Привет. Рад тебя слышать, как прошёл день?"
    assert done["reply"] == "Привет. Рад тебя слышать, как прошёл день?"
    assert memory.recent_turns(UID)[-1]["content"] == done["reply"]   # never remembered
    assert done["timing"]["first_sound"] is not None


def test_his_answer_does_not_say_the_sound_again(env, sounds, monkeypatch):
    _shares(monkeypatch, 0.0, 1.0)
    first_sound._made.pop((his_voice(), "Ну…"))    # so the thinking sound is «Хм…»
    env.mind.replies = ["Хм, ну я не знаю. Наверное, стоит."]
    with talk(env) as line:
        line.ears().send(turn("StartOfTurn", "а ты"), turn("EndOfTurn", "а ты как думаешь, стоит идти?"))
        line.expect("heard")
        done = line.expect("done")
    says = after_heard(line)
    assert says[0] == "Хм…"
    assert says[1].startswith("Ну я не знаю")              # not «Хм» twice
    assert done["reply"] == "Хм, ну я не знаю. Наверное, стоит."   # what he meant, kept whole


def test_a_pause_gets_a_listeners_sound_where_he_can_be_talked_over(env, sounds):
    """«М-м» into their pause: if they carry on, it was a listener's sound —
    and the end of the turn does not get a second one straight after."""
    with talk(env, duplex=True) as line:
        line.ears().send(turn("StartOfTurn", "я сегодня"), turn("EagerEndOfTurn", "я сегодня в школу пришёл"))
        pull_until(line, lambda: MM in line.audio)
        line.ears().send(turn("TurnResumed", "я сегодня в школу пришёл"),
                         turn("EndOfTurn", "я сегодня в школу пришёл а там никого"))
        line.expect("heard")
        line.expect("done")
    before = line.kinds().index("heard")
    assert [m["text"] for m in line.messages[:before] if m["kind"] == "say"] == ["М-м…"]
    assert "М-м…" not in after_heard(line)


def test_without_being_interruptible_a_pause_gets_no_sound(env, sounds):
    """The microphone is closed while he makes a sound: their next words would
    be lost under it."""
    with talk(env, duplex=False) as line:
        line.ears().send(turn("StartOfTurn", "я сегодня"), turn("EagerEndOfTurn", "я сегодня в школу пришёл"))
        wait_until(lambda: len(env.mind.calls) == 1)
        line.ears().send(turn("EndOfTurn", "я сегодня в школу пришёл"))
        line.expect("heard")
        line.expect("done")
    before = line.kinds().index("heard")
    assert not [m for m in line.messages[:before] if m["kind"] == "say"]


def test_a_goodbye_gets_no_sound(env, sounds):
    env.mind.replies = ["Давай, пока!"]
    with talk(env) as line:
        line.ears().send(turn("StartOfTurn", "ладно"), turn("EndOfTurn", "ладно мне пора пока"))
        line.expect("heard")
        line.expect("done")
    assert " ".join(after_heard(line)) == "Давай, пока!"     # his first pause is his own


def test_he_makes_no_sound_before_his_own_hello(env, sounds):
    with talk(env, hello=True) as line:
        line.expect("done")
    assert "М-м…" not in line.says()


def test_a_slow_answer_gets_one_more_sound_and_never_inside_his_words(env, sounds, monkeypatch):
    _shares(monkeypatch, 0.0, 0.0)
    monkeypatch.setattr(first_sound, "LATE", 0.05)
    env.mind.delay = 0.03
    with talk(env) as line:
        line.ears().send(turn("StartOfTurn", "я сегодня"), turn("EndOfTurn", "я сегодня в школе был"))
        line.expect("heard")
        line.expect("done")
    says = after_heard(line)
    assert says[0] in ("Да…", "Ну…")                       # a word, not a second breath
    assert sum(said in ("Да…", "Ну…", "(вдох)") for said in says) == 1


# ── a guess is written, never voiced (2026-10-05) ───────────────────────────
#
# The owner, 2026-10-03, of Gemini Live: in the wait to be sure you have
# finished, «they already have everything ready to go». So the draft begun on
# «похоже, договорил» is written while the turn may still go on — and only the
# brain's: the owner, 2026-10-05, «будет тратить больше денег и лишней
# энергии». Its voice is asked for once the turn is certain, which on the real
# ears came before its first piece was even written (live.py).

def test_a_guess_is_written_but_never_voiced(env):
    env.mind.replies = ["Ого, сам программу пишешь? А про что она?"]
    with talk(env) as line:
        line.ears().send(turn("StartOfTurn", "я сам"), turn("EagerEndOfTurn", "я сам программу пишу"))
        wait_until(lambda: live._open[UID]._draft is not None and live._open[UID]._draft._finished)
        assert env.voice.texts == []                        # the brain wrote it; nobody voiced it
        assert "say" not in line.kinds()
        line.ears().send(turn("EndOfTurn", "я сам программу пишу"))
        heard = line.expect("heard")
        done = line.expect("done")
    assert heard["timing"]["draft_reused"] is True and heard["timing"]["guesses"] == 1
    assert env.voice.texts[0] == "Ого," and env.voice.texts.count("Ого,") == 1
    assert after_heard(line)[0] == "Ого,"
    assert done["reply"] == "Ого, сам программу пишешь? А про что она?"
    assert done["timing"]["first_piece"] is not None
    assert done["timing"]["head_waited"] >= 0               # written before the turn was certain


def test_a_guess_they_talked_past_never_reached_the_voice(env):
    env.mind.replies = ["Ого, сам программу пишешь?", "А, понятно. И как успехи?"]
    with talk(env) as line:
        line.ears().send(turn("StartOfTurn", "я сам"), turn("EagerEndOfTurn", "я сам программу пишу"))
        wait_until(lambda: live._open[UID]._draft is not None and live._open[UID]._draft.opening)
        line.ears().send(turn("TurnResumed", "я сам программу пишу"),
                         turn("EndOfTurn", "я сам программу пишу но уже бросил"))
        line.expect("heard")
        done = line.expect("done")
    assert not any(text.startswith("Ого") for text in env.voice.texts)   # not even made
    assert "Ого," not in line.says()
    assert done["reply"] == "А, понятно. И как успехи?"
    assert roles() == ["user", "assistant"]


def test_a_first_word_that_is_ready_needs_no_sound_before_it(env, sounds):
    first_sound._made[(his_voice(), "Ого,")] = [(16000, b"OG")]
    env.mind.replies = ["Ого, сам программу пишешь?"]
    with talk(env) as line:
        line.ears().send(turn("StartOfTurn", "я сам"), turn("EagerEndOfTurn", "я сам программу пишу"))
        wait_until(lambda: live._open[UID]._draft is not None and live._open[UID]._draft.opening)
        line.ears().send(turn("EndOfTurn", "я сам программу пишу"))
        line.expect("heard")
        done = line.expect("done")
    assert after_heard(line)[0] == "Ого,"                    # straight in, no «м-м» first
    assert done["timing"]["head_ready"] is True


def test_a_written_answer_drops_the_word_his_sound_has_just_said(env, sounds, monkeypatch):
    """Nothing of a guess is voiced, so its first word can still go: «Хм…» at
    once, then «Ну я не знаю» — not «Хм…» and then «Хм, ну»."""
    _shares(monkeypatch, 0.0, 1.0)
    first_sound._made.pop((his_voice(), "Ну…"))              # only «Хм…» left to make
    env.mind.replies = ["Хм, ну я не знаю. Наверное, стоит."]
    with talk(env) as line:
        line.ears().send(turn("StartOfTurn", "а ты"),
                         turn("EagerEndOfTurn", "а ты как думаешь, стоит идти?"))
        wait_until(lambda: live._open[UID]._draft is not None and live._open[UID]._draft.opening)
        line.ears().send(turn("EndOfTurn", "а ты как думаешь, стоит идти?"))
        line.expect("heard")
        done = line.expect("done")
    says = after_heard(line)
    assert says[0] == "Хм…" and says[1].startswith("Ну я не знаю")
    assert done["reply"] == "Хм, ну я не знаю. Наверное, стоит."   # what he meant, kept whole


def test_a_whole_voice_keeps_two_pieces_in_the_making(env, monkeypatch):
    """A voice that makes each piece whole (Gemini through OpenRouter): while
    one plays, the next two are being made, so «Ого,» is not followed by a
    silence while the rest of the sentence is made."""
    monkeypatch.setattr(tts, "slow_start", lambda: True)
    env.mind.replies = ["Ого, сам? Слушай, это здорово. А про что она?"]
    env.voice.delay = 0.1
    with talk(env) as line:
        line.ears().send(turn("EndOfTurn", "я программу пишу"))
        line.expect("say")
        assert len(env.voice.texts) >= 2                     # the next one already on its way
        line.expect("done")


def test_the_brain_reads_ahead_on_the_first_turn_and_after_a_pause(env, monkeypatch):
    read: list[str] = []

    async def prewarm(user_id):
        read.append(user_id)

    monkeypatch.setattr(main, "prewarm", prewarm)
    with talk(env) as line:
        wait_until(lambda: read == [UID])                    # as the conversation opens
        line.ears().send(turn("StartOfTurn", "привет"))
        time.sleep(0.1)
        assert read == [UID]                                 # fresh: nothing to read again
        live._open[UID]._read_at = 0.0                       # …a long pause later
        line.ears().send(turn("StartOfTurn", "слушай"))
        wait_until(lambda: len(read) == 2)


def test_a_vow_a_guess_breaks_is_never_said_and_noted_once_real(env, monkeypatch):
    noted: list[str] = []
    monkeypatch.setattr(vow, "note", lambda user_id, slip, said: noted.append(slip))
    env.mind.replies = ["Я всего лишь программа, понимаешь. Но мне интересно."]
    with talk(env) as line:
        line.ears().send(turn("StartOfTurn", "ты кто"), turn("EagerEndOfTurn", "ты кто вообще"))
        time.sleep(0.2)
        assert not any("программа" in text for text in env.voice.texts)
        assert noted == []                                   # a guess writes nothing, notes nothing
        line.ears().send(turn("EndOfTurn", "ты кто вообще"))
        done = line.expect("done")
    assert noted == [vow.MACHINE]
    assert "программа" not in done["reply"]


def test_his_usual_first_word_is_played_ready_made_without_asking_the_voice(env):
    """first_sound.REACTIONS: «Ого,» is already made in his voice, so it plays
    the moment the brain writes it — and only the rest goes to the voice."""
    first_sound._made[(his_voice(), "Ого,")] = [(16000, b"OG")]
    env.mind.replies = ["Ого, сам программу пишешь?"]
    with talk(env) as line:
        line.ears().send(turn("StartOfTurn", "я сам"), turn("EagerEndOfTurn", "я сам программу пишу"))
        wait_until(lambda: live._open[UID]._draft is not None and live._open[UID]._draft.opening)
        line.ears().send(turn("EndOfTurn", "я сам программу пишу"))
        line.expect("heard")
        done = line.expect("done")
    assert "Ого," not in env.voice.texts                     # never asked of the voice
    assert after_heard(line)[0] == "Ого," and b"OG" in line.audio
    assert done["timing"]["head_ready"] is True
    assert done["reply"] == "Ого, сам программу пишешь?"



# ── thinking while they talk, and what it costs (2026-10-05) ────────────────
#
# The owner: «Companion must be thinking while person is speaking» — and then,
# of a draft at every pause: «будет тратить больше денег и лишней энергии».
# He thinks where the ears say they may have finished, and nowhere else.

def _audio(line, seconds: float) -> None:
    """Their speech, as far as the ears are concerned: loud enough to pass the
    gate, so that every frame reaches Flux and its clock (gate.py)."""
    for _ in range(int(seconds / 0.08)):
        line.ws.send_bytes(VOICE)


def test_a_pause_of_theirs_is_not_paid_for(env):
    """Flux sends the words every quarter second, the last ending ~0.16 s
    behind the voice, so a draft «at every 0.2 s pause» was a draft at nearly
    every message: 69 for five turns on the real ears. A pause costs nothing
    now."""
    env.mind.replies = ["Ого, сам программу пишешь? А про что она?"]
    with talk(env) as line:
        line.ears().send(turn("StartOfTurn", "я сам"), turn("Update", "я сам программу пишу", end=0.5))
        _audio(line, 0.8)                                   # a pause of theirs, nothing more said
        time.sleep(0.2)
        assert env.mind.calls == []                          # nobody asked the brain
        line.ears().send(turn("EagerEndOfTurn", "Я сам программу пишу."))
        wait_until(lambda: len(env.mind.calls) == 1)         # the ears' guess: now he thinks
        line.ears().send(turn("EndOfTurn", "Я сам программу пишу."))
        heard = line.expect("heard")
        line.expect("done")
    assert heard["timing"]["draft_reused"] is True
    assert len(env.mind.calls) == 1


def test_no_more_than_three_guesses_a_turn(env):
    """A turn that keeps stopping and going on is not paid for at every stop
    (LiveKit's max_retries, 3): after three, «договорил» begins the draft."""
    env.mind.delay = 0.01
    with talk(env) as line:
        ears = line.ears()
        said = "я"
        ears.send(turn("StartOfTurn", said))
        for n, word in enumerate(("думаю", "что", "завтра", "поеду"), start=1):
            said = f"{said} {word}"
            ears.send(turn("EagerEndOfTurn", said))
            if n <= 3:
                wait_until(lambda: len(env.mind.calls) == n)
            else:
                time.sleep(0.1)
            ears.send(turn("TurnResumed", said))
        time.sleep(0.05)
        assert len(env.mind.calls) == 3                      # the fourth guess was not taken
        said = f"{said} к маме"
        ears.send(turn("EagerEndOfTurn", said), turn("EndOfTurn", said))
        heard = line.expect("heard")
        line.expect("done")
    assert heard["timing"]["guesses"] == 3 and heard["timing"]["draft_reused"] is False
    assert len(env.mind.calls) == 4
    assert memory.recent_turns(UID)[0]["content"] == "я думаю что завтра поеду к маме"


def test_the_next_turn_may_guess_again(env):
    env.mind.delay = 0.01
    with talk(env) as line:
        ears = line.ears()
        for n, word in enumerate(("раз", "два", "три"), start=1):
            ears.send(turn("EagerEndOfTurn", f"ну {word}"))
            wait_until(lambda: len(env.mind.calls) == n)
            ears.send(turn("TurnResumed", f"ну {word}"))
        ears.send(turn("EndOfTurn", "ну раз два три"))
        line.expect("done")
        ears.send(turn("StartOfTurn", "а"), turn("EagerEndOfTurn", "а теперь"))
        wait_until(lambda: len(env.mind.calls) == 5)         # three guesses, an answer, a new guess


def test_a_guess_thrown_away_opens_the_line_to_the_brain_again(env, monkeypatch):
    """Cut off half-way, a reply takes its connection with it; the next one
    would begin with a handshake (+0.2 s, measured) — so it is opened again at
    once, while they are still talking."""
    opened: list[str] = []

    async def warm():
        opened.append("brain")

    monkeypatch.setattr(brain, "warm", warm)
    env.mind.delay = 0.05
    with talk(env) as line:
        wait_until(lambda: opened == ["brain"])              # as the conversation opens
        line.ears().send(turn("StartOfTurn", "я вот"), turn("EagerEndOfTurn", "я вот думаю"))
        wait_until(lambda: len(env.mind.calls) == 1)
        line.ears().send(turn("TurnResumed", "я вот думаю"))
        wait_until(lambda: len(opened) == 2)


def test_two_lines_to_a_voice_that_makes_two_pieces_at_once(env, monkeypatch):
    asked: list[int] = []

    async def warm(lines=1):
        asked.append(lines)

    monkeypatch.setattr(tts, "warm", warm)
    monkeypatch.setattr(tts, "slow_start", lambda: True)
    with talk(env):
        wait_until(lambda: asked == [live._AHEAD_WHOLE])


# ── his first word, ready-made, however short (2026-10-07) ──────────────────

def test_a_short_ready_first_word_plays_at_once_and_the_rest_is_voiced(env):
    """«Ох...» has two letters — too few to be a piece for the voice — but it
    is made already, so it is cut off and played the moment it is written."""
    first_sound._made[(his_voice(), "Ох…")] = [(16000, b"OH")]
    env.mind.replies = ["Ох... понимаю. Давно за рулём?"]
    with talk(env) as line:
        line.ears().send(turn("StartOfTurn", "я"), turn("EndOfTurn", "я водителем работаю"))
        line.expect("heard")
        done = line.expect("done")
    assert after_heard(line)[0] == "Ох..." and b"OH" in line.audio
    assert not any(text.startswith("Ох") for text in env.voice.texts)   # never asked of the voice
    assert env.voice.texts[0].startswith("понимаю.")        # the voice's first piece, short too
    assert done["reply"] == "Ох... понимаю. Давно за рулём?"


def test_a_first_word_that_is_not_made_is_not_cut_short():
    assert first_sound.opener(his_voice(), "Ох... понимаю. ") == 0          # nothing made yet
    first_sound._made[(his_voice(), "Ох…")] = [(16000, b"OH")]
    assert first_sound.opener(his_voice(), "Ох... понимаю.") == len("Ох...")
    assert first_sound.opener(his_voice(), "Ох...") == 0                    # nothing after it yet
    assert first_sound.opener(his_voice(), "Охотно, давай.") == 0
    assert first_sound.opener(his_voice(), "Ого… да") == 0                  # «О…» is not «Ого…»


# ── ten requests a minute (2026-10-07) ──────────────────────────────────────
#
# Google takes ten requests a minute for the voice on a paid key's first tier,
# and Bob used three or four an answer: in a real conversation he would have
# gone quiet. The owner: «Оптимизирую сейчас все для одного человека».

def test_a_rationed_voice_says_an_answer_in_two_requests(env, monkeypatch):
    monkeypatch.setattr(tts, "limited", lambda: True)
    env.mind.replies = ["После работы всегда так... Тяжёлый был день? Расскажи, что было."]
    env.mind.delay = 0.01
    with talk(env) as line:
        line.ears().send(turn("EndOfTurn", "я с работы пришёл, устал"))
        done = line.expect("done")
    assert env.voice.texts == ["После работы всегда так...", "Тяжёлый был день? Расскажи, что было."]
    assert done["reply"] == "После работы всегда так... Тяжёлый был день? Расскажи, что было."


def test_a_voice_that_is_not_rationed_still_goes_sentence_by_sentence(env, monkeypatch):
    monkeypatch.setattr(tts, "limited", lambda: False)
    env.mind.replies = ["После работы всегда так... Тяжёлый был день? Расскажи, что было."]
    env.mind.delay = 0.01
    with talk(env) as line:
        line.ears().send(turn("EndOfTurn", "я с работы пришёл, устал"))
        line.expect("done")
    assert len(env.voice.texts) >= 3


def test_after_a_ready_first_word_the_next_piece_waits_for_nothing_when_requests_are_left(env, monkeypatch):
    first_sound._made[(his_voice(), "Ох…")] = [(16000, b"OH")]
    monkeypatch.setattr(tts, "limited", lambda: True)
    monkeypatch.setattr(tts, "room", lambda: 10)
    env.mind.replies = ["Ох... понимаю. Давно за рулём? Наверное, устаёшь сильно."]
    env.mind.delay = 0.02
    with talk(env) as line:
        line.ears().send(turn("EndOfTurn", "я водителем работаю"))
        line.expect("done")
    assert env.voice.texts[0] == "понимаю."                  # alone, before the rest is written
    assert len(env.voice.texts) == 2


def test_with_few_requests_left_the_rest_follows_a_ready_first_word_whole(env, monkeypatch):
    first_sound._made[(his_voice(), "Ох…")] = [(16000, b"OH")]
    monkeypatch.setattr(tts, "limited", lambda: True)
    monkeypatch.setattr(tts, "room", lambda: 2)
    env.mind.replies = ["Ох... понимаю. Давно за рулём? Наверное, устаёшь сильно."]
    env.mind.delay = 0.02
    with talk(env) as line:
        line.ears().send(turn("EndOfTurn", "я водителем работаю"))
        line.expect("done")
    assert env.voice.texts == ["понимаю. Давно за рулём? Наверное, устаёшь сильно."]


# ── a breath, a word, or nothing (2026-10-08) ───────────────────────────────

def test_an_older_friend_breathes_more_and_says_less(env, sounds, monkeypatch):
    monkeypatch.setattr(first_sound, "SHARES", {k: (0.0, 1.0) for k in first_sound.SHARES})
    monkeypatch.setattr(first_sound, "SHARES_OLDER", {k: (1.0, 0.0) for k in first_sound.SHARES})
    persona.save_persona(UID, {**persona.load_persona(UID), "age": "71"})
    for text, pcm in ((first_sound.BREATH, BR), ("Да…", DA), ("Ну…", NU)):
        first_sound._made[(his_voice(), text)] = [(16000, pcm)]   # in the voice he has now
    with talk(env) as line:
        line.ears().send(turn("EndOfTurn", "я сегодня в саду работал"))
        line.expect("heard")
        line.expect("done")
    assert after_heard(line)[0] == "(вдох)"


def test_his_breath_is_never_taken_for_his_words_coming_back(env, sounds):
    with talk(env) as line:
        line.ears().send(turn("EndOfTurn", "я сегодня в школе был"))
        line.expect("done")
        assert "(вдох)" not in live._open[UID]._said


# ── his breath runs into his words (2026-10-08) ─────────────────────────────
#
# The owner: «в начале он говорит «э» или «м», затем оно резко обрывается,
# тишина, и затем начинает говорить, что неестественно. Звучит как
# некачественный SFX».

def test_his_breath_waits_for_his_words_and_comes_just_before_them(env, sounds):
    env.mind.replies = ["После работы всегда так... Тяжёлый был день?"]
    env.mind.delay = 0.25                                     # the brain takes a moment
    with talk(env) as line:
        line.ears().send(turn("EndOfTurn", "я с работы пришёл, устал"))
        line.expect("heard")
        began = time.monotonic()
        first = line.expect("say")
        waited = time.monotonic() - began
        line.expect("done")
    assert first["text"] == "(вдох)"
    assert waited > 0.15                                      # not at once, into a silence
    says = after_heard(line)
    assert says[:2] == ["(вдох)", "После работы всегда так..."]


def test_no_breath_before_a_first_word_that_is_ready_made(env, sounds):
    first_sound._made[(his_voice(), "Ох…")] = [(16000, b"OH" * 4000)]
    env.mind.replies = ["Ох... понимаю. Давно за рулём?"]
    with talk(env) as line:
        line.ears().send(turn("EndOfTurn", "я водителем работаю"))
        line.expect("done")
    assert after_heard(line)[0] == "Ох..."
    assert "(вдох)" not in after_heard(line)


def test_somebody_past_sixty_gets_the_deep_breath(env, sounds, monkeypatch):
    from app import young

    young.remember(UID, "72")
    first_sound._made[(his_voice(), first_sound.DEEP_BREATH)] = [(16000, b"DB" * 9600)]   # 0.6 s
    monkeypatch.setattr(first_sound, "SHARES_OLDER", {k: (1.0, 0.0) for k in first_sound.SHARES})
    monkeypatch.setattr(first_sound, "SHARES", {k: (0.0, 0.0) for k in first_sound.SHARES})
    with talk(env) as line:
        line.ears().send(turn("EndOfTurn", "я сегодня в саду работал"))
        line.expect("done")
    assert after_heard(line)[0] == "(вдох)"
    assert any(audio.endswith(b"DB" * 200) for audio in line.audio)          # the deep one


def test_his_words_start_on_the_word_not_on_the_voice_s_silence():
    rate = 1000
    silence, word = [0] * 250, [0, 5000, -5000] * 100
    pcm = live._from_first_sound(array.array("h", silence + word).tobytes(), rate)
    cut = array.array("h")
    cut.frombytes(pcm)
    assert len(cut) == len(word) - 1 + int(rate * live._LEAD_KEPT)   # 30 ms kept before the word
    assert cut[0] == 0                                                # faded in, no click
    assert live._from_first_sound(array.array("h", [0] * 500).tobytes(), rate) is None   # wait for more


def test_a_breath_longer_than_the_moment_is_joined_in_the_middle_and_never_cut(env, sounds, monkeypatch):
    """The owner, 2026-10-08: «it cuts in the middle of the sound». A breath
    longer than the time before his words is heard from the middle of it,
    faded in, to its own end — and his words do not wait for it."""
    first_sound._made[(his_voice(), first_sound.BREATH)] = [(16000, b"LB" * 32000)]   # two seconds
    env.voice.first_delay = 0.75
    with talk(env) as line:
        line.ears().send(turn("EndOfTurn", "я сегодня в саду работал"))
        done = line.expect("done")
    breath = breath_heard(line)
    assert b"LB" * 200 in breath and len(breath) < len(b"LB" * 32000)   # from the middle of it
    assert breath[:2] == b"\x00\x00"                         # faded in
    assert done["timing"]["after_sound"] > -0.2              # and his words did not wait for it


def test_his_breath_gives_way_to_his_words_when_they_come_and_fades_under_them(env, sounds):
    """Started to outlast the moment his words are expected, a breath that is
    still going when they come ends there — its rest faded out over a few
    hundredths of a second, as an in-breath ends when one speaks — and they
    follow at once."""
    first_sound._made[(his_voice(), first_sound.BREATH)] = [(16000, b"\x10\x27" * 32000)]   # two loud seconds
    env.voice.first_delay = 0.6
    with talk(env) as line:
        line.ears().send(turn("EndOfTurn", "я сегодня в саду работал"))
        done = line.expect("done")
    breath = array.array("h")
    breath.frombytes(breath_heard(line))
    assert 0 < len(breath) < 32000                           # it gave way before its end
    assert abs(breath[-1]) < 300                             # …fading, not cut
    assert abs(done["timing"]["after_sound"]) < 0.25          # and his words came straight after
