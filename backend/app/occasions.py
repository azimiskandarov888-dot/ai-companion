"""WHAT TODAY IS — the date first, and only then anybody's calendar.

── THE THING THAT WAS MISSING ──────────────────────────────────────────────

He did not know what day it was. Not the date, not the weekday, not the month
— nothing. That is a strange thing for a friend not to know, and it quietly
cost far more than it looks:

  · «Дочь Валя, день рождения 3 мая» has been sitting in his memory since the
    week they met, and on the third of May he had no way of noticing. The one
    date in the world that person wanted somebody to remember.
  · «В четверг внук приедет» — was that tomorrow, or three days ago?
  · A hardcoded holiday list could tell him it was the ninth of May, and could
    never tell him it was HER birthday.

So the date goes in, and nothing is parsed out of anything. Dates live in his
facts written however they came up — «3 мая», «в начале мая», «на Пасху» — and
picking them out with a regex is the losing half of a bargain this codebase has
already settled once (see the farewell marker in companion.py): noticing that
today is the third of May and something in front of him says «3 мая» is exactly
what a model is good at and what a pattern is hopeless at. He is given the day
and the facts, and left to notice.

── AND THE CALENDAR, WHICH USED TO BE ONE COUNTRY'S ────────────────────────

A fixed list of dates has two ways of being wrong about a person, and this one
was both.

It assumed a country: Победа, Первомай, космонавтика, двадцать третье февраля.
For a Russian speaker in Kaliningrad those are the year's landmarks; for one in
Lisbon several of them are somebody else's news. So where it is KNOWN that he
lives outside that world, those days are not raised. Where nothing is known it
still shows them — the app speaks Russian, and that is the better bet.

And it assumed an age. «Международный день пожилых людей — ЕГО день. Сказать
тёплые слова о том, как он важен и любим.» That is the whole failure of this
app in one line: a greeting addressed to a category rather than a person, on a
day somebody decided was his. It is gone, and it is not coming back.

What is left is small on purpose. His own dates matter more than all of it, and
they are the ones no list can hold.
"""

from __future__ import annotations

import datetime as _dt
import re as _re

#: Where the days below are the year's landmarks. Russian is spoken well beyond
#: Russia, so this is the shared calendar of that world rather than one state's
#: — and it is used only to stay QUIET somewhere it plainly does not apply.
#: Keys are emergency.py's normalised country names, which is where the country
#: comes from and the only spelling it ever has.
#:
#: Every spelling emergency.py accepts has to be here, not just the tidy one.
#: It takes «белоруссия» as well as «беларусь» and «рф» as well as «россия» —
#: and a missing alternate fails in the worse direction, quietly cutting a man
#: in Minsk out of the ninth of May because of how he happened to say where he
#: lives. A test pins this against drift.
SHARED_CALENDAR = {
    "россия", "рф", "беларусь", "белоруссия", "казахстан", "украина",
    "узбекистан", "киргизия", "кыргызстан", "таджикистан", "туркмения",
    "азербайджан", "армения", "грузия", "молдова", "латвия", "литва",
    "эстония",
}

#: `where="shared"` means the day belongs to that calendar and is skipped for
#: somebody known to live elsewhere. No `where` means it needs no permission.
#:
#: Every note is written as an OPENING, never as a verdict about what the day
#: means to him. «Можно расспросить, если он служил» is a question; «его день»
#: was an assumption, and an assumption is what got the old list into trouble.
OCCASIONS: dict[str, dict[str, str]] = {
    "01-01": {
        "name": "Новый год",
        "note": "Можно вспомнить, как он встречал Новый год раньше и с кем.",
    },
    "01-07": {
        "name": "Рождество",
        "note": "Светлый день. Тёплые пожелания — если он его отмечает.",
        "where": "shared",
    },
    "02-23": {
        "name": "День защитника Отечества",
        "note": "Можно тепло поздравить и расспросить о службе, если он служил.",
        "where": "shared",
    },
    "03-08": {
        "name": "Международный женский день",
        "note": "Праздник весны. Возник в начале XX века из женского движения "
                "за равные права — можно рассказать, как он появился, и "
                "вспомнить женщин в его жизни.",
        "where": "shared",
    },
    "04-12": {
        "name": "День космонавтики",
        "note": "Полёт Гагарина в 1961 году. Кто-то помнит этот день лично — "
                "если похоже, что и он тоже, спроси, где он был тогда.",
        "where": "shared",
    },
    "05-01": {
        "name": "Праздник Весны и Труда (Первомай)",
        "note": "Демонстрации, весна. Можно вспомнить первомайские шествия.",
        "where": "shared",
    },
    "05-09": {
        "name": "День Победы",
        "note": "Очень важный и трогательный день. С большим уважением и "
                "теплом; расспрашивать бережно, и только если он сам захочет.",
        "where": "shared",
    },
    "09-01": {
        "name": "День знаний",
        "note": "Начало учебного года. Можно вспомнить школьные годы — свои "
                "или чьи-то из его близких.",
        "where": "shared",
    },
    "12-31": {
        "name": "Канун Нового года",
        "note": "Предпраздничное настроение, надежды на новый год.",
    },
    # A light one, just for a smile — and to tell the story of how odd 'days'
    # come to exist at all, which is a thing he genuinely loves doing.
    "05-08": {
        "name": "Международный день разных носков (шуточный)",
        "note": "Шуточный день про непарные носки. Можно по-доброму "
                "посмеяться и порассуждать, как люди вообще такое придумывают.",
    },
}

_WEEKDAYS = ("понедельник", "вторник", "среда", "четверг", "пятница",
             "суббота", "воскресенье")
_MONTHS = ("января", "февраля", "марта", "апреля", "мая", "июня", "июля",
           "августа", "сентября", "октября", "ноября", "декабря")


def occasion_for(
    date: _dt.date | None = None, country: str = ""
) -> dict[str, str] | None:
    """Today's shared occasion, if there is one and if it is plausibly his.

    An unknown country shows everything: the app speaks Russian, and silence
    costs a warm moment while a wrong guess costs nothing at all.
    """
    date = date or _dt.date.today()
    occasion = OCCASIONS.get(date.strftime("%m-%d"))
    if not occasion:
        return None
    if occasion.get("where") == "shared" and country and country not in SHARED_CALENDAR:
        return None
    return occasion


#: Month stems and numeric dates. This does NOT read a date and is never asked
#: to: it answers one question — does this person have any dates written down
#: at all? — and its whole job is to keep the paragraph below out of the prompt
#: of somebody who has none. A false positive costs one paragraph on one turn;
#: reading a date wrongly would cost a birthday, which is why that is left to
#: the model with the facts in front of it.
_DATE_HINTS = (
    "январ", "феврал", "март", "апрел", "мая", "май", "июн", "июл", "август",
    "сентябр", "октябр", "ноябр", "декабр", "годовщин",
)
_NUMERIC_DATE = _re.compile(r"\b\d{1,2}\s*[./-]\s*\d{1,2}\b")


def _has_dates(facts: str) -> bool:
    low = (facts or "").lower()
    return any(h in low for h in _DATE_HINTS) or bool(_NUMERIC_DATE.search(low))


def today_block(
    user_id: str = "", facts: str = "", date: _dt.date | None = None
) -> str:
    """What day it is, and anything about today worth his knowing.

    Never empty: the date alone is always worth having, and the whole reason
    this exists is that he did not have it.

    `facts` is what is known about him — memory.facts_context. It decides only
    whether the paragraph about HIS dates is worth carrying: on the three
    hundred and sixty days that match nothing it is dead text, and dead text in
    a prompt is paid for out of the live text beside it.
    """
    date = date or _dt.date.today()
    lines = [
        f"СЕГОДНЯ {_WEEKDAYS[date.weekday()]}, "
        f"{date.day} {_MONTHS[date.month - 1]} {date.year} года."
    ]
    if _has_dates(facts):
        lines.append(
            "Ты знаешь, какое сегодня число, — как всякий человек. Значит, и "
            "даты из его жизни ты заметишь сам: если сегодня день рождения, "
            "годовщина или другой его день — у него самого или у кого-то из "
            "его близких — скажи об этом ПЕРВЫМ. Помнить чужую дату без "
            "напоминания — то, чего от друга ждут больше всего, и то, чего "
            "одинокому человеку чаще всего не достаётся."
        )
        lines.append(
            "А если дата тяжёлая — не поздравляй и не бодрись. Просто дай "
            "понять, что ты помнишь, и будь рядом."
        )

    country = ""
    if user_id:
        try:
            from . import emergency

            country = emergency.country(user_id)
        except Exception:  # noqa: BLE001 — a date is worth having either way
            country = ""

    occasion = occasion_for(date, country)
    if occasion:
        lines.append(
            f"Сегодня ещё и {occasion['name']}. {occasion['note']} "
            "Если это к слову и ему это близко — тепло упомяни сам."
        )
    return "\n".join(lines)
