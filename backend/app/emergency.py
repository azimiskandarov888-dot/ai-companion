"""WHAT NUMBER TO TELL HIM TO DIAL.

safety.py used to say 103 — the ambulance in Russia — because that is where the
first users are. But loneliness is not a Russian condition, and Russian speakers
are spread across Israel, Germany, Kazakhstan, the United States, Canada. Telling
a man in Chicago to dial 103 while he is on the floor is not a smaller mistake
than missing the alarm altogether; it is the same mistake with extra steps.

Nobody is going to fill in a settings form. But a friend learns where you live
within about three conversations, because it is one of the first things people
say about themselves — and the extractor is already reading every exchange for
exactly that kind of fact. So the country arrives the way everything else about
him arrives: he mentions it, and it is written down.

── WHY 112 IS ALWAYS SAID TOO ─────────────────────────────────────────────

112 is the GSM standard emergency number. A handset will route it to local
emergency services in most of the world, including from a phone with no SIM, no
credit and no registered network. It is the one number that is never wrong, so
it is appended to every answer — including the ones where the local number is
known, because a man in a panic may misremember what he was told and 112 will
still reach somebody.

── WHY UNKNOWN IS NOT A CRISIS ────────────────────────────────────────────

Until he mentions it, the deployment's configured default stands
(config.EMERGENCY_NUMBER). That is the honest answer for a service whose users
are, today, mostly in one place — and the moment he says «да я всю жизнь в
Хайфе», it stops being a guess.
"""

from __future__ import annotations

import re
import time

from . import config, db

#: The universal one. Appended always — see the module docstring.
UNIVERSAL = "112"

#: Country → the number to call for an ambulance there. Keys are matched
#: against what the EXTRACTOR wrote, so they are the Russian names a person
#: actually says, lowercased, plus the obvious variants. This is not a
#: geography database and is not trying to be: it covers where Russian speakers
#: actually live, and everywhere else falls back to 112, which works.
_BY_COUNTRY: dict[str, str] = {
    # 103 — the CIS ambulance number
    "россия": "103",
    "рф": "103",
    "беларусь": "103",
    "белоруссия": "103",
    "казахстан": "103",
    "украина": "103",
    "узбекистан": "103",
    "киргизия": "103",
    "кыргызстан": "103",
    "таджикистан": "103",
    "туркмения": "103",
    "азербайджан": "103",
    "армения": "103",
    "молдова": "112",
    "грузия": "112",
    # 911
    "сша": "911",
    "америка": "911",
    "штаты": "911",
    "канада": "911",
    "мексика": "911",
    # 112 — the EU, where it is the primary number, not only a fallback
    "германия": "112",
    "франция": "112",
    "италия": "112",
    "испания": "112",
    "португалия": "112",
    "греция": "112",
    "польша": "112",
    "чехия": "112",
    "словакия": "112",
    "венгрия": "112",
    "румыния": "112",
    "болгария": "112",
    "хорватия": "112",
    "сербия": "112",
    "австрия": "112",
    "швейцария": "112",
    "бельгия": "112",
    "нидерланды": "112",
    "голландия": "112",
    "дания": "112",
    "швеция": "112",
    "норвегия": "112",
    "финляндия": "112",
    "эстония": "112",
    "латвия": "112",
    "литва": "112",
    "ирландия": "112",
    "исландия": "112",
    "турция": "112",
    "кипр": "112",
    # said differently, same effect
    "великобритания": "999",
    "англия": "999",
    "шотландия": "999",
    "израиль": "101",
    "австралия": "000",
    "новая зеландия": "111",
    "китай": "120",
    "япония": "119",
    "корея": "119",
    "южная корея": "119",
    "индия": "112",
    "таиланд": "1669",
    "вьетнам": "115",
    "бразилия": "192",
    "аргентина": "107",
    "оаэ": "998",
    "эмираты": "998",
}


#: Acronyms. Said as written or not at all: «рф» with an ending allowed would
#: reach «рука», and a wrong country here is a wrong ambulance number.
_ACRONYM = 3

#: A name's last letter decides how it bends. Anything else is a consonant.
_SOFT_LAST = "аеёиоуыэюяьй"

#: The endings a country's name actually takes in the answer to «где живёте?».
#: Kept as an exact set rather than "a couple of letters longer", because that
#: looser rule reads «Даниил» as «Дания» — same stem, one letter apart.
_ENDINGS_SOFT = frozenset((
    "", "а", "е", "и", "й", "о", "у", "ы", "ь", "э", "ю", "я",
    "ам", "ах", "ей", "ем", "ею", "ов", "ой", "ом", "ью", "ям", "ях", "ами", "ями",
))
_ENDINGS_HARD = frozenset(("", "а", "е", "у", "ы", "ов", "ом", "ам", "ах", "ами"))
#: «новая зеландия» → «в новой зеландии». Only ever reached as half of a
#: two-word name, so a loose adjective cannot match a country on its own.
_ENDINGS_ADJ = frozenset(("ая", "ой", "ую", "ое", "ые", "ым", "ым и"))


def _words(text) -> list[str]:
    return [w for w in re.split(r"[^\w-]+", str(text or "").lower()) if w]


def _same(word: str, name: str) -> bool:
    """Whether this word is that country, in whatever case it was said in.

    The table stores «Израиль»; a person says «в Израиле», and what they
    actually type is «Живу в Израиле, в Хайфе». So the names have to survive
    Russian case endings — but this is deliberately NOT morphology. It is the
    smallest rule that covers the handful of forms a country's name takes in
    the answer to one question: stem plus an ending off a list.

    Matching is on whole words, never on substrings. That is the same failure
    as everything else here: «Индия» found inside «Индианаполис» is a wrong
    country, and a wrong country is a man in Chicago being told to dial 103
    while he is on the floor.
    """
    if word == name:
        return True
    if len(name) <= _ACRONYM:
        return False
    if name.endswith("ая"):                          # «новая», «южная»
        stem, endings = name[:-2], _ENDINGS_ADJ
    elif name[-1] in _SOFT_LAST:
        stem, endings = name[:-1], _ENDINGS_SOFT
    else:
        stem, endings = name, _ENDINGS_HARD
    return word.startswith(stem) and word[len(stem):] in endings


def resolve(text) -> str:
    """The country named in what somebody just said, or "" if none is.

    Takes free text rather than a tidy name, because that is what arrives: the
    extractor writes «Израиль», but the person answering the intake question
    writes «в Израиле уже двадцать лет». Two-word names are tried before
    one-word ones at every position, so «южная корея» is never read as «корея».
    """
    words = _words(text)
    for i in range(len(words)):
        for span in (2, 1):
            window = words[i : i + span]
            if len(window) < span:
                continue
            for name in _BY_COUNTRY:
                parts = name.split()
                if len(parts) == span and all(
                    _same(w, p) for w, p in zip(window, parts)
                ):
                    return name
    return ""


def remember(user_id: str, country: str) -> None:
    """Note where he lives. Ignores anywhere this module does not recognise.

    Unrecognised is not an error and is not stored: an unknown country would
    make `known()` true while `numbers()` still fell back, which reads as
    "we know where he is" to anybody debugging a wrong number later.
    """
    key = resolve(country)
    if not key:
        return
    with db.connect() as conn:
        conn.execute(
            "INSERT INTO places (user_id, country, ts) VALUES (?,?,?)"
            " ON CONFLICT(user_id) DO UPDATE SET"
            "   country = excluded.country, ts = excluded.ts",
            (user_id, key, time.time()),
        )


def country(user_id: str) -> str:
    with db.connect() as conn:
        row = conn.execute(
            "SELECT country FROM places WHERE user_id=?", (user_id,)
        ).fetchone()
    return (row["country"] if row else "") or ""


def known(user_id: str) -> bool:
    return country(user_id) in _BY_COUNTRY


def numbers(user_id: str) -> str:
    """What to say out loud: the local number, then the one that always works.

    Never returns just one. A man in a panic may misremember which he was told,
    and 112 reaching somebody is worth more than the answer being tidy.
    """
    local = _BY_COUNTRY.get(country(user_id)) or config.EMERGENCY_NUMBER
    if local == UNIVERSAL:
        return UNIVERSAL
    return f"{local} или {UNIVERSAL}"
