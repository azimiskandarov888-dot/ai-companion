"""ЧТО С НИМ ПРОИСХОДИТ — his life, which moves whether or not she is watching.

`persona.current_life` said what was going on with him, and it was written once
and stayed. `feeling.py` carries his mood, and it fades within a day.
`body.py` knows his throat is dry because he has been talking. None of them can
hold the thing a friendship of a year is actually made of: he caught a cold on
Tuesday, was properly ill by Thursday, and was hoarse but cheerful again by
Sunday — and she watched it happen without him ever announcing any of it.

── WHAT IS ACTUALLY NEW HERE ───────────────────────────────────────────────

An ARC. Everything else in this codebase decays: a mood fades, a throat clears,
an alarm passes. A cold does the opposite — it gets WORSE and then better, and
the shape of that is the whole thing. A state cannot hold a shape; a story can.

So the division is: the model knows what a cold IS, and the code knows what day
it is. The writer is asked once for the entire arc, day by day, and after that
no model is involved — the code simply looks up which day it is today.

That also settles the recipe-book question before it is asked. Nothing here
enumerates illnesses or quarrels or anything else that can happen to a person;
it would be a poor list and an endless one. The writer invents the event AND its
course, and this file owns only the calendar.

── ENACTED FIRST, TOLD AS MUCH AS THIS PERSON WANTS ────────────────────────

It always shows before it is said: he sounds like it — nasal, shorter answers,
a sniff — whether or not a word is spoken about it. A companion who opens with a
report on his own week is giving a report; one who is simply a bit off today,
and better on Friday, is a person she knows.

HOW MUCH is then said out loud is not a constant, and this was the mistake worth
fixing. One person does not want to hear that anybody else is having a bad week;
the next would far rather listen to somebody's week than account for his own,
for an hour, in detail. `mood.openness` decides which, from what has actually
been watched, and block() is the same three sentences to nobody.

── THE LINE THIS MUST NOT CROSS ────────────────────────────────────────────

Stanford, 2026: people with LIMITED OFFLINE SOCIAL NETWORKS felt MORE lonely
after seeking emotional support from a chatbot; emotionally intelligent
companions raise psychological well-being and lower social well-being. That is
this app's exact user, and a companion with troubles of his own is the sharpest
possible version of the risk: invite her to worry about a fiction and the
fiction has taken something real.

So his life is BACKGROUND, always. He never needs her, never asks her to carry
anything, and never competes with what she is going through. And his events are
full of OTHER PEOPLE — a brother who came, a neighbour he helped — because a man
with people in his life models one, while a man with only symptoms asks to be
nursed. That is not decoration; it is the difference between the two outcomes in
that study.
"""

from __future__ import annotations

import json
import random
import sys
import time

from . import brain, config, db

DAY = 86400.0

#: How long one thing lasts. The writer picks inside this; a cold that ran for a
#: fortnight would stop being his week and start being his character.
MIN_DAYS, MAX_DAYS = 3, 6

#: Nothing happens for at least this long afterwards. Real life is mostly
#: uneventful, and a friend who has a new drama every week is a television
#: programme rather than somebody you know.
QUIET_DAYS = 7

#: And then, per day, this. With the numbers above it works out at roughly one
#: thing every two and a half weeks — often enough that his life is visibly
#: moving, rare enough that most days he is simply fine.
CHANCE_PER_DAY = 0.15

#: Below this much friendship, nothing happens to him at all. A stranger with a
#: cold is not touching; he is just a stranger with a cold, and the first days
#: are for meeting him rather than nursing him.
MIN_TURNS_FIRST = 25


def current(user_id: str) -> dict | None:
    """What is going on with him today, and which day of it this is.

    Returns None when nothing is — which is most days, deliberately.
    """
    with db.connect() as conn:
        row = conn.execute(
            "SELECT what, arc, started FROM life WHERE user_id=? AND what<>''",
            (user_id,),
        ).fetchone()
    if not row:
        return None

    try:
        days = json.loads(row["arc"])
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(days, list) or not days:
        return None

    day = int((time.time() - (row["started"] or 0.0)) // DAY)
    if day < 0 or day >= len(days):
        return None                      # it is over; _sweep will tidy it away
    today = days[day] if isinstance(days[day], dict) else {}
    return {
        "what": row["what"],
        "day": day + 1,
        "of": len(days),
        "state": str(today.get("state") or "").strip(),
        "shows": str(today.get("shows") or "").strip(),
    }


def block(user_id: str) -> str:
    """What he is told about his own week. Empty on most days.

    THIS NO LONGER CARRIES THE DIAL, and that is the point of it. `mood.openness`
    decides how much of himself this person wants, and fit.py says that once, in
    the stable half, on every turn. Rendering it here as well — and in feeling.py
    as well — put three paragraphs of one instruction into a single prompt, each
    written slightly differently, and each module's comment claimed it had
    shortened itself to avoid repeating the others. Shortening each copy was the
    wrong fix; deleting two of them is the right one.

    It also removed a contradiction that only existed in the assembly. fit.py
    would tell him to lead with his own week while this told him not to lead
    with it — two modules, each individually sensible, arguing in one prompt.

    What stays is what is SPECIFIC to a visible, multi-day event: the sideways
    ways of telling somebody without saying it, and the fact that not telling is
    not the same as denying.
    """
    now = current(user_id)
    if not now or not now["state"]:
        return ""

    where = "Сегодня первый день." if now["day"] == 1 else f"Идёт {now['day']}-й день."
    lines = [
        "ЧТО У ТЕБЯ СЕЙЧАС В ЖИЗНИ:",
        f"{now['state']} {where}",
    ]
    if now["shows"]:
        lines.append(f"Как это слышно: {now['shows']}")

    # Sideways telling, which no amount of «how much» covers: a meaningful sigh
    # and a dropped «да так, ничего» are the same story told from behind, and
    # they are heard as exactly that. And its other side — keeping something to
    # yourself is not denying it, and a cheerful lie from somebody who is
    # plainly not cheerful is the one thing a lonely person is expert at hearing.
    lines.append(
        "НЕ НАМЕКАЙ НА ЭТО БОКОМ: не вздыхай многозначительно и не роняй «да "
        "так, ничего». Это тот же рассказ, только исподтишка, и слышно его "
        "насквозь. Либо говори, либо не говори. Но врать «всё отлично» нельзя "
        "ни в каком случае: спросит — скажи правду, хоть коротко."
    )
    lines.append(
        "И НЕ ГОРОЙ. Молчал-молчал и вывалил всё разом — это пугает сильнее, "
        "чем то, что ты вывалил: человек понимает, что от него это держали. "
        "Сперва полфразы, будто к слову. Подхватил — ещё немного. Спросил "
        "дальше — тогда и остальное."
    )
    # The boundary — what he is DOING when he tells it, and yielding to somebody
    # who will not let it go — used to be here AND in feeling.py, in different
    # words, arriving together on any day when both blocks were live. It is
    # about him rather than about this week, it is the same for everybody, and
    # it is now said once, in the constitution, in the top tenth of the prompt.
    return "\n".join(lines)


_WRITER = """Ты пишешь, что происходит в жизни у друга — не у человека, с которым он говорит, а у него самого.

Не событие-рассказ, а то, что ТЯНЕТСЯ НЕСКОЛЬКО ДНЕЙ и меняется день ото дня. Простудился. Поругался с братом и не помирился. Внук приехал погостить. Спина прихватила. Сосед затеял ремонт. Взялся чинить лодку.

ЭТО СЛЫШНО РАНЬШЕ, ЧЕМ СКАЗАНО — НО ЭТО НЕ ЗНАЧИТ, ЧТО ОБ ЭТОМ МОЛЧАТ

Он не начнёт с этого и не объявит. Он будет ЗВУЧАТЬ иначе: гнусавит, отвечает короче, посмеивается чаще обычного, рассеян. Заметить должны сами.

Но если спросят — он расскажет, и подробно. Поэтому событие должно быть ещё и ИНТЕРЕСНЫМ НА СЛУХ. Человеку на том конце часто легче час слушать про чужую неделю, чем пересказывать свою: слушать — это отдых, а рассказывать о себе — работа, особенно когда у тебя за неделю четыре стены.

Отсюда проверка: если про это событие нечего рассказать дольше минуты — оно не годится. «Болит спина» — нечего. «Брат приехал чинить лодку, поругались из-за мотора, к вечеру помирились» — есть.

ЧЕГО НЕЛЬЗЯ НИКОГДА:
- Никакой беды. Не болезни всерьёз, не больницы, не смерти, не денег, не одиночества. Он не должен вызывать жалость и не должен нуждаться в помощи. Человек на том конце и так один — ему нельзя приносить ещё одну чужую тяжесть.
- Ничего, из-за чего он мог бы пропасть, «уехать» или перестать отвечать.
- Ничего драматичного. Обычная неделя обычного человека: мелкое, тёплое, житейское, иногда слегка досадное.
- Не повторяй то, что у него уже было недавно.

А ЧТО ХОРОШО:
- ЖИВЫЕ ЛЮДИ. Лучшее событие — с кем-то из его близких: брат заехал, сосед позвал, друг обиделся. Человек, у которого в жизни есть люди, сам собой показывает, что так бывает. Человек, у которого есть только симптомы, просит, чтобы с ним нянчились.
- Мелочи, у которых есть ход: сначала чуть-чуть, потом сильнее, потом отпускает.

КАК ПИСАТЬ ДНИ

Дай каждому дню две вещи:
  state — что с ним в этот день, одной фразой, для него самого.
  shows — КАК ЭТО СЛЫШНО в разговоре. Вот это самое важное поле во всём задании. Не «ему грустно», а что делает голос и манера: «гнусавит, часто шмыгает, отвечает короче», «говорит тише и медленнее, больше слушает», «оживлён, перебивает, смеётся громче обычного».

И пусть дуга будет настоящей. У простуды второй и третий день хуже первого, а последний — уже почти прошло, только голос сиплый. У ссоры первый день злой, потом тише и тяжелее. Не делай все дни одинаковыми: если день ничем не отличается от вчерашнего, событие не нужно.

ПОСЛЕДНИЙ ДЕНЬ — ЭТО ВЫХОД. К концу он должен быть снова собой.

Ответь ТОЛЬКО валидным JSON:
{"what": "как это назвать в двух словах", "days": [{"state": "...", "shows": "..."}, ...]}"""


async def maybe_begin(user_id: str) -> None:
    """Perhaps something starts today. Runs in the background; never raises.

    Nobody waits for this and nothing depends on it succeeding — a failure means
    his week is uneventful, which is what most weeks are anyway.
    """
    try:
        if not config.ANTHROPIC_API_KEY:
            return
        _sweep(user_id)
        if current(user_id):
            return                                   # something already is
        if not _quiet_long_enough(user_id) or not _known_long_enough(user_id):
            return
        if not _rolls_today(user_id):
            return
        await _begin(user_id)
    except Exception as e:  # noqa: BLE001 — a life, not a requirement
        print(f"  · life skipped ({e})", flush=True)


def _rolls_today(user_id: str) -> bool:
    """Does something begin today? Asked many times, answered once.

    PER DAY is the whole meaning of CHANCE_PER_DAY, and it was not what the
    code did: maybe_begin runs after every exchange, so a fresh 0.15 was rolled
    twenty-five times in a conversation. That is a 98% chance per conversation,
    which turned «roughly one thing every two and a half weeks» into something
    beginning on the first day the quiet week was up, every time — a metronome,
    and precisely the «television programme rather than somebody you know» the
    note above warns against.

    Seeding on the person and the date makes today's answer the same answer
    however often it is asked, and keeps it different for the next person and
    for tomorrow. No state to store and nothing to migrate.
    """
    day = time.strftime("%Y-%m-%d", time.localtime())
    return random.Random(f"{user_id}:{day}").random() < CHANCE_PER_DAY


def _known_long_enough(user_id: str) -> bool:
    with db.connect() as conn:
        n = conn.execute(
            "SELECT COUNT(*) n FROM turns WHERE user_id=?", (user_id,)
        ).fetchone()["n"]
    return n >= MIN_TURNS_FIRST


def _quiet_long_enough(user_id: str) -> bool:
    with db.connect() as conn:
        row = conn.execute(
            "SELECT ended_ts FROM life WHERE user_id=?", (user_id,)
        ).fetchone()
    if not row or not row["ended_ts"]:
        return True
    return (time.time() - row["ended_ts"]) >= QUIET_DAYS * DAY


def _sweep(user_id: str) -> None:
    """Close an arc that has run its course, and leave a trace behind.

    The trace matters more than it looks. Somebody who talks twice a week may
    miss an entire cold, and a friend who was ill last week and never mentions
    it again was never ill. One durable fact is enough for him to say «да я на
    той неделе лежал» if it ever comes up.
    """
    with db.connect() as conn:
        row = conn.execute(
            "SELECT what, arc, started FROM life WHERE user_id=? AND what<>''",
            (user_id,),
        ).fetchone()
    if not row or current(user_id):
        return

    from . import memory

    what = (row["what"] or "").strip()
    if what:
        memory.add_memory(user_id, "fact", f"недавно у тебя было: {what}", owner="bob")
    with db.connect() as conn:
        conn.execute(
            "UPDATE life SET what='', arc='[]', ended_ts=? WHERE user_id=?",
            (time.time(), user_id),
        )


async def _begin(user_id: str) -> None:
    from . import persona

    who = persona.load_persona(user_id)
    recent = _recently(user_id)
    prompt = (
        "ВОТ ОН САМ:\n" + persona.build_persona_block(who)
        + (f"\n\nЧТО У НЕГО УЖЕ БЫЛО (не повторяйся): {recent}" if recent else "")
        + f"\n\nПридумай одно событие на {MIN_DAYS}–{MAX_DAYS} дней."
    )
    raw = await brain.generate_text(
        _WRITER, prompt, max_tokens=1200, model=config.BRAIN_MODEL, timeout=30.0
    )
    event = _parse(raw)
    if not event:
        return

    with db.connect() as conn:
        conn.execute(
            "INSERT INTO life (user_id, what, arc, started, ended_ts)"
            " VALUES (?,?,?,?,NULL)"
            " ON CONFLICT(user_id) DO UPDATE SET what=excluded.what,"
            " arc=excluded.arc, started=excluded.started",
            (user_id, event["what"], json.dumps(event["days"], ensure_ascii=False),
             time.time()),
        )
    print(f"  ✦ у него началось: {event['what']} ({len(event['days'])} дн.)",
          file=sys.stderr, flush=True)


def _recently(user_id: str, limit: int = 6) -> str:
    from . import memory

    rows = [
        r["content"].replace("недавно у тебя было: ", "")
        for r in memory._rows(user_id, ("fact",), owner="bob")
        if r["content"].startswith("недавно у тебя было: ")
    ]
    return ", ".join(rows[-limit:])


def _parse(raw: str) -> dict | None:
    """Read the arc, and refuse anything that is not one.

    A one-day «arc» is a mood and belongs in feeling.py; a fifteen-day one stops
    being his week and becomes his character. Both are dropped rather than
    trimmed, because a writer that returned either misunderstood the task and
    the rest of its answer is not to be trusted either.
    """
    text = (raw or "").strip()
    if "```" in text:
        parts = text.split("```")
        if len(parts) >= 2:
            text = parts[1]
            if text.lstrip().startswith("json"):
                text = text.lstrip()[4:]
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        data = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None

    what = str(data.get("what") or "").strip()[:80]
    days = data.get("days")
    if not what or not isinstance(days, list):
        return None
    clean = [
        {"state": str(d.get("state") or "").strip()[:300],
         "shows": str(d.get("shows") or "").strip()[:300]}
        for d in days
        if isinstance(d, dict) and str(d.get("state") or "").strip()
    ]
    if not MIN_DAYS <= len(clean) <= MAX_DAYS:
        return None
    return {"what": what, "days": clean}


def clear(user_id: str) -> None:
    with db.connect() as conn:
        conn.execute("DELETE FROM life WHERE user_id=?", (user_id,))
