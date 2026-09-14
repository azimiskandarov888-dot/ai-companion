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


# ── he did not know what day it was ─────────────────────────────────────────
#
# Not the date, not the weekday, not the month. So «дочь Валя, день рождения 3
# мая» could sit in his memory for a year and pass unremarked on the third of
# May — the one date in the world that person wanted somebody to remember.

def test_he_is_told_the_day_and_it_is_never_omitted():
    said = occasions.today_block(date=dt.date(2026, 7, 22))
    assert "СЕГОДНЯ среда, 22 июля 2026 года" in said


def test_and_told_that_this_is_how_he_notices_the_dates_that_matter():
    """Nothing is parsed out of anything. Dates live in his facts however they
    came up — «3 мая», «в начале мая», «на Пасху» — and noticing that today is
    the third of May is what a model is good at and a regex is hopeless at."""
    said = occasions.today_block(
        facts="- дочь Валя, день рождения 3 мая", date=dt.date(2026, 7, 22)
    )
    assert "годовщина или другой его день" in said
    assert "скажи об этом ПЕРВЫМ" in said
    # …and the other half, which matters more and is easier to get wrong
    assert "дата тяжёлая — не поздравляй и не бодрись" in said


def test_somebody_with_no_dates_recorded_is_not_told_to_watch_for_them():
    """Dead text on the three hundred and sixty days that match nothing — and
    every day, for somebody whose dates nobody has ever mentioned."""
    said = occasions.today_block(facts="- любит рыбалку", date=dt.date(2026, 7, 22))
    assert "СЕГОДНЯ среда" in said
    assert "ПЕРВЫМ" not in said


def test_a_date_is_recognised_however_it_was_written_down():
    for written in ("день рождения 3 мая", "родился 12.04", "годовщина в ноябре",
                    "свадьба была 7 сентября"):
        assert occasions._has_dates(written), written
    for not_a_date in ("любит рыбалку", "дочь Валя", "работал сварщиком"):
        assert not occasions._has_dates(not_a_date), not_a_date


def test_a_plain_day_is_still_a_day():
    said = occasions.today_block(date=dt.date(2026, 7, 22))
    assert "Сегодня ещё и" not in said


# ── the calendar no longer assumes a country or an age ──────────────────────

def test_the_day_that_told_him_how_old_his_friend_was_is_gone():
    """«Международный день пожилых людей — ЕГО день. Сказать тёплые слова о
    том, как он важен и любим.» The whole failure of this app in one line: a
    greeting addressed to a category rather than a person."""
    assert occasions.occasion_for(dt.date(2026, 10, 1)) is None
    for occ in occasions.OCCASIONS.values():
        assert "пожил" not in occ["name"].lower()
        assert "пожил" not in occ["note"].lower()


def test_somebody_known_to_live_elsewhere_is_not_wished_a_local_holiday():
    may_ninth = dt.date(2026, 5, 9)
    assert occasions.occasion_for(may_ninth, country="россия") is not None
    assert occasions.occasion_for(may_ninth, country="казахстан") is not None
    assert occasions.occasion_for(may_ninth, country="португалия") is None


def test_an_unknown_country_still_gets_them():
    """Most of this app's people are in that world; silence costs a warm
    moment, and there is nothing to be wrong about yet."""
    assert occasions.occasion_for(dt.date(2026, 5, 9)) is not None


def test_new_year_belongs_to_everybody():
    for where in ("", "россия", "португалия", "австралия"):
        assert occasions.occasion_for(dt.date(2026, 1, 1), country=where) is not None


def test_the_country_reaches_the_block_through_what_was_learned(tmp_path, monkeypatch):
    from app import config, db, emergency

    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "t.db"))
    db.init_db()
    emergency.remember("иван", "россия")
    emergency.remember("жоао", "португалия")

    may_ninth = dt.date(2026, 5, 9)
    assert "День Победы" in occasions.today_block("иван", date=may_ninth)
    assert "День Победы" not in occasions.today_block("жоао", date=may_ninth)
    # and the date itself survives either way — that is the part he must have
    for who in ("иван", "жоао", "никто"):
        assert "СЕГОДНЯ" in occasions.today_block(who, date=may_ninth)


def test_no_note_asserts_what_the_day_means_to_him():
    """«Его день» was an assumption. Every note is an opening now."""
    for occ in occasions.OCCASIONS.values():
        assert "его день" not in occ["note"].lower()


def test_every_spelling_of_a_country_lands_on_the_same_side():
    """emergency.py takes more than one name for some places. A missing
    alternate fails in the worse direction: it would cut a man in Minsk out of
    the ninth of May over how he happened to phrase where he lives.

    Listed rather than derived, because emergency.py's map cannot tell an
    alternate spelling from a coincidence — half of Europe shares 112."""
    from app import emergency

    alternates = (
        {"россия", "рф"},
        {"беларусь", "белоруссия"},
        {"киргизия", "кыргызстан"},
        {"сша", "америка", "штаты"},
        {"великобритания", "англия", "шотландия"},
        {"нидерланды", "голландия"},
        {"корея", "южная корея"},
        {"оаэ", "эмираты"},
    )
    for names in alternates:
        assert names <= set(emergency._BY_COUNTRY), f"уже не все известны: {names}"
        inside = names & occasions.SHARED_CALENDAR
        assert inside in (set(), names), (
            f"одна страна по разные стороны календаря: {sorted(names - inside)}"
        )


def test_the_calendar_names_countries_this_app_can_actually_recognise():
    """A name emergency.py never stores could never match, so it would sit here
    looking like coverage and providing none."""
    from app import emergency

    assert occasions.SHARED_CALENDAR <= set(emergency._BY_COUNTRY)
