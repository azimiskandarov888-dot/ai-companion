"""Which voice each companion speaks in — his own, for good.

Every person gets a companion of his own, so every companion needs a voice of
his own: the owner, 2026-10-03 — «we are not having 2 ai companions. we need
hundred of them voices, and atleast 10 out of them must be russian».

── THE POOL ─────────────────────────────────────────────────────────────────

Google's thirty Gemini voices (docs/VOICES-RU.md). The owner heard all thirty
read the same words in Russian, blind: «all of them are briliant». They speak
English as well, so a companion keeps his voice in either language. Each has
the one word Google gives it, and the gender Google's own list gives it
(Chirp 3: HD) — except Pulcherrima, which Google files as a woman and the
owner heard as a man («23rd is more musculine voice rather then femenine»),
so she is nobody's voice: a woman who sounds like a man and a man the list
calls a woman are both wrong.

── A VOICE, AND WHOM IT PLAYS ───────────────────────────────────────────────

The same voice told whom it plays (`speech_metadata.style`) becomes a
different person: one of them read these words in 20.5 s as a man in his
seventies and in 12.6 s as a student of nineteen. So a companion's voice is a
voice from the pool AND a line about him — his age, his manner — taken from
his portrait when he is written, and kept with it.

── FOR GOOD ─────────────────────────────────────────────────────────────────

It is written into his persona once (`ensure`) and never chosen again: his
portrait grows (persona.deepen), and a friend whose voice changed one morning
is not the same friend. A persona written before this existed gets one the
first time it speaks, the same one every time it is asked (`choose` depends
on nothing that changes).
"""

from __future__ import annotations

import hashlib
import re

from . import aloud, persona

#: (name, gender, Google's word for it).
CATALOG: tuple[tuple[str, str, str], ...] = (
    ("Achird", "male", "Friendly"),
    ("Algenib", "male", "Gravelly"),
    ("Algieba", "male", "Smooth"),
    ("Alnilam", "male", "Firm"),
    ("Charon", "male", "Informative"),
    ("Enceladus", "male", "Breathy"),
    ("Fenrir", "male", "Excitable"),
    ("Iapetus", "male", "Clear"),
    ("Orus", "male", "Firm"),
    ("Puck", "male", "Upbeat"),
    ("Rasalgethi", "male", "Informative"),
    ("Sadachbia", "male", "Lively"),
    ("Sadaltager", "male", "Knowledgeable"),
    ("Schedar", "male", "Even"),
    ("Umbriel", "male", "Easy-going"),
    ("Zubenelgenubi", "male", "Casual"),
    ("Achernar", "female", "Soft"),
    ("Aoede", "female", "Breezy"),
    ("Autonoe", "female", "Bright"),
    ("Callirrhoe", "female", "Easy-going"),
    ("Despina", "female", "Smooth"),
    ("Erinome", "female", "Clear"),
    ("Gacrux", "female", "Mature"),
    ("Kore", "female", "Firm"),
    ("Laomedeia", "female", "Upbeat"),
    ("Leda", "female", "Youthful"),
    ("Sulafat", "female", "Warm"),
    ("Vindemiatrix", "female", "Gentle"),
    ("Zephyr", "female", "Bright"),
)
#: Heard as the other gender (see the module docstring) — in nobody's pool.
EXCLUDED = frozenset({"Pulcherrima"})
NAMES = frozenset(name for name, _, _ in CATALOG)

#: How a friend sounds whatever else he is — the line all thirty were heard
#: with, and liked with, in the owner's rounds.
MANNER = "warm, relaxed and natural, like a friend talking in person — not a narrator"

#: What in a portrait points at which of Google's words. The voice is chosen
#: among the ones that fit him; a portrait that says none of this gets one of
#: all of them.
_TEMPERS: tuple[tuple[re.Pattern, frozenset[str]], ...] = (
    (re.compile(r"спокойн|тих|невозмутим|размерен|calm|quiet|gentle|easy", re.I),
     frozenset({"Easy-going", "Even", "Gentle", "Soft", "Smooth", "Casual"})),
    (re.compile(r"весёл|весел|живой|энерг|бодр|задор|lively|cheer|energ|bubbly", re.I),
     frozenset({"Upbeat", "Lively", "Bright", "Excitable", "Breezy"})),
    (re.compile(r"тёпл|тепл|добр|ласков|мягк|warm|kind|soft", re.I),
     frozenset({"Warm", "Friendly", "Gentle", "Soft"})),
    (re.compile(r"серьёзн|серьезн|строг|основательн|сдержан|serious|stern|firm|reserved", re.I),
     frozenset({"Firm", "Informative", "Knowledgeable", "Even", "Clear"})),
    (re.compile(r"застенчив|стеснител|робк|скромн|shy|timid|modest", re.I),
     frozenset({"Soft", "Gentle", "Breathy", "Easy-going"})),
)
#: …and age. An old man is not «Youthful», a girl of sixteen is not «Mature».
_OLD = frozenset({"Mature", "Gravelly", "Even", "Informative", "Knowledgeable", "Warm", "Soft", "Gentle"})
_YOUNG = frozenset({"Youthful", "Bright", "Upbeat", "Lively", "Breezy", "Casual", "Easy-going", "Friendly"})
OLD_FROM = 55


def years(who: dict | None) -> int | None:
    """His age in years, when the portrait gives it in digits."""
    found = re.search(r"\d+", str((who or {}).get("age") or ""))
    return int(found.group()) if found else None


def _pool(who: dict | None) -> list[tuple[str, str, str]]:
    from . import tts   # tts imports this module

    gender = "female" if tts.is_female(who) else "male"
    return [v for v in CATALOG if v[1] == gender and v[0] not in EXCLUDED]


def _fits(voice: tuple[str, str, str], who: dict | None) -> int:
    """How many things about him this voice's word agrees with."""
    trait = voice[2]
    told = " ".join(str((who or {}).get(k) or "") for k in ("personality", "speech_style", "one_liner"))
    score = sum(1 for pattern, traits in _TEMPERS if pattern.search(told) and trait in traits)
    age = years(who)
    if age is not None:
        score += trait in (_OLD if age >= OLD_FROM else _YOUNG if age < 26 else frozenset())
    elif aloud.young(who):
        score += trait in _YOUNG
    return score


def _seed(who: dict | None) -> int:
    """A number that is his and does not change as his portrait grows."""
    who = who or {}
    stable = f"{who.get('name', '')}|{who.get('gender', '')}|{who.get('age', '')}|{who.get('home', '')}"
    return int(hashlib.sha256(stable.encode("utf-8")).hexdigest(), 16)


def style_for(who: dict | None) -> str:
    """Whom the voice plays: a man or a woman of his age, his manner, and how a
    friend sounds. In English — it is read by the voice, never heard."""
    from . import tts

    who = who or {}
    woman = tts.is_female(who)
    age = years(who)
    if age is not None and age < 18:
        person = f"a {age}-year-old {'girl' if woman else 'boy'}"
    elif age is not None:
        person = f"a {'woman' if woman else 'man'} of {age}"
    elif aloud.young(who):
        person = f"a young {'woman' if woman else 'man'}"
    else:
        person = "a woman" if woman else "a man"
    manner = re.sub(r"\s+", " ", str(who.get("personality") or "")).strip(" .;")
    if len(manner) > 90:
        manner = manner[:90].rsplit(" ", 1)[0].rstrip(",;")
    return f"{person}{f' ({manner})' if manner else ''}, {MANNER}"


def choose(who: dict | None) -> dict:
    """His voice: the best fit for him among his gender's voices, and among the
    equally fitting ones always the same one for the same him."""
    pool = _pool(who)
    best = max(_fits(v, who) for v in pool)
    fitting = [v for v in pool if _fits(v, who) == best]
    name = fitting[_seed(who) % len(fitting)][0]
    return {"name": name, "style": style_for(who)}


def of(who: dict | None) -> dict:
    """The voice his persona carries, or the one he would be given."""
    kept = (who or {}).get("voice")
    if isinstance(kept, dict) and kept.get("name") in NAMES:
        return {"name": kept["name"], "style": str(kept.get("style") or style_for(who))}
    return choose(who)


def ensure(user_id: str) -> dict:
    """Give this person's companion his voice, once, and keep it (see the
    module docstring). Returns his persona. The built-in template is nobody's
    and gets no file."""
    who = persona.load_persona(user_id)
    if persona.has_persona(user_id) and of(who) != who.get("voice"):
        who = persona.save_persona(user_id, {**who, "voice": of(who)})
    return who


# ── as the mouth is given it ───────────────────────────────────────────────

PREFIX = "gemini:"


def key(voice: dict) -> str:
    """A voice as tts.py is handed it — one string, so everything that keys on
    «which voice» (his first sounds, made once per voice) keeps working."""
    return f"{PREFIX}{voice['name']}|{voice.get('style', '')}"


def parse(voice_key: str | None) -> tuple[str, str] | None:
    """(name, style) back out of a key, or None for anything that is not one."""
    if not voice_key or not voice_key.startswith(PREFIX):
        return None
    name, _, style = voice_key[len(PREFIX):].partition("|")
    return (name, style) if name in NAMES or name in EXCLUDED else None
