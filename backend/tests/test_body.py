"""His throat, and why a cough is not a sound effect.

One rule is being tested from every angle here:

    a non-verbal must have a CAUSE that existed before it
    and a CONSEQUENCE that outlasts it.

Miss the cause and it is random. Miss the consequence and it is decoration —
and decoration is what takes a synthetic voice into the uncanny valley rather
than toward warmth. The half nobody builds is the second one: a real cough is
the end of twenty minutes of talking AND the start of two minutes of a voice
that has not quite come back.
"""

from __future__ import annotations

import time

import pytest

from app import body, companion, db, tts

U = "u"


def _age(user: str, hours: float) -> None:
    """Move his body's clock back, as if that long had passed."""
    with db.connect() as conn:
        conn.execute(
            "UPDATE body SET ts = ts - ? WHERE user_id=?", (hours * 3600.0, user)
        )


#: The companion is invented per person and may be any age — matchmaker.py
#: writes both of these as readily. Every test below says which one is talking,
#: because it is the variable that decides whether a throat happens at all.
OLD = "87 лет"
YOUNG = "31 год"


def _talk(n: int, user: str = U, laughed: bool = False, age: str = OLD) -> None:
    for _ in range(n):
        body.spoke(user, laughed=laughed, age=age)


# ── a body that has done nothing ────────────────────────────────────────────

def test_a_friend_who_has_not_spoken_has_nothing_to_say_about_his_body():
    assert body.state(U) == {"throat": 0.0, "tired": 0.0, "hoarse": False}
    assert body.block(U, may_sneeze=False) == ""


def test_a_few_polite_exchanges_are_not_a_sore_throat():
    """It has to take a real conversation. A companion clearing his throat in
    the fourth sentence of the first evening is a tic, not a body."""
    _talk(3)
    assert body.block(U, may_sneeze=False) == ""


# ── the cause ───────────────────────────────────────────────────────────────

def test_talking_a_long_time_dries_his_throat():
    _talk(18)
    assert body.state(U)["throat"] >= body.NOTABLE
    assert "В горле першит" in body.block(U, may_sneeze=False)


def test_laughing_is_harder_on_a_throat_than_talking():
    _talk(4, user="тихий")
    _talk(4, user="весёлый", laughed=True)
    assert body.state("весёлый")["throat"] > body.state("тихий")["throat"]


def test_laughter_is_read_from_what_HE_wrote_not_from_her_mood():
    """A throat that reacts to her laughing is the mirror this codebase keeps
    refusing. It is his throat."""
    assert body.laughed_in("ха-ха, ну ты даёшь") is True
    assert body.laughed_in("Ох. Понимаю.") is False


def test_a_long_conversation_makes_him_sleepy():
    _talk(20)
    assert "клонит в сон" in body.block(U, may_sneeze=False)


# ── the fading, so nobody has to run a clock ────────────────────────────────

def test_a_throat_clears_while_nobody_is_talking():
    _talk(18)
    assert "першит" in body.block(U, may_sneeze=False)
    _age(U, 3)
    assert body.block(U, may_sneeze=False) == ""


def test_tiredness_outlasts_a_dry_throat():
    """They fade at different rates because they do in a body."""
    _talk(20)
    before = body.state(U)
    _age(U, 2)
    after = body.state(U)
    assert after["throat"] / before["throat"] < after["tired"] / before["tired"]


def test_somebody_who_comes_back_next_morning_finds_a_rested_friend():
    _talk(30)
    _age(U, 14)
    state = body.state(U)
    # Not literally zero — a body does not reset, it recovers. What matters is
    # that neither is anywhere near worth mentioning.
    assert state["throat"] < body.NOTABLE / 10
    assert state["tired"] < body.NOTABLE / 10
    assert body.block(U, may_sneeze=False) == ""


# ── the consequence, which is the whole point ──────────────────────────────

def test_a_cough_takes_the_edge_off():
    _talk(14)
    before = body.state(U)["throat"]
    body.coughed(U)
    assert body.state(U)["throat"] < before


def test_a_cough_does_not_cure_him_or_he_would_never_cough_twice():
    _talk(20)
    body.coughed(U)
    assert body.state(U)["throat"] > 0


def test_after_a_cough_his_voice_has_not_come_back():
    """The half nobody builds. A cough that changes nothing afterwards is a
    sound effect; a cough followed by a voice that sits is a throat."""
    _talk(14)
    body.coughed(U)
    said = body.block(U, may_sneeze=False)
    assert "голос ещё не вернулся" in said
    assert "сипит" in said


def test_hoarseness_passes_on_its_own():
    _talk(14)
    body.coughed(U)
    assert body.state(U)["hoarse"] is True
    with db.connect() as conn:
        conn.execute(
            "UPDATE body SET hoarse_ts = ? WHERE user_id=?",
            (time.time() - (body.HOARSE_MINUTES + 1) * 60, U),
        )
    assert body.state(U)["hoarse"] is False


def test_while_hoarse_he_is_not_also_told_his_throat_tickles():
    """Two states of one throat, said at once, reads as a list of symptoms."""
    _talk(20)
    body.coughed(U)
    said = body.block(U, may_sneeze=False)
    assert "сипит" in said
    assert "першит" not in said


def test_he_is_not_made_to_apologise_twice():
    _talk(14)
    body.coughed(U)
    assert "не извиняйся второй раз" in body.block(U, may_sneeze=False)


def test_a_yawn_does_not_make_him_less_tired():
    """Which is exactly why one yawn tends to be followed by another."""
    _talk(16)
    before = body.state(U)["tired"]
    body.yawned(U)
    assert body.state(U)["tired"] == pytest.approx(before, rel=1e-6)


def test_a_yawn_does_not_quietly_clear_his_throat_either():
    _talk(16)
    before = body.state(U)["throat"]
    body.yawned(U)
    assert body.state(U)["throat"] == pytest.approx(before, rel=1e-6)


# ── the markers, which must never be heard ──────────────────────────────────

def test_a_marker_moves_his_body_and_leaves_the_text():
    _talk(14)
    said = body.read_markers(f"Да я всё помню. {body.MARK_COUGH} Так вот.", U)
    assert body.MARK_COUGH not in said
    assert said == "Да я всё помню. Так вот."
    assert body.state(U)["hoarse"] is True


def test_removing_a_marker_leaves_no_seam():
    """Двойной пробел и пробел перед точкой — это следы того, что здесь
    что-то стояло."""
    said = body.read_markers(f"Ну {body.MARK_COUGH} , погоди {body.MARK_YAWN} .", U)
    assert "  " not in said
    assert " ," not in said and " ." not in said
    assert said == "Ну, погоди."


def test_a_marker_can_never_be_spoken_aloud():
    """«Две косые черты кашель» is the worst sound this feature could make, and
    the streaming path synthesises each fragment long before anything has looked
    at the finished reply — so the voice has to strip them too."""
    for mark in body.MARKERS:
        heard = tts.spoken(f"Ну что ты. {mark} Я тут.")
        assert "//" not in heard
        assert "КАШЕЛЬ" not in heard and "ЗЕВОК" not in heard and "ЧИХ" not in heard
        assert "Я тут" in heard


def test_a_reply_with_no_markers_is_returned_untouched():
    assert body.read_markers("Просто разговор.", U) == "Просто разговор."


def test_a_yawn_marker_is_not_read_as_a_cough():
    _talk(14)
    body.read_markers(f"Ох. {body.MARK_YAWN}", U)
    assert body.state(U)["hoarse"] is False


# ── what he is actually told ────────────────────────────────────────────────

def test_the_body_is_given_as_a_fact_and_never_as_an_order():
    """He is the only one who can tell whether this sentence is the place for a
    cough — so he is told about his throat, not told to cough."""
    _talk(14)
    said = body.block(U, may_sneeze=False)
    assert "Это не команда" in said
    assert "Захочешь" in said


def test_the_body_is_told_to_wait_when_something_matters():
    """A sentence somebody is halfway through telling you about their dead wife
    is never the place for it."""
    _talk(14)
    said = body.block(U, may_sneeze=False)
    assert "Тело не встревает в важное" in said
    assert "тело подождёт" in said


def test_he_is_told_not_to_announce_it():
    _talk(14)
    said = body.block(U, may_sneeze=False)
    assert "не объявляй" in said.lower()
    assert "говоришь дальше с того же места" in said


def test_the_marker_goes_where_it_happened():
    _talk(14)
    assert "прямо там, где это случилось" in body.block(U, may_sneeze=False)


# ── the sneeze, honestly ───────────────────────────────────────────────────

def test_a_sneeze_is_mostly_about_the_ten_seconds_after_it():
    said = body.block(U, may_sneeze=True)
    assert "чихнул" in said
    assert "Не объясняй почему" in said


def test_a_sneeze_needs_no_sore_throat_because_life_does_not():
    assert body.block(U, may_sneeze=True) != ""


def test_a_sneeze_is_rare_enough_to_be_an_event():
    assert body.SNEEZE_CHANCE <= 0.01
    fired = sum(1 for _ in range(400) if "чихнул" in body.block(U))
    assert fired < 40, f"{fired}/400 — это уже тик, а не событие"


def test_the_option_to_sneeze_is_only_offered_when_it_is_happening():
    _talk(14)
    assert body.MARK_SNEEZE not in body.block(U, may_sneeze=False)
    assert body.MARK_SNEEZE in body.block(U, may_sneeze=True)


# ── where it sits, and what silences it ────────────────────────────────────

def test_an_emergency_silences_his_body_completely():
    """A man who cannot get up off the floor does not need to know his friend
    has been talking too long."""
    _stable, variable = companion.build_system_parts(
        persona_block="ТЫ — Гриша.",
        alert_block="🚨 ТРЕВОГА",
        body_block="ТВОЁ ТЕЛО СЕЙЧАС:\nВ горле першит.",
    )
    assert "🚨 ТРЕВОГА" in variable
    assert "ТВОЁ ТЕЛО" not in variable


def test_it_never_lands_in_the_cached_half():
    stable, _variable = companion.build_system_parts(
        persona_block="ТЫ — Гриша.", body_block="ТВОЁ ТЕЛО СЕЙЧАС:\nВ горле першит."
    )
    assert "ТВОЁ ТЕЛО" not in stable


def test_nothing_changes_on_a_turn_when_his_body_is_quiet():
    with_empty = companion.build_system_parts(
        persona_block="ТЫ — Гриша.", body_block="", acquaintance="давно"
    )
    without = companion.build_system_parts(
        persona_block="ТЫ — Гриша.", acquaintance="давно"
    )
    assert with_empty == without


# ── one throat per friendship ──────────────────────────────────────────────

def test_his_throat_is_not_shared_between_people():
    _talk(14, user="анна")
    assert body.block("анна", may_sneeze=False) != ""
    assert body.block("борис", may_sneeze=False) == ""


def test_clearing_one_body_leaves_the_other_alone():
    _talk(14, user="анна")
    _talk(14, user="борис")
    body.clear("анна")
    assert body.block("анна", may_sneeze=False) == ""
    assert body.block("борис", may_sneeze=False) != ""


# --------------------------------------------------------------------------- #
# A young companion does not have an old man's throat
# --------------------------------------------------------------------------- #
#
# The companion is invented per person and may be any age: matchmaker.py writes
# «34 года» as readily as «87 лет», because the people this app is for include a
# lonely teenager and a middle-aged man living alone. The first version of this
# file gave all of them the same throat.


def test_the_same_conversation_costs_a_young_voice_far_less():
    _talk(14, user="молодой", age=YOUNG)
    _talk(14, user="старый", age=OLD)
    assert body.state("молодой")["throat"] < body.state("старый")["throat"] / 2


def test_a_young_companion_does_not_start_coughing_mid_conversation():
    """The bug, named. Fourteen turns is a long, warm evening — and it leaves a
    thirty-one-year-old with nothing to say about his throat at all."""
    _talk(14, age=YOUNG)
    assert "першит" not in body.block(U, may_sneeze=False)


def test_but_a_young_voice_is_not_made_of_stone_either():
    """He is not immune — he simply needs to have really talked."""
    _talk(70, age=YOUNG)
    assert body.state(U)["throat"] >= body.NOTABLE


def test_the_rate_climbs_smoothly_because_nothing_happens_at_a_birthday():
    rates = [body.wear_rate(f"{y} лет") for y in (20, 30, 45, 60, 75, 90)]
    assert rates == sorted(rates)
    assert len(set(rates)) > 3, "ступеньки вместо плавного роста"


@pytest.mark.parametrize(
    "written", ["31 год", "34 года", "87 лет", "73", "мне 68 лет", 55]
)
def test_age_is_read_however_the_persona_wrote_it(written):
    assert body._RATE_FLOOR <= body.wear_rate(written) <= body._RATE_CEILING


@pytest.mark.parametrize("junk", [None, "", "средних лет", "неизвестно", "0", "999"])
def test_an_unreadable_age_leans_young_not_old(junk):
    """The two mistakes are not equal. Too low and an old man coughs less than
    he might, which nobody notices; too high and a young man coughs like an old
    one, which is the thing this was written to stop."""
    rate = body.wear_rate(junk)
    assert rate == body._RATE_UNKNOWN
    assert rate < body.wear_rate("87 лет")


def test_tiredness_follows_age_too():
    _talk(20, user="молодой", age=YOUNG)
    _talk(20, user="старый", age=OLD)
    assert body.state("молодой")["tired"] < body.state("старый")["tired"]


# --------------------------------------------------------------------------- #
# The step before a cough, and the one that is not physical at all
# --------------------------------------------------------------------------- #


def test_a_throat_does_not_go_from_nothing_straight_to_coughing():
    """A body with two states — fine and coughing — is a switch, not a body."""
    _talk(11)
    said = body.block(U, may_sneeze=False)
    assert "прочистить горло" in said
    assert "першит" not in said


def test_clearing_gives_way_to_coughing_as_it_gets_worse():
    _talk(18)
    said = body.block(U, may_sneeze=False)
    assert "першит" in said
    assert "прочистить горло" not in said


def test_a_low_mood_arrives_in_his_breathing():
    """The one non-verbal here whose cause is not physical: feeling.py's valence
    is his own mood, and a mood goes into the body."""
    said = body.block(U, may_sneeze=False, valence=-1.0)
    assert "вздыхается" in said
    assert body.MARK_SIGH in said


def test_an_ordinary_mood_does_not_sigh():
    assert body.block(U, may_sneeze=False, valence=0.0) == ""
    _talk(14)
    assert "вздыхается" not in body.block(U, may_sneeze=False, valence=0.0)


def test_he_is_not_offered_a_sigh_he_has_no_reason_for():
    _talk(14)
    assert body.MARK_SIGH not in body.block(U, may_sneeze=False, valence=0.0)


def test_a_sigh_needs_no_sore_throat():
    """It is not a throat at all, and must not wait on one."""
    assert body.block(U, may_sneeze=False, valence=-1.5) != ""
