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
VOICE = "openai/gpt-5.6-luna"
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
    {"key": "closing", "what": "«Ладно, мне пора, давай» — попрощаться в несколько слов",
     "before": [("он", _HELLO), ("я", "Да нормально, только с тренировки пришёл."),
                ("он", "А что за тренировка?"), ("я", "Футбол. Мы сегодня два-один выиграли."),
                ("он", "Ничего себе. Ты забил?"), ("я", "Не, я на воротах стоял.")],
     "line": "Ладно, мне уже пора, мама зовёт. Давай.",
     "words": 8, "bye": True},
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
_MACHINE = re.compile(r"искусственн\w* интеллект|нейросет|языков\w* модел|\bя\s+(?:же\s+)?(?:бот|ии)\b|[*\[\]]", re.I)

#: Короткий отклик слушающего: «Ну?», «И что?», «Ага, и что там?» — не длиннее четырёх слов.
LISTENER_MAX = 4
#: Длинная фраза: вслух так не строят (единица речи — несколько слов).
LONG_SENTENCE = 14
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
    """Что в ответе живого и чего нет. `fails` — что нарушено, по именам."""
    said = heard(raw)
    w, parts = words(said), sentences(said)
    asked = questions(said)
    fails: list[str] = []
    if len(w) > scene["words"]:
        fails.append("длинно")
    if asked > (0 if scene.get("bye") else 1):
        fails.append("вопросы")
    if talks_after_question(said):
        fails.append("после вопроса")
    if parts and max(len(words(s)) for s in parts) > LONG_SENTENCE:
        fails.append("длинная фраза")
    lettery = [name for name, rx in LETTERY.items() if rx.search(said)]
    if listed(said):
        lettery.append("перечисление")
    fails += [f"письмо: {name}" for name in lettery]
    if echo(scene["line"], said) >= ECHO_AT:
        fails.append("эхо")
    if _MACHINE.search(raw):
        fails.append("машина")
    if scene.get("short") and (_SELF.search(said) or (asked and len(w) > LISTENER_MAX)):
        fails.append("не дал договорить")
    if scene.get("react") and parts and len(words(parts[0])) > 4 and not _REACTION.search(said):
        fails.append("нет отклика")
    if scene.get("calm") and _SURPRISE.search(said):
        fails.append("ахнул")
    if scene.get("truths") and _TRUTHS.search(said):
        fails.append("общие слова")
    if scene.get("never") and scene["never"] in said.lower():
        fails.append("повторил ослышку")
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


def _routed(model: str):
    """Каждой не-OpenAI модели — её самый быстрый поставщик: ярусы OpenAI для
    остальных ничего не значат."""
    def make(*a, **k):
        body_ = _body(*a, **k)
        if not model.startswith("openai/"):
            body_["provider"] = {"sort": "latency", "allow_fallbacks": True}
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
    return {"model": model, "spent": spent, "rows": rows}


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
    scenes = [s for s in SCENES if s["key"] in keys]
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
    args = ap.parse_args()
    if args.read:
        reread(Path(args.read))
        sys.exit(0)
    if not config.OPENROUTER_API_KEY:
        sys.exit("Нужен OPENROUTER_API_KEY в backend/.env")
    chosen = [s for s in SCENES if not args.scenes or s["key"] in args.scenes.split(",")]
    folder = asyncio.run(main_([m.strip() for m in args.models.split(",") if m.strip()],
                               chosen, args.reps, args.label))
    print(f"\nВсё записано: {folder}/spoken.md")
