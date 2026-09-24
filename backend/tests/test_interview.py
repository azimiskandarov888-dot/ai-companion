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
#
# Designed from what has to be known on day one (a second council, 2026-09-24:
# an information architect, the psychology of needs, the craft of the question).
# The rule for keeping a question: people differ on it, it changes the friend,
# learning it by trial and error would cost, and a stranger can answer it in a
# few words. Everything else is left to the re-reads, which run for the life
# of the friendship.


def test_every_fixed_question_has_a_job():
    """Eight, in this order: name; what fills the day (the friend's topic must
    NOT land here); what they love (it should); what is coming up this week
    (the only question that looks forward, and the friend's first «ну как
    прошло?»); country and age (safety); man or woman; a cat or a dog (a
    breather, and a living detail he will ask about)."""
    says = [s["say"] for s in _steps()]
    assert says == [
        "Как вас зовут?",
        "А день обычно чем занят?",
        "А для души что любите?",
        "А на этой неделе что намечается?",
        "А живёте где — в какой стране?",
        "Сколько вам лет, если не секрет?",
        "А вы мужчина или женщина?",
        "А кот или собака дома есть?",
    ]


def test_nothing_is_asked_that_nothing_uses():
    """«Как сегодня день?» fed nothing and was answered with the same words
    as «чем занимаетесь»; «горы или море», «чай или кофе», «сова», «лето или
    зима» fed nothing at all — and a tapped choice was read as a love, which
    is how «Море» became the owner's friend's topic."""
    says = " ".join(s["say"] for s in _steps()).lower()
    for gone in ("как сегодня день", "горы или море", "пьёте", "сова", "летом"):
        assert gone not in says, gone
    assert "выбор из двух кнопок" in reading._READING_SYSTEM


def test_no_question_invites_a_no():
    """Russian «-нибудь» works like English "any", and "any" gets "no": in a
    clinic, «что-то ещё?» cut patients' unmet concerns by 78% where «что-нибудь
    ещё?» did nothing (Heritage 2007). The owner's «ты с кем-нибудь этим
    делился?» got «nikto»."""
    fixed = " ".join(s["say"] for s in _steps())
    assert "нибудь" not in fixed
    assert "нибудь" not in " ".join(intake._QUESTIONS)


def test_the_pet_question_asks_about_a_pet_and_carries_the_turn():
    pet = next(s for s in _steps() if "кот или собака" in s["say"])
    assert pet["options"] == ["Кот", "Собака", "Нет"]


def test_fourteen_in_all():
    """Eight fixed and six from the interviewer — completion falls and late
    answers shorten with every question added."""
    assert len(_steps()) == 8
    assert intake.MAX_TURNS == 14 and len(intake._QUESTIONS) == 6


# ── the interviewer ─────────────────────────────────────────────────────────

def test_the_six_are_positions_not_topics():
    """A model told to cover topics follows a good thread and covers the first
    one three times — the owner's intake spent three questions on his startup.
    So each position carries its one question, word for word; the model may
    change only ты/вы, add one of the person's own words at the front, or go
    deeper if it was already answered."""
    assert [q.split("«")[1].split("»")[0] for q in intake._QUESTIONS] == [
        "А что любите, да давно не делали?",
        "А что у вас лучше всего получается?",
        "А с кем последний раз говорили по душам?",
        "А кто вас последний раз о чём-то просил?",
        "А когда последний раз было тяжело — что помогло?",
        "А о чём бы поговорить, да не с кем?",
    ]
    ask = intake._ASK_SYSTEM
    assert "Менять в них можно только три вещи" in ask
    assert "НИКОГДА НЕ ПОДСКАЗЫВАЙ ОТВЕТ" in ask


def test_each_question_is_about_what_happened_not_what_they_believe():
    """«What do you usually think about in the evening» returns what people
    believe about themselves, not what happened (Robinson & Clore 2002) — the
    owner's «не могу сказать, слишком много». People are asked about the LAST
    time; «по душам», not «всерьёз», because «всерьёз» drifted into business
    and got the owner's «ai»; and what lifted them is asked as what helped,
    not as which kind of help they would like — a list of options is copied,
    and past seventy the last option heard wins (Knäuper 1999)."""
    ask = intake._ASK_SYSTEM
    assert "«По душам», а не «всерьёз»" in ask
    assert "что его правда поднимает: не что он о себе думает, а что было" in ask
    assert "два разных одиночества, и одно другим не лечится" in ask


def test_there_is_one_real_question_and_it_is_required():
    asked = []

    async def fake(system_prompt, user_text, **kw):
        asked.append(user_text)
        return '{"reaction": "", "say": "ну?", "kind": "short", "enough": false}'

    import asyncio
    from app import brain
    real = brain.generate_text
    brain.generate_text = fake
    try:
        for answered in range(8, intake.MAX_TURNS):
            conv = [{"q": f"в{i}", "a": f"о{i}"} for i in range(answered)]
            asyncio.run(intake.next_question(conv))
    finally:
        brain.generate_text = real
    assert [a.count("Пора") for a in asked] == [0, 0, 0, 0, 0, 1]
    for n, text in enumerate(asked, 1):
        assert f"Сейчас вопрос {n} из 6" in text
    # Required, with the reason: in simulation the model ended both interviews
    # one question early — the earlier answers had shown WHOM there is nobody
    # to talk to, and only this question shows what about.
    assert "Он обязателен, даже если кажется, что всё уже ясно" in asked[-1]
    assert "С КЕМ ему не поговорить, а этот покажет — О ЧЁМ" in asked[-1]


def test_grief_does_not_end_the_interview_and_danger_is_answered_on_screen():
    """«Муж умер» used to be able to trip the stop meant for danger, and the
    widow was cut off exactly where it was hardest."""
    ask = intake._ASK_SYSTEM
    assert "ГОРЕ И ПОТЕРЯ — НЕ ПОВОД ЗАКАНЧИВАТЬ" in ask
    assert 'Ответь коротко и тепло (в "reaction" — его покажут)' in ask


def test_the_interviewers_last_words_are_shown_not_dropped():
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


def test_what_they_told_the_intake_reaches_their_friend():
    """Everything the intake learned used to reach only the reading and the
    writer, and the friend began knowing nothing but a name. Now the answers
    are read once and what was SAID is kept — facts, their people, the thing
    coming up this week as a follow-up — and never for a child."""
    from app import learn

    create = inspect.getsource(main.companion_create)
    assert "background_tasks.add_task(learn.from_intake, user_id, req.about)" in create
    assert create.index("young.forget(user_id)") < create.index("learn.from_intake")
    # Only what was said: an intake is not a visit, so no mood reading and no
    # observation of behaviour is taken from it.
    source = inspect.getsource(learn.from_intake)
    assert "_store_what_they_said" in source and "_store_what_was_watched" not in source


def test_what_the_reading_learns_over_weeks_reaches_every_turn():
    """«Главное» — what the person lacks — used to reach only the writer,
    once, so every re-read that corrected it over weeks of conversation
    reached nobody."""
    block = reading.standing_block({"verdict": "не с кем говорить о чувствах"})
    assert "Главное про него: не с кем говорить о чувствах" in block


def test_absence_counts_only_where_it_was_asked_about():
    """No question used to look forward, so every reading found «no future in
    his text» — for everybody. An absence is evidence only where a question
    made room for it."""
    assert "Но только там, где вопрос давал для этого место" in reading._READING_SYSTEM


def test_a_child_who_types_the_age_as_a_word_is_still_a_child():
    """«Двенадцать» used to be read as a grown-up, and a child's inner life
    kept — the one thing young.py exists to prevent."""
    from app import young

    assert young.band("мне двенадцать") == young.CHILD
    assert young.band("пятнадцать") == young.TEEN
    assert young.band("двадцать пять") == ""        # «пять» inside a grown-up's age
    assert young.band("семьдесят") == ""

