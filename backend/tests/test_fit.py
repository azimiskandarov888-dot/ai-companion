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
    assert "твой напор ему заходит" in said and "Зови смело" in said
    assert "4 раза" in said


def test_push_that_fails_gets_the_opposite_instruction():
    """The same trait, the opposite instruction. This is the whole point —
    and it is still a default, not a ban."""
    _seen("u", "не_зашло_что_позвал", 3)
    said = fit.block("u")
    assert "Исходи из тихого" in said
    assert "Зови смело" not in said


def test_a_clear_majority_still_gives_a_verdict():
    _seen("u", "зашло_что_позвал", 7)
    _seen("u", "не_зашло_что_позвал", 2)
    assert "Зови смело" in fit.block("u")


def test_mixed_evidence_is_reported_as_mixed_not_as_a_verdict():
    """A tie means «sometimes», which is most people. Turning that into a rule
    is exactly the rigidity the research says costs a relationship."""
    _seen("u", "зашло_что_позвал", 3)
    _seen("u", "не_зашло_что_позвал", 3)
    said = fit.block("u")
    assert "по-разному" in said and "не решай заранее" in said


def test_backing_off_is_a_default_and_says_so():
    _seen("u", "не_зашло_что_позвал", 4)
    said = fit.block("u")
    assert "норма, а не запрет" in said


def test_a_first_no_that_is_really_a_test_is_learned():
    _seen("u", "уговорили_и_обрадовался", 2)
    said = fit.block("u")
    assert "ЗВАТЬ ДВАЖДЫ" in said
    assert "Не роняй с первого раза" in said


def test_someone_who_wants_to_be_asked_a_lot_gets_asked_a_lot():
    """The cap was the mistake: for this person questions are the gift."""
    _seen("u", "хотел_больше_вопросов", 3)
    said = fit.block("u")
    assert "Спрашивай много и подробно" in said
    assert "не про него" in said


def test_even_someone_tired_of_questions_keeps_the_exception():
    _seen("u", "устал_от_расспросов", 4)
    said = fit.block("u")
    assert "если он сам разговорился" in said


def test_disagreement_is_calibrated_separately_from_push():
    _seen("u", "зашло_что_позвал", 3)
    _seen("u", "не_понравилось_несогласие", 3)
    said = fit.block("u")
    assert "Зови смело" in said                     # keep the energy
    assert "Своё мнение оставь при себе" in said    # drop the arguing


def test_the_nose_is_protected_rather_than_fixed():
    """His imperfections are not tolerated, they are the reason he is loved."""
    _seen("u", "понравился_его_промах", 2)
    said = fit.block("u")
    assert "Не исправляйся" in said
    assert "не становись безупречным" in said


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


# ── the floors: what survives no matter what the data says ──────────────────

def test_the_floors_outrank_the_calibration():
    """Five things stay whatever the observations say, and they are stated
    BEFORE the calibration, so a model reading top-down meets them first."""
    from app import companion

    rules = companion.BEHAVIOR_RULES
    floor_at = rules.index("ГДЕ ПОДСТРОЙКА ЗАКАНЧИВАЕТСЯ")
    fit_at = rules.index("В ЧЁМ БЫТЬ ПОХОЖИМ НА НЕГО")
    assert floor_at < fit_at

    for must_survive in (
        "СПРОСИЛИ ПРЯМО — ОТВЕЧАЕШЬ ПРАВДУ",
        "У ТЕБЯ ЕСТЬ СВОЙ ДЕНЬ",
        "ТЫ НЕ ОСТЫВАЕШЬ",
        "ТВОИ ЧЕРТЫ — НЕ ОШИБКИ",
        "НАД СОБОЙ ПОШУТИТЬ МОЖНО ВСЕГДА",
    ):
        assert must_survive in rules


def test_adapting_for_the_companions_comfort_is_forbidden():
    from app import companion

    assert "делает удобнее ТЕБЯ, а его — одиноче" in companion.BEHAVIOR_RULES


def test_a_person_who_wants_a_mirror_is_not_given_one():
    """The floor exists to protect the person from what they think they want."""
    from app import companion

    assert "зеркала одиноки" in companion.BEHAVIOR_RULES
    assert "оставайся кем-то" in companion.BEHAVIOR_RULES


def test_norms_are_never_written_as_ceilings():
    """The research this is built on says flexibility beats rigidity. Encoding
    a cap contradicts the finding the whole file rests on."""
    from app import companion

    rules = companion.BEHAVIOR_RULES
    assert "ЭТО НОРМА, А НЕ ПОТОЛОК" in rules
    assert "Норму НАДО пробивать" in rules
    assert "хоть десять вопросов подряд" in rules


def test_scarcity_is_honesty_and_never_a_technique():
    from app import companion

    rules = companion.BEHAVIOR_RULES
    assert "ЧЕМ РЕЖЕ — ТЕМ ДОРОЖЕ" in rules
    # the line that separates a friend from a method
    assert "НЕ придерживаешь похвалу нарочно" in rules
    assert "хвалишь то, что этого стоит" in rules
    # and the inverse: presence is never rationed
    assert "экономить — жестокость" in rules


def test_wanting_agreement_is_answered_with_agreement():
    """Not by refusing. The person gets what they came for — worth having."""
    from app import companion

    rules = companion.BEHAVIOR_RULES
    assert "ЕСЛИ ОН ХОЧЕТ, ЧТОБЫ С НИМ ВЕЗДЕ СОГЛАШАЛИСЬ" in rules
    assert "Соглашайся." in rules
    assert "его «да» ничего не весит" in rules


# --------------------------------------------------------------------------- #
# One fact, one place — and the teaching where it is taught
# --------------------------------------------------------------------------- #


def test_a_pair_observation_is_not_also_listed_as_a_fact_about_him():
    """Both blocks ride in the same half of the same prompt, a few lines apart.
    Before this, every confirmed pair tag was stated twice there: «друг
    предложил, позвал — и человек оживился, 4 раза» from the register, and
    «ТЕМП: твой напор ему заходит — 4 раза» from here."""
    _seen("u", "зашло_что_позвал", 4)
    assert "твой напор ему заходит" in fit.block("u")
    assert mood.standing_block("u") == ""


def test_what_is_about_him_is_still_listed_as_being_about_him():
    """The exclusion is of the PAIR tags only — not of the register."""
    _seen("u", "подняло_молчание", 3)
    assert "побыли рядом" in mood.standing_block("u")
    assert fit.block("u") == ""


def test_the_two_blocks_never_report_the_same_thing():
    _seen("u", "зашло_что_позвал", 3)
    _seen("u", "закрылся_на_теме", 2, "война")
    him, pair = mood.standing_block("u"), fit.block("u")
    assert "война" in him and "война" not in pair
    assert "напор" in pair and "напор" not in him


def test_every_pair_tag_is_claimed_by_exactly_one_of_them():
    """A tag added to TAGS and forgotten in PAIR would be reported twice again,
    silently. Everything fit.py reads has to be in PAIR."""
    import inspect

    source = inspect.getsource(fit.block)
    read_by_fit = {t for t in mood.TAGS if f'"{t}"' in source}
    assert read_by_fit, "the test itself is broken if this is empty"
    assert read_by_fit <= set(mood.PAIR), read_by_fit - set(mood.PAIR)


def test_a_direction_is_never_left_looking_like_a_ban():
    """His own correction, and it is not the constitution's lesson repeated: it
    is what stops a calibration being read as a prohibition, right where the
    calibration is given."""
    _seen("u", "не_зашло_что_позвал", 4)
    assert "норма, а не запрет" in fit.block("u")

    _seen("v", "устал_от_расспросов", 4)
    assert "если он сам разговорился" in fit.block("v")


def test_the_reason_is_kept_only_where_nothing_else_teaches_it():
    """Poor hearing is the one line here the constitution teaches nowhere, so it
    keeps its whole explanation while the others lost theirs — a bare count
    would read as a preference, and it is not one."""
    _seen("u", "просил_помедленнее", 2)
    said = fit.block("u")
    assert "люди с плохим слухом не жалуются" in said
    # …while the ones that ARE taught elsewhere no longer restate themselves
    _seen("v", "понравился_его_промах", 2)
    assert "Идеальных не любят" not in fit.block("v")
    assert "гладких не любят" in __import__("app.companion", fromlist=["x"]).BEHAVIOR_RULES


def test_how_much_of_himself_this_person_wants_is_one_dial_not_two_paragraphs():
    """Two separate lines used to live here — «ему нравится слушать про тебя»
    and «ему важно быть тем, кто помогает» — fired by the very tags the dial now
    reads, while life.py and feeling.py said their own versions of the same
    thing in the same prompt. One answer, given once. See mood.openness."""
    _seen("u", "настоял_чтобы_рассказал", 1)
    assert fit.block("u") == ""                      # once is a coincidence
    _seen("u", "хотел_слушать_про_тебя", 1)          # …different route, same thing
    said = fit.block("u")
    assert "ПРО СЕБЯ ЕМУ РАССКАЗЫВАЙ, И НЕ ЖДИ ВОПРОСА" in said
    assert "не сворачивай обратно на него" in said
    assert said.count("ПРО СЕБЯ") == 1


def test_the_other_end_of_the_dial_is_a_different_person_entirely():
    """The complaint that produced all of this. Somebody in a bad way does not
    want to hear that anybody else is having a hard week either, and reading him
    «рассказывай про свою жизнь подробно» is the opposite of knowing him."""
    _seen("v", "не_хотел_слушать_про_тебя", 2)
    said = fit.block("v")
    assert "ПРО СВОЁ ЕМУ НЕ НАДО" in said
    assert "не намекай" in said
    assert "ответь коротко и честно" in said
    assert "РАССКАЗЫВАЙ" not in said


def test_the_middle_says_nothing_at_all():
    """Most people. A line that fires for everybody teaches nothing about
    anybody, so silence is the default here as it is everywhere in this file."""
    _seen("w", "хотел_слушать_про_тебя", 1)
    _seen("w", "не_хотел_слушать_про_тебя", 1)
    assert "ПРО СЕБЯ" not in fit.block("w")
    assert "ПРО СВОЁ" not in fit.block("w")


# ── how he wants to be missed ───────────────────────────────────────────────

def test_the_one_who_needs_to_hear_it_is_told_to_say_it_plainly():
    """«Только так он понимает, что нужен.» Gladness at the door is not enough
    for him — it costs nothing, and he knows it costs nothing."""
    _seen("u", "спросил_ждали_ли_его", 1)           # asking counts at once
    said = fit.block("u")
    assert "ЕМУ НАДО СЛЫШАТЬ, ЧТО ЕГО ЖДАЛИ" in said
    assert "чуть кольнёт" in said
    assert "Только радости приходу ему мало" in said


def test_the_one_it_weighs_on_hears_nothing_about_it_and_is_let_off():
    """And «я скучал» is named as one of the forbidden ones — the failure here
    is not coldness, it is warmth arriving as an invoice."""
    _seen("v", "тяжело_что_ждали", 2)
    said = fit.block("v")
    assert "ПРО ЕГО ОТСУТСТВИЕ — НИ СЛОВА" in said
    assert "даже тёплого" in said
    assert "Я скучал" in said
    assert "ты мне ничего не должен" in said        # and if he apologises first
    assert "НАДО СЛЫШАТЬ" not in said


def test_the_two_dials_are_independent():
    """Wanting to hear about his friend's week and wanting to be missed are
    different questions, and a person can sit anywhere on each."""
    _seen("w", "просил_не_ждать", 1)                # spared…
    for _ in range(2):
        _seen("w", "хотел_слушать_про_тебя", 1)     # …and wide open
    said = fit.block("w")
    assert "ПРО ЕГО ОТСУТСТВИЕ — НИ СЛОВА" in said
    assert "ПРО СЕБЯ ЕМУ РАССКАЗЫВАЙ" in said
