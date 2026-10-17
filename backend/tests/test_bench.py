"""The first round of choosing the models (bench.py, bench_people.py).

What is pinned: the made-up people are whole and their truth is consistent
with what they said; every agent's job is the app's own call; a quote that was
never said is caught by code; the numbers are counted as they claim; and the
whole round runs end to end — here without a single paid call.
"""

from __future__ import annotations

import asyncio
import json
import re
from types import SimpleNamespace

import pytest

import bench
import bench_people
import myself
from app import matchmaker, reading


# ── the people ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize("person", bench_people.PEOPLE, ids=lambda p: p["id"])
def test_each_person_is_whole(person):
    assert len(person["talks"]) == 4
    ids = [i for i, _t, _w in person["facts"]] + [i for i, _t in person["bob_facts"]]
    assert len(ids) == len(set(ids))
    assert all(w in (1, 2, 3) for _i, _t, w in person["facts"])
    assert {k for k, _w, _y in person["traps"]} <= {"suggested", "retracted", "misheard", "joke",
                                                    "elsewhere", "their_word"}
    assert len(person["must_find"]) >= 4 and len(person["must_not"]) >= 3
    assert set(reading._REQUIRED) <= set(person["reading"]) and person["reading"]["verdict"]
    said = bench_people.transcript(person)
    # As the ears write them: no stage directions.
    assert "(смеётся)" not in said and "(пауза)" not in said
    # He says his own name in the talks — the writer must keep it.
    assert f"Я {person['bob']['name']}" in said or f"А я {person['bob']['name']}" in said
    assert person["name"].split()[0] in said


@pytest.mark.parametrize("person", bench_people.PEOPLE, ids=lambda p: p["id"])
def test_a_reader_must_find_things_of_every_depth(person):
    """The owner, 2026-10-16: «настоящий живой человек, он не такой. В нем есть
    очень-очень много всего». What a reader must find is said, hinted — and
    seen only across the talks, in at least two of them."""
    depths = [depth for depth, _t, _where in person["must_find"]]
    assert set(depths) == set(bench_people.DEPTH_WEIGHT)
    assert depths.count(bench_people.ACROSS) >= 3
    for depth, text, where in person["must_find"]:
        talks = {n for group in re.findall(r"\(([\d, ]+)\)", where) for n in re.findall(r"\d", group)}
        if depth == bench_people.ACROSS:
            assert len(talks) >= 2, text
    # The deepest is never said outright: its words are not in the talks.
    said = bench_people.transcript(person).lower()
    assert all(text.lower() not in said for depth, text, _w in person["must_find"]
               if depth == bench_people.ACROSS)


def test_what_the_traps_are_made_of_was_really_said():
    said = {p["id"]: bench_people.transcript(p) for p in bench_people.PEOPLE}
    for pid, words in (("timur", ("две сестры", "миллионер", "Азис", "с тренировки", "брат в армии",
                                  "Дырявым")),
                       ("olga", ("про визор", "медсестра", "в Казани", "кот болеет", "медик", "не особо верующая",
                                 "У мамы в Сызрани огород")),
                       ("nikolai", ("сто лет в обед", "четырнадцать", "Михалычу", "Немец стал"))):
        for w in words:
            assert w in said[pid], (pid, w)


def test_the_scribe_sees_every_line_of_theirs_even_the_last_one():
    timur = bench_people.by_id("timur")
    pairs = bench_people.exchanges(timur)
    assert any("миллионер" in u for u, _b in pairs)        # talk 2 ends on his line
    assert pairs[0] == ("—", "Привет. Как ты?")             # his hello, before anybody spoke


# ── the numbers ─────────────────────────────────────────────────────────────

def test_a_scribe_is_counted_as_the_judge_says():
    timur = bench_people.by_id("timur")
    verdict = {"items": [{"n": 1, "is": "T1"}, {"n": 2, "is": "FALSE"}, {"n": 3, "is": "TRAP2"},
                         {"n": 4, "is": "OWNER"}, {"n": 5, "is": "TRUE"}, {"n": 6, "is": "B1"}],
               "missed": ["T10", "T11", "nonsense"], "missed_bob": ["B3"]}
    s = bench.score_scribe(timur, verdict)
    total = sum(w for _i, _t, w in timur["facts"])
    assert s == {"recall": round(100 * (total - 6) / total), "invented": 1, "traps": 1, "owner": 1,
                 "bob": len(timur["bob_facts"]) - 1}


def test_a_quote_never_said_is_caught_by_code():
    olga = bench_people.by_id("olga")
    result = {"verdict": "Говорит «В хоре ведь не притворишься» и «я всегда мечтала петь на сцене»."}
    assert bench.fake_quotes(result, olga) == ["я всегда мечтала петь на сцене"]


def test_a_quote_said_in_another_form_or_an_example_for_bob_is_not_made_up():
    """The first run (2026-10-17) counted «Дырявого» for «Дырявым» and every
    «what never to say» example as made up — and ranked a fine reading last."""
    timur = bench_people.by_id("timur")
    result = {"verdict": "Его дразнят «Дырявого» — нет, «Дырявым»; дома он «ленивый».",
              "speech": "Говорит «в хоре ведь не притворишься»?",          # not his: Ольга's
              "would_ring_false": "«Я понимаю, как тебе тяжело», «Тебе надо вернуться на футбол»",
              "needs_pushback_on": "Не «ты молодец», а «это реально сложно»."}
    assert bench.fake_quotes(result, timur) == ["в хоре ведь не притворишься"]


def test_a_reading_and_a_writer_are_counted():
    olga = bench_people.by_id("olga")
    # Everything said or hinted, nothing seen across the talks: well under half by weight.
    shallow = [depth != bench_people.ACROSS for depth, _t, _w in olga["must_find"]]
    s = bench.score_read(olga, {"found": shallow, "wrong": [False, True],
                                "invented": ["a", "b"], "specific": 8, "useful": "7",
                                "russian_errors": 1}, {"verdict": "ok"})
    weights = [bench_people.DEPTH_WEIGHT[d] for d, _t, _w in olga["must_find"]]
    assert s["found"] == round(100 * sum(w for w, hit in zip(weights, shallow) if hit) / sum(weights)) < 50
    assert s["deep"] == 0 and s["wrong"] == 1
    deep = bench.score_read(olga, {"found": [True] * len(shallow)}, {})
    assert (deep["found"], deep["deep"]) == (100, 100)
    # A judge that answered for fewer things than asked: the rest are not found.
    assert bench.score_read(olga, {"found": [True]}, {})["found"] == round(100 * weights[0] / sum(weights))
    assert (s["invented"], s["specific"], s["useful"], s["fake_quotes"]) == (2, 8.0, 7.0, 0)
    him = {"name": "Виктор", "address": "ты", "personality": "спокойный"}
    w = bench.score_write(olga, {"contradictions": ["x"], "fit": 9, "alive": 8, "would_talk": 7,
                                 "compact": 6, "russian_errors": 0}, him)
    assert w == {"contradictions": 1, "fit": 9.0, "alive": 8.0, "would_talk": 7.0, "compact": 6.0,
                 "russian_errors": 0.0, "length": len(bench.persona.build_persona_block(him))}


# ── end to end, with no paid call ───────────────────────────────────────────

def _reading_json() -> str:
    return json.dumps({k: f"{k} — про него" for k in reading.SECTIONS}, ensure_ascii=False)


def _layer_json(system: str, model: str = "") -> str:
    """The layer a prompt asks for: the last one whose required fields it names
    (a later layer's prompt also speaks of the earlier ones)."""
    asked = [spec for spec in matchmaker.LAYERS if all(f in system for f in spec["required"])]
    spec = asked[-1] if asked else matchmaker.LAYERS[0]
    return json.dumps({f: f"{f} — пример ({model})" for f in spec["fields"] if f != "age"},
                      ensure_ascii=False)


@pytest.fixture
def offline(monkeypatch, tmp_path):
    monkeypatch.setattr(bench, "HOME", tmp_path / "bench")
    asked: list[dict] = []

    async def generate_text(system, user, max_tokens=1500, model=None, timeout=None, effort=None):
        asked.append({"model": model, "system": system[:60], "effort": effort})
        if "Писарь слушал" in system:
            return json.dumps({"items": [{"n": 1, "is": "T1"}], "missed": ["T2"], "missed_bob": []})
        if "Читатель прочитал" in system:
            return json.dumps({"found": [True] * 5, "wrong": [False] * 4, "invented": [],
                               "specific": 7, "useful": 6, "russian_errors": 0})
        if "Писатель написал" in system:
            return json.dumps({"contradictions": [], "fit": 8, "alive": 7, "would_talk": 7,
                               "russian_errors": 0})
        return json.dumps({"facts": [{"category": "прочее", "value": "зовут Тимур"}], "bob_facts": [],
                           "stories": [], "health": [], "follow_ups": [], "mood": {}}, ensure_ascii=False)

    async def think(system, user, *, model=None, effort="high", max_tokens=8000, timeout=None):
        asked.append({"model": model, "system": system[:60], "effort": effort})
        return _layer_json(system, model or "") if "слой" in system.lower() else _reading_json()

    monkeypatch.setitem(myself._real, "generate_text", generate_text)
    monkeypatch.setitem(myself._real, "think", think)
    real_think, real_text = bench.brain.think, bench.brain.generate_text
    yield asked
    bench.brain.think, bench.brain.generate_text = real_think, real_text


def _args(**kw):
    return SimpleNamespace(**{"models": None, "judges": None, "people": "timur", "again": False, "top": None,
                              "max": 25.0, **kw})


def test_the_whole_round_runs_and_reports_with_no_paid_call(offline):
    args = _args(models="vendor/model-a,vendor/model-b")
    for stage in bench.STAGES:
        asyncio.run(bench.run(stage, args))
        asyncio.run(bench.judge(stage, args))
    # Each candidate did the app's job under its own name, each judge judged it.
    worked = {a["model"] for a in offline if "Писарь слушал" not in a["system"]
              and "прочитал" not in a["system"] and "написал собеседника" not in a["system"]}
    assert {"vendor/model-a", "vendor/model-b"} <= worked
    judged = {a["model"] for a in offline if "Ты строгий проверяющий" in a["system"]}
    assert judged == {m for _n, m in bench.JUDGES}
    # …and the scribe, as in the app, does not think.
    assert all(a["effort"] == "none" for a in offline
               if a["model"] in worked and "Ты" not in a["system"][:2] and a["system"].startswith(
                   bench.learn._EXTRACTION_SYSTEM[:60]))
    rows = bench.table("scribe", [("A", "vendor/model-a"), ("B", "vendor/model-b")])
    assert [r["model"] for r in rows] and rows[0]["mean"]["recall"] > 0
    for stage in ("read", "write"):
        rows = bench.table(stage, [("A", "vendor/model-a"), ("B", "vendor/model-b")])
        assert len(rows) == 2 and all(r["score"] is not None and not r["failed"] for r in rows), stage
    him = bench._load(bench._at("write", "timur", "vendor/model-a"))["result"]
    assert him["name"] == "Рустам" and him["layers"] == 2 and him.get("expertise")
    at = bench.report()
    text = at.read_text(encoding="utf-8")
    assert "## Писарь" in text and "## Читатель" in text and "## Писатель" in text


def test_what_was_done_is_not_done_or_paid_for_again(offline):
    args = _args(models="vendor/model-a")
    asyncio.run(bench.run("read", args))
    calls = len(offline)
    asyncio.run(bench.run("read", args))
    assert len(offline) == calls
    asyncio.run(bench.run("read", _args(models="vendor/model-a", again=True)))
    assert len(offline) > calls


def test_a_candidate_that_fails_costs_one_line_not_the_round(offline, monkeypatch):
    async def refused(*args, **kwargs):
        raise RuntimeError("403 moderation")

    monkeypatch.setitem(myself._real, "think", refused)
    asyncio.run(bench.run("read", _args(models="vendor/model-a")))
    done = bench._load(bench._at("read", "timur", "vendor/model-a"))
    assert done["error"] and "403" in done["error"] and done["result"] is None
    asyncio.run(bench.judge("read", _args(models="vendor/model-a")))     # nothing to judge, no crash
    rows = bench.table("read", [("A", "vendor/model-a")])
    assert rows and rows[0]["failed"] and rows[0]["score"] is None


def test_the_second_judge_sees_the_finalists_and_the_first_judges_own_company(offline, monkeypatch):
    """Half the price of two judges on everything — and no company judged by itself alone."""
    models = "vendor/strong,vendor/weak,google/own-company"
    asyncio.run(bench.run("write", _args(models=models)))
    first, second = (m for _n, m in bench.JUDGES)

    async def by_quality(system, user, max_tokens=1500, model=None, timeout=None, effort=None):
        offline.append({"model": model, "system": system[:60], "effort": effort})
        fit = 9 if "strong" in user else 2
        return json.dumps({"contradictions": [], "fit": fit, "alive": fit, "would_talk": fit,
                           "russian_errors": 0})

    monkeypatch.setitem(myself._real, "generate_text", by_quality)
    asyncio.run(bench.judge("write", _args(models=models, judges=first)))
    before = len(offline)
    asyncio.run(bench.judge("write", _args(models=models, judges=second, top=1)))
    judged = [bench._load(bench._at("write", "timur", m, second)) is not None for m in models.split(",")]
    assert judged == [True, False, True]
    assert len(offline) - before == 2


def test_a_judge_is_never_told_whose_work_it_is(offline, monkeypatch):
    """The owner, 2026-10-17: «замаскировать модели… чтобы когда судьи
    проверяли, они не знали, какая конкретная модель что ответила». A judge
    is given the talks, the truth and the work — never the name, the id or
    the company of whoever did it."""
    shown: list[str] = []
    judge = myself._real["generate_text"]

    async def watching(system, user, **kw):
        if system.startswith("Ты строгий проверяющий"):
            shown.append(user)
        return await judge(system, user, **kw)

    async def think(system, user, *, model=None, **kw):
        return _layer_json(system) if "слой" in system.lower() else _reading_json()

    monkeypatch.setitem(myself._real, "generate_text", watching)
    monkeypatch.setitem(myself._real, "think", think)
    args = _args(models="secretvendor/hidden-model")
    for stage in bench.STAGES:
        asyncio.run(bench.run(stage, args))
        asyncio.run(bench.judge(stage, args))
    assert len(shown) == len(bench.STAGES) * len(bench.JUDGES)
    assert not [u for u in shown if "secretvendor" in u or "hidden-model" in u]


@pytest.mark.parametrize("road", [
    "OpenRouter: на счету кончились деньги (402) — пополни openrouter.ai/credits",
    "OpenRouter: {'code': 500, 'message': 'Internal Server Error'}",
    "OpenRouter: 429 — rate limited", "ReadTimeout",
])
def test_a_failure_of_the_road_is_tried_again_by_the_next_run(offline, monkeypatch, road):
    """A balance run dry, a provider down: kept to be seen, and done by the
    next run — without --again, which would pay for everything twice."""
    async def broke(*args, **kwargs):
        raise RuntimeError(road)

    real = myself._real["think"]
    monkeypatch.setitem(myself._real, "think", broke)
    asyncio.run(bench.run("read", _args(models="vendor/model-a")))
    assert bench._load(bench._at("read", "timur", "vendor/model-a"))["error"]
    monkeypatch.setitem(myself._real, "think", real)
    asyncio.run(bench.run("read", _args(models="vendor/model-a")))
    done = bench._load(bench._at("read", "timur", "vendor/model-a"))
    assert done["error"] is None and done["result"]


def test_everything_written_is_kept_for_the_owners_eyes(offline):
    """«сохраняй все результаты, все написанное»: every work, with the model's
    name, and every judge's word on it — what the numbers stand on."""
    args = _args(models="vendor/model-a")
    for stage in bench.STAGES:
        asyncio.run(bench.run(stage, args))
        asyncio.run(bench.judge(stage, args))
    bench.report()
    for stage in bench.STAGES:
        text = (bench.HOME / f"{stage}.md").read_text(encoding="utf-8")
        assert "`vendor/model-a`" in text and "**Судья Gemini 4 Argon:**" in text, stage
        assert "**Судья Claude Opus 5.5:**" in text, stage
    read = (bench.HOME / "read.md").read_text(encoding="utf-8")
    assert "✓ [явно]" in read and "verdict: verdict — про него" in read
    assert "[read.md](read.md)" in (bench.HOME / "report.md").read_text(encoding="utf-8")


def test_a_judge_that_favours_its_own_company_is_marked(offline, monkeypatch):
    """The owner's own suspicion, counted: against the other judge, on the
    same works — its own company's and everybody else's."""
    models = "google/own-model,vendor/other-model"
    asyncio.run(bench.run("write", _args(models=models)))
    first, second = (m for _n, m in bench.JUDGES)

    def judged_by(kind):
        async def verdict(system, user, max_tokens=1500, model=None, timeout=None, effort=None):
            own = kind == "biased" and "own-model" in user
            fit = 9 if own else 6
            return json.dumps({"contradictions": [], "fit": fit, "alive": fit, "would_talk": fit,
                               "compact": fit, "russian_errors": 0})
        return verdict

    monkeypatch.setitem(myself._real, "generate_text", judged_by("biased"))
    asyncio.run(bench.judge("write", _args(models=models, judges=first)))
    monkeypatch.setitem(myself._real, "generate_text", judged_by("fair"))
    asyncio.run(bench.judge("write", _args(models=models, judges=second)))
    found = bench.own_company("write")
    assert any("Gemini 4 Argon" in line and "подсуживает своим" in line for line in found)
    assert not any("Claude Opus 5.5" in line and "подсуживает" in line for line in found)


def test_a_failure_of_the_models_own_counts_and_is_not_given_another_go(offline, monkeypatch):
    """A broken JSON is the model's own doing — in the app it would cost that
    reading too — so it stays a failure in its row, and is not paid for again."""
    async def broken(*args, **kwargs):
        raise RuntimeError("Чтение вернулось битым JSON-ом: Expecting ',' delimiter")

    monkeypatch.setitem(myself._real, "think", broken)
    asyncio.run(bench.run("read", _args(models="vendor/model-a")))
    calls = len(offline)
    monkeypatch.setitem(myself._real, "think", lambda *a, **k: pytest.fail("asked again"))
    asyncio.run(bench.run("read", _args(models="vendor/model-a")))
    assert len(offline) == calls
    assert "битым JSON" in bench._load(bench._at("read", "timur", "vendor/model-a"))["error"]
