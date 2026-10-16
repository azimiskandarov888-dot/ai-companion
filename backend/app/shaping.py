"""One companion, written over time — from a blank to somebody, and on.

The owner, 2026-10-09: «Мы не должны создавать отдельного агента для этого.
Я думал, тень будет тем же самым компаньоном. Только сначала он будет как
пустая бланка. Сперва с рандомным именем. И если у юзера будут какие-то
предпочтения… с самого начала он будет с ними, но все еще пустой… В реальной
жизни они открываются со временем, а у нас они будут создаваться со временем,
потому что, чтобы их создать, мы должны знать о человеке. И в итоге для юзера
… это выглядит одно и то же». And of what comes after: «its not one build.
its a build that we are always shaping and making better».

── BORN BLANK ──────────────────────────────────────────────────────────────

A random name, the person's own wishes (gender, age, anything they wrote) —
and nothing else (matchmaker.create_blank: no model, no wait). He talks
plainly; what he says about himself is kept by the scribe and is law for
everything written after (persona._BLANK).

── WRITTEN IN LAYERS, IN THE ORDER PEOPLE OPEN UP ──────────────────────────

After every talk the reader reads ALL their talks afresh (reading.read_talks),
and the writer writes the next layer of him once it is time — each layer once,
never rewritten, everything already written or said kept as law
(matchmaker.LAYERS, write_layer):

  1 · what he is like — character, manner, where he lives, what he does:
      after the first real talk. From the second, he shows a little of himself.
  2 · what he lives for, and what he is for THIS person — his subject, what he
      wants to learn from them, his people, his things: when the reader is
      sure — two readings in a row name the same need (reading.same_need), as
      every inference about a person here needs two — never before the second
      reading, and at the fifth whatever it says (the owner's choice:
      «when the reader is sure»).
  3 · his depths — his story, his faults, the contradiction, what has not
      healed: once they KNOW each other (meeting.stage 2, ~2,000 of the
      person's words), as a friend's depths come out after weeks, not days.

── BETWEEN TALKS, NEVER DURING ONE ─────────────────────────────────────────

A layer is written in the background when a talk ends, and becomes part of
him as the next one begins (settle). Somebody who says goodbye and then «а,
слушай…» is still talking to the same man.

── AND THEN HE GOES ON BEING SHAPED ───────────────────────────────────────

Once all of him is written, the reader re-reads on its own schedule
(reading.keep_reading), and whenever it understands something new about what
the person needs, the writer adds to him (persona.deepen) — only adding,
never contradicting what he is or anything he has said.

── WHAT IT COSTS ───────────────────────────────────────────────────────────

A reading after each of the first two to five talks, a one-line comparison
after each, three layers — roughly $1–2 a person, once, on the current models
through OpenRouter. An estimate: the owner's test prints real prices.
"""

from __future__ import annotations

import sys
import time

from . import (brain, config, consistency, learn, matchmaker, meeting, memory, mood, persona,
               reading, voices, young)

#: The second layer — what he is for this person — never before this reading…
FIRST_READ_TO_SHAPE = 2
#: …and at this one whatever the reader says.
LAST_READ_UNSURE = 5
#: A talk in which the person said less than this adds nothing worth reading:
#: «привет — пока» is not a second evening.
MIN_NEW_WORDS = 40
#: His depths once they know each other (meeting.KNOWN_AT: «знакомы»).
DEPTHS_AT_STAGE = 2

#: Where the reader's own count is kept: in the reading, the most private file
#: the app keeps and never sends anywhere — not in his persona. A new friend
#: starts it over (erase._FRIENDSHIP_COUNTERS).
STATE = "_becoming"

#: Whose layers are being written right now. A goodbye and the line closing
#: both end a talk, seconds apart, and one reading is enough.
_busy: set[str] = set()


def transcript(user_id: str, name: str) -> str:
    """Every talk so far, as the reader and the writer are given it."""
    him = (name or "ОН").upper()
    blocks = []
    for n, talk in enumerate(memory.talks(user_id), 1):
        lines = "\n".join(
            f"{'ЧЕЛОВЕК' if t['role'] == 'user' else him}: {t['content']}" for t in talk
        )
        blocks.append(f"— разговор {n} —\n{lines}")
    return "\n\n".join(blocks)


def waiting(user_id: str) -> bool:
    """Is a layer of this person's companion still to be written by the app?"""
    if not persona.has_persona(user_id):
        return False
    who = persona.load_persona(user_id)
    # HELD: the owner's own test writes the layers by hand, one model at a
    # time (myself.py), and the app must not get there first.
    return (persona.written(who) < len(matchmaker.LAYERS)
            and not who.get("_held") and not who.get("_next"))


async def after_talk(user_id: str) -> None:
    """A talk has ended: read the person, and write the next layer of him if it
    is time. Background work: never raises, and nobody waits for it."""
    if user_id in _busy:
        return
    _busy.add(user_id)
    try:
        await _after_talk(user_id)
    except Exception as e:  # noqa: BLE001 — a layer a talk later is no failure
        print(f"  · shaping skipped ({e})", file=sys.stderr, flush=True)
    finally:
        _busy.discard(user_id)


async def _after_talk(user_id: str) -> None:
    if not waiting(user_id):
        return
    # Nothing about a child is kept — no reading, no log past today — so there
    # is nothing to write him from. He stays a blank; open (HANDOVER §0).
    if young.keeps_nothing(user_id) or not brain.can_call(config.WRITER_MODEL):
        return
    layer = persona.written(persona.load_persona(user_id)) + 1
    words = memory.words_said(user_id)

    if layer <= 2:
        if not await _read(user_id, words) and layer == 2:
            return
        state = (reading.load(user_id) or {}).get(STATE) or {}
        if not state:
            return
        if layer == 2:
            if state["reads"] < FIRST_READ_TO_SHAPE:
                return
            if not state.get("sure") and state["reads"] < LAST_READ_UNSURE:
                return
    elif meeting.stage(words) < DEPTHS_AT_STAGE:
        return
    else:
        await learn.learn_from_conversation(user_id, farewell=True)

    proposed: dict = {}
    fields = await write(user_id, layer, revisions=proposed)
    # What he has said aloud is law, what is only written may be put right —
    # and the check between is consistency.py's, here, between talks.
    who = persona.load_persona(user_id)
    checked = await consistency.check(before=who, layer=fields, proposed=proposed,
                                      spoken=memory.bob_self_context(user_id))
    if waiting(user_id):     # still the same companion: nobody started over meanwhile
        persona.save_persona(user_id, {**persona.load_persona(user_id),
                                       "_next": {"layer": layer, "fields": fields, **checked}})
        print(f"  ✎ {user_id[:8]}: layer {layer} («{matchmaker.LAYERS[layer - 1]['name']}») "
              "written — part of him from the next talk", flush=True)


async def _read(user_id: str, words: int) -> bool:
    """Read all their talks afresh, if enough was said since the last reading.
    Returns whether a reading happened."""
    before = reading.load(user_id) or {}
    state = dict(before.get(STATE) or {})
    if words - int(state.get("words") or 0) < MIN_NEW_WORDS:
        return False
    if not brain.can_call(config.READING_MODEL):
        return False
    # What he said about himself is in memory before anyone reads or writes from it.
    await learn.learn_from_conversation(user_id, farewell=True)
    said = transcript(user_id, persona.persona_name(persona.load_persona(user_id)))
    fresh = await reading.read_talks(said)
    verdict = str(fresh.get("verdict") or "")
    verdicts = list(state.get("verdicts") or [])
    sure = bool(verdicts) and await reading.same_need(verdicts[-1], verdict)
    state.update(reads=int(state.get("reads") or 0) + 1, words=words,
                 verdicts=(verdicts + [verdict])[-3:], sure=sure)
    kept = reading.with_what_stays(before, fresh)
    kept.update({STATE: state, "_read_at_visit": memory.visits_so_far(user_id),
                 "_confirmed_at_read": mood.confirmed_count(user_id)})
    reading.save(user_id, kept)
    print(f"  ✎ {user_id[:8]}: read {state['reads']}, "
          f"{'sure' if sure else 'not sure yet'}", flush=True)
    return True


async def write(user_id: str, layer: int, said: str | None = None, *,
                revisions: dict | None = None) -> dict:
    """The writer: the next layer of this companion, for this person —
    `revisions` filled with what it proposes to put right (matchmaker)."""
    who = persona.load_persona(user_id)
    context = matchmaker.layer_context(
        now=who,
        his_words=memory.bob_self_context(user_id),
        facts=memory.facts_context(user_id),
        brief=reading.as_brief(reading.load(user_id)),
        talks=said if said is not None else transcript(user_id, persona.persona_name(who)),
        band=young.of(user_id),
    )
    return await matchmaker.write_layer(context, layer, who, revisions=revisions)


def grown(who: dict, layer: int, fields: dict, *, revise: dict | None = None,
          fixes: dict | None = None) -> dict:
    """He, with one more layer: the new layer fills only empty places; what
    was only written and checked unsaid may be put right (`revise`); and what
    contradicted what he has said aloud is corrected (`fixes`, last — they
    win) — consistency.py. And the same voice the person has been hearing,
    sounding now like who he is turning out to be (voices.style_for)."""
    out = dict(who)
    for key, value in fields.items():
        if key == "more" and out.get("more"):
            # The one open field: each layer adds to it, nothing in it is replaced.
            out["more"] = persona.merge_growth(out, {"more": value})["more"]
        elif not out.get(key):
            out[key] = value
    for key, value in {**(revise or {}), **(fixes or {})}.items():
        if key in consistency.REVISABLE:
            out[key] = value
    out["layers"] = max(persona.written(who), layer)
    voice = who.get("voice") if isinstance(who.get("voice"), dict) else {}
    if voice.get("name"):
        out["voice"] = {"name": voice["name"], "style": voices.style_for(out)}
    out.pop("_next", None)
    return out


def settle(user_id: str) -> bool:
    """A layer is waiting and nobody is mid-talk: it becomes part of him, now.
    Cheap — one small file — so it is asked at the start of every turn."""
    if not persona.has_persona(user_id):
        return False
    who = persona.load_persona(user_id)
    waiting_layer = who.get("_next")
    if not isinstance(waiting_layer, dict) or memory.in_a_talk(user_id):
        return False
    persona.save_persona(user_id, grown(who, int(waiting_layer.get("layer") or 0),
                                        dict(waiting_layer.get("fields") or {}),
                                        revise=dict(waiting_layer.get("revise") or {}),
                                        fixes=dict(waiting_layer.get("fixes") or {})))
    print(f"  ✎ {user_id[:8]}: {who.get('name')} — layer {waiting_layer.get('layer')} is part "
          "of him now", flush=True)
    return True
