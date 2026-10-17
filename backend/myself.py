#!/usr/bin/env python3
"""Проверить всех агентов на себе — в том порядке, в каком их проходит человек.

    python3 myself.py begin            # 1. знакомство: он рождается пустым — имя и твои пожелания
                                       #    (--held — приложение его не дописывает: проверка руками)
      … потом поговори с ним 2–3 раза: ./run.sh и http://localhost:8000/live#me
    python3 myself.py scribe           # 2. что каждый писарь вынес из ваших разговоров
    python3 myself.py read             # 3. несколько чтений тебя по этим разговорам
    python3 myself.py write            # 4. несколько писателей дописывают его — выбранный и станет им
    python3 myself.py status           # что пройдено, сколько разговоров, сколько ушло
    python3 myself.py show             # какой он сейчас — то, что он читает перед каждой репликой
    python3 myself.py fix humor "…"    # поправить поле руками (список — через « | »)
    python3 myself.py pick read Б      # выбрать позже, если сразу не решил

ОДИН КОМПАНЬОН, С ПЕРВОЙ СЕКУНДЫ

Владелец, 2026-10-09: никакой отдельной «тени» — с первой секунды человек
говорит с тем же компаньоном, с которым будет говорить через месяц и через
год. Сначала он пустая бланка: случайное имя и пожелания человека. Потом он
дописывается слоями, как люди открываются: какой он; чем живёт и зачем он
тебе; его глубина (shaping.py). Пока ты проверяешь, приложение само его не
дописывает (у него стоит «_held»): первые два слоя пишет тот, кого выберешь ты.

ЗАЧЕМ НА СЕБЕ

tryout.py слушает, как пятеро играют Фёдора для Николая Петровича. Владелец
верно заметил, что судить, хорош ли ответ шестидесятивосьмилетнему, он не
может — он им не является. А про себя может всё: правда ли это чтение, хочется
ли говорить с этим человеком, не спорит ли он с тем, что сам о себе говорил.
Ни один бенчмарк этого не меряет.

КАК УСТРОЕНО, И ПОЧЕМУ ТАК

  · ПРОМПТЫ — ПРИЛОЖЕНИЯ, И ДОРОГА ТОЖЕ. Здесь не написано ни одного промпта.
    Каждый этап вызывает ту же функцию, что приложение (learn.extraction_prompt,
    reading.read_talks, matchmaker.write_layer), и тем же путём —
    brain.think / generate_text, через OpenRouter. Подменяется одно: какая
    модель отвечает.

  · ПО ПОРЯДКУ, И МЕНЯЕТСЯ ОДНО. Каждый этап ест то, что выбрано на прошлом:
    все писатели дописывают ОДНОГО и того же его из ОДНОГО и того же чтения.

  · ВСЛЕПУЮ. Ответы подписаны буквами и перетасованы; имена открываются
    только после выбора. Судить слова, а не марку.

  · ВСЁ НА ДИСК. data/myself/ — каждый этап в .json и в .md (читать глазами,
    спокойно). Выбор и одна фраза «почему» ложатся туда же.

  · ЦЕНА НАСТОЯЩАЯ. OpenRouter возвращает стоимость каждого вызова — она и
    печатается, а не оценка.

Нужны OPENROUTER_API_KEY в backend/.env и обычная установка (setup.sh), и
сервер — из этой же папки: разговоры, которые читают этапы, лежат в её базе.
"""

from __future__ import annotations

import argparse
import asyncio
import contextvars
import json
import random
import subprocess
import sys
import time
from pathlib import Path

from app import (brain, config, emergency, erase, identity, lang, learn, matchmaker, memory, mood,
                 persona, reading, shaping, voices, young)

HOME = config.DATA_DIR / "myself"

# ── кандидаты ───────────────────────────────────────────────────────────────
#
# Откуда они и почему именно эти — docs/MODELS-FOR-EACH-AGENT.md. Любой этап
# принимает --models id,id,… — чтобы добавить кандидата, не трогая файл.

#: Писарь — без размышления (так и в приложении, learn._extract). Из прежнего
#: списка ушли Sonnet 5.5, Gemini 3.8 Flash и GLM-5.3: размышление у них не
#: выключается. Пришли GPT-5.4 Nano (меньше всех выдумывает по Vectara, 3.1%)
#: и DeepSeek V4.1 Flash (без модерации, чистый русский своего семейства).
#: И твой вопрос (2026-10-09) — «может, писарю лучше думать?» — решает сама
#: проверка: нынешний Sonnet 5 здесь дважды, без размышления и думающий, как
#: думал до сих пор («@high»). docs/MODELS-RESEARCH-2026-10-09.md
SCRIBES = [
    ("Claude Haiku 5.5", "anthropic/claude-haiku-5.5"),
    ("GPT-5.4 Mini", "openai/gpt-5.4-mini"),
    ("GPT-5.4 Nano", "openai/gpt-5.4-nano"),
    ("DeepSeek V4.1 Flash", "deepseek/deepseek-v4.1-flash"),
    ("Claude Sonnet 5 — без размышления", "anthropic/claude-sonnet-5"),
    ("Claude Sonnet 5 — думает, как раньше", "anthropic/claude-sonnet-5@high"),
]

#: Gemini 3.1 Pro ушла (21-я из 28 в EQ-Bench 4, поддакивает больше всех,
#: худший русский в сравнении переводов на Habr), Kimi K3 вернулся (3-й в
#: EQ-Bench 4; по-русски не проседает — 16-й против 15-го по-английски).
#: Gemini 3.8 Flash — дешёвая проверка: 5-я на русской арене, в 7 раз дешевле.
#: 2026-10-16: Gemini 4 Argon — в исследовании первая на русской арене (1533),
#: но купить было нельзя; с 13 октября есть на OpenRouter, и без хранения
#: разговоров (ZDR через Google). Проверена: отвечает.
READERS = [
    ("Claude Opus 5", "anthropic/claude-opus-5"),
    ("Claude Opus 5.5", "anthropic/claude-opus-5.5"),
    ("Gemini 4 Argon", "google/gemini-4-argon"),
    ("Kimi K3", "moonshotai/kimi-k3"),
    ("GPT-5.5", "openai/gpt-5.5"),
    ("Gemini 3.8 Flash", "google/gemini-3.8-flash"),
    # Думать ещё сильнее — не обязательно лучше (у одной модели понимание
    # других на самом высоком уровне упало с 0.84 до 0.69): решит проверка.
    ("Claude Opus 5 — думает на максимуме", "anthropic/claude-opus-5@max"),
]

#: Ушли Fable 5.1 (нет пути без хранения разговоров — ZDR), Kimi K3 (17-й в
#: длинной прозе, к концу слабеет) и GPT-6.1 Sol (его ещё нет на досках, а у
#: GPT-6 Sol самые слабые персонажи). Opus 5 на xhigh — второй раунд, если он
#: выиграет: «--models anthropic/claude-opus-5,anthropic/claude-opus-5@xhigh».
WRITERS = [
    ("Claude Opus 5", "anthropic/claude-opus-5"),
    ("Claude Opus 5.5", "anthropic/claude-opus-5.5"),
    ("Gemini 4 Argon", "google/gemini-4-argon"),   # 2026-10-16, как у читателей
    ("GPT-6 Astra", "openai/gpt-6-astra"),
    ("GLM-5.3", "z-ai/glm-5.3"),
]

_LABELS = "АБВГДЕЖЗИК"

# ── один вызов, к той модели, которую сейчас проверяем ─────────────────────

#: Какой модели уходит вызов. ContextVar, а не глобальная переменная: этап
#: гоняет всех кандидатов разом, и у каждого своя задача со своей моделью.
_model: contextvars.ContextVar[str] = contextvars.ContextVar("model")
#: …и как ей думать, если у кандидата сказано своё: «модель@high». Иначе —
#: как велит приложение (у писаря — не думать).
_effort: contextvars.ContextVar[str | None] = contextvars.ContextVar("effort", default=None)


def candidate(spec: str) -> tuple[str, str | None]:
    """«anthropic/claude-sonnet-5@high» → модель и её размышление."""
    model, _, effort = spec.partition("@")
    return model, (effort or None)
#: The app's own calls, kept before they are pointed at the candidate.
_real = {"think": brain.think, "generate_text": brain.generate_text}


async def _think(system_prompt, user_text, *, model=None, effort="high",
                 max_tokens=8000, timeout=None):
    """The app's deep call, to the candidate — at the app's effort and on its
    road. No stall limit: a model that thinks longer than ours did is waited
    for, not judged on our impatience."""
    return await _real["think"](system_prompt, user_text, model=_model.get(),
                                effort=_effort.get() or effort, max_tokens=max_tokens,
                                timeout=None)


async def _generate_text(system_prompt, user_text, max_tokens=1500, model=None,
                         timeout=None, effort=None):
    return await _real["generate_text"](system_prompt, user_text, max_tokens=max_tokens,
                                        model=_model.get(), timeout=None,
                                        effort=_effort.get() or effort)


def _patch() -> None:
    """Приложение зовёт brain.think / brain.generate_text в момент вызова —
    значит, подменить их здесь достаточно, чтобы всё остальное осталось его."""
    brain.think = _think
    brain.generate_text = _generate_text


async def _one(name: str, model: str, job) -> dict:
    """Один кандидат на одном этапе. Никогда не поднимает исключение: упавший
    провайдер должен стоить одной строчки, а не всего этапа."""
    base, effort = candidate(model)
    _model.set(base)
    _effort.set(effort)
    bill = {"cost": 0.0, "calls": 0}
    brain.bill.set(bill)
    began = time.monotonic()
    try:
        result, error = await job(), None
    except Exception as e:  # noqa: BLE001
        result, error = None, str(e) or type(e).__name__
    return {"name": name, "model": model, "result": result, "error": error,
            "cost": round(bill.get("cost", 0.0), 5),
            "seconds": round(time.monotonic() - began, 1)}


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


def _chosen(stage: str, *, needed: bool = True):
    """Что выбрано на этапе — вход для следующего."""
    record = _load(stage)
    pick = (record or {}).get("pick")
    if not pick:
        if not needed:
            return None
        if record is None:
            sys.exit(f"Сначала этап «{stage}»: python3 myself.py {stage}")
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


def _ask(question: str) -> str:
    print(f"\n\033[1m{question}\033[0m")
    try:
        return input("> ").strip()
    except (EOFError, KeyboardInterrupt):
        sys.exit("\nПрервано. Ничего не сохранено.")


# ── твой друг в живом разговоре ─────────────────────────────────────────────

#: Кто ты в живом разговоре, когда страница открыта как localhost:8000/live#me —
#: один и тот же здесь и там (static/live.html, MY_FRIEND). Не секрет: это
#: страница разработки на твоём Mac, и к другим людям он не подходит.
LIVE_TOKEN = "myself-live-friend-0001"


def _me() -> str:
    return identity.user_id_from_token(f"Bearer {LIVE_TOKEN}")


def _talked() -> tuple[str, str]:
    """Твои разговоры с ним — так, как их получат читатель и писатель."""
    uid = _me()
    if not persona.has_persona(uid):
        sys.exit("Сначала знакомство: python3 myself.py begin")
    talks = memory.talks(uid)
    if not talks:
        sys.exit("Вы ещё не разговаривали: ./run.sh и http://localhost:8000/live#me")
    if len(talks) < 2:
        print("\033[2mПока один разговор — увидеть по нему можно немного. Лучше два-три.\033[0m")
    return uid, shaping.transcript(uid, persona.persona_name(persona.load_persona(uid)))


# ── 1 · знакомство ──────────────────────────────────────────────────────────

def _door() -> dict:
    """Как при входе в приложение — обычная регистрация, не анкета."""
    print("Как при входе в приложение. Он этого не услышит: твоё имя он узнает, "
          "только когда ты сам его скажешь.")
    return {
        "name": _ask("Как тебя зовут?"),
        "age": _ask("Сколько тебе лет?"),
        "country": _ask("Из какой ты страны?"),
        "wants": _ask("С кем хочешь познакомиться? Например: «с парнем», «с девушкой постарше», "
                      "«чтобы любил футбол». Можно пусто."),
    }


def begin(args) -> None:
    """Он рождается — без модели, сразу: случайное имя и твои пожелания. И
    совсем заново: прежний друг уходит со всем, что было."""
    door, uid = _door(), _me()
    erase.everything(uid)
    young.remember(uid, door["age"])
    if door["country"]:
        emergency.remember(uid, door["country"])
    if door["name"] and not young.keeps_nothing(uid):
        memory.add_memory(uid, "fact", f"имя: {door['name']}", owner="elder", title="имя",
                          importance=3)
    him = matchmaker.create_blank(uid, wants=door["wants"], their_age=door["age"],
                                  band=young.of(uid))
    # The models are chosen (2026-10-17): the app writes his layers itself.
    # Held (--held) only to test the agents by hand again: then it does not.
    held = bool(getattr(args, "held", False))
    persona.save_persona(uid, {**him, "_held": True} if held else him)
    HOME.mkdir(parents=True, exist_ok=True)
    _path("begin").write_text(json.dumps({"door": door, "him": him}, ensure_ascii=False,
                                         indent=2), encoding="utf-8")
    about = ", ".join(x for x in (him["name"], him.get("age", "")) if x)
    print(f"\nТвой друг: {about}. Больше о нём пока ничего не известно — даже ему самому.")
    print("\nТеперь поговори с ним 2–3 раза — как с незнакомым, как есть:")
    print("  ./run.sh   →   http://localhost:8000/live#me   →   «Начать разговор»")
    print("Между разговорами — перерыв больше 10 минут, иначе это один разговор.")
    if held:
        print("Потом: python3 myself.py scribe")
    else:
        print("Дописывать его будет само приложение — между разговорами.")


# ── 2 · писарь ──────────────────────────────────────────────────────────────

def exchanges(talks: list[list[dict]]) -> list[tuple[str, str]]:
    """Реплика человека и его ответ — пары, как их видит писарь. Его первое
    «привет», сказанное до человека, — тоже: и в нём он мог сказать о себе."""
    out: list[tuple[str, str]] = []
    for talk in talks:
        heard = "—"
        for t in talk:
            if t["role"] == "user":
                heard = t["content"]
            else:
                out.append((heard, t["content"]))
                heard = "—"
    return out


def _as_known(found: list[dict], key: str) -> str:
    if key == "bob_facts":
        facts = [str(x) for d in found for x in d.get("bob_facts", [])]
    else:
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
    uid, _said = _talked()
    pairs = exchanges(memory.talks(uid))
    batches = [pairs[i:i + learn.BATCH_EXCHANGES]
               for i in range(0, len(pairs), learn.BATCH_EXCHANGES)]

    async def job():
        found: list[dict] = []
        for batch in batches:
            text = "\n".join(f"ЧЕЛОВЕК: {u}\nБОБ: {b}" for u, b in batch)
            prompt = learn.extraction_prompt(_as_known(found, "facts"),
                                             _as_known(found, "bob_facts"), "", text)
            found.append(learn._parse_json(await brain.generate_text(
                learn._EXTRACTION_SYSTEM + lang.write_in(), prompt, max_tokens=learn.SCRIBE_TOKENS,
                effort="none")))   # как в приложении; «@high» у кандидата — думать
        return found

    entries = await _race(_candidates(args, SCRIBES), lambda m: job)
    record = {"stage": "scribe", "exchanges": len(pairs), "entries": entries}
    _save("scribe", record)
    at = _paper("scribe", "Что запомнил каждый писарь — вслепую", entries, _as_notes)
    print(f"\nСверь с тем, что вы говорили на самом деле: {at}")
    _judge("scribe", "Кто запомнил верно — про тебя и про него — и ничего не выдумал?", record)
    print("Дальше: python3 myself.py read")


def _facts_kept(found: list[dict]) -> str:
    """What the chosen scribe kept about the person, as the writer reads it."""
    lines = [f"- {f.get('value', '')}" for d in found for f in d.get("facts", [])
             if isinstance(f, dict) and f.get("value")]
    lines += [f"- {s.get('title', '')}: {s.get('summary', '')}" for d in found
              for s in d.get("stories", []) if isinstance(s, dict)]
    return "\n".join(lines)


# ── 3 · чтение ──────────────────────────────────────────────────────────────

async def read(args) -> None:
    _uid, said = _talked()
    entries = await _race(_candidates(args, READERS),
                          lambda m: (lambda: reading.read_talks(said)))
    record = {"stage": "read", "entries": entries}
    _save("read", record)
    at = _paper("read", "Чтения тебя — вслепую", entries, _as_reading)
    print(f"\nПрочитай спокойно: {at}")
    _judge("read", "Какое из чтений правдивее про тебя?", record)
    print("Дальше: python3 myself.py write")


def _as_reading(r: dict) -> str:
    """Чтение — и во что оно обойдётся: писателю один раз, голосу каждый ход."""
    brief, every = reading.as_brief(r), reading.standing_block(r)
    return (f"*{len(brief)} знаков писателю · {len(every)} — в каждую реплику "
            f"разговора*\n\n{brief}")


# ── 4 · писатель ────────────────────────────────────────────────────────────

def _his_words_kept(found: list[dict]) -> str:
    """What the chosen scribe kept of what HE said about himself — law."""
    return "\n".join(f"- {b}" for d in found for b in d.get("bob_facts", []) if str(b).strip())


async def write(args) -> None:
    uid, said = _talked()
    who = persona.load_persona(uid)
    if persona.written(who) >= 2:
        sys.exit("Первые два слоя уже написаны. Совсем заново: python3 myself.py begin")
    chosen = _chosen("read")["result"]
    kept = _chosen("scribe", needed=False)
    facts = _facts_kept(kept["result"]) if kept else memory.facts_context(uid)
    his_words = _his_words_kept(kept["result"]) if kept else memory.bob_self_context(uid)
    brief, band = reading.as_brief(chosen), young.of(uid)

    async def job():
        # The two layers that are due after a few talks — what he is like, then
        # what he lives for and is for you — each on what the first one wrote.
        him = dict(who)
        for layer in (1, 2):
            if persona.written(him) >= layer:
                continue
            context = matchmaker.layer_context(now=him, his_words=his_words, facts=facts,
                                               brief=brief, talks=said, band=band)
            proposed: dict = {}     # what it puts right, as in the app (shaping.grown)
            fields = await matchmaker.write_layer(context, layer, him, revisions=proposed)
            him = shaping.grown(him, layer, fields, revise=proposed)
        return him

    entries = await _race(_candidates(args, WRITERS), lambda m: job)
    record = {"stage": "write", "entries": entries}
    _save("write", record)
    at = _paper("write", "Он — дописанный разными писателями — вслепую", entries,
                persona.build_persona_block)
    print(f"\nПрочитай спокойно: {at}")
    _judge("write", "С кем из них тебе хотелось бы разговаривать каждый день — "
                    "и кто не спорит с тем, что он тебе уже о себе сказал?", record)
    if record.get("pick"):
        _become(record)


def _become(record: dict) -> None:
    """Выбранный становится им — и выбранное чтение становится тем, как он
    с тобой говорит. Его глубину приложение допишет само, когда вы будете
    знакомы, — уже тем писателем, кто здесь выиграл."""
    uid = _me()
    him = next(e for e in record["entries"] if e["label"] == record["pick"])["result"]
    kept = reading.with_what_stays(reading.load(uid), _chosen("read")["result"])
    # Read just now: the app's own re-reading starts counting from here.
    kept.update({"_read_at_visit": memory.visits_so_far(uid),
                 "_confirmed_at_read": mood.confirmed_count(uid)})
    reading.save(uid, kept)
    persona.save_persona(uid, {k: v for k, v in him.items() if k != "_held"})
    print(f"\nГотово: {him.get('name')} — {him.get('one_liner', '')}")
    print("Со следующего разговора он открывается тебе: какой он, чем живёт и зачем он тебе. "
          "Глубина — потом, когда вы будете знакомы.")


# ── служебное ───────────────────────────────────────────────────────────────

STAGES = ("scribe", "read", "write")


def status(args) -> None:
    total = 0.0
    for stage in STAGES:
        record = _load(stage)
        if record is None:
            print(f"  {stage:8} —")
            continue
        spent = sum(e.get("cost", 0) for e in record["entries"])
        total += spent
        pick = record.get("pick")
        chosen = next((e["name"] for e in record["entries"] if e["label"] == pick), None)
        print(f"  {stage:8} {'выбран ' + chosen if chosen else 'ещё не выбрано'}, ${spent:.4f}")
    print(f"\n  Всего: ${total:.4f}")
    uid = _me()
    if persona.has_persona(uid):
        who = persona.load_persona(uid)
        print(f"\n  Твой друг: {who.get('name')} — написано слоёв {persona.written(who)} из "
              f"{len(matchmaker.LAYERS)}; разговоров {len(memory.talks(uid))}, "
              f"твоих слов {memory.words_said(uid)}")


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
    if args.stage == "write":
        _become(record)


async def _staged(stage) -> None:
    _patch()
    await stage


def show(args) -> None:
    """Him, as he reads himself before every reply — and his fields by name."""
    who = persona.load_persona(_me())
    print(persona.build_persona_block(who))
    print("\nПоля:", ", ".join(k for k in who if not k.startswith("_") and k != "voice"))


def fix(args) -> None:
    """The owner's own hand on him (2026-10-16: «нам все-таки нужно его хоть
    как-то исправить»): one field, replaced — a list given as «a | b | c». No
    check stops it: this is the owner's decision. But what he has already said
    aloud the person has heard — the old value is printed, so it is a choice."""
    uid = _me()
    who = persona.load_persona(uid)
    field = args.field
    if field not in matchmaker.FIELD_HINTS and field not in ("name", "address", "gender"):
        sys.exit(f"Нет такого поля: {field}. Поля: {', '.join(matchmaker.FIELD_HINTS)}")
    old = who.get(field)
    new = ([part.strip() for part in args.value.split("|") if part.strip()]
           if isinstance(old, list) or "|" in args.value else args.value.strip())
    persona.save_persona(uid, {**who, field: new})
    print(f"{field}:\n  было: {json.dumps(old, ensure_ascii=False)}\n  стало: {json.dumps(new, ensure_ascii=False)}")
    said = memory.bob_self_context(uid)
    if said.strip():
        print("\nЧто он уже сказал о себе вслух (человек это слышал):\n" + said)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="stage", required=True)
    for name in STAGES:
        s = sub.add_parser(name)
        s.add_argument("--models", help="свои кандидаты: id,id,… (имена OpenRouter)")
    b = sub.add_parser("begin")
    b.add_argument("--held", action="store_true",
                   help="приложение его не дописывает — чтобы снова проверить агентов руками")
    sub.add_parser("status")
    sub.add_parser("show")
    f = sub.add_parser("fix")
    f.add_argument("field")
    f.add_argument("value")
    p = sub.add_parser("pick")
    p.add_argument("stage", choices=STAGES)
    p.add_argument("letter")
    p.add_argument("why", nargs="?", default="")
    args = ap.parse_args()

    if args.stage == "status":
        return status(args)
    if args.stage == "begin":
        return begin(args)
    if args.stage == "pick":
        return pick(args)
    if args.stage == "show":
        return show(args)
    if args.stage == "fix":
        return fix(args)
    asyncio.run(_staged(globals()[args.stage](args)))


if __name__ == "__main__":
    main()
