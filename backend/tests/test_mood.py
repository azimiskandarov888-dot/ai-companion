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
