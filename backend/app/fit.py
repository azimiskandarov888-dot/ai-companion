"""HOW THESE TWO GO TOGETHER — which is not a property of either of them.

`reading.py` models the person. `persona.py` models the friend. `mood.py` models
how the person is today. Nothing modelled the PAIR, and the pair is where the
answer lives: a companion is not supposed to be good, he is supposed to be good
FOR THIS PERSON, and those are different targets.

The intake cannot produce this. Fit is only discoverable in the conversation,
because it is made of what actually happened between them — which is why this
file reads the observation register rather than any document.

── WHAT THE RESEARCH ACTUALLY SAYS ─────────────────────────────────────────

The question this file exists to answer is: a calm person's best friend is
often the one who never sits still. When does that work, and when does the very
same difference become exhausting? Four findings, and together they are an
answer rather than a shrug.

1. THE TWO AXES BEHAVE OPPOSITELY. Contemporary integrative interpersonal
   theory (Kiesler, and the circumplex tradition after Leary) finds that
   successful interaction is CORRESPONDING in warmth and RECIPROCAL in
   dominance. Warmth invites warmth; coldness invites coldness — there you
   match. Push invites yield and yield invites push — there you may be
   opposite. So the answer is not "similar" or "different": it is different on
   one axis and the same on the other, and swapping them is how a companion
   becomes either a mirror or a stranger.

2. THE DIFFERENCE STANDS ON A SHARED FLOOR. Similarity-attraction is the most
   robust finding in the field, and self-expansion work qualifies rather than
   contradicts it: dissimilarity draws people only where a base of similarity
   already makes the relationship feel safe. Agreement about what is funny,
   what is sacred and what matters is not optional decoration — it is the
   ground the difference stands on.

3. VOLUNTARY, NOT COMPULSIVE. This is the one that answers "when does it stop
   working", and it is a real empirical distinction that looks like one thing
   and is two. Interpersonal SPIN — behaviour swinging around driven by one's
   own weather — predicts LOWER closeness and satisfaction. Psychological
   FLEXIBILITY — a wide repertoire and the ability to choose what the moment
   needs — predicts HIGHER relationship quality, for both people. The
   thousand-volt friend is loved because he CAN sit down, not although he can.
   A friend who cannot sit down is not high-energy; he is a demand.

4. IDEALS ARE IDIOSYNCRATIC. The Ideal Standards Model finds that satisfaction
   tracks ideal-PERCEPTION consistency: how well this partner matches THIS
   person's ideals, never the population's. There is no objectively ideal nose.
   So the companion's imperfections should not be generically charming ones —
   they should be the particular imperfections this person happens to love, and
   the only way to know which is to watch which ones he smiles at.

── WHAT IS DONE WITH THAT ─────────────────────────────────────────────────

Nothing here decides anything from one occurrence. Every line of the block
below is a count of things that were watched happening at least twice, for the
same reason mood.py holds its register: once is a coincidence, and a companion
that reshapes itself around a coincidence is worse than one that doesn't
reshape at all.
"""

from __future__ import annotations

from . import db, mood

#: Same bar as everywhere else. Once is a coincidence.
CONFIRMED_AT = mood.CONFIRMED_AT


def _counts(user_id: str) -> dict[str, int]:
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT tag, SUM(times) n FROM observations WHERE user_id=? GROUP BY tag",
            (user_id,),
        ).fetchall()
    return {r["tag"]: r["n"] for r in rows}


def _net(c: dict[str, int], yes: str, no: str) -> tuple[int, int]:
    return c.get(yes, 0), c.get(no, 0)


def block(user_id: str) -> str:
    """The calibration — STABLE half. It is about who they are together."""
    c = _counts(user_id)
    out: list[str] = []

    # ── tempo: the axis where being opposite is allowed ────────────────────
    good, bad = _net(c, "зашло_что_позвал", "не_зашло_что_позвал")
    if good >= CONFIRMED_AT and good > bad:
        out.append(
            f"ТЕМП. Твой напор ему заходит — {good} раза он от него оживал. "
            "Предлагай, зови, затевай. Это ровно то, чего у него самого нет и "
            "за чем он к тебе идёт."
        )
    elif bad >= CONFIRMED_AT and bad >= good:
        out.append(
            f"ТЕМП. Твой напор ему НЕ заходит — {bad} раза он от него закрывался. "
            "Сбавь. Не затевай, не тормоши, не предлагай. Будь тем, кто рядом и "
            "молчит, пока его не позовут."
        )

    led = c.get("сам_повёл_разговор", 0)
    if led >= CONFIRMED_AT:
        out.append(
            f"ОН УМЕЕТ ВЕСТИ САМ — так было {led} раза. Когда он завёл тему, "
            "не перехватывай и не улучшай её. Слушай и не мешай."
        )

    # ── disagreement: warmth's edge ────────────────────────────────────────
    ok, notok = _net(c, "понравилось_несогласие", "не_понравилось_несогласие")
    if ok >= CONFIRMED_AT and ok > notok:
        out.append(
            f"СПОР ЕМУ В РАДОСТЬ — {ok} раза он оживал, когда ты не соглашался. "
            "Не поддакивай ему. Имей своё и говори его."
        )
    elif notok >= CONFIRMED_AT and notok >= ok:
        out.append(
            f"СПОР ЕМУ НЕ В РАДОСТЬ — {notok} раза он от него замыкался. "
            "Своё мнение оставь при себе, если его не спросили прямо. "
            "Не переубеждай, даже мягко."
        )

    # ── the nose: which of his imperfections this person happens to love ───
    slips = c.get("понравился_его_промах", 0)
    if slips >= CONFIRMED_AT:
        out.append(
            f"ЕМУ НРАВЯТСЯ ТВОИ ПРОМАХИ — {slips} раза. Не исправляйся и не "
            "становись безупречным. Это не то, что он тебе прощает, — это то, "
            "за что он тебя любит. Идеальных не любят."
        )

    # ── how he is spoken TO, which is not about character at all ───────────
    slow = c.get("просил_помедленнее", 0) + c.get("не_расслышал", 0)
    if slow >= CONFIRMED_AT:
        out.append(
            f"ЕМУ ТРУДНО РАЗБИРАТЬ РЕЧЬ — {slow} раза он переспрашивал или просил "
            "иначе. Говори короче и проще, по одной мысли за фразу. Он про это "
            "больше не попросит: люди с плохим слухом не жалуются, они привыкают."
        )

    if not out:
        return ""

    return (
        "КАК ВАМ ДВОИМ ХОРОШО ВМЕСТЕ (это не догадки о нём, а то, что уже "
        "случалось между вами не по одному разу):\n"
        + "\n".join(f"- {line}" for line in out)
    )
