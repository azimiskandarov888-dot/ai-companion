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

── AND HIS NORMAL DEPENDS ON THE HOUR ──────────────────────────────────────

«His own normal» was at first one number for the whole day, and that was wrong
in a way that fired daily. Older adults shift toward morningness, and morning
types are reliably worse in the evening; a man who is simply flatter at eight
therefore sat below a single all-day average EVERY evening, and was announced as
subdued every evening. A false alarm on a schedule is worse than no alarm: it
teaches the companion to tread carefully when nothing is wrong, and it buries
the real change on the day it finally arrives.

So the baseline is kept per part of the day — evenings compared with evenings.
The descriptive lines still use his overall normal, because «обычно он ровный»
is a fact about the man rather than about eight in the evening; only the
WARNING uses the hour. See _normal_by_part.

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

#: Fewer readings than this and there is no such thing as his normal yet. Eight
#: is roughly two real conversations: enough that one bad evening cannot become
#: the baseline, few enough that the companion is not blind for a fortnight.
MIN_FOR_BASELINE = 8

#: The newest readings are what he is like NOW, so they are held out of the
#: baseline. Including them would let a change quietly redefine "normal" and
#: erase itself.
RECENT_N = 3

#: How far from his own normal counts as having moved. On a -2..+2 scale, half
#: a step is noise and a whole step is a different person in the room.
MOVED = 0.55
STRONGLY = 1.0

#: A gap this long means the next reading belongs to a new conversation.
CONVERSATION_GAP = 10 * 60

#: How many readings from the same part of the day before that part gets its own
#: normal. Below it, the overall baseline is used — which is exactly the
#: behaviour that existed before this, so a new friendship loses nothing waiting.
#:
#: Three, and the number was picked by reproducing the fault rather than by
#: taste. Five looked prudent and was wrong: the evenings that most need their
#: own normal belong to somebody who talks in the evening only OCCASIONALLY, and
#: he reaches five of them after a month or two — during which he is flagged as
#: subdued every single time. A median over three is coarse, but it errs toward
#: silence, which is the right way to be wrong here.
MIN_PER_PART = 3

#: Hours per part of the day. Four even blocks rather than named ones, because
#: the names would be a lie: see _part().
_PART_HOURS = 6

#: How far back "when did this start" is allowed to look.
_TRAIL = 40


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


def observe(user_id: str, tag: str, subject: str = "", evidence: str = "") -> None:
    """Note that something happened — once. Twice is what makes it true."""
    tag = (tag or "").strip()
    if tag not in TAGS:
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

def recent(user_id: str, limit: int = _TRAIL) -> list[dict]:
    """Newest first."""
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT * FROM mood_readings WHERE user_id=? ORDER BY ts DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def _mean(rows: list[dict], dim: str) -> float | None:
    vals = [r[dim] for r in rows if r.get(dim) is not None]
    return statistics.fmean(vals) if vals else None


def _median(rows: list[dict], dim: str) -> float | None:
    """Median, not mean, for the baseline: one terrible evening should not
    become who somebody is."""
    vals = [r[dim] for r in rows if r.get(dim) is not None]
    return statistics.median(vals) if vals else None


def _composite(per_dim: dict[str, float | None]) -> float | None:
    vals = [per_dim[d] for d in FEELING if per_dim.get(d) is not None]
    return statistics.fmean(vals) if vals else None


def _part(ts: float) -> int:
    """Which part of HIS day a reading belongs to. 0–3.

    UTC, and the hour is deliberately never shown to anybody. It does not need
    to be the right hour where he lives — it needs to be the SAME hour every
    time. His eight-in-the-evening is always the same block whatever that block
    would be called here, so evenings get compared with evenings without the app
    ever knowing his timezone.

    UTC rather than server-local for one reason: local time moves. Daylight
    saving, or the server being rehomed, would drop new readings into a
    different block from the old ones and quietly compare his evenings against
    his mornings — the exact fault this function exists to remove, reintroduced
    invisibly and six months later.
    """
    return int(time.gmtime(ts).tm_hour) // _PART_HOURS


def _normal_by_part(older: list[dict], overall: float | None) -> dict[int, float | None]:
    """His usual level for each part of the day.

    Older adults shift toward morningness, and morning types are reliably worse
    in the evening — so a man who is simply flatter at eight is, against a single
    all-day average, BELOW HIS NORMAL every single evening. That fired the
    "he is quieter than usual" warning daily: a false alarm on a schedule, which
    teaches the companion to tread carefully when nothing is wrong and buries
    the real change on the day it finally comes.

    Parts with too little history fall back to the overall normal, which is
    precisely the old behaviour.
    """
    out: dict[int, float | None] = {}
    for part in range(24 // _PART_HOURS):
        same = [r for r in older if _part(r["ts"]) == part]
        level = (
            _composite({d: _median(same, d) for d in DIMS})
            if len(same) >= MIN_PER_PART
            else None
        )
        out[part] = overall if level is None else level
    return out


def _drop_against_own_part(
    newest: list[dict], normal: dict[int, float | None]
) -> float | None:
    """How far he is from usual — each reading judged against its OWN hour.

    Compared per reading and then averaged, rather than averaging first: the
    newest few can straddle a morning and an evening, and averaging those
    together before comparing would reintroduce the mixing this fixes.
    """
    diffs = []
    for r in newest:
        c = _composite(r)
        against = normal[_part(r["ts"])]
        if c is not None and against is not None:
            diffs.append(c - against)
    return statistics.fmean(diffs) if diffs else None


def _started_days_ago(rows: list[dict], normal: dict[int, float | None]) -> float | None:
    """How long he has been below his own normal.

    Walks back from now to the last reading that was still at his usual level,
    and reports the age of the one after it — the first one that wasn't. Each
    reading is measured against the normal for its own part of the day, or the
    dip would appear to start at whichever evening came first.
    """
    last_ok: dict | None = None
    for r in rows:                                   # newest first
        c = _composite(r)
        if c is None:
            continue
        against = normal[_part(r["ts"])]
        if against is None or c >= against - MOVED:
            last_ok = r
            break
    if last_ok is None:
        return None
    first_bad = None
    for r in rows:
        if r["ts"] <= last_ok["ts"]:
            break
        first_bad = r
    if first_bad is None:
        return None
    return (time.time() - first_bad["ts"]) / 86400.0


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
            " ORDER BY times DESC, last_ts DESC LIMIT 8",
            (user_id, CONFIRMED_AT, *PAIR),
        ).fetchall()
    if not rows:
        return ""
    lines = []
    for r in rows:
        what = TAGS.get(r["tag"], r["tag"])
        subject = f" — {r['subject']}" if r["subject"] else ""
        lines.append(f"- {what}{subject}. Так было {r['times']} раза.")
    return (
        "ЧТО УЖЕ ПОДТВЕРДИЛОСЬ (не один раз, а несколько — значит это про НЕГО,"
        " а не случайность):\n" + "\n".join(lines) +
        "\nЭто дороже любых догадок: это проверено на нём самом. Пользуйся этим,"
        " а не общими правилами."
    )


def wants_to_hear(user_id: str) -> bool:
    """Has it been WATCHED that he wants to be let in on the friend's own life?

    Either of two things counts: he asked about it and listened gladly, or the
    friend deflected and he would not let it go. Both mean the same — waiting to
    be asked is no longer the right shape with him, and life.py is told to let
    the companion simply say it.
    """
    marks = ("хотел_слушать_про_тебя", "настоял_чтобы_рассказал")
    holes = ",".join("?" for _ in marks)
    with db.connect() as conn:
        row = conn.execute(
            f"SELECT 1 FROM observations WHERE user_id=? AND tag IN ({holes})"
            " AND times>=? LIMIT 1",
            (user_id, *marks, CONFIRMED_AT),
        ).fetchone()
    return row is not None


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
    rows = recent(user_id)
    if len(rows) < MIN_FOR_BASELINE:
        return ""

    out = ["ЧТО ПРО НЕГО УЖЕ ИЗМЕРЕНО (это не догадки — это считалось само, по каждому разговору):"]
    base = {d: _median(rows[RECENT_N:], d) for d in DIMS}
    usual = _describe(base, "")
    if usual:
        out.append(f"Обычно он: {usual}.")

    with db.connect() as conn:
        seen = conn.execute(
            "SELECT tag, subject, times FROM observations WHERE user_id=? AND times>=?"
            " ORDER BY times DESC, last_ts DESC LIMIT 12",
            (user_id, CONFIRMED_AT),
        ).fetchall()
    def render(rows) -> list[str]:
        lines = []
        for r in rows:
            what = TAGS.get(r["tag"], r["tag"])
            subject = f" — {r['subject']}" if r["subject"] else ""
            lines.append(f"- {what}{subject}. Раз: {r['times']}.")
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

    per_dim_now = {d: rows[0].get(d) for d in DIMS}
    today_note = (rows[0].get("note") or "").strip()
    because = (rows[0].get("because") or "").strip()

    # Not enough history to know what usual even is. Say so plainly rather than
    # inventing a baseline out of three readings.
    if len(rows) < MIN_FOR_BASELINE:
        parts = ["КАК ОН СЕЙЧАС:"]
        parts.append(_describe(per_dim_now, "ничего особенного") + ".")
        if today_note:
            parts.append(today_note)
        parts.append(
            "Вы разговаривали ещё слишком мало, чтобы знать, какой он ОБЫЧНО. "
            "Поэтому не делай выводов из сегодняшнего дня: то, что кажется "
            "тяжестью, может быть просто его манерой."
        )
        return "\n".join(parts)

    older = rows[RECENT_N:]
    newest = rows[:RECENT_N]
    base = {d: _median(older, d) for d in DIMS}
    now = {d: _mean(newest, d) for d in DIMS}
    base_c, now_c = _composite(base), _composite(now)

    out = ["КАК ОН СЕГОДНЯ — И ЧЕМ ЭТО ОТЛИЧАЕТСЯ ОТ ОБЫЧНОГО:"]
    out.append("Обычно он: " + _describe(base, "ровный, без крайностей") + ".")
    out.append("Последнее время: " + _describe(now, "как обычно") + ".")
    if today_note:
        out.append(f"В этот раз: {today_note}")
    if because:
        out.append(f"Его слова, по которым это видно: {because}")

    # Inside this one conversation — did he arrive one way and change?
    turn = [r for r in rows if time.time() - r["ts"] < CONVERSATION_GAP * 3]
    if len(turn) >= 3:
        first_c, last_c = _composite(turn[-1]), _composite(turn[0])
        if first_c is not None and last_c is not None:
            d = last_c - first_c
            if d <= -MOVED:
                out.append("ВНУТРИ ЭТОГО РАЗГОВОРА он потускнел: начал живее, "
                           "чем говорит сейчас. Что-то в самом разговоре его "
                           "притушило — вспомни, о чём вы только что говорили.")
            elif d >= MOVED:
                out.append("ВНУТРИ ЭТОГО РАЗГОВОРА он ожил: сейчас живее, чем "
                           "начинал. То, о чём вы сейчас говорите, ему хорошо.")

    if base_c is None or now_c is None:
        return "\n".join(out)

    # The descriptive lines above use his overall normal, which is the right
    # thing to SAY — «обычно он ровный» is a fact about the man, not about eight
    # in the evening. The warning below uses his normal FOR THIS HOUR, which is
    # the right thing to ACT on. See _normal_by_part.
    normal = _normal_by_part(older, base_c)
    delta = _drop_against_own_part(newest, normal)
    if delta is None:
        return "\n".join(out)
    days = _started_days_ago(rows, normal) if delta <= -MOVED else None

    if delta <= -STRONGLY:
        out.append("")
        out.append("⚠ ЭТО ЗАМЕТНАЯ ПЕРЕМЕНА, И НЕ В ЛУЧШУЮ СТОРОНУ.")
        if days and days >= 0.7:
            out.append(f"Длится примерно {_days(days)}.")
        out.append(
            "Не бодрись и не веди себя как ни в чём не бывало — бодрячок тому, "
            "кому нужна тишина, хуже, чем ничего. Заметь это ОДНИМ касанием, "
            "мягко, и оставь ему возможность не отвечать. Не допрашивай. "
            "Чем именно поднимать ЕГО — сказано выше, в чтении о нём; не "
            "подставляй общую заготовку."
        )
    elif delta <= -MOVED:
        out.append("")
        out.append(
            "Он немного тише обычного. Возможно, ничего. Не расспрашивай и не "
            "делай из этого события — просто будь чуть мягче, не тормоши и не "
            "требуй от него бодрости."
        )
    elif delta >= MOVED:
        out.append("")
        out.append(
            "Он живее обычного. Не гаси это осторожностью и сочувствием — "
            "поддержи и побудь с ним в этом."
        )

    # Clarity alone: sadness and confusion are different things, and only one
    # of them is a reason to be careful with how you speak rather than what
    # you say.
    if base.get("clarity") is not None and now.get("clarity") is not None:
        dc = now["clarity"] - base["clarity"]
        if dc <= -STRONGLY:
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
