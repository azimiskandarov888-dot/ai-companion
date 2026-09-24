"""The intake interview — what it asks, in what order, and why.

Redesigned 2026-09-24 by a council of three independent reviews (the science
of eliciting what somebody lacks; an audit of every downstream need against
the question that feeds it; how each question feels to a lonely person of
any age), after the owner ran it on himself and the one thing he most needed
— somebody to talk to about feelings — never reached the page.

The frame is Funder's: accuracy needs the cue to EXIST and to REACH the
reader before any model can notice or use it. The interview is where cues
exist. Every question below has a job downstream, and the ones without one
are gone.
"""

from __future__ import annotations

import inspect
from pathlib import Path

import myself
from app import intake, main, reading

IOS = Path(__file__).resolve().parents[2] / "ios" / "BobCompanion"


def _steps():
    return myself.warm_up()


# ── the warm-up ─────────────────────────────────────────────────────────────

def test_what_they_love_is_asked_right_after_what_they_do():
    """The friend's topic must land on a love and never on the person's daily
    work. Left to the interviewer, a good thread about work used every
    question — so it is asked here, fixed, where nothing can skip it. An open
    «что», because «есть ли…» gets «нет»."""
    says = [s["say"] for s in _steps()]
    assert says.index("А для души что любите?") == says.index("А чем обычно занимаетесь?") + 1


def test_a_forced_choice_is_not_mistaken_for_a_love():
    """«Горы или море?» — the reading took the tap for a love, and «Море»
    became the owner's friend's topic. «Чай или кофе» went with it: five taps
    in a row is the questionnaire the design comments warn against."""
    says = " ".join(s["say"] for s in _steps())
    assert "горы или море" not in says and "Пьёте" not in says
    assert sum(1 for s in _steps() if s["options"]) == 4   # gender + three light ones
    assert "выбор из двух кнопок («сова», «лето») — не любовь" in reading._READING_SYSTEM


def test_the_pet_question_asks_about_a_pet():
    """«А дома у вас кто-нибудь есть — кот, собака?» asked first whether
    anybody at all was at home; a widow had to tap «Никого» among the light
    questions, and the reading read it as «lives alone»."""
    pet = next(s for s in _steps() if "кот или собака" in s["say"])
    assert pet["say"] == "А кот или собака дома есть?"
    assert pet["options"] == ["Кот", "Собака", "Нет"]


def test_the_backend_gets_six_questions_after_ten():
    """Ten warm-up answers and six from the interviewer: two about the life
    they love, three about their people, one real question. Sixteen rather
    than eighteen — completion falls and late answers shorten with every
    question added."""
    assert len(_steps()) == 10
    assert intake.MAX_TURNS == 16


# ── the interviewer ─────────────────────────────────────────────────────────

def test_the_people_rung_asks_about_the_last_time_and_tells_the_two_lonelinesses_apart():
    """Specific past episodes are reported more validly than «usually» (past
    behaviour questions .56 vs .45, Taylor & Small 2002). And «who is around»
    cannot tell «nobody there» from «people there, nobody to tell» — Weiss's
    social and emotional loneliness, which one does not cure the other — so
    the confidant is asked for on its own. The third question, who comes to
    him and for what, is where he is needed: reassurance of worth and the
    chance to care for someone, two of the six things relationships provide
    (Cutrona & Russell) and the two this friend can actually give back."""
    ask = intake._ASK_SYSTEM
    assert "ПРО ПОСЛЕДНИЙ РАЗ, А НЕ ПРО «ОБЫЧНО» И НЕ ПРО «ЕСЛИ БЫ»" in ask
    assert "с кем последний раз говорил всерьёз, по душам" in ask
    assert "кто приходит к нему самому и за чем" in ask
    assert "«люди есть, а сказать некому»" in ask


def test_there_is_one_real_question_not_two():
    """«Пора» used to be served at two left AND at one left, so the last slot
    was either wasted or a second «real question»."""
    asked = []

    async def fake(system_prompt, user_text, **kw):
        asked.append(user_text)
        return '{"reaction": "", "say": "ну?", "kind": "short", "enough": false}'

    import asyncio
    from app import brain
    real = brain.generate_text
    brain.generate_text = fake
    try:
        for answered in range(10, intake.MAX_TURNS):
            conv = [{"q": f"в{i}", "a": f"о{i}"} for i in range(answered)]
            asyncio.run(intake.next_question(conv))
    finally:
        brain.generate_text = real
    stages = ["close" if "Пора" in a else "people" if "про людей" in a else "life" for a in asked]
    assert stages == ["life", "life", "people", "people", "people", "close"]
    assert "«А о чём бы поговорить, да не с кем?»" in asked[-1]
    # Required, with the reason: in simulation the model ended both interviews
    # one question early — the people rung had shown WHOM there is nobody to
    # talk to, and only this question shows what about. With it, the simulated
    # fifteen-year-old said «что мне 15, а я только с кодом общаюсь, и что
    # нравится одна», and the widow «о муже… страшно одной ночью».
    assert "Он обязателен, даже если кажется, что всё уже ясно" in asked[-1]
    assert "С КЕМ ему не поговорить, а этот покажет — О ЧЁМ" in asked[-1]
    assert '"enough": true — когда на настоящий вопрос уже ответили, или если человеку плохо прямо сейчас' in intake._ASK_SYSTEM


def test_grief_does_not_end_the_interview_and_danger_is_answered_on_screen():
    """«Муж умер» used to be able to trip the stop meant for danger, and the
    widow — the person this app was first built for — was cut off exactly
    where it was hardest. And whatever was said to somebody in danger was
    never shown at all (see the iOS test below)."""
    ask = intake._ASK_SYSTEM
    assert "ГОРЕ И ПОТЕРЯ — НЕ ПОВОД ЗАКАНЧИВАТЬ" in ask
    assert 'Ответь коротко и тепло (в "reaction" — его покажут)' in ask


def test_the_interviewers_last_words_are_shown_not_dropped():
    """The app ended the intake the moment it was told to, before it ever
    read the reaction — so the words written for somebody who had just said
    something frightening never reached the screen, and the next thing they
    saw was «кого бы вы хотели встретить». Now they are shown, with one tap."""
    screen = (IOS / "Screens" / "ScrollScreen.swift").read_text(encoding="utf-8")
    assert "THE LAST WORDS ARE SHOWN, NOT DROPPED" in screen
    assert screen.count("if parting { finish(); return }") == 2


# ── what the answers are used for ───────────────────────────────────────────

def test_his_name_reaches_his_friend():
    """He gave it on the first line; the voice took the name from a
    deployment setting from the single-user days, so the friend written from
    his answers did not know what to call him."""
    story = "— Как вас зовут?\nazim\n\n— Ну, как сегодня день?\nнормально"
    assert intake.their_name(story) == "Azim"
    assert intake.their_name("— What's your name?\nDana") == "Dana"
    assert intake.their_name("просто текст о себе") == ""
    assert 'f"имя: {name}"' in inspect.getsource(main.companion_create)


def test_their_own_age_is_not_the_age_they_asked_for():
    """What the app sends as `age` is the person's OWN age. Passed on as the
    friend's age, it became law — «Кого он хотел бы встретить (закон):
    возраст: 74» — and every adult was given a friend their own age."""
    create = inspect.getsource(main.companion_create)
    assert "age=req.age" not in create
    assert "band=young.of(user_id)" in create


def test_the_wishes_screen_asks_what_the_friend_is_for():
    """A trait-shaped example («кто повидал жизнь») gets a trait back, and the
    commonest trait is «как я». «С кем можно…» gets what he would be FOR —
    and the wish stays theirs and stays law. «Хотелось», not «хотел»: the
    masculine addressed every woman as a man."""
    strings = (IOS / "Design" / "Strings.swift").read_text(encoding="utf-8")
    assert '"Кого бы тебе хотелось встретить?"' in strings
    assert '"Кого-то, с кем можно…"' in strings
    assert 'chipAgeText    = Phrase(ru: "Лет ", en: "About ")' in strings
