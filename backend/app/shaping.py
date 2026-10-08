"""He is shaped, never built once — from a shadow to somebody, and on.

The owner, 2026-10-08: «we won't have an interviewer and from the very
beginning we will be talking to our regular voice AI which from the beginning
would be like a shadow with no exact personality like real people do in real
world and after a while after several conversations we are going to know
exactly what kind of person our user need and we would shape the companion to
it». And of what comes after: «it will be created when the reader and writer
would know that it is a proper time to. then afterwards they will add more
stuff to the companion. shaping its character, personality etc. so its not
one build. its a build that we are always shaping and making better».

── THE SHADOW ──────────────────────────────────────────────────────────────

He begins as what a stranger shows on the first evening — a name, an age, a
place, what he does (matchmaker.create_shadow) — and nothing of a character.
He talks plainly and says little about himself (persona.is_shadow), and what
he does say is kept by the scribe and becomes law for whoever writes him.

── WHEN HE BECOMES SOMEBODY: WHEN THE READER IS SURE ──────────────────────

After every talk the reader reads ALL their talks so far, afresh
(reading.read_talks). When two readings in a row name the same need
(reading.same_need) the reader is sure — twice, the way every inference about
a person in this app needs two (mood.CONFIRMED_AT) — and the writer writes
him: the sketch the dice chose, unfolded for what this person lacks, with
every word he has said about himself kept (matchmaker.portrait_context).
Never before the second reading: one evening with a stranger shows too little.
Never later than the fifth: a shadow for longer than that is a bore, and a
reader still wavering by then is wavering between true things. (The owner's
choice of the three he was offered: «when the reader is sure».)

── BETWEEN TALKS, NEVER DURING ONE ─────────────────────────────────────────

He is written in the background when a talk ends, and becomes it when the
next one begins (settle). Somebody who says goodbye and then «а, слушай…» is
still talking to the same stranger: a person does not turn into somebody
else mid-sentence.

── AND THEN HE GOES ON BEING SHAPED ───────────────────────────────────────

From then on the reader re-reads on its own schedule (reading.keep_reading),
and whenever it understands something new about what the person needs, the
writer adds to him (persona.deepen) — only adding, never contradicting what
he is or anything he has said.

── WHAT IT COSTS ───────────────────────────────────────────────────────────

A reading after each of the first two to five talks, a one-line comparison
after each, and one portrait — roughly $0.5–1 a person, once, on the current
models through OpenRouter. An estimate: the owner's test prints real prices.
"""

from __future__ import annotations

import sys
import time

from . import (brain, config, learn, matchmaker, memory, mood, persona, reading, voices,
               young)

#: The earliest reading after which he may be written…
FIRST_READ_TO_SHAPE = 2
#: …and the reading after which he is written, sure or not.
LAST_READ_AS_SHADOW = 5
#: A talk in which the person said less than this adds nothing worth reading:
#: «привет — пока» is not a second evening.
MIN_NEW_WORDS = 40

#: Where the shadow's readings are counted: in the reading, which is the most
#: private file the app keeps and is never sent anywhere — not in his persona.
#: A new friend starts this count over (erase._FRIENDSHIP_COUNTERS).
STATE = "_shadow"

#: Whose becoming is being worked on right now. A goodbye and the line
#: closing both end a talk, seconds apart, and one reading is enough.
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


async def after_talk(user_id: str) -> None:
    """A talk has ended: read the person — and, once the reader is sure, write
    him. Background work: never raises, and nobody waits for it."""
    if user_id in _busy:
        return
    _busy.add(user_id)
    try:
        await _after_talk(user_id)
    except Exception as e:  # noqa: BLE001 — a shadow a little longer is no failure
        print(f"  · shaping skipped ({e})", file=sys.stderr, flush=True)
    finally:
        _busy.discard(user_id)


def waiting(user_id: str) -> bool:
    """Is this person's companion a shadow the app may still write?"""
    if not persona.has_persona(user_id):
        return False
    who = persona.load_persona(user_id)
    # HELD: the owner's own test writes him by hand, one model at a time
    # (myself.py), and the app must not get there first.
    return persona.is_shadow(who) and not who.get("_held") and not who.get("_portrait")


async def _after_talk(user_id: str) -> None:
    if not waiting(user_id):
        return
    # Nothing about a child is kept — no reading, no log past today — so there
    # is nothing to grow sure from. He stays a shadow; open (HANDOVER §0).
    if young.keeps_nothing(user_id) or not brain.can_call(config.READING_MODEL):
        return
    before = reading.load(user_id) or {}
    state = dict(before.get(STATE) or {})
    words = memory.words_said(user_id)
    if words - int(state.get("words") or 0) < MIN_NEW_WORDS:
        return

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
    print(f"  ✎ shadow {user_id[:8]}: read {state['reads']}, "
          f"{'sure' if sure else 'not sure yet'}", flush=True)

    if state["reads"] < FIRST_READ_TO_SHAPE:
        return
    if not sure and state["reads"] < LAST_READ_AS_SHADOW:
        return
    written = await portrait(user_id, said)
    if waiting(user_id):     # still the same shadow: nobody started him over meanwhile
        persona.save_persona(user_id, {**persona.load_persona(user_id), "_portrait": written})
        print(f"  ✎ shadow {user_id[:8]}: written — he is {written.get('name')} "
              "from the next talk", flush=True)


async def portrait(user_id: str, said: str | None = None) -> dict:
    """The writer: this shadow, unfolded for this person."""
    who = persona.load_persona(user_id)
    context = matchmaker.portrait_context(
        talks=said if said is not None else transcript(user_id, persona.persona_name(who)),
        facts=memory.facts_context(user_id),
        brief=reading.as_brief(reading.load(user_id)),
        band=young.of(user_id),
    )
    written = persona.clean(await matchmaker.write_him(context, who.get("sketch") or ""))
    return becoming(who, written)


def becoming(shadow: dict, written: dict) -> dict:
    """The written man, keeping what the shadow already was out loud: his
    name, his gender and his age, and the voice the person has been hearing —
    how he sounds in it may now carry who he turned out to be."""
    out = {**written}
    for key in ("name", "gender", "age"):
        if shadow.get(key):
            out[key] = shadow[key]
    voice = shadow.get("voice") if isinstance(shadow.get("voice"), dict) else {}
    if voice.get("name"):
        out["voice"] = {"name": voice["name"], "style": voices.style_for(out)}
    if shadow.get("sketch"):
        out["sketch"] = shadow["sketch"]
    out.pop("shadow", None)
    return out


def settle(user_id: str) -> bool:
    """A portrait is waiting and nobody is mid-talk: he becomes it, now. Cheap
    — one small file — so it is asked at the start of every turn and call."""
    if not persona.has_persona(user_id):
        return False
    written = persona.load_persona(user_id).get("_portrait")
    if not isinstance(written, dict) or not written.get("name") or memory.in_a_talk(user_id):
        return False
    persona.save_persona(user_id, {**written, "_shaped_at": time.time()})
    print(f"  ✎ {user_id[:8]}: the shadow is {written.get('name')} now", flush=True)
    return True
