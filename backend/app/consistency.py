"""What he has said is law; what is only written is a draft — and the check between.

The owner, 2026-10-16, of «the code only fills empty fields»: «вдруг написанное
раньше было не совсем точным, и нам все-таки нужно его хоть как-то исправить»
— and of a check that would hold him to what was written: «с моими поправками
это может не сработать». He was right. So two rules, the way it is between people:

  · WHAT HE HAS SAID OUT LOUD IS LAW. The person heard it: to change it quietly
    would be to lie, and they would notice. The scribe keeps it (memory: what
    he said about himself).
  · WHAT IS ONLY WRITTEN IS A DRAFT. Nobody has heard it — when it is wrong, it
    may be put right: a writer may propose to revise it (matchmaker «revise»).

After every layer and every deepening — between talks, so that no reply waits
for it — one cheap call (config.CHECKER_MODEL) reads him against the law:
which proposed revisions touch what he has said aloud (rejected), and where
anything in him, old or new, contradicts what he said or contradicts itself
(fixes: applied last, and they win).

And the code holds what a model may forget (persona.merge_growth: «accepting
that once is how somebody's friend quietly becomes a different man»): a
revision or a fix puts right, it does not replace him — the same kind of
value, and most of what was there still there (keeps_him); a fix only corrects
what is written, never writes what was not. The check never raises: when it
cannot read him, no revision passes — nothing is changed unchecked — and no
fix is made; the next check reads all of him again.
"""

from __future__ import annotations

import datetime
import json
import re
import sys

from . import brain, config, matchmaker

#: Who he is to the person: his name, man or woman, his age — chosen for them
#: (a teenager's friend is a peer: matchmaker.wished) — and how he addresses
#: them. No model changes these; what does not agree with them is put right
#: instead. A live check, 2026-10-16, «fixed» a sixteen-year-old's friend to
#: twenty-two by his year of birth.
FIXED = frozenset({"name", "gender", "age", "address"})
#: What a revision or a fix may touch: everything else the writer writes.
REVISABLE = frozenset(matchmaker.FIELD_HINTS) - FIXED

#: «Puts right, does not replace»: of a value long enough to tell (MEASURED_FROM
#: different words or more), at least KEEPS of its words stay. Words by their
#: first letters, so that «работал» put right as «работала» is still kept.
KEEPS = 0.5
MEASURED_FROM = 6
_STEM = 5
_WORD = re.compile(r"\w{3,}")

_SYSTEM = """Ты сверщик собеседника. Тебе дают: каким он был написан раньше; новый слой, который о нём только что написали (он заполняет пустые поля, а списки дописывает к старым); поправки, которые писатель предлагает к написанному раньше; и что он САМ уже сказал о себе вслух в разговорах — это закон: человек это слышал.

Сделай две вещи и больше ничего:
1. rejected — какие из предложенных поправок трогают то, что он уже сказал вслух (хотя бы частично). Их нельзя: человек это слышал.
2. fixes — во всём, что получится (написанное раньше с принятыми поправками и новый слой), найди поля, которые противоречат сказанному вслух или друг другу: возраст и прожитое, годы, город, имена, кто кому кто. Правь в пользу сказанного вслух; если вслух не было ни того, ни другого — в пользу поправки, потом — написанного раньше. Для каждого такого поля дай его ПОЛНОЕ новое значение того же вида (строку — строкой, список — всем списком, старое и новое вместе): поменяй только противоречащее, всё остальное сохрани слово в слово.

Имя, пол, возраст и обращение не меняются никогда: если с ними что-то не сходится (год рождения, прожитое, школа, работа), правь это другое под них. Годы считай от сегодняшней даты.

Ничего не улучшай на свой вкус и не переписывай то, что не противоречит. Нечего отклонить — rejected пустой; нет противоречий — fixes пустой.

Ответь ТОЛЬКО JSON такого вида: {"rejected": [имена полей], "fixes": {имя поля: новое значение}}"""


def _shown(fields: dict) -> str:
    keep = {k: v for k, v in (fields or {}).items()
            if not str(k).startswith("_") and k not in ("voice", "layers")}
    return json.dumps(keep, ensure_ascii=False, indent=1) if keep else "— нет"


def _stems(value) -> set[str]:
    if isinstance(value, dict):
        return {s for v in value.values() for s in _stems(v)}
    if isinstance(value, list):
        return {s for v in value for s in _stems(v)}
    return {w[:_STEM] for w in _WORD.findall(str(value).lower())}


def keeps_him(old, new) -> bool:
    """Is `new` the same thing put right — not something else in its place?"""
    was = _stems(old)
    return len(was) < MEASURED_FROM or len(was & _stems(new)) / len(was) >= KEEPS


def _same_kind(old, new) -> bool:
    """A line stays a line, a list a list of the same things — what is shown
    to him (persona.build_persona_block) is built by the kind it was written."""
    if isinstance(old, list):
        kinds = {type(item) for item in old} or {str, dict}
        return (isinstance(new, list) and bool(new)
                and all(type(item) in kinds and str(item).strip() for item in new))
    if isinstance(old, (str, int)) and not isinstance(old, bool):
        return isinstance(new, str) and bool(new.strip())
    return False


def _as_built(field: str, before: dict, layer: dict, revise: dict):
    """What `field` will be once this layer and these revisions are in
    (shaping.grown): a revision; else what was written; else the layer's —
    and a list the layer adds to, both."""
    if field in revise:
        return revise[field]
    old, new = before.get(field), layer.get(field)
    if isinstance(old, list) and isinstance(new, list):
        return old + new
    return old or new


def nothing_checked() -> dict:
    """What a check that could not run allows: no revision, no fix."""
    return {"revise": {}, "fixes": {}}


async def check(*, before: dict, layer: dict | None = None, proposed: dict | None = None,
                spoken: str = "") -> dict:
    """{"revise": the proposed revisions that may be made, "fixes": {field:
    value} that put right what contradicts} — never raises."""
    before, layer, proposed = dict(before or {}), dict(layer or {}), dict(proposed or {})
    model = config.CHECKER_MODEL
    if not brain.can_call(model):
        return nothing_checked()
    asked = (f"СЕГОДНЯ: {datetime.date.today().isoformat()}\n\n"
             f"БЫЛ НАПИСАН РАНЬШЕ:\n{_shown(before)}\n\nНОВЫЙ СЛОЙ:\n{_shown(layer)}\n\n"
             f"ПРЕДЛОЖЕННЫЕ ПОПРАВКИ К НАПИСАННОМУ РАНЬШЕ:\n{_shown(proposed)}\n\n"
             f"ЧТО ОН САМ СКАЗАЛ О СЕБЕ ВСЛУХ (закон):\n{spoken.strip() or '— пока ничего'}")
    try:
        # It thinks a little: «born in 1975» against «мне сорок» is arithmetic.
        raw = await brain.generate_text(_SYSTEM, asked, max_tokens=2_500, model=model,
                                        timeout=90, effort="low")
        m = re.search(r"\{.*\}", raw or "", re.S)
        got = json.loads(m.group(0)) if m else None
    except Exception as e:  # noqa: BLE001 — a check that failed costs a check
        print(f"  · consistency check skipped ({type(e).__name__}: {e})", file=sys.stderr, flush=True)
        return nothing_checked()
    if not isinstance(got, dict):
        return nothing_checked()

    # Silence about the proposals is not a yes.
    said_no = got.get("rejected")
    refused = (set(proposed) if not isinstance(said_no, list)
               else {f for f in said_no if isinstance(f, str)})
    revise = {f: v for f, v in proposed.items()
              if f not in refused and f in REVISABLE
              and _same_kind(before.get(f), v) and keeps_him(before.get(f), v)}

    fixes = {}
    for f, v in (got.get("fixes") if isinstance(got.get("fixes"), dict) else {}).items():
        now = _as_built(f, before, layer, revise) if f in REVISABLE else None
        if now and v != now and _same_kind(now, v) and keeps_him(now, v):
            fixes[f] = v

    if proposed or fixes:
        print(f"  ✎ checked: revised {sorted(revise) or '—'}, refused "
              f"{sorted(set(proposed) - set(revise)) or '—'}, fixed {sorted(fixes) or '—'}",
              flush=True)
    return {"revise": revise, "fixes": fixes}
