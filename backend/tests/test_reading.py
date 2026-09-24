"""The reading — understanding a person from HOW they wrote.

The most important stage in the app, and the one with the most ways to fail
quietly. These tests pin the three properties that matter: it never blocks a
friend from arriving, it never leaks into what the companion says, and the
slice that reaches every turn stays in the cached half of the prompt.
"""

from __future__ import annotations

import asyncio
import json
import re
import time

import pytest

from app import (db, brain, companion, config, identity, matchmaker, memory, mood,
                 persona, reading)

#: These tests check config.READING_PATH / config.PERSONA_PATH directly, which
#: are the anonymous user's files — so that is whose reading this is.
U = identity.ANONYMOUS

READING = {
    "verdict": "устал держать лицо; нужен тот, при ком можно не держать",
    "register": "пишет коротко и сухо; говори так же — без обилия нежности",
    "would_ring_false": "бодрый оптимизм и «всё будет хорошо»",
    "would_reach_them": "спокойный, медленный, с паузами, без напора",
    "needs_pushback_on": "что он «никому не интересен»",
    "do_not_touch": "смерть жены",
    "common_ground_seeds": ["рыбалка", "старые машины"],
    "confidence": "твёрдое",
}


@pytest.fixture
def reader(monkeypatch):
    """Fake the deep model. Records what it was asked to read."""
    calls: list[str] = []

    async def fake_think(system_prompt, user_text, *, model=None, effort="high",
                         max_tokens=8000, timeout=None):
        # think() serves the reading AND the deep write now. This fixture is
        # the READER; the write is faked per-test where it's needed.
        if "знакомишь людей" in system_prompt:
            raise RuntimeError("this fixture only reads")
        calls.append(user_text)
        return "Вот чтение:\n```json\n" + json.dumps(READING, ensure_ascii=False) + "\n```"

    monkeypatch.setattr(brain, "think", fake_think)
    return calls


def test_reads_the_person_and_keeps_the_reading(reader):
    result = asyncio.run(reading.read_person("Мне не спится. Так вышло.", "кого-то весёлого"))
    assert result["do_not_touch"] == "смерть жены"

    # The text is passed VERBATIM — the whole method depends on the exact
    # words, so anything that summarises before reading defeats the stage.
    assert "Мне не спится. Так вышло." in reader[0]
    assert "кого-то весёлого" in reader[0]

    reading.save(U, result)
    assert reading.load(U)["register"] == READING["register"]


def test_a_reading_without_the_essentials_is_refused(monkeypatch):
    """Half a reading is worse than none: it would silently shape a character
    on nothing. Refusing sends creation down the no-brief path instead."""
    async def thin(system_prompt, user_text, **kwargs):
        return json.dumps({"surface": "любит рыбалку"}, ensure_ascii=False)

    monkeypatch.setattr(brain, "think", thin)
    with pytest.raises(reading.ReadingFailed):
        asyncio.run(reading.read_person("про меня"))


def test_empty_story_is_refused_before_spending_anything(monkeypatch):
    def explode(*a, **k):
        raise AssertionError("should never call the model for an empty story")

    monkeypatch.setattr(brain, "think", explode)
    with pytest.raises(reading.ReadingFailed):
        asyncio.run(reading.read_person("   "))


def test_the_brief_carries_judgement_but_never_the_quotes(reader):
    """The pen gets what to DO with the person, not the person's own words.

    Handed the quotes, a model writes a character who echoes them back — which
    is the single most alarming thing this app could do: a stranger repeating
    your own sentences to you on the first evening.
    """
    brief = reading.as_brief(READING)
    assert "спокойный, медленный" in brief          # what would reach them
    assert "смерть жены" in brief                    # what never to touch
    assert "мне не спится" not in brief              # …but never their words
    assert "так вышло" not in brief


def test_the_standing_block_is_only_what_every_turn_needs():
    block = reading.standing_block(READING)
    assert "без обилия нежности" in block            # register
    assert "бодрый оптимизм" in block                # what rings false
    assert "смерть жены" in block                    # what not to touch
    # …and what he lacks, first: it is the one thing the whole reading is
    # for, and the re-reads keep correcting it for as long as they talk.
    assert "устал держать лицо" in block
    # Everything else is already baked into who he is — carrying it per-turn
    # would be tokens spent on every reply for no behavioural change.
    assert "рыбалка" not in block


def test_the_standing_block_rides_in_the_cached_half():
    """It describes the person, not today — so it belongs beside WHO HE IS,
    where the cache reads it instead of re-processing it every turn."""
    stable, variable = companion.build_system_parts(
        persona_block="ТЫ — Фёдор.",
        reading_block=reading.standing_block(READING),
        memory_context="Вчера говорили о рыбалке.",
    )
    assert "смерть жены" in stable
    assert "смерть жены" not in variable
    assert "рыбалке" in variable      # today's context stays uncached


def test_no_reading_no_block():
    assert reading.standing_block(None) == ""
    assert reading.as_brief(None) == ""


def test_a_failed_reading_still_lets_a_friend_walk_in(monkeypatch, capsys):
    """The one property that outranks depth: a person who came to meet someone
    must meet someone. A dead reading degrades the character; it never denies
    it — and it says so loudly rather than vanishing."""
    async def broken_reading(*a, **k):
        raise RuntimeError("модель недоступна")

    async def fake_generate(system_prompt, user_text, max_tokens=1500, model=None,
                            timeout=None, effort=None):
        return "1. Зоя, 31, северный город, крановщица.\n2. Пётр, 44, село, пасечник."

    async def fake_think(system_prompt, user_text, **kwargs):
        return json.dumps(
            {
                "name": "Зоя", "age": "31 год", "home": "северный город",
                "backstory": "выросла у реки", "personality": "прямая", "flaws": ["перебивает"], "intention": "перебрать лодку до заморозков",
            "things": ["чайник, который свистит не так", "кресло у окна"],
                "speech_style": "коротко, по делу",
            },
            ensure_ascii=False,
        )

    monkeypatch.setattr(reading, "read_person", broken_reading)
    monkeypatch.setattr(brain, "generate_text", fake_generate)
    monkeypatch.setattr(brain, "think", fake_think)

    created = asyncio.run(matchmaker.create_companion(U, "Люблю тишину."))
    assert created["name"] == "Зоя"
    assert "чтение человека не получилось" in capsys.readouterr().err


def test_the_reading_survives_starting_over(reader, monkeypatch):
    """A new companion doesn't make the person a different person. «Начать
    заново» replaces who they talk to, not who they are."""
    reading.save(U, READING)

    async def fake_generate(system_prompt, user_text, max_tokens=1500, model=None,
                            timeout=None, effort=None):
        return "1. Гриша, 73, посёлок, сварщик.\n2. Нина, 52, горы, фельдшер."

    real_think = brain.think

    async def fake_think(system_prompt, user_text, **kwargs):
        # The reading still goes through the `reader` fixture's fake; only the
        # write is answered here.
        if "знакомишь людей" not in system_prompt:
            return await real_think(system_prompt, user_text, **kwargs)
        return json.dumps(
            {
                "name": "Гриша", "age": "73 года", "home": "посёлок",
                "backstory": "варил всю жизнь", "personality": "ворчливый", "flaws": ["перебивает"], "intention": "перебрать лодку до заморозков",
            "things": ["чайник, который свистит не так", "кресло у окна"],
                "speech_style": "короткие фразы",
            },
            ensure_ascii=False,
        )

    monkeypatch.setattr(brain, "generate_text", fake_generate)
    monkeypatch.setattr(brain, "think", fake_think)
    asyncio.run(matchmaker.create_companion(U, "Люблю тишину."))

    assert persona.load_persona(U)["name"] == "Гриша"
    assert reading.load(U) is not None          # the person is still known
    assert config.READING_PATH.exists()


# --------------------------------------------------------------------------- #
# Reading him again, for as long as they know each other
# --------------------------------------------------------------------------- #
#
# The first reading is the worst one he will ever have: a few minutes of
# somebody talking to a machine they have never met, on the day it was
# installed. Everything since is better evidence.

W = "u-reread"


def test_a_reread_refines_and_never_demolishes(monkeypatch):
    """A field the model forgets to return must survive. A dropped key is a
    model slip, not a discovery that the person no longer has a register."""
    async def fake_think(system, prompt, **kw):
        return '{"register": "теплее, чем казалось", "learned": "не любит, когда его жалеют"}'

    monkeypatch.setattr(reading.brain, "think", fake_think)
    before = {"register": "сухо", "do_not_touch": "смерть жены",
              "would_ring_false": "бодрячок"}
    after = asyncio.run(reading.reread(W, before, [{"role": "user", "content": "ну"}]))

    assert after["register"] == "теплее, чем казалось"      # revised
    assert after["do_not_touch"] == "смерть жены"           # kept, untouched
    assert after["would_ring_false"] == "бодрячок"          # kept, untouched
    assert after["learned"] == ["не любит, когда его жалеют"]  # new, accumulated


def test_an_empty_stretch_of_talk_changes_nothing(monkeypatch):
    called = False

    async def fake_think(system, prompt, **kw):
        nonlocal called
        called = True
        return "{}"

    monkeypatch.setattr(reading.brain, "think", fake_think)
    before = {"register": "сухо"}
    assert asyncio.run(reading.reread(W, before, [])) == before
    assert not called


def test_what_was_learned_live_reaches_every_turn():
    """The most valuable line in the whole reading, because the person said it
    themselves rather than being inferred."""
    block = reading.standing_block({"learned": "просил не звать его по отчеству"})
    assert "просил не звать его по отчеству" in block
    assert "дороже всего" in block


def test_it_waits_for_enough_conversation(monkeypatch):
    """Cheap when it isn't worth doing: no reading, no brain call."""
    called = False

    async def fake_reread(*a, **kw):
        nonlocal called
        called = True
        return {}

    monkeypatch.setattr(reading, "reread", fake_reread)
    asyncio.run(reading.keep_reading("nobody-has-a-reading"))
    assert not called


def test_how_they_want_to_matter_is_its_own_axis():
    """The one the whole «тебя давно не было» argument turned on, and the one
    the reading had no room for. It cannot be inferred from age or averaged
    across people: to one person being missed out loud is the proof they are
    needed, to another it is a weight, to a third it is a reproach."""
    assert "closeness" in reading._READING_SYSTEM
    assert "КАК ЭТОТ ЧЕЛОВЕК ХОЧЕТ БЫТЬ НУЖНЫМ" in reading._READING_SYSTEM
    # It must refuse to guess rather than pick a middle — and refuse by
    # leaving it EMPTY. It used to say «так и напиши, что не видно», and a
    # written «не видно» is not nothing: standing_block wraps it in an
    # instruction and it rides into every turn of every conversation, a
    # paragraph telling him how this person wants to matter that says nothing.
    assert "если из текста не видно — оставь пустым" in reading._READING_SYSTEM
    assert "так и напиши, что не видно" not in reading._READING_SYSTEM


def test_closeness_reaches_every_single_turn():
    """It governs what he says whenever somebody comes back, so it cannot
    live only in the write — it has to ride in the standing block."""
    block = reading.standing_block({"closeness": "ему нужно слышать, что его ждали"})
    assert "ему нужно слышать, что его ждали" in block
    assert "«я тебя ждал»" in block


def test_the_reread_watches_for_it_where_it_actually_shows():
    """An intake almost never reveals this. Coming back after a gap reveals it
    every time."""
    assert "closeness" in reading._REREAD_SYSTEM
    assert "когда он возвращается после перерыва" in reading._REREAD_SYSTEM


def test_what_lifts_him_is_read_and_reaches_every_turn():
    """Getting this wrong is expensive: cheerfulness aimed at somebody who
    needed silence is worse than saying nothing at all."""
    assert "what_lifts_him" in reading._READING_SYSTEM
    assert "ЧЕМ ЕГО ПОДНИМАТЬ" in reading._READING_SYSTEM
    block = reading.standing_block({"what_lifts_him": "молчать рядом, без бодрости"})
    assert "молчать рядом, без бодрости" in block
    assert "не угадывай" in block


def test_the_reread_learns_it_from_what_actually_worked():
    """Not from the intake — from what happened AFTER he was low."""
    assert "посмотри, что было ДАЛЬШЕ" in reading._REREAD_SYSTEM
    assert "А после чего замыкался сильнее?" in reading._REREAD_SYSTEM


def test_one_bad_evening_is_never_evidence():
    """The diagnostic he described, with the half that makes it safe. Mood
    drops, he's asked, he doesn't answer — that looks EXACTLY the same whether
    the companion caused it or whether it's something private. One occurrence
    cannot tell them apart, so one occurrence may not be written down.

    This used to be enforced by telling the model to count repeats by eye across
    sixty turns, under a rule demanding «дважды или больше» — while those same
    events were being counted for it, one exchange at a time, in a table. Now the
    counting is the register's and only the meaning is the model's.
    """
    r = reading._REREAD_SYSTEM
    assert "СЧИТАТЬ ТЕБЕ НЕ НАДО" in r
    assert "ТОЛЬКО то, что стоит в этом списке" in r
    # The reason one occurrence cannot be trusted still has to be stated, or the
    # rule reads as bureaucracy and gets argued with.
    assert "РОВНО ТАК ЖЕ ВЫГЛЯДИТ ПРОСТО ЛИЧНОЕ" in r
    assert "НЕВОЗМОЖНО" in r
    # An empty list means leave it alone — not "look harder in the transcript".
    assert "Если список пуст" in r
    # And the cost of a false entry is named, because it is permanent.
    assert "навсегда отнимает у друга что-то живое" in r


def test_the_model_is_left_the_part_that_is_actually_thinking():
    """Counting is arithmetic and was taken away from it. Turning «закрылся на
    теме — война, 3 раза» into «про войну не расспрашивать» is not arithmetic,
    and that half is deliberately left where it was."""
    r = reading._REREAD_SYSTEM
    assert "ЧТО С ЭТИМ ДЕЛАТЬ — уже твоя работа" in r
    assert "это ещё не запись" in r


def test_the_evidence_for_hurt_is_handed_over_already_sorted(tmp_path, monkeypatch):
    """Which observations count as hurt must be a fact, not the model's
    judgement — otherwise we hand it a pile and call it evidence."""
    from app import db, mood

    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "t.db"))
    db.init_db()
    now = time.time()
    with db.connect() as conn:
        for i in range(14):
            conn.execute(
                "INSERT INTO mood_readings (user_id, ts, energy, warmth, lightness,"
                " clarity, engagement, word, note, because) VALUES (?,?,?,?,?,?,?,?,?,?)",
                ("u", now - (14 - i) * 7200, -1.0, -1.0, -1.0, 0.0, -1.0, "", "", ""),
            )
    for _ in range(3):
        mood.observe("u", "закрылся_на_теме", "война")
    for _ in range(4):
        mood.observe("u", "подняло_молчание", "")
    mood.observe("u", "ушёл_от_вопроса", "")          # once — not evidence

    said = mood.as_measured("u")
    hurt_part = said.split("Ещё случалось")[0]
    assert "доказательство для hurt_by" in hurt_part
    assert "война" in hurt_part
    assert "побыли рядом" not in hurt_part            # a lift, not a hurt
    assert "замолчал или свернул" not in said         # seen once, still withheld


def test_what_is_proven_to_hurt_is_stated_as_an_absolute():
    block = reading.standing_block({"hurt_by": "подтрунивать над его памятью"})
    assert "подтрунивать над его памятью" in block
    assert "ТОЧНО НЕ РАБОТАЕТ" in block
    # Changed silently. Announcing it would make him apologise for it.
    assert "не объявляй об этом" in block


def test_the_first_read_is_forbidden_to_invent_what_hurts_him():
    """`hurt_by` is the one field stated as an absolute in every turn, so an
    invented entry costs the companion something living, permanently. It can
    only ever come from a repeated pattern in real conversation — and the
    intake contains no conversations at all."""
    assert "hurt_by — ОСТАВЬ ПУСТЫМ" in reading._READING_SYSTEM
    assert "угадать, что человека заденет, нельзя" in reading._READING_SYSTEM
    # And it must not be confused with the field that IS guessable.
    assert "это would_ring_false, а это другое поле" in reading._READING_SYSTEM


def test_every_reading_field_reaches_both_places_it_is_needed(tmp_path):
    """A field the model fills in and nobody ever reads is worse than no
    field: it costs tokens on every write and silently does nothing. This
    walks the whole set rather than spot-checking, because the ones that go
    missing are always the ones added last."""
    every_turn = ("register", "would_ring_false", "do_not_touch", "closeness",
                  "what_lifts_him", "hurt_by", "learned")
    the_write = ("verdict", "register", "would_ring_false", "strong_at", "would_reach_them", "needs_pushback_on",
                 "closeness", "what_lifts_him", "hurt_by", "do_not_touch",
                 "common_ground_seeds")

    for field in every_turn:
        assert f"ЗНАЧ-{field}" in reading.standing_block({field: f"ЗНАЧ-{field}"}), field
    for field in the_write:
        assert f"ЗНАЧ-{field}" in reading.as_brief({field: f"ЗНАЧ-{field}"}), field


def test_nothing_is_asked_of_the_reader_that_nobody_reads():
    """The other direction of the test above, and the one that was missing.

    Four fields lived here for months that nothing downstream ever read —
    `surface` (a retelling of what he had just said), `beneath` and
    `evidence` (quotes), `confidence` — and they were most of what the owner
    saw when he tested it on himself: «они просто пересказали своими словами
    всё, что я сказал». Each of them was paid for on every reading and did
    nothing but make the reading longer than the person's own words, which
    is how a reading of 1,341 characters of answers came back at 8,000."""
    spec = reading._READING_SYSTEM.split("с ключами:", 1)[1]
    asked = re.findall(r"(?m)^([a-z_]+) — ", spec)
    assert len(asked) >= 10, asked
    for field in asked:
        probe = {field: f"ЗНАЧ-{field}"}
        read = reading.as_brief(probe) + reading.standing_block(probe)
        assert f"ЗНАЧ-{field}" in read, f"{field}: просим, но никто не читает"
    for dead in ("surface", "beneath", "evidence", "confidence"):
        assert dead not in asked


def test_one_thought_lives_in_one_field():
    """The second pass, after the first one was run on the owner's own
    answers. Shorter was not enough: one idea — «he wants an intellectual
    equal» — came back in four fields at once (verdict, longing,
    would_reach_them, closeness), because four fields asked for overlapping
    things and each had to be filled. Models give repeated content more
    weight, so the writer would have built the friend around one trait.

    So the four psychological fields that overlapped — carrying, longing,
    absent, self_image — went into verdict, and the rule is said outright.
    They were also the ones that invited guessing: on the same answers one
    model wrote «обиду на близких» and «чувство превосходства», neither of
    which he said."""
    spec = reading._READING_SYSTEM.split("с ключами:", 1)[1]
    asked = re.findall(r"(?m)^([a-z_]+) — ", spec)
    for merged in ("carrying", "longing", "absent", "self_image"):
        assert merged not in asked, merged
    assert asked[0] == "verdict"
    assert "Каждая мысль — в одном поле" in reading._READING_SYSTEM
    # What the merged fields carried now lives in verdict, by name.
    verdict = next(line for line in spec.splitlines() if line.startswith("verdict — "))
    assert "чего в ней нет" in verdict and "о чём он сам не попросил" in verdict


def test_the_friend_is_for_what_is_missing_not_for_more_of_the_same():
    """The owner, after reading five readings of himself: every one of them
    saw him with somebody to work on his project with — «which is true at
    some point, but hard projects are better alone» — and none of them saw
    what he had actually told the interviewer: that his whole mind is the
    project and AI, and what he is missing is somebody to talk to about fear,
    FOMO, love. «Fulfil what I miss, not what I already have.»

    The prompt had asked the wrong main question — «какое присутствие ему
    было бы не в тягость» — and the easiest presence to bear is more of what
    one already does, so every model mirrored him. Now the main question is
    what his life lacks, with the one distinction that says why a busy life
    is not a full one: Weiss (1973) — social loneliness (nobody around) and
    emotional loneliness (people around, nobody to say the real things to)
    have different remedies, and one does not cure the other."""
    rules = reading._READING_SYSTEM
    assert "ЧЕГО В ЕГО ЖИЗНИ НЕТ?" in rules
    assert "не для того, что у человека и так есть" in rules
    assert "Одиночество бывает двух видов, и одно другим не лечится" in rules
    assert "не с кем о главном — о страхе, о любви" in rules
    # Comfort is still asked — but after, not instead.
    assert rules.index("ЧЕГО В ЕГО ЖИЗНИ НЕТ?") < rules.index("не заставил бы его снова держать лицо")


def test_what_he_could_not_say_is_not_what_he_forbade():
    """Asked what he thinks about alone at night, he answered «не могу
    сказать, слишком много». All five readings filed it as a door to keep
    shut — «не выпытывай вечерние мысли», «его одиночество как тема» — and
    one concluded that talk about feelings would not lift him. It was the one
    thing he wanted to talk about. do_not_touch forbids the friend ever
    opening a subject; it must hold only what he showed hurts."""
    rules = reading._READING_SYSTEM
    assert "«не могу сказать» чаще значит «не с кем», а не «не трогай»" in rules
    # And what lifts him is not read off what he is busy with.
    assert "дело, в которое человек ушёл с головой, и то, что его поднимает, — разные вещи" in rules


def test_the_reading_is_written_for_the_models_that_read_it():
    """Nobody human reads it. A model writes a friend from it, and another
    holds part of it on every turn — and a model cannot skip what it was
    given, even when it can see that it is irrelevant. So: a conclusion
    rather than a retelling, a norm of one or two sentences with its break
    condition, no quotes (a model handed somebody's own phrases hands them
    back to him), and an empty field where the text shows nothing."""
    rules = reading._READING_SYSTEM
    assert "Пиши вывод, а не то, из чего он сделан. Не пересказывай его ответы." in rules
    assert "одно-два коротких предложения. Это норма, а не потолок" in rules
    assert "В ответ их не выписывай" in rules
    assert "Мало текста — мало чтения" in rules
    # The verdict comes first where the writer reads it.
    assert reading.as_brief({"verdict": "В", "register": "Р"}).index("Главное: В") < \
        reading.as_brief({"verdict": "В", "register": "Р"}).index("Р")
    # The re-read keeps the same discipline.
    assert "вывод, а не пересказ, и без его цитат" in reading._REREAD_SYSTEM


# --------------------------------------------------------------------------- #
# When the register has watched it, the reading stops guessing at it
# --------------------------------------------------------------------------- #
#
# «Чем его поднимать» is answered twice in the same prompt. The reading guesses
# it from a paragraph somebody wrote to a machine they had never met, on the day
# their son installed the app — and phrases it as an instruction: «не угадывай —
# вот это и делай». mood.standing_block carries the answer that was actually
# watched happening, twice or more, and phrases it mildly. Both present, the
# louder and weaker one wins, which is backwards.

_GUESSES = {"register": "коротко", "what_lifts_him": "истории, чтобы отвлечься"}


def test_the_guess_is_used_while_nothing_has_been_watched():
    """It is a guess, but at the start it is the only answer there is."""
    said = reading.standing_block(_GUESSES, lifts_confirmed=False)
    assert "истории, чтобы отвлечься" in said


def test_the_guess_is_dropped_once_it_has_been_watched():
    """Not argued with — removed. Two answers to one question is the problem."""
    said = reading.standing_block(_GUESSES, lifts_confirmed=True)
    assert "истории" not in said
    assert "Чем его поднимать" not in said


def test_nothing_else_about_him_is_dropped_with_it():
    said = reading.standing_block(
        {**_GUESSES, "do_not_touch": "про сына не спрашивать"}, lifts_confirmed=True
    )
    assert "коротко" in said
    assert "про сына не спрашивать" in said


def test_a_reading_with_nothing_else_in_it_goes_quiet_entirely():
    assert reading.standing_block({"what_lifts_him": "истории"}, lifts_confirmed=True) == ""


def test_it_is_watched_that_decides_not_guessed(tmp_path, monkeypatch):
    """The switch is the observation register, at its usual bar of twice."""
    from app import db, mood

    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "t.db"))
    db.init_db()

    assert mood.lifts_confirmed("u") is False
    mood.observe("u", "подняло_молчание", "")
    assert mood.lifts_confirmed("u") is False, "once is a coincidence, as everywhere"
    mood.observe("u", "подняло_молчание", "")
    assert mood.lifts_confirmed("u") is True


def test_a_confirmed_observation_about_something_else_does_not_count(tmp_path, monkeypatch):
    """«Он устал от расспросов» is confirmed knowledge, and it is not an answer
    to what lifts him — so it must not silence the only answer there is."""
    from app import db, mood

    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "t.db"))
    db.init_db()
    for _ in range(3):
        mood.observe("u", "устал_от_расспросов", "")
    assert mood.lifts_confirmed("u") is False


def test_one_persons_register_does_not_silence_anothers_reading(tmp_path, monkeypatch):
    from app import db, mood

    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "t.db"))
    db.init_db()
    for _ in range(2):
        mood.observe("анна", "поднял_юмор", "")
    assert mood.lifts_confirmed("анна") is True
    assert mood.lifts_confirmed("борис") is False


# --------------------------------------------------------------------------- #
# The re-reading is no longer blind to what was counted
# --------------------------------------------------------------------------- #
#
# It used to be handed the old document and a transcript and asked to work out
# from the transcript what lifts him — while «подняло_молчание · 4 раза» sat in
# a table nobody showed it. Two systems learning the same thing separately, and
# the one with arithmetic behind it was the one kept in the dark.


def _measured_person(user: str, tmp_path, monkeypatch):
    from app import db, mood

    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "t.db"))
    db.init_db()
    now = time.time()
    with db.connect() as conn:
        for i in range(14):
            v = -1.0 if i % 4 else 0.0
            conn.execute(
                "INSERT INTO mood_readings (user_id, ts, energy, warmth, lightness,"
                " clarity, engagement, word, note, because) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (user, now - (14 - i) * 7200, v, v, v, 0.0, v, "", "", ""),
            )
    for _ in range(4):
        mood.observe(user, "подняло_молчание", "")
    mood.observe(user, "поднял_юмор", "")          # once — deliberately not counted
    return mood


def test_the_reread_is_handed_what_was_counted(tmp_path, monkeypatch):
    _measured_person("u", tmp_path, monkeypatch)
    seen: dict[str, str] = {}

    async def fake_think(system, prompt, **kw):
        seen["prompt"] = prompt
        seen["system"] = system
        return '{"register": "сухо"}'

    monkeypatch.setattr(reading.brain, "think", fake_think)
    asyncio.run(reading.reread("u", {"register": "сухо"},
                               [{"role": "user", "content": "ну"}]))

    assert "УЖЕ ИЗМЕРЕНО" in seen["prompt"]
    assert "просто побыли рядом без бодрости" in seen["prompt"]
    assert "Обычно он:" in seen["prompt"]


def test_what_happened_only_once_is_still_withheld(tmp_path, monkeypatch):
    """Same bar as everywhere. A single occurrence is held and not acted on —
    including here, where acting on it would write it into who he is."""
    mood = _measured_person("u", tmp_path, monkeypatch)
    assert "шутк" not in mood.as_measured("u")
    assert "дурачество" not in mood.as_measured("u")


def test_nothing_is_claimed_before_there_is_enough_to_claim_it(tmp_path, monkeypatch):
    """A baseline off three readings is not a measurement, it is a rumour with
    a number on it."""
    from app import db, mood

    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "t.db"))
    db.init_db()
    mood.record("u", {"energy": -1, "warmth": -1, "note": "устал"})
    assert mood.as_measured("u") == ""


def test_one_persons_measurements_are_not_anothers(tmp_path, monkeypatch):
    mood = _measured_person("анна", tmp_path, monkeypatch)
    assert mood.as_measured("анна")
    assert mood.as_measured("борис") == ""


def test_the_reread_is_told_the_count_beats_its_impression():
    """It sees a few dozen turns; the register counted all of them. When the
    transcript and the arithmetic disagree, the arithmetic is right."""
    s = reading._REREAD_SYSTEM
    assert "ПОСЧИТАНО ЗА ТЕБЯ" in s
    assert "верь посчитанному" in s
    assert "what_lifts_him" in s
    # and it is told the count covers only a short list, not all of him
    assert "Всё остальное про него — по-прежнему твоя работа" in s


# --------------------------------------------------------------------------- #
# Copying the document forward is bookkeeping, and bookkeeping belongs in code
# --------------------------------------------------------------------------- #


def test_a_reread_that_changed_nothing_costs_nothing():
    """«Пустой объект {} — правильный ответ» has to actually work, or the
    instruction is a lie and the model will keep restating everything."""
    before = {"register": "сухо", "do_not_touch": "смерть жены"}
    after = asyncio.run(_reread_returning("{}", before))
    assert after["register"] == "сухо"
    assert after["do_not_touch"] == "смерть жены"


def test_what_was_learned_before_is_not_lost_when_only_new_is_sent():
    """The trap in asking for new-only. Replacing would erase everything
    understood before this revision, every thirty turns."""
    before = {"learned": ["не звать по отчеству"]}
    after = asyncio.run(_reread_returning('{"learned": ["не любит, когда его жалеют"]}', before))
    assert after["learned"] == ["не звать по отчеству", "не любит, когда его жалеют"]


def test_restating_something_already_known_does_not_duplicate_it():
    before = {"learned": ["не звать по отчеству"]}
    after = asyncio.run(_reread_returning('{"learned": ["не звать по отчеству"]}', before))
    assert after["learned"] == ["не звать по отчеству"]


def test_understanding_does_not_pile_up_forever():
    """It rides in the cached block on EVERY turn, and «что ты понял про него»
    only ever grows. The oldest fall off; the things that must never expire live
    in do_not_touch and hurt_by, which are not capped."""
    before = {"learned": [f"понял {i}" for i in range(reading.MAX_LEARNED + 5)]}
    after = asyncio.run(_reread_returning('{"learned": ["самое свежее"]}', before))
    assert len(after["learned"]) == reading.MAX_LEARNED
    assert after["learned"][-1] == "самое свежее"
    assert "понял 0" not in after["learned"]          # oldest dropped


def test_a_learned_written_as_one_sentence_still_works():
    """Readings written before it became a list, and models that answer with a
    sentence. Neither may end up rendered as «['...']» in somebody's prompt."""
    after = asyncio.run(_reread_returning('{"learned": "стал доверять"}',
                                          {"learned": "раньше был сух"}))
    assert after["learned"] == ["раньше был сух", "стал доверять"]
    assert "[" not in reading.standing_block(after)


def test_the_reread_is_told_to_send_only_what_changed():
    r = reading._REREAD_SYSTEM
    assert "ТОЛЬКО ТЕ ПОЛЯ, КОТОРЫЕ ТЫ МЕНЯЕШЬ" in r
    assert "останется как было, само" in r
    assert "только НОВОЕ" in r
    # and permanent prohibitions are steered to the fields that never expire
    assert '"do_not_touch" или "hurt_by"' in r


async def _reread_returning(payload: str, before: dict) -> dict:
    import app.reading as _r

    async def fake_think(system, prompt, **kw):
        return payload

    real, _r.brain.think = _r.brain.think, fake_think
    try:
        return await _r.reread("u", before, [{"role": "user", "content": "ну"}])
    finally:
        _r.brain.think = real


# --------------------------------------------------------------------------- #
# The two fields that may only ever grow
#
# A re-reading is a model rewriting the most consequential document in the app,
# unattended, every few visits. Everything else in it is an opinion and is meant
# to be revised. These two are the record of what actually wounded somebody, and
# of what they asked in their own words never to be put through again.
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("empty", ["[]", "null", '""', "{}", '[" "]'])
def test_nothing_to_add_here_cannot_erase_what_must_never_be_lost(empty):
    """THE BUG THIS SECTION EXISTS FOR, and it was live.

    The presence test was `str(value).strip()` — and str([]) is "[]", str(None)
    is "None", both truthy. A revision answering «"do_not_touch": []», which is
    exactly what a model sends when it means "nothing to add here", replaced
    «про сына не спрашивать, он умер» with an empty list. Silently, permanently,
    on the one field whose whole purpose is never to be lost. The friend would
    then walk straight into it, warmly, and the man would have to say it twice.
    """
    before = {"register": "сухо", "do_not_touch": "про сына не спрашивать, он умер",
              "hurt_by": "подтрунивать над его памятью"}
    after = asyncio.run(_reread_returning(
        '{"do_not_touch": %s, "hurt_by": %s, "register": %s}' % (empty, empty, empty),
        before,
    ))
    assert after["do_not_touch"] == "про сына не спрашивать, он умер"
    assert after["hurt_by"] == "подтрунивать над его памятью"
    # and the same slip on an ordinary field is just as much a slip
    assert after["register"] == "сухо"


def test_a_revision_may_add_to_the_sore_list_and_never_replace_it():
    """«Список больного может только расти» was a sentence in the prompt asking
    a model to restrain itself. It is a mechanism now: what the revision sends
    is added to what was there, and what was there does not move."""
    after = asyncio.run(_reread_returning(
        '{"do_not_touch": "про развод тоже не надо"}',
        {"do_not_touch": "смерть жены"},
    ))
    assert after["do_not_touch"] == ["смерть жены", "про развод тоже не надо"]


def test_a_revision_that_adds_nothing_leaves_the_sore_field_exactly_as_it_was():
    """A reading that has never had anything added keeps its plain string. A
    field that quietly turns into a one-item list on every re-read would show up
    as a change in the history and make a real change impossible to spot."""
    after = asyncio.run(_reread_returning('{"register": "теплее"}',
                                          {"register": "сухо", "do_not_touch": "смерть жены"}))
    assert after["do_not_touch"] == "смерть жены"


def test_a_grown_sore_list_never_reaches_the_prompt_as_brackets():
    grown = {"do_not_touch": ["смерть жены", "про развод тоже не надо"],
             "hurt_by": ["подтрунивать над его памятью"]}
    block = reading.standing_block(grown)
    assert "[" not in block and "'" not in block
    assert "смерть жены; про развод тоже не надо" in block


def test_a_first_reading_with_an_empty_required_field_is_not_a_reading():
    """Same slip, at the other end of the life of a reading: a register that
    came back as [] used to pass the bar, and then a whole companion was written
    on top of nothing."""
    with pytest.raises(reading.ReadingFailed):
        reading._extract_json('{"register": [], "would_reach_them": "спокойно"}',
                              require=reading._REQUIRED)


# --------------------------------------------------------------------------- #
# Sore is not forbidden — it is his to open
# --------------------------------------------------------------------------- #


def test_the_sore_subject_is_never_raised_by_him_and_never_refused_to_the_person():
    """The owner's rule, and the reason it is one sentence rather than two
    sections: a line that says only «это больное» gets obeyed completely,
    including in the case it was never written for — a man who has nobody to say
    his wife's name out loud to finally says it, and his friend changes the
    subject. That is the loneliest answer available, and it is what everybody
    else in his life already does."""
    block = reading.standing_block({"do_not_touch": "смерть жены"})
    # he never takes him there
    assert "не заговаривай об этом первым" in block
    # and he never refuses to go when he is taken there
    assert "если он" in block and "заговорил сам — иди за ним и говори" in block
    assert "не надо уводить" in block


def test_what_does_not_work_with_him_is_about_his_own_behaviour():
    """hurt_by is a list of things HE did that landed badly. Read as a list of
    banned topics it would gag the person about their own life."""
    block = reading.standing_block({"hurt_by": "подтрунивать над его памятью"})
    assert "про то, что делаешь ТЫ" in block
    assert "заговорит сам — говори с ним" in block


# --------------------------------------------------------------------------- #
# A revision can be undone
# --------------------------------------------------------------------------- #


def test_a_revision_records_what_the_field_used_to_say(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "READING_PATH", tmp_path / "reading.json")
    reading.save(U, {"register": "сухо"})
    reading.save(U, {"register": "теплее, чем казалось"})
    past = reading.history(U)
    assert len(past) == 1
    assert past[0]["was"] == {"register": "сухо"}


def test_a_field_the_model_invented_can_be_taken_back(tmp_path, monkeypatch):
    """The case this exists for, and the one the first version missed: an
    invented field has no previous value, so it appears nowhere in `was`. An
    invented hurt_by would have his friend avoid his children forever."""
    monkeypatch.setattr(config, "READING_PATH", tmp_path / "reading.json")
    reading.save(U, {"register": "сухо"})
    reading.save(U, {"register": "сухо", "hurt_by": "не спрашивать про детей"})

    entry = reading.history(U)[-1]
    assert entry["added"] == ["hurt_by"]

    undone = {**reading.load(U), **entry["was"]}
    for key in entry["added"]:
        undone.pop(key, None)
    assert "hurt_by" not in undone
    assert undone["register"] == "сухо"


def test_saving_the_same_reading_again_records_nothing(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "READING_PATH", tmp_path / "reading.json")
    reading.save(U, {"register": "сухо"})
    reading.save(U, {"register": "сухо"})
    assert reading.history(U) == []


def test_the_first_reading_has_nothing_behind_it(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "READING_PATH", tmp_path / "reading.json")
    reading.save(U, {"register": "сухо"})
    assert reading.history(U) == []


def test_only_the_last_few_revisions_are_kept(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "READING_PATH", tmp_path / "reading.json")
    for i in range(reading.KEEP_REVISIONS + 4):
        reading.save(U, {"register": f"ревизия {i}"})
    past = reading.history(U)
    assert len(past) == reading.KEEP_REVISIONS
    assert past[-1]["was"]["register"] == f"ревизия {reading.KEEP_REVISIONS + 2}"


def test_a_broken_history_file_never_costs_a_reading(tmp_path, monkeypatch):
    """A log must not be able to stop a friendship learning something."""
    monkeypatch.setattr(config, "READING_PATH", tmp_path / "reading.json")
    reading.save(U, {"register": "сухо"})
    reading.history_path(U).write_text("не json", encoding="utf-8")
    reading.save(U, {"register": "теплее"})
    assert reading.load(U)["register"] == "теплее"
    assert reading.history(U) == [] or reading.history(U)[-1]["was"]["register"] == "сухо"


def test_the_day_one_guess_at_closeness_is_dropped_once_it_has_been_watched():
    """The same discipline as what_lifts_him, applied to the field that waited
    longest for it. Both guesses are phrased as instructions and were made from
    one paragraph written to a machine the person had never met; the watched
    answer is phrased mildly. With both in the prompt the louder and weaker one
    wins, which is backwards — so the guess is removed rather than argued with."""
    r = {
        "register": "коротко и просто",
        "closeness": "надо прямо говорить, что ждал",
        "what_lifts_him": "истории",
    }
    guessed = reading.standing_block(r)
    assert "Как он хочет быть нужным" in guessed

    watched = reading.standing_block(r, closeness_confirmed=True)
    assert "Как он хочет быть нужным" not in watched
    assert "надо прямо говорить, что ждал" not in watched
    # and the two drops are independent of each other
    assert "Чем его поднимать" in watched
    assert "коротко и просто" in watched


# ── the permanent document is rewritten in visits, not in rows ──────────────

def test_re_reading_is_counted_in_visits_and_not_in_turn_rows():
    """`REREAD_EVERY` counted rows in `turns`, and a turn is logged twice per
    exchange. «Roughly a few conversations» was, at twenty-five exchanges a
    conversation, TWICE A DAY — six hundred rewritings a year of the permanent
    document, with KEEP_REVISIONS covering under five days of that year."""
    assert not hasattr(reading, "REREAD_EVERY")
    # Dense while he is a stranger, rare once he is known: at visit two the
    # thing being replaced is a paragraph written to a machine on install day,
    # and at visit forty it is weeks of how he really talks.
    assert reading.every_at(1) == 1 and reading.every_at(3) == 1
    assert reading.every_at(10) == 3
    assert reading.every_at(40) == 10
    assert reading.every_at(5) < reading.every_at(20), "должно РЕДЕТЬ, а не густеть"
    # The sparse end still has to satisfy the constraint the flat number had:
    # eight saved versions covering more than a token slice of a year.
    assert reading.KEEP_REVISIONS * reading.every_at(40) >= 30


def test_visits_are_counted_the_same_for_a_talker_and_a_quiet_man(tmp_path, monkeypatch):
    """The property turns did not have. Five visits is five visits whether
    somebody talks for an hour or for five minutes — «sixty turns» is a
    fortnight for one of them and an afternoon for the other."""
    from app import config, memory

    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "t.db"))
    db.init_db()

    now = time.time()
    with db.connect() as conn:
        for who, per_visit in (("говорун", 25), ("молчун", 3)):
            for visit in range(10):
                for i in range(per_visit):
                    conn.execute(
                        "INSERT INTO turns(user_id,role,content,ts,farewell)"
                        " VALUES (?,?,?,?,0)",
                        (who, "user", "x", now - (10 - visit) * 86400 + i * 40),
                    )
    assert memory.visits_so_far("говорун") == 10
    assert memory.visits_so_far("молчун") == 10


def test_a_pause_inside_one_conversation_is_not_a_second_visit(tmp_path, monkeypatch):
    """Answering the door must not count as leaving and coming back."""
    from app import config, memory

    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "t.db"))
    db.init_db()

    now = time.time()
    with db.connect() as conn:
        for offset in (0, 60, 120, 400, 460):          # all inside ten minutes
            conn.execute(
                "INSERT INTO turns(user_id,role,content,ts,farewell) VALUES (?,?,?,?,0)",
                ("u", "user", "x", now - 3600 + offset),
            )
    assert memory.visits_so_far("u") == 1


# ── the schedule is a ceiling, not the decision ────────────────────────────

def test_a_person_who_has_changed_is_read_before_the_clock_says_so(tmp_path, monkeypatch):
    """The whole job of this app is noticing when somebody is not who they
    were. A fixed schedule cannot do that: a man who has been steady for six
    months and changes in a week would wait out ten visits holding a
    description of the person he used to be.

    So the visits are a ceiling and the evidence is the trigger. Three
    behaviours CONFIRMED since the last reading — six sightings, because
    mood.CONFIRMED_AT is what separates «happened once» from «is true of him»
    — and he is read again now rather than on schedule."""
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "t.db"))
    db.init_db()
    user = "changed"
    for i in range(reading.REREAD_MIN_TURNS):
        memory.log_turn(user, "user" if i % 2 == 0 else "assistant", f"слово {i}")

    reading.save(user, {
        "register": "просто",
        "_read_at_visit": memory.visits_so_far(user),
        "_confirmed_at_read": mood.confirmed_count(user),
    })

    called = False

    async def fake_reread(*a, **kw):
        nonlocal called
        called = True
        return {"register": "просто"}

    monkeypatch.setattr(reading, "reread", fake_reread)

    # Nothing has changed and the clock has not come round: nothing happens.
    asyncio.run(reading.keep_reading(user))
    assert not called, "прочитал, хотя ни расписание, ни перемена не сработали"

    # …and now three behaviours, each watched twice. He is not who it says.
    for tag in list(mood.TAGS)[: reading.NOTICED_CONFIRMATIONS]:
        mood.observe(user, tag)
        mood.observe(user, tag)
    assert mood.confirmed_count(user) >= reading.NOTICED_CONFIRMATIONS

    asyncio.run(reading.keep_reading(user))
    assert called, "перемену подтвердили, а он всё ещё ждёт расписания"


def test_one_confirmed_thing_is_not_a_changed_person(tmp_path, monkeypatch):
    """The other half. A trigger that fires on the first confirmation would be
    a re-reading every other visit, which is the churn the graduated schedule
    exists to stop — on a document that is REPLACED, not added to."""
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "t.db"))
    db.init_db()
    user = "steady"
    for i in range(reading.REREAD_MIN_TURNS):
        memory.log_turn(user, "user" if i % 2 == 0 else "assistant", f"слово {i}")
    reading.save(user, {
        "register": "просто",
        "_read_at_visit": memory.visits_so_far(user),
        "_confirmed_at_read": 0,
    })

    called = False

    async def fake_reread(*a, **kw):
        nonlocal called
        called = True
        return {"register": "просто"}

    monkeypatch.setattr(reading, "reread", fake_reread)
    tag = list(mood.TAGS)[0]
    mood.observe(user, tag)
    mood.observe(user, tag)
    assert mood.confirmed_count(user) == 1

    asyncio.run(reading.keep_reading(user))
    assert not called, "одного подтверждения хватило — это уже не перемена, а шум"


def test_the_reader_is_told_how_not_to_be_wrong():
    """Accuracy about a person needs four things in a row — the cues have to
    exist, reach the judge, be noticed and be used right (Funder's Realistic
    Accuracy Model) — and the last one is where a model fails on its own. So
    the reading is walked through the techniques that measurably help:
    perspective-taking first (SimToM, Wilf et al. 2023, beats plain
    chain-of-thought on theory-of-mind tasks); direct words over form, because
    the owner's own «po seryoznomu delu?? ai» was the strongest sentence he
    wrote; more than one hypothesis and a look for what contradicts the
    winner, which measurably cuts confirmation bias in LLMs; and the Barnum
    check, because a sentence true of most lonely people says nothing about
    this one. All of it in the thinking — none of it costs the output."""
    rules = reading._READING_SYSTEM
    assert "КАК НЕ ОШИБИТЬСЯ (это в размышлениях, до ответа)" in rules
    assert "Побудь им" in rules
    assert "Прямые слова весомее формы" in rules
    assert "Первая, что приходит в голову, обычно про то, чем он занят, — а это зеркало" in rules
    assert "поищи, что ей противоречит" in rules
    assert "подошёл бы почти любому одинокому человеку" in rules
    # And it comes before the main question, so the question is asked of a
    # reading that has already been checked.
    assert rules.index("КАК НЕ ОШИБИТЬСЯ") < rules.index("ГЛАВНЫЙ ВОПРОС")


def test_the_reread_revisits_what_is_missing_first():
    """The first reading is a hypothesis made from a dozen answers to a
    stranger. The conversations are the evidence — and the owner's case is the
    reason this field comes first: what he lacked was visible in how he would
    talk, not in the questionnaire."""
    assert "ЧЕГО ЕМУ НЕ ХВАТАЕТ (поле verdict)" in reading._REREAD_SYSTEM
    assert "это важнее любого другого поля" in reading._REREAD_SYSTEM


def test_the_interview_asks_the_one_question_that_answers_it():
    """No reader can read what was never said. The owner's closing question
    was «о чём думаешь вечером» — «не могу сказать, слишком много» — and so
    the one thing he most wanted, to talk about feelings, never reached the
    page. The closing question is now the one whose answer says what is
    missing: whom there is nobody to talk to about what."""
    from app import intake

    ask = intake._ASK_SYSTEM
    assert "«А о чём бы поговорить, да не с кем?» — чего ему не хватает" in ask
    # The two alternatives that were there are gone: «когда не спится» is
    # exactly what got «слишком много», and «кому позвонил бы в три ночи»
    # makes the most isolated say «никому» and asks about a crisis he can't be.
    assert "когда не спится" not in ask and "в три ночи" not in ask
