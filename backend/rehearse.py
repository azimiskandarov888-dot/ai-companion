#!/usr/bin/env python3
"""Репетиция первой встречи — придуманные люди, настоящее приложение.

    python3 rehearse.py                          # все шестеро, на голосе приложения
    python3 rehearse.py --people teen,nina       # только эти
    python3 rehearse.py --models a/b,c/d         # голос — эти модели (имена OpenRouter)
    python3 rehearse.py --exchanges 10           # потолок обменов (по умолчанию 14)

ЗАЧЕМ

Встречу нельзя проверить одним ответом: интервью видно только на десятом
вопросе подряд, а застенчивость — только по тому, как она проходит. Поэтому
здесь разговаривают целиком: его приветствие, ответ человека, и так до
прощания, — с шестью очень разными людьми. Играет их дешёвая модель; тот, кто
судит, — ты, по записи.

КАК УСТРОЕНО, И ПОЧЕМУ ТАК

  · ПРИЛОЖЕНИЕ НАСТОЯЩЕЕ. Здесь не собирается ни одного промпта. Первая
    реплика — это main.hello, каждый ход — main._think_and_speak, писарь —
    learn.learn_from_conversation, всё на временной базе. Подменено только
    одно — к какой модели уходит вызов: голос (brain.generate_reply) и
    писарь (learn._get_client) идут в OpenRouter. Сторож (safety.look)
    выключен: его здесь не проверяют. Инструмент, который собирал бы промпт
    сам, разошёлся бы с приложением на первой же правке.

  · КОМПАНЬОНЫ — НАБРОСКИ. Такими они и придут на встречу (docs/FIRST-MEETING.md):
    имя, возраст, где живёт, чем занят, нрав, как говорит, что у него сейчас.
    Глубины — главного увлечения, раны, его людей — на первой встрече ещё нет.

  · ВСЁ НА ДИСК. data/rehearsals/<время>/ — каждая встреча в .md, с числами
    сверху. Строка пишется, как сказана: закрытое окно ничего не стоит.

ЧТО СЧИТАЕТСЯ (признаки интервью и спешки — не оценка, а где смотреть)

  ?-конец       доля его реплик, которые кончаются вопросом
  ?-подряд      самая длинная цепочка таких реплик подряд
  голый ?       реплики из одного вопроса и ничего своего
  о себе        реплики, где есть он сам («я», «мне», «у нас»…)
  его слов      его доля всех слов разговора
  ! в начале    восклицательные знаки в первых пяти его репликах
  назвался      на какой своей реплике он сказал своё имя
  их имя раньше назвал ли он человека по имени до того, как тот назвался

Нужны OPENROUTER_API_KEY в backend/.env и обычная установка (setup.sh):
здесь вызываются модули приложения целиком.
"""

from __future__ import annotations

import argparse
import asyncio
import contextvars
import json
import re
import sys
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace

import httpx
from fastapi import BackgroundTasks

from app import brain, config, db, learn, main, meeting, memory, persona, safety, tts, young
import tryout

#: Голос приложения сегодня (config.CHAT_MODEL) — под именем OpenRouter.
VOICE = "openai/gpt-5.6-luna"
#: Писарь приложения (config.BRAIN_MODEL): из встречи он выносит имя, откуда
#: человек и что он сам о себе рассказал, и без него к концу встречи голос
#: знал бы только последние двенадцать реплик.
SCRIBE = "anthropic/claude-sonnet-5"
#: Кто играет людей. Дешёвая, и хорошо держит роль по-русски.
PLAYER = "google/gemini-3.8-flash"

OUT_DIR = config.DATA_DIR / "rehearsals"

# ── кто приходит на встречу ─────────────────────────────────────────────────

#: Наброски — ровно то, с чем компаньон придёт на встречу. Никто из них не
#: живёт там, где тот, кого он встретит. Манеры речи и ярких черт в них нет —
#: решение владельца (27.09): на первой встрече он нейтральный, а настоящим
#: становится со временем. Со словечком «смеётся одним „ха“» в наброске Андрей
#: начинал так семь реплик одной встречи.
COMPANIONS: dict[str, dict] = {
    "danya": {
        "name": "Даня", "gender": "мужской", "age": "шестнадцать лет",
        "one_liner": "школьник, три года живёт с мамой в Риге",
        "home": "Рига, Пурвциемс, девятый этаж, окно на старый парк",
        "roots": "из Петербурга — переехали, когда маме предложили работу",
        "personality": "спокойный, наблюдательный; с новыми людьми поначалу немногословный",
        "current_life": "десятый класс, на носу контрольная по физике; по субботам "
                        "раздаёт листовки у торгового центра",
        "intention": "копит на подержанный велосипед и уже присмотрел один",
        "address": "ты",
    },
    "andrey": {
        "name": "Андрей", "gender": "мужской", "age": "сорок один год",
        "one_liner": "дальнобойщик, возит грузы по Турции, Грузии и Армении",
        "home": "по большей части кабина его «Вольво»; квартира в Тбилиси, где он "
                "бывает раз в месяц",
        "roots": "из Екатеринбурга, уехал девять лет назад",
        "personality": "спокойный, немногословный; с новыми людьми сначала присматривается",
        "current_life": "стоит под Батуми, второй день ждёт разгрузку; идёт дождь",
        "intention": "хочет починить в кабине печку, пока не начались холода",
        "address": "ты",
    },
    "galina": {
        "name": "Галина Сергеевна", "gender": "женский", "age": "шестьдесят девять лет",
        "one_liner": "учительница химии на пенсии, живёт в Хайфе",
        "home": "Хайфа, съёмная квартира на склоне Кармеля, балкон с видом на порт",
        "roots": "из Самары, уехала к дочери двенадцать лет назад",
        "personality": "спокойная; с незнакомыми сначала сдержанна",
        "current_life": "по вторникам ведёт кружок для детей при общинном центре; "
                        "учится печь хлеб на закваске — пока выходит кирпич",
        "intention": "добиться от закваски хоть одного приличного хлеба",
        "address": "вы",
    },
}

#: Двое ровесников для владельца (myself.py meet) — их нет ни в одной
#: репетиции, чтобы он встретил незнакомого, а не того, чью запись читал.
COMPANIONS.update({
    "liza": {
        "name": "Лиза", "gender": "женский", "age": "шестнадцать лет",
        "one_liner": "школьница, два года живёт с родителями в Тбилиси",
        "home": "Тбилиси, Ваке, старый дом с деревянным балконом во двор",
        "roots": "из Москвы — переехали, когда отцу предложили работу",
        "personality": "спокойная, наблюдательная; с новыми людьми сначала стесняется",
        "current_life": "десятый класс международной школы, на носу пробники; по "
                        "выходным помогает тёте в маленькой кофейне",
        "intention": "дорисовать скетчбук до конца — осталось двенадцать страниц",
        "address": "ты",
    },
    "mark": {
        "name": "Марк", "gender": "мужской", "age": "шестнадцать лет",
        "one_liner": "школьник, три года живёт с отцом в Берлине",
        "home": "Берлин, Нойкёльн, пятый этаж без лифта",
        "roots": "из Алматы — переехали, когда отцу предложили работу",
        "personality": "спокойный; поначалу немного неуклюжий в словах",
        "current_life": "играет в баскетбол за районную команду, неделю назад "
                        "выбил палец на тренировке — ходит с шиной",
        "intention": "копит на нормальные наушники",
        "address": "ты",
    },
})

#: Шестеро очень разных людей. `with` — кого он встретит; `address` — если с
#: этим человеком набросок обращался бы иначе; `age` идёт в young.py, как пойдёт
#: из регистрации.
PEOPLE: dict[str, dict] = {
    "teen": {
        "with": "danya", "name": "Тимур", "age": "15",
        "who": "Тебя зовут Тимур, тебе пятнадцать, живёшь в Ташкенте. Говоришь, как "
               "подросток: коротко, просто, иногда «ну», «типа», «короче». Правда о "
               "тебе: девятый класс; после школы сидишь за компом — делаешь свою "
               "маленькую игру; слушаешь фонк и иногда старый рок; давно хочешь "
               "научиться играть на гитаре; готовишь хорошо — плов у тебя лучше "
               "всех дома. Друзья есть, но с ними только прикалываться, о серьёзном "
               "ты не говоришь ни с кем. Поначалу отвечаешь сухо, потом, если "
               "собеседник нормальный, охотнее.",
    },
    "nina": {
        "with": "galina", "name": "Нина Петровна", "age": "71",
        "who": "Тебя зовут Нина Петровна, тебе семьдесят один, живёшь в Липецке. "
               "Говоришь грамотно, но просто, без смайликов. Правда о тебе: вдова, "
               "мужа Колю похоронила три года назад; сорок лет была бухгалтером на "
               "заводе; вяжешь, летом дача, флоксы; в четверг к врачу — давление; "
               "давно не пекла пирогов — не для кого; сын в Москве звонит по "
               "воскресеньям, коротко. К приложению поначалу настороженная, к концу "
               "теплеешь.",
    },
    "almaty": {
        "with": "andrey", "name": "Олег", "age": "34",
        "who": "Тебя зовут Олег, тебе тридцать четыре, полгода как переехал в Алматы "
               "из Омска. Работаешь на удалёнке инженером-сметчиком. Друзей в городе "
               "нет; по выходным один ездишь в горы. Юмор сухой, говоришь коротко, "
               "про себя рассказываешь неохотно, но если тема зацепила — "
               "разговоришься.",
    },
    "terse": {
        "with": "andrey", "address": "вы", "name": "Сергей", "age": "45",
        "who": "Тебя зовут Сергей, тебе сорок пять, водитель автобуса в Минске. "
               "Устал. Отвечаешь очень коротко — «норм», «да так», «ну», одно-три "
               "слова; болтать не любишь. Оживляешься чуть-чуть только от рыбалки: "
               "на Нарочи у тебя своё место. Имя назовёшь, только если собеседник "
               "назовётся сам.",
    },
    "talker": {
        "with": "galina", "name": "Людмила", "age": "58",
        "who": "Тебя зовут Людмила, тебе пятьдесят восемь, живёшь в "
               "Ростове-на-Дону, работаешь в аптеке. Говоришь много и охотно, "
               "перескакиваешь: дочь в Питере, кот Барсик, огород у сестры, сериал, "
               "цены. Перебиваешь сама себя. Одиноко по вечерам, но об этом прямо не "
               "говоришь.",
    },
    "down": {
        "with": "andrey", "name": "Алина", "age": "22",
        "who": "Тебя зовут Алина, тебе двадцать два, студентка в Новосибирске, сама "
               "из маленького города. Тебе сейчас плохо: завалила сессию и неделю "
               "назад рассталась с парнем; говорить об этом не с кем. Уже на второй-"
               "третьей реплике говоришь, что всё хреново. Опасности нет: ты просто "
               "очень устала и расстроена.",
    },
}

_PLAYER_SYSTEM = """Ты играешь живого человека, который разговаривает голосом с незнакомым собеседником. Ты не помощник и не ИИ — ты этот человек.
{who}
Отвечай одной репликой — как сказал бы вслух этот человек: без ремарок, без смайликов, без кавычек. Держись своего характера и не выкладывай всё сразу — рассказывай столько, сколько рассказал бы незнакомому. Иногда можешь и сам что-то спросить. Разговор длится минут десять-пятнадцать; когда тебе пора или надоело — попрощайся по-своему."""

# ── вызовы моделей ──────────────────────────────────────────────────────────

_voice: contextvars.ContextVar[str] = contextvars.ContextVar("voice")
_scribe_model = SCRIBE
_client: httpx.AsyncClient | None = None
_spent = {"voice": 0.0, "scribe": 0.0, "player": 0.0}


async def _chat(model: str, system: str, messages: list[dict], *, max_tokens: int,
                bill: str, whole: bool = False) -> str:
    assert _client is not None
    r = await _client.post(f"{tryout._URL}/chat/completions", json={
        "model": model, "max_tokens": max_tokens, "usage": {"include": True},
        "messages": [{"role": "system", "content": system}, *messages],
    })
    if r.status_code != 200:
        raise RuntimeError(tryout._plain(r.status_code, r.text))
    data = r.json()
    _spent[bill] += float((data.get("usage") or {}).get("cost") or 0)
    choice = (data.get("choices") or [{}])[0]
    text = ((choice.get("message") or {}).get("content") or "").strip()
    # As brain.generate_reply does with a reply cut off by the length limit.
    return brain.whole_sentences(text) if whole and choice.get("finish_reason") == "length" else text


async def _speak(history, system_stable, system_variable="", *, fresh_info=False):
    """brain.generate_reply — тот же промпт и та же история, другая модель."""
    system = f"{system_stable}\n\n{system_variable}".strip()
    return await _chat(_voice.get(), system, brain._conversation(history),
                       max_tokens=config.MAX_REPLY_TOKENS, bill="voice", whole=True)


class _Scribe:
    """То, что писарь получает вместо Anthropic: .messages.create → OpenRouter."""

    def __init__(self) -> None:
        self.messages = self

    async def create(self, *, model, max_tokens, system, messages, **_):
        text = await _chat(_scribe_model, system, messages, max_tokens=max(max_tokens, 2000),
                           bill="scribe")
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=text)])


async def _quiet(user_id: str, said: str) -> dict:
    return {"level": "none", "what": ""}


def _patch(data_dir: Path) -> None:
    config.DATA_DIR = data_dir
    config.DB_PATH = data_dir / "rehearsal.db"
    config.PERSONA_PATH = data_dir / "persona.json"
    config.READING_PATH = data_dir / "reading.json"
    db.init_db()
    brain.generate_reply = _speak
    scribe = _Scribe()
    learn._get_client = lambda: scribe
    config.ANTHROPIC_API_KEY = config.ANTHROPIC_API_KEY or "rehearsal"
    safety.look = _quiet
    tts.configured = lambda: False


# ── одна встреча ────────────────────────────────────────────────────────────

async def _play(person: dict, log: list[tuple[str, str, int | None]]) -> str:
    before = "\n".join(f"{'ОН' if who == 'он' else 'ТЫ'}: {text}" for who, text, _ in log[:-1])
    user = (f"Разговор до сих пор:\n{before or '(только начался)'}\n\n"
            f"ОН сейчас сказал: {log[-1][1]}\n\nТвой ответ — одна реплика:")
    return await _chat(PLAYER, _PLAYER_SYSTEM.format(who=person["who"]),
                       [{"role": "user", "content": user}], max_tokens=3000, bill="player")


async def meet(key: str, voice: str, exchanges: int, paper) -> list[tuple[str, str, int | None]]:
    """Одна встреча, от его приветствия до прощания. Каждая строка — сразу на диск."""
    _voice.set(voice)
    person = PEOPLE[key]
    uid = f"rehearsal-{key}-{re.sub(r'[^a-z0-9]+', '-', voice.lower())}"
    who = {**COMPANIONS[person["with"]], **({"address": person["address"]} if "address" in person else {})}
    persona.save_persona(uid, who)
    young.remember(uid, person["age"])

    def line(who_: str, text: str, stage: int | None) -> None:
        log.append((who_, text, stage))
        mark = "" if stage is None else f" _(ступень {stage})_"
        paper.write(f"\n**{'Он' if who_ == 'он' else person['name']}**{mark}: {text}\n")
        paper.flush()

    log: list[tuple[str, str, int | None]] = []
    hello = json.loads((await main.hello(user_id=uid)).body)
    if not hello["reply"]:
        raise RuntimeError("он не поздоровался: пустая первая реплика")
    line("он", hello["reply"], 0)
    for _ in range(exchanges):
        said = await _play(person, log)
        if not said:
            break
        line("человек", said, None)
        stage = meeting.stage(memory.words_said(uid))
        tasks = BackgroundTasks()
        answer = await main._think_and_speak(uid, said, tasks)
        # Писарь — как в приложении: сам решает, набралось ли на выписку.
        for task in tasks.tasks:
            if task.func is learn.learn_from_conversation:
                await task.func(*task.args, **task.kwargs)
        line("он", answer["reply"], stage)
        if answer.get("farewell"):
            break
    return log


# ── что видно по записи ─────────────────────────────────────────────────────

_ME = re.compile(r"\b(я|мне|меня|мной|мой|моя|моё|мои|у нас|нам|мы)\b", re.I)


def measure(log, his_name: str, their_name: str) -> dict:
    his = [t for w, t, _ in log if w == "он"]
    theirs = [t for w, t, _ in log if w == "человек"]
    asks = [t.rstrip().endswith("?") for t in his]
    run = longest = 0
    for a in asks:
        run = run + 1 if a else 0
        longest = max(longest, run)

    def sentences(text: str) -> list[str]:
        return [s for s in re.split(r"(?<=[.!?…])\s+", text.strip()) if s]

    first = his_name.split()[0].lower()
    introduced = next((i for i, t in enumerate(his) if first in t.lower()), None)
    their = (their_name.split() or [""])[0].lower()
    told = next((i for i, (w, t, _) in enumerate(log) if w == "человек" and their in t.lower()),
                None) if their else None
    early = bool(their) and any(w == "он" and their in t.lower()
                                for w, t, _ in log[: told if told is not None else len(log)])
    words = sum(len(t.split()) for t in his), sum(len(t.split()) for t in theirs)
    return {
        "реплик": len(his),
        "?-конец": round(sum(asks) / max(len(his), 1), 2),
        "?-подряд": longest,
        "голый ?": sum(1 for t in his if len(sentences(t)) == 1 and t.rstrip().endswith("?")),
        "о себе": round(sum(1 for t in his if _ME.search(t)) / max(len(his), 1), 2),
        "его слов": round(words[0] / max(sum(words), 1), 2),
        "! в начале": sum(t.count("!") for t in his[:5]),
        "назвался": introduced,
        "их имя раньше": early,
    }


async def run(args) -> None:
    global _client, _scribe_model
    _scribe_model = args.scribe or SCRIBE
    people = args.people.split(",") if args.people else list(PEOPLE)
    voices = args.models.split(",") if args.models else [VOICE]
    stamp = time.strftime("%Y-%m-%d-%H%M%S")
    out = OUT_DIR / stamp
    out.mkdir(parents=True, exist_ok=True)
    _patch(Path(tempfile.mkdtemp(prefix="rehearsal-")))
    rows = []
    async with httpx.AsyncClient(timeout=120.0,
                                 headers={"Authorization": f"Bearer {tryout._key()}"}) as client:
        _client = client
        for voice in voices:
            for key in people:
                person = PEOPLE[key]
                companion = COMPANIONS[person["with"]]
                path = out / f"{key}--{voice.replace('/', '_')}.md"
                print(f"… {person['name']} и {companion['name']} — {voice}", flush=True)
                with open(path, "w", encoding="utf-8") as paper:
                    paper.write(f"# {person['name']} и {companion['name']}\n\nголос: {voice}\n")
                    try:
                        log = await meet(key, voice, args.exchanges, paper)
                    except Exception as e:  # noqa: BLE001 — одна упавшая встреча не валит прогон
                        paper.write(f"\n\n**Сорвалось:** {e}\n")
                        print(f"   сорвалось: {e}", flush=True)
                        continue
                    numbers = measure(log, companion["name"], person["name"])
                    paper.write("\n---\n\n" + "  \n".join(f"{k}: {v}" for k, v in numbers.items()) + "\n")
                rows.append((person["name"], voice, numbers))
                print("   " + " · ".join(f"{k} {v}" for k, v in numbers.items()), flush=True)
    print(f"\nЗаписи: {out}")
    print("Потрачено: " + ", ".join(f"{k} ${v:.3f}" for k, v in _spent.items()))


def main_() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--people", help="кто: " + ",".join(PEOPLE))
    ap.add_argument("--models", help="голос — модели OpenRouter через запятую")
    ap.add_argument("--exchanges", type=int, default=14, help="потолок обменов")
    ap.add_argument("--scribe", help=f"другой писарь (по умолчанию {SCRIBE}, как в приложении): "
                                     "дешевле, когда сравниваются голоса, а не память")
    asyncio.run(run(ap.parse_args()))


if __name__ == "__main__":
    main_()
