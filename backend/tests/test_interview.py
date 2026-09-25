"""The intake interview — what it finds out, how, and why.

Three rounds, all on 2026-09-24. The first two councils decided WHAT has to
be known on day one and the best wording for each; the rule for keeping a
question is that people differ on it, it changes the friend, learning it by
trial and error would cost, and a stranger can answer it in a few words.

The third round was the owner's, on first use: the app's eight fixed
questions felt dead. He answered «ничем» to «А день обычно чем занят?» and
the next question came as if nobody had listened. So every question is now
the interviewer's — a semi-structured interview: a list of targets, each with
a question close to the best wording, asked in the flow of the conversation
with room for one follow-up, and a server that keeps the list. Chatbots that
probe draw more informative, specific answers than fixed surveys (Xiao et al.
2020); follow-up questions are what make an asker liked (Huang et al. 2017).
"""

from __future__ import annotations

import inspect
from pathlib import Path

from app import intake, main, reading

IOS = Path(__file__).resolve().parents[2] / "ios" / "BobCompanion"


# ── what it has to find out ─────────────────────────────────────────────────

def test_every_target_has_a_job_and_nothing_else_is_asked():
    """Twelve, in this order, each for something downstream. What fills the
    day is asked so the friend's topic can land ANYWHERE BUT there; what they
    love is where it should; what is coming up is the only look forward and
    the friend's first «ну как прошло?»; country and age are safety; the six
    after them are what the reading and the writer build the friend from."""
    assert [t[0] for t in intake.TARGETS] == [
        "name", "days", "love", "coming_up", "country", "age",
        "miss", "strength", "confidant", "needed", "lifts", "closing",
    ]
    # Gone, because nothing downstream used them — and a tapped choice was
    # read as a love, which is how «Море» became the owner's friend's topic.
    asked = " ".join(q for _t, _w, q in intake.TARGETS).lower()
    for gone in ("горы или море", "пьёте", "сова", "летом", "кот"):
        assert gone not in asked, gone
    # «Как сегодня день?» came BACK, and why is the lesson: the first council
    # cut it because it fed nothing, and the owner missed it at once — right
    # after the name a person asks how you are, not what fills your days.
    # It feeds rapport, and rapport is what the rest is said into.
    assert dict((t[0], t[2]) for t in intake.TARGETS)["days"] == "Ну, как сегодня день?"


def test_the_wording_carries_the_signal():
    """«По душам», not «всерьёз» — «всерьёз» drifted into business and got the
    owner's «ai». What HELPED, not what helps — a case, not a belief about
    oneself (Robinson & Clore 2002). And never «-нибудь»: it works like «any»,
    and «any» gets «no» — in a clinic «что-то ещё?» cut unmet concerns by 78%
    where «что-нибудь ещё?» did nothing (Heritage 2007)."""
    by_id = {t[0]: t[2] for t in intake.TARGETS}
    assert by_id["confidant"] == "А с кем последний раз говорили по душам?"
    assert by_id["lifts"] == "А когда последний раз было тяжело — что помогло?"
    assert by_id["closing"] == "А о чём бы поговорить, да не с кем?"
    assert "нибудь" not in " ".join(t[2] for t in intake.TARGETS)
    assert "без «-нибудь»" in intake._ASK_SYSTEM


def test_gender_is_asked_only_when_it_is_not_already_clear():
    """Russian past tenses usually say it. When they have not, nothing
    downstream should have to guess — so it may be asked, once, after age."""
    assert intake.GENDER[0] == "gender"
    assert "только если по его словам ещё не ясно" in intake.GENDER[1]


# ── how it is asked ─────────────────────────────────────────────────────────

def test_every_question_is_the_interviewers_and_none_is_the_apps():
    """The app used to fire eight fixed questions before the interviewer was
    ever called, and none of them could react to an answer. Now it asks the
    server for every one; the first comes back instantly without a model."""
    screen = (IOS / "Screens" / "ScrollScreen.swift").read_text(encoding="utf-8")
    assert "warmUp" not in screen and "Step(say:" not in screen
    assert "Every question is the interviewer's" in screen
    # It hands the target of each question back, and reads country and age by it.
    assert screen.count("target: target))") == 2      # a tapped and a typed answer
    assert 'onFacts(answers(to: "country"), answers(to: "age"))' in screen
    client = (IOS / "Net" / "BackendClient.swift").read_text(encoding="utf-8")
    assert "var target: String? = nil" in client
    assert intake.opening()["say"] == "Как вас зовут?"


def test_it_is_a_conversation_first_and_a_list_second():
    """The owner, again, on the version that asked every question from a list:
    after his name it asked what he usually does, not how he was; after «пишу
    программу» it did not ask what the program was about. «It's like it wants
    to end the interview as fast as possible.» The list had been the master
    and the conversation its servant; now it is the other way round.

    What the research says a first conversation needs: small talk first — it
    builds trust (Bickmore & Cassell 2001); and follow-up questions, about
    what was just said, are the ones that make the asker liked, where a switch
    to the next topic does not (Huang et al. 2017)."""
    ask = intake._ASK_SYSTEM
    assert "ЭТО РАЗГОВОР, А НЕ АНКЕТА" in ask
    assert "После имени — как любой при знакомстве: обрадуйся и спроси, как у него сегодня день" in ask
    assert "следующий вопрос — про то, что он только что сказал" in ask
    assert "«Пишу программу» — «О, а про что она?»" in ask
    assert "«А вчера, например, как прошёл?»" in ask
    assert "Отзывайся живо и по-настоящему: удивись, обрадуйся, посочувствуй" in ask
    # The topics are a memo, not a script — taken up when they come up.
    assert "не по порядку и не словами анкеты, а когда к слову" in ask
    assert intake.MAX_PER_TOPIC == 3


def test_the_last_question_is_required_and_says_why():
    """Left to judge, the model ended simulated interviews one question early:
    the earlier answers had shown WHOM there is nobody to talk to — only this
    one shows what about."""
    source = inspect.getsource(intake.next_question)
    assert "последний и обязательный" in source
    assert "С КЕМ ему не поговорить" in source


def test_grief_does_not_end_the_interview_and_danger_is_answered_on_screen():
    """«Муж умер» used to be able to trip the stop meant for danger, and the
    widow was cut off exactly where it was hardest."""
    ask = intake._ASK_SYSTEM
    assert "ГОРЕ И ПОТЕРЯ — НЕ ПОВОД ЗАКАНЧИВАТЬ" in ask
    assert '"enough": true, "trouble": true' in ask


def test_the_interviewers_last_words_are_shown_not_dropped():
    screen = (IOS / "Screens" / "ScrollScreen.swift").read_text(encoding="utf-8")
    assert "THE LAST WORDS ARE SHOWN, NOT DROPPED" in screen
    assert screen.count("if parting { finish(); return }") == 2


def test_the_interviewer_is_chosen_for_its_ear():
    """It had been the middle model by default, never by comparison. Compared
    on the real prompt, every candidate kept the list; the one chosen is #1 on
    EQ-Bench 4 — the benchmark that measures reading what a particular person
    needs across a conversation — and was the fastest Claude model there."""
    from app import config

    assert config.INTAKE_MODEL == "claude-opus-5"


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

