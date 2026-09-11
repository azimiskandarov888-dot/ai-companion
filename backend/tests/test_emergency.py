"""Which number he is told to dial.

103 is the ambulance where the first users are. Telling a man in Chicago to dial
it while he is on the floor is not a smaller failure than missing the alarm —
it is the same failure with extra steps. Nobody fills in a settings form, so the
country arrives the way everything else about him arrives: he mentions where he
lives, and it is written down.
"""

from __future__ import annotations

import pytest

from app import config, emergency, learn, safety

U = "u"


# ── learning it from the conversation ───────────────────────────────────────

def test_nothing_is_known_until_he_says_so():
    assert emergency.country(U) == ""
    assert emergency.known(U) is False


@pytest.mark.asyncio
async def test_saying_where_he_lives_is_enough():
    await learn._store(U, {"country": "Израиль"})
    assert emergency.known(U)
    assert "101" in emergency.numbers(U)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "said,expected",
    [
        ("Россия", "103"),
        ("россия", "103"),
        ("  Казахстан  ", "103"),
        ("США", "911"),
        ("Канада", "911"),
        ("Германия", "112"),
        ("Великобритания", "999"),
        ("Австралия", "000"),
    ],
)
async def test_the_number_follows_the_country(said, expected):
    await learn._store(U, {"country": said})
    assert expected in emergency.numbers(U)


@pytest.mark.asyncio
async def test_moving_house_moves_the_number():
    await learn._store(U, {"country": "Россия"})
    assert "103" in emergency.numbers(U)
    await learn._store(U, {"country": "Канада"})
    assert "911" in emergency.numbers(U)
    assert "103" not in emergency.numbers(U)


@pytest.mark.asyncio
async def test_a_country_nobody_listed_is_not_recorded_as_known():
    """Unrecognised has to stay unknown. Storing it would make known() true
    while numbers() still fell back, which reads as «we know where he is» to
    whoever is later trying to work out why he got the wrong number."""
    await learn._store(U, {"country": "Нарния"})
    assert emergency.known(U) is False
    assert emergency.country(U) == ""


@pytest.mark.asyncio
async def test_an_exchange_that_says_nothing_about_place_changes_nothing():
    await learn._store(U, {"country": "Россия"})
    await learn._store(U, {"facts": [{"category": "семья", "value": "внучка Оля"}]})
    assert emergency.country(U) == "россия"


@pytest.mark.asyncio
async def test_nonsense_is_not_fatal():
    for junk in ({"country": ""}, {"country": "   "}, {"country": 42}, {}):
        await learn._store(U, junk)
    assert emergency.known(U) is False


# ── what actually gets said ─────────────────────────────────────────────────

def test_the_universal_number_is_always_there_too():
    """A man in a panic may misremember which number he was told. 112 routes to
    local emergency services nearly everywhere, including from a phone with no
    SIM — so it is never the only thing said, and never left out."""
    emergency.remember(U, "США")
    said = emergency.numbers(U)
    assert "911" in said and "112" in said


def test_a_country_where_112_is_already_the_number_does_not_say_it_twice():
    emergency.remember(U, "Германия")
    assert emergency.numbers(U) == "112"


def test_an_unknown_country_still_gets_a_usable_answer():
    assert config.EMERGENCY_NUMBER in emergency.numbers(U)
    assert emergency.UNIVERSAL in emergency.numbers(U)


# ── the wire into the alarm ─────────────────────────────────────────────────

def test_the_alarm_uses_his_number_not_the_default():
    emergency.remember(U, "Канада")
    said = safety.block({"level": "danger", "what": "упал"}, U)
    assert "911" in said
    assert "103" not in said


def test_the_alarm_without_a_user_still_names_numbers():
    """The signature keeps user_id optional, and a caller without one must not
    produce an alarm with no number in it — worse than knowing, far better than
    nothing."""
    said = safety.block({"level": "danger", "what": "упал"})
    assert config.EMERGENCY_NUMBER in said
    assert emergency.UNIVERSAL in said


def test_one_persons_country_is_not_anothers():
    emergency.remember("анна", "США")
    emergency.remember("борис", "Россия")
    assert "911" in emergency.numbers("анна")
    assert "103" in emergency.numbers("борис")


def test_the_extractor_is_told_to_only_report_what_he_said():
    """A guessed country is worse than none: it would be stored as known and
    silently decide what he is told to dial."""
    assert "ТОЛЬКО если он сам об этом сказал" in learn._EXTRACTION_SYSTEM
