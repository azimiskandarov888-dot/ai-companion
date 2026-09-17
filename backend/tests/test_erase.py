"""Deleting — the one thing in this app that must not be approximately right.

Two different things used to share one button and one sentence, and neither of
them did anything on the server. «Начать заново» cleared five keys in the
phone's UserDefaults while telling the person, in writing, that he would forget
everything and his diary would close forever. Deleting an account did not exist.

These tests pin three properties:

  · starting over leaves the PERSON and takes the FRIEND — all of him;
  · deleting an account leaves nothing at all, including in tables written
    after these tests;
  · neither can ever reach anybody else, and neither is one malformed id away
    from removing the service.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app import (config, db, diary, emergency, erase, identity, main, memory,
                 mood, persona, reading, safety)

TOKEN = "aVerYlOngRandomLookingTokenFromTheKeychain_0123456789"
AUTH = {"Authorization": f"Bearer {TOKEN}"}
U = identity.user_id_from_token(TOKEN)
OTHER = identity.user_id_from_token("someoneElsesEntirelyDifferentToken_98765")


def _a_whole_friendship(user_id: str) -> None:
    """Somebody with a friend, a history, and everything the app keeps."""
    persona.save_persona(user_id, {"name": "Гриша", "age": "73 года",
                                   "home": "посёлок", "backstory": "варил всю жизнь"})
    reading.save(user_id, {"register": "сухо", "would_reach_them": "спокойно",
                           "do_not_touch": "смерть жены",
                           "learned": ["не звать по отчеству"],
                           "_read_at_visit": 12, "_confirmed_at_read": 3})
    memory.log_turn(user_id, "user", "привет")
    memory.log_turn(user_id, "assistant", "ну здравствуй")
    memory.add_memory(user_id, "fact", "внучку зовут Оля", owner="elder")
    memory.add_memory(user_id, "fact", "живёт у реки", owner="bob")
    emergency.remember(user_id, "Канада")
    safety._record(user_id, {"level": "danger", "kind": "body", "what": "упал"},
                   "я упал")
    with db.connect() as conn:
        conn.execute(
            "INSERT INTO diary(user_id, content, fingerprint, updated_ts)"
            " VALUES (?,?,?,?)", (user_id, "Книга про друга", "fp", 1.0))
        conn.execute(
            "INSERT INTO life(user_id, what, arc, started) VALUES (?,?,?,?)",
            (user_id, "простуда", json.dumps([{"state": "першит"}]), 1.0))
        conn.execute(
            "INSERT INTO body(user_id, throat, tired, ts) VALUES (?,?,?,?)",
            (user_id, 0.4, 0.2, 1.0))
        conn.execute(
            "INSERT INTO companion_feeling(user_id, valence, arousal, note, ts)"
            " VALUES (?,?,?,?,?)", (user_id, 0.5, -0.2, "тихо", 1.0))
        conn.execute(
            "INSERT INTO observations(user_id, tag, subject, times, first_ts, last_ts)"
            " VALUES (?,?,?,?,?,?)", (user_id, "слышит-плохо", "", 2, 1.0, 2.0))
        conn.execute(
            "INSERT INTO mood_readings(user_id, ts, energy, warmth, word)"
            " VALUES (?,?,?,?,?)", (user_id, 1.0, 0.5, 0.5, "ровное"))
        conn.execute(
            "INSERT INTO usage(user_id, day, seconds, turns) VALUES (?,?,?,?)",
            (user_id, "2026-09-17", 120, 4))


def _rows(table: str, user_id: str) -> int:
    with db.connect() as conn:
        return conn.execute(
            f"SELECT COUNT(*) n FROM {table} WHERE user_id=?", (user_id,)
        ).fetchone()["n"]


# --------------------------------------------------------------------------- #
# The two lists have to cover the schema, today and after the next table
# --------------------------------------------------------------------------- #


def test_every_table_is_either_his_or_theirs():
    """THE TEST THIS MODULE IS REALLY FOR.

    Starting over names its tables, because whose a table is — his or hers — is
    a judgement and cannot be derived. That makes it a promise somebody has to
    keep, so the day a table is added and claimed by neither list, this fails
    and somebody has to decide. Without it the new table simply survives a
    parting that told the person he would forget everything.
    """
    with db.connect() as conn:
        about_people = set(erase._tables_about_people(conn))
    unclaimed = about_people - set(erase.HIS) - set(erase.SPLIT) - set(erase.THEIRS)
    assert not unclaimed, f"новая таблица, и непонятно, чья она: {sorted(unclaimed)}"
    # …and nothing is claimed by both, which would read as an answer while
    # being two contradictory ones.
    claimed = list(erase.HIS) + list(erase.SPLIT) + list(erase.THEIRS)
    assert len(claimed) == len(set(claimed))


def test_deleting_everything_asks_the_schema_rather_than_a_list(monkeypatch):
    """A hard-coded list of tables is a promise with a silent failure: a table
    added next month is left behind while the person has been told their data
    is gone. So the list is not a list — and this proves it by inventing a
    table the code has never heard of."""
    with db.connect() as conn:
        conn.execute("CREATE TABLE souvenirs (user_id TEXT, what TEXT)")
        conn.execute("INSERT INTO souvenirs VALUES (?,?)", (U, "ракушка"))

    erase.everything(U)
    assert _rows("souvenirs", U) == 0


# --------------------------------------------------------------------------- #
# Starting over: he goes, the person stays
# --------------------------------------------------------------------------- #


def test_everything_he_knew_goes_with_him():
    """What the sheet has been promising all along, and what nothing did."""
    _a_whole_friendship(U)
    erase.the_companion(U)

    assert not persona.has_persona(U)
    for table in erase.HIS:
        assert _rows(table, U) == 0, f"{table} пережила расставание"
    assert diary._load_cached(U) is None
    # What HE had told them about his own life goes with him…
    assert memory.bob_self_context(U) == ""


def test_the_person_is_not_deleted_along_with_him():
    """A new friend does not make somebody a new person. Being made to tell
    your whole life again to prove otherwise is the opposite of what this is
    for — and the emergency number is not his to take with him either."""
    _a_whole_friendship(U)
    erase.the_companion(U)

    kept = reading.load(U)
    assert kept["register"] == "сухо"
    assert kept["do_not_touch"] == "смерть жены"
    assert kept["learned"] == ["не звать по отчеству"]
    # …and so does what they told HIM about themselves. The granddaughter's
    # name is true of them whoever they are talking to — which is what makes
    # starting over «choose who to meet next» rather than «tell it all again».
    assert "Оля" in memory.facts_context(U, "elder")
    assert "911" in emergency.numbers(U)          # where they live is theirs
    assert _rows("usage", U) == 1                 # the day's spending is not reset
    assert _rows("alerts", U) == 1                # the watcher's ledger is a record


def test_the_new_friend_does_not_inherit_the_old_ones_age():
    """mood.py's visit count IS the age of the friendship, and fit.py calls
    itself a property of the pair. Kept, they would have a stranger greeting
    somebody like an old acquaintance on his first evening — which is the
    borrowed life this whole app exists to prevent."""
    _a_whole_friendship(U)
    erase.the_companion(U)

    assert memory.visits_so_far(U) == 0
    assert mood.confirmed_count(U) == 0


def test_the_readings_counters_do_not_outlive_the_friendship_they_counted():
    """Subtle, and it would have been silent. `keep_reading` compares these
    against a visit count that has just gone back to zero, gets a negative
    number, and never re-reads the person again — so the app would hold a
    description of who they used to be, forever."""
    _a_whole_friendship(U)
    erase.the_companion(U)

    kept = reading.load(U)
    for counter in erase._FRIENDSHIP_COUNTERS:
        assert counter not in kept


def test_starting_over_twice_is_not_an_error():
    """Somebody taps it, nothing visible happens fast enough, they tap again."""
    _a_whole_friendship(U)
    erase.the_companion(U)
    assert erase.the_companion(U) == {} or not persona.has_persona(U)


# --------------------------------------------------------------------------- #
# Leaving: nothing at all
# --------------------------------------------------------------------------- #


def test_leaving_takes_everything_including_what_starting_over_keeps():
    _a_whole_friendship(U)
    gone = erase.everything(U)

    for table in erase.HIS + erase.SPLIT + erase.THEIRS:
        assert _rows(table, U) == 0, f"{table} пережила удаление аккаунта"
    assert not persona.has_persona(U)
    assert not reading.load(U)
    assert not reading.history_path(U).exists()
    assert emergency.known(U) is False
    assert gone["files"] >= 2


def test_leaving_is_not_an_error_for_somebody_who_never_arrived():
    assert erase.everything(U) == {}


# --------------------------------------------------------------------------- #
# It can never reach anybody else
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("erasing", [erase.everything, erase.the_companion])
def test_one_persons_parting_is_not_anothers(erasing):
    _a_whole_friendship(U)
    _a_whole_friendship(OTHER)
    erasing(U)

    assert persona.has_persona(OTHER)
    assert reading.load(OTHER)["register"] == "сухо"
    assert _rows("turns", OTHER) == 2
    assert _rows("memories", OTHER) == 2


def test_a_malformed_id_cannot_delete_the_service(tmp_path, monkeypatch):
    """THE ONE THAT WOULD NOT HAVE BEEN FUNNY.

    identity.user_dir falls back to the whole data directory for any id it does
    not recognise — and that directory holds the database and every other
    person's folder. A deletion must never be one bad id away from removing
    everybody. The guard is on the resolved PATH, not on the id.
    """
    _a_whole_friendship(U)
    ours = identity.user_dir(U)
    assert ours.exists()

    for bad in ("", "../..", "default", "не-хеш", "A" * 32):
        erase.everything(bad)

    assert config.DATA_DIR.exists()
    assert ours.exists(), "чужая папка исчезла из-за чужого кривого id"
    assert persona.has_persona(U)


def test_the_anonymous_user_is_deleted_by_name_not_by_folder(tmp_path, monkeypatch):
    """Their files sit loose in data/, beside the database and everybody else's
    folders, so this is the one person whose deletion may not remove a
    directory."""
    monkeypatch.setattr(config, "PERSONA_PATH", tmp_path / "persona.json")
    monkeypatch.setattr(config, "READING_PATH", tmp_path / "reading.json")
    _a_whole_friendship(identity.ANONYMOUS)
    _a_whole_friendship(U)

    erase.everything(identity.ANONYMOUS)

    assert not persona.has_persona(identity.ANONYMOUS)
    assert config.DATA_DIR.exists()
    assert persona.has_persona(U)


# --------------------------------------------------------------------------- #
# Over the wire
# --------------------------------------------------------------------------- #


@pytest.fixture
def client():
    with TestClient(main.app) as c:
        yield c


def test_the_two_are_different_endpoints(client):
    """They must never be one route with a flag. The whole failure this fixes
    is two different things having shared one button and one sentence."""
    _a_whole_friendship(U)

    r = client.post("/api/companion/start-over", headers=AUTH)
    assert r.status_code == 200 and r.json()["ok"]
    assert reading.load(U)["register"] == "сухо"      # they are still here

    r = client.delete("/api/me", headers=AUTH)
    assert r.status_code == 200 and r.json()["ok"]
    assert not reading.load(U)                        # and now they are not


def test_a_deletion_says_what_went_rather_than_ok(client):
    """Somebody who has just asked for this is owed more than being told to
    trust us."""
    _a_whole_friendship(U)
    gone = client.delete("/api/me", headers=AUTH).json()["gone"]
    assert gone["turns"] == 2
    assert gone["memories"] == 2
    assert gone["files"] >= 2


def test_deleting_reaches_only_the_caller_over_the_wire(client):
    """Identity comes from the token and from nowhere else, so there is no
    shape of request that deletes somebody else."""
    _a_whole_friendship(U)
    _a_whole_friendship(OTHER)

    client.delete("/api/me", headers=AUTH)
    assert persona.has_persona(OTHER)


def test_the_app_can_tell_that_he_is_gone(client):
    """«Начать заново» sends the phone back to «кого бы вы хотели встретить»,
    and reconcileWithServer acts only on a clear no. So the server has to give
    one."""
    _a_whole_friendship(U)
    assert client.get("/api/health", headers=AUTH).json()["has_companion"] is True

    client.post("/api/companion/start-over", headers=AUTH)
    assert client.get("/api/health", headers=AUTH).json()["has_companion"] is False
