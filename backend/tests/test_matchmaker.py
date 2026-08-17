"""A friend walks in — created from the user's story, never designed by them.

The user writes about themselves and picks only age / gender / origin. The
friend's name and character are chosen for them (common ground included), and
he becomes the live persona the voice loop speaks as.
"""

from __future__ import annotations

import asyncio
import json

import pytest
from fastapi.testclient import TestClient

from app import brain, identity, main, matchmaker, memory, persona

#: The endpoint tests post with no token, so the created friend belongs to the
#: anonymous user — the same one the direct calls below use.
U = identity.ANONYMOUS

FRIEND = {
    "name": "Фёдор",
    "one_liner": "спокойный, тёплый, с хитрым юмором",
    "age": "62 года",
    "home": "город у гор",
    "backstory": "работал архитектором, теперь рисует и гуляет",
    "personality": "спокойный, наблюдательный, с хитрым юмором",
    "speech_style": "короткие фразы, любит словечко «стало быть»",
    "likes": ["футбол", "старые фильмы", "архитектура"],
    "dislikes": ["спешку"],
    "habits": ["утренние прогулки"],
    "cast": [{"name": "Гоша", "who": "сосед и напарник по шахматам"}],
}


#: Ten sketch-people, as the first call returns them.
TEN = "\n".join(
    f"{i}. {name}, {age} лет, {where}, {trade}. Нрав спокойный."
    for i, (name, age, where, trade) in enumerate(
        [
            ("Зоя", 31, "северный город", "крановщица"),
            ("Пётр", 44, "село под Тверью", "пасечник"),
            ("Лида", 67, "Ростов", "учительница физики"),
            ("Марат", 28, "Казань", "машинист метро"),
            ("Нина", 52, "городок в горах", "фельдшер"),
            ("Гриша", 73, "посёлок при заводе", "сварщик"),
            ("Тамара", 39, "Иркутск", "проводница"),
            ("Фёдор", 62, "город у гор", "архитектор"),
            ("Слава", 24, "Пермь", "автомеханик"),
            ("Оля", 81, "деревня на Волге", "почтальон"),
        ],
        start=1,
    )
)


@pytest.fixture
def pen(monkeypatch):
    """Fake both AI calls: the ten sketches, then the deep write (wrapped in
    prose + code fences — the messy case)."""
    calls: list[str] = []

    async def fake_generate(system_prompt, user_text, max_tokens=1500, model=None, timeout=None):
        calls.append(user_text)
        if "ДЕСЯТЬ" in system_prompt:
            return TEN
        return "Вот его друг:\n```json\n" + json.dumps(FRIEND, ensure_ascii=False) + "\n```"

    monkeypatch.setattr(brain, "generate_text", fake_generate)
    return calls


def test_friend_is_created_and_becomes_the_persona(pen):
    created = asyncio.run(
        matchmaker.create_companion(
            U,
            "Люблю футбол, старые фильмы и архитектуру.",
            wishes="Хотел бы кого-то спокойного, кто много читает.",
            age="около 60",
            gender="мужчина",
            origin="Грузия",
        )
    )
    # The reveal: he has his own name — and the user's wishes reached BOTH
    # calls. Wishes are law at every stage, not just the last one.
    assert created["name"] == "Фёдор"
    for prompt in pen:
        assert "кого-то спокойного, кто много читает" in prompt
        assert "возраст: около 60" in prompt
        assert "пол: мужчина" in prompt
        assert "откуда: Грузия" in prompt
        assert "Люблю футбол" in prompt

    # He is now the live persona — exactly as created, never topped up from
    # the built-in template (that merge is how every friend got the same cat).
    live = persona.load_persona(U)
    assert live["name"] == "Фёдор"
    assert live["age"] == "62 года"
    assert live["speech_style"] == FRIEND["speech_style"]
    assert "opinions" not in live  # the pen didn't write it → it isn't there
    assert "_note" not in live


def test_no_wishes_is_fine(pen):
    # Leaving "who would you like to meet?" blank is a perfectly good choice —
    # the friend is then built from their story plus the dice alone.
    created = asyncio.run(matchmaker.create_companion(U, "Люблю рыбалку и тишину."))
    assert created["name"] == "Фёдор"
    assert "Пожеланий о друге он не оставил" in pen[0]


def test_sparks_start_the_imagination_somewhere_new():
    """The dice carry no biography — only where to start looking.

    Sparks are ordinary nouns («керосинка», «ипподром»), never traits. Nothing
    about a person is decided here; the model still authors every character.
    What the sparks buy is a different starting point each time, so its
    imagination doesn't set off down the same road it always takes.
    """
    import random

    a = matchmaker._roll_sparks(random.Random(1))
    b = matchmaker._roll_sparks(random.Random(2))
    assert a != b
    assert len(set(a)) == len(a)  # no word twice in one striking

    # Across many creations the sparks must actually roam the lexicon, or
    # they're decoration.
    seen = {w for seed in range(60) for w in matchmaker._roll_sparks(random.Random(seed))}
    assert len(seen) >= 100

    # And they must stay NOUNS, never character traits — the moment a spark
    # prescribes who someone is, we're back to premade people.
    for word in matchmaker._SPARK_WORDS:
        assert not any(
            word.startswith(stem)
            for stem in ("добр", "злой", "весёл", "груст", "умн", "ворчлив")
        ), f"{word!r} is a trait, not a spark"


def test_ten_strangers_then_the_dice_choose():
    """Two mechanisms, and both are load-bearing.

    Asking for TEN at once lets the model see its own repetition inside one
    reply and steer away from it — across separate replies it can't, and
    returns its favourite every time. Then Python picks, because a model asked
    to choose picks that same favourite and undoes the whole thing.
    """
    import random

    sketches = matchmaker._split_sketches(TEN)
    assert len(sketches) == 10
    assert "крановщица" in sketches[0]

    picked = {random.Random(seed).choice(sketches) for seed in range(40)}
    assert len(picked) >= 7  # the pick genuinely roams the ten


def test_a_reply_that_isnt_a_list_still_yields_someone():
    """Degraded, not broken: if the ten come back as prose, the whole text
    becomes one sketch and a friend is still born."""
    assert matchmaker._split_sketches("Просто человек, живёт и работает.") == [
        "Просто человек, живёт и работает."
    ]


def test_wishes_are_law_at_every_stage(pen):
    # Not just in the final write — a wish ignored while sketching is a wish
    # that never had a chance to be honoured.
    asyncio.run(
        matchmaker.create_companion(
            U,
            "Люблю горы.", age="около 30", gender="женщина", origin="с Урала"
        )
    )
    assert len(pen) == 2
    for prompt in pen:
        assert "возраст: около 30" in prompt
        assert "пол: женщина" in prompt
        assert "откуда: с Урала" in prompt


def test_new_friend_starts_with_a_clean_slate(pen):
    """A new person means a new life — and only HIS side of memory is wiped.

    Without this, friend number two inherits friend number one's stories about
    himself and contradicts his own biography mid-sentence. What was learned
    about the USER stays: their birthday is true no matter who they talk to.
    """
    memory.log_turn(U, "user", "привет")
    memory.add_memory(U, "fact", "Я всю жизнь рыбачил", owner="bob")
    memory.add_memory(U, "fact", "У него день рождения в мае", owner="elder")

    asyncio.run(matchmaker.create_companion(U, "Люблю тишину."))

    assert memory.recent_turns(U) == []
    assert memory.counts(U, "bob").get("fact", 0) == 0
    assert memory.counts(U, "elder").get("fact", 0) == 1


def test_unparseable_reply_fails_gently(monkeypatch):
    async def fake_generate(system_prompt, user_text, max_tokens=1500, model=None, timeout=None):
        return "Извини, сегодня без JSON."

    monkeypatch.setattr(brain, "generate_text", fake_generate)
    with pytest.raises(RuntimeError):
        asyncio.run(matchmaker.create_companion(U, "про меня"))


def test_half_a_person_is_refused(monkeypatch):
    """A character missing its core isn't a person yet — and the holes must
    never again be filled from the template. Rejecting is the only honest
    option left, so it has to actually happen."""
    async def fake_generate(system_prompt, user_text, max_tokens=1500, model=None, timeout=None):
        if "ДЕСЯТЬ" in system_prompt:
            return TEN
        return json.dumps({"name": "Аноним", "age": "40 лет"}, ensure_ascii=False)

    monkeypatch.setattr(brain, "generate_text", fake_generate)
    with pytest.raises(RuntimeError):
        asyncio.run(matchmaker.create_companion(U, "про меня"))


def test_a_bad_reply_is_never_shown_blind():
    """The regression this pins: three different causes (no JSON at all,
    broken JSON, a missing required field) used to raise the identical blank
    message, both to the user and in the terminal — there was no way to tell
    which had happened, or what the model had actually said, without
    reproducing it live. Every branch must now name itself and show a preview
    of the real response."""
    with pytest.raises(RuntimeError):
        matchmaker._extract_json("Извини, сегодня без JSON.")

    with pytest.raises(RuntimeError):
        matchmaker._extract_json('{"name": "Аноним", "age":}')  # malformed

    with pytest.raises(RuntimeError):
        # Valid JSON, but missing everything required except a name.
        matchmaker._extract_json('{"name": "Аноним"}')


def test_truncated_json_is_told_apart_from_not_json_at_all(capsys):
    """The live bug this pins: a real reply was cut off mid-backstory by
    max_tokens, with an opening { and NO closing } anywhere at all. That used
    to raise the exact same "ответ не похож на JSON вовсе" as a reply with no
    braces whatsoever — which sends a debugging session off reasoning from a
    raw preview instead of straight to the actual cause. The two must be
    told apart at the point of failure."""
    with pytest.raises(RuntimeError):
        matchmaker._extract_json(
            '```json\n{\n  "name": "Кира",\n  "backstory": "Училась на '
            'биофак, бросила на третьем курсе, потому что'  # cut off, no }
        )
    truncated_msg = capsys.readouterr().err
    assert "не хватило max_tokens" in truncated_msg

    with pytest.raises(RuntimeError):
        matchmaker._extract_json("Извини, сегодня без JSON.")
    not_json_msg = capsys.readouterr().err
    assert "не хватило max_tokens" not in not_json_msg
    assert "нет вообще ни одной" in not_json_msg


def test_the_write_budget_is_generous_for_the_schema_it_asks_for():
    """The actual live fix: max_tokens=2500 was truncating real replies. The
    schema asks for ~19 fields, several wanting real literary Russian prose,
    and Cyrillic tokenizes less efficiently than English — 2500 had not been
    revisited as fields were added over several past sessions. This just
    keeps the number from silently drifting back down without anyone
    noticing until it starts truncating people again."""
    assert matchmaker._WRITE_MAX_TOKENS >= 4000


def test_missing_required_fields_are_named(capsys):
    with pytest.raises(RuntimeError):
        matchmaker._extract_json(
            json.dumps({"name": "Аноним", "age": "40 лет"}, ensure_ascii=False)
        )
    err = capsys.readouterr().err
    # The exact gap that met the app live: everything present except the
    # fields the pen skipped. Somebody debugging this later needs to see
    # WHICH ones, not just "failed".
    assert "home" in err and "backstory" in err and "personality" in err
    assert "speech_style" in err
    assert "Аноним" not in err.split("ответ модели")[0]  # the reason, not the dump


def test_the_ten_strangers_and_deep_write_calls_are_both_bounded(pen, monkeypatch):
    """The other half of the real bug: the reading was the slow one, but
    neither of THESE two calls had a timeout either. On a stall in either one,
    the client's own ceiling was the only thing that would ever have given
    up — silently, after a long wait, with no clean failure in between."""
    timeouts: list[float | None] = []

    async def recording(system_prompt, user_text, max_tokens=1500, model=None, timeout=None):
        timeouts.append(timeout)
        if "ДЕСЯТЬ" in system_prompt:
            return TEN
        return json.dumps(FRIEND, ensure_ascii=False)

    monkeypatch.setattr(brain, "generate_text", recording)
    asyncio.run(matchmaker.create_companion(U, "Люблю тишину."))

    assert timeouts == [matchmaker._STAGE_TIMEOUT, matchmaker._STAGE_TIMEOUT]


def test_a_bad_first_reply_gets_one_retry_before_giving_up(monkeypatch):
    """The one stage in creation with no fallback of its own: a failed
    reading is skipped, an unparseable ten-strangers reply degrades to one
    sketch, but a broken deep write used to fail creation outright — on the
    single screen where that means «он пока не смог прийти» to someone who
    came specifically to meet him. A malformed reply is a real, observed
    failure mode of the model itself, and asking again routinely fixes it."""
    write_calls = 0

    async def fake_generate(system_prompt, user_text, max_tokens=1500, model=None, timeout=None):
        nonlocal write_calls
        if "ДЕСЯТЬ" in system_prompt:
            return TEN
        write_calls += 1
        if write_calls == 1:
            return "Извини, не в этот раз."  # no JSON — the exact live symptom
        return json.dumps(FRIEND, ensure_ascii=False)

    monkeypatch.setattr(brain, "generate_text", fake_generate)
    created = asyncio.run(matchmaker.create_companion(U, "про меня"))

    assert created["name"] == "Фёдор"
    assert write_calls == 2


def test_two_bad_replies_in_a_row_still_fails_and_says_so(monkeypatch, capsys):
    """The retry is bounded at one — this must not become a silent loop that
    keeps spending money while someone stares at an arriving screen."""
    write_calls = 0

    async def fake_generate(system_prompt, user_text, max_tokens=1500, model=None, timeout=None):
        nonlocal write_calls
        if "ДЕСЯТЬ" in system_prompt:
            return TEN
        write_calls += 1
        return "Извини, не в этот раз."

    monkeypatch.setattr(brain, "generate_text", fake_generate)
    with pytest.raises(RuntimeError):
        asyncio.run(matchmaker.create_companion(U, "про меня"))

    assert write_calls == 2  # tried twice, not once, not forever
    assert capsys.readouterr().err.count("друг не собрался") == 2


def test_create_endpoint(pen):
    with TestClient(main.app) as client:
        r = client.post(
            "/api/companion/create",
            json={
                "about": "Люблю футбол и сериалы",
                "wishes": "Кого-нибудь весёлого",
                "age": "30",
                "gender": "женщина",
            },
        )
        assert r.status_code == 200
        assert r.json()["name"] == "Фёдор"

        # …and the wishes are optional — the story alone is enough.
        assert (
            client.post(
                "/api/companion/create", json={"about": "Люблю тишину"}
            ).status_code
            == 200
        )

        # An empty story is the one thing we can't work with.
        assert (
            client.post("/api/companion/create", json={"about": "   "}).status_code
            == 400
        )
