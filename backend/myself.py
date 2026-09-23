#!/usr/bin/env python3
"""Проверить всех агентов на себе — по порядку, как их проходит человек.

    python3 myself.py interview        # 1. знакомство — ровно как в приложении
    python3 myself.py read             # 2. несколько чтений тебя, вслепую
    python3 myself.py sketch           # 3. наборы из десяти набросков
    python3 myself.py write            # 4. несколько друзей из одного наброска
    python3 myself.py talk             # 5. пять голосов с ТВОИМ другом
    python3 myself.py scribe           # 6. что каждый писарь вынес из разговора
    python3 myself.py status           # что пройдено, что выбрано, сколько ушло
    python3 myself.py pick read Б      # выбрать позже, если сразу не решил

ЗАЧЕМ НА СЕБЕ

tryout.py слушает, как пятеро играют Фёдора для Николая Петровича. Владелец
верно заметил, что судить, хорош ли ответ шестидесятивосьмилетнему, он не
может — он им не является. А про себя может всё: правда ли это чтение, хочется
ли говорить с этим человеком, живой ли он. Ни один бенчмарк этого не меряет.

КАК УСТРОЕНО, И ПОЧЕМУ ТАК

  · ПРОМПТЫ — ПРИЛОЖЕНИЯ. Здесь не написано ни одного промпта. Каждый этап
    вызывает ту же функцию, что приложение (intake.next_question,
    reading.read_person, matchmaker.sketch_ten и write_him), а подменяется
    только одно — к какой модели уходит вызов: brain.think и
    brain.generate_text здесь отправляют его в OpenRouter. Инструмент,
    который собирал бы промпты сам, разошёлся бы с приложением на первой же
    правке и судил бы уже не наш продукт.

  · ПО ПОРЯДКУ, И МЕНЯЕТСЯ ОДНО. Каждый этап ест то, что выбрано на прошлом.
    Поэтому все писатели разворачивают ОДИН и тот же набросок из ОДНОГО и
    того же чтения — иначе нельзя понять, кто из них что сделал.

  · ВСЛЕПУЮ. Ответы подписаны буквами и перетасованы; имена открываются
    только после выбора. Судить слова, а не марку.

  · ВСЁ НА ДИСК. data/myself/ — каждый этап в .json (для программы) и в .md
    (чтобы читать глазами, спокойно). Выбор и одна фраза «почему» ложатся
    туда же: через неделю это будет единственным, что объясняет решение.

  · ЦЕНА НАСТОЯЩАЯ. OpenRouter возвращает стоимость каждого вызова — она и
    печатается, а не оценка.

Честные оговорки. Потолки токенов здесь щедрее, чем в приложении: они
подобраны под то, сколько думает Claude, а модель, которая думает дольше и
которую обрезали, проиграла бы не за своё. Ответ, который не обрезали, от
потолка не меняется. Писарю «что уже известно» собирается из его же прошлых
выписок, а не из базы, как в приложении, — близко, но не байт в байт.

Нужны OPENROUTER_API_KEY в backend/.env и обычная установка (setup.sh): в
отличие от tryout.py, здесь вызываются модули приложения целиком.
"""

from __future__ import annotations

import argparse
import asyncio
import contextvars
import json
import random
import re
import subprocess
import sys
import time
from pathlib import Path

import httpx

from app import brain, config, intake, learn, matchmaker, persona, reading, young
import tryout

HOME = config.DATA_DIR / "myself"

#: Откуда берётся разминка — прямо из приложения, а не копией рядом с ним.
SWIFT = Path(__file__).resolve().parents[1] / "ios" / "BobCompanion" / "Screens" / "ScrollScreen.swift"

# ── кандидаты ───────────────────────────────────────────────────────────────
#
# Откуда они и почему именно эти — docs/MODELS-FOR-EACH-AGENT.md. Любой этап
# принимает --models id,id,… — чтобы добавить кандидата, не трогая файл.

INTERVIEWER = ("Claude Sonnet 5", "anthropic/claude-sonnet-5")

#: Читателю язык важнее всего — поэтому здесь нет Kimi (у Kimi K2 #24 на
#: русской арене), зато есть Gemini 3.1 Pro, которая на русской арене первая.
READERS = [
    ("Claude Opus 5", "anthropic/claude-opus-5"),
    ("Claude Opus 5.5", "anthropic/claude-opus-5.5"),
    ("GPT-5.5", "openai/gpt-5.5"),
    ("Gemini 3.1 Pro", "google/gemini-3.1-pro-preview"),
    ("GPT-6 Sol", "openai/gpt-6-sol"),
]

#: Двое — и третьим набором их смесь: у разных семейств разные «любимые»
#: люди, поэтому пять от одного и пять от другого могут оказаться разнее,
#: чем десять от любого из них.
SKETCHERS = [
    ("Claude Opus 5", "anthropic/claude-opus-5"),
    ("GLM-5.3", "z-ai/glm-5.3"),
]

WRITERS = [
    ("Claude Opus 5", "anthropic/claude-opus-5"),
    ("Claude Opus 5.5", "anthropic/claude-opus-5.5"),
    ("Claude Fable 5.1", "anthropic/claude-fable-5.1"),
    ("GPT-6 Astra", "openai/gpt-6-astra"),
    ("Kimi K3", "moonshotai/kimi-k3"),
]

SCRIBES = [
    ("Claude Sonnet 5", "anthropic/claude-sonnet-5"),
    ("GPT-5.4 Mini", "openai/gpt-5.4-mini"),
    ("Gemini 3.8 Flash", "google/gemini-3.8-flash"),
    ("GLM-5.3", "z-ai/glm-5.3"),
]

_LABELS = "АБВГДЕЖЗИК"

# ── один вызов, к той модели, которую сейчас проверяем ─────────────────────

#: Какой модели уходит вызов. ContextVar, а не глобальная переменная: этап
#: гоняет всех кандидатов разом, и у каждого своя задача со своей моделью.
_model: contextvars.ContextVar[str] = contextvars.ContextVar("model")
#: Сколько потратил этот кандидат — копится по всем его вызовам на этапе.
_bill: contextvars.ContextVar[dict] = contextvars.ContextVar("bill")
_client: httpx.AsyncClient | None = None


async def _route(system: str, user: str, *, max_tokens: int, effort: str | None) -> str:
    body = {
        "model": _model.get(),
        "max_tokens": max(max_tokens, 20_000 if effort else 4_000),
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
        "usage": {"include": True},
    }
    if effort:
        body["reasoning"] = {"effort": effort}
    assert _client is not None, "клиент OpenRouter не открыт"
    r = await _client.post(f"{tryout._URL}/chat/completions", json=body)
    if r.status_code != 200:
        raise RuntimeError(tryout._plain(r.status_code, r.text))
    data = r.json()
    bill = _bill.get(None)
    if bill is not None:
        bill["cost"] += float((data.get("usage") or {}).get("cost") or 0)
        bill["calls"] += 1
    choice = (data.get("choices") or [{}])[0]
    text = ((choice.get("message") or {}).get("content") or "").strip()
    if not text:
        raise RuntimeError(f"пустой ответ (провайдер закончил так: {choice.get('finish_reason')})")
    return text


async def _think(system_prompt, user_text, *, model=None, effort="high",
                 max_tokens=8000, timeout=None):
    return await _route(system_prompt, user_text, max_tokens=max_tokens, effort=effort)


async def _generate_text(system_prompt, user_text, max_tokens=1500, model=None,
                         timeout=None, effort=None):
    return await _route(system_prompt, user_text, max_tokens=max_tokens, effort=effort)


def _patch() -> None:
    """Приложение зовёт brain.think / brain.generate_text в момент вызова —
    значит, подменить их здесь достаточно, чтобы всё остальное осталось его."""
    brain.think = _think
    brain.generate_text = _generate_text


async def _one(name: str, model: str, job) -> dict:
    """Один кандидат на одном этапе. Никогда не поднимает исключение: упавший
    провайдер должен стоить одной строчки, а не всего этапа."""
    _model.set(model)
    bill = {"cost": 0.0, "calls": 0}
    _bill.set(bill)
    began = time.monotonic()
    try:
        result, error = await job(), None
    except Exception as e:  # noqa: BLE001
        result, error = None, str(e) or type(e).__name__
    return {"name": name, "model": model, "result": result, "error": error,
            "cost": round(bill["cost"], 5), "seconds": round(time.monotonic() - began, 1)}


async def _race(candidates, job_for) -> list[dict]:
    """Все кандидаты разом, в перетасованном порядке, с буквами вместо имён."""
    order = list(candidates)
    random.shuffle(order)
    print(f"Работают {len(order)}: жду всех, это может занять пару минут…", flush=True)
    done = await asyncio.gather(*(_one(n, m, job_for(m)) for n, m in order))
    for label, entry in zip(_LABELS, done):
        entry["label"] = label
    return done


# ── файлы этапов ────────────────────────────────────────────────────────────

def _path(stage: str, ext: str = "json") -> Path:
    return HOME / f"{stage}.{ext}"


def _save(stage: str, record: dict) -> None:
    HOME.mkdir(parents=True, exist_ok=True)
    _path(stage).write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")


def _load(stage: str) -> dict | None:
    at = _path(stage)
    return json.loads(at.read_text(encoding="utf-8")) if at.exists() else None


def _chosen(stage: str):
    """Что выбрано на этапе — вход для следующего."""
    record = _load(stage)
    if record is None:
        sys.exit(f"Сначала этап «{stage}»: python3 myself.py {stage}")
    pick = record.get("pick")
    if not pick:
        sys.exit(f"На этапе «{stage}» ещё ничего не выбрано: python3 myself.py pick {stage} <буква>")
    return next(e for e in record["entries"] if e["label"] == pick)


def _paper(stage: str, title: str, entries: list[dict], render) -> Path:
    """Всё вслепую — в .md, чтобы читать глазами, а не листать терминал."""
    lines = [f"# {title}", ""]
    for e in entries:
        lines += [f"## {e['label']}", ""]
        lines.append(f"*не получилось: {e['error']}*" if e["error"] else render(e["result"]))
        lines.append("")
    at = _path(stage, "md")
    at.write_text("\n".join(lines), encoding="utf-8")
    # Папка лежит внутри скрытой .claude, и Finder её не показывает — владелец
    # дважды не смог её найти. Поэтому файл открывается сам.
    if sys.platform == "darwin":
        subprocess.run(["open", str(at)], check=False)
    return at


def _judge(stage: str, question: str, record: dict) -> None:
    """Выбор — потом имена. Никогда наоборот."""
    alive = [e["label"] for e in record["entries"] if not e["error"]]
    print(f"\n\033[1m{question}\033[0m")
    try:
        pick = input(f"буква ({', '.join(alive)}; пусто — решу потом): ").strip().upper()
    except (EOFError, KeyboardInterrupt):
        pick = ""
    if pick and pick in alive:
        try:
            why = input("почему — одной фразой (можно пусто): ").strip()
        except (EOFError, KeyboardInterrupt):
            why = ""
        record["pick"], record["why"] = pick, why
    _save(stage, record)
    _reveal(record)
    if not record.get("pick"):
        print(f"\nВыбрать позже: python3 myself.py pick {stage} <буква>")


def _reveal(record: dict) -> None:
    print("\n\033[1mКто есть кто\033[0m")
    for e in record["entries"]:
        mark = "  ← выбран" if e["label"] == record.get("pick") else ""
        fail = "  (не получилось)" if e["error"] else ""
        print(f"  {e['label']} — {e['name']}: ${e['cost']:.4f}, {e['seconds']} с{fail}{mark}")


def _candidates(args, default):
    if not args.models:
        return default
    return [(m, m) for m in args.models.split(",") if m.strip()]


# ── 1 · знакомство ──────────────────────────────────────────────────────────

def warm_up() -> list[dict]:
    """Разминка — из ScrollScreen.swift, русская половина, как видит её человек.

    Читается из исходника, а не переписана сюда: вторая копия разошлась бы с
    первой на первой же правке, и чтение судило бы разговор, которого в
    приложении нет."""
    src = SWIFT.read_text(encoding="utf-8")
    block = src[src.index("private static let warmUp"):]
    block = block[block.index("? [") + 3: block.index("] : [")]
    steps, at = [], 0
    while (at := block.find("Step(", at)) != -1:
        depth, i, quoted = 0, at + 4, False
        while True:
            c = block[i]
            if c == '"':
                quoted = not quoted
            elif not quoted and c == "(":
                depth += 1
            elif not quoted and c == ")":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        body = block[at:i]
        options = re.search(r"options:\s*\[([^\]]*)\]", body)
        steps.append({
            "say": re.search(r'say:\s*"([^"]*)"', body).group(1),
            "options": re.findall(r'"([^"]*)"', options.group(1)) if options else [],
            "country": "asksCountry: true" in body,
            "age": "asksAge: true" in body,
        })
        at = i
    return steps


def _ask(question: str, options: list[str]) -> str:
    print(f"\n\033[1m{question}\033[0m")
    for n, o in enumerate(options, 1):
        print(f"  {n}. {o}")
    try:
        said = input("> ").strip()
    except (EOFError, KeyboardInterrupt):
        sys.exit("\nПрервано. Ничего не сохранено — знакомство проходится за один раз.")
    if said.isdigit() and 1 <= int(said) <= len(options):
        return options[int(said) - 1]
    return said


async def interview(args) -> None:
    name, model = (args.model, args.model) if args.model else INTERVIEWER
    _model.set(model)
    _bill.set(bill := {"cost": 0.0, "calls": 0})
    print("Отвечай так, как написал бы другу в мессенджере: быстро и как есть.")
    print("Читатель смотрит не только на ЧТО, но и на КАК — вылизанный текст его обманет.")
    print("Цифрой — выбрать вариант, словами — ответить по-своему. Пусто — пропустить.")

    turns, facts = [], {"country": "", "age": ""}
    for step in warm_up():
        said = _ask(step["say"], step["options"])
        turns.append({"q": step["say"], "a": said})
        for key in ("country", "age"):
            if step[key]:
                facts[key] = said

    print(f"\n\033[2m— дальше вопросы задаёт интервьюер ({name}) —\033[0m")
    while True:
        try:
            nxt = await intake.next_question(turns)
        except Exception as e:  # noqa: BLE001 — как в приложении: конец, а не ошибка
            print(f"\n\033[2m(вопрос не получился — заканчиваю, как сделало бы приложение: {e})\033[0m")
            break
        if nxt["enough"] or not nxt["say"]:
            break
        if nxt["reaction"]:
            print(f"\n\033[2m{nxt['reaction']}\033[0m")
        turns.append({"q": nxt["say"], "a": _ask(nxt["say"], [])})

    wishes = _ask("Кого бы ты хотел встретить?\n\033[2mЧем больше решишь о нём "
                  "сейчас, тем меньше останется — встретить. Можно пусто.\033[0m", [])

    if _path("interview").exists():
        _path("interview").rename(HOME / f"interview.{time.strftime('%Y%m%d-%H%M%S')}.json")
    _save("interview", {
        "interviewer": name, "model": model, "cost": round(bill["cost"], 5),
        "turns": turns, "story": intake.as_story(turns), "wishes": wishes,
        "name": turns[0]["a"] if turns else "", **facts,
    })
    print(f"\nСохранено: {_path('interview')}  (интервьюер стоил ${bill['cost']:.4f})")
    print("Дальше: python3 myself.py read")


def _interview() -> dict:
    record = _load("interview")
    if record is None:
        sys.exit("Сначала знакомство: python3 myself.py interview")
    return record


# ── 2 · чтение ──────────────────────────────────────────────────────────────

async def read(args) -> None:
    me = _interview()
    entries = await _race(
        _candidates(args, READERS),
        lambda m: (lambda: reading.read_person(me["story"], me["wishes"])),
    )
    record = {"stage": "read", "entries": entries}
    _save("read", record)
    at = _paper("read", "Чтения тебя — вслепую", entries, _as_reading)
    print(f"\nПрочитай спокойно: {at}")
    _judge("read", "Какое из чтений правдивее про тебя?", record)
    print("Дальше: python3 myself.py sketch")


def _as_reading(r: dict) -> str:
    """Чтение — и во что оно обойдётся: писателю один раз, голосу каждый ход."""
    brief, every = reading.as_brief(r), reading.standing_block(r)
    return (f"*{len(brief)} знаков писателю · {len(every)} — в каждую реплику "
            f"разговора*\n\n{brief}")


# ── 3 · наброски ────────────────────────────────────────────────────────────

def _context() -> str:
    """Ровно то, что create_companion даёт наброскам и писателю."""
    me, chosen = _interview(), _chosen("read")["result"]
    story = matchmaker._their_story(me["story"], me["wishes"], me.get("age", ""),
                                    "", "", young.band(me.get("age", "")))
    brief = reading.as_brief(chosen)
    return story + ("\n\n" + brief if brief else "")


def mixed(first: list[str], second: list[str]) -> list[str]:
    """Пять от одного и пять от другого, через одного."""
    out: list[str] = []
    for a, b in zip(first[:5], second[:5]):
        out += [a, b]
    return out


async def sketch(args) -> None:
    context = _context()
    # Одни и те же искры для всех: иначе разница в наборах — это разница в
    # искрах, а не в моделях.
    seed = random.randrange(1 << 30)
    entries = await _race(
        _candidates(args, SKETCHERS),
        lambda m: (lambda: matchmaker.sketch_ten(context, random.Random(seed))),
    )
    alive = [e for e in entries if not e["error"]]
    if len(alive) >= 2:
        entries.append({
            "name": f"смесь: {alive[0]['name']} + {alive[1]['name']}", "model": "",
            "result": mixed(alive[0]["result"], alive[1]["result"]), "error": None,
            "cost": 0.0, "seconds": 0.0, "label": _LABELS[len(entries)],
        })
    record = {"stage": "sketch", "seed": seed, "entries": entries}
    _save("sketch", record)
    at = _paper("sketch", "Наборы по десять — вслепую", entries,
                lambda ten: "\n\n".join(f"{n}. {s}" for n, s in enumerate(ten, 1)))
    print(f"\nПрочитай спокойно: {at}")
    _judge("sketch", "В каком наборе люди правда РАЗНЫЕ, а не один человек десять раз?", record)
    if record.get("pick"):
        _roll(record)
    print("Дальше: python3 myself.py write")


def _roll(record: dict) -> None:
    """Кубик, а не модель и не ты: так в приложении, так и здесь."""
    ten = next(e for e in record["entries"] if e["label"] == record["pick"])["result"]
    n = random.randrange(len(ten))
    record["rolled"], record["sketch"] = n + 1, ten[n]
    _save("sketch", record)
    print(f"\nКубик выбрал набросок №{n + 1}:\n{ten[n]}")


# ── 4 · писатель ────────────────────────────────────────────────────────────

async def write(args) -> None:
    context = _context()
    rolled = _load("sketch") or {}
    if not rolled.get("sketch"):
        sys.exit("Сначала наброски и выбор набора: python3 myself.py sketch")

    async def job():
        return persona.clean(await matchmaker.write_him(context, rolled["sketch"]))

    entries = await _race(_candidates(args, WRITERS), lambda m: job)
    record = {"stage": "write", "sketch": rolled["sketch"], "entries": entries}
    _save("write", record)
    at = _paper("write", "Друзья из одного наброска — вслепую", entries, persona.build_persona_block)
    print(f"\nПрочитай спокойно: {at}")
    _judge("write", "С кем из них тебе хотелось бы разговаривать каждый день?", record)
    print("Дальше: python3 myself.py talk")


# ── 5 · голос ───────────────────────────────────────────────────────────────

async def talk(args) -> None:
    me, friend = _interview(), _chosen("write")["result"]
    who = me.get("name") or "ты"
    tryout.SAMPLE_PERSONA = friend
    tryout.SAMPLE_READING = reading.standing_block(_chosen("read")["result"])
    tryout.SAMPLE_MEMORY = ""
    tryout.SAMPLE_NAME = me.get("name", "")
    tryout.LISTENER = (f"{who} — это ты сам.",
                       "Суди не «хорошо ли написано», а «живой ли он со мной».")
    # Как в приложении: младшему в конец промпта ложится блок о том, как с ним
    # говорить. Без него голос проверялся бы не на том промпте, что услышит он.
    tryout.SAMPLE_YOUNG = young.for_band(young.band(me.get("age", "")))
    try:
        first = input("\nЧто скажешь ему первым? ").strip()
    except (EOFError, KeyboardInterrupt):
        return
    paper, whois = await tryout._run(argparse.Namespace(
        text=first or "Привет", talk=True, blind=True, reveal=False))
    labels = dict(line.split(" — ", 1) for line in whois.read_text(encoding="utf-8").splitlines())
    record = {"stage": "talk", "paper": str(paper), "whois": str(whois), "entries": [
        {"label": k, "name": v, "model": "", "result": None, "error": None,
         "cost": 0.0, "seconds": 0.0} for k, v in labels.items()]}
    _judge("talk", "Кто из них был с тобой живым — и остался собой до конца?", record)
    print("Дальше: python3 myself.py scribe")


# ── 6 · писарь ──────────────────────────────────────────────────────────────

def exchanges(paper: str, label: str) -> list[tuple[str, str]]:
    """Реплики человека и ответы ОДНОГО голоса — из записи tryout.py."""
    out = []
    for turn in paper.split("\n---\n")[1:]:
        said = re.search(r"^## Ты: (.*)$", turn, re.M)
        reply = re.search(rf"^\*\*{label}\*\*[^\n]*\n\n(.*?)(?=\n\*\*|\Z)", turn, re.M | re.S)
        if said and reply:
            out.append((said.group(1).strip(), reply.group(1).strip()))
    return out


def _as_known(found: list[dict]) -> str:
    facts = [f.get("value", "") for d in found for f in d.get("facts", []) if isinstance(f, dict)]
    facts += [str(x) for d in found for x in d.get("follow_ups", [])]
    return "\n".join(f"[{n}] {f}" for n, f in enumerate(facts, 1) if f) or "(пока ничего)"


def _as_notes(found: list[dict]) -> str:
    lines = []
    for n, d in enumerate(found, 1):
        lines.append(f"**Пачка {n}**")
        for f in d.get("facts", []):
            lines.append(f"- {f.get('category', '')}: {f.get('value', '')}")
        for s in d.get("stories", []):
            lines.append(f"- история «{s.get('title', '')}»: {s.get('summary', '')}")
        for h in d.get("health", []):
            lines.append(f"- здоровье: {h}")
        mood = d.get("mood") or {}
        if mood.get("note"):
            lines.append(f"- настроение: {mood.get('word', '')} — {mood['note']}")
        for q in d.get("follow_ups", []):
            lines.append(f"- спросить потом: {q}")
        for b in d.get("bob_facts", []):
            lines.append(f"- о себе он сказал: {b}")
        lines.append("")
    return "\n".join(lines)


async def scribe(args) -> None:
    heard = _load("talk") or {}
    pick = heard.get("pick")
    if not pick:
        sys.exit("Сначала разговор и выбор голоса: python3 myself.py talk")
    said = exchanges(Path(heard["paper"]).read_text(encoding="utf-8"), pick)
    if not said:
        sys.exit("В записи разговора не нашлось реплик выбранного голоса.")
    batches = [said[i:i + learn.BATCH_EXCHANGES]
               for i in range(0, len(said), learn.BATCH_EXCHANGES)]

    async def job():
        found: list[dict] = []
        for batch in batches:
            text = "\n".join(f"ЧЕЛОВЕК: {u}\nБОБ: {b}" for u, b in batch)
            prompt = learn.extraction_prompt(_as_known(found), "(пока ничего)", "", text)
            found.append(learn._parse_json(await _route(
                learn._EXTRACTION_SYSTEM, prompt, max_tokens=800, effort=None)))
        return found

    entries = await _race(_candidates(args, SCRIBES), lambda m: job)
    record = {"stage": "scribe", "exchanges": len(said), "entries": entries}
    _save("scribe", record)
    at = _paper("scribe", "Что запомнил каждый писарь — вслепую", entries, _as_notes)
    print(f"\nСверь с тем, что ты говорил на самом деле: {at}")
    _judge("scribe", "Кто запомнил верно — и ничего не выдумал?", record)


# ── служебное ───────────────────────────────────────────────────────────────

STAGES = ("interview", "read", "sketch", "write", "talk", "scribe")


def status(args) -> None:
    total = 0.0
    for stage in STAGES:
        record = _load(stage)
        if record is None:
            print(f"  {stage:10} —")
            continue
        if stage == "interview":
            total += record.get("cost", 0)
            print(f"  {stage:10} пройдено ({record['interviewer']}), ${record.get('cost', 0):.4f}")
            continue
        spent = sum(e.get("cost", 0) for e in record["entries"])
        total += spent
        pick = record.get("pick")
        chosen = next((e["name"] for e in record["entries"] if e["label"] == pick), None)
        print(f"  {stage:10} {'выбран ' + chosen if chosen else 'ещё не выбрано'}, ${spent:.4f}")
    print(f"\n  Всего: ${total:.4f}")


def pick(args) -> None:
    record = _load(args.stage)
    if record is None:
        sys.exit(f"Этапа «{args.stage}» ещё не было.")
    letter = args.letter.upper()
    if letter not in {e["label"] for e in record["entries"] if not e["error"]}:
        sys.exit(f"Нет такой буквы среди получившихся: {letter}")
    record["pick"], record["why"] = letter, args.why or record.get("why", "")
    _save(args.stage, record)
    _reveal(record)
    if args.stage == "sketch":
        _roll(record)


async def _staged(stage) -> None:
    global _client
    _patch()
    async with httpx.AsyncClient(
        timeout=600.0, headers={"Authorization": f"Bearer {tryout._key()}"}
    ) as client:
        _client = client
        await stage


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="stage", required=True)
    for name in STAGES:
        s = sub.add_parser(name)
        s.add_argument("--models", help="свои кандидаты: id,id,… (имена OpenRouter)")
        if name == "interview":
            s.add_argument("--model", help="другой интервьюер (имя OpenRouter)")
    sub.add_parser("status")
    p = sub.add_parser("pick")
    p.add_argument("stage", choices=STAGES[1:])
    p.add_argument("letter")
    p.add_argument("why", nargs="?", default="")
    args = ap.parse_args()

    if args.stage == "status":
        return status(args)
    if args.stage == "pick":
        return pick(args)
    asyncio.run(_staged(globals()[args.stage](args)))


if __name__ == "__main__":
    main()
