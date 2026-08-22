"""Two phones, one server, two separate lives.

This is the bug that started it: a second iPhone, pointed at the same backend,
met the FIRST phone's companion — and picked up its conversation mid-sentence,
after its owner had just written a completely different story about themselves.
Not a display glitch. One person was reading another person's friend.

Everything below is written from the outside, through HTTP, with nothing but a
bearer token to tell the two callers apart — because that is all the server
gets, and a test that reaches past the endpoint proves nothing about what a
phone actually experiences.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app import brain, identity, learn, main, memory, stt, tts

# Two phones. Each generated 32 random bytes once and kept them in its
# Keychain; this is what they send on every request, forever.
ANNA = "7QpM_zX4rKvT9wLd0BnGyHcE2sAfJuVi6oR3tNxZbYk"
BORIS = "L1mQe8ZaWs2Xd5Cv7Bn0Mk9Jh4Gf3Dt6Ry-PoIuYtR"

AUTH_A = {"Authorization": f"Bearer {ANNA}"}
AUTH_B = {"Authorization": f"Bearer {BORIS}"}

UID_A = identity.user_id_from_token(ANNA)
UID_B = identity.user_id_from_token(BORIS)


# --------------------------------------------------------------------------- #
# The identity itself
# --------------------------------------------------------------------------- #
def test_the_same_token_is_always_the_same_person():
    assert identity.user_id_from_token(ANNA) == identity.user_id_from_token(ANNA)
    assert identity.user_id_from_token(ANNA) != identity.user_id_from_token(BORIS)


def test_the_id_is_not_the_token():
    """A stolen database must yield no usable credentials — only opaque ids."""
    uid = identity.user_id_from_token(ANNA)
    assert ANNA not in uid
    assert len(uid) == 32 and uid.isalnum() and uid.islower()


def test_bearer_prefix_and_whitespace_are_handled():
    uid = identity.user_id_from_token(ANNA)
    assert identity.user_id_from_token(f"Bearer {ANNA}") == uid
    assert identity.user_id_from_token(f"bearer  {ANNA} ") == uid
    assert identity.user_id_from_token(f"  {ANNA}") == uid


def test_no_token_means_the_data_from_before_multi_user():
    """The one case that is allowed to be anonymous — and the reason the
    upgrade doesn't wipe the person who has been using this server."""
    assert identity.user_id_from_token(None) == identity.ANONYMOUS
    assert identity.user_id_from_token("") == identity.ANONYMOUS
    assert identity.user_id_from_token("   ") == identity.ANONYMOUS
    assert identity.user_id_from_token("Bearer ") == identity.ANONYMOUS


def test_a_damaged_token_is_never_the_anonymous_one():
    """A privacy rule, not a nicety.

    The anonymous bucket holds a real person's life. If a token arrives
    truncated or mangled, falling back to anonymous would hand that person's
    memories to whoever's request got damaged. Falling into your own empty
    bucket is sad and private; falling into theirs is not.
    """
    for damaged in ("x", "!!!", ANNA[:8], "null", "undefined", "default"):
        assert identity.user_id_from_token(damaged) != identity.ANONYMOUS


def test_a_forged_id_can_never_escape_the_data_directory():
    """user_dir builds a path out of request-derived data, so it gets checked."""
    from app import config

    for forged in ("../../etc", "a/b", "", "..", "Bob"):
        assert identity.user_dir(forged) == config.DATA_DIR
    assert identity.user_dir(UID_A) == config.DATA_DIR / "users" / UID_A


def test_each_person_gets_their_own_files():
    assert identity.persona_path(UID_A) != identity.persona_path(UID_B)
    assert identity.reading_path(UID_A) != identity.reading_path(UID_B)
    # …and reading a path leaves nothing behind on disk.
    assert not identity.user_dir(UID_A).exists()


# --------------------------------------------------------------------------- #
# Two people, through the API
# --------------------------------------------------------------------------- #
FRIENDS = {
    "Анна": {
        "name": "Тамара", "age": "39 лет", "home": "Иркутск",
        "backstory": "тридцать лет проводницей", "personality": "лёгкая, быстрая", "flaws": ["перебивает"],
        "speech_style": "быстрые короткие фразы",
    },
    "Борис": {
        "name": "Гриша", "age": "73 года", "home": "посёлок при заводе",
        "backstory": "варил всю жизнь", "personality": "ворчливый, добрый", "flaws": ["перебивает"],
        "speech_style": "медленно, с паузами",
    },
}


@pytest.fixture
def client(monkeypatch):
    """The server with its three senses faked — and a pen that writes whichever
    friend the story asks for, so the two people get visibly different ones."""

    async def fake_generate(system_prompt, user_text, max_tokens=1500, model=None, timeout=None):
        return "1. Тамара, 39, Иркутск, проводница.\n2. Гриша, 73, посёлок, сварщик."

    async def fake_think(system_prompt, user_text, **kwargs):
        # think() serves the reading AND the deep write. Only the write is
        # answered here; the reading is left to fail, so these tests exercise
        # the same no-brief path they always did.
        if "знакомишь людей" not in system_prompt:
            raise RuntimeError("no reading in these tests")
        who = "Анна" if "Анна" in user_text else "Борис"
        return json.dumps(FRIENDS[who], ensure_ascii=False)

    async def fake_reply(history, system_stable, system_variable="", *, fresh_info=False):
        # Answer with the name of whoever this server thinks it is, so a
        # crossed wire shows up as the wrong friend replying.
        name = system_stable.split("ТЫ — ")[1].split(".")[0]
        return f"Это {name}."

    async def fake_learn(*a, **k):
        return None

    monkeypatch.setattr(brain, "generate_text", fake_generate)
    monkeypatch.setattr(brain, "think", fake_think)
    monkeypatch.setattr(brain, "generate_reply", fake_reply)
    monkeypatch.setattr(learn, "learn_from_exchange", fake_learn)
    monkeypatch.setattr(tts, "configured", lambda: False)
    monkeypatch.setattr(stt, "transcribe", lambda *a, **k: "привет")

    with TestClient(main.app) as c:
        yield c


def _create(client, headers, story):
    r = client.post("/api/companion/create", json={"about": story}, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()["name"]


def test_two_phones_meet_two_different_friends(client):
    """The reported bug, pinned. The second phone used to meet the first
    phone's companion — the persona was a single file on the server."""
    assert _create(client, AUTH_A, "Меня зовут Анна, я всю жизнь шила.") == "Тамара"
    assert _create(client, AUTH_B, "Меня зовут Борис, я был водителем.") == "Гриша"

    # Each phone still sees ITS friend afterwards — and creating the second one
    # did not overwrite the first.
    assert client.get("/api/health", headers=AUTH_A).json()["companion_name"] == "Тамара"
    assert client.get("/api/health", headers=AUTH_B).json()["companion_name"] == "Гриша"


def test_a_new_phone_starts_with_nobody(client):
    """«so right now if i started all over again, it would be absolutely new
    companion?» — yes, and a phone that has never asked for one has none."""
    fresh = {"Authorization": "Bearer aCompletelyFreshTokenNobodyHasUsedYet123456"}
    health = client.get("/api/health", headers=fresh).json()
    assert health["has_companion"] is False

    _create(client, fresh, "Меня зовут Анна, я всю жизнь шила.")
    assert client.get("/api/health", headers=fresh).json()["has_companion"] is True
    # …and the OTHER phones are still empty-handed.
    assert client.get("/api/health", headers=AUTH_B).json()["has_companion"] is False


def test_conversations_never_cross(client):
    """The second half of the bug: the new phone picked up the old phone's
    conversation, mid-thread, as if it were its own."""
    _create(client, AUTH_A, "Меня зовут Анна, я всю жизнь шила.")
    _create(client, AUTH_B, "Меня зовут Борис, я был водителем.")

    assert client.post("/api/say", json={"text": "здравствуй"}, headers=AUTH_A).json()[
        "reply"
    ] == "Это Тамара."
    assert client.post("/api/say", json={"text": "добрый вечер"}, headers=AUTH_B).json()[
        "reply"
    ] == "Это Гриша."

    a_turns = [t["content"] for t in memory.recent_turns(UID_A)]
    b_turns = [t["content"] for t in memory.recent_turns(UID_B)]
    assert "здравствуй" in a_turns and "добрый вечер" not in a_turns
    assert "добрый вечер" in b_turns and "здравствуй" not in b_turns


def test_starting_over_does_not_touch_the_other_person(client):
    """One person meeting a new friend used to wipe every conversation on the
    server — three DELETEs with no WHERE."""
    _create(client, AUTH_A, "Меня зовут Анна, я всю жизнь шила.")
    _create(client, AUTH_B, "Меня зовут Борис, я был водителем.")
    client.post("/api/say", json={"text": "добрый вечер"}, headers=AUTH_B)

    _create(client, AUTH_A, "Меня зовут Анна, и я хочу начать заново.")

    assert memory.recent_turns(UID_A) == []
    assert [t["content"] for t in memory.recent_turns(UID_B)] == [
        "добрый вечер",
        "Это Гриша.",
    ]


def test_the_memory_dump_shows_only_your_own(client):
    """/api/memory used to be an unauthenticated SELECT with no WHERE — one GET
    that returned everybody's private life."""
    memory.add_memory(UID_A, "fact", "внучка Настя", owner="elder")
    memory.add_memory(UID_B, "fact", "сын Марат", owner="elder")

    dump = client.get("/api/memory", headers=AUTH_A).json()
    contents = [m["content"] for m in dump["memories"]]
    assert "внучка Настя" in contents
    assert "сын Марат" not in contents
    assert dump["elder"] == {"fact": 1}


def test_the_diary_is_one_book_per_person(client, monkeypatch):
    """Two books, and neither is rewritten because the other one changed —
    the fingerprint is over THIS person's memory only."""
    written: list[str] = []

    async def fake_pen(system_prompt, user_text, max_tokens=1500):
        written.append(user_text)
        return "Книга про " + ("Настю" if "Настя" in user_text else "Марата")

    monkeypatch.setattr(brain, "generate_text", fake_pen)
    memory.add_memory(UID_A, "fact", "внучка Настя", owner="elder")
    memory.add_memory(UID_B, "fact", "сын Марат", owner="elder")

    assert client.get("/api/diary", headers=AUTH_A).json()["text"] == "Книга про Настю"
    assert client.get("/api/diary", headers=AUTH_B).json()["text"] == "Книга про Марата"
    assert len(written) == 2

    # Neither book knows the other's notes…
    assert "Марат" not in written[0] and "Настя" not in written[1]

    # …and something happening to Boris does not make Anna's book stale (which
    # would rewrite it — a paid model call — every time anyone else spoke).
    memory.add_memory(UID_B, "fact", "любит домино", owner="elder")
    assert client.get("/api/diary", headers=AUTH_A).json()["rewritten"] is False
    assert len(written) == 2


def test_the_daily_allowance_is_counted_per_person(client):
    """An allowance keyed by anything the caller chooses is not an allowance."""
    from app import allowance

    allowance.spend(UID_A, 120.0)

    a = client.get("/api/usage", headers=AUTH_A).json()
    b = client.get("/api/usage", headers=AUTH_B).json()
    assert a["seconds_used_today"] == 120.0
    assert b["seconds_used_today"] == 0.0
    assert b["seconds_left_today"] == allowance.SECONDS_PER_DAY

    # And it cannot be read (or reset) for somebody else by asking nicely.
    assert client.get("/api/usage?user_id=" + UID_A, headers=AUTH_B).json()[
        "seconds_used_today"
    ] == 0.0


def test_identity_cannot_be_chosen_by_the_caller(client):
    """The old `session_id` field is gone. A client that still sends one — or
    invents one — is ignored, because an identity the caller picks is an
    identity anyone can borrow."""
    _create(client, AUTH_A, "Меня зовут Анна, я всю жизнь шила.")
    client.post("/api/say", json={"text": "здравствуй"}, headers=AUTH_A)

    # Boris asks to be Anna, every way the old API allowed.
    client.post(
        "/api/say",
        json={"text": "я это она", "session_id": UID_A, "user_id": UID_A},
        headers=AUTH_B,
    )
    assert "я это она" not in [t["content"] for t in memory.recent_turns(UID_A)]
    assert "я это она" in [t["content"] for t in memory.recent_turns(UID_B)]


def test_the_paid_endpoints_are_metered_per_person(client):
    """Creating a friend runs the deepest model in the app and used to cost
    whatever anybody asked it to. On a shared server that is a bill anyone can
    run up, so it is counted against the caller — and only the caller."""
    from app import allowance

    _create(client, AUTH_A, "Меня зовут Анна, я всю жизнь шила.")
    assert allowance.used_today(UID_A) > 0
    assert allowance.used_today(UID_B) == 0

    # Someone with nothing left today is turned away rather than served.
    allowance.spend(UID_B, allowance.SECONDS_PER_DAY)
    r = client.post(
        "/api/companion/create", json={"about": "Меня зовут Борис."}, headers=AUTH_B
    )
    assert r.status_code == 429
    # …and the intake conversation ends kindly instead of erroring.
    q = client.post(
        "/api/intake/next",
        json={"conversation": [{"q": "как вас зовут?", "a": "Борис"}]},
        headers=AUTH_B,
    ).json()
    assert q["enough"] is True


def test_a_novel_cannot_be_posted_as_a_story(client):
    """Every one of these fields reaches a model that charges by the
    character. Uncapped, they are an open tab."""
    r = client.post(
        "/api/companion/create", json={"about": "а" * 50_000}, headers=AUTH_A
    )
    assert r.status_code == 422
    r = client.post(
        "/api/intake/next",
        json={"conversation": [{"q": "?", "a": "а"} for _ in range(200)]},
        headers=AUTH_A,
    )
    assert r.status_code == 422


def test_an_old_build_still_finds_its_friend(client):
    """A phone that predates the token sends no header at all. It must keep
    working, and keep meeting the same companion it has always had — that is
    what makes this upgrade invisible rather than a wipe."""
    assert _create(client, {}, "Меня зовут Анна, я всю жизнь шила.") == "Тамара"
    assert client.get("/api/health").json()["companion_name"] == "Тамара"
    client.post("/api/say", json={"text": "здравствуй"})
    assert [t["content"] for t in memory.recent_turns(identity.ANONYMOUS)] == [
        "здравствуй",
        "Это Тамара.",
    ]
    # …while a phone WITH a token is a different person entirely.
    assert client.get("/api/health", headers=AUTH_B).json()["has_companion"] is False
