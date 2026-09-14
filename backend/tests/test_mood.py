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


# --------------------------------------------------------------------------- #
# One spelling per topic, or nothing is ever counted twice
# --------------------------------------------------------------------------- #
#
# The row is keyed on (user, tag, subject), so the whole «дважды — это правда»
# rule silently failed for every observation carrying a subject — which are the
# most specific and most valuable ones it holds.


def test_the_same_topic_spelled_differently_still_counts_as_the_same():
    for spelling in ("Война.", "война", "  ВОЙНА  ", "«война»"):
        mood.observe("u", "закрылся_на_теме", spelling)
    said = mood.standing_block("u")
    assert "война" in said
    assert "4 раза" in said


def test_genuinely_different_topics_still_count_apart():
    """The fix must not collapse his children into his war."""
    mood.observe("u", "закрылся_на_теме", "война")
    mood.observe("u", "закрылся_на_теме", "дети")
    assert mood.standing_block("u") == ""          # neither reached two


def test_the_extractor_is_shown_the_words_it_already_used():
    """No cleaning in code turns «про войну» into «война». Showing what exists
    and letting the model recognise its own topic does."""
    mood.observe("u", "закрылся_на_теме", "война")
    mood.observe("u", "оживился_на_теме", "рыбалка")
    seen = mood.subjects_seen("u")
    assert "«война»" in seen and "«рыбалка»" in seen


def test_nothing_is_offered_before_anything_was_named():
    assert mood.subjects_seen("u") == ""


def test_observations_without_a_topic_are_not_offered_as_topics():
    mood.observe("u", "поднял_юмор", "")
    assert mood.subjects_seen("u") == ""


def test_one_persons_topics_are_not_anothers():
    mood.observe("анна", "закрылся_на_теме", "война")
    assert "война" in mood.subjects_seen("анна")
    assert mood.subjects_seen("борис") == ""


# ── the dial: how much of his own life this person wants ────────────────────
#
# «Мне не нравится, что одно и то же принимается ко всем.» Two people, the same
# app. One is in a bad way and does not want to hear about anybody's troubles,
# not even hinted at. The other would far rather listen to his friend's week
# than recount his own. They are not the same person and the same paragraph was
# being read to both.
#
# Watched, never guessed — and the watching is the varied, indirect part: one
# goes quiet and terse when the friend starts on himself, another asks harder.
# The TAG is the conclusion the reader reached, not the signal it reached it
# from, which is why nothing here enumerates the signals.

def test_most_people_are_simply_in_the_middle():
    """Which is the point. A dial that took a side on everybody would be the
    same mistake with three settings instead of one."""
    assert mood.openness("u") == "normal"


def test_once_is_not_enough_to_conclude_anything():
    """He went quiet on it. Quiet has more than one meaning, and reshaping a
    friendship around a single coincidence is worse than not reshaping at all."""
    mood.observe("u", "не_хотел_слушать_про_тебя", "")
    assert mood.openness("u") == "normal"
    mood.observe("u", "хотел_слушать_про_тебя", "")
    assert mood.openness("u") == "normal"


def test_twice_is():
    mood.observe("анна", "не_хотел_слушать_про_тебя", "")
    mood.observe("анна", "не_хотел_слушать_про_тебя", "")
    assert mood.openness("анна") == "closed"

    mood.observe("борис", "хотел_слушать_про_тебя", "")
    mood.observe("борис", "хотел_слушать_про_тебя", "")
    assert mood.openness("борис") == "open"


def test_either_of_the_two_open_signals_counts_toward_the_same_conclusion():
    """Asking to hear more and refusing to be brushed off are different
    behaviours that mean the same thing, so they are added, not counted apart."""
    mood.observe("u", "хотел_слушать_про_тебя", "")
    mood.observe("u", "настоял_чтобы_рассказал", "")
    assert mood.openness("u") == "open"


def test_asking_outright_counts_the_very_first_time():
    """The «twice» rule is for INFERENCES. «Не рассказывай мне про свои
    болячки» is not an inference. Making somebody say it twice before it counts
    is not caution, it is ignoring them — and it is the thing they would
    notice."""
    mood.observe("анна", "просил_не_рассказывать_про_тебя", "")
    assert mood.openness("анна") == "closed"

    mood.observe("борис", "просил_рассказывать_про_себя", "")
    assert mood.openness("борис") == "open"


def test_what_he_said_outweighs_what_was_guessed_from_him():
    """He was watched brushing it aside twice — and then asked, in words, to
    hear about it. The words win: they are the one signal that cannot be a
    misreading."""
    for _ in range(3):
        mood.observe("u", "не_хотел_слушать_про_тебя", "")
    mood.observe("u", "просил_рассказывать_про_себя", "")
    assert mood.openness("u") == "open"


def test_where_both_were_said_the_quieter_answer_wins():
    """Nothing here can tell which request came later, so it takes the safer of
    the two: being spared something you wanted is a smaller harm than being
    handed something you asked not to hear."""
    mood.observe("u", "просил_рассказывать_про_себя", "")
    mood.observe("u", "просил_не_рассказывать_про_тебя", "")
    assert mood.openness("u") == "closed"


def test_the_same_holds_for_what_was_merely_watched():
    for _ in range(2):
        mood.observe("u", "хотел_слушать_про_тебя", "")
        mood.observe("u", "не_хотел_слушать_про_тебя", "")
    assert mood.openness("u") == "closed"


def test_one_persons_dial_is_not_anothers():
    """The whole complaint, in one assertion."""
    mood.observe("анна", "просил_не_рассказывать_про_тебя", "")
    for _ in range(2):
        mood.observe("борис", "хотел_слушать_про_тебя", "")
    assert mood.openness("анна") == "closed"
    assert mood.openness("борис") == "open"
    assert mood.openness("виктор") == "normal"


def test_the_three_tags_are_in_the_vocabulary_the_reader_is_given():
    """A tag the extractor has never been shown is a tag that is never written,
    and the dial would sit at «normal» for everybody for ever."""
    from app import learn

    for tag in ("не_хотел_слушать_про_тебя", "просил_не_рассказывать_про_тебя",
                "просил_рассказывать_про_себя"):
        assert tag in mood.TAGS, tag
        assert tag in learn._EXTRACTION_SYSTEM, tag


def test_the_dial_tags_are_never_also_reported_as_findings():
    """The register reports what is proven about HIM; the dial is about the two
    of them, and fit.py renders it. A tag that escaped PAIR would arrive twice
    in one prompt — once as «подтвердилось: не хотел слушать про тебя» and once
    as the instruction — which is the double-reporting this file already fixed
    once and must not reintroduce."""
    for tag in (*mood._OPEN, *mood._CLOSED, *mood._SAID_OPEN, *mood._SAID_CLOSED):
        assert tag in mood.PAIR, tag

    for _ in range(3):
        mood.observe("u", "не_хотел_слушать_про_тебя", "")
    assert mood.openness("u") == "closed"
    assert "слушать" not in mood.standing_block("u")


# ── the second dial: how he wants to be missed ──────────────────────────────
#
# The oldest unmechanised rule in the app. The constitution describes three
# people in prose — one needs to hear outright that he was waited for and needs
# it to sting; one finds somebody else's feeling a weight; one hears any mention
# of his absence as a reproach — and then said «смотри, кто перед тобой» while
# handing him nothing to look at. reading.py guessed at it on install day, from
# a paragraph written to a machine the person had never met, and nothing ever
# checked that guess. It governs the first sentence said to somebody who has
# been gone a week, which is the highest-stakes sentence in the app.

def test_most_people_are_in_the_middle_here_too():
    assert mood.closeness("u") == "normal"


def test_it_is_watched_and_once_is_not_enough():
    mood.observe("u", "обрадовался_что_ждали", "")
    assert mood.closeness("u") == "normal"
    mood.observe("u", "обрадовался_что_ждали", "")
    assert mood.closeness("u") == "missed"


def test_the_other_end_is_watched_the_same_way():
    for _ in range(2):
        mood.observe("u", "тяжело_что_ждали", "")
    assert mood.closeness("u") == "spared"


def test_asking_whether_he_was_missed_counts_at_once():
    """«Ты хоть скучал?» is not a thing the other two kinds of person ever say.
    It is a direct act, not a tone to be read twice."""
    mood.observe("u", "спросил_ждали_ли_его", "")
    assert mood.closeness("u") == "missed"


def test_asking_not_to_be_waited_for_counts_at_once():
    mood.observe("u", "просил_не_ждать", "")
    assert mood.closeness("u") == "spared"


def test_the_quieter_answer_wins_here_too():
    """The two mistakes are not the same size. Not hearing «я тебя ждал» when
    you wanted it is a quiet disappointment; hearing it when it lands as a debt
    is one more thing to feel guilty about — from the one place that was
    supposed to be free of that."""
    mood.observe("u", "спросил_ждали_ли_его", "")
    mood.observe("u", "просил_не_ждать", "")
    assert mood.closeness("u") == "spared"


def test_the_four_new_tags_are_real_and_belong_to_the_pair():
    from app import learn

    for tag in (*mood._MISSED, *mood._SPARED, *mood._SAID_MISSED, *mood._SAID_SPARED):
        assert tag in mood.TAGS, tag
        assert tag in mood.PAIR, tag
        assert tag in learn._EXTRACTION_SYSTEM, tag
