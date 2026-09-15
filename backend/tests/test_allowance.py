"""The day's allowance, and falling asleep.

Both of these guard real money, so they are tested for the cases that actually
happen: someone who talks a lot, and a television left on in an empty room.
"""

from __future__ import annotations

import pytest

from app import allowance, db


@pytest.fixture(autouse=True)
def _clean():
    """Each test gets its own person, and a woken one."""
    allowance._asleep.clear()
    allowance._stray.clear()
    yield
    allowance._asleep.clear()
    allowance._stray.clear()


# ── the day's allowance ──────────────────────────────────────────────────────


def test_a_fresh_day_is_allowed():
    verdict = allowance.check("fresh-person")
    assert verdict.allowed
    assert verdict.seconds_left == allowance.SECONDS_PER_DAY


def test_spending_reduces_what_is_left():
    allowance.spend("spender", 600)
    assert allowance.used_today("spender") == pytest.approx(600)
    assert allowance.seconds_left("spender") == allowance.SECONDS_PER_DAY - 600


def test_the_day_runs_out_and_he_says_so_himself():
    allowance.spend("chatty", allowance.SECONDS_PER_DAY + 1)

    verdict = allowance.check("chatty")
    assert not verdict.allowed
    assert verdict.code == "daily_limit"
    assert verdict.seconds_left == 0
    # Never an error code — he says it, in his own voice.
    assert verdict.reason
    assert "limit" not in verdict.reason.lower()
    assert "error" not in verdict.reason.lower()


def test_each_person_has_their_own_day():
    allowance.spend("one", allowance.SECONDS_PER_DAY + 1)
    assert not allowance.check("one").allowed
    assert allowance.check("two").allowed


def test_negative_seconds_cannot_buy_time_back():
    allowance.spend("clock-back", 100)
    allowance.spend("clock-back", -500)
    assert allowance.used_today("clock-back") == pytest.approx(100)


# ── falling asleep ───────────────────────────────────────────────────────────


def test_a_television_puts_him_to_sleep():
    """Short fragments, over and over, with nobody actually talking to him."""
    for _ in range(allowance.DOZE_AFTER_STRAY_TURNS):
        allowance.note_turn("tv-room", "…ага")

    assert allowance.is_asleep("tv-room")

    verdict = allowance.check("tv-room")
    assert not verdict.allowed
    assert verdict.code == "asleep"


def test_one_real_sentence_keeps_him_awake():
    """Someone thinking quietly between sentences is never cut off."""
    for _ in range(allowance.DOZE_AFTER_STRAY_TURNS - 1):
        allowance.note_turn("thinker", "мм")

    allowance.note_turn("thinker", "Я сегодня вспоминал, как мы ездили на море.")

    # The count is reset entirely, not merely decremented.
    for _ in range(allowance.DOZE_AFTER_STRAY_TURNS - 1):
        allowance.note_turn("thinker", "мм")

    assert not allowance.is_asleep("thinker")


def test_waking_him_does_not_refill_the_day():
    """Waking is free. It must not become a way around the allowance."""
    allowance.spend("woken", allowance.SECONDS_PER_DAY + 1)
    for _ in range(allowance.DOZE_AFTER_STRAY_TURNS):
        allowance.note_turn("woken", "…")

    allowance.wake("woken")

    assert not allowance.is_asleep("woken")
    verdict = allowance.check("woken")
    assert not verdict.allowed
    assert verdict.code == "daily_limit"


def test_waking_clears_the_dozing():
    for _ in range(allowance.DOZE_AFTER_STRAY_TURNS):
        allowance.note_turn("napper", "…")
    assert allowance.is_asleep("napper")

    allowance.wake("napper")

    assert allowance.check("napper").allowed


# ── a terse man is not stray noise ──────────────────────────────────────────

def _talks_like(user: str, text: str, n: int = 12) -> None:
    """n turns in conversations that are over, so they are measurable."""
    from app import memory

    for _ in range(n):
        memory.log_turn(user, "user", text)
    with db.connect() as conn:
        conn.execute("UPDATE turns SET ts = ts - ? WHERE user_id=?", (2 * 86400, user))


def test_two_words_are_a_man_answering():
    """«Ага», «да», «угу», «ладно», «нет» are all under twelve characters, so six
    of them in a row put somebody to sleep for talking the way he talks."""
    for said in ("да нет, не надо", "ну ладно", "не знаю"):
        for _ in range(allowance.DOZE_AFTER_STRAY_TURNS + 2):
            allowance.note_turn("u", said)
        assert not allowance.is_asleep("u"), said
        allowance.wake("u")


def test_a_measured_terse_man_is_never_dozed_on_for_single_words():
    """The app already measures that he talks this way. Asking is the fix — and
    the asymmetry decides it: dozing on a real person means a voice-only friend
    saying «кажется, я задремал» and a man who has to find a tap; not dozing on
    a scrap of television means a few odd replies."""
    _talks_like("молчун", "ага")
    for _ in range(allowance.DOZE_AFTER_STRAY_TURNS + 3):
        allowance.note_turn("молчун", "угу")
    assert not allowance.is_asleep("молчун")


def test_but_somebody_who_does_not_talk_that_way_still_dozes():
    """The mechanism has to survive, or the microphone answers the television
    for ever."""
    _talks_like("обычный", "да нормально всё, вчера в магазин ходил за хлебом")
    for _ in range(allowance.DOZE_AFTER_STRAY_TURNS + 1):
        allowance.note_turn("обычный", "угу")
    assert allowance.is_asleep("обычный")
