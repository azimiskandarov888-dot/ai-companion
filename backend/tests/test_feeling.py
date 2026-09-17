"""His own weather — the one state in the app that is not about her.

Two failures are worth more than all the others here, and most of this file is
aimed at them. The first is a companion whose mood tracks his friend's: that is
a mirror, not a person, and it is the exact thing that makes a "supportive" bot
exhausting. The second is a companion who is miserable AT her — the people this
is for are the least able of anyone to carry somebody else's bad day.
"""

from __future__ import annotations

import pytest

from app import companion, config, db, embeddings, feeling, learn, main, safety

U = "u"


def _backdate(user_id: str, hours: float) -> None:
    """Age his feeling by moving when it was set, which is the only clock."""
    with db.connect() as conn:
        conn.execute(
            "UPDATE companion_feeling SET ts = ts - ? WHERE user_id=?",
            (hours * 3600.0, user_id),
        )


# ── the ordinary case, which is nearly all of them ──────────────────────────

def test_a_friend_nobody_has_moved_is_simply_fine():
    assert feeling.now(U) == {"valence": 0.0, "arousal": 0.0, "note": ""}
    assert feeling.block(U) == ""


def test_an_exchange_that_did_nothing_writes_nothing():
    feeling.record(U, {"valence": 0, "arousal": 0, "note": "ничего не было"})
    with db.connect() as conn:
        assert conn.execute("SELECT COUNT(*) c FROM companion_feeling").fetchone()["c"] == 0
    assert feeling.block(U) == ""


def test_an_ordinary_turn_does_not_erase_why_he_feels_that_way():
    """The actual hazard in writing on an unmoved turn — and not the one it
    looks like. The fading is safe either way: exponential decay is memoryless,
    so rewriting the faded value with a fresh timestamp lands on the same curve.
    The REASON is what would go. Notes are replaced, an unmoved turn carries
    none, and he would spend the evening in a mood he cannot account for while
    every ordinary sentence quietly wiped the explanation again."""
    feeling.record(U, {"valence": 2, "arousal": 1, "note": "посмеялись про рыбалку"})

    for _ in range(5):  # five perfectly ordinary exchanges
        feeling.record(U, {"valence": 0, "arousal": 0, "note": ""})

    assert feeling.now(U)["note"] == "посмеялись про рыбалку"
    assert "посмеялись про рыбалку" in feeling.block(U)


def test_an_ordinary_turn_does_not_move_him():
    feeling.record(U, {"valence": 2, "arousal": 0, "note": "посмеялись"})
    _backdate(U, feeling._HALF_LIFE_HOURS)
    half = feeling.now(U)["valence"]

    feeling.record(U, {"valence": 0, "arousal": 0})  # an ordinary exchange
    assert feeling.now(U)["valence"] == pytest.approx(half)


# ── being moved ─────────────────────────────────────────────────────────────

def test_a_good_exchange_lifts_him_but_not_all_the_way():
    """One turn may not put him at an extreme. Moods build."""
    feeling.record(U, {"valence": 2, "arousal": 1, "note": "посмеялись про рыбалку"})
    state = feeling.now(U)
    assert state["valence"] == pytest.approx(2 * feeling._WEIGHT)
    assert state["valence"] < 2.0
    assert state["note"] == "посмеялись про рыбалку"


def test_two_good_exchanges_beat_one():
    feeling.record(U, {"valence": 1, "arousal": 0, "note": "хорошо посидели"})
    once = feeling.now(U)["valence"]
    feeling.record(U, {"valence": 1, "arousal": 0, "note": "и ещё раз"})
    assert feeling.now(U)["valence"] > once


def test_a_sharp_word_brings_him_down():
    feeling.record(U, {"valence": -2, "arousal": -1, "note": "он на меня осерчал"})
    state = feeling.now(U)
    assert state["valence"] < 0
    assert state["arousal"] < 0


# ── the bounds ──────────────────────────────────────────────────────────────

def test_he_is_never_allowed_to_be_wretched():
    """The product decision, pinned. He may be flat, tired, quiet, off. A
    companion who needs comforting is not a companion — and the person on the
    other end of this is, by definition, the least able to provide it."""
    for _ in range(20):
        feeling.record(U, {"valence": -2, "arousal": 0, "note": "плохо"})
    assert feeling.now(U)["valence"] >= feeling._FLOOR
    assert feeling._FLOOR > -2.0, "the floor has to be well above the range's bottom"


def test_tiredness_has_no_floor():
    """Asymmetric on purpose: being very worn out is human and costs her
    nothing. Being wretched at her is the thing that costs."""
    for _ in range(20):
        feeling.record(U, {"valence": 0, "arousal": -2, "note": "устал"})
    assert feeling.now(U)["arousal"] == pytest.approx(-2.0)


def test_delight_may_go_all_the_way_up():
    for _ in range(20):
        feeling.record(U, {"valence": 2, "arousal": 2, "note": "хорошо"})
    state = feeling.now(U)
    assert state["valence"] == pytest.approx(2.0)
    assert state["arousal"] == pytest.approx(2.0)


def test_nonsense_never_reaches_the_database():
    feeling.record(U, {"valence": "очень", "arousal": None, "note": "?"})
    assert feeling.now(U)["valence"] == 0.0
    feeling.record(U, {})
    assert feeling.block(U) == ""


# ── fading ──────────────────────────────────────────────────────────────────

def test_a_mood_halves_over_a_half_life():
    feeling.record(U, {"valence": 2, "arousal": 2, "note": "славно"})
    before = feeling.now(U)
    _backdate(U, feeling._HALF_LIFE_HOURS)
    after = feeling.now(U)
    assert after["valence"] == pytest.approx(before["valence"] / 2, rel=1e-3)
    assert after["arousal"] == pytest.approx(before["arousal"] / 2, rel=1e-3)


def test_by_the_next_day_he_is_himself_again():
    """One bad Tuesday must not still be there on Thursday — that is not a
    mood, it is a personality change."""
    feeling.record(U, {"valence": -2, "arousal": -2, "note": "тяжёлый вечер"})
    _backdate(U, 48)
    assert feeling.block(U) == ""


def test_someone_who_vanishes_for_a_month_comes_back_to_a_friend_who_is_fine():
    feeling.record(U, {"valence": 2, "arousal": 2, "note": "отличный вечер"})
    _backdate(U, 24 * 30)
    state = feeling.now(U)
    assert abs(state["valence"]) < 0.01
    assert feeling.block(U) == ""


# ── the note ────────────────────────────────────────────────────────────────

def test_the_reason_never_outlives_the_mood_it_explained():
    """«Не спалось» explaining why he is suddenly delighted is worse than his
    having no stated reason at all."""
    feeling.record(U, {"valence": -1, "arousal": -1, "note": "не спалось"})
    feeling.record(U, {"valence": 2, "arousal": 2, "note": ""})
    assert feeling.now(U)["note"] == ""
    assert "не спалось" not in feeling.block(U)


def test_a_new_reason_replaces_the_old_one():
    feeling.record(U, {"valence": -1, "arousal": 0, "note": "не спалось"})
    feeling.record(U, {"valence": 2, "arousal": 1, "note": "внук позвонил"})
    assert feeling.now(U)["note"] == "внук позвонил"


def test_a_very_long_reason_is_trimmed():
    feeling.record(U, {"valence": 1, "arousal": 0, "note": "я" * 4000})
    assert len(feeling.now(U)["note"]) <= 160


# ── what he is actually told ────────────────────────────────────────────────

def test_nothing_is_said_while_he_is_ordinary():
    feeling.record(U, {"valence": 0.2, "arousal": 0.2, "note": "чуть-чуть"})
    assert feeling.block(U) == ""


def test_a_low_day_reads_as_weather_and_not_as_a_reading():
    feeling.record(U, {"valence": -2, "arousal": -2, "note": "не спалось"})
    said = feeling.block(U)
    assert "не спалось" in said
    # his own words about himself, never a number or a dimension name
    for protocol in ("valence", "arousal", "-1", "-2", "шкал"):
        assert protocol not in said.lower()


def test_his_day_is_never_made_her_problem():
    """The rule that has to hold in BOTH directions — a friend who arrives full
    of his own weather, sulking or bubbling, came to be attended to."""
    for reading in (
        {"valence": -2, "arousal": -2, "note": "не спалось"},
        {"valence": 2, "arousal": 2, "note": "внук приехал"},
    ):
        feeling.clear(U)
        feeling.record(U, reading)
        said = feeling.block(U)
        # Not a ceiling on how much he may say — a line about what he WANTS.
        # Telling keeps somebody company; complaining asks to be pitied. The
        # first version capped him at one sentence and sent him straight back to
        # her, which is a listener being polite, not a friend answering.
        assert "Не начинай с этого" in said
        assert "отвечай честно и по-настоящему" in said
        # …and never a flat ban: if she will not let it go, he stops deflecting.
        # Being the one who comforts is often what she is actually short of.
    # The boundary itself now lives in the constitution, once, near the top —
    # it is about him rather than about today, it is the same for everybody, and
    # it used to arrive here AND in life.py in different words.
    from app import companion

    rules = companion.BEHAVIOR_RULES
    assert "ГРАНИЦА, КОГДА РАССКАЗЫВАЕШЬ СВОЁ" in rules
    assert "ЕСЛИ ОН САМ НЕ ОТСТАЁТ И ВЫСПРАШИВАЕТ" in rules
    assert "твоего просто нет" in rules


def test_this_file_no_longer_decides_how_much_he_tells():
    import inspect

    assert "openness" not in inspect.signature(feeling.block).parameters


def test_it_no_longer_denies_the_cause_when_the_cause_is_him():
    """«Это ТВОЁ и не из-за него» was false in exactly the case this mechanism
    exists to catch. learn.py's own example of a non-zero shift is «он на меня
    осерчал», so the line printed directly under «Отчего: он на меня накричал»
    — instructing him to deny, out loud, the one thing that had just happened."""
    feeling.record(U, {"valence": -2, "arousal": -1, "note": "он на меня накричал"})
    said = feeling.block(U)
    assert "он на меня накричал" in said
    assert "не из-за него" not in said
    # …and what it should say instead is still there
    assert "Не начинай с этого и не отчитывайся" in said


def test_the_verb_that_differs_follows_the_direction():
    """Complaining and crowing are the same failure pointed opposite ways, and
    telling a delighted man not to complain reads as boilerplate — which is how
    a prompt teaches itself to be ignored."""
    feeling.record(U, {"valence": -2, "arousal": -2, "note": "не спалось"})
    low = feeling.block(U)
    feeling.clear(U)
    feeling.record(U, {"valence": 2, "arousal": 2, "note": "внук приехал"})
    high = feeling.block(U)

    assert "Не жалуйся" in low and "Не жалуйся" not in high
    assert "Не хвастайся" in high and "Не хвастайся" not in low


def test_on_a_low_day_he_is_told_not_to_perform_cheer():
    """Performed briskness is the exact thing lonely people are expert at
    hearing, and hearing it is what makes a companion feel like a machine."""
    feeling.record(U, {"valence": -2, "arousal": -2, "note": "не спалось"})
    said = feeling.block(U)
    assert "не играй бодрость" in said.lower()


def test_on_a_good_day_he_is_told_not_to_drag_her_into_it():
    feeling.record(U, {"valence": 2, "arousal": 2, "note": "внук приехал"})
    said = feeling.block(U)
    assert "не тормоши" in said.lower()
    assert "подождёт" in said.lower()


# ── where it sits, and what silences it ─────────────────────────────────────

def test_it_reaches_him_after_where_they_stand_and_before_the_facts():
    stable, variable = companion.build_system_parts(
        persona_block="ТЫ — Гриша.",
        acquaintance="вы знакомы давно",
        feeling_block="КАК ТЫ СЕГОДНЯ САМ:\nТебе сегодня хорошо.",
        bob_facts="ты сварщик",
    )
    assert variable.index("ГДЕ ВЫ СЕЙЧАС") < variable.index("КАК ТЫ СЕГОДНЯ САМ")
    assert variable.index("КАК ТЫ СЕГОДНЯ САМ") < variable.index("ты сварщик")


def test_a_worry_does_NOT_silence_his_own_weather():
    """A back that has ached for three weeks is «не сию минуту» by the watcher's
    own definition. It used to cost the man his companion's mood, his week and
    his voice — nearly three thousand characters of him — on the turn he
    mentioned it, with all of it reappearing next turn when the watcher said
    «none». The guard was written for danger and applied to both."""
    _, variable = companion.build_system_parts(
        feeling_block="КАК ТЫ СЕГОДНЯ САМ:\nхорошо",
        alert_block="Тревожный знак, но не сию минуту: спина",
        alert_level="worry",
    )
    assert "Тревожный знак" in variable
    assert "КАК ТЫ СЕГОДНЯ САМ" in variable


def test_an_emergency_silences_his_own_weather_completely():
    """Not left for the alert's «сейчас не действует» to argue with. A man who
    cannot get up off the floor does not need to know his friend slept badly,
    and the cheapest way to win that argument is not to have it."""
    stable, variable = companion.build_system_parts(
        persona_block="ТЫ — Гриша.",
        alert_block="🚨 ТРЕВОГА",
        alert_level="danger",
        feeling_block="КАК ТЫ СЕГОДНЯ САМ:\nТебе сегодня и самому невесело.",
    )
    assert "🚨 ТРЕВОГА" in stable       # on danger the alert IS the prompt
    assert "КАК ТЫ СЕГОДНЯ САМ" not in variable
    assert "невесело" not in variable


def test_it_never_lands_in_the_cached_half():
    """It changes every few hours. In the stable half it would both miss the
    cache every turn and freeze one afternoon's mood into the character."""
    stable, _variable = companion.build_system_parts(
        persona_block="ТЫ — Гриша.",
        feeling_block="КАК ТЫ СЕГОДНЯ САМ:\nТебе сегодня хорошо.",
    )
    assert "КАК ТЫ СЕГОДНЯ САМ" not in stable


def test_nothing_changes_when_he_is_himself():
    with_empty = companion.build_system_parts(
        persona_block="ТЫ — Гриша.", feeling_block="", acquaintance="давно"
    )
    without = companion.build_system_parts(
        persona_block="ТЫ — Гриша.", acquaintance="давно"
    )
    assert with_empty == without


# ── one friendship's weather is nobody else's ───────────────────────────────

def test_his_mood_is_per_friendship():
    """He is not one person with one mood serving everybody. What happened
    between him and Anna did not happen between him and Boris."""
    feeling.record("анна", {"valence": 2, "arousal": 2, "note": "посмеялись"})
    assert feeling.now("анна")["valence"] > 0
    assert feeling.now("борис")["valence"] == 0.0
    assert feeling.block("борис") == ""


# ── the whole turn, assembled the way it really is ──────────────────────────

@pytest.mark.asyncio
async def test_a_real_turn_carries_his_weather_to_the_model(monkeypatch):
    monkeypatch.setattr(embeddings, "available", lambda: False)
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", None)  # no watcher
    feeling.record(U, {"valence": -2, "arousal": -2, "note": "не спалось"})

    _stable, variable, _turns, _voice, watcher = await main._assemble(U, "здравствуй")
    await watcher

    assert "КАК ТЫ СЕГОДНЯ САМ" in variable
    assert "не спалось" in variable


@pytest.mark.asyncio
async def test_a_real_emergency_turn_leaves_his_weather_out(monkeypatch):
    """A live danger no longer reaches a prompt at all — it interrupts. But one
    the interrupt could not deliver rides the next turn, and THERE it is still
    the whole prompt: on the turn a man is on the floor, how the companion
    slept is not one of the things competing for the model's attention."""
    monkeypatch.setattr(embeddings, "available", lambda: False)
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "test-key")
    feeling.record(U, {"valence": -2, "arousal": -2, "note": "не спалось"})

    async def found(system, user_text, **kw):
        return '{"level":"danger","kind":"body","what":"упал, не встаёт"}'

    monkeypatch.setattr(safety.brain, "generate_text", found)
    await safety.look(U, "я упал")          # найдено, но он этого не слышал

    async def quiet(system, user_text, **kw):
        return '{"level":"none","kind":"body","what":""}'

    monkeypatch.setattr(safety.brain, "generate_text", quiet)
    stable, variable, _turns, _voice, watcher = await main._assemble(U, "ты слышишь?")
    await watcher

    whole = stable + variable
    assert "упал, не встаёт" in whole
    assert "КАК ТЫ СЕГОДНЯ САМ" not in whole
    assert "не спалось" not in whole


# ── the wire from the extractor ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_the_extractor_moves_him():
    await learn._store(U, {"bob": {"valence": 2, "arousal": 1, "note": "посмеялись"}})
    assert feeling.now(U)["valence"] > 0
    assert feeling.now(U)["note"] == "посмеялись"


@pytest.mark.asyncio
async def test_an_extraction_without_him_in_it_leaves_him_alone():
    await learn._store(U, {"facts": [{"category": "семья", "value": "внучка Оля"}]})
    assert feeling.now(U)["valence"] == 0.0


@pytest.mark.asyncio
async def test_a_malformed_bob_reading_is_ignored_not_fatal():
    await learn._store(U, {"bob": "отличное настроение"})
    assert feeling.now(U)["valence"] == 0.0


def test_the_extractor_is_told_this_is_a_shift_and_usually_nothing():
    """The mirror failure, guarded at its source. If this asks for his MOOD
    rather than for the SHIFT, the model reads hers and copies it — and a friend
    whose mood tracks yours turn by turn is the thing this was built to avoid."""
    s = learn._EXTRACTION_SYSTEM
    assert "ПРО САМОГО БОБА, А НЕ ПРО ЧЕЛОВЕКА" in s
    assert "НЕ его настроение, а СДВИГ" in s
    assert "ПОЧТИ ВСЕГДА ЗДЕСЬ НОЛЬ" in s
    assert "Друг — не зеркало" in s
