"""The mood system: a change is only visible against a person's own normal."""

from __future__ import annotations

import time

import pytest

from app import db, mood


@pytest.fixture(autouse=True)
def _fresh(tmp_path, monkeypatch):
    from app import config

    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "t.db"))
    db.init_db()
    yield


def _fill(user: str, n: int, *, level: float, ago_from: float = 0, note: str = "") -> None:
    """n readings at a given level, oldest first, ending `ago_from` seconds ago."""
    now = time.time()
    with db.connect() as conn:
        for i in range(n):
            conn.execute(
                "INSERT INTO mood_readings (user_id, ts, energy, warmth, lightness,"
                " clarity, engagement, word, note, because) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (user, now - ago_from - (n - i) * 3600, level, level, level, 0.0,
                 level, "", note, ""),
            )


def test_no_readings_is_silent():
    assert mood.block("nobody") == ""


def test_too_little_history_says_so_instead_of_inventing_a_baseline():
    _fill("u", 3, level=-2)
    said = mood.block("u")
    assert "слишком мало" in said
    # And it must NOT claim a change, because there is nothing to compare to.
    assert "ПЕРЕМЕНА" not in said


def test_steady_person_shows_no_change():
    _fill("u", 20, level=0)
    said = mood.block("u")
    assert "ПЕРЕМЕНА" not in said
    assert "тише обычного" not in said


def test_a_drop_from_his_own_normal_is_seen_and_dated():
    _fill("u", 20, level=1, ago_from=6 * 86400)     # usually bright
    _fill("u", 3, level=-2)                          # now flat
    said = mood.block("u")
    assert "ЗАМЕТНАЯ ПЕРЕМЕНА" in said
    assert "Не бодрись" in said


def test_the_same_low_mood_is_NOT_a_change_for_someone_always_low():
    """The whole point: «устал» means nothing from a person who always is."""
    _fill("u", 20, level=-2, ago_from=6 * 86400)
    _fill("u", 3, level=-2)
    said = mood.block("u")
    assert "ПЕРЕМЕНА" not in said


def test_a_rise_is_seen_too_and_is_not_treated_as_trouble():
    _fill("u", 20, level=-1, ago_from=6 * 86400)
    _fill("u", 3, level=2)
    said = mood.block("u")
    assert "живее обычного" in said
    assert "ПЕРЕМЕНА" not in said


def test_clarity_is_reported_on_its_own_not_averaged_away():
    """Sadness and confusion are different, and only one changes HOW you speak."""
    now = time.time()
    with db.connect() as conn:
        for i in range(20):                      # usually clear, ordinary mood
            conn.execute(
                "INSERT INTO mood_readings (user_id, ts, energy, warmth, lightness,"
                " clarity, engagement) VALUES (?,?,?,?,?,?,?)",
                ("u", now - (40 - i) * 3600, 0, 0, 0, 1, 0),
            )
        for i in range(3):                       # today: same mood, lost the thread
            conn.execute(
                "INSERT INTO mood_readings (user_id, ts, energy, warmth, lightness,"
                " clarity, engagement) VALUES (?,?,?,?,?,?,?)",
                ("u", now - (3 - i) * 60, 0, 0, 0, -2, 0),
            )
    said = mood.block("u")
    assert "труднее держать нить" in said
    assert "ЗАМЕТНАЯ ПЕРЕМЕНА" not in said       # his feeling did not move


def test_one_terrible_evening_does_not_become_who_he_is():
    """Median, not mean: the baseline must survive an outlier."""
    _fill("u", 19, level=1, ago_from=6 * 86400)
    _fill("u", 1, level=-2, ago_from=5 * 86400)   # one awful night, long ago
    _fill("u", 3, level=1)                        # back to himself
    assert "ПЕРЕМЕНА" not in mood.block("u")


def test_record_ignores_an_empty_reading():
    mood.record("u", {})
    assert mood.recent("u") == []


def test_record_clamps_out_of_range_scores():
    mood.record("u", {"energy": 99, "warmth": -99, "word": "бодр"})
    r = mood.recent("u")[0]
    assert r["energy"] == 2 and r["warmth"] == -2


def test_a_string_mood_from_the_old_shape_still_records():
    mood.record("u", {"word": "устал"})
    assert mood.recent("u")[0]["word"] == "устал"


# ── the observation register ────────────────────────────────────────────────

def test_once_is_held_but_never_told():
    mood.observe("u", "ушёл_от_вопроса", "здоровье", "«не знаю»")
    assert mood.standing_block("u") == ""          # one time is not a truth


def test_twice_becomes_a_truth():
    mood.observe("u", "ушёл_от_вопроса", "здоровье")
    mood.observe("u", "ушёл_от_вопроса", "здоровье")
    said = mood.standing_block("u")
    assert "здоровье" in said and "2 раза" in said


def test_the_same_thing_about_a_different_subject_counts_separately():
    mood.observe("u", "закрылся_на_теме", "дочь")
    mood.observe("u", "закрылся_на_теме", "война")
    assert mood.standing_block("u") == ""          # neither reached two


def test_invented_tags_are_dropped():
    mood.observe("u", "он_грустный_потому_что_осень", "")
    mood.observe("u", "он_грустный_потому_что_осень", "")
    assert mood.standing_block("u") == ""


def test_what_lifts_him_is_confirmed_the_same_way():
    for _ in range(3):
        mood.observe("u", "подняли_воспоминания", "")
    said = mood.standing_block("u")
    assert "вспоминали хорошее" in said
    assert "3 раза" in said


# --------------------------------------------------------------------------- #
# His normal depends on the hour, because he does
# --------------------------------------------------------------------------- #
#
# Older adults shift toward morningness, and morning types are reliably worse in
# the evening. Against one all-day average, a man who is simply flatter at eight
# reads as BELOW HIS NORMAL every single evening — a false alarm on a schedule,
# which teaches the companion to tread carefully when nothing is wrong and
# buries the real change on the day it finally comes.

DAY = 86400


def _at(user: str, days_ago: float, utc_hour: int, level: float, nudge: int = 0) -> None:
    """One reading landing on a given UTC hour, `days_ago` days back."""
    t = time.time() - days_ago * DAY
    t -= (time.gmtime(t).tm_hour - utc_hour) * 3600
    with db.connect() as conn:
        conn.execute(
            "INSERT INTO mood_readings (user_id, ts, energy, warmth, lightness,"
            " clarity, engagement, word, note, because) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (user, t + nudge, level, level, level, 0.0, level, "", "", ""),
        )


def _a_man_brighter_by_day(user: str = "u") -> None:
    """Talks most days around noon and is bright (+1); drops in on some evenings
    and is flatter then (-1). Both are simply how he is."""
    for d in range(14, 1, -1):
        _at(user, d, 13, 1.0)
        _at(user, d, 13, 1.0, nudge=600)
        if d % 3 == 0:
            _at(user, d, 20, -1.0)


def _tonight(level: float, user: str = "u", hour: int = 20) -> None:
    for k in range(3):
        _at(user, 0, hour, level, nudge=k * 600)


def test_his_ordinary_evening_is_not_treated_as_a_bad_day():
    """The fault this exists to remove. He is flatter every evening and always
    has been; that is not news and must not be announced as news."""
    _a_man_brighter_by_day()
    _tonight(-1.0)
    said = mood.block("u")
    assert "⚠" not in said
    assert "немного тише" not in said


def test_an_evening_worse_than_his_own_evenings_is_still_caught():
    """Sensitivity is the thing that must survive the fix."""
    _a_man_brighter_by_day()
    _tonight(-2.0)
    assert "⚠" in mood.block("u")


def test_a_daytime_drop_is_still_caught():
    """He is always bright at noon, so flat at noon is a real change — and the
    per-hour normal must not soften it."""
    _a_man_brighter_by_day()
    _tonight(-1.0, hour=13)
    assert "⚠" in mood.block("u")


def test_a_part_of_the_day_he_barely_visits_falls_back_to_his_overall_normal():
    """Below MIN_PER_PART there is no such thing as his three-in-the-morning
    self, and inventing one from a single reading would be worse than the
    all-day average it replaced."""
    _a_man_brighter_by_day()
    _tonight(-1.0, hour=3)                     # a part with no history at all
    assert "⚠" in mood.block("u")


def test_the_hour_is_read_in_utc_so_it_cannot_drift():
    """Local time moves — daylight saving, or the server being rehomed — and a
    reading that changed parts would compare his evenings against his mornings
    six months later, invisibly."""
    winter = time.mktime((2026, 1, 15, 20, 0, 0, 0, 0, 0))
    summer = time.mktime((2026, 7, 15, 20, 0, 0, 0, 0, 0))
    assert mood._part(winter) == mood._part(summer)


def test_every_hour_of_the_day_lands_in_a_part():
    seen = {mood._part(time.time() - h * 3600) for h in range(48)}
    assert seen == set(range(24 // mood._PART_HOURS))


def test_a_new_friendship_behaves_exactly_as_it_did_before():
    """With no per-hour history, the fallback is the old all-day baseline — so
    nothing about somebody's first fortnight changed."""
    _fill("u", 12, level=1.0)
    _fill("u", 3, level=-1.0)
    assert "⚠" in mood.block("u")
