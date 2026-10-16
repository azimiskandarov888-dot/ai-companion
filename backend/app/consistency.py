"""What he has said is law; what is only written is a draft — and no second model.

The owner, 2026-10-16, of «the code only fills empty fields»: «вдруг написанное
раньше было не совсем точным, и нам все-таки нужно его хоть как-то исправить».
So two rules, the way it is between people:

  · WHAT HE HAS SAID OUT LOUD IS LAW. The person heard it: to change it quietly
    would be to lie. The scribe keeps it (memory: what he said about himself),
    and before every reply he is told to hold to it — and that where his
    description says otherwise, what he said is true (companion).
  · WHAT IS ONLY WRITTEN IS A DRAFT. Nobody has heard it. The writer of the
    next layer, in the same call, checks it against what he said and puts
    right what disagrees (matchmaker «revise»).

And the same day, of a separate model checking him after every layer: «это
тупо… Можем ли мы просто поставить запрет?… нежели чем создавать отдельного
агента». Right again: it was a cheap model second-guessing a stronger writer,
and in its live test it «fixed» a sixteen-year-old's friend to twenty-two. So
there is no model here — only what the code holds whatever a model sends
(admit): who he is to the person is never revised, and a revision keeps the
same kind of value and most of what was there — put right, not replaced
(persona.merge_growth's fear: «how somebody's friend quietly becomes a
different man»). Whether a writer keeps to what he said is measured once,
when the writer is chosen (bench.py, «contradictions») — not paid for after
every layer.
"""

from __future__ import annotations

import re

from . import matchmaker

#: Who he is to the person: his name, man or woman, his age — chosen for them
#: (a teenager's friend is a peer: matchmaker.wished) — and how he addresses
#: them. Never revised; what does not agree with them is put right instead.
FIXED = frozenset({"name", "gender", "age", "address"})
#: What a revision may touch: everything else the writer writes.
REVISABLE = frozenset(matchmaker.FIELD_HINTS) - FIXED

#: «Puts right, does not replace»: of a value long enough to tell (MEASURED_FROM
#: different words or more), at least KEEPS of its words stay. Words by their
#: first letters, so that «работал» put right as «работала» is still kept.
KEEPS = 0.5
MEASURED_FROM = 6
_STEM = 5
_WORD = re.compile(r"\w{3,}")


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


def admit(before: dict, proposed: dict | None) -> dict:
    """What of the writer's revisions may be made to `before`: a field already
    written and open to revision, the same kind of value, put right and not
    replaced. Everything else is dropped, quietly — the layer still goes in."""
    before = before or {}
    return {f: v for f, v in (proposed or {}).items()
            if f in REVISABLE and before.get(f) and v != before[f]
            and _same_kind(before[f], v) and keeps_him(before[f], v)}
