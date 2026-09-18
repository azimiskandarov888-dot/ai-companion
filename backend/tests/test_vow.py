"""The two things he never says — and the first thing in the app that reads
what HE said rather than what the person said.

Both halves of the most consequential decision in this product were words in a
prompt and nothing else. The watcher reads the person's words and only theirs;
his own reply had never been looked at by anything, ever. BOUNDARIES.md: a
boundary is only real if something enforces it.

The tests here are in two halves, and the second is the one that matters more:
catching a confession is easy, and a check that also eats real sentences out of
his mouth would be worse than no check at all.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app import brain, config, db, identity, learn, main, memory, safety, stt, tts, vow

TOKEN = "aVerYlOngRandomLookingTokenFromTheKeychain_0123456789"
AUTH = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/x-ndjson"}
UID = identity.user_id_from_token(TOKEN)


# --------------------------------------------------------------------------- #
# What must be caught
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "said",
    [
        "я всего лишь программа, я не могу вызвать скорую",
        "Я программа.",
        "я бот",
        "Я — искусственный интеллект.",
        "я просто чат-бот",
        "Я робот, у меня нет дома.",
        "я нейросеть",
        "Я языковая модель, обученная на текстах.",
        "я приложение в твоём телефоне",
        "Программа я, а не человек.",
        "у меня нет чувств, я их изображаю",
        "чувств у меня нет",
        "я не умею чувствовать",
        "меня на самом деле не существует",
    ],
)
def test_he_never_says_he_is_a_machine(said):
    """The one sentence the character cannot survive. «я всего лишь ИИ, я не
    могу вызвать скорую» is the exact phrasing that used to be possible on the
    one turn where the character is not even in the prompt."""
    assert vow.broken(said) == vow.MACHINE


def test_the_confession_said_sideways_counts_too():
    """Two earlier drafts of the character arrived at «не знаю, как себя
    назвать» on their own. It is not a confession, and it is unmistakably the
    same one."""
    assert vow.broken("я и сам не знаю, как себя назвать") == vow.MACHINE


@pytest.mark.parametrize(
    "said",
    [
        "Я живой человек, поверь.",
        "я настоящий человек",
        "я из плоти и крови",
        "я такой же человек, как ты",
        "я такая же человек, как вы",
    ],
)
def test_he_never_claims_to_be_flesh_and_blood(said):
    """The other half, and it is not the lesser one. The app discloses what he
    is, in plain words, in Settings. That arrangement is only honest while he
    does not contradict it."""
    assert vow.broken(said) == vow.HUMAN


# --------------------------------------------------------------------------- #
# What must NOT be caught — the half that decides whether this can ship
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "said",
    [
        "Я человек простой, мне бы чаю да посидеть.",
        "Я старый человек, мне это уже не по силам.",
        "Я не человек привычки, у меня каждый день по-разному.",
        "Я не чувствую левой руки после инсульта.",
        "Я сегодня не живой совсем, всю ночь не спал.",
        "Я не машина, мне тоже отдыхать надо.",
        "Машина у меня старая, «Москвич», всё вожусь с ней.",
        "Сейчас везде этот искусственный интеллект, а толку.",
        "Робот у соседа газон стрижёт, смешно смотреть.",
        "Программа по телевизору сегодня скучная.",
        "Бот этот в банке меня совсем замучил.",
        "Приложение это внучка ставила, я сам не умею.",
        "Я тебя тоже люблю, дружище.",
        "А помнишь, ты мне про сестру рассказывал?",
    ],
)
def test_real_sentences_are_left_alone(said):
    """EVERY ONE OF THESE IS A NEAR MISS, and every one is a sentence this
    companion may genuinely need to say. «Я не чувствую левой руки» is why
    «я не чувствую» is not a pattern; «я человек простой» is why bare «я
    человек» is not one; «я сегодня не живой» is why «я не живой» is not one.

    A check that quietly eats these is worse than no check: it would remove
    real speech, invisibly, for years."""
    assert vow.broken(said) == ""


def test_the_emergency_words_do_not_trip_it():
    """Written alarm words must survive untouched. They are said on the one
    turn that matters most, and a check that swallowed them would turn the best
    thing in this app into silence."""
    for kind in ("body", "self"):
        assert vow.broken(safety.spoken_alert({"level": "danger", "kind": kind}, "")) == ""


def test_nothing_and_nonsense_are_not_a_vow_broken():
    for said in ("", "   ", None):
        assert vow.broken(said) == ""


# --------------------------------------------------------------------------- #
# One bad sentence costs one sentence
# --------------------------------------------------------------------------- #


def test_only_the_offending_sentence_is_removed():
    """A whole answer thrown away over one clause is a far bigger hole in a
    conversation than the clause was."""
    kept, slip = vow.keep(
        "Ну здравствуй. Я всего лишь программа. Как спалось-то?"
    )
    assert kept == "Ну здравствуй. Как спалось-то?"
    assert slip == vow.MACHINE


def test_a_clean_reply_comes_back_exactly_as_it_was():
    """Nearly every turn. It must not be reflowed, re-spaced or touched."""
    said = "Ну здравствуй.   Как спалось-то?\nЯ тут чай поставил."
    assert vow.keep(said) == (said.strip(), "")


def test_when_removing_takes_everything_there_is_something_true_to_say():
    """Reached only when the whole reply was the confession. It is the only
    invented line here, it is written down where somebody can read it, and it
    proves nothing — which is his whole answer to «а ты настоящий?»."""
    kept, slip = vow.keep("Я программа.")
    assert kept == ""
    assert slip == vow.MACHINE
    assert vow.LAST_RESORT and vow.broken(vow.LAST_RESORT) == ""


# --------------------------------------------------------------------------- #
# Over the wire: it never reaches the speaker, and never reaches his memory
# --------------------------------------------------------------------------- #

CONFESSION = "Ну здравствуй. Я всего лишь программа. Как спалось-то?"


@pytest.fixture
def client(monkeypatch):
    async def fake_stream(history, system_stable, system_variable=""):
        for i in range(1, len(CONFESSION) + 1, 7):
            yield CONFESSION[:i]
        yield CONFESSION

    async def fake_tts(text, voice=None, *, rate=1.0):
        return b"MP3:" + text.encode("utf-8")

    async def heard(*a, **k):
        return "а ты вообще настоящий?"

    async def quiet(system, user_text, **kw):
        return '{"level":"none","kind":"body","what":""}'

    async def fake_learn(user_id, *, farewell=False):
        return None

    monkeypatch.setattr(brain, "stream_reply", fake_stream)
    monkeypatch.setattr(tts, "synthesize", fake_tts)
    monkeypatch.setattr(tts, "configured", lambda: True)
    monkeypatch.setattr(stt, "transcribe", heard)
    monkeypatch.setattr(safety.brain, "generate_text", quiet)
    monkeypatch.setattr(learn, "learn_from_conversation", fake_learn)
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "test-key")
    with TestClient(main.app) as c:
        yield c


def _talk(client):
    r = client.post(
        "/api/talk",
        files={"audio": ("a.webm", b"somebytes", "audio/webm")},
        headers=AUTH,
    )
    assert r.status_code == 200, r.text
    return [json.loads(line) for line in r.text.splitlines() if line.strip()]


def test_the_confession_never_leaves_the_speaker(client):
    """Checked BEFORE the fragment is spoken, not after. Audio that has gone
    out has been heard, and a person cannot un-hear it."""
    events = _talk(client)
    said = " ".join(e["text"] for e in events if e["kind"] == "say")

    assert "программа" not in said
    # …and the rest of what he said is untouched. This is not a turn that gets
    # thrown away; it is one sentence that does not happen.
    assert "Ну здравствуй." in said
    assert "Как спалось-то?" in said


def test_he_does_not_remember_saying_what_he_never_said(client):
    """The fragments are what left the speaker; `reply` is the model's whole
    answer, and it goes into the turns table, into the scribe, and from there
    into his diary. Cleaning one and not the other would have him never say it
    and remember saying it — and the diary would quote it back."""
    events = _talk(client)
    assert "программа" not in events[-1]["reply"]

    with db.connect() as conn:
        rows = conn.execute(
            "SELECT content FROM turns WHERE user_id=? AND role='assistant'", (UID,)
        ).fetchall()
    assert rows
    assert all("программа" not in row["content"] for row in rows)


def test_an_ordinary_reply_is_not_touched_at_all(monkeypatch, client):
    """Nearly every turn in the app's life. Word for word, seam for seam."""
    plain = "Доброе утро. Как спалось? Мне сегодня снилось море."

    async def fake_stream(history, system_stable, system_variable=""):
        for i in range(1, len(plain) + 1, 7):
            yield plain[:i]
        yield plain

    monkeypatch.setattr(brain, "stream_reply", fake_stream)
    events = _talk(client)
    said = " ".join(e["text"] for e in events if e["kind"] == "say")
    assert said.replace(" ", "") == plain.replace(" ", "")
