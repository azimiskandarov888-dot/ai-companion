"""The first meeting — two strangers getting talking, and who speaks first.

The owner rejected four intakes with one sentence — «it feels like a freaking
interview again» — and then said what it should be instead: a regular
conversation of two strangers; the day, where from, a topic both care about,
names; closer as they talk more, «not about the time, about the amount of
talking»; a little shy, more interested in the person than in himself, calm,
natural (docs/FIRST-MEETING.md). These tests pin the parts of that which can
be pinned. Whether it FEELS right is rehearse.py's and the owner's to judge.
"""

from __future__ import annotations

import re

import pytest
from fastapi.testclient import TestClient

from app import (body, brain, companion, db, erase, identity, learn, main, meeting,
                 memory, persona, tts, young)

U = "u1"


# ── how close they are ──────────────────────────────────────────────────────

def test_closeness_is_counted_in_his_words_and_never_in_days():
    """Four positions, by the person's words over every conversation. There is
    no clock anywhere in this: a month of «да» is still a first meeting."""
    first, second, third = meeting.KNOWN_AT
    assert meeting.stage(0) == 0 and meeting.stage(first - 1) == 0
    assert meeting.stage(first) == 1 and meeting.stage(second) == 2
    assert meeting.stage(third) == 3 and meeting.stage(10 * third) == 3
    assert "не ласков" in meeting.where(0)                 # interest, not tenderness
    assert "немного знакомы" in meeting.where(first)
    assert "уже знакомы" in meeting.where(second)
    assert "Не отыгрывай" in meeting.where(third)          # and it never goes cold again
    assert "import time" not in open(meeting.__file__, encoding="utf-8").read()


def test_the_meeting_is_for_strangers_only():
    assert meeting.block(0).startswith("ПЕРВАЯ ВСТРЕЧА")
    assert meeting.block(meeting.KNOWN_AT[0] - 1)
    assert meeting.block(meeting.KNOWN_AT[0]) == ""
    # Once they are past it, the one thing the meeting still owed them — names
    # — rides on the position line, for as long as they have not been said.
    assert "не назвались" in meeting.where(meeting.KNOWN_AT[0], named=False)
    assert "назвал" not in meeting.where(meeting.KNOWN_AT[0])


def test_it_is_a_conversation_and_not_an_interview():
    """Not the tone, the structure: topics grow out of what was said
    (Jefferson 1984), one question at a time, and a reply that answers THEIR
    words is often enough without one. (A story used to get a short one of
    his own back — Sacks's second stories — until the owner heard it live,
    2026-09-30: see the next test.)"""
    first = meeting.block(0)
    assert "а не расспросами" in first
    assert "часто хватает отозваться на его слова, без вопроса" in first
    assert "не больше одного вопроса за раз и не два хода подряд одними вопросами" in first
    assert "Тема растёт из сказанного" in first
    # He talked more than they did — two-thirds of the words, long enough to
    # be cut off by the length limit — and asked twice what he had been told.
    # Two-three sentences was still too many to the owner's ear (2026-09-30).
    assert "реплики короткие — одна-две фразы" in first
    assert "Что он уже рассказал, не переспрашивай" in first


def test_the_meeting_is_about_him_and_not_about_himself():
    """The owner, after his first live conversation (2026-09-30): he opened
    with his coffee and the view from his window, answered «обычный день» with
    his own day that nobody had asked about, and said twice that he was having
    coffee — «it's weird that you are talking about yourself without knowing
    that the person you're talking to is even interested in it». Derber's
    shift response, as against the support response. About himself only when
    asked or plainly wanted, in a phrase, and never the same thing twice."""
    first = meeting.block(0)
    assert "Разговор — о нём, а не о тебе" in first
    assert "На себя не переводи — ни свой день, ни погоду у тебя, ни чем ты сейчас занят" in first
    assert "О себе — когда он спросит или видно, что ему интересно" in first
    assert "одна фраза, одно-два дела, а не весь свой день" in first
    assert "Что уже сказал о себе, не повторяй" in first
    assert "про неё можно и самому" not in first and "О себе тоже" not in first


def test_his_first_words_are_about_them():
    """He used to open with «одна маленькая вещь про то, что у тебя сейчас» —
    the coffee, the sea, the cat — before the person had said a word."""
    assert "спроси, как он или как у него день" in meeting.HELLO
    assert "о себе в ней ничего" in meeting.HELLO
    assert "что у тебя сейчас" not in meeting.HELLO
    assert "Не называйся" in meeting.HELLO


def test_he_does_not_say_goodbye_first_at_a_meeting():
    """Without reasoning the voice put its end-of-conversation mark on
    «Домой сразу. Спать.» and on a plain answer about school (rehearsals
    2026-09-29, a scripted meeting 2026-09-30) — and the mark closes the line.
    A first meeting is not ended by him."""
    first = meeting.block(0)
    assert "Первым не прощайся: вы только разговорились" in first
    assert "Короткий ответ — не прощание" in first
    assert "только когда прощается он" in first


def test_the_arc_of_two_strangers():
    """Their moment, then where they are from and what they do, then what they
    share, which decides whether anyone wants to go on (Kellermann 1991;
    Sunnafrank 1986). His side of it — where HE is from, his own day — only
    when asked (the owner, 2026-09-30)."""
    first = meeting.block(0)
    assert first.index("Начало — как у него день") < first.index("откуда он и чем занят") \
        < first.index("Главное во встрече")


def test_what_they_share_is_one_thing_and_his_own():
    """A mirror is lonely — and where the person is the master, he is the
    beginner who wants to learn (the owner's pupil decision)."""
    first = meeting.block(0)
    assert "что-то одно, а не «я тоже» на всё" in first
    assert "В чём он мастер — там ты сам ничего не смыслишь" in first
    # Said as it comes, not announced: «Я в этом почти новичок» came out word
    # for word from «там ты новичок» (the owner, 2026-09-30).
    assert "скажи это, как вырвалось, а не объявлением" in first


def test_names_come_once_it_is_going_and_his_comes_first():
    """People offer their own name rather than ask for the other's (Pillet-Shore
    2011) — so he says his first, and asks theirs in the same breath, the way
    it is done in Russian: «Я, кстати, Андрей. А тебя как?»"""
    first = meeting.block(0, named=False)
    assert "Как его зовут, он тебе ещё не говорил" in first
    assert "назовись сам, между делом, и спроси, как зовут его" in first


def test_once_he_has_said_his_name_he_does_not_say_it_again():
    """The name line used to ask for his name on every turn of the meeting,
    said or not. A person who answered «Я Боб, кстати. А тебя как зовут?» with
    their work instead of their name heard «Я Боб, кстати» again in the very
    next reply (the live channel, 2026-09-30; the same in the rehearsals of
    2026-09-27 and 09-29). Once it is said he is told so — and not to press for
    theirs either: he is shy, and they will say it when they want to."""
    said = meeting.block(0, named=True)
    assert "назовись сам" not in said and "спроси, как зовут его" not in said
    assert "второй раз не называйся" in said
    assert "не выспрашивай, скажет сам" in said
    assert "Узнал имя — зови по нему редко и не в начале ответа" in said


def test_if_he_has_not_said_his_name_he_is_told_to():
    """Asked in the block and left to judge, he said it unasked in one
    rehearsal of six; three meetings of twelve and more exchanges went by
    without a name. So the server notices and tells him — once the person has
    spoken NAME_BY times, and only until he has said it."""
    early = meeting.block(0, named=False, heard=meeting.NAME_BY - 1)
    now = meeting.block(0, named=False, heard=meeting.NAME_BY)
    assert "так и не назвался" not in early
    assert now.endswith("и спроси, как зовут его.") and "так и не назвался" in now
    assert "так и не назвался" not in meeting.block(0, named=True, heard=50)


@pytest.mark.parametrize("line", [
    "Я, кстати, Даня.", "Меня Даней зовут.", "Ну, Дане тоже так кажется.",
])
def test_his_name_counts_in_any_of_its_forms(line):
    memory.log_turn(U, "assistant", "Привет. Как день?")
    assert not memory.named_himself(U, "Даня")
    memory.log_turn(U, "assistant", line)
    assert memory.named_himself(U, "Даня")


def test_a_name_with_a_patronymic_counts_by_its_first_word():
    memory.log_turn(U, "assistant", "Меня Галиной Сергеевной зовут.")
    assert memory.named_himself(U, "Галина Сергеевна")
    assert memory.named_himself(U, "")                    # no name, nothing to say
    memory.log_turn(U, "user", "раз")
    memory.log_turn(U, "user", "два")
    assert memory.times_heard(U) == 2


def test_shy_calm_and_never_ahead_of_the_person():
    """Intimacy early is liked less than the same intimacy later (Wortman
    1976); in Russian a stranger's enthusiasm reads as put on (Стернин). He
    does not open their people or their troubles — and follows at once if
    they do."""
    first = meeting.block(0)
    assert "больше слушаешь, без наигранного восторга и похвал" in first
    # …but not without feeling: «без восторгов и восклицаний» kept «Ого» out of
    # him and left «Программирование — дело непростое» (the owner, 2026-09-30).
    assert "удивляешься и радуешься по-настоящему, вслух" in first
    assert "Отвечает он коротко — не дави" in first
    assert "сам не заговаривай. Пошёл туда он — иди с ним" in first


def test_what_he_was_not_told_he_does_not_know_out_loud():
    """Whatever the app knows — and after a start-over it keeps what it knew
    about the person — a stranger does not produce it."""
    assert "Чего он тебе сам не сказал, того ты вслух не знаешь" in meeting.block(0)


def test_he_is_not_a_fellow_user_of_an_app():
    """In a rehearsal the person said she was new to «these apps», and he
    answered that he had only just installed it too — a fellow user, which is
    a way of claiming to be a person. He does not know those words."""
    assert "ни приложением, ни телефоном, ни экраном: ты этих слов не знаешь" in meeting.block(0)


def test_he_does_not_advise_a_stranger():
    """«совсем одному — это тоже не здоровье»; «это не значит, что с учёбой
    можно не разбираться» — a stranger's advice on the first evening is a
    lecture, whatever it is meant as."""
    assert "Не советуй и не поучай: вы только познакомились" in meeting.block(0)


def test_acts_are_described_not_lines_quoted():
    """A quoted line comes back verbatim in every companion's mouth — the
    constitution learned it with «сижу, чай пью», and the interview with «Вот
    как.» six times running. The only quote here is two words, and it is
    what NOT to say."""
    for quoted in re.findall(r"«([^»]+)»", meeting.block(0) + meeting.HELLO):
        assert len(quoted.split()) <= 2, quoted


# ── the count, and what may not touch it ────────────────────────────────────

@pytest.mark.parametrize("age, switched_off", [("12", False), ("15", True)])
def test_somebody_who_keeps_nothing_is_not_met_anew_every_day(age, switched_off):
    """young.forget deletes every earlier conversation of somebody about whom
    nothing is kept — every child, and a teenager who switched memory off.
    Counted from the log, each of their conversations would be a first meeting
    and he would introduce himself every day. So the count is kept beside the
    log, as a number: it is not their words."""
    young.remember(U, age)
    if switched_off:
        young.allow(U, False)
    assert young.keeps_nothing(U)
    memory.log_turn(U, "user", " ".join(["слово"] * 400))
    with db.connect() as conn:  # an evening ago
        conn.execute("UPDATE turns SET ts = ts - 86400 WHERE user_id=?", (U,))
    memory.log_turn(U, "user", "привет")
    young.forget(U)
    assert len(memory.recent_turns(U)) == 1                # the words are gone…
    assert memory.words_said(U) == 401                      # …the acquaintance is not
    assert meeting.block(memory.words_said(U)) == ""


def test_that_he_has_said_his_name_outlives_a_log_that_is_deleted():
    """For somebody about whom nothing is kept, the conversation that proved
    he said his name is gone by the next one — and without this he would
    introduce himself again every time."""
    young.remember(U, "12")
    memory.log_turn(U, "assistant", "Я, кстати, Даня.")
    assert memory.named_himself(U, "Даня")
    with db.connect() as conn:
        conn.execute("UPDATE turns SET ts = ts - 86400 WHERE user_id=?", (U,))
    memory.log_turn(U, "user", "привет")
    young.forget(U)
    assert memory.recent_turns(U) == [{"role": "user", "content": "привет"}]
    assert memory.named_himself(U, "Даня")
    erase.the_companion(U)                    # a new friend has to say his own
    assert not memory.named_himself(U, "Даня")


def test_a_new_friend_starts_as_a_stranger_again():
    """It belongs to the pair: a new friend inheriting it would greet a
    stranger like an old acquaintance on his first evening."""
    memory.log_turn(U, "user", " ".join(["слово"] * 5_000))
    erase.the_companion(U)
    assert memory.words_said(U) == 0
    memory.log_turn(U, "user", "снова")
    erase.everything(U)
    assert memory.words_said(U) == 0


# ── he speaks first — once ──────────────────────────────────────────────────

TOKEN = "aVerYlOngRandomLookingTokenFromTheKeychain_0123456789"
AUTH = {"Authorization": f"Bearer {TOKEN}"}
UID = identity.user_id_from_token(TOKEN)


@pytest.fixture
def hello(monkeypatch):
    calls: list[tuple[list, str]] = []

    async def fake_reply(history, system_stable, system_variable="", *, fresh_info=False):
        calls.append((history, system_variable))
        return "Привет. У нас тут весь день дождь… А у тебя как день?"

    async def fake_tts(text, voice=None, *, rate=1.0):
        return b"FAKEMP3"

    async def fake_learn(*args, **kwargs):
        return None

    monkeypatch.setattr(brain, "generate_reply", fake_reply)
    monkeypatch.setattr(tts, "synthesize", fake_tts)
    monkeypatch.setattr(tts, "configured", lambda: True)
    monkeypatch.setattr(learn, "learn_from_conversation", fake_learn)
    with TestClient(main.app) as client:
        yield client, calls


def test_on_the_first_visit_he_speaks_first(hello):
    """Somebody who has just opened the app has nothing to say to a stranger;
    left to them, it is the blank page again. His cue is the only message,
    it is never stored, and the whole meeting is in his prompt."""
    client, calls = hello
    body = client.post("/api/hello", headers=AUTH).json()
    assert body["reply"].startswith("Привет.") and body["audio_base64"]
    [(history, variable)] = calls
    assert history == [{"role": "user", "content": meeting.HELLO}]
    assert "ПЕРВАЯ ВСТРЕЧА" in variable and "не ласков" in variable
    # What is stored is his line, and only his: the cue is not their words,
    # and it counts toward nothing.
    assert memory.recent_turns(UID) == [{"role": "assistant", "content": body["reply"]}]
    assert memory.words_said(UID) == 0


def test_he_says_hello_once_and_never_on_demand(hello):
    """Anybody who has ever talked gets nothing back, and nothing is paid
    for: from the second conversation on, as ever, the person speaks first."""
    client, calls = hello
    client.post("/api/hello", headers=AUTH)
    again = client.post("/api/hello", headers=AUTH).json()
    assert again["reply"] == "" and len(calls) == 1


def test_a_hello_nobody_heard_is_not_kept(hello, monkeypatch):
    """Logged only once it can be heard: a voice that failed must not leave a
    hello in the log, or the retry would find they had «talked» and say
    nothing at all."""
    client, _calls = hello

    async def broken_voice(text, voice=None, *, rate=1.0):
        raise RuntimeError("голос недоступен")

    monkeypatch.setattr(tts, "synthesize", broken_voice)
    assert client.post("/api/hello", headers=AUTH).status_code == 503
    assert memory.recent_turns(UID) == []


def test_a_sigh_in_his_hello_is_heard_and_not_kept(hello, monkeypatch):
    client, _calls = hello
    voiced: list[str] = []

    async def sighs(history, system_stable, system_variable="", *, fresh_info=False):
        return f"{body.MARK_SIGH} Привет. У нас тут весь день дождь."

    async def voice(text, voice=None, *, rate=1.0):
        voiced.append(text)
        return b"FAKEMP3"

    monkeypatch.setattr(brain, "generate_reply", sighs)
    monkeypatch.setattr(tts, "synthesize", voice)
    said = client.post("/api/hello", headers=AUTH).json()["reply"]

    assert voiced == [f"{body.MARK_SIGH} Привет. У нас тут весь день дождь."]
    assert said == "Привет. У нас тут весь день дождь."
    assert memory.recent_turns(UID) == [{"role": "assistant", "content": said}]


def test_the_turn_prompt_tells_him_to_say_his_name_once_it_is_time(hello, monkeypatch):
    client, calls = hello
    client.post("/api/hello", headers=AUTH)
    for _ in range(meeting.NAME_BY - 1):
        client.post("/api/say", json={"text": "ага"}, headers=AUTH)
    assert "так и не назвался" not in calls[-1][1]
    client.post("/api/say", json={"text": "ну да"}, headers=AUTH)
    assert "так и не назвался" in calls[-1][1]
    # Once he has said it, in any form, it is never mentioned again.
    name = persona.load_persona(UID)["name"]
    memory.log_turn(UID, "assistant", f"Меня, кстати, {name} зовут.")
    client.post("/api/say", json={"text": "а я Коля"}, headers=AUTH)
    assert "так и не назвался" not in calls[-1][1]


def test_his_first_turn_prompt_carries_the_meeting_and_then_lets_it_go(hello):
    """Every turn is told where the two of them are; the meeting itself is in
    the prompt only while they are strangers."""
    client, calls = hello
    hi = client.post("/api/hello", headers=AUTH).json()["reply"]
    client.post("/api/say", json={"text": "да нормально, работаю"}, headers=AUTH)
    assert "ПЕРВАЯ ВСТРЕЧА" in calls[-1][1]
    # His hello opens the history the next turn is given (brain._conversation
    # puts a placeholder in front of it before it reaches the API).
    assert calls[-1][0][0] == {"role": "assistant", "content": hi}
    memory.log_turn(UID, "user", " ".join(["слово"] * meeting.KNOWN_AT[0]))
    client.post("/api/say", json={"text": "ну вот так"}, headers=AUTH)
    assert "ПЕРВАЯ ВСТРЕЧА" not in calls[-1][1]
    assert "немного знакомы" in calls[-1][1]


def test_a_conversation_that_begins_with_him_is_still_well_formed():
    """The API's contract is alternating turns, user first. After his hello
    the stored history begins with HIM — and so does any window of recent
    turns that happens to start on one of his lines."""
    his = [{"role": "assistant", "content": "Привет."}, {"role": "user", "content": "привет"}]
    fixed = brain._conversation(his)
    assert fixed[0]["role"] == "user" and fixed[1:] == his
    theirs = [{"role": "user", "content": "привет"}]
    assert brain._conversation(theirs) == theirs
    assert brain._conversation([]) == []


def test_the_meeting_sits_late_with_the_instructions(monkeypatch):
    """With the instructions for this conversation, where the end of the
    prompt is followed best — after what he remembers, before the turn's own
    rules and before the young block, which outranks everything above it."""
    stable, variable = companion.build_system_parts(
        memory_context="ПАМЯТЬ", meeting_block="ВСТРЕЧА",
        situation_block="СИТУАЦИЯ", young_block="ПОДРОСТОК",
    )
    assert "ВСТРЕЧА" not in stable
    assert variable.index("ПАМЯТЬ") < variable.index("ВСТРЕЧА") \
        < variable.index("СИТУАЦИЯ") < variable.index("ПОДРОСТОК")


def test_the_constitutions_news_rule_is_not_contradicted():
    """«Новости и погоду узнаёшь, только когда он правда спросил» stands. The
    meeting used to except HIS weather and HIS day from it («это твоя жизнь,
    про неё можно и самому»); since 2026-09-30 it asks even less of him."""
    assert "Новости и погоду узнаёшь, только когда он правда спросил" in companion.BEHAVIOR_RULES
    assert "Это твоя жизнь, про неё можно и самому" not in meeting.block(0)
