"""Occasions: reactive special-date lookup."""

from __future__ import annotations

import datetime as dt

from app import occasions


def test_known_occasion():
    occ = occasions.occasion_for(dt.date(2026, 3, 8))
    assert occ is not None and "женский день" in occ["name"].lower()


def test_no_occasion_on_plain_day():
    assert occasions.occasion_for(dt.date(2026, 7, 22)) is None


def test_occasion_has_origin_hint():
    # Every occasion carries a 'note' the brain can use to tell the story.
    for key, occ in occasions.OCCASIONS.items():
        assert occ.get("name") and occ.get("note")
