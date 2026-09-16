"""Rules that arrive only when they apply.

The asymmetry that shapes every test here: a false positive costs a few hundred
tokens on one turn and nothing else, while a false negative means he cannot play
the game he was just asked to play. So the matching is deliberately loose, and
these tests are mostly about it being loose ENOUGH — with one exception, which
is the most important test in the file.
"""

from __future__ import annotations

import pytest

from app import companion, situations


# ── the ordinary turn ───────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "said",
    [
        "да ничего, чай пью",
        "внучка вчера приезжала, привезла пирог",
        "колено опять ноет",
        "спал плохо",
        "",
    ],
)
def test_an_ordinary_turn_carries_none_of_it(said):
    assert situations.block(said) == ""


# ── games ───────────────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "said",
    [
        "давай поиграем",
        "а сыграем во что-нибудь?",
        "загадай мне загадку",
        "давай в слова",
        "во что играть будем",
        "может в города?",
        "загадай число",
        "а пословицу продолжи",
    ],
)
def test_asking_to_play_brings_the_rulebook(said):
    out = situations.block(said)
    assert "СЕЙЧАС ПРО ИГРУ" in out
    assert "В слова" in out


def test_the_turn_where_she_simply_agrees_still_has_the_rules():
    """The one a short window would drop. «Ну давай» contains no game word
    whatsoever — the only record that a game is happening is the offer HE made a
    moment earlier, so his side of the history has to be read too."""
    history = [
        {"role": "user", "content": "да так, сижу"},
        {"role": "assistant", "content": "а давай сыграем в слова?"},
    ]
    assert "СЕЙЧАС ПРО ИГРУ" in situations.block("ну давай", history)


def test_a_game_in_progress_keeps_its_rules():
    history = [
        {"role": "user", "content": "давай в города"},
        {"role": "assistant", "content": "Астрахань"},
        {"role": "user", "content": "Новгород"},
        {"role": "assistant", "content": "Донецк"},
    ]
    assert "СЕЙЧАС ПРО ИГРУ" in situations.block("Курск", history)


def test_a_game_long_finished_lets_go():
    history = [{"role": "user", "content": f"реплика {i}"} for i in range(10)]
    history[0] = {"role": "user", "content": "давай в слова"}
    assert situations.block("а что у тебя нового?", history) == ""


def test_grief_is_never_answered_with_a_game():
    """THE test in this file. «Скучаю» looks like the most natural cue in the
    language for offering a game, and «скучаю по мужу» is grief. Answering that
    with «а давай сыграем в слова?» is the worst thing this module could cause,
    so the cue is not a trigger at any strength."""
    for said in (
        "скучаю по мужу",
        "так скучаю по нему, сил нет",
        "мне без него скучно очень",
        "скучно одной целыми днями",
    ):
        assert "СЕЙЧАС ПРО ИГРУ" not in situations.block(said)


# ── news and weather ────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "said",
    ["какая сегодня погода?", "что нового в мире?", "какие новости?"],
)
def test_asking_for_news_brings_the_manner(said):
    out = situations.block(said)
    assert "ПРО НОВОСТИ ИЛИ ПОГОДУ" in out
    assert "не ссылайся на источники" in out


def test_talking_about_the_weather_is_not_asking_for_it():
    """«Холодно сегодня» is conversation. Nobody asked him to look anything up,
    and the rules for handing over a forecast have no business being there."""
    assert "СЕЙЧАС ПРО НОВОСТИ" not in situations.block("холодно сегодня, дует")


def test_both_can_arrive_together():
    out = situations.block("какая погода? а потом давай сыграем в слова")
    assert "СЕЙЧАС ПРО ИГРУ" in out and "ПРО НОВОСТИ ИЛИ ПОГОДУ" in out


# ── what the constitution kept, and what it let go ──────────────────────────

def test_the_capability_stayed_behind_but_the_detail_did_not():
    """He must always know he CAN play — the offer is where a game starts, and
    a capability he only learns about once a game is under way can never begin
    one. The rules of «данетки» are a different matter."""
    rules = companion.BEHAVIOR_RULES
    assert "в слова" in rules
    assert "не навязывай" in rules
    assert "данетки" not in rules
    assert "по одному ходу за раз" not in rules


def test_the_constitution_stays_within_its_ceiling():
    """A ratchet, not a target. The reordering IS the removal: every section
    below the two that went moves up out of the 35–65% band where instructions
    are followed worst. It has caught real regrowth more than once.

    The ceiling has moved exactly once, from 23_000 to 26_000, and the reason
    is recorded here so the next move has to argue with it. An audit found the
    constitution was 22_901 characters about WARMTH and almost nothing about
    harm: four prohibitions, no rule anywhere about money, papers, fraud,
    impersonating a real person, or being talked out of its own guardrails. So
    the room bought was for a CATEGORY that was missing, not for more nuance —
    and the two deleted sections were ~2_400, which still does not fit in the
    headroom this leaves. Slow accretion of warmth rules fails this as before."""
    rules = companion.BEHAVIOR_RULES
    assert len(rules) < 26_000, f"{len(rules)} chars — the constitution regrew"


def test_what_was_removed_is_bigger_than_what_replaced_it():
    fired = situations.block("давай в слова, а какая погода?")
    assert len(fired) > 2_000, "the detail has to have actually survived"


# ── where it lands in the prompt ────────────────────────────────────────────

def test_it_arrives_late_where_instructions_are_followed_best():
    _stable, variable = companion.build_system_parts(
        persona_block="ТЫ — Гриша.",
        acquaintance="давно",
        memory_context="вы говорили про рыбалку",
        situation_block="СЕЙЧАС ПРО ИГРУ — вот чем ты играешь",
    )
    assert variable.index("ВАШИ ОБЩИЕ МОМЕНТЫ") < variable.index("СЕЙЧАС ПРО ИГРУ")


def test_it_never_lands_in_the_cached_half():
    stable, _variable = companion.build_system_parts(
        persona_block="ТЫ — Гриша.", situation_block="СЕЙЧАС ПРО ИГРУ"
    )
    assert "СЕЙЧАС ПРО ИГРУ" not in stable


def test_nothing_changes_on_a_turn_that_needs_nothing():
    with_empty = companion.build_system_parts(
        persona_block="ТЫ — Гриша.", situation_block="", acquaintance="давно"
    )
    without = companion.build_system_parts(
        persona_block="ТЫ — Гриша.", acquaintance="давно"
    )
    assert with_empty == without


def test_no_history_is_not_a_crash():
    assert situations.block("привет") == ""
    assert situations.block("привет", None) == ""
    assert situations.block("привет", []) == ""
    assert "СЕЙЧАС ПРО ИГРУ" in situations.block("давай в слова", [{}])


# ── what the triggers must NOT fire on ──────────────────────────────────────
#
# Both of these were measured firing on ordinary speech, and both are expensive
# when they do: the game rulebook puts 1,377 characters at the very end of the
# prompt — where instructions are followed best — and keeps them there for six
# turns; the news trigger attaches a search tool, switches to the slow model and
# takes the turn off the streaming path entirely.

@pytest.mark.parametrize("said", [
    "в детстве мы во дворе играли в футбол дотемна",
    "мы с женой объехали все города на юге",
    "внук играет на гитаре, третий год",
    "я на Олимпийские игры ездил в восьмидесятом",
    "врач сказал, это не игрушки",
    "люблю пословицы, мать много знала",
    "мне бы сыграть на гармони, да пальцы не те",
])
def test_ordinary_reminiscence_is_not_a_game(said):
    """The single most common thing this app's people say, and every one of
    these used to be answered with the rules of «Города»."""
    assert situations.block(said) == ""


@pytest.mark.parametrize("said", [
    "давай сыграем в слова",
    "а давай в города",
    "загадай мне загадку",
    "чья очередь?",
])
def test_an_actual_invitation_still_brings_the_rules(said):
    assert "В слова" in situations.block(said)


def test_accepting_an_offer_still_counts():
    """«Ну давай» carries no game word at all — the only record that a game is
    happening is the offer he made a moment earlier."""
    said = situations.block("ну давай", [{"role": "assistant",
                                          "content": "а давай сыграем в слова?"}])
    assert "В слова" in said


@pytest.mark.parametrize("said", [
    "температура тридцать восемь, вторые сутки",
    "у нас всю неделю погода дрянь",
    "прогноз у меня один — колено ноет, значит дождь",
    "высокий жар, встать не могу",
])
def test_talking_about_a_body_is_not_asking_for_the_forecast(said):
    """The one that mattered most: safety.py lists «высокий жар» as a danger
    sign, and the same words were being read as a question about the weather —
    with the turn taken off streaming, so the person waited longer for it."""
    from app import brain

    assert brain.wants_fresh_info(said) is False
    assert "НОВОСТИ" not in situations.block(said)


@pytest.mark.parametrize("said", [
    "какая сегодня погода?",
    "что нового в мире?",
    "новости смотрел?",
    "а погоду не знаешь на завтра",
])
def test_actually_asking_still_works(said):
    from app import brain

    assert brain.wants_fresh_info(said) is True


def test_the_news_block_no_longer_asserts_that_he_asked():
    """It said «он правда спросил», which on a false match is simply untrue —
    and the model has the turn in front of it and can see that it is."""
    said = situations.block("какая сегодня погода?")
    assert "он правда спросил" not in said
    assert "если не спрашивает" in said
