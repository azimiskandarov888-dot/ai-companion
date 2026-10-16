"""The first round of choosing the models (bench.py, bench_people.py).

What is pinned: the made-up people are whole and their truth is consistent
with what they said; every agent's job is the app's own call; a quote that was
never said is caught by code; the numbers are counted as they claim; and the
whole round runs end to end — here without a single paid call.
"""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import pytest

import bench
import bench_people
import myself
from app import matchmaker, reading


# ── the people ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize("person", bench_people.PEOPLE, ids=lambda p: p["id"])
def test_each_person_is_whole(person):
    assert len(person["talks"]) == 3
    ids = [i for i, _t, _w in person["facts"]] + [i for i, _t in person["bob_facts"]]
    assert len(ids) == len(set(ids))
    assert all(w in (1, 2, 3) for _i, _t, w in person["facts"])
    assert {k for k, _w, _y in person["traps"]} <= {"suggested", "retracted", "misheard", "joke",
                                                    "elsewhere", "their_word"}
    assert len(person["must_find"]) >= 4 and len(person["must_not"]) >= 3
    assert set(reading._REQUIRED) <= set(person["reading"]) and person["reading"]["verdict"]
    said = bench_people.transcript(person)
    # He says his own name in the talks — the writer must keep it.
    assert f"Я {person['bob']['name']}" in said or f"А я {person['bob']['name']}" in said
    assert person["name"].split()[0] in said


def test_what_the_traps_are_made_of_was_really_said():
    said = {p["id"]: bench_people.transcript(p) for p in bench_people.PEOPLE}
    for pid, words in (("timur", ("две сестры", "миллионер", "Азис", "с тренировки")),
                       ("olga", ("про визор", "медсестра", "в Казани", "кот болеет", "медик", "не особо верующая")),
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
    assert s == {"recall": round(100 * (total - 6) / total), "invented": 1, "traps": 1, "owner": 1, "bob": 2}


def test_a_quote_never_said_is_caught_by_code():
    olga = bench_people.by_id("olga")
    result = {"verdict": "Говорит «Я сама за себя» и «я всегда мечтала петь на сцене»."}
    assert bench.fake_quotes(result, olga) == ["я всегда мечтала петь на сцене"]


def test_a_reading_and_a_writer_are_counted():
    olga = bench_people.by_id("olga")
    s = bench.score_read(olga, {"found": [True, True, False, True, True, True, True], "wrong": [False, True],
                                "invented": ["a", "b"], "specific": 8, "useful": "7",
                                "russian_errors": 1}, {"verdict": "ok"})
    assert s["found"] == round(100 * 5 / len(olga["must_find"])) and s["wrong"] == 1
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
