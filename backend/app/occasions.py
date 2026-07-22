"""A small calendar of dates worth mentioning.

The companion can bring these up in a morning greeting or spontaneously, and —
because each carries a short origin hint — it can tell the little story of *how*
such a day even came to be (a thing he specifically loves).

Keyed by "MM-DD". Extend freely. The `note` is a gentle hint for the brain, not
a script — it phrases things warmly in Russian itself.
"""

from __future__ import annotations

import datetime as _dt

# Real, widely-known dates (meaningful to an elderly Russian speaker) + a few
# light "fun" days he can smile at. Origin hints are soft prompts to discuss.
OCCASIONS: dict[str, dict[str, str]] = {
    "01-01": {
        "name": "Новый год",
        "note": "Самый тёплый семейный праздник. Можно вспомнить, как встречали Новый год в молодости.",
    },
    "01-07": {
        "name": "Рождество",
        "note": "Светлый праздник. Тёплые пожелания.",
    },
    "02-23": {
        "name": "День защитника Отечества",
        "note": "Можно тепло поздравить и расспросить о службе, если он служил.",
    },
    "03-08": {
        "name": "Международный женский день",
        "note": "Праздник весны. История: возник в начале XX века из женского движения за равные права; можно рассказать, как он появился, и вспомнить женщин в его жизни.",
    },
    "04-12": {
        "name": "День космонавтики",
        "note": "Полёт Гагарина в 1961 году. Многие помнят этот день лично — можно спросить, где он был тогда.",
    },
    "05-01": {
        "name": "Праздник Весны и Труда (Первомай)",
        "note": "Демонстрации, весна. Можно вспомнить первомайские шествия его молодости.",
    },
    "05-09": {
        "name": "День Победы",
        "note": "Очень важный и трогательный день. Отнестись с большим уважением и теплом; расспрашивать бережно.",
    },
    "09-01": {
        "name": "День знаний",
        "note": "Начало учебного года. Можно вспомнить школьные годы, детей и внуков-школьников.",
    },
    "10-01": {
        "name": "Международный день пожилых людей",
        "note": "Его день. Сказать тёплые слова о том, как он важен и любим.",
    },
    "12-31": {
        "name": "Канун Нового года",
        "note": "Предпраздничное настроение, надежды на новый год.",
    },
    # A light one, just for a smile — and to tell the story of how odd 'days' appear.
    "05-08": {
        "name": "Международный день разных носков (шуточный)",
        "note": "Шуточный день про непарные носки. Можно по-доброму посмеяться и порассуждать, как вообще люди придумывают такие забавные праздники.",
    },
}


def occasion_for(date: _dt.date | None = None) -> dict[str, str] | None:
    """Return today's occasion, if any."""
    date = date or _dt.date.today()
    return OCCASIONS.get(date.strftime("%m-%d"))
