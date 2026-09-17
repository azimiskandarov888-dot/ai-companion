"""The companion's memory — what makes it feel like a real friend.

Every function here takes `user_id` FIRST, and none of them has a default for
it. That is deliberate and it is the whole safety model of this module: a
forgotten argument becomes a TypeError the first time the code runs, instead
of a silent read from somebody else's life. A default value would have made
every missed call site a privacy bug that never raises — which is exactly the
bug this file was written to end.

Two owners share the store, per user (see db.py):
  - owner='elder' : memory ABOUT the person — facts, stories, health, mood, and
                    caring follow-ups. This is what gets recalled to make them
                    feel known.
  - owner='bob'   : durable details the companion has revealed about his OWN
                    life, so he stays consistent about himself.

Kinds: fact | story | health | mood | follow_up.

How it's used:
  - Before each reply → facts_context(uid, 'elder') + bob_self_context(uid) +
    build_memory_context(uid, ...) load what he should have in mind.
  - After each reply → learn.py extracts new memories in the background.

Storage-agnostic on purpose. A later phase can swap SQLite/cosine for
Postgres + pgvector without changing callers.
"""

from __future__ import annotations

import json
import random
import time

from . import db, embeddings

# How many recent turns to feed the brain as live conversation. 12 covers the
# thread of a spoken chat; anything older that mattered has been distilled into
# memory and comes back through recall. Every extra turn here is tokens the
# brain re-reads before EVERY reply — this is spoken conversation, where that
# wait is a silence — so the window stays small on purpose.
RECENT_TURNS = 12
# How many semantically-recalled stories to surface per reply.
RECALL_K = 4
# Only keep recalled stories at least this related (cosine) to what he just said.
RECALL_MIN_SCORE = 0.2
# Chance of spontaneously resurfacing an old warm memory in a reply.
RESURFACE_CHANCE = 0.25
# A follow-up stops being raised after it's been surfaced this many times.
FOLLOW_UP_MAX_SURFACES = 2
# Don't check back on something in the same conversation — wait at least this long
# (so "как твоё колено?" comes next time he talks, not two sentences later).
FOLLOW_UP_MIN_AGE = 3 * 3600
# Once raised, don't raise the same follow-up again for this long.
FOLLOW_UP_COOLDOWN = 12 * 3600
# Follow-ups older than this (seconds) are considered stale and dropped.
FOLLOW_UP_MAX_AGE = 21 * 24 * 3600

#: EVERY read that tells the companion what is true of his friend's life today
#: carries this. A memory with a `superseded_ts` is not deleted and not false —
#: it stopped being CURRENT (see supersede()), and the difference between those
#: two words is the difference between a diary that still remembers his wife
#: and a companion who asks how she is.
#:
#: It is a constant rather than typed out per query for one reason: the failure
#: mode of forgetting it is silent. A read without it returns MORE rows, never
#: an error, and the extra row is the one thing in this database that must
#: never be spoken aloud.
_LIVE = "superseded_ts IS NULL"


# --------------------------------------------------------------------------- #
# Raw conversation log
# --------------------------------------------------------------------------- #
def log_turn(user_id: str, role: str, content: str, farewell: bool = False) -> None:
    with db.connect() as conn:
        conn.execute(
            "INSERT INTO turns(user_id, role, content, ts, farewell) VALUES (?,?,?,?,?)",
            (user_id, role, content, time.time(), 1 if farewell else 0),
        )


def recent_turns(user_id: str, limit: int = RECENT_TURNS) -> list[dict[str, str]]:
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT role, content FROM turns WHERE user_id=? "
            "ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]


# --------------------------------------------------------------------------- #
# Did the last conversation end, or just stop?
# --------------------------------------------------------------------------- #
#
# People close apps. They don't say goodbye to them — and this app depends on
# them doing the human thing instead, because that is the whole difference
# between a friend and a program.
#
# Telling somebody that in a tutorial would be telling them about software. So
# he notices it himself, the way a person would: «в прошлый раз ты как-то
# пропал». One remark, in his own words, at the moment it is actually true.
#
# Everything below exists to keep that remark rare. It is a nudge for somebody
# who hasn't learnt the shape of this yet — and a nag if it ever arrives twice.

#: How long a silence has to be before the next word begins a NEW conversation
#: rather than continuing the old one. Ten minutes is long enough that
#: answering the door doesn't count, short enough that morning and afternoon
#: are two separate visits.
NEW_CONVERSATION_GAP = 10 * 60

#: He only ever raises it while the friendship is new. After a fortnight, this
#: is simply how his friend is, and a friend who is still correcting you after
#: two weeks isn't being warm — he's being a tutorial.
LEARNING_PERIOD = 14 * 24 * 3600

#: Fewer exchanges than this and there was no conversation to break off — just
#: a hello, or a wrong word into a phone.
REAL_CONVERSATION = 6

#: Enough history to measure the last conversation exactly. Anything longer
#: than this was unquestionably a real conversation anyway.
_CONVERSATION_SCAN = 40

#: And enough to find where the CURRENT conversation started, which needs far
#: more. Forty rows is twenty exchanges, and an ordinary conversation is
#: twenty-five — so a scan sized for «was this a real conversation?» cannot see
#: back to the beginning of one, and quietly reports that it began in the
#: middle. Five hundred rows is a two-hundred-and-fifty-exchange conversation;
#: the query is one indexed read against a local file.
_VISIT_SCAN = 500


def broke_off_last_time(user_id: str) -> bool:
    """Did their last real conversation just stop, with nobody saying goodbye?

    True only while it is still worth him mentioning:

      · this word is starting a new conversation, not continuing one;
      · the last one was a proper conversation, not a hello;
      · they have never ONCE said goodbye to him — the moment they do, he has
        nothing to notice and never brings it up again;
      · and the friendship is still new.

    Deliberately derived rather than stored. A counter would need a rule for
    when to reset it; these four conditions extinguish themselves, and the one
    that matters most — they learnt — extinguishes it permanently and for the
    right reason.
    """
    now = time.time()
    with db.connect() as conn:
        last = conn.execute(
            "SELECT ts FROM turns WHERE user_id=? ORDER BY id DESC LIMIT 1",
            (user_id,),
        ).fetchone()
        if last is None or now - last["ts"] < NEW_CONVERSATION_GAP:
            return False

        first = conn.execute(
            "SELECT ts FROM turns WHERE user_id=? ORDER BY id LIMIT 1",
            (user_id,),
        ).fetchone()
        if now - first["ts"] > LEARNING_PERIOD:
            return False

        parted = conn.execute(
            "SELECT 1 FROM turns WHERE user_id=? AND farewell=1 LIMIT 1",
            (user_id,),
        ).fetchone()
        if parted is not None:
            return False

        stamps = [
            row["ts"]
            for row in conn.execute(
                "SELECT ts FROM turns WHERE user_id=? ORDER BY id DESC LIMIT ?",
                (user_id, _CONVERSATION_SCAN),
            )
        ]

    # Walk back from the most recent turn until the gap between two of them is
    # long enough to be a different visit. What's left is the conversation that
    # ended without a word.
    length = 1
    for newer, older in zip(stamps, stamps[1:]):
        if newer - older > NEW_CONVERSATION_GAP:
            break
        length += 1
    return length >= REAL_CONVERSATION


# --------------------------------------------------------------------------- #
# How much this person actually says
# --------------------------------------------------------------------------- #
#
# «По умолчанию отвечай КОРОТКО: одна-три простые фразы» is the most-applied
# constant in the constitution — it governs every single reply — and it was the
# same number for a man who answers in three words and a woman who tells you
# about her whole Tuesday. Answering «ага» with five sentences is the most
# robot-like thing a companion does; answering a long, detailed story with «да,
# понятно» is dismissal. Length should CORRESPOND, and the constitution already
# says as much about tempo: «скупость — не холодность, читай как ТЕМП, к
# которому надо подстроиться».
#
# Unlike every other dial in this app, this one needs no tags and no model call.
# The turns are already in the table. A median over his own last twenty is not
# an inference to be confirmed twice — it is arithmetic, it cannot hallucinate,
# and it keeps moving on its own as he opens up. The register's «twice» rule
# exists because tags are inferences; measurement is not one.
#
# Thresholds in WORDS, chosen for speech rather than writing: a spoken
# conversational turn runs ten to twenty-five words, «ну да» and «ага» are one
# or two, and somebody telling a story goes well past thirty.
_TERSE_AT = 5
_TALKATIVE_AT = 25

#: Below this many turns there is nothing to take a median of, and early turns
#: are short for everybody — a hello is a hello. Silence until then.
_ENOUGH_TO_JUDGE = 10

#: How far back to look. Long enough to be stable, short enough that somebody
#: who has been drawn out over a month reads as the person he is now rather
#: than the one who arrived.
_SPEECH_WINDOW = 20


def how_much_he_says(user_id: str) -> str:
    """terse | normal | talkative — measured, never guessed.

    Returns "normal" for anybody there is not yet enough of, which is also the
    right answer: the constitution's own default is the middle.
    """
    # Turns from BEFORE this conversation, which is both the honest measurement
    # and the one that keeps the answer still.
    #
    # Honest, because the question is how this person usually speaks, not how he
    # has spoken in the last four minutes. And still, because fit.block rides in
    # the STABLE half of the system prompt — the half a provider caches on the
    # promise that it is byte-identical turn to turn. A median recomputed every
    # turn broke that promise in the middle of a conversation: nine long turns
    # read as `normal`, twelve short ones later the same conversation read as
    # `terse`, the cached block changed under the cache, and every turn after it
    # paid full price for the whole character.
    started = _this_conversation_began(user_id)
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT content FROM turns WHERE user_id=? AND role='user' AND ts < ?"
            " ORDER BY id DESC LIMIT ?",
            (user_id, started, _SPEECH_WINDOW),
        ).fetchall()
    if len(rows) < _ENOUGH_TO_JUDGE:
        return "normal"

    # Median, not mean, for the reason mood.py had to learn: one evening when he
    # told a long story must not turn a quiet man into a talkative one.
    lengths = sorted(len((r["content"] or "").split()) for r in rows)
    middle = lengths[len(lengths) // 2]
    if middle <= _TERSE_AT:
        return "terse"
    if middle >= _TALKATIVE_AT:
        return "talkative"
    return "normal"


#: Where the warmth rule gets something to stand on. Without this the model
#: has only the last twelve turns to judge by, and twelve turns look identical
#: on day one and in year two.
_JUST_MET = 6
_STILL_NEW = 14 * 24 * 3600


def how_long_acquainted(user_id: str) -> str:
    """One line telling him how far into this friendship he actually is.

    THE WARMTH RULE NEEDS THIS. He is told to be interested at first and to
    warm as he comes to know somebody — which is unusable advice unless he
    knows which of those he is doing. A friend who is still cautious after a
    year is cold; one who is tender on the first evening is a salesman.
    """
    with db.connect() as conn:
        row = conn.execute(
            "SELECT COUNT(*) n, MIN(ts) first FROM turns WHERE user_id=?",
            (user_id,),
        ).fetchone()

    turns, first = row["n"], row["first"]
    if not turns:
        return ("Вы только что познакомились. Ты внимателен и тебе любопытно — "
                "но ещё не ласков: пока не за что.")
    if turns < _JUST_MET:
        return ("Вы едва знакомы — это первый разговор. Интерес есть, тепло "
                "ещё нет. Не забегай вперёд.")
    if time.time() - first < _STILL_NEW:
        return ("Вы знакомы недавно, несколько дней. Ты уже кое-что о нём "
                "знаешь, и тебе стало не всё равно. Можно теплее — "
                "настолько, насколько ты правда узнал.")
    return ("Вы знакомы давно, и он тебе дорог. Здесь уместна та теплота, "
            "которую вы нажили вместе. Не отыгрывай её назад.")


#: Below this a gap is just life — he was busy, he slept in. Above it, it is a
#: thing that happened, and a friend knows it happened.
NOTICED_GAP = 3 * 86400


def how_long_since_last_time(user_id: str) -> str:
    """How long he has been gone. Empty unless it was long enough to matter.

    NOTHING in the prompt used to say this. A woman whose last word was
    sixty-two days ago got «Вы знакомы давно» and twelve UNDATED turns from
    July, handed over as though they were the last twelve minutes — while the
    constitution spent two thousand characters on how to handle an absence and
    fit.py carried a whole confirmed dial for it. All of that machinery stood on
    a fact the model was never given.

    It says the length and nothing else. What to DO with it is per person and
    lives where per-person things live (mood.closeness, rendered by fit.py); the
    constitution's default, for everybody else, is to be glad he is here and say
    nothing about the gap.
    """
    with db.connect() as conn:
        row = conn.execute(
            "SELECT MAX(ts) last FROM turns WHERE user_id=?", (user_id,)
        ).fetchone()
    gap = time.time() - (row["last"] or 0.0) if row and row["last"] else 0.0
    if gap < NOTICED_GAP:
        return ""
    return f"Вы не разговаривали {_days(gap / 86400.0)}."


def _days(days: float) -> str:
    """«три дня», «две недели», «почти два месяца» — never a number of hours."""
    if days < 14:
        n = int(round(days))
        if n % 10 == 1 and n % 100 != 11:
            return f"{n} день"
        if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14):
            return f"{n} дня"
        return f"{n} дней"
    if days < 60:
        n = int(round(days / 7))
        return f"около {n} недель" if n >= 5 else f"{n} недели"
    return f"около {int(round(days / 30))} месяцев"


# --------------------------------------------------------------------------- #
# Storing what the companion learns
# --------------------------------------------------------------------------- #
def add_memory(
    user_id: str,
    kind: str,
    content: str,
    *,
    owner: str = "elder",
    title: str | None = None,
    embedding: list[float] | None = None,
    importance: int = 1,
    status: str = "open",
    meta: dict | None = None,
) -> int | None:
    """Store one memory, skipping exact duplicates. Returns the new id or None."""
    content = content.strip()
    if not content:
        return None
    with db.connect() as conn:
        # Only a LIVE row counts as a duplicate. If something was retired and he
        # then says it again — a mistake corrected, a daughter who came back, a
        # pain that returned — the fact has to be able to come back with it, and
        # matching against a retired row would silently swallow it forever.
        dup = conn.execute(
            "SELECT id FROM memories WHERE user_id=? AND owner=? AND kind=? "
            f"AND content=? AND {_LIVE} LIMIT 1",
            (user_id, owner, kind, content),
        ).fetchone()
        if dup:
            return None
        cur = conn.execute(
            "INSERT INTO memories(user_id, owner, kind, title, content, importance, "
            "status, embedding, meta, created_ts, recall_count) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,0)",
            (
                user_id,
                owner,
                kind,
                title,
                content,
                importance,
                status,
                json.dumps(embedding) if embedding else None,
                json.dumps(meta, ensure_ascii=False) if meta else None,
                time.time(),
            ),
        )
        return cur.lastrowid


def _mark_recalled(ids: list[int]) -> None:
    if not ids:
        return
    now = time.time()
    with db.connect() as conn:
        conn.executemany(
            "UPDATE memories SET last_recalled_ts=?, recall_count=recall_count+1 "
            "WHERE id=?",
            [(now, i) for i in ids],
        )


# --------------------------------------------------------------------------- #
# Facts
# --------------------------------------------------------------------------- #
#
# THESE HAVE TO BE BOUNDED, and for a long time they were not. There was no cap,
# no merge and no decay — only exact-string dedup, so «ноет колено» and «ноет
# левое колено» both lived for ever. Measured at a conservative two new facts a
# day, after one year: 30,000 characters in the system prompt on every single
# turn, and 33,000 more sent to the extractor twenty-five times a conversation.
# A year of friendship is the case this app exists for; it must not be the case
# that breaks it.
#
# Ordering is importance first and then NEWEST, which matters more than the cap
# itself. Oldest-first was the previous order, so a cap would have kept the
# dentist appointment from last spring and dropped «переехал к дочери». And
# importance stays ahead of recency because a biography does not expire: «работал
# сварщиком тридцать лет» is old, permanent and worth more than most of what was
# said this week.

#: What the companion carries about him in every prompt. Roughly a hundred
#: facts, which is a great deal to know about somebody.
FACTS_BUDGET = 3_000

#: And what the extractor is shown so it can retire what stopped being true.
#: Much larger on purpose, and the asymmetry is deliberate: a fact that falls
#: out of THIS list can never be marked superseded again, and the worst thing
#: this app can do is ask how a dead wife is doing. Tokens are the cheaper side
#: of that trade by a wide margin.
BELIEFS_BUDGET = 12_000


def _within(lines: list[str], budget: int) -> list[str]:
    """As many of these as fit, in the order given."""
    out, used = [], 0
    for line in lines:
        used += len(line) + 1
        if used > budget:
            break
        out.append(line)
    return out


def facts_context(user_id: str, owner: str = "elder") -> str:
    """The known facts for an owner, formatted for the prompt.

    Live facts only. This is the one function that decides what the companion
    believes is true of his friend's life RIGHT NOW, which is why the whole of
    supersede() exists: a row left in here after it stopped being true is how
    somebody gets asked how their dead wife is doing.
    """
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT content FROM memories WHERE user_id=? AND kind='fact' AND owner=? "
            f"AND {_LIVE} ORDER BY importance DESC, created_ts DESC",
            (user_id, owner),
        ).fetchall()
    return "\n".join(_within([f"- {r['content']}" for r in rows], FACTS_BUDGET))


def believes(user_id: str, owner: str = "elder") -> str:
    """Everything the companion currently holds as true — numbered, for the
    extractor and nobody else.

    The companion is never shown these numbers: he would have no idea what they
    were and might well say one out loud. But something has to be able to POINT
    at a memory to retire it, and pointing by text is how the wrong one gets
    retired when two of them start with «дочь».

    OPEN FOLLOW-UPS ARE IN HERE TOO, and that is the whole reason this is not
    just the facts. «Спросить, как Валя» is a separate row from «жена Валя»:
    retiring the fact leaves the follow-up open, due_follow_ups surfaces it,
    and the companion asks after a dead woman anyway — for up to three weeks,
    which is how long one takes to expire on its own. Both have to be able to
    end, so both are offered here and the caller need not know the difference.
    """
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT id, kind, content FROM memories"
            " WHERE user_id=? AND owner=?"
            "   AND (kind='fact' OR (kind='follow_up' AND status='open'))"
            f"  AND {_LIVE}"
            " ORDER BY kind DESC, importance DESC, created_ts DESC",
            (user_id, owner),
        ).fetchall()
    out = []
    for r in rows:
        mark = "собирается спросить: " if r["kind"] == "follow_up" else ""
        out.append(f"[{r['id']}] {mark}{r['content']}")
    return "\n".join(_within(out, BELIEFS_BUDGET))


def supersede(user_id: str, memory_id: int, why: str = "") -> bool:
    """Retire one memory: it is no longer true of his life today.

    NOT a delete, and the difference is the whole point. «Жена Валя» does not
    become false when Valya dies — it becomes PAST. She was real, she mattered,
    and the diary is meant to outlive the subscription and still be able to
    write about her. What has to stop is the present tense reaching the
    companion, and that is exactly what this does and all it does.

    Scoped to `user_id` and not merely to `memory_id`, so a wrong id can only
    ever fail — never reach into somebody else's life. Returns True if a row
    was actually retired, which is what makes a bad id visible instead of
    silent.
    """
    with db.connect() as conn:
        cur = conn.execute(
            f"UPDATE memories SET superseded_ts=?, superseded_why=? "
            f"WHERE id=? AND user_id=? AND {_LIVE}",
            (time.time(), (why or "").strip()[:300], memory_id, user_id),
        )
        return cur.rowcount > 0


def past_facts(user_id: str, owner: str = "elder") -> list[dict]:
    """What was once true and no longer is. Newest ending first.

    Nothing in the live conversation reads this — it is for the diary, which
    is the one place his life is allowed to have a past tense, and for anybody
    checking later whether something was retired that should not have been.
    """
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT id, kind, content, superseded_ts, superseded_why FROM memories"
            " WHERE user_id=? AND owner=? AND superseded_ts IS NOT NULL"
            " ORDER BY superseded_ts DESC",
            (user_id, owner),
        ).fetchall()
    return [dict(r) for r in rows]


def bob_self_context(user_id: str) -> str:
    """Durable details the companion has said about his own life (consistency)."""
    return facts_context(user_id, owner="bob")


def seed_facts_from_file(user_id: str, path=None) -> int:
    """Import hand-written facts about the user from data/facts.json (once).

    Lets family pre-load what they know — family, birthdays, routine, his
    doctor/contact. Safe to run every startup: duplicates are skipped.

    This file belongs to whoever runs the server, so it seeds the anonymous
    user at startup. It is not a multi-user feature and deliberately hasn't
    become one: a shared server has no business reading one family's notes
    into everybody's memory.
    """
    from . import config

    path = path or (config.DATA_DIR / "facts.json")
    if not path.exists():
        return 0
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return 0
    if not isinstance(data, dict):
        return 0
    added = 0
    for key, value in data.items():
        if isinstance(value, (list, tuple)):
            value = ", ".join(str(v) for v in value)
        if add_memory(
            user_id, "fact", f"{key}: {value}", title=str(key), importance=3
        ):
            added += 1
    return added


# --------------------------------------------------------------------------- #
# Recall (the user's memory)
# --------------------------------------------------------------------------- #
def _rows(user_id: str, kinds: tuple[str, ...], owner: str = "elder") -> list:
    marks = ",".join("?" for _ in kinds)
    with db.connect() as conn:
        return conn.execute(
            f"SELECT * FROM memories WHERE user_id=? AND owner=? AND kind IN ({marks})"
            f" AND {_LIVE}",
            (user_id, owner, *kinds),
        ).fetchall()


async def recall_relevant(
    user_id: str, query_text: str, k: int = RECALL_K, exclude: set[int] | None = None
) -> list[dict]:
    """Semantically recall the stories/health notes most relevant right now."""
    exclude = exclude or set()
    rows = [r for r in _rows(user_id, ("story", "health")) if r["id"] not in exclude]
    if not rows:
        return []

    q = None
    if embeddings.available() and query_text.strip():
        try:
            q = await embeddings.embed(query_text)
        except Exception:
            q = None

    if q is not None:
        scored = [
            (embeddings.cosine(q, json.loads(r["embedding"]) if r["embedding"] else None), r)
            for r in rows
        ]
        scored.sort(key=lambda t: t[0], reverse=True)
        picked = [r for score, r in scored[:k] if score > RECALL_MIN_SCORE]
    else:
        # No embeddings → fall back to the most recent stories.
        picked = sorted(rows, key=lambda r: r["created_ts"], reverse=True)[:k]

    _mark_recalled([r["id"] for r in picked])
    return [dict(r) for r in picked]


def resurface(user_id: str, exclude: set[int] | None = None) -> dict | None:
    """Pick a warm story he hasn't been reminded of in a while (spaced recall)."""
    exclude = exclude or set()
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT * FROM memories WHERE user_id=? AND owner='elder' AND kind='story' "
            f"AND {_LIVE} "
            "ORDER BY (last_recalled_ts IS NULL) DESC, last_recalled_ts ASC, "
            "created_ts ASC LIMIT 5",
            (user_id,),
        ).fetchall()
    candidates = [r for r in rows if r["id"] not in exclude]
    if not candidates:
        return None
    chosen = candidates[0]
    _mark_recalled([chosen["id"]])
    return dict(chosen)


def _this_conversation_began(user_id: str) -> float:
    """When the conversation happening right now started.

    Walks back through turns until the silence between two of them is long
    enough to be somebody putting the phone down.

    Returns NOW when no conversation is in progress — nobody has said anything
    yet, or the last word was long enough ago that the next one will begin a new
    one. That is the right answer and it was not the first one: returning the
    start of the LAST conversation, hours after it ended, put every turn of it
    inside «this conversation» and hid the whole history from both callers.
    """
    now = time.time()
    with db.connect() as conn:
        stamps = [
            r["ts"] for r in conn.execute(
                "SELECT ts FROM turns WHERE user_id=? ORDER BY id DESC LIMIT ?",
                (user_id, _VISIT_SCAN),
            )
        ]
    if not stamps or now - stamps[0] > NEW_CONVERSATION_GAP:
        return now
    started = stamps[0]
    for newer, older in zip(stamps, stamps[1:]):
        if newer - older > NEW_CONVERSATION_GAP:
            break
        started = older
    return started


def due_follow_ups(user_id: str, limit: int = 1) -> list[dict]:
    """Caring things that are *due* to be checked back on now (never nagging).

    ONE PER CONVERSATION, and that is the whole point of the cooldown, which
    used not to achieve it. `FOLLOW_UP_COOLDOWN` is twelve hours per item, and
    this runs once per TURN — so a backlog of forty open follow-ups produced a
    different one on nearly every turn. Measured on one twenty-minute
    conversation with such a backlog: twenty turns, twenty different «а как там
    твоё колено?», which is not a friend remembering, it is a nurse with a
    clipboard.

    The fix is the conversation boundary this module already computes for other
    reasons: once ANYTHING has been raised in this conversation, the door is
    shut until the next one.

    And it has to be that global check rather than a stricter per-item cooldown,
    which was tried first and did nothing: the per-item clause is `last_recalled
    IS NULL OR last_recalled < …`, and a follow-up nobody has ever raised has
    NULL, so it passes every threshold there is. Forty never-raised items meant
    forty different questions no cooldown could touch.
    """
    now = time.time()
    started = _this_conversation_began(user_id)
    with db.connect() as conn:
        if conn.execute(
            "SELECT 1 FROM memories WHERE user_id=? AND owner='elder'"
            " AND kind='follow_up' AND last_recalled_ts >= ? LIMIT 1",
            (user_id, started),
        ).fetchone():
            return []
        rows = conn.execute(
            "SELECT * FROM memories WHERE user_id=? AND owner='elder' AND kind='follow_up' "
            f"AND status='open' AND {_LIVE} AND created_ts < ? AND created_ts > ? "
            "AND recall_count < ? AND (last_recalled_ts IS NULL OR last_recalled_ts < ?) "
            "ORDER BY created_ts ASC LIMIT ?",
            (
                user_id,
                now - FOLLOW_UP_MIN_AGE,
                now - FOLLOW_UP_MAX_AGE,
                FOLLOW_UP_MAX_SURFACES,
                now - FOLLOW_UP_COOLDOWN,
                limit,
            ),
        ).fetchall()
    return [dict(r) for r in rows]


def surface_follow_up(user_id: str, follow_up_id: int) -> None:
    """Mark a follow-up as raised; auto-close it once it's been raised enough."""
    _mark_recalled([follow_up_id])
    with db.connect() as conn:
        conn.execute(
            "UPDATE memories SET status='done' "
            "WHERE id=? AND user_id=? AND kind='follow_up' AND recall_count >= ?",
            (follow_up_id, user_id, FOLLOW_UP_MAX_SURFACES),
        )


def latest_mood(user_id: str) -> str | None:
    with db.connect() as conn:
        row = conn.execute(
            "SELECT content FROM memories WHERE user_id=? AND owner='elder' AND kind='mood' "
            "ORDER BY created_ts DESC LIMIT 1",
            (user_id,),
        ).fetchone()
    return row["content"] if row else None


def counts(user_id: str, owner: str = "elder") -> dict[str, int]:
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT kind, COUNT(*) AS n FROM memories WHERE user_id=? AND owner=? "
            f"AND {_LIVE} GROUP BY kind",
            (user_id, owner),
        ).fetchall()
    return {r["kind"]: r["n"] for r in rows}


# --------------------------------------------------------------------------- #
# Assemble the memory block for the system prompt
# --------------------------------------------------------------------------- #
async def build_memory_context(user_id: str, query_text: str) -> str:
    """Recalled stories + (sometimes) a resurfaced memory + a due follow-up + mood.

    Facts are fetched separately (facts_context). He always speaks first; this is
    what the companion should have in mind when he answers.
    """
    used: set[int] = set()
    sections: list[str] = []

    relevant = await recall_relevant(user_id, query_text, exclude=used)
    used.update(r["id"] for r in relevant)
    if relevant:
        lines = "\n".join(f"- {_fmt(r)}" for r in relevant)
        sections.append(
            "Из ваших прошлых бесед (можешь мягко вспомнить, если к слову):\n" + lines
        )

    # A gentle, spaced "а помнишь…" — sometimes, out of nowhere.
    if random.random() < RESURFACE_CHANCE:
        r = resurface(user_id, exclude=used)
        if r:
            used.add(r["id"])
            sections.append(
                "Тёплый момент, о котором можешь вспомнить сам, даже без повода:\n"
                f"- {_fmt(r)}"
            )

    # A caring follow-up that's due — check back on what he mentioned before.
    for fup in due_follow_ups(user_id, limit=1):
        sections.append(
            "По-доброму поинтересуйся, как дела с тем, о чём он говорил раньше:\n"
            f"- {fup['content']}"
        )
        surface_follow_up(user_id, fup["id"])

    # How he is against HIS OWN normal, not a word with nothing to compare it
    # to. This is the section companion.py's «перемена важнее самого тона»
    # depends on; see mood.py for why one word could never carry it.
    from . import mood as _mood   # local: mood imports db only, keep it that way

    said = _mood.block(user_id)
    if said:
        sections.append(said)
    else:
        latest = latest_mood(user_id)
        if latest:
            sections.append(f"Его настроение в последнее время: {latest}.")

    return "\n\n".join(sections)


def _fmt(row: dict) -> str:
    title = row.get("title")
    content = row.get("content", "")
    return f"«{title}» — {content}" if title else content


def visits_so_far(user_id: str) -> int:
    """How many separate conversations this person has had. Cheap and exact.

    Counted in SQL rather than by walking rows in Python: a year of daily use is
    eighteen thousand turns, and this is asked on every turn. The window
    function gives each row the timestamp of the one before it, and a visit
    begins wherever that gap is long enough to be somebody putting the phone
    down — the same boundary the rest of this module uses.
    """
    with db.connect() as conn:
        row = conn.execute(
            "SELECT COUNT(*) n FROM ("
            "  SELECT ts - LAG(ts) OVER (ORDER BY id) AS gap"
            "  FROM turns WHERE user_id=?"
            ") WHERE gap IS NULL OR gap > ?",
            (user_id, NEW_CONVERSATION_GAP),
        ).fetchone()
    return int(row["n"] or 0)
