"""DELETING — the two different things that both got called «начать заново».

Until now neither existed on the server. «Начать заново» cleared five keys in
the phone's UserDefaults and told the person, in writing, that «Фёдор забудет всё,
и его дневник закроется навсегда. Это нельзя отменить.» Every word of that was untrue:
he remembered everything, his diary was intact, and the only thing that had
happened was that one phone had forgotten his name. Deleting an account did
not exist at all.

── THEY ARE NOT THE SAME THING ───────────────────────────────────────

  · `the_companion()` — STARTING OVER. Somebody wants a different friend: a
    different name, a different life, a different way of talking. He goes, and
    so does everything that happened between them. What the app understands
    about the PERSON stays, because a new friend does not make somebody a new
    person, and being asked to tell your whole life again to prove that is the
    opposite of what this is for.

  · `everything()` — LEAVING. Not a friend going: a person going. Every row
    in every table and every file on disk, with no archive, no tombstone and
    no way back. The one function here that must be able to look somebody in
    the eye afterwards.

── WHY THE TABLE LIST IS NOT A LIST ────────────────────────────────

`everything()` asks the DATABASE which tables are about a person rather than
naming them. A hard-coded list is a promise somebody else has to keep, and its
failure mode is the worst one available here: a table added next month is
silently left behind, while the person has been told their data is gone. A
list can fall behind a schema; a question cannot.

Starting over DOES name its tables, because there the two halves are a
judgement — whose is this, his or hers — and a judgement cannot be derived.
What keeps that honest is a test rather than a comment:
`test_every_table_is_either_his_or_theirs` fails the build the day a table is
added that none of the three lists claims.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from . import config, db, identity, reading

#: HIS, and THEIRS TOGETHER — whole tables, all of which go when somebody
#: starts over.
#:
#: `turns` is the friendship itself. `diary` is his book about them. `life`,
#: `body` and `companion_feeling` are his week, his throat and his mood: they
#: belong to a man who is leaving, and a new friend arriving mid-way through
#: somebody else's cold is not a small oddity.
#:
#: `observations` and `mood_readings` are the subtle two, and they go for the
#: same reason. fit.py calls itself «a property of the pair», and the visit
#: count that mood.py keeps is the AGE OF THE FRIENDSHIP. A new friend
#: inheriting forty visits would greet a stranger like an old acquaintance on
#: his first evening — which is exactly the borrowed life this app exists to
#: prevent.
HIS = (
    "turns",
    "diary",
    "life",
    "body",
    "companion_feeling",
    "observations",
    "mood_readings",
)

#: SPLIT DOWN THE MIDDLE, by its `owner` column.
#:
#: `owner='bob'` is what he had revealed about his OWN life, and it leaves with
#: him. `owner='elder'` is what he had been told about THEIRS — the
#: granddaughter's name, the bad knee, the birthday — and that stays true
#: whoever they are talking to. This is not a new judgement: it is the one
#: memory.forget_companion has been making since multi-user landed, kept here
#: because there must be exactly one place that says what a parting removes.
SPLIT = ("memories",)

#: `ages` is the one word kept about somebody who is not an adult (young.py),
#: and it survives a parting for the plainest reason there is: a child who
#: chooses a new friend is still a child.
THEIRS = ("places", "usage", "alerts", "ages")

#: Counters inside the reading that point at a friendship that no longer
#: exists. Left in place they are worse than wrong: `keep_reading` compares
#: them against a visit count that has just gone back to zero, gets a negative
#: number, and quietly never re-reads the person again.
_FRIENDSHIP_COUNTERS = ("_read_at_visit", "_read_at_turn", "_confirmed_at_read")


def _tables_about_people(conn) -> list[str]:
    """Every table in this database that is keyed by a person.

    Asked, not listed — see the module docstring.
    """
    names = [
        row["name"]
        for row in conn.execute(
            "SELECT name FROM sqlite_master"
            " WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
    ]
    about = []
    for name in names:
        columns = {row["name"] for row in conn.execute(f'PRAGMA table_info("{name}")')}
        if "user_id" in columns:
            about.append(name)
    return sorted(about)


def _delete_from(conn, tables, user_id: str) -> dict[str, int]:
    gone: dict[str, int] = {}
    for table in tables:
        cursor = conn.execute(f'DELETE FROM "{table}" WHERE user_id=?', (user_id,))
        if cursor.rowcount > 0:
            gone[table] = cursor.rowcount
    return gone


def _folder(user_id: str) -> Path | None:
    """This person's own folder, or None if they do not have one of their own.

    THE GUARD HERE IS LOAD-BEARING and it is not `is_anonymous`. `user_dir`
    falls back to the whole data directory for any id it does not recognise —
    the anonymous user, but also a malformed one — and that directory holds
    the database and every other person's folder. Deleting an account must
    never be one bad id away from deleting the service.

    So the test is on the resolved path, not on the id: a folder counts as
    somebody's own only if it sits directly inside `data/users/`.
    """
    folder = identity.user_dir(user_id)
    return folder if folder.parent == config.DATA_DIR / "users" else None


def _erase_files(user_id: str) -> int:
    """Their persona, their reading, and its history. Returns how many went."""
    folder = _folder(user_id)
    if folder is not None:
        # The whole folder rather than three names: a file added here later
        # would otherwise survive a deletion that reported having removed
        # everything, which is the failure this module exists to not have.
        if not folder.exists():
            return 0
        count = sum(1 for path in folder.rglob("*") if path.is_file())
        shutil.rmtree(folder, ignore_errors=True)
        return count
    # The pre-multi-user user, whose files sit loose in data/ beside the
    # database. Named, one at a time, and nothing else touched.
    count = 0
    for path in (
        identity.persona_path(user_id),
        identity.reading_path(user_id),
        reading.history_path(user_id),
    ):
        if path.exists():
            path.unlink(missing_ok=True)
            count += 1
    return count


def everything(user_id: str) -> dict[str, int]:
    """Delete every trace of this person. No archive, no tombstone, no undo.

    Returns what was removed, per table, plus `files` — for the endpoint to
    answer with, and so that somebody checking can see the shape of what went
    rather than having to take "ok" on trust.

    Note what is NOT done: the phone's token is not invalidated, because there
    is nothing to invalidate. The database has only ever held sha256 of it
    (identity.py), so after this runs that hash addresses nothing at all. The
    person keeps the same key to an empty room, which is also why signing up
    again works and does not strand a second bucket somewhere.
    """
    with db.connect() as conn:
        gone = _delete_from(conn, _tables_about_people(conn), user_id)
    gone["files"] = _erase_files(user_id)
    return {k: v for k, v in gone.items() if v}


def the_companion(user_id: str) -> dict[str, int]:
    """He goes, and everything between them goes with him. The person stays.

    The ONE definition of what a parting removes. Both ways of parting reach
    it: the button, through /api/companion/start-over, and simply being given
    somebody new, through matchmaker.create_companion — which must do exactly
    the same thing, and used to do rather less of it.

    The reading survives, and that is the point rather than an oversight: it is
    the app's understanding of the PERSON, and somebody choosing a different
    friend has not become a different person. Its bookkeeping does not survive,
    though — see _FRIENDSHIP_COUNTERS.
    """
    with db.connect() as conn:
        gone = _delete_from(conn, HIS, user_id)
        cursor = conn.execute(
            "DELETE FROM memories WHERE user_id=? AND owner='bob'", (user_id,)
        )
        if cursor.rowcount > 0:
            gone["memories"] = cursor.rowcount

    path = identity.persona_path(user_id)
    if path.exists():
        path.unlink(missing_ok=True)
        gone["companion"] = 1

    was = reading.load(user_id)
    if was and any(key in was for key in _FRIENDSHIP_COUNTERS):
        kept = {k: v for k, v in was.items() if k not in _FRIENDSHIP_COUNTERS}
        reading.save(user_id, kept)
        gone["reading_counters"] = 1
    return {k: v for k, v in gone.items() if v}
