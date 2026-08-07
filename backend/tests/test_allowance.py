"""The day's allowance, and falling asleep.

Both of these guard real money, so they are tested for the cases that actually
happen: someone who talks a lot, and a television left on in an empty room.
"""

from __future__ import annotations

import pytest

from app import allowance


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
