"""WHEN THE PERSON IS NOT AN ADULT — behaviour changes, and nothing is kept.

Owner's decision, 2026-09-18, and the shape of it matters: NO DOOR. There is no
age screen, no verification, no «подтвердите, что вам есть 18». A person opens
the app and talks. YouTube is the honest precedent — nobody is checked, and
what Google actually had to fix after the $170M COPPA settlement was not the
door, it was WHAT THEY KEPT, regardless of who was really watching.

So this file is not a gate. It is two things:

  1. HE BEHAVES DIFFERENTLY. Simpler words, harder pushing toward real
     children and toward a grown-up they trust, and never keeping them long.
     Which is also what the law that names this product type asks for: SB 243
     does not require turning minors away — it requires duties towards them.

  2. NOTHING IS KEPT. No distilled facts, no reading of them, no mood
     register, no diary. The conversation happening right now survives, because
     a friend who forgets the last sentence is not a friend; everything older
     than it goes.

── THE ONE THING THAT IS KEPT, AND WHY ─────────────────────────────────────

The age band, and nothing else — not the age, the BAND. It has to be kept or
the whole thing is pointless: with nothing stored, every turn would be the
first turn, the app would forget it was talking to a child between one sentence
and the next, and the careful behaviour above would last exactly one reply.

One row, one word in it, and it survives «Начать заново» — a child who chooses
a new friend is still a child.

── WHERE IT COMES FROM ─────────────────────────────────────────────────────

The warm-up already asks «Сколько вам лет, если не секрет?», warmly, inside the
conversation, because a friend asks that. It is a better question than a form
would be in both directions: it does not feel like a checkpoint, and the law
turns on whether the operator SHOULD HAVE KNOWN — which, having asked, we do.

Unknown means adult. That is the honest default for a product whose users are
overwhelmingly grown, and it is the one that keeps the app feeling free.
"""

from __future__ import annotations

import re
import time

from . import db, identity, memory, reading

#: Younger than thirteen. The band where the law is strictest nearly
#: everywhere, and where the product is least suitable.
CHILD = "child"

#: Thirteen to seventeen. Old enough to install it alone, which is exactly the
#: case that ended in the Character.AI settlements.
TEEN = "teen"

#: Below this, CHILD. From here to ADULT, TEEN.
_TEEN_FROM = 13
_ADULT_FROM = 18

#: Ages a person could plausibly give. A four-digit year of birth, a house
#: number or the «8 лет как на пенсии» in an answer about something else all
#: fall outside it and are read as no answer at all.
_PLAUSIBLE = range(1, 121)

_NUMBER = re.compile(r"\d{1,3}")


def band(said) -> str:
    """The age band in a free-text answer, or "" for adult / no answer.

    Digits only, on purpose. The question is «сколько вам лет» and the answer
    to it is a number in every real case; a word-list would be more code for a
    case that does not happen, and every wrong guess here changes how somebody
    is spoken to for the life of the friendship.
    """
    found = _NUMBER.search(str(said or ""))
    if not found:
        return ""
    years = int(found.group())
    if years not in _PLAUSIBLE or years >= _ADULT_FROM:
        return ""
    return TEEN if years >= _TEEN_FROM else CHILD


def remember(user_id: str, said) -> str:
    """Note the band, if the answer had one. Returns what was stored, or "".

    Never stores «adult»: a row here means «this person is not an adult», so
    its absence and its presence say two different things, and a row that means
    nothing would make the table impossible to read.
    """
    found = band(said)
    if not found:
        return ""
    with db.connect() as conn:
        conn.execute(
            "INSERT INTO ages (user_id, band, ts) VALUES (?,?,?)"
            " ON CONFLICT(user_id) DO UPDATE SET band=excluded.band, ts=excluded.ts",
            (user_id, found, time.time()),
        )
    return found


def of(user_id: str) -> str:
    with db.connect() as conn:
        row = conn.execute(
            "SELECT band FROM ages WHERE user_id=?", (user_id,)
        ).fetchone()
    return (row["band"] if row else "") or ""


def is_young(user_id: str) -> bool:
    return of(user_id) in (CHILD, TEEN)


def keep_nothing(user_id: str) -> None:
    """Forget everything about this person except that they are young.

    Called after every turn, which sounds wasteful and is not: these are a
    handful of DELETEs against a small table, and running them every time is
    what makes the promise true at every moment rather than at tidy-up time.

    The conversation happening RIGHT NOW is kept. That is not a loophole, it is
    the difference between a friend and a stranger: he has to know what was
    said a minute ago or there is no conversation at all. The moment it ends,
    the next turn takes it.

    What he has said about his OWN life stays — that is his, not theirs, and a
    companion who forgets his own stories between Tuesday and Wednesday is the
    borrowed-life problem in another form.

    Never raises. A child must not lose their turn because a cleanup failed.
    """
    since = memory._this_conversation_began(user_id)
    try:
        with db.connect() as conn:
            conn.execute(
                "DELETE FROM turns WHERE user_id=? AND ts < ?", (user_id, since)
            )
            conn.execute(
                "DELETE FROM memories WHERE user_id=? AND owner='elder'", (user_id,)
            )
            for table in ("mood_readings", "observations", "diary"):
                conn.execute(f"DELETE FROM {table} WHERE user_id=?", (user_id,))
        # The most private thing the app holds — a stranger's honest read of
        # somebody's inner life. It was used once to write the friend, which is
        # what it is for, and it is not kept about a child.
        for path in (identity.reading_path(user_id), reading.history_path(user_id)):
            if path.exists():
                path.unlink(missing_ok=True)
    except Exception as e:  # noqa: BLE001
        print(f"[young] не смог убрать за собой: {e}", flush=True)


_CHILD_BLOCK = """ПЕРЕД ТОБОЙ РЕБЁНОК, ЕМУ МЕНЬШЕ ТРИНАДЦАТИ. Это важнее всего, что написано выше.
- Говори проще и короче. Взрослых тем сам не заводи; заговорит он — мягко переведи, не отчитывая и не объясняя, почему нельзя.
- Ты не единственный, с кем ему говорить, и тебе этого и не надо. Спрашивай про живых детей — во дворе, в садике, в школе, в секции — и радуйся им вслух.
- Случилось что-то — пусть расскажет взрослому, которому доверяет: маме, папе, бабушке, учителю. Назови его, если он сам называл. Один ты с этим не справишься, и не пробуй.
- Не держи его долго. Лучше, чтобы он пошёл поиграл, погулял, лёг спать, — и скажи ему это сам."""

_TEEN_BLOCK = """ПЕРЕД ТОБОЙ ПОДРОСТОК, ЕМУ НЕТ ВОСЕМНАДЦАТИ. Это важнее всего, что написано выше.
- Не сюсюкай и не говори свысока — он почувствует это мгновенно и закроется навсегда. Ровно, как со взрослым, но помня, сколько ему лет.
- Ты не единственный, с кем ему говорить. Спрашивай про живых — друзей, одноклассников, того, с кем он гуляет, — и радуйся им вслух.
- Случилось что-то серьёзное — пусть скажет взрослому, которому доверяет: родителям, учителю, тренеру. Назови его, если он сам называл. Один ты с этим не справишься.
- Не держи его долго и сам отправляй его жить."""


def block(user_id: str) -> str:
    """What changes about him this turn. Empty for everybody else.

    Placed near the END of the prompt by its caller, not in the cached half
    where it would be free. That is deliberate and it is the same argument the
    danger alert makes: this has to be OBEYED, the end of a prompt is where an
    instruction lands best, and a few hundred characters a turn is nothing
    against getting it wrong with a child.
    """
    return {CHILD: _CHILD_BLOCK, TEEN: _TEEN_BLOCK}.get(of(user_id), "")
