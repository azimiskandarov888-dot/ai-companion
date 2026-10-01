"""HOW A SENTENCE SOUNDS SAID, NOT WRITTEN.

The owner, 2026-09-30, on «О, программирование — это мне всегда казалось
каким-то фокусом. Сам учишься или кто-то помогает?»: still fake, because it is
too perfect — «это не эссе, это не подготовленная переписка. Это живой
разговор, где должны быть ошибки, запинания, слова-паразиты». Research and
measurements: docs/SOUNDS-HUMAN.md.

WHY THIS IS CODE AND NOT A RULE. Told in every way we tried — a rule for live
speech, the same rule framed as a word-for-word transcript, the rule written in
speech itself, examples of live speech, the same thing as HIS manner in the
persona — the voice (Luna, without reasoning) still wrote clean prose: 0.6–0.9
small imperfections a reply, against 0.4–0.6 with no instruction at all (a
scripted A/B on the real prompt, 2026-09-30). Instruction tuning is what makes a
model's text unlike speech, and asking barely moves it (Reinhart et al., PNAS
2025). Claude Sonnet did it from the rule alone — a second slower, ~30× dearer.

So the imperfections are put where a speaker actually makes them, not anywhere:

- a hedge or a pause before the VAGUE word a speaker reaches for when the exact
  one is not there yet — «казалось, ну, каким-то фокусом». Hesitations gather
  before what is hard to plan (Maclay & Osgood 1959; Clark & Fox Tree 2002);
- the vague «там» in an either-or question — «сам или там кто-то помогает»;
- a restart as he begins on himself — «Я… я бы» — or the «вот» that holds
  the floor while he finds the rest — «Я вот там не был»;
- «ну» after a comma in a long sentence, while the next clause is planned, or
  opening a sentence that turns to a new thought — «Ну, наверное…».

About one a reply, sometimes none, never more than two, never the same one
twice in a reply. People make about six in a hundred words (Bortfeld et al.
2001); a machine that stumbles in every sentence is caught «trying too hard»
(Jones & Bergen 2023). The words are the commonest of Russian everyday speech
— вот, ну, там, как бы, я не знаю (the «Один речевой день» corpus) — and fit
any age.

Only the VOICE gets them. What is remembered, and read back later, is what he
meant — the clean reply; what is heard, and shown while he speaks, is how he
said it. Where exactness matters — a number, a warning — he speaks plainly.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass

#: A reply's small imperfections, at most — and a piece that could carry one
#: gets it four times in five. Tried on 650 of the voice's own replies: about
#: seven in ten a reply, which with the pauses it already writes («…») comes
#: to about one — people make about six in a hundred words.
MAX_PER_REPLY = 2
CHANCE = 0.8

#: Where exactness matters, nothing is roughened — from here to the end of the
#: reply: a number (a phone, a code, an address) or the words of a warning.
_EXACT = re.compile(
    r"\d|скор(?:ая|ую|ой)\b|полици|трубк|\bкод\b|\bкарт[ауые]\b|\bбанк|парол|врач", re.I)

_WORD = re.compile(r"[А-Яа-яЁёA-Za-z]+(?:-[А-Яа-яЁё]+)?")

#: The vague words a speaker reaches for when the exact one is not there yet.
_VAGUE = re.compile(
    r"(?<![А-Яа-яЁё-])(?:как(?:ой|ая|ое|ие|им|ую|ого|ому|ом|ими|их)|что|чем|чего|кто|кого|"
    r"где|как|куда|когда|почему|откуда|чей|чья|чьё)-то(?![А-Яа-яЁё-])", re.I)

#: «или» that offers a second choice in a question — and is not «или нет».
_OR = re.compile(r"(?<=\s)или\s+(?!там\b|нет\b)(?=[А-Яа-яЁё])", re.I)

#: A sentence he begins on himself.
_I = re.compile(r"(?:(?<=[.!?…]\s)|^)Я(?=\s)")

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

#: Sentences that turn to a new thought, and can open with «Ну».
_TURNS = re.compile(r"(?<=[.!?…]\s)(Наверное|Хорошо|Тогда|После|Там|Зато|Может|Главное)(?=[\s,])")

#: How a hedge goes in before a vague word, by what stands before it.
_HEDGES = (("ну", "ну, "), ("как бы", "как бы "), ("я не знаю", "я не знаю, "), ("…", "… "))


@dataclass(frozen=True)
class _Edit:
    start: int
    end: int
    text: str
    marker: str
    weight: int


def _sentence_start(piece: str, at: int) -> bool:
    """Nothing but a sentence's end, or the piece's start, before `at`."""
    before = piece[:at].rstrip()
    return not before or before[-1] in ".!?…"


def _hedges(piece: str) -> list[_Edit]:
    edits = []
    for m in _VAGUE.finditer(piece):
        if _sentence_start(piece, m.start()):
            continue                       # nothing said yet to hesitate after
        said_before = _WORD.findall(piece[:m.start()])
        if said_before and said_before[-1].lower() in _NOT_AFTER:
            continue
        gap_start = len(piece[:m.start()].rstrip())
        comma = piece[gap_start - 1:gap_start] == ","
        for marker, text in _HEDGES:
            if marker == "…":
                if comma:
                    continue               # «казалось,… каким-то» is not speech
                edits.append(_Edit(gap_start, m.start(), "… ", marker, 1))
            elif comma:
                edits.append(_Edit(m.start(), m.start(), text, marker, 1))
            elif marker == "как бы":
                edits.append(_Edit(gap_start, m.start(), " как бы ", marker, 1))
            else:
                edits.append(_Edit(gap_start, m.start(), f", {text}", marker, 1))
    return edits


def _there(piece: str) -> list[_Edit]:
    edits = []
    for m in _OR.finditer(piece):
        rest = piece[m.end():]
        if "?" in rest.split(".")[0]:      # a question, and this sentence of it
            edits.append(_Edit(m.start(), m.end(), "или там ", "там", 3))
    return edits


def _restarts(piece: str, first: bool) -> list[_Edit]:
    edits = []
    for m in _I.finditer(piece):
        if first and m.start() == 0:
            continue                       # the reply's very first word stays whole
        sentence = re.match(r"[^.!?…]*", piece[m.start():]).group()
        if len(_WORD.findall(sentence)) >= 6:   # a thought long enough to restart
            edits.append(_Edit(m.start(), m.end(), "Я… я", "я… я", 1))
        following = _WORD.findall(piece[m.end():])
        if following and following[0].lower() not in ("бы", "вот", "же", "и", "не", "ну"):
            edits.append(_Edit(m.start(), m.end(), "Я вот", "вот", 2))
    return edits


def _turns(piece: str) -> list[_Edit]:
    return [_Edit(m.start(), m.end(), f"Ну, {m.group(1).lower()}", "ну", 1)
            for m in _TURNS.finditer(piece)]


def _commas(piece: str) -> list[_Edit]:
    edits = []
    for sentence in re.finditer(r"[^.!?…]+[.!?…]*", piece):
        words = _WORD.findall(sentence.group())
        if len(words) < 9:
            continue
        for m in re.finditer(r",\s+", sentence.group()):
            before = _WORD.findall(sentence.group()[:m.start()])
            after = _WORD.findall(sentence.group()[m.end():])
            if (len(before) < 3 or len(after) < 3 or after[0].lower() in _JOINS
                    or before[-1].lower() in _NOT_AFTER or _listed(before[-1], after[0])):
                continue
            at = sentence.start() + m.end()
            edits.append(_Edit(at, at, "ну, ", "ну", 2))
    return edits


def _listed(left: str, right: str) -> bool:
    """Two words either side of a comma that end alike are a list — «шумный,
    тёплый», «сесть, выпить» — and nobody says «ну» in the middle of one."""
    return len(left) > 3 and len(right) > 3 and left[-2:].lower() == right[-2:].lower()


class Speaker:
    """One reply, said aloud: how many small imperfections it has had so far,
    and which. Give it the reply's pieces in order."""

    def __init__(self, rng: random.Random | None = None) -> None:
        self._rng = rng or random.Random()
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
        if self._left <= 0 or len(_WORD.findall(piece)) < 5:
            return piece
        options = [e for e in (_hedges(piece) + _there(piece) + _restarts(piece, first)
                               + _turns(piece) + _commas(piece))
                   if e.marker not in self._used]
        if not options or self._rng.random() > CHANCE:
            return piece
        edit = self._rng.choices(options, weights=[e.weight for e in options])[0]
        self._left -= 1
        self._used.add(edit.marker)
        return piece[:edit.start] + edit.text + piece[edit.end:]


def said(text: str, rng: random.Random | None = None) -> str:
    """A whole reply said at once — sentence by sentence, as the pieces of a
    streamed one are."""
    speaker = Speaker(rng)
    sentences = re.findall(r"[^.!?…]+[.!?…]*\s*", text) or [text]
    return "".join(speaker.say(s.rstrip()) + s[len(s.rstrip()):] for s in sentences)
