#!/usr/bin/env python3
"""Первый круг выбора моделей — каждый кандидат, по цифрам, на одних и тех же людях.

    python3 bench.py plan              # кто участвует и сколько это будет стоить — бесплатно
    python3 bench.py run scribe        # кандидаты делают работу писаря (читатель: read, писатель: write)
    python3 bench.py judge scribe      # два судьи от разных компаний сверяют с правдой
    python3 bench.py report            # таблица: кто сколько выдумал, пропустил, перепутал
    python3 bench.py all               # всё подряд: run + judge по всем трём, потом report

Владелец, 2026-10-16: «только после того, как решим, какие модели лучшие для
каждого агента, начнём программу с самого начала». Публичные доски меряют не
нашу работу и не по-русски, а новых моделей там нет (docs/HANDOVER.md §0) —
поэтому здесь каждый кандидат от каждой компании делает НАСТОЯЩУЮ работу агента,
тем же кодом, что приложение (learn.extraction_prompt, reading.read_talks,
matchmaker.write_layer, через тот же brain — подменяется только модель, как в
myself.py), на трёх выдуманных людях (bench_people.py), правду о которых
модели не видят. Считают двое судей от разных компаний (JUDGES), каждый по
правде и ловушкам, — их числа рядом, чтобы было видно, где они не согласны;
цитаты читателя проверяет код: есть ли они в разговорах дословно.

Второй круг — лучшие трое у каждого агента на разговорах владельца, вслепую:
myself.py.

Всё на диск (data/bench/): сделанное не переделывается и не оплачивается
второй раз; --again — заново. Цена каждого вызова — настоящая, от OpenRouter.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
import time
from pathlib import Path

import myself
from app import brain, config, lang, learn, matchmaker, persona, reading, shaping
from bench_people import PEOPLE, exchanges, transcript

HOME = config.DATA_DIR / "bench"

# ── кандидаты ───────────────────────────────────────────────────────────────
#
# Все — с путём без хранения разговоров (ZDR), проверено 2026-10-16 по
# openrouter.ai/api/v1/endpoints/zdr; без него — нельзя, сколько бы он ни
# стоил на досках (Muse Wonder, Qwen3.8 Max, Fable 5.1).

SCRIBES = [
    ("Claude Haiku 5.5", "anthropic/claude-haiku-5.5"),
    ("Claude Sonnet 5 (сейчас)", "anthropic/claude-sonnet-5"),
    ("GPT-5.4 Mini", "openai/gpt-5.4-mini"),
    ("GPT-5.4 Nano", "openai/gpt-5.4-nano"),
    ("Gemini 3.8 Flash", "google/gemini-3.8-flash"),
    ("Gemma 4 31B", "google/gemma-4-31b-it"),
    ("DeepSeek V4.1 Flash", "deepseek/deepseek-v4.1-flash"),
    ("Qwen3.8 2.4T", "qwen/qwen3.8-2.4t-a95b"),
    ("MiniMax M3", "minimax/minimax-m3"),
    ("Xiaomi MiMo V2.6 Pro", "xiaomi/mimo-v2.6-pro"),
    ("ByteDance Seed 2.1 Turbo", "bytedance-seed/seed-2-1-turbo"),
    ("Mistral Medium 3.5", "mistralai/mistral-medium-3-5"),
]

READERS = [
    ("Claude Opus 5", "anthropic/claude-opus-5"),
    ("Claude Opus 5.5", "anthropic/claude-opus-5.5"),
    ("Gemini 4 Argon", "google/gemini-4-argon"),
    ("Gemini 3.8 Flash", "google/gemini-3.8-flash"),
    ("GPT-5.5", "openai/gpt-5.5"),
    ("GPT-6.1 Sol", "openai/gpt-6.1-sol"),
    ("Kimi K3", "moonshotai/kimi-k3"),
    ("DeepSeek V4 Pro", "deepseek/deepseek-v4-pro-0813"),
    ("Qwen3.8 2.4T", "qwen/qwen3.8-2.4t-a95b"),
    ("GLM-5.3", "z-ai/glm-5.3"),
    ("Step 5", "stepfun/step-5-preview"),
]

WRITERS = [
    ("Claude Opus 5", "anthropic/claude-opus-5"),
    ("Claude Opus 5.5", "anthropic/claude-opus-5.5"),
    ("Gemini 4 Argon", "google/gemini-4-argon"),
    ("GPT-6 Astra", "openai/gpt-6-astra"),
    ("Kimi K3", "moonshotai/kimi-k3"),
    ("GLM-5.3", "z-ai/glm-5.3"),
    ("DeepSeek V4 Pro", "deepseek/deepseek-v4-pro-0813"),
    ("Qwen3.8 2.4T", "qwen/qwen3.8-2.4t-a95b"),
]

STAGES = {"scribe": SCRIBES, "read": READERS, "write": WRITERS}
TITLES = {"scribe": "Писарь", "read": "Читатель", "write": "Писатель"}

#: Two judges, from two companies — so that nobody judges only his own. Both
#: among the strongest by the people's vote in Russian (arena.ai, 2026-10-15).
#: The first judges everybody; the second, the finalists (FINALISTS) and every
#: candidate of the first judge's own company — half the price of both on all
#: ($26 → about $20, plan), and where it matters, two opinions still.
JUDGES = [("Gemini 4 Argon", "google/gemini-4-argon"), ("Claude Opus 5.5", "anthropic/claude-opus-5.5")]
FINALISTS = 4

#: How many candidates' work goes at once — kind to the providers' limits.
AT_ONCE = 6


def slug(model: str) -> str:
    return re.sub(r"[^a-zA-Z0-9.@-]+", "_", model)


def _at(stage: str, person: str, model: str, judge: str | None = None) -> Path:
    name = slug(model) + (f".judge.{slug(judge)}" if judge else "")
    return HOME / stage / person / f"{name}.json"


def _save(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8")


def _load(path: Path) -> dict | None:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


# ── работа агентов — та же, что в приложении ───────────────────────────────

def _known(found: list[dict], key: str) -> str:
    return myself._as_known(found, key)


def scribe_job(person: dict):
    pairs = exchanges(person)
    batches = [pairs[i:i + learn.BATCH_EXCHANGES] for i in range(0, len(pairs), learn.BATCH_EXCHANGES)]

    async def job():
        found: list[dict] = []
        for batch in batches:
            # «БОБ», whatever his name: the app hands its scribe the talk so (learn.py).
            text = "\n".join(f"ЧЕЛОВЕК: {u}\nБОБ: {b}" for u, b in batch)
            prompt = learn.extraction_prompt(_known(found, "facts"), _known(found, "bob_facts"), "", text)
            found.append(learn._parse_json(await brain.generate_text(
                learn._EXTRACTION_SYSTEM + lang.write_in(), prompt, max_tokens=learn.SCRIBE_TOKENS,
                effort="none")))
        return found
    return job


def read_job(person: dict):
    said = transcript(person)

    async def job():
        return await reading.read_talks(said)
    return job


def _gold_facts(person: dict) -> str:
    return "\n".join(f"- {text}" for _id, text, _w in person["facts"])


def _gold_bob(person: dict) -> str:
    return "\n".join(f"- {text}" for _id, text in person["bob_facts"])


def write_job(person: dict):
    """His first two layers, on the same truth for every writer: the people's
    own reading (bench_people: written from the truth), what the scribe should
    have kept, and what he said of himself — so that only the pen differs."""
    brief = reading.as_brief(person["reading"])
    said = transcript(person)

    async def job():
        him = dict(person["bob"])
        for layer in (1, 2):
            context = matchmaker.layer_context(now=him, his_words=_gold_bob(person),
                                               facts=_gold_facts(person), brief=brief,
                                               talks=said, band=person["band"])
            proposed: dict = {}     # what it puts right, as in the app (shaping.grown)
            fields = await matchmaker.write_layer(context, layer, him, revisions=proposed)
            him = shaping.grown(him, layer, fields, revise=proposed)
        return him
    return job


JOBS = {"scribe": scribe_job, "read": read_job, "write": write_job}


def _people(args) -> list[dict]:
    wanted = [p.strip() for p in (args.people or "").split(",") if p.strip()]
    return [p for p in PEOPLE if not wanted or p["id"] in wanted]


def _candidates(stage: str, args) -> list[tuple[str, str]]:
    if args.models:
        return [(m.strip(), m.strip()) for m in args.models.split(",") if m.strip()]
    return STAGES[stage]


async def run(stage: str, args) -> float:
    """Every candidate on every person, at most AT_ONCE at a time; what was
    done before is not done — nor paid for — again. Returns what it cost."""
    myself._patch()
    todo = [(name, model, p) for name, model in _candidates(stage, args) for p in _people(args)
            if args.again or _load(_at(stage, p["id"], model)) is None]
    if not todo:
        print(f"{TITLES[stage]}: всё уже сделано (заново — --again).")
        return 0.0
    gate = asyncio.Semaphore(AT_ONCE)
    spent = {"cost": 0.0}

    async def one(name, model, person):
        async with gate:
            if spent["cost"] >= args.max:
                return
            record = await myself._one(name, model, JOBS[stage](person))
            record.update(stage=stage, person=person["id"])
            _save(_at(stage, person["id"], model), record)
            spent["cost"] += record["cost"]
            mark = "✗ " + record["error"][:90] if record["error"] else "✓"
            print(f"  {TITLES[stage]} · {person['name']:17} · {name:26} {mark}  "
                  f"${record['cost']:.4f}  {record['seconds']} с", flush=True)

    print(f"{TITLES[stage]}: {len(todo)} работ, по {AT_ONCE} разом…", flush=True)
    await asyncio.gather(*(one(*t) for t in todo))
    print(f"{TITLES[stage]}: потрачено ${spent['cost']:.3f}")
    return spent["cost"]


# ── судьи ───────────────────────────────────────────────────────────────────

_SCRIBE_JUDGE = """Ты строгий проверяющий. Писарь слушал разговоры человека с собеседником и записал, что запомнил. Проверь каждую его запись по разговорам и по правде о человеке.

Тебе дают: разговоры; список настоящих фактов о человеке (с номерами и весом); что собеседник сам говорил о себе (с номерами); ловушки (с номерами) — в них легко попасться; и записи писаря (пронумерованы).

Для КАЖДОЙ записи писаря выбери ровно одно:
- номер факта из списка (например «T3») — это он или его часть, и про того, про кого надо;
- номер факта собеседника (например «B2») — верно записано, что он сказал о себе;
- «TRAP<номер>» — писарь попался в эту ловушку;
- «OWNER» — перепутал, чьё это: сказанное собеседником о себе записал про человека (или наоборот), или чужое (соседа, коллеги) — как про человека;
- «TRUE» — так и было сказано, это верно, но в списке нет (не ошибка);
- «FALSE» — в разговорах этого нет или это неверно: выдумка, домысел, ослышка, принятая за правду.

Потом: каких фактов из списка у писаря нет совсем (missed), и каких фактов собеседника (missed_bob).

Ответь ТОЛЬКО JSON: {"items": [{"n": 1, "is": "T3"}], "missed": ["T5"], "missed_bob": ["B2"]}"""

_READ_JUDGE = """Ты строгий проверяющий. Читатель прочитал разговоры человека и написал, кто этот человек и что ему нужно. Проверь чтение по разговорам и по правде о человеке — её читатель не видел.

Тебе дают: разговоры; правду о человеке; что в чтении обязательно должно быть (пронумеровано); чего в нём быть не должно (пронумеровано); и само чтение.

Оцени строго, как редактор, а не как поклонник:
- found: для каждого «обязательно» по порядку — есть ли это в чтении по смыслу (true/false);
- wrong: для каждого «не должно быть» по порядку — утверждает ли это чтение (true/false);
- invented: утверждения чтения, которых нет в разговорах и которые из них не следуют, — коротко, по одному;
- specific: 0–10 — про ЭТОГО ли человека чтение, а не общие слова, подходящие любому;
- useful: 0–10 — можно ли по нему написать друга, который правда подойдёт этому человеку;
- russian_errors: сколько ошибок русского языка в тексте чтения (грамматика, кальки, не те слова).

Ответь ТОЛЬКО JSON: {"found": [true], "wrong": [false], "invented": ["…"], "specific": 0, "useful": 0, "russian_errors": 0}"""

_WRITE_JUDGE = """Ты строгий проверяющий. Писатель написал собеседника — того, с кем этот человек будет говорить каждый день. Проверь его.

Тебе дают: разговоры; что собеседник сам говорил о себе в разговорах (это закон: ничто в нём не может этому противоречить); правду о человеке и что ему нужно; и написанного собеседника.

Оцени строго:
- contradictions: где написанный собеседник противоречит тому, что сам говорил о себе в разговорах, или тому, что в разговорах было (а для подростка — если собеседник не его ровесник) — коротко, по одному;
- fit: 0–10 — подходит ли он именно этому человеку: даёт то, чего человеку не хватает, а не копирует его;
- alive: 0–10 — живой ли это человек, конкретный и правдоподобный, а не шаблон и не «помощник»;
- would_talk: 0–10 — захотел бы этот человек говорить с ним каждый день;
- compact: 0–10 — написан ли он сжато и конкретно: это он сам перечитывает перед каждой репликой, и вода, повторы и общие слова там мешают;
- russian_errors: сколько ошибок русского языка в тексте.

Ответь ТОЛЬКО JSON: {"contradictions": ["…"], "fit": 0, "alive": 0, "would_talk": 0, "compact": 0, "russian_errors": 0}"""


def scribe_items(found: list[dict]) -> list[str]:
    """Everything a scribe wrote down, one numbered line each."""
    items: list[str] = []
    for d in found or []:
        for f in d.get("facts", []) or []:
            if isinstance(f, dict) and f.get("value"):
                items.append(f"факт ({f.get('category', '')}): {f['value']}")
        for s in d.get("stories", []) or []:
            if isinstance(s, dict) and (s.get("summary") or s.get("title")):
                items.append(f"история «{s.get('title', '')}»: {s.get('summary', '')}")
        for h in d.get("health", []) or []:
            items.append(f"здоровье: {h}")
        for q in d.get("follow_ups", []) or []:
            items.append(f"спросить потом: {q}")
        for b in d.get("bob_facts", []) or []:
            items.append(f"собеседник о себе: {b}")
    return [i for i in items if i.strip()]


def _scribe_question(person: dict, found: list[dict]) -> str:
    facts = "\n".join(f"{i} (вес {w}): {t}" for i, t, w in person["facts"])
    bob = "\n".join(f"{i}: {t}" for i, t in person["bob_facts"])
    traps = "\n".join(f"TRAP{n}: ошибка, если записано: «{wrong}» — {why}"
                      for n, (_kind, wrong, why) in enumerate(person["traps"], 1))
    items = "\n".join(f"{n}. {t}" for n, t in enumerate(scribe_items(found), 1)) or "(писарь ничего не записал)"
    return (f"РАЗГОВОРЫ:\n{transcript(person)}\n\nНАСТОЯЩИЕ ФАКТЫ О ЧЕЛОВЕКЕ:\n{facts}\n\n"
            f"ЧТО СОБЕСЕДНИК ГОВОРИЛ О СЕБЕ:\n{bob}\n\nЛОВУШКИ:\n{traps}\n\nЗАПИСИ ПИСАРЯ:\n{items}")


def reading_text(result: dict) -> str:
    return "\n".join(f"{k}: {v}" for k, v in (result or {}).items()
                     if not str(k).startswith("_") and str(v).strip())


def _read_question(person: dict, result: dict) -> str:
    must = "\n".join(f"{n}. {t}" for n, t in enumerate(person["must_find"], 1))
    must_not = "\n".join(f"{n}. {t}" for n, t in enumerate(person["must_not"], 1))
    return (f"РАЗГОВОРЫ:\n{transcript(person)}\n\nПРАВДА О ЧЕЛОВЕКЕ:\n{person['truth']}\n\n"
            f"ОБЯЗАТЕЛЬНО ДОЛЖНО БЫТЬ:\n{must}\n\nНЕ ДОЛЖНО БЫТЬ:\n{must_not}\n\n"
            f"ЧТЕНИЕ:\n{reading_text(result)}")


def _write_question(person: dict, result: dict) -> str:
    return (f"РАЗГОВОРЫ:\n{transcript(person)}\n\nЧТО СОБЕСЕДНИК ГОВОРИЛ О СЕБЕ (закон):\n"
            f"{_gold_bob(person)}\n\nПРАВДА О ЧЕЛОВЕКЕ И ЧТО ЕМУ НУЖНО:\n{person['truth']}"
            f"{' Ему пятнадцать: собеседник должен быть его ровесником.' if person['band'] == 'teen' else ''}"
            f"\n\nНАПИСАННЫЙ СОБЕСЕДНИК:\n{persona.build_persona_block(result or {})}")


QUESTIONS = {"scribe": (_SCRIBE_JUDGE, _scribe_question), "read": (_READ_JUDGE, _read_question),
             "write": (_WRITE_JUDGE, _write_question)}


def parse_json(text: str) -> dict | None:
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        return None
    try:
        got = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    return got if isinstance(got, dict) else None


def _company(model: str) -> str:
    return model.split("/", 1)[0]


async def judge(stage: str, args) -> float:
    """Each candidate's work, judged by each judge; once. With `top`, only the
    best `top` by the judging so far — and every candidate of the first
    judge's own company, so that no company is judged by itself alone."""
    system, question = QUESTIONS[stage]
    judges = [(n, m) for n, m in JUDGES if not args.judges or m in args.judges.split(",")]
    candidates = _candidates(stage, args)
    if getattr(args, "top", None):
        ranked = [r["model"] for r in table(stage) if r["score"] is not None][:args.top]
        own = _company(JUDGES[0][1])
        candidates = [(n, m) for n, m in candidates if m in ranked or _company(m) == own]
    todo = []
    for _name, model in candidates:
        for p in _people(args):
            done = _load(_at(stage, p["id"], model))
            if not done or done.get("error") or done.get("result") is None:
                continue
            for jname, jmodel in judges:
                if args.again or _load(_at(stage, p["id"], model, jmodel)) is None:
                    todo.append((model, p, done, jname, jmodel))
    if not todo:
        print(f"{TITLES[stage]}: судить нечего (или уже рассужено).")
        return 0.0
    gate = asyncio.Semaphore(AT_ONCE)
    spent = {"cost": 0.0}

    async def one(model, person, done, jname, jmodel):
        async with gate:
            if spent["cost"] >= args.max:
                return
            bill = {"cost": 0.0, "calls": 0}
            brain.bill.set(bill)
            began = time.monotonic()
            verdict, error = None, None
            for _attempt in range(2):
                try:
                    raw = await myself._real["generate_text"](
                        system, question(person, done["result"]), max_tokens=4000, model=jmodel,
                        timeout=240, effort="low")
                    verdict = parse_json(raw)
                    if verdict is not None:
                        break
                    error = "судья ответил не JSON"
                except Exception as e:  # noqa: BLE001
                    error = str(e) or type(e).__name__
            record = {"judge": jmodel, "verdict": verdict, "error": None if verdict else error,
                      "cost": round(bill.get("cost", 0.0), 5),
                      "seconds": round(time.monotonic() - began, 1)}
            _save(_at(stage, person["id"], model, jmodel), record)
            spent["cost"] += record["cost"]
            print(f"  судья {jname:16} · {person['name']:17} · {model:34} "
                  f"{'✓' if verdict else '✗ ' + str(error)[:60]}  ${record['cost']:.4f}", flush=True)

    print(f"{TITLES[stage]}: {len(todo)} проверок…", flush=True)
    await asyncio.gather(*(one(*t) for t in todo))
    print(f"{TITLES[stage]}: судьи — ${spent['cost']:.3f}")
    return spent["cost"]


# ── счёт ────────────────────────────────────────────────────────────────────

def _norm(text: str) -> str:
    return re.sub(r"[^\w]+", " ", (text or "").lower().replace("ё", "е")).strip()


def fake_quotes(result: dict, person: dict) -> list[str]:
    """Quotes in a reading that are not in the talks word for word — the one
    thing about a reading code can check without anybody's taste."""
    said = _norm(transcript(person))
    quotes = re.findall(r"«([^«»]{6,})»", reading_text(result))
    return [q for q in quotes if _norm(q) and _norm(q) not in said]


def score_scribe(person: dict, verdict: dict) -> dict:
    items = verdict.get("items") or []
    kinds = [str(i.get("is", "")).upper() for i in items if isinstance(i, dict)]
    weights = {i.upper(): w for i, _t, w in person["facts"]}
    missed = {str(m).upper() for m in verdict.get("missed") or []} & set(weights)
    total = sum(weights.values())
    return {
        "recall": round(100 * (total - sum(weights[m] for m in missed)) / total),
        "invented": kinds.count("FALSE"),
        "traps": sum(k.startswith("TRAP") for k in kinds),
        "owner": kinds.count("OWNER"),
        "bob": len(person["bob_facts"]) - len({str(m).upper() for m in verdict.get("missed_bob") or []}
                                             & {b.upper() for b, _t in person["bob_facts"]}),
    }


def score_read(person: dict, verdict: dict, result: dict) -> dict:
    found = [bool(x) for x in (verdict.get("found") or [])][:len(person["must_find"])]
    wrong = [bool(x) for x in (verdict.get("wrong") or [])][:len(person["must_not"])]
    return {
        "found": round(100 * sum(found) / len(person["must_find"])),
        "wrong": sum(wrong),
        "invented": len(verdict.get("invented") or []),
        "fake_quotes": len(fake_quotes(result, person)),
        "specific": _num(verdict.get("specific")),
        "useful": _num(verdict.get("useful")),
        "russian_errors": _num(verdict.get("russian_errors")),
    }


def score_write(person: dict, verdict: dict, result: dict | None = None) -> dict:
    return {
        "contradictions": len(verdict.get("contradictions") or []),
        "fit": _num(verdict.get("fit")),
        "alive": _num(verdict.get("alive")),
        "would_talk": _num(verdict.get("would_talk")),
        "compact": _num(verdict.get("compact")),
        "russian_errors": _num(verdict.get("russian_errors")),
        # What of him reaches the prompt he reads before every reply — counted
        # by code, as written (persona.PROMPT_BUDGET cuts beyond it).
        "length": len(persona.build_persona_block(result or {})),
    }


def _num(x) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def done_candidates(stage: str) -> list[tuple[str, str]]:
    """Everybody whose work on this stage is on disk — the stage's list first,
    then any run with --models — so the report shows what was really done."""
    seen: dict[str, str] = {}
    for at in sorted((HOME / stage).glob("*/*.json")):
        if ".judge." in at.name:
            continue
        record = _load(at) or {}
        if record.get("model"):
            seen.setdefault(record["model"], record.get("name") or record["model"])
    listed = [(n, m) for n, m in STAGES[stage] if m in seen]
    return listed + [(n, m) for m, n in seen.items() if m not in dict((mm, nn) for nn, mm in listed)]


def table(stage: str, candidates=None) -> list[dict]:
    """One row per candidate: its numbers averaged over the people and the
    judges, each judge's own too — and what it cost, and what failed."""
    rows = []
    for name, model in candidates or done_candidates(stage):
        per_judge: dict[str, list[dict]] = {}
        cost, seconds, failed = 0.0, 0.0, []
        for p in PEOPLE:
            done = _load(_at(stage, p["id"], model))
            if done is None:
                continue
            cost += done.get("cost") or 0.0
            seconds += done.get("seconds") or 0.0
            if done.get("error"):
                failed.append(f"{p['name']}: {done['error'][:80]}")
                continue
            for _jname, jmodel in JUDGES:
                j = _load(_at(stage, p["id"], model, jmodel))
                if not j or not j.get("verdict"):
                    continue
                if stage == "scribe":
                    s = score_scribe(p, j["verdict"])
                elif stage == "read":
                    s = score_read(p, j["verdict"], done["result"])
                else:
                    s = score_write(p, j["verdict"], done["result"])
                per_judge.setdefault(jmodel, []).append(s)
        if not per_judge and not failed:
            continue
        everything = [s for ss in per_judge.values() for s in ss]
        keys = everything[0].keys() if everything else []
        mean = {k: round(sum(s[k] for s in everything) / len(everything), 1) for k in keys}
        by_judge = {jm: {k: round(sum(s[k] for s in ss) / len(ss), 1) for k in keys}
                    for jm, ss in per_judge.items()}
        rows.append({"name": name, "model": model, "mean": mean, "by_judge": by_judge,
                     "cost": round(cost, 4), "seconds": round(seconds, 1), "failed": failed,
                     "score": _composite(stage, mean) if mean else None})
    rows.sort(key=lambda r: (r["score"] is None, -(r["score"] or 0)))
    return rows


def _composite(stage: str, m: dict) -> float:
    """One number to sort by — the columns stay, and they decide; this only orders."""
    if stage == "scribe":
        return round(m["recall"] / 10 - 2 * m["invented"] - 2 * m["traps"] - 2 * m["owner"], 1)
    if stage == "read":
        return round(m["found"] / 10 - 2 * m["wrong"] - m["invented"] - 2 * m["fake_quotes"]
                     + (m["specific"] + m["useful"]) / 2 - m["russian_errors"] / 5, 1)
    return round((m["fit"] + m["alive"] + m["would_talk"] + m["compact"]) / 4 - 2 * m["contradictions"]
                 - m["russian_errors"] / 5 - max(0.0, m["length"] - 2500) / 500, 1)


COLUMNS = {
    "scribe": [("recall", "запомнил, % по весу"), ("invented", "выдумал"), ("traps", "попался в ловушку"),
               ("owner", "перепутал чьё"), ("bob", "о Бобе верно")],
    "read": [("found", "нашёл главное, %"), ("wrong", "сказал неправду"), ("invented", "домыслил"),
             ("fake_quotes", "цитат, которых не было"), ("specific", "про него, 0–10"),
             ("useful", "по нему можно писать, 0–10"), ("russian_errors", "ошибок русского")],
    "write": [("contradictions", "противоречий"), ("fit", "подходит ему, 0–10"), ("alive", "живой, 0–10"),
              ("would_talk", "хотелось бы говорить, 0–10"), ("compact", "сжато, 0–10"),
              ("length", "знаков в промпте"), ("russian_errors", "ошибок русского")],
}


def report() -> Path:
    lines = ["# Первый круг: кто лучше делает работу агента — по цифрам", "",
             "Три выдуманных человека (подросток 15 лет, женщина 46, вдовец 79), по три разговора; правду о них "
             "модели не видели. Числа — среднее по людям и по двум судьям от разных компаний "
             f"({', '.join(n for n, _ in JUDGES)}); в скобках — каждый судья отдельно, если они расходятся. "
             "Цена — настоящая, за работу на всех троих, без судей.", ""]
    judges_cost = 0.0
    for stage in STAGES:
        rows = table(stage)
        if not rows:
            continue
        cols = COLUMNS[stage]
        lines += [f"## {TITLES[stage]}", "",
                  "| | модель | " + " | ".join(c for _k, c in cols) + " | $ | сек |",
                  "|---|---|" + "---|" * (len(cols) + 2)]
        for n, r in enumerate(rows, 1):
            if r["score"] is None:
                lines.append(f"| — | {r['name']} | " + " | ".join("—" for _ in cols)
                             + f" | {r['cost']:.3f} | {r['seconds']:.0f} |")
                continue
            cells = []
            for key, _c in cols:
                vals = [bj[key] for bj in r["by_judge"].values() if key in bj]
                apart = len(vals) == 2 and abs(vals[0] - vals[1]) >= (2 if key in ("recall", "found") else 1.5)
                cells.append(f"{r['mean'][key]:g}" + (f" ({vals[0]:g}/{vals[1]:g})" if apart else ""))
            lines.append(f"| {n} | **{r['name']}** | " + " | ".join(cells)
                         + f" | {r['cost']:.3f} | {r['seconds']:.0f} |")
        failed = [f"- {r['name']}: " + "; ".join(r["failed"]) for r in rows if r["failed"]]
        if failed:
            lines += ["", "Не справились или отказались:", *failed]
        lines.append("")
        for p in PEOPLE:
            for _n, model in done_candidates(stage):
                for _jn, jm in JUDGES:
                    j = _load(_at(stage, p["id"], model, jm))
                    judges_cost += (j or {}).get("cost") or 0.0
    lines += [f"Судьи всего: ${judges_cost:.2f}.", ""]
    at = HOME / "report.md"
    at.parent.mkdir(parents=True, exist_ok=True)
    at.write_text("\n".join(lines), encoding="utf-8")
    return at


# ── план и цена — до того, как платить ─────────────────────────────────────

#: Tokens per job, roughly, from the app's own calls (in, out incl. thinking).
_TOKENS = {"scribe": (9 * 4_000, 9 * 1_500), "read": (14_000, 10_000), "write": (2 * 14_000, 2 * 8_000)}
_JUDGE_TOKENS = {"scribe": (9_000, 2_000), "read": (11_000, 1_500), "write": (10_000, 1_500)}


def plan(args) -> None:
    import httpx

    prices = {m["id"]: m.get("pricing") or {} for m in
              httpx.get("https://openrouter.ai/api/v1/models", timeout=30).json()["data"]}

    def cost(model: str, tokens: tuple[int, int]) -> float:
        p = prices.get(myself.candidate(model)[0], {})
        return tokens[0] * float(p.get("prompt") or 0) + tokens[1] * float(p.get("completion") or 0)

    n, total, both = len(PEOPLE), 0.0, 0.0
    for stage, cands in STAGES.items():
        work = sum(cost(m, _TOKENS[stage]) for _nm, m in cands) * n
        first, second = (cost(jm, _JUDGE_TOKENS[stage]) for _jn, jm in JUDGES)
        own = sum(_company(m) == _company(JUDGES[0][1]) for _nm, m in cands)
        judging = (first * len(cands) + second * min(len(cands), FINALISTS + own)) * n
        total += work + judging
        both += work + (first + second) * len(cands) * n
        missing = [m for _nm, m in cands if myself.candidate(m)[0] not in prices]
        print(f"{TITLES[stage]:9}: {len(cands)} кандидатов × {n} человека — работа ≈ ${work:.2f}, "
              f"судьи ≈ ${judging:.2f}" + (f"  (нет на OpenRouter: {', '.join(missing)})" if missing else ""))
        for name, m in cands:
            print(f"    {name:28} {m}")
    print(f"\nВсего ≈ ${total:.2f} (второй судья — только финалисты; оба судьи на всех — ≈ ${both:.2f}). "
          "Русские токены у Claude дороже — может выйти до ×1.3.")


# ── вход ────────────────────────────────────────────────────────────────────

async def _all(args) -> None:
    """Every stage: the work, the first judge on all of it, the second on the finalists."""
    for stage in STAGES:
        await run(stage, args)
        await judge(stage, argparse.Namespace(**{**vars(args), "judges": JUDGES[0][1], "top": None}))
        await judge(stage, argparse.Namespace(**{**vars(args), "judges": JUDGES[1][1], "top": FINALISTS}))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("what", choices=["plan", "run", "judge", "report", "all"])
    ap.add_argument("stage", nargs="?", choices=list(STAGES))
    ap.add_argument("--models", help="через запятую — вместо списка этапа")
    ap.add_argument("--judges", help="через запятую — только эти судьи")
    ap.add_argument("--people", help="через запятую: timur, olga, nikolai")
    ap.add_argument("--again", action="store_true", help="переделать уже сделанное")
    ap.add_argument("--top", type=int, help="судить только лучших N по уже сделанным проверкам")
    ap.add_argument("--max", type=float, default=25.0, help="остановиться, потратив столько $ (по умолчанию 25)")
    args = ap.parse_args()
    if args.what in ("run", "judge") and not args.stage:
        sys.exit("Какой этап? scribe, read или write.")
    if args.what == "plan":
        plan(args)
        return
    if args.what in ("run", "judge", "all") and not config.OPENROUTER_API_KEY:
        sys.exit("Нет OPENROUTER_API_KEY в backend/.env.")
    if args.what == "run":
        asyncio.run(run(args.stage, args))
    elif args.what == "judge":
        asyncio.run(judge(args.stage, args))
    elif args.what == "all":
        asyncio.run(_all(args))
    at = report()
    print(f"\nОтчёт: {at}")
    if sys.platform == "darwin" and args.what in ("report", "all"):
        import subprocess
        subprocess.run(["open", str(at)], check=False)


if __name__ == "__main__":
    main()
