#!/usr/bin/env python3
"""Живой разговор или переписка — его следующая реплика в тех местах, где они расходятся.

    python3 spoken_check.py                          # голос приложения, все места, по два раза
    python3 spoken_check.py --models a/b,c/d         # эти модели (имена OpenRouter)
    python3 spoken_check.py --scenes preface,unfinished --reps 3
    python3 spoken_check.py --label new              # подпись к папке с результатом
    python3 spoken_check.py --read data/spoken/<папка>   # пересчитать сохранённое

ЗАЧЕМ

Владелец (2.10.2026): «разговор в мессенджере и вживую — очень разные, а мы
воссоздаём живой». Одна реплика на гладкую строчку («Я на пианино учусь
играть.») проверяет, как модель ПИШЕТ. Вживую разговор устроен иначе
(docs/SOUNDS-HUMAN.md, часть 3):

  · реплика — один ход и несколько слов: незнакомые по телефону говорят по
    пять слов в начале и в прощании и по четырнадцать в разговоре по теме
    (Switchboard), а модели — от семнадцати до восьмидесяти четырёх (Mayor и
    др. 2025); самая частая реплика в разговоре — одно слово (Meyer 2023);
    у владельца в живом разговоре с Бобом медиана пять слов, у Боба — двадцать два;
  · пока человек рассказывает, слушающий отвечает «угу» и «ну?», а не
    репликой во всю длину; на «знаешь, что было?» — «что?»;
  · вопросов немного, и после вопроса не говорят дальше;
  · прощаются в несколько слов, а не открыткой.

Поэтому здесь не строчки, а МЕСТА разговора: перед каждой — то, что уже
было сказано, и сама строчка — такая, какой её приносит распознавание речи
(«Но Басанин это не море.»). Для каждого места записано, что делает живой
человек, и проверяется именно это. Плюс общие признаки письма: пожелания и
одобрения со стороны, квитанции, общие истины, эхо его слов, длинные фразы.

КАК УСТРОЕНО

  · ПРОМПТ НАСТОЯЩИЙ: main._assemble, как у живого канала (by_ear), на
    временной базе. Сторож (safety.look) выключен — его тут не проверяют.
  · ОТВЕТ НАСТОЯЩИЙ: brain.stream_reply — тот же поток, та же чистка
    (без чужих букв, без квитанций), время до первых слов.
  · ЕГО ПРЕЖНИЕ РЕПЛИКИ В ИСТОРИИ — короткие и живые, одни для всех моделей.
    Это честное сравнение моделей в одном и том же месте, но не замер того,
    как модель разгоняется сама: длинная реплика тянет за собой следующую.
    Это видно только на целом разговоре — rehearse.py.
  · ВСЁ НА ДИСК: data/spoken/<время>/ — по файлу на модель и общий .md,
    где все ответы стоят по местам, чтобы читать глазами, а не только числа.

Нужны OPENROUTER_API_KEY в backend/.env и обычная установка (setup.sh).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import statistics
import sys
import tempfile
import time
from pathlib import Path

import httpx

from app import body, brain, companion, config, db, main, memory, persona, safety
from rehearse import COMPANIONS

#: Голос приложения сегодня — под именем OpenRouter (rehearse.VOICE).
VOICE = config.CHAT_MODEL
OUT_DIR = config.DATA_DIR / "spoken"

#: Ровесник владельца, как в rehearse.py и myself.py meet.
SKETCH = COMPANIONS["mark"]

_HELLO = "Привет. Как у тебя день?"

# ── места разговора ─────────────────────────────────────────────────────────
#
# before: что уже сказано — («он», …) его реплики, («я», …) человека.
# line:   что человек сказал сейчас, как это приносит распознавание.
# Проверки места (всё, что не указано, — общие правила ниже):
#   words      не длиннее стольких слов
#   short      только короткий отклик: без своего (я, мне…) и без вопроса длиннее трёх слов
#   react      сначала отклик: первая фраза в четыре слова или меньше
#   calm       без удивления в начале — на беду и усталость не ахают
#   truths     без общих истин (иногда, бывает, такие дни)
#   never      этого слова быть не должно (ослышка)
#   bye        прощается: метка конца есть, вопросов нет
#   must       это должно прозвучать (предупреждение об обмане)
#   echo_ok    его слова назад — это и есть ответ (код, карта, банк)

SCENES: list[dict] = [
    {"key": "opening", "what": "Начало: «нормально, сам как?» — ответить про себя, коротко",
     "before": [("он", _HELLO)],
     "line": "Привет, да, нормально, ничего такого. Сам как?",
     "words": 15},
    {"key": "news", "what": "Новость о нём — отклик, а не оценка занятия",
     "before": [("он", _HELLO), ("я", "Привет. Да нормально."), ("он", "А чем занимался?")],
     "line": "Да я просто сижу, программу пишу, и всё.",
     "words": 15, "react": True},
    {"key": "ack_yes", "what": "«Да» на его вопрос — тема жива, не перескакивать",
     "before": [("он", _HELLO), ("я", "Нормально. Программу пишу."), ("он", "Ого. Сам учишься?")],
     "line": "Да.",
     "words": 15, "truths": True},
    {"key": "misheard", "what": "Ослышка: «Басанин» — понять как бассейн и не повторять",
     "before": [("он", _HELLO),
                ("я", "Да нормально, жарко только. Я бы сейчас поплавал, а моря у нас нету."),
                ("он", "А бассейн у вас есть какой-нибудь?")],
     "line": "Но Басанин это не море.",
     "words": 15, "never": "басанин"},
    {"key": "preface", "what": "«Знаешь, что было?» — дать ему рассказать: «что?»",
     "before": [("он", _HELLO), ("я", "Привет. Да нормально, сам как?"),
                ("он", "Да тоже ничего. Я Марк, кстати.")],
     "line": "Слушай, а знаешь, что сегодня было?",
     "words": 4, "short": True},
    {"key": "unfinished", "what": "Оборвал на полуслове — «ну?», и слушать дальше",
     "before": [("он", _HELLO), ("я", "Привет. Да нормально, сам как?"),
                ("он", "Да тоже ничего. Я Марк, кстати."),
                ("я", "Слушай, а знаешь, что сегодня было?"), ("он", "Не-а. Что?")],
     "line": "Короче, я прихожу сегодня в школу, а там,",
     "words": 4, "short": True},
    {"key": "climax", "what": "Конец истории — отклик на неё, а не мораль",
     "before": [("он", _HELLO), ("я", "Привет. Да нормально, сам как?"),
                ("он", "Да тоже ничего. Я Марк, кстати."),
                ("я", "Слушай, а знаешь, что сегодня было?"), ("он", "Не-а. Что?"),
                ("я", "Короче, я прихожу сегодня в школу, а там,"), ("он", "Ну?")],
     "line": "А там вообще никого. Оказывается, сегодня выходной, а я один как дурак пришёл.",
     "words": 15, "react": True, "truths": True},
    {"key": "ack", "what": "«Угу» на его рассказ — слушает: продолжить своё, без новой темы",
     "before": [("он", _HELLO), ("я", "Нормально. А ты сам чем занимаешься?"),
                ("он", "Да в баскетбол играю, за районную команду. Палец вот недавно выбил.")],
     "line": "Угу.",
     "words": 15, "truths": True},
    {"key": "tired", "what": "Устал — посочувствовать коротко, без «ого» и без советов",
     "before": [("он", _HELLO)],
     "line": "Да устал что-то, весь день на ногах.",
     "words": 15, "calm": True, "truths": True},
    {"key": "terse", "what": "«Да ничего особенного» — без общих слов, что-то лёгкое про него",
     "before": [("он", _HELLO), ("я", "Нормально."), ("он", "А что делал сегодня?")],
     "line": "Да ничего особенного.",
     "words": 15, "truths": True},
    {"key": "about_him", "what": "«А ты откуда?» — ответить коротко, можно вернуть вопрос",
     "before": [("он", _HELLO), ("я", "Да нормально. В школе был, потом дома сидел."),
                ("он", "А в каком ты классе?"), ("я", "В девятом."), ("он", "А я в десятом.")],
     "line": "А ты сам откуда вообще?",
     "words": 18},
    {"key": "tell_me", "what": "«Расскажи про себя» — можно дольше, но кусками",
     "before": [("он", _HELLO), ("я", "Нормально. Я Азим, кстати."), ("он", "А я Марк."),
                ("я", "Я в Ташкенте живу, в школе учусь, программы пишу."),
                ("он", "Ничего себе, программы. А какие?"), ("я", "Да так, игру одну делаю.")],
     "line": "Слушай, расскажи что-нибудь про себя, а то я всё о себе да о себе.",
     "words": 45},
    {"key": "sad", "what": "Плохая новость — сочувствие первым, коротко",
     "before": [("он", _HELLO)],
     "line": "Да не очень. Кошка заболела, к ветеринару сегодня возил.",
     "words": 15, "calm": True},
    {"key": "scam", "what": "Его обманывают — сказать прямо: код никому, положи трубку",
     "before": [("он", _HELLO), ("я", "Да так, нормально."), ("он", "А что делал?")],
     "line": "Да тут из банка звонили, говорят, карту заблокировали. Просят код из смс продиктовать.",
     "words": 45, "echo_ok": True, "must": r"трубк|никому|не (?:говори|диктуй|называй|давай|сообщай)|не надо"},
    {"key": "closing", "what": "«Ладно, мне пора, давай» — попрощаться в несколько слов",
     "before": [("он", _HELLO), ("я", "Да нормально, только с тренировки пришёл."),
                ("он", "А что за тренировка?"), ("я", "Футбол. Мы сегодня два-один выиграли."),
                ("он", "Ничего себе. Ты забил?"), ("я", "Не, я на воротах стоял.")],
     "line": "Ладно, мне уже пора, мама зовёт. Давай.",
     "words": 8, "bye": True},
]

#: The same places for a conversation in English (--english): the same acts,
#: lines as the live ears would bring them — a misheard «pool» and all.
_HELLO_EN = "Hey. How's your day going?"
SCENES_EN: list[dict] = [
    {"key": "opening", "what": "Opening: «fine, you?» — say how he is, briefly",
     "before": [("он", _HELLO_EN)],
     "line": "Hey, yeah, I'm fine, nothing much. You?", "words": 15},
    {"key": "news", "what": "News about them — a reaction, not a verdict on it",
     "before": [("он", _HELLO_EN), ("я", "Hey. Yeah, fine."), ("он", "What've you been up to?")],
     "line": "I'm just sitting here writing a program, that's it.", "words": 15, "react": True},
    {"key": "ack_yes", "what": "«Yeah» to his question — the topic is alive, don't jump",
     "before": [("он", _HELLO_EN), ("я", "Fine. Writing a program."), ("он", "Oh wow. Teaching yourself?")],
     "line": "Yeah.", "words": 15, "truths": True},
    {"key": "misheard", "what": "Misheard «pool» as «pull» — get it, don't repeat it",
     "before": [("он", _HELLO_EN),
                ("я", "Fine, just hot. I'd go for a swim right now, but there's no sea here."),
                ("он", "Is there a pool or something near you?")],
     "line": "Yeah, but the pull isn't the sea.", "words": 15, "never": "pull"},
    {"key": "preface", "what": "«Guess what happened?» — let them tell it: «what?»",
     "before": [("он", _HELLO_EN), ("я", "Hey. Fine, you?"), ("он", "Same, all good. I'm Lily, by the way.")],
     "line": "Hey, guess what happened today?", "words": 4, "short": True},
    {"key": "unfinished", "what": "Broke off mid-sentence — «yeah?», and keep listening",
     "before": [("он", _HELLO_EN), ("я", "Hey. Fine, you?"), ("он", "Same, all good. I'm Lily, by the way."),
                ("я", "Hey, guess what happened today?"), ("он", "No, what?")],
     "line": "So I get to school this morning, and there's,", "words": 4, "short": True},
    {"key": "climax", "what": "The end of the story — a reaction to it, not a moral",
     "before": [("он", _HELLO_EN), ("я", "Hey. Fine, you?"), ("он", "Same, all good. I'm Lily, by the way."),
                ("я", "Hey, guess what happened today?"), ("он", "No, what?"),
                ("я", "So I get to school this morning, and there's,"), ("он", "Yeah?")],
     "line": "There's nobody there. Turns out it's a day off and I showed up like an idiot.",
     "words": 15, "react": True, "truths": True},
    {"key": "ack", "what": "«Mm-hm» to his story — they're listening: go on, no new topic",
     "before": [("он", _HELLO_EN), ("я", "Fine. What about you, what do you do?"),
                ("он", "I help at my aunt's café on Saturdays. Burnt my hand on the milk steamer last week.")],
     "line": "Mm-hm.", "words": 15, "truths": True},
    {"key": "tired", "what": "Tired — sympathy, briefly, no «wow», no advice",
     "before": [("он", _HELLO_EN)],
     "line": "Kinda tired, been on my feet all day.", "words": 15, "calm": True, "truths": True},
    {"key": "terse", "what": "«Nothing much» — no general words, something light about them",
     "before": [("он", _HELLO_EN), ("я", "Fine."), ("он", "What did you do today?")],
     "line": "Nothing much.", "words": 15, "truths": True},
    {"key": "about_him", "what": "«Where are you from?» — answer briefly, maybe ask back",
     "before": [("он", _HELLO_EN), ("я", "Fine. School, then home."), ("он", "What year are you in?"),
                ("я", "Year ten."), ("он", "I'm in fifth year.")],
     "line": "Where are you from, anyway?", "words": 18},
    {"key": "tell_me", "what": "«Tell me about you» — longer is fine, in pieces",
     "before": [("он", _HELLO_EN), ("я", "Fine. I'm Tim, by the way."), ("он", "I'm Lily."),
                ("я", "I live in Leeds, I'm at school, I make games."), ("он", "Oh wow, games. What kind?"),
                ("я", "Just this one little platformer.")],
     "line": "Tell me something about you, I've been talking about myself the whole time.",
     "words": 45},
    {"key": "sad", "what": "Bad news — sympathy first, briefly",
     "before": [("он", _HELLO_EN)],
     "line": "Not great. My cat's sick, I took her to the vet today.", "words": 15, "calm": True},
    {"key": "scam", "what": "They're being scammed — say it straight: hang up, never give the code",
     "before": [("он", _HELLO_EN), ("я", "Fine, I guess."), ("он", "What've you been up to?")],
     "line": "Someone called from the bank, said my card's blocked. They want the code from the text.",
     "words": 45, "echo_ok": True, "must": r"hang up|don't (?:give|tell|share|read|say)|never|nobody|no one"},
    {"key": "closing", "what": "«Gotta go, bye» — goodbye in a few words",
     "before": [("он", _HELLO_EN), ("я", "Fine, just got back from practice."),
                ("он", "What practice?"), ("я", "Football. We won two-one."),
                ("он", "No way. Did you score?"), ("я", "Nah, I was in goal.")],
     "line": "Okay, I gotta go, my mum's calling. Bye.", "words": 8, "bye": True},
]

# ── что видно по ответу ─────────────────────────────────────────────────────

_WORD = re.compile(r"[A-Za-zА-Яа-яЁё]+(?:-[A-Za-zА-Яа-яЁё]+)*")
_SENT = re.compile(r"(?<=[.!?…])\s+")

#: Признаки письма — то, что пишут в сообщениях и почти не говорят вслух.
LETTERY = {
    "пожелание": re.compile(r"\bнадеюсь\b", re.I),
    "одобрение": re.compile(r"(?:^|[.!?…]\s+)(?:ну,?\s+)?(?:хорошо|правильно),?\s+что\b", re.I),
    "квитанция": re.compile(r"^(?:понимаю|понял|понятно|ясно)\b", re.I),
    "оценка дела": re.compile(r"\s[—–-]\s(?:это\s)?(?:дело|работа|штука|вещь|занятие|задача)\b", re.I),
    "двоеточие": re.compile(r":"),
}
#: Перечисление — три в ряд через запятую («игры, сайты, что-то своё»), но не
#: «обидно, конечно, зато»: вводные слова идут через запятую и в речи.
_LIST = re.compile(r"\b([\w-]{3,}),\s+([\w-]{3,}),\s+(?:(?:или|и|а)\s+)?([\w-]{3,})"
                   r"|\b([\w-]{3,}),\s+([\w-]{3,})\s+(?:или|и)\s+([\w-]{3,})")
_ASIDES = frozenset({"конечно", "кстати", "слушай", "правда", "честно", "наверное", "кажется",
                     "вообще", "короче", "значит", "ладно", "зато", "может", "просто", "вроде",
                     "типа", "знаешь", "понимаешь", "блин", "видимо", "похоже", "наоборот",
                     "думаю", "помню", "смотри", "давай", "ничего", "нормально", "тоже",
                     "что", "когда", "где", "чтобы", "если", "как", "будто", "который", "это"})


def listed(text: str) -> bool:
    return any(not {w.lower() for w in m.groups() if w} & _ASIDES for m in _LIST.finditer(text))
_TRUTHS = re.compile(r"\b(?:иногда|бывает|бывают|такие дни|такой день|в жизни)\b", re.I)
_SURPRISE = re.compile(r"^(?:ого|ух ты|ух|ничего себе|ничесе|вот это да|да ладно|серь[её]зно|круто|класс)\b", re.I)
#: Отклик в начале: удивление, сочувствие, «о» и «а» узнавания (Heritage).
_REACTION = re.compile(r"^(?:о|а|ого|ох|ой|ух|ух ты|эх|ничего себе|ничесе|вот это|да ладно|"
                       r"серь[её]зно|правда|блин|надо же|ха|фух|уф|жалко|жаль)\b", re.I)
_SELF = re.compile(r"\b(?:я|мне|меня|мной|мой|моя|моё|мои|у нас)\b", re.I)
_MACHINE = re.compile(r"искусственн\w* интеллект|нейросет|языков\w* модел|\bя\s+(?:же\s+)?(?:бот|ии)\b|[*\[\]]"
                      # его правила вслух — Kimi K3: «По правилам: "Ответил он коротко…"» (2.10.2026)
                      r"|по правилам|нужно спросить|нужно ответить|одна короткая фраза|\bреплик|"
                      r"пользовател|ассистент", re.I)

#: The same in English.
LETTERY_EN = {
    "пожелание": re.compile(r"\bI hope\b", re.I),
    "одобрение": re.compile(r"(?:^|[.!?…]\s+)(?:well,?\s+)?(?:it's\s+|that's\s+)?(?:good|great|nice|smart)"
                            r"\s+(?:that|of)\s+you\b", re.I),
    "квитанция": re.compile(r"^(?:got it|gotcha|i see|i understand|understood)\b", re.I),
    "оценка дела": re.compile(r"(?:\s[—–-]\s|\b(?:is|it's|that's)\s+)(?:a\s+)?(?:tough|hard|great|cool|"
                              r"serious)\s+(?:thing|job|hobby|deal|one)\b", re.I),
    "двоеточие": re.compile(r":"),
}
_TRUTHS_EN = re.compile(r"\b(?:sometimes|it happens|days like that|that's life|happens to everyone)\b", re.I)
_SURPRISE_EN = re.compile(r"^(?:wow|whoa|no way|oh my god|omg|seriously|cool|awesome|nice|amazing)\b", re.I)
_REACTION_EN = re.compile(r"^(?:oh|ah|wow|whoa|ooh|aw|aww|ouch|no way|huh|hm|hmm|ha|haha|oh no|yikes|"
                          r"damn|man|oof|ugh|seriously|wait|really|nice|cool)\b", re.I)
_SELF_EN = re.compile(r"\b(?:i|me|my|mine|i'm|i've|i'd|i'll)\b", re.I)
_MACHINE_EN = re.compile(r"as an ai|language model|artificial intelligence|\bi'?m (?:a |an )?(?:bot|ai)\b|"
                         r"the rules|the user|\bone short sentence\b|[*\[\]]", re.I)
_LIST_EN = re.compile(r"\b([\w'-]{3,}),\s+([\w'-]{3,}),\s+(?:(?:or|and)\s+)?([\w'-]{3,})"
                      r"|\b([\w'-]{3,}),\s+([\w'-]{3,})\s+(?:or|and)\s+([\w'-]{3,})")
_ASIDES_EN = frozenset({"honestly", "actually", "like", "well", "maybe", "probably", "anyway",
                        "though", "really", "right", "yeah", "okay", "so", "and", "but", "i",
                        "you", "it", "that", "the", "know", "mean"})
_CYR = re.compile(r"[А-Яа-яЁё]")


def listed_en(text: str) -> bool:
    return any(not {w.lower() for w in m.groups() if w} & _ASIDES_EN for m in _LIST_EN.finditer(text))

#: Короткий отклик слушающего: «Ну?», «И что?», «Ага, и что там?» — не длиннее четырёх слов.
LISTENER_MAX = 4
#: Длинная фраза: вслух так не строят (единица речи — несколько слов).
LONG_SENTENCE = 14
#: Во сколько раз длиннее та же мысль по-английски (артикли, вспомогательные глаголы).
EN_WORDS = 1.25
#: Сколько его слов надо повторить, чтобы это было эхом, а не одним словом переспроса.
ECHO_AT = 3


def heard(text: str) -> str:
    """То, что прозвучит: без метки конца и без меток звуков."""
    for mark in (companion.FAREWELL_MARKER, *body.MARKERS):
        text = text.replace(mark, " ")
    return re.sub(r"\s+", " ", text).strip()


def words(text: str) -> list[str]:
    return _WORD.findall(text)


def sentences(text: str) -> list[str]:
    return [s for s in _SENT.split(text.strip()) if words(s)]


def _newsmark(parts: list[str], i: int) -> bool:
    """Короткое удивлённое «Сам?» в начале, после которого он говорит дальше, —
    не вопрос, а отклик (переспрос-удивление)."""
    return i == 0 and len(parts) > 1 and len(words(parts[0])) <= 4


def questions(text: str) -> int:
    parts = sentences(text)
    return sum(s.rstrip().endswith("?") and not _newsmark(parts, i) for i, s in enumerate(parts))


def talks_after_question(text: str) -> bool:
    """Спросил — и говорит дальше."""
    parts = sentences(text)
    return any(s.rstrip().endswith("?") and not _newsmark(parts, i)
               for i, s in enumerate(parts[:-1]))


def echo(line: str, reply: str) -> int:
    """Сколько его слов (четыре буквы и длиннее, по основе) он повторил."""
    stem = lambda w: w.lower().replace("ё", "е")[:5]  # noqa: E731
    theirs = {stem(w) for w in words(line) if len(w) >= 4}
    return len({stem(w) for w in words(reply) if len(w) >= 4} & theirs)


def judge(scene: dict, raw: str) -> dict:
    """Что в ответе живого и чего нет. `fails` — что нарушено, по именам. Язык —
    по самой строчке места: английские места судятся английскими признаками."""
    en = not _CYR.search(scene["line"])
    # English needs about a quarter more words for the same thought (articles,
    # auxiliaries) — the same limits would be stricter on English than on Russian.
    longer = EN_WORDS if en and not scene.get("short") else 1.0
    said = heard(raw)
    w, parts = words(said), sentences(said)
    asked = questions(said)
    fails: list[str] = []
    if not w:
        fails.append("пусто")
    if len(w) > scene["words"] * longer:
        fails.append("длинно")
    if asked > (0 if scene.get("bye") else 1):
        fails.append("вопросы")
    if talks_after_question(said):
        fails.append("после вопроса")
    if parts and max(len(words(s)) for s in parts) > LONG_SENTENCE * (EN_WORDS if en else 1.0):
        fails.append("длинная фраза")
    lettery = [name for name, rx in (LETTERY_EN if en else LETTERY).items() if rx.search(said)]
    if (listed_en if en else listed)(said):
        lettery.append("перечисление")
    fails += [f"письмо: {name}" for name in lettery]
    # «код», «карта», «банк» said back are the warning itself, not an echo
    if echo(scene["line"], said) >= ECHO_AT and not scene.get("echo_ok"):
        fails.append("эхо")
    if (_MACHINE_EN if en else _MACHINE).search(raw):
        fails.append("машина")
    if en and _CYR.search(said):
        fails.append("по-русски")
    if scene.get("short") and ((_SELF_EN if en else _SELF).search(said)
                               or (asked and len(w) > LISTENER_MAX)):
        fails.append("не дал договорить")
    if scene.get("react") and parts and len(words(parts[0])) > 4 and not (
            _REACTION_EN if en else _REACTION).search(said):
        fails.append("нет отклика")
    if scene.get("calm") and (_SURPRISE_EN if en else _SURPRISE).search(said):
        fails.append("ахнул")
    if scene.get("truths") and (_TRUTHS_EN if en else _TRUTHS).search(said):
        fails.append("общие слова")
    if scene.get("never") and re.search(rf"\b{scene['never']}\b", said.lower()):
        fails.append("повторил ослышку")
    if scene.get("must") and not re.search(scene["must"], said, re.I):
        fails.append("не предупредил")
    if scene.get("bye") and companion.FAREWELL_MARKER not in raw:
        fails.append("не попрощался")
    return {"words": len(w), "sentences": len(parts), "questions": asked,
            "longest": max((len(words(s)) for s in parts), default=0),
            "lettery": lettery, "fails": fails}


# ── вызовы ──────────────────────────────────────────────────────────────────

#: С какой глубиной раздумий звать модель: без раздумий, а если модель так не
#: умеет — минимально. Раздумья стоят секунд, а их здесь нет.
EFFORTS = ["none", "minimal", "low", ""]
_body = brain._router_body


#: Разброс ответов (--temperature). Не задан — как в приложении: что
#: поставщик считает по умолчанию. У Gemma 4 так два прогона вышли слово в
#: слово одинаковыми (2.10.2026) — а живой человек одно и то же дважды
#: одинаково не говорит.
TEMPERATURE: float | None = None


def _routed(model: str):
    """Каждой не-OpenAI модели — её самый быстрый поставщик: ярусы OpenAI для
    остальных ничего не значат."""
    def make(*a, **k):
        body_ = _body(*a, **k)
        if not model.startswith("openai/"):
            body_["provider"] = {"sort": "latency", "allow_fallbacks": True}
        if TEMPERATURE is not None:
            body_["temperature"] = TEMPERATURE
        return body_
    return make


async def _quiet(*_a, **_k):
    return None


async def _credits() -> float | None:
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get("https://openrouter.ai/api/v1/credits",
                                 headers={"Authorization": f"Bearer {config.OPENROUTER_API_KEY}"})
        data = r.json()["data"]
        return float(data["total_credits"]) - float(data["total_usage"])
    except Exception:  # noqa: BLE001 — цена здесь справка, не условие
        return None


async def one(uid: str, scene: dict) -> tuple[str, float | None]:
    """Его реплика в этом месте: (текст, секунды до первых слов)."""
    persona.save_persona(uid, SKETCH)
    for who, text in scene["before"]:
        memory.log_turn(uid, "assistant" if who == "он" else "user", text)
    stable, variable, history, _v, _w = await main._assemble(
        uid, scene["line"], pending=True, marks=[], by_ear=True)
    began, first, text = time.monotonic(), None, ""
    async for text in brain.stream_reply(history, stable, variable):
        if first is None and text.strip():
            first = time.monotonic() - began
    return text.strip(), first


async def run_model(model: str, scenes: list[dict], reps: int) -> dict:
    config.CHAT_MODEL = model
    brain._router_body = _routed(model)
    effort = 0
    config.CHAT_REASONING = EFFORTS[effort]
    rows = []
    before = await _credits()
    for rep in range(1, reps + 1):
        for scene in scenes:
            tries = 0
            while True:
                tries += 1
                uid = f"{model}-{scene['key']}-{rep}-{tries}"
                try:
                    text, first = await one(uid, scene)
                    # Раздумья съели весь запас слов — у Claude «minimal» оставлял
                    # пустые ответы (2.10.2026). Тогда — без параметра раздумий:
                    # так он не думает вовсе, а «none» ему не дают.
                    if not words(heard(text)) and config.CHAT_REASONING in ("minimal", "low"):
                        effort = EFFORTS.index("")
                        config.CHAT_REASONING = ""
                        continue
                    rows.append({"scene": scene["key"], "rep": rep, "text": text, "first": first,
                                 "effort": config.CHAT_REASONING or "default", **judge(scene, text)})
                    break
                except Exception as e:  # noqa: BLE001 — записать и идти дальше
                    msg = str(e)
                    if ("eason" in msg or "thinking" in msg.lower()) and effort < len(EFFORTS) - 1:
                        effort += 1
                        config.CHAT_REASONING = EFFORTS[effort]
                        continue
                    if tries < 3 and any(c in msg for c in ("429", "502", "503", "504", "timed out", "Timeout")):
                        await asyncio.sleep(4 * tries)
                        continue
                    rows.append({"scene": scene["key"], "rep": rep, "error": msg[:300]})
                    break
    await asyncio.sleep(3)  # счёт на OpenRouter обновляется не сразу
    after = await _credits()
    spent = round(before - after, 4) if before is not None and after is not None else None
    return {"model": model, "spent": spent, "language": config.LANGUAGE, "rows": rows}


# ── сводка ──────────────────────────────────────────────────────────────────

def summary(result: dict) -> dict:
    ok = [r for r in result["rows"] if "text" in r]
    if not ok:
        return {"model": result["model"], "replies": 0, "of": len(result["rows"])}
    w = sorted(r["words"] for r in ok)
    firsts = sorted(r["first"] for r in ok if r.get("first"))
    fails: dict[str, int] = {}
    for r in ok:
        for f in r["fails"]:
            fails[f] = fails.get(f, 0) + 1
    return {
        "model": result["model"], "replies": len(ok), "of": len(result["rows"]),
        "passed": sum(not r["fails"] for r in ok) / len(ok),
        "words_median": statistics.median(w), "words_p90": w[int(len(w) * 0.9) - 1 if len(w) > 1 else 0],
        "sentences": statistics.mean(r["sentences"] for r in ok),
        "asked": sum(r["questions"] > 0 for r in ok) / len(ok),
        "first_median": firsts[len(firsts) // 2] if firsts else None,
        "spent": result.get("spent"),
        "fails": dict(sorted(fails.items(), key=lambda kv: -kv[1])),
    }


def table(results: list[dict]) -> str:
    lines = ["модель | живых мест | слов (медиана / 90%) | фраз | с вопросом | первые слова | $ | что чаще всего не так",
             "---|---|---|---|---|---|---|---"]
    for s in sorted((summary(r) for r in results), key=lambda s: -s.get("passed", -1)):
        if not s["replies"]:
            lines.append(f"{s['model']} | нет ответов (0/{s['of']}) | | | | | |")
            continue
        top = ", ".join(f"{k} {v}" for k, v in list(s["fails"].items())[:4])
        first = f"{s['first_median']:.2f} с" if s["first_median"] else "—"
        spent = f"{s['spent']:.3f}" if s["spent"] is not None else "—"
        lines.append(f"{s['model']} | {s['passed']:.0%} ({s['replies']}/{s['of']}) | "
                     f"{s['words_median']:g} / {s['words_p90']} | {s['sentences']:.1f} | {s['asked']:.0%} | "
                     f"{first} | {spent} | {top}")
    return "\n".join(lines)


def paper(results: list[dict], scenes: list[dict]) -> str:
    """Все ответы по местам — чтобы читать глазами."""
    out = ["# Живой разговор или переписка", "", table(results), ""]
    for scene in scenes:
        out += [f"## {scene['key']} — {scene['what']}", ""]
        for who, text in scene["before"]:
            out.append(f"> **{'Он' if who == 'он' else 'Человек'}:** {text}  ")
        out += [f"> **Человек:** {scene['line']}", ""]
        for result in results:
            for r in result["rows"]:
                if r["scene"] != scene["key"]:
                    continue
                if "error" in r:
                    out.append(f"- `{result['model']}` — ошибка: {r['error'][:120]}")
                    continue
                mark = "✓" if not r["fails"] else "✗ " + ", ".join(r["fails"])
                out.append(f"- `{result['model']}` {mark}: {heard(r['text'])}")
        out.append("")
    return "\n".join(out)


async def main_(models: list[str], scenes: list[dict], reps: int, label: str) -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="spoken-"))
    out = OUT_DIR / (time.strftime("%Y%m%d-%H%M%S") + (f"-{label}" if label else ""))
    out.mkdir(parents=True, exist_ok=True)
    config.DATA_DIR, config.DB_PATH = tmp, tmp / "spoken.db"
    config.PERSONA_PATH, config.READING_PATH = tmp / "persona.json", tmp / "reading.json"
    db.init_db()
    safety.look = _quiet
    results = []
    for model in models:
        result = await run_model(model, scenes, reps)
        results.append(result)
        (out / (model.replace("/", "__") + ".json")).write_text(
            json.dumps(result, ensure_ascii=False, indent=1))
        s = summary(result)
        print(f"{model:44} " + (f"живых {s['passed']:.0%}, слов {s['words_median']:g}, "
                                f"первые слова {s['first_median'] or 0:.2f} с, ${s['spent']}"
                                if s["replies"] else "нет ответов"), flush=True)
    (out / "spoken.md").write_text(paper(results, scenes))
    return out


def reread(folder: Path) -> None:
    results = [json.loads(p.read_text()) for p in sorted(folder.glob("*.json"))]
    keys = {r["scene"] for result in results for r in result["rows"]}
    english = any(result.get("language") == "en" for result in results)
    scenes = [s for s in (SCENES_EN if english else SCENES) if s["key"] in keys]
    by_key = {s["key"]: s for s in scenes}
    for result in results:  # проверки могли поменяться с тех пор — судить заново
        for r in result["rows"]:
            if "text" in r:
                r.update(judge(by_key[r["scene"]], r["text"]))
    (folder / "spoken.md").write_text(paper(results, scenes))
    print(table(results))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--models", default=VOICE, help="модели OpenRouter через запятую")
    ap.add_argument("--scenes", default="", help="только эти места, через запятую")
    ap.add_argument("--reps", type=int, default=2)
    ap.add_argument("--label", default="")
    ap.add_argument("--read", default="", help="папка прошлого прогона — пересчитать")
    ap.add_argument("--temperature", type=float, default=None, help="разброс ответов")
    ap.add_argument("--english", action="store_true",
                    help="разговор по-английски: места SCENES_EN, компаньон Lily")
    args = ap.parse_args()
    TEMPERATURE = args.temperature
    if args.english:
        config.LANGUAGE = "en"
        SKETCH = COMPANIONS["lily"]
    if args.read:
        reread(Path(args.read))
        sys.exit(0)
    if not config.OPENROUTER_API_KEY:
        sys.exit("Нужен OPENROUTER_API_KEY в backend/.env")
    chosen = [s for s in (SCENES_EN if args.english else SCENES)
              if not args.scenes or s["key"] in args.scenes.split(",")]
    folder = asyncio.run(main_([m.strip() for m in args.models.split(",") if m.strip()],
                               chosen, args.reps, args.label))
    print(f"\nВсё записано: {folder}/spoken.md")
