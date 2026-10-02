"""HOW A SENTENCE SOUNDS SAID, NOT WRITTEN — in Russian and in English.

The owner, 2026-09-30, on «О, программирование — это мне всегда казалось
каким-то фокусом. Сам учишься или кто-то помогает?»: still fake, because it is
too perfect — «это не эссе, это не подготовленная переписка. Это живой
разговор, где должны быть ошибки, запинания, слова-паразиты». And again,
2026-10-02: «реальный человек в настоящем разговоре очень часто тормозит,
повторяет слова, и у него очень много этих слов-паразитов — добавь их в
достаточном количестве». Research and measurements: docs/SOUNDS-HUMAN.md.

WHY THIS IS CODE AND NOT A RULE. Told in every way we tried — a rule for live
speech, the same rule framed as a word-for-word transcript, the rule written in
speech itself, examples of live speech, the same thing as HIS manner in the
persona — the voice (Luna, without reasoning) still wrote clean prose: 0.6–0.9
small imperfections a reply, against 0.4–0.6 with no instruction at all (a
scripted A/B on the real prompt, 2026-09-30). Instruction tuning is what makes a
model's text unlike speech, and asking barely moves it (Reinhart et al., PNAS
2025).

HOW MANY. People are disfluent six to ten times in a hundred words (Fox Tree
1995; Shriberg 1994, 2001; Bortfeld et al. 2001: 5.6–6.7), about one and a
half of them repeats; and fifteen-to-sixteen-year-olds add a «like» about once
in twenty words on top (Tagliamonte 2005). The first version of this layer
added at most two a reply, about one — some three in a hundred words on
twenty-word replies, and fewer since the replies got short. Now it aims at the
rate itself: RATE in a hundred words, RATE_YOUNG for a companion under
YOUNG_UNTIL, counted on each piece as it is said.

WHAT, AND WHERE — each where a speaker actually makes it:

- a filled pause — «э-э…», «м-м…» / "uh", "um" — before the word he is reaching
  for, after a little word: hesitations gather before what is hard to plan
  (Maclay & Osgood 1959; Clark & Fox Tree 2002);
- the first word of a clause said twice — «я… я», «это… это» / "I… I",
  "it's… it's": repeats sit on the function word that opens a constituent
  (Clark & Wasow 1998);
- a word that holds the floor, by age — «ну», «вот», «как бы», «в общем»;
  «типа», «короче» for the young / "well", "I mean", "you know"; "like",
  "honestly" for the young — at the start of a sentence or after a comma; and
  in English «like» or «kind of» after «is», «was», «it's» before what follows;
- a hedge before the vague word — «казалось, ну, каким-то фокусом» / "it was,
  like, something";
- the vague «или там» in an either-or question / "or, like," for the young;
- «Я вот» as he begins on himself, «Ну, наверное…» as a sentence turns.

NEVER: a filled pause or a repeat as the reply's very first word — the reaction
comes first, and his first sound has already been made (first_sound.py);
inside his markers (//КАШЕЛЬ//); in a list; after an aside or before a word
that joins a clause on; in a piece under MIN_WORDS words; two in one place;
the same word twice in a reply; more than MAX_PER_SENTENCE in a sentence; and
nothing at all from a number or the words of a warning on (_EXACT).

Only the VOICE gets them. What is remembered, and read back later, is what he
meant — the clean reply; what is heard is how he said it.
"""

from __future__ import annotations

import math
import random
import re
from dataclasses import dataclass

from . import lang

#: Small imperfections in a hundred words this layer AIMS at — an adult
#: companion, and one under YOUNG_UNTIL, whose «типа» and «like» come on top.
#: What lands is less (short pieces, a cap per sentence, no word twice): on 640
#: of the voices' own replies, 5.5 and 7.5 in a hundred words — and the voice
#: writes 3.8 of its own («…», «ну», «вот»), so about 9 and 11 in all, the top
#: of what people make (6–10; Fox Tree 1995, Shriberg 2001) and, for the young,
#: Tagliamonte's «like» on top (2026-10-02).
RATE = 8.5
RATE_YOUNG = 12.0
YOUNG_UNTIL = 26
#: A multiplier on the rate: 1 as shipped, 0 for a test that compares what was
#: said word for word (conftest).
CHANCE = 1.0
#: At most, in one sentence and in one reply.
MAX_PER_SENTENCE = 2
MAX_PER_REPLY = 4
#: A piece shorter than this is said as written: «Ой. Сильно ударился?» is
#: already a reaction, and «Ну?» is already a listener.
MIN_WORDS = 4

#: Where exactness matters, nothing is roughened — from here to the end of the
#: reply: a number (a phone, a code, an address) or the words of a warning.
_EXACT = re.compile(
    r"\d|скор(?:ая|ую|ой)\b|полици|трубк|\bкод\b|\bкарт[ауые]\b|\bбанк|парол|врач"
    r"|\bambulance|\bpolice|hang up|\bcode\b|\bcard\b|\bbank\b|password|doctor|\bscam", re.I)

_WORD = re.compile(r"[А-Яа-яЁёA-Za-z]+(?:['’-][А-Яа-яЁёA-Za-z]+)*")
_RUSSIAN = re.compile(r"[А-Яа-яЁё]")
#: His markers — a cough, a laugh, the end — are never broken into.
_MARKER = re.compile(r"//[^/\s]+//")

# ── Russian ─────────────────────────────────────────────────────────────────

#: The vague words a speaker reaches for when the exact one is not there yet.
_VAGUE = re.compile(
    r"(?<![А-Яа-яЁё-])(?:как(?:ой|ая|ое|ие|им|ую|ого|ому|ом|ими|их)|что|чем|чего|кто|кого|"
    r"где|как|куда|когда|почему|откуда|чей|чья|чьё)-то(?![А-Яа-яЁё-])", re.I)
#: «или» that offers a second choice in a question — and is not «или нет».
_OR = re.compile(r"(?<=\s)или\s+(?!там\b|нет\b)(?=[А-Яа-яЁё])", re.I)
#: After these a comma is where the next clause is being planned — unless the
#: clause is already starting with a word that joins it on.
_JOINS = frozenset({"и", "а", "но", "что", "чтобы", "чтоб", "как", "когда", "если", "где",
                    "куда", "который", "которая", "которое", "которые", "потому", "хотя",
                    "да", "или", "ли", "ну", "вот", "там", "то", "либо", "пока", "раз",
                    "чем", "будто", "словно", "зато", "пусть"})
#: Words a hesitation does not follow: a conjunction wants its clause, and a
#: word said as an aside («наверное,») already is one.
_NOT_AFTER = frozenset({"и", "или", "а", "но", "да", "наверное", "конечно", "кстати",
                        "правда", "может", "вроде", "честно", "впрочем", "значит"})
#: Little words a pause or a repeat may follow or be.
_SMALL = frozenset({"я", "ты", "он", "она", "оно", "мы", "вы", "они", "это", "вот", "так",
                    "в", "во", "на", "у", "с", "со", "к", "по", "за", "из", "о", "об", "от",
                    "до", "для", "про", "мне", "меня", "тебе", "его", "её", "их", "там",
                    "тут", "же", "бы", "не", "что", "как", "мой", "моя", "моё", "свой",
                    "своя", "такой", "такая", "какой", "этот", "эта", "этой", "этим"})
#: …and the ones a clause may open on twice.
_REPEATABLE = frozenset({"я", "ты", "он", "она", "мы", "они", "это", "в", "на", "у", "мне",
                         "там", "так", "как", "что", "мой", "моя", "у", "с"})
_PAUSES = ("э-э…", "м-м…", "э…")
_MARKERS_START = ("Ну, ", "Вот, ", "В общем, ", "Слушай, ")
_MARKERS_START_YOUNG = ("Ну, ", "Короче, ", "Слушай, ", "Вот, ")
_MARKERS_COMMA = ("ну, ", "вот, ", "как бы, ")
_MARKERS_COMMA_YOUNG = ("ну, ", "типа, ", "вот, ", "короче, ")
#: How a hedge goes in before a vague word.
_HEDGES = (("ну", ", ну, "), ("как бы", " как бы "), ("я не знаю", ", я не знаю, "), ("…", "… "))

# ── English ─────────────────────────────────────────────────────────────────

_VAGUE_EN = re.compile(r"\b(?:something|somewhere|somehow|someone|somebody|stuff)\b", re.I)
_OR_EN = re.compile(r"(?<=\s)or\s+(?!not\b|no\b)(?=[A-Za-z])", re.I)
_JOINS_EN = frozenset({"and", "but", "or", "so", "that", "which", "who", "when", "if", "where",
                       "because", "cause", "though", "although", "while", "than", "like",
                       "then", "as", "until", "unless"})
_NOT_AFTER_EN = frozenset({"and", "or", "but", "so", "honestly", "actually", "maybe",
                           "probably", "anyway", "well", "like", "really"})
_SMALL_EN = frozenset({"a", "an", "the", "to", "of", "in", "on", "at", "for", "with", "about",
                       "my", "your", "his", "her", "our", "their", "some", "this", "that",
                       "these", "those", "into", "from", "is", "was", "were", "are", "it's",
                       "i'm", "be", "been", "just", "really", "so", "very"})
_REPEATABLE_EN = frozenset({"i", "i'm", "it's", "it", "we", "you", "the", "that", "my", "he",
                            "she", "they", "there", "this", "in", "on", "to", "and", "but"})
#: After these, «like» or «kind of» goes in before what follows: «it was like
#: really hard», «that's kind of cool».
_COPULA_EN = frozenset({"is", "was", "it's", "that's", "he's", "she's", "they're", "we're",
                        "i'm", "were", "are", "felt", "feels", "seems", "seemed", "looks",
                        "looked", "sounds", "sounded"})
_PAUSES_EN = ("uh", "um")
_INTENSIFIERS_EN = frozenset({"way", "really", "so", "very", "too", "much", "pretty", "super",
                              "quite", "not", "never", "always", "all"})
_MARKERS_START_EN = ("Well, ", "I mean, ", "So, ", "You know, ")
_MARKERS_START_YOUNG_EN = ("Like, ", "Honestly, ", "I mean, ", "So, ")
_MARKERS_COMMA_EN = ("you know, ", "I mean, ")
_MARKERS_COMMA_YOUNG_EN = ("like, ", "you know, ", "I mean, ")


@dataclass(frozen=True)
class _Edit:
    start: int
    end: int
    text: str
    word: str      # what it adds, so the same is never added twice in a reply
    weight: int


def young(persona: dict | None) -> bool:
    """Is this companion young enough for «типа» and «like»? From the persona's
    own age — digits, or the words of a teenage age."""
    age = str((persona or {}).get("age") or "").lower()
    found = re.search(r"\d+", age)
    if found:
        return int(found.group()) < YOUNG_UNTIL
    from . import young as _young   # local: young imports reading, which is heavy

    words = re.findall(r"\w+", age)
    tens = [w for w in words if w in _young._TENS or w.startswith(("двадцат", "twenty"))]
    if tens:                               # «восемьдесят семь» is not seven
        return all(w.startswith(("двадцат", "twenty")) for w in tens)
    return any(w in _young._WORDS for w in words)


class Speaker:
    """One reply, said aloud: how many small imperfections it has had so far,
    and which. Give it the reply's pieces in order."""

    def __init__(self, rng: random.Random | None = None, *, young: bool = False) -> None:
        self._rng = rng or random.Random()
        self._young = young
        self._english = lang.english()
        self._left = MAX_PER_REPLY
        self._used: set[str] = set()
        self._pieces = 0
        self._plain = False

    def say(self, piece: str) -> str:
        first = self._pieces == 0
        self._pieces += 1
        if self._plain or _EXACT.search(piece):
            self._plain = True             # exactness: plain from here on
            return piece
        if self._left <= 0 or len(_WORD.findall(piece)) < MIN_WORDS:
            return piece
        if bool(_RUSSIAN.search(piece)) == self._english:
            return piece                   # every edit here is of one language
        masked, held = _mask(piece)
        words = _WORD.findall(masked)
        rate = (RATE_YOUNG if self._young else RATE) * CHANCE
        expected = len(words) * rate / 100.0
        count = int(expected) + (self._rng.random() < expected - math.floor(expected))
        count = min(count, self._left)
        if count <= 0:
            return piece
        options = [e for e in self._options(masked, first) if e.word not in self._used]
        chosen = self._choose(masked, options, count)
        if not chosen:
            return piece
        self._left -= len(chosen)
        self._used.update(e.word for e in chosen)
        out = masked
        for edit in sorted(chosen, key=lambda e: e.start, reverse=True):
            out = out[:edit.start] + edit.text + out[edit.end:]
        return _unmask(out, held)

    def _options(self, text: str, first: bool) -> list[_Edit]:
        if self._english:
            return (_pauses_en(text, first) + _repeats(text, first, _REPEATABLE_EN)
                    + _markers_en(text, self._young) + _hedges_en(text, self._young)
                    + _there_en(text, self._young))
        return (_pauses(text, first) + _repeats(text, first, _REPEATABLE)
                + _markers(text, self._young) + _hedges(text) + _there(text)
                + _restarts(text, first))

    def _choose(self, text: str, options: list[_Edit], count: int) -> list[_Edit]:
        """Up to `count` of them, by weight, never two at one place, never two
        of the same word, never more than MAX_PER_SENTENCE in a sentence."""
        chosen: list[_Edit] = []
        pool = list(options)
        while pool and len(chosen) < count:
            edit = self._rng.choices(pool, weights=[e.weight for e in pool])[0]
            pool = [e for e in pool if e is not edit]
            if any(e.word == edit.word for e in chosen):
                continue
            if any(_near(text, e, edit) for e in chosen):
                continue
            sentence = _sentence_of(text, edit.start)
            if sum(_sentence_of(text, e.start) == sentence for e in chosen) >= MAX_PER_SENTENCE:
                continue
            chosen.append(edit)
        return chosen


def said(text: str, rng: random.Random | None = None, *, young: bool = False) -> str:
    """A whole reply said at once — sentence by sentence, as the pieces of a
    streamed one are."""
    speaker = Speaker(rng, young=young)
    sentences = re.findall(r"[^.!?…]+[.!?…]*\s*", text) or [text]
    return "".join(speaker.say(s.rstrip()) + s[len(s.rstrip()):] for s in sentences)


# ── the places ──────────────────────────────────────────────────────────────

def _mask(piece: str) -> tuple[str, list[str]]:
    """His markers out of the way: no edit may land inside one."""
    held: list[str] = []

    def hold(m: re.Match) -> str:
        held.append(m.group())
        return f"\x00{len(held) - 1}\x00"

    return _MARKER.sub(hold, piece), held


def _unmask(text: str, held: list[str]) -> str:
    for i, mark in enumerate(held):
        text = text.replace(f"\x00{i}\x00", mark)
    return text


def _sentence_of(text: str, at: int) -> int:
    return len(re.findall(r"[.!?…]\s", text[:at]))


def _near(text: str, a: _Edit, b: _Edit) -> bool:
    """Two edits with fewer than two words between them are one place."""
    lo, hi = sorted((a.start, b.start))
    return len(_WORD.findall(text[lo:hi])) < 2


def _sentence_start(text: str, at: int) -> bool:
    before = text[:at].rstrip()
    return not before or before[-1] in ".!?…" or before.endswith("\x00")


def _clause_starts(text: str) -> list[re.Match]:
    """The first word of each sentence and of each clause after a comma."""
    out = []
    for m in _WORD.finditer(text):
        before = text[:m.start()].rstrip()
        if not before or before[-1] in ".!?…,":
            out.append(m)
    return out


#: Words that may lose their capital after «Ну, » or "Well, " — the commonest
#: openers. Anything else keeps it: it may be a name, and «ну, азим» is wrong.
_STARTERS = frozenset({"а", "и", "но", "я", "ты", "он", "она", "мы", "они", "это", "мне",
                       "там", "тут", "так", "тогда", "наверное", "может", "хорошо", "после",
                       "зато", "главное", "давно", "сам", "сама", "что", "как", "когда",
                       "где", "все", "всё", "у", "в", "на", "с", "не", "просто", "даже"})
_STARTERS_EN = frozenset({"it", "it's", "that", "that's", "you", "we", "the", "so", "maybe",
                          "then", "there", "what", "how", "but", "and", "my", "this", "they",
                          "he", "she", "just", "not", "no", "yeah", "anyway", "probably"})


def _lowered(word: str, common: frozenset[str]) -> str:
    return word[:1].lower() + word[1:] if word.lower() in common else word


def _listed(left: str, right: str) -> bool:
    """Two words either side of a comma that end alike are a list — «шумный,
    тёплый», «сесть, выпить» — and nobody says «ну» in the middle of one."""
    return len(left) > 3 and len(right) > 3 and left[-2:].lower() == right[-2:].lower()


def _pauses(text: str, first: bool) -> list[_Edit]:
    """«э-э…» before the word he reaches for, after a little word."""
    edits = []
    words = list(_WORD.finditer(text))
    for prev, word in zip(words, words[1:]):
        w = word.group().lower()
        if len(w) < 5 or w in _SMALL or prev.group().lower() not in _SMALL:
            continue
        if text[prev.end():word.start()].strip():
            continue                       # a comma or a dash between: not mid-phrase
        pause = _PAUSES[(word.start() + len(w)) % len(_PAUSES)]
        edits.append(_Edit(word.start(), word.start(), f"{pause} ", pause, 2))
    return [e for e in edits if not (first and e.start == words[0].start())]


def _repeats(text: str, first: bool, repeatable: frozenset[str]) -> list[_Edit]:
    """«Я… я тоже» — the clause's first word said twice."""
    edits = []
    for m in _clause_starts(text):
        word = m.group()
        if word.lower() not in repeatable or (first and m.start() == 0):
            continue
        rest = re.match(r"[^.!?…,]*", text[m.start():]).group()
        if len(_WORD.findall(rest)) < 4:
            continue                       # a clause too short to stumble into
        again = word if word[:1] == "I" and (len(word) == 1 or word[1] in "'’") else word.lower()
        edits.append(_Edit(m.start(), m.end(), f"{word}… {again}", f"repeat:{word.lower()}", 2))
    return edits


def _markers(text: str, young: bool) -> list[_Edit]:
    """«Ну,» opening a sentence after the first; «, вот,» after a comma in a clause."""
    edits = []
    starts = _MARKERS_START_YOUNG if young else _MARKERS_START
    commas = _MARKERS_COMMA_YOUNG if young else _MARKERS_COMMA
    weight = 3 if young else 2
    for m in _WORD.finditer(text):
        before = text[:m.start()].rstrip()
        if before and before[-1] in ".!?…":
            lowered = _lowered(m.group(), _STARTERS)
            for pick in starts:
                edits.append(_Edit(m.start(), m.end(), pick + lowered, pick.strip(" ,").lower(), weight))
    for sentence in re.finditer(r"[^.!?…]+[.!?…]*", text):
        body = sentence.group()
        for c in re.finditer(r",\s+", body):
            before = _WORD.findall(body[:c.start()])
            after = _WORD.findall(body[c.end():])
            if (len(before) < 3 or len(after) < 2 or after[0].lower() in _JOINS | _NOT_AFTER
                    or before[-1].lower() in _NOT_AFTER or _listed(before[-1], after[0])):
                continue                   # an exclamation, a join, an aside, a list
            at = sentence.start() + c.end()
            for pick in commas:
                edits.append(_Edit(at, at, pick, pick.strip(" ,").lower(), weight))
    return edits


def _hedges(text: str) -> list[_Edit]:
    edits = []
    for m in _VAGUE.finditer(text):
        if _sentence_start(text, m.start()):
            continue                       # nothing said yet to hesitate after
        said_before = _WORD.findall(text[:m.start()])
        if said_before and said_before[-1].lower() in _NOT_AFTER:
            continue
        gap_start = len(text[:m.start()].rstrip())
        comma = text[gap_start - 1:gap_start] == ","
        for word, insert in _HEDGES:
            if word == "…":
                if not comma:
                    edits.append(_Edit(gap_start, m.start(), "… ", "…", 1))
            elif comma:
                edits.append(_Edit(m.start(), m.start(), insert.lstrip(", "), word, 1))
            else:
                edits.append(_Edit(gap_start, m.start(), insert, word, 1))
    return edits


def _there(text: str) -> list[_Edit]:
    edits = []
    for m in _OR.finditer(text):
        if "?" in text[m.end():].split(".")[0]:   # a question, and this sentence of it
            edits.append(_Edit(m.start(), m.end(), "или там ", "там", 3))
    return edits


def _restarts(text: str, first: bool) -> list[_Edit]:
    """«Я вот там не был» — the «вот» that holds the floor as he begins on himself."""
    edits = []
    for m in re.finditer(r"(?:(?<=[.!?…]\s)|^)Я(?=\s)", text):
        if first and m.start() == 0:
            continue
        following = _WORD.findall(text[m.end():])
        if following and following[0].lower() not in ("бы", "вот", "же", "и", "не", "ну"):
            edits.append(_Edit(m.start(), m.end(), "Я вот", "вот", 2))
    return edits


def _pauses_en(text: str, first: bool) -> list[_Edit]:
    """"a, uh, game" — before the word he reaches for, after a little word."""
    edits = []
    words = list(_WORD.finditer(text))
    for prev, word in zip(words, words[1:]):
        w = word.group().lower()
        if len(w) < 4 or w in _SMALL_EN or prev.group().lower() not in _SMALL_EN:
            continue
        if text[prev.end():word.start()].strip():
            continue
        pause = _PAUSES_EN[(word.start() + len(w)) % len(_PAUSES_EN)]
        edits.append(_Edit(prev.end(), prev.end(), f", {pause},", pause, 2))
    return [e for e in edits if not (first and e.start <= words[0].end())]


def _markers_en(text: str, young: bool) -> list[_Edit]:
    edits = []
    starts = _MARKERS_START_YOUNG_EN if young else _MARKERS_START_EN
    commas = _MARKERS_COMMA_YOUNG_EN if young else _MARKERS_COMMA_EN
    weight = 3 if young else 2
    for m in _WORD.finditer(text):
        before = text[:m.start()].rstrip()
        if before and before[-1] in ".!?…":
            lowered = _lowered(m.group(), _STARTERS_EN)
            for pick in starts:
                edits.append(_Edit(m.start(), m.end(), pick + lowered, pick.strip(" ,").lower(), weight))
    for sentence in re.finditer(r"[^.!?…]+[.!?…]*", text):
        body = sentence.group()
        for c in re.finditer(r",\s+", body):
            before = _WORD.findall(body[:c.start()])
            after = _WORD.findall(body[c.end():])
            if (len(before) < 3 or len(after) < 2 or after[0].lower() in _JOINS_EN | _NOT_AFTER_EN
                    or before[-1].lower() in _NOT_AFTER_EN or _listed(before[-1], after[0])):
                continue
            at = sentence.start() + c.end()
            for pick in commas:
                edits.append(_Edit(at, at, pick, pick.strip(" ,").lower(), weight))
    words = list(_WORD.finditer(text))
    for prev, word in zip(words, words[1:]):
        nxt = word.group().lower()
        before_ok = _SMALL_EN - _INTENSIFIERS_EN if young else _SMALL_EN
        if prev.group().lower() not in _COPULA_EN or nxt in before_ok | _JOINS_EN:
            continue                       # «it was like really hard» — the young only
        if text[prev.end():word.start()].strip():
            continue
        if not young and nxt in _INTENSIFIERS_EN:
            continue                       # «kind of way harder» is nobody's English
        filler = "like" if young else "kind of"
        edits.append(_Edit(word.start(), word.start(), f"{filler} ", filler, weight))
    return edits


def _hedges_en(text: str, young: bool) -> list[_Edit]:
    edits = []
    for m in _VAGUE_EN.finditer(text):
        if _sentence_start(text, m.start()):
            continue
        said_before = _WORD.findall(text[:m.start()])
        if said_before and said_before[-1].lower() in _NOT_AFTER_EN:
            continue
        gap_start = len(text[:m.start()].rstrip())
        word = "like" if young else "uh"
        if text[gap_start - 1:gap_start] == ",":
            edits.append(_Edit(m.start(), m.start(), f"{word}, ", word, 1))
        else:
            edits.append(_Edit(gap_start, m.start(), f", {word}, ", word, 1))
    return edits


def _there_en(text: str, young: bool) -> list[_Edit]:
    if not young:
        return []
    edits = []
    for m in _OR_EN.finditer(text):
        if "?" in text[m.end():].split(".")[0]:
            edits.append(_Edit(m.start(), m.end(), "or, like, ", "like", 3))
    return edits
