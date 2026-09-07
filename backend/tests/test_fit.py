"""The fit between two people — a property of the pair, never of either one."""

from __future__ import annotations

import pytest

from app import db, fit, mood


@pytest.fixture(autouse=True)
def _fresh(tmp_path, monkeypatch):
    from app import config

    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "t.db"))
    db.init_db()
    yield


def _seen(user: str, tag: str, n: int, subject: str = "") -> None:
    for _ in range(n):
        mood.observe(user, tag, subject)


def test_nothing_watched_yet_says_nothing():
    assert fit.block("u") == ""


def test_one_occurrence_is_never_enough():
    _seen("u", "зашло_что_позвал", 1)
    assert fit.block("u") == ""


def test_push_that_works_is_encouraged():
    _seen("u", "зашло_что_позвал", 4)
    said = fit.block("u")
    assert "Предлагай, зови, затевай" in said
    assert "4 раза" in said


def test_push_that_fails_is_told_to_stop():
    """The same trait, the opposite instruction. This is the whole point."""
    _seen("u", "не_зашло_что_позвал", 3)
    said = fit.block("u")
    assert "Сбавь" in said
    assert "Предлагай, зови, затевай" not in said


def test_mixed_evidence_follows_the_majority():
    _seen("u", "зашло_что_позвал", 5)
    _seen("u", "не_зашло_что_позвал", 2)
    assert "Предлагай, зови, затевай" in fit.block("u")


def test_a_tie_is_resolved_toward_backing_off():
    """When it is genuinely unclear, the quiet mistake is the cheaper one."""
    _seen("u", "зашло_что_позвал", 3)
    _seen("u", "не_зашло_что_позвал", 3)
    assert "Сбавь" in fit.block("u")


def test_disagreement_is_calibrated_separately_from_push():
    _seen("u", "зашло_что_позвал", 3)
    _seen("u", "не_понравилось_несогласие", 3)
    said = fit.block("u")
    assert "Предлагай, зови, затевай" in said       # keep the energy
    assert "Своё мнение оставь при себе" in said    # drop the arguing


def test_the_nose_is_protected_rather_than_fixed():
    """His imperfections are not tolerated, they are the reason he is loved."""
    _seen("u", "понравился_его_промах", 2)
    said = fit.block("u")
    assert "Не исправляйся" in said
    assert "за что он тебя любит" in said


def test_hearing_trouble_is_counted_from_both_signals():
    """People with poor hearing do not complain, they get used to it — so
    asking once and mishearing once must add up rather than each wait for two."""
    _seen("u", "просил_помедленнее", 1)
    _seen("u", "не_расслышал", 1)
    assert "ТРУДНО РАЗБИРАТЬ РЕЧЬ" in fit.block("u")


def test_someone_who_leads_is_left_to_lead():
    _seen("u", "сам_повёл_разговор", 3)
    assert "не перехватывай" in fit.block("u")


def test_the_block_says_it_was_watched_not_guessed():
    _seen("u", "зашло_что_позвал", 2)
    assert "не догадки" in fit.block("u")


def test_two_people_do_not_share_a_fit():
    _seen("a", "понравился_его_промах", 3)
    assert fit.block("b") == ""
