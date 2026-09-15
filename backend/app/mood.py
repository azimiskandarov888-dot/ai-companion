"""HOW HE IS TODAY — and, which matters far more, how that differs from usual.

`companion.py` says «Перемена важнее самого тона», and it was right and it was
unenforceable. What actually reached the prompt was one word — «устал» — pulled
from the newest memory row. One word cannot be compared with the word before
it, so a change could never be seen. The rule was written; the mechanism was
missing. This file is the mechanism.

── WHY A WORD IS NOT ENOUGH ────────────────────────────────────────────────

«Устал» from somebody who is always tired means nothing at all. «Устал» from
somebody who is usually bright means everything. A mood is not a state, it is a
POSITION RELATIVE TO HIS OWN NORMAL — and a direction of travel. Neither can be
computed from a single word, and neither survives being averaged across people.
So each exchange is read on five small scales, his own baseline is built from
his own history, and what the companion is told is the difference.

── A VISIT IS ONE OBSERVATION, NOT TWENTY-FIVE ─────────────────────────────

This was wrong for a long time and it is worth writing down why, because the
mistake is easy to make again. Readings were counted one per exchange, and the
baseline was a window of the last forty. Forty exchanges is one conversation —
so «his usual» was computed from the very conversation being judged against it,
and a man who had been bright for a month and arrived flat today was described
to his friend as «обычно он вялый, слушает вполуха».

The error has a name: twenty-five exchanges inside one conversation are not
twenty-five observations of a person, they are ONE occasion sampled twenty-five
times, and treating them as independent is the ecological fallacy. So a VISIT
is the unit, everything is counted in visits, and the window means the same
thing whether somebody comes every day or twice a month.

It also explains why the per-part-of-day baseline never worked. Evenings were
meant to be compared with evenings, so that a man who is simply flatter at
eight is not announced as subdued every evening — a sound idea, and measured
over ninety simulated days it never once did anything, because a forty-reading
window only ever held ONE part of the day and the per-part normal was always
the overall normal. The idea was right and the window made it unreachable. It
is kept, as a sliding window over visits: see _comparable.

── HOW FAR IS FAR IS NOT THE SAME DISTANCE FOR TWO PEOPLE ──────────────────

Thresholds used to be absolute — 0.55 of a point was "moved" for everybody.
Half a point from a man who is the same every evening is an event; half a point
from somebody whose ordinary range is two points is Tuesday. One fixed number
is deaf to the first and hysterical at the second.

So the limits come from HIS OWN SPREAD between visits, which is what individual
control charts do and what makes them work without per-person tuning. A steady
person gets narrow limits; a variable one gets wide limits and his ordinary
swings — including being flatter in the evenings — pass unremarked. Same code,
different answer per person, nothing to configure.

── THE FIVE ───────────────────────────────────────────────────────────────

All five run -2..+2 and all five point the same way: higher is better. That
uniformity is not tidiness, it is what makes them averageable — a scale that
ran the other way would have to be remembered and inverted at every use, and
one day it wouldn't be.

    energy      силы          exhausted ←→ lively
    warmth      открытость    closed, curt ←→ reaching toward you
    lightness   легко ли      carrying something heavy ←→ light
    clarity     ясность       lost, confused ←→ clear and present
    engagement  участие       answering out of politeness ←→ really in it

`clarity` is deliberately kept out of the composite. A person can be perfectly
clear and deeply sad, and averaging the two hides both. It is also the only one
of the five that can mean something medical, so it is reported alone and
watched separately.

── WHAT HE IS ACTUALLY TOLD ───────────────────────────────────────────────

Never numbers. Numbers are for computing the change; what a friend gets is the
sentence a friend would think: what this person is usually like, what he has
been like lately, what he is like right now, when it started, and his own words
that showed it. Then one instruction whose strength matches the size of the
change — because the failure this exists to prevent is not missing a bad day,
it is being cheerful at somebody who needed quiet.
"""

from __future__ import annotations

import statistics
import time

from . import db

# ── the shape of a reading ──────────────────────────────────────────────────

DIMS = ("energy", "warmth", "lightness", "clarity", "engagement")

#: Averaged into one number for "how is he". `clarity` is not among them — see
#: the module docstring.
FEELING = ("energy", "warmth", "lightness", "engagement")

# ── THE UNIT OF OBSERVATION, WHICH IS A VISIT AND NOT A SENTENCE ────────────
#
# A twenty-minute conversation is about twenty-five exchanges, and learn.py
# writes one reading per exchange. Those twenty-five are NOT twenty-five
# observations of what this person is like. They are ONE occasion, sampled
# twenty-five times, and treating them as independent is the ecological fallacy
# — the error of drawing conclusions about one level from statistics gathered
# at another. It has a name because it is common and because it is expensive.
#
# The cost here was exact and measurable. The old window held forty READINGS,
# so for anybody who actually talks it spanned ONE CONVERSATION: «his usual»
# was computed almost entirely from the very conversation being judged against
# it. A man who had been bright for a month and arrived flat today was
# described to his friend as «обычно он вялый, слушает вполуха» — a false
# statement about a person, in the block the app calls the most valuable thing
# it does.
#
# So a visit is one observation. Everything below counts in visits.

#: A gap this long means the next reading belongs to a new conversation.
CONVERSATION_GAP = 10 * 60

#: How many past VISITS make his usual. The same number means the same thing to
#: everybody, which is the property the old window did not have: fourteen visits
#: is fourteen visits whether he comes every day or twice a month. It is also
#: what «usual» means to a friend — the last dozen-odd times he saw you, however
#: long that took.
USUAL_OVER = 14

#: Fewer past visits than this and there is no usual yet, and the honest answer
#: is to say so. Three is about a week for a daily talker and six weeks for a
#: rare one — in both cases the point at which a friend starts to have an
#: opinion about what you are normally like.
MIN_VISITS = 3

# ── HOW FAR IS FAR, WHICH IS NOT THE SAME DISTANCE FOR TWO PEOPLE ───────────
#
# The old thresholds were absolute: 0.55 of a point was «moved» for everybody.
# But half a point from a man who is the same every single evening is a real
# event, and half a point from somebody whose ordinary range is two points is
# Tuesday. One fixed number has to be either deaf to the first or hysterical at
# the second, and it was quietly both.
#
# So the limits are built from HIS OWN SPREAD — the standard answer in
# individual control charts, where limits come from the process rather than
# from a specification. It needs no per-user setting and no tuning: a steady
# person gets narrow limits and small changes are caught, a variable person
# gets wide ones and his ordinary swings pass unremarked. The same code, a
# different answer for different people.

#: How many of HIS OWN steps away from usual counts as noticed, and as serious.
NOTICED = 1.5
STRONG = 2.6

#: A floor under the spread, for somebody with no variation at all: without it
#: his limits would be zero and he would trip on rounding.
#:
#: Set so that STRONG × MIN_SPREAD lands just under a whole point. That is the
#: property worth holding: for a man who is the same every single time, a full
#: point of change — a quarter of the entire scale — is a serious matter and
#: must be said so. Anything above 0.385 quietly makes it merely «немного тише».
MIN_SPREAD = 0.35

#: How many readings to pull in order to find those visits. Generous: at
#: twenty-five exchanges a visit this covers twenty-four visits, and the query
#: is one indexed read against a local file.
_SCAN = 600


# ── the observation register ────────────────────────────────────────────────

#: A closed vocabulary, because these are counted, and counting free text means
#: «ушёл от вопроса» and «ушел от вопроса» are two different truths that each
#: never reach two. The model picks from this list or says nothing.
TAGS: dict[str, str] = {
    "ушёл_от_вопроса": "замолчал или свернул разговор после того, как его спросили",
    "утешение_не_зашло": "его попытались утешить, и стало хуже, а не легче",
    "устал_от_расспросов": "вопросов было слишком много, он от них устал",
    "закрылся_на_теме": "на этой теме он закрывается",
    "поднял_юмор": "его подняла шутка, дурачество",
    "подняла_история": "его подняла история, что-то интересное со стороны",
    "подняли_воспоминания": "его подняло, когда вспоминали хорошее из его жизни",
    "подняло_дело": "его подняло, когда разобрались по делу, помогли конкретным",
    "подняло_молчание": "ему стало легче оттого, что просто побыли рядом без бодрости",
    "оживился_на_теме": "на этой теме он оживает",
    # ── how the two of them fit, which is a different thing from how he is ──
    # These feed fit.py — see PAIR below, which is the list of them and the
    # reason standing_block leaves them alone. They live here rather than in
    # their own vocabulary because they are found the same way — watched
    # happening, twice — and one register is one place to look.
    "зашло_что_позвал": "друг предложил, позвал, затеял — и человек оживился",
    "не_зашло_что_позвал": "друг предложил или затеял — и человек закрылся, ушёл",
    "понравилось_несогласие": "друг не согласился с ним — и человеку это понравилось",
    "не_понравилось_несогласие": "друг не согласился — и человек обиделся или замкнулся",
    "понравился_его_промах": "друг оплошал, перепутал, сглупил — и человеку это было мило",
    "сам_повёл_разговор": "человек сам завёл тему и вёл её, друг только слушал",
    "просил_помедленнее": "человек попросил говорить медленнее, тише или громче",
    "не_расслышал": "человек не расслышал, переспросил, ответил невпопад",
    "уговорили_и_обрадовался": "человек сперва отказался, друг позвал второй раз — и человек обрадовался",
    "хотел_больше_вопросов": "человек раскрылся именно оттого, что его расспрашивали",
    "хотел_слушать_про_тебя": "человек сам расспрашивал про жизнь друга и слушал охотно",
    "настоял_чтобы_рассказал": "друг отговорился, а человек продолжил выспрашивать — ему важно было влезть и помочь",
    "не_хотел_слушать_про_тебя": "друг заговорил о своём — и человек поскучнел, свернул тему или вернул разговор к себе",
    "просил_не_рассказывать_про_тебя": "человек ПРЯМО сказал, что не хочет слушать про дела и беды друга",
    "просил_рассказывать_про_себя": "человек ПРЯМО попросил друга больше рассказывать о себе",
    "обрадовался_что_ждали": "друг показал, что ждал его или скучал, — и человеку это было в радость",
    "тяжело_что_ждали": "друг показал, что ждал его, — и человеку стало неловко: оправдывался, отшучивался, замкнулся",
    "спросил_ждали_ли_его": "человек сам спросил, ждали ли его, скучали ли, заметили ли, что его не было",
    "просил_не_ждать": "человек ПРЯМО сказал, что ждать его не надо и что он ничего не должен",
    "просил_говорить_короче": "человек ПРЯМО попросил отвечать покороче, не так длинно",
    "просил_рассказывать_подробнее": "человек ПРЯМО попросил рассказывать подробнее, не торопиться",
}

#: Once is a coincidence. This is the whole reason the register exists.
CONFIRMED_AT = 2

#: The tags that answer «чем его поднимать». The reading guesses at this from
#: the way somebody wrote a paragraph on the day they installed the app; these
#: are what actually worked on him, watched happening. When any of them is
#: confirmed, the guess is dropped rather than argued with — see
#: reading.standing_block.
LIFTS = (
    "поднял_юмор",
    "подняла_история",
    "подняли_воспоминания",
    "подняло_дело",
    "подняло_молчание",
)

#: The tags that describe the PAIR rather than the man, and that fit.py renders
#: with what to do about them. standing_block leaves these out, and that is not
#: a detail: before it did, every confirmed one of them was stated TWICE in the
#: same half of the same prompt — «друг предложил, позвал — и человек оживился,
#: 4 раза» from here, and «ТЕМП: твой напор ему заходит — 4 раза» from there,
#: back to back. One fact, one place.
PAIR = (
    "зашло_что_позвал",
    "не_зашло_что_позвал",
    "понравилось_несогласие",
    "не_понравилось_несогласие",
    "понравился_его_промах",
    "сам_повёл_разговор",
    "просил_помедленнее",
    "не_расслышал",
    "уговорили_и_обрадовался",
    "хотел_больше_вопросов",
    "устал_от_расспросов",
    "хотел_слушать_про_тебя",
    "настоял_чтобы_рассказал",
    "не_хотел_слушать_про_тебя",
    "просил_не_рассказывать_про_тебя",
    "просил_рассказывать_про_себя",
    "обрадовался_что_ждали",
    "тяжело_что_ждали",
    "спросил_ждали_ли_его",
    "просил_не_ждать",
    "просил_говорить_короче",
    "просил_рассказывать_подробнее",
)

#: And the tags that answer «что его задевает» — the evidence behind the
#: reading's hurt_by. The re-reading used to be asked to find these by reading
#: sixty turns of transcript and counting repeats BY EYE, under a rule that
#: demanded «дважды или больше» — while these very events were being counted
#: for it, one exchange at a time, in a table. Counting is arithmetic and
#: belongs here; what the count MEANS is the re-reading's job.
HURTS = (
    "ушёл_от_вопроса",
    "утешение_не_зашло",
    "закрылся_на_теме",
    "не_понравилось_несогласие",
    "устал_от_расспросов",
)


# ── words for numbers ───────────────────────────────────────────────────────

#: Nothing is said about a dimension sitting at its ordinary value, because a
#: friend does not think "his warmth is average" — he thinks nothing at all
#: until something moves. Printing all five every time buried the one that had
#: actually changed in four that hadn't.
_WORDS: dict[str, dict[int, str]] = {
    "energy":     {-2: "совсем без сил", -1: "вялый",
                    1: "в тонусе", 2: "оживлённый"},
    "warmth":     {-2: "закрыт", -1: "сдержан",
                    1: "открыт", 2: "сам тянется навстречу"},
    "lightness":  {-2: "несёт что-то тяжёлое", -1: "придавлен",
                    1: "ему легко", 2: "ему светло"},
    "clarity":    {-2: "путается, теряет нить", -1: "рассеян",
                    1: "собран", 2: "очень ясен"},
    "engagement": {-2: "отвечает из вежливости", -1: "слушает вполуха",
                    1: "увлечён", 2: "его не остановить"},
}

#: Below this, a dimension is simply his ordinary and goes unmentioned.
_NOTABLE = 0.5


def _describe(per_dim: dict[str, float | None], fallback: str) -> str:
    said = []
    for d in DIMS:
        v = per_dim.get(d)
        if v is None or abs(v) < _NOTABLE:
            continue
        step = 2 if abs(v) >= 1.5 else 1
        said.append(_WORDS[d][step if v > 0 else -step])
    return ", ".join(said) if said else fallback


def _clamp(v) -> float | None:
    try:
        return max(-2.0, min(2.0, float(v)))
    except (TypeError, ValueError):
        return None


# ── writing ─────────────────────────────────────────────────────────────────

def record(user_id: str, reading: dict) -> None:
    """Store one read of how he seemed. Silently ignores an unusable one."""
    vals = {d: _clamp(reading.get(d)) for d in DIMS}
    word = (reading.get("word") or "").strip()
    note = (reading.get("note") or "").strip()
    if not any(v is not None for v in vals.values()) and not word:
        return
    with db.connect() as conn:
        conn.execute(
            "INSERT INTO mood_readings"
            " (user_id, ts, energy, warmth, lightness, clarity, engagement,"
            "  word, note, because) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (user_id, time.time(), vals["energy"], vals["warmth"], vals["lightness"],
             vals["clarity"], vals["engagement"], word, note,
             (reading.get("because") or "").strip()),
        )


def _same_subject(subject: str) -> str:
    """One spelling per topic, or nothing is ever counted twice.

    The row is keyed on (user, tag, subject), so «Война» and «война» were two
    different truths that each waited forever to reach two — and «закрылся на
    теме» is one of the most valuable things this register holds. Case and
    trailing punctuation are free to fix here; wording («война» versus «про
    войну») is not, and is handled where it can be: the extractor is shown the
    words it has already used for this person and asked to reuse them.
    """
    return (subject or "").strip().strip(".,!?;:«»\"'…- ").lower()[:80]


#: «Ё» is optional in written Russian, and a model writes it or writes «е» by
#: chance, sentence to sentence. Two tags carry one — `ушёл_от_вопроса` and
#: `сам_повёл_разговор` — and a tag that misses the lookup was dropped in total
#: silence: no row, no error, nothing in the log. `ушёл_от_вопроса` is in HURTS,
#: the set the re-reading is told to trust to the exclusion of its own judgement,
#: so the silent half of those observations was being lost from the one place
#: that is meant to be evidence rather than guesswork.
#:
#: Note what this is NOT: a fuzzy match. The vocabulary stays closed and an
#: invented tag is still refused. It only forgives the one letter whose presence
#: is genuinely optional in the language.
_CANONICAL = {tag.replace("ё", "е"): tag for tag in TAGS}


def _known_tag(tag: str) -> str:
    """The real tag this is, or empty. See _CANONICAL."""
    return _CANONICAL.get((tag or "").strip().lower().replace("ё", "е"), "")


def _times(n: int) -> str:
    """«1 раз», «2 раза», «5 раз» — and Russian does not count like English.

    This text goes into the prompt of a Russian-speaking companion, and «так
    было 5 раза» is the kind of mistake a model will happily echo back in his
    own voice. Counts pass five routinely.
    """
    n = abs(int(n))
    if n % 100 in (11, 12, 13, 14):
        return f"{n} раз"
    if n % 10 == 1:
        return f"{n} раз"
    if n % 10 in (2, 3, 4):
        return f"{n} раза"
    return f"{n} раз"


def observe(user_id: str, tag: str, subject: str = "", evidence: str = "") -> None:
    """Note that something happened — once. Twice is what makes it true."""
    tag = _known_tag(tag)
    if not tag:
        return
    subject = _same_subject(subject)
    now = time.time()
    with db.connect() as conn:
        conn.execute(
            "INSERT INTO observations (user_id, tag, subject, times, first_ts,"
            " last_ts, evidence) VALUES (?,?,?,1,?,?,?)"
            " ON CONFLICT(user_id, tag, subject) DO UPDATE SET"
            "   times = times + 1, last_ts = excluded.last_ts,"
            "   evidence = COALESCE(NULLIF(excluded.evidence,''), evidence)",
            (user_id, tag, subject, now, now, (evidence or "").strip()[:200]),
        )


# ── reading back ────────────────────────────────────────────────────────────

def recent(user_id: str, limit: int = _SCAN) -> list[dict]:
    """Newest first."""
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT * FROM mood_readings WHERE user_id=? ORDER BY ts DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def _median(rows: list[dict], dim: str) -> float | None:
    """Median, not mean, for the baseline: one terrible evening should not
    become who somebody is."""
    vals = [r[dim] for r in rows if r.get(dim) is not None]
    return statistics.median(vals) if vals else None


def _composite(per_dim: dict[str, float | None]) -> float | None:
    vals = [per_dim[d] for d in FEELING if per_dim.get(d) is not None]
    return statistics.fmean(vals) if vals else None


def _visits(rows: list[dict]) -> list[list[dict]]:
    """Group newest-first readings into visits, newest visit first.

    A visit ends where the silence between two exchanges is long enough to be
    somebody putting the phone down — the same gap memory.py uses to decide
    that a word is starting a new conversation rather than continuing one.
    """
    if not rows:
        return []
    out: list[list[dict]] = [[rows[0]]]
    for newer, older in zip(rows, rows[1:]):
        if (newer["ts"] or 0.0) - (older["ts"] or 0.0) > CONVERSATION_GAP:
            out.append([older])
        else:
            out[-1].append(older)
    return out


#: Visits within this many hours of each other, around the clock, are the same
#: time of day for this purpose. A sliding window rather than fixed blocks: with
#: blocks, two visits forty minutes apart land in different ones whenever the
#: boundary falls between them, and neither is comparable with the other.
NEARBY_HOURS = 4


def _hour_of(visit: list[dict]) -> int:
    """When this visit began, in UTC hours.

    UTC, and the hour is never shown to anybody. It does not need to be the
    right hour where he lives — it needs to be the SAME hour every time, so his
    eight-in-the-evening always lands near his other eight-in-the-evenings
    without the app ever knowing his timezone. Local time would move under
    daylight saving and quietly start comparing his evenings with his mornings.
    """
    return time.gmtime(min(r["ts"] or 0.0 for r in visit)).tm_hour


def _hours_apart(a: int, b: int) -> int:
    gap = abs(a - b) % 24
    return min(gap, 24 - gap)


def _comparable(levels: list[dict], visits: list[list[dict]], when: float) -> list[dict]:
    """The past visits worth comparing today with — the ones at about this hour.

    Older adults shift toward morningness and morning types are reliably worse
    in the evening, so a man who is simply flatter at eight sits below any
    all-day average EVERY evening. Judged against all his visits at once he is
    announced as subdued on a schedule, which teaches the companion to tread
    carefully when nothing is wrong and buries the real change on the day it
    comes.

    Falls back to all of them when there are too few nearby, which is also the
    right answer: a man with two evening visits has no evening normal yet.
    """
    hour = time.gmtime(when).tm_hour
    near = [
        lv for lv, v in zip(levels, visits)
        if _hours_apart(_hour_of(v), hour) <= NEARBY_HOURS
    ]
    return near if len(near) >= MIN_VISITS else levels


def _level(visit: list[dict]) -> dict[str, float | None]:
    """What one visit came to, per scale.

    Median within the visit as well: a person who said one flat thing in an
    hour of good talk had one flat exchange, not a flat evening.
    """
    return {d: _median(visit, d) for d in DIMS}


def _spread(levels: list[dict[str, float | None]]) -> float:
    """How much HE varies between visits, in points — his own yardstick.

    Half the interquartile range. Not a standard deviation, for the reason the
    baseline is a median: one genuinely awful evening should widen nobody's
    limits, and over a dozen visits a single outlier moves a standard deviation
    a great deal. On ordinary data IQR/2 and the median absolute deviation are
    the same size, so the multipliers mean the same thing either way.

    And NOT the median absolute deviation, which was tried first and failed the
    exact case this exists for. A man who is bright at noon and quiet at eight
    has two clusters, and more than half his visits sit in the bigger one — so
    the median deviation is zero, his limits collapse to the floor, and every
    ordinary evening is announced as a change. That was the daily false alarm
    the old per-part-of-day baseline had been built to prevent. A quantile
    measure sees the two clusters as the range they are, which is what makes
    this replace that mechanism rather than merely delete it.
    """
    vals = sorted(c for c in (_composite(v) for v in levels) if c is not None)
    if len(vals) < 4:
        return MIN_SPREAD
    low, _, high = statistics.quantiles(vals, n=4, method="inclusive")
    return max(MIN_SPREAD, (high - low) / 2.0)


def _days_since(levels: list[dict[str, float | None]],
                visits: list[list[dict]], normal: float, limit: float) -> float | None:
    """How long this has been going on — in days, counted back through visits.

    Walks back from today to the first visit that was still at his usual level,
    and reports the age of the visit after it. Returns None when today is the
    first one that is off, which is most of the time and is the honest answer:
    a thing that started today has no duration worth naming.
    """
    first_off = None
    for level, visit in zip(levels, visits):         # newest first
        c = _composite(level)
        if c is None or c >= normal - limit:
            break
        first_off = visit
    if first_off is None:
        return None
    started = min(r["ts"] or 0.0 for r in first_off)
    days = (time.time() - started) / 86400.0
    return days if days >= 0.7 else None


# ── what he is told ─────────────────────────────────────────────────────────

def standing_block(user_id: str) -> str:
    """The confirmed observations — STABLE half, so it is cached and near-free.

    Only what has happened at least twice. A single occurrence is held in the
    table and deliberately withheld: acting on one is exactly the mistake the
    register exists to prevent.

    And only what is about HIM. The tags in PAIR describe the two of them and
    are rendered by fit.py with what to do about them; listing them here as well
    put the same fact in the same prompt twice, a few lines apart.
    """
    marks = ",".join("?" for _ in PAIR)
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT tag, subject, times FROM observations"
            f" WHERE user_id=? AND times>=? AND tag NOT IN ({marks})"
            " ORDER BY last_ts DESC, times DESC LIMIT 8",
            (user_id, CONFIRMED_AT, *PAIR),
        ).fetchall()
    if not rows:
        return ""
    lines = []
    for r in rows:
        what = TAGS.get(r["tag"], r["tag"])
        subject = f" — {r['subject']}" if r["subject"] else ""
        lines.append(f"- {what}{subject}. Так было {_times(r['times'])}.")
    return (
        "ЧТО УЖЕ ПОДТВЕРДИЛОСЬ (не один раз, а несколько — значит это про НЕГО,"
        " а не случайность):\n" + "\n".join(lines) +
        "\nЭто дороже любых догадок: это проверено на нём самом. Пользуйся этим,"
        " а не общими правилами."
    )


#: HOW MUCH OF HIS OWN LIFE THIS PERSON WANTS. One dial, and it replaces the
#: one choreography that used to be handed to everybody.
#:
#: Two people, the same app. One is in a bad way and does not want to hear about
#: anybody's troubles, not even hinted at. The other would far rather listen to
#: his friend's week than recount his own. Nothing about them is the same, and a
#: single «сперва полфразы, потом ещё немного» was being read to both.
_OPEN = ("хотел_слушать_про_тебя", "настоял_чтобы_рассказал")
_CLOSED = ("не_хотел_слушать_про_тебя",)

#: SAID OUTRIGHT, and therefore true at once.
#:
#: Everything else in this register waits for a second occurrence, and that rule
#: is right because everything else is an INFERENCE — he went quiet, and quiet
#: has more than one meaning. «Не рассказывай мне про свои болячки» is not an
#: inference. Making a person say it twice before it counts is not caution, it
#: is ignoring them, and it is the thing they would notice.
_SAID_OPEN = ("просил_рассказывать_про_себя",)
_SAID_CLOSED = ("просил_не_рассказывать_про_тебя",)


def _seen_any(user_id: str, tags: tuple[str, ...], times: int) -> bool:
    """Have these been watched, BETWEEN THEM, at least `times`?

    Summed across the group rather than counted per tag, and the difference is
    not a detail. The tags in a group are different BEHAVIOURS meaning the same
    thing: somebody who asked about your week on Monday and, on Thursday,
    refused to let you brush him off has shown you the same thing twice by two
    different routes — which is better evidence than the same route twice, not
    worse. Requiring one tag to reach two on its own would have read that as a
    pair of coincidences and told him nothing.
    """
    if not tags:
        return False
    holes = ",".join("?" for _ in tags)
    with db.connect() as conn:
        row = conn.execute(
            "SELECT COALESCE(SUM(times), 0) n FROM observations"
            f" WHERE user_id=? AND tag IN ({holes})",
            (user_id, *tags),
        ).fetchone()
    return (row["n"] or 0) >= times


def openness(user_id: str) -> str:
    """How much of the companion's own life this person wants: closed|normal|open.

    Asked outright beats watched, and watched beats nothing. Where somebody has
    both asked to hear more and later asked to hear less, the later ASKING is
    what counts — so a direct request in either direction is checked before any
    amount of inference, and closed is checked before open, because being spared
    something you wanted is a smaller harm than being handed something you asked
    not to hear.
    """
    if _seen_any(user_id, _SAID_CLOSED, 1):
        return "closed"
    if _seen_any(user_id, _SAID_OPEN, 1):
        return "open"
    if _seen_any(user_id, _CLOSED, CONFIRMED_AT):
        return "closed"
    if _seen_any(user_id, _OPEN, CONFIRMED_AT):
        return "open"
    return "normal"


#: HOW THIS PERSON WANTS TO BE MISSED. The second dial, and it was the oldest
#: unmechanised rule in the app.
#:
#: The constitution describes three different people in prose — one needs to
#: hear outright that he was waited for, and needs it to sting a little, or he
#: does not believe he is wanted; one finds somebody else's feeling a weight and
#: has to be let off it at once; one hears any mention of his absence as a
#: reproach — and then says «смотри, кто перед тобой» while handing him nothing
#: to look at. reading.py guesses at it on day one, from a paragraph written to
#: a machine somebody had never met, and nothing ever checked that guess against
#: what actually happened. `what_lifts_him` has been watched and confirmed for
#: months; this, which governs the highest-stakes sentence in the app — the
#: first thing said to somebody who has been gone a week — had nothing.
_MISSED = ("обрадовался_что_ждали",)
_SPARED = ("тяжело_что_ждали",)

#: Done outright, and therefore true at once. Asking «ты хоть скучал?» is not a
#: thing the other two kinds of person ever say; and «не надо меня ждать» is a
#: request, not a mood to be read twice before it counts.
_SAID_MISSED = ("спросил_ждали_ли_его",)
_SAID_SPARED = ("просил_не_ждать",)


def closeness(user_id: str) -> str:
    """How he wants to be missed: spared | normal | missed.

    Same order of precedence as openness(), and for the same reason. Spared is
    checked first because the two mistakes are not the same size: not hearing
    «я тебя ждал» when you wanted it is a quiet disappointment, and hearing it
    when it lands as a debt is one more thing to feel guilty about — from the
    one place that was supposed to be free of that.
    """
    if _seen_any(user_id, _SAID_SPARED, 1):
        return "spared"
    if _seen_any(user_id, _SAID_MISSED, 1):
        return "missed"
    if _seen_any(user_id, _SPARED, CONFIRMED_AT):
        return "spared"
    if _seen_any(user_id, _MISSED, CONFIRMED_AT):
        return "missed"
    return "normal"


def subjects_seen(user_id: str, limit: int = 20) -> str:
    """Topics already named for this person — for the extractor, to reuse.

    Counting «закрылся на теме» needs one spelling per topic, and no amount of
    cleaning in code turns «про войну» into «война». What does work is the thing
    the app already does for facts: show what exists and let the model recognise
    its own topic in it. Nothing to enumerate in advance, nothing to maintain.
    """
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT DISTINCT subject FROM observations"
            " WHERE user_id=? AND subject<>'' ORDER BY last_ts DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    return ", ".join(f"«{r['subject']}»" for r in rows)


def lifts_confirmed(user_id: str) -> bool:
    """Has it been WATCHED, twice or more, what actually lifts him?

    Asked by the one caller that needs to stand down when the answer is yes:
    the reading's «чем его поднимать» is a guess made from a paragraph somebody
    wrote to a stranger on their first day, and it rides in the same prompt as
    this register, phrased as an instruction. Two answers to one question, and
    the weaker one said more loudly.
    """
    marks = ",".join("?" for _ in LIFTS)
    with db.connect() as conn:
        row = conn.execute(
            f"SELECT 1 FROM observations WHERE user_id=? AND tag IN ({marks})"
            " AND times>=? LIMIT 1",
            (user_id, *LIFTS, CONFIRMED_AT),
        ).fetchone()
    return row is not None


def as_measured(user_id: str) -> str:
    """What has been COUNTED about him — for the re-reading, not for the prompt.

    reading.reread() was handed the old document and a transcript, and asked to
    work out from the transcript what lifts him — while «подняло_молчание · 4
    раза» sat in a table it was never shown. Two systems learning the same thing
    separately, neither aware of the other, and the one with arithmetic behind it
    was the one kept in the dark.

    Empty until there is enough history to mean anything, because a baseline off
    three readings is not a measurement, it is a rumour with a number on it.
    """
    past = _visits(recent(user_id))[1 : 1 + USUAL_OVER]
    if len(past) < MIN_VISITS:
        return ""

    out = ["ЧТО ПРО НЕГО УЖЕ ИЗМЕРЕНО (это не догадки — это считалось само, по каждому разговору):"]
    levels = [_level(v) for v in past]
    base = {
        d: (statistics.median(vals) if (vals := [lv[d] for lv in levels if lv[d] is not None]) else None)
        for d in DIMS
    }
    usual = _describe(base, "")
    if usual:
        out.append(f"Обычно он: {usual}.")

    with db.connect() as conn:
        seen = conn.execute(
            "SELECT tag, subject, times FROM observations WHERE user_id=? AND times>=?"
            " ORDER BY last_ts DESC, times DESC LIMIT 12",
            (user_id, CONFIRMED_AT),
        ).fetchall()
    def render(rows) -> list[str]:
        lines = []
        for r in rows:
            what = TAGS.get(r["tag"], r["tag"])
            subject = f" — {r['subject']}" if r["subject"] else ""
            lines.append(f"- {what}{subject}. {_times(r['times']).capitalize()}.")
        return lines

    # Hurts are listed apart, and that is not tidiness. It is the difference
    # between handing somebody evidence and handing them a pile to sort: the
    # re-reading writes hurt_by from this group and from nothing else, so which
    # rows belong to it must be a fact rather than its judgement.
    hurts = [r for r in seen if r["tag"] in HURTS]
    rest = [r for r in seen if r["tag"] not in HURTS]
    if hurts:
        out.append("ЕГО ЗАДЕВАЛО — и не по одному разу (вот доказательство для hurt_by):")
        out += render(hurts)
    if rest:
        out.append("Ещё случалось не по одному разу:")
        out += render(rest)

    return "\n".join(out) if len(out) > 1 else ""


def block(user_id: str) -> str:
    """How he is today against his own normal — VARIABLE half, every turn."""
    rows = recent(user_id)
    if not rows:
        return ""

    today_note = (rows[0].get("note") or "").strip()
    because = (rows[0].get("because") or "").strip()

    visits = _visits(rows)
    today, past = visits[0], visits[1 : 1 + USUAL_OVER]
    now = _level(today)

    # Not enough visits to know what usual even is. Say so plainly rather than
    # inventing a baseline out of one evening — and note that this branch is
    # about VISITS, so an hour of talking on the first day does not buy an
    # opinion about what he is normally like.
    if len(past) < MIN_VISITS:
        parts = ["КАК ОН СЕЙЧАС:", _describe(now, "ничего особенного") + "."]
        if today_note:
            parts.append(today_note)
        parts.append(
            "Вы разговаривали ещё слишком мало, чтобы знать, какой он ОБЫЧНО. "
            "Поэтому не делай выводов из сегодняшнего дня: то, что кажется "
            "тяжестью, может быть просто его манерой."
        )
        return "\n".join(parts)

    levels = [_level(v) for v in past]
    # Like with like: his visits at about this hour, if he has enough of them.
    against = _comparable(levels, past, today[0]["ts"] or time.time())
    base = {
        d: (statistics.median(vals) if (vals := [lv[d] for lv in against if lv[d] is not None]) else None)
        for d in DIMS
    }
    base_c, now_c = _composite(base), _composite(now)

    out = ["КАК ОН СЕГОДНЯ — И ЧЕМ ЭТО ОТЛИЧАЕТСЯ ОТ ОБЫЧНОГО:"]
    out.append("Обычно он: " + _describe(base, "ровный, без крайностей") + ".")
    out.append("Сегодня: " + _describe(now, "как обычно") + ".")
    if today_note:
        out.append(f"В этот раз: {today_note}")
    if because:
        out.append(f"Его слова, по которым это видно: {because}")

    if base_c is None or now_c is None:
        return "\n".join(out)

    # His own yardstick — see MIN_SPREAD and the note above it. Everything
    # below is measured in these, which is why no number here is a preference.
    limit = _spread(against)
    delta = now_c - base_c

    # Did he arrive one way and leave another? Halves of today's visit, not the
    # first exchange against the last: those are two single integer judgements,
    # and comparing them fired on ordinary model jitter one turn in seven. The
    # same yardstick decides what counts, so this adds no second idea.
    if len(today) >= 6:
        half = len(today) // 2
        started, ended = _composite(_level(today[half:])), _composite(_level(today[:half]))
        if started is not None and ended is not None:
            swing = ended - started
            if swing <= -limit * NOTICED:
                out.append("ВНУТРИ ЭТОГО РАЗГОВОРА он потускнел: начал живее, "
                           "чем говорит сейчас. Что-то в самом разговоре его "
                           "притушило — вспомни, о чём вы только что говорили.")
            elif swing >= limit * NOTICED:
                out.append("ВНУТРИ ЭТОГО РАЗГОВОРА он ожил: сейчас живее, чем "
                           "начинал. То, о чём вы сейчас говорите, ему хорошо.")

    if delta <= -limit * STRONG:
        days = _days_since(levels, past, base_c, limit * NOTICED)
        out.append("")
        out.append("⚠ ЭТО ЗАМЕТНАЯ ПЕРЕМЕНА, И НЕ В ЛУЧШУЮ СТОРОНУ.")
        if days:
            out.append(f"Длится примерно {_days(days)}.")
        out.append(
            "Не бодрись и не веди себя как ни в чём не бывало — бодрячок тому, "
            "кому нужна тишина, хуже, чем ничего. Заметь это ОДНИМ касанием, "
            "мягко, и оставь ему возможность не отвечать. Не допрашивай. "
            "Чем именно поднимать ЕГО — сказано выше, в чтении о нём; не "
            "подставляй общую заготовку."
        )
    elif delta <= -limit * NOTICED:
        out.append("")
        out.append(
            "Он немного тише обычного. Возможно, ничего. Не расспрашивай и не "
            "делай из этого события — просто будь чуть мягче, не тормоши и не "
            "требуй от него бодрости."
        )
    elif delta >= limit * NOTICED:
        out.append("")
        out.append(
            "Он живее обычного. Не гаси это осторожностью и сочувствием — "
            "поддержи и побудь с ним в этом."
        )

    # Clarity alone: sadness and confusion are different things, and only one
    # of them is a reason to be careful with how you speak rather than what you
    # say. And it SUPPRESSES the paragraph above rather than sitting beside it:
    # «заметь это одним касанием» and «ни в коем случае не показывай, что
    # заметил» cancel each other, and they co-occur constantly, because both are
    # read off the same five numbers.
    if base.get("clarity") is not None and now.get("clarity") is not None:
        if now["clarity"] - base["clarity"] <= -limit * STRONG:
            out = [line for line in out if "ЗАМЕТНАЯ ПЕРЕМЕНА" not in line
                   and "Заметь это ОДНИМ касанием" not in line
                   and "немного тише обычного" not in line]
            out.append("")
            out.append(
                "⚠ Сегодня ему заметно труднее держать нить, чем обычно. "
                "Говори короче и проще, не переспрашивай по многу раз, не "
                "поправляй его и ни в коем случае не показывай, что заметил. "
                "Если он путается сильно или не понимает, где он — мягко "
                "предложи позвать близких."
            )

    return "\n".join(out)


def _days(d: float) -> str:
    n = int(round(d))
    if n <= 1:
        return "около суток"
    if n < 5:
        return f"{n} дня"
    if n < 21:
        return f"{n} дней"
    return f"около {int(round(d / 7))} недель"
