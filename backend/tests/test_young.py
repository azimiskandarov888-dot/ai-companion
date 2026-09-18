"""When the person is not an adult.

Owner's decision, 2026-09-18, and the shape of it is the point: NO DOOR. There
is no age screen and there will not be one — the app must feel free to open and
talk, the way YouTube does. What changes is how he speaks, and what is kept.

Which is also, exactly, what Google had to change after the YouTube settlement:
not who gets in, but what is stored — regardless of who is really watching.

These tests pin four things:

  · the band is read from the warm-up answer, and adults are never marked;
  · nothing about a young person accumulates, ever;
  · the conversation happening right now still works, because a friend who
    forgets the last sentence is not a friend;
  · the one word that IS kept survives, or the whole thing lasts one reply.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import (brain, companion, db, erase, identity, learn, main, memory,
                 persona, reading, safety, tts, young)

TOKEN = "aVerYlOngRandomLookingTokenFromTheKeychain_0123456789"
AUTH = {"Authorization": f"Bearer {TOKEN}"}
U = identity.user_id_from_token(TOKEN)


# --------------------------------------------------------------------------- #
# Reading an age out of what somebody actually types
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "said,band",
    [
        ("7", young.CHILD),
        ("мне 7 лет", young.CHILD),
        ("12", young.CHILD),
        ("13", young.TEEN),
        ("мне только что исполнилось 15", young.TEEN),
        ("17 лет", young.TEEN),
        ("18", ""),
        ("45", ""),
        ("87", ""),
    ],
)
def test_the_band_comes_from_the_answer_the_warm_up_already_gets(said, band):
    """«Сколько вам лет, если не секрет?» is asked warmly, inside the
    conversation, because a friend asks that. It is a better question than a
    form in both directions: it is not a checkpoint, and the law turns on
    whether the operator SHOULD HAVE KNOWN — which, having asked, we do."""
    assert young.band(said) == band


@pytest.mark.parametrize(
    "said", ["", "   ", None, "не скажу", "а зачем тебе", "родился в 2012", "много"]
)
def test_no_answer_means_adult(said):
    """The honest default for a product whose users are overwhelmingly grown —
    and the one that keeps the app feeling free. A guess in the other direction
    would treat a silent eighty-year-old like a child."""
    assert young.band(said) == ""


def test_an_adult_is_never_written_down():
    """A row here means «not an adult», so its absence and its presence say two
    different things. A row that meant nothing would make the table unreadable
    by anybody trying to work out what happened."""
    assert young.remember(U, "45") == ""
    assert young.of(U) == ""
    assert young.is_young(U) is False


def test_a_child_is_written_down_once_and_stays():
    assert young.remember(U, "мне 9") == young.CHILD
    assert young.is_young(U) is True
    # …and the friendship ending does not make them an adult.
    erase.the_companion(U)
    assert young.of(U) == young.CHILD


def test_leaving_takes_it_like_everything_else():
    young.remember(U, "14")
    erase.everything(U)
    assert young.of(U) == ""


# --------------------------------------------------------------------------- #
# How he speaks
# --------------------------------------------------------------------------- #


def test_nothing_changes_for_a_grown_up():
    """Nearly everybody. Not one character of their prompt moves."""
    assert young.block(U) == ""


def test_a_child_and_a_teenager_are_not_the_same_person():
    """«Ну а в школе как дела?» to a seventeen-year-old lands the way «вспомни
    молодость» lands on a twenty-year-old — the constitution already says so
    about age generally, and it is truest here."""
    young.remember(U, "8")
    child = young.block(U)
    young.remember(U, "16")
    teen = young.block(U)

    assert "МЕНЬШЕ ТРИНАДЦАТИ" in child
    assert "НЕТ ВОСЕМНАДЦАТИ" in teen
    assert "Не сюсюкай" in teen, "с подростком снисходительность — верный способ его потерять"


def test_he_sends_them_to_real_people_and_to_a_grown_up():
    """The measure of success for this app is that somebody goes on having a
    life with real people in it. For a child that is not a nice-to-have — it is
    the one thing an app must not quietly replace."""
    for age in ("8", "16"):
        young.remember(U, age)
        block = young.block(U)
        assert "живых" in block
        assert "взрослому, которому доверяет" in block
        assert "Не держи его долго" in block


def test_it_is_late_in_the_prompt_where_instructions_are_obeyed():
    """It could have ridden free in the cached half — a person's age does not
    change between turns. It does not, because this one has to be FOLLOWED, and
    the end of a prompt is where an instruction lands best. A few hundred
    characters a turn is a cheap price for not getting it wrong with a child."""
    stable, variable = companion.build_system_parts(
        persona_block="Тебя зовут Гриша.",
        memory_context="что-то про вчера",
        elder_facts="внучку зовут Оля",
        situation_block="СЕЙЧАС ВЫ ИГРАЕТЕ В ГОРОДА.",
        young_block=young._CHILD_BLOCK,
    )
    # Not in the cached half, where it would have been free.
    assert "ПЕРЕД ТОБОЙ РЕБЁНОК" not in stable
    # Dead last on an ordinary turn — after the memories, after this turn's own
    # rules. The only thing allowed past it is the note that fires once, on the
    # first reply of a conversation.
    assert variable.rstrip().endswith(young._CHILD_BLOCK.strip())


# --------------------------------------------------------------------------- #
# Nothing is kept — over the wire
# --------------------------------------------------------------------------- #

SCRIBE_RAN: list[str] = []


@pytest.fixture
def client(monkeypatch):
    async def fake_reply(history, system_stable, system_variable="", *, fresh_info=False):
        return "Ну здравствуй. Как в школе-то?"

    async def fake_learn(user_id, *, farewell=False):
        SCRIBE_RAN.append(user_id)

    async def quiet(system, user_text, **kw):
        return '{"level":"none","kind":"body","what":""}'

    SCRIBE_RAN.clear()
    monkeypatch.setattr(brain, "generate_reply", fake_reply)
    monkeypatch.setattr(tts, "configured", lambda: False)
    monkeypatch.setattr(learn, "learn_from_conversation", fake_learn)
    monkeypatch.setattr(safety.brain, "generate_text", quiet)
    with TestClient(main.app) as c:
        yield c


def _say(client, text="привет"):
    r = client.post("/api/say", json={"text": text}, headers=AUTH)
    assert r.status_code == 200, r.text
    return r.json()


def _rows(table: str) -> int:
    with db.connect() as conn:
        return conn.execute(
            f"SELECT COUNT(*) n FROM {table} WHERE user_id=?", (U,)
        ).fetchone()["n"]


def test_no_profile_is_ever_built_for_a_child(client):
    """The scribe distils somebody into facts, the reader reads them, the
    register measures them. For a child none of it runs — so there is no
    dossier to leak, to subpoena, or to have to delete later."""
    young.remember(U, "9")
    _say(client)

    assert SCRIBE_RAN == [], "писарь разбирал ребёнка на факты"


def test_a_grown_up_is_not_affected_by_any_of_this(client):
    """The other half, and the one that decides whether this can ship: the app
    for the people it was built for must be exactly as it was."""
    _say(client)
    assert SCRIBE_RAN == [U]


def test_what_was_learned_earlier_is_taken_away(client):
    """Not only «stop collecting» — «stop having». A dossier built before the
    app knew, or before the person said how old they were, is the same dossier."""
    memory.add_memory(U, "fact", "живёт с бабушкой", owner="elder")
    reading.save(U, {"register": "коротко", "would_reach_them": "спокойно"})
    young.remember(U, "11")

    _say(client)

    assert memory.facts_context(U, "elder") == ""
    assert not reading.load(U)
    assert not identity.reading_path(U).exists()


def test_his_own_life_is_his_and_stays(client):
    """What HE has said about himself is not the child's data, and a companion
    who forgets his own stories between Tuesday and Wednesday is the
    borrowed-life problem wearing a different hat."""
    persona.save_persona(U, {"name": "Гриша", "age": "73 года", "home": "посёлок"})
    memory.add_memory(U, "fact", "живёт у реки", owner="bob")
    young.remember(U, "10")

    _say(client)

    assert "у реки" in memory.bob_self_context(U)
    assert persona.has_persona(U)


def test_the_conversation_happening_right_now_still_works(client):
    """THE LINE THAT MAKES THIS A FRIEND AND NOT A STRANGER. Keeping nothing
    cannot mean forgetting the sentence before this one — that is not privacy,
    it is a companion with no short-term memory, three times a minute."""
    young.remember(U, "12")
    _say(client, "меня зовут Петя")
    _say(client, "а помнишь, как меня зовут?")

    said = [t["content"] for t in memory.recent_turns(U)]
    assert any("Петя" in s for s in said), "он забыл, что было минуту назад"


def test_yesterday_is_gone_by_today(client):
    """And the moment the conversation ends, it takes it. Come back tomorrow
    and there is nothing about you here."""
    young.remember(U, "12")
    _say(client, "меня зовут Петя")

    # Their words, pushed back past the gap that ends a conversation.
    with db.connect() as conn:
        conn.execute(
            "UPDATE turns SET ts = ts - ? WHERE user_id=?",
            (memory.NEW_CONVERSATION_GAP * 3, U),
        )

    _say(client, "привет ещё раз")
    said = " ".join(t["content"] for t in memory.recent_turns(U))
    assert "Петя" not in said


def test_a_child_gets_a_friend_and_leaves_no_reading_behind(monkeypatch):
    """The window this closes is small and real: the reading is the most
    private thing the app produces, it is made at signup to write the friend,
    and without this it would sit on disk from then until the first word."""
    import json as _json

    async def fake_read(about, wishes=""):
        return {"register": "коротко", "would_reach_them": "спокойно"}

    async def fake_generate(system_prompt, user_text, max_tokens=1500, model=None,
                            timeout=None, effort=None):
        return "1. Гриша, 73, посёлок, сварщик.\n2. Нина, 52, горы, фельдшер."

    async def fake_think(system_prompt, user_text, **kwargs):
        return _json.dumps({
            "name": "Гриша", "age": "73 года", "home": "посёлок",
            "backstory": "варил всю жизнь", "personality": "ворчливый",
            "flaws": ["перебивает"], "intention": "перебрать лодку",
            "things": ["чайник"], "speech_style": "коротко",
        }, ensure_ascii=False)

    monkeypatch.setattr(reading, "read_person", fake_read)
    monkeypatch.setattr(brain, "generate_text", fake_generate)
    monkeypatch.setattr(brain, "think", fake_think)

    with TestClient(main.app) as c:
        r = c.post("/api/companion/create",
                   json={"about": "люблю рисовать", "age": "мне 9"}, headers=AUTH)
    assert r.status_code == 200

    # He arrived — a child gets a friend like anybody else. There is no door.
    assert persona.has_persona(U)
    # …and the band is the only thing left behind.
    assert young.of(U) == young.CHILD
    assert not identity.reading_path(U).exists()


# --------------------------------------------------------------------------- #
# A teenager gets the full app — and decides about the memory themselves
#
# Owner's decision, 2026-09-18: loneliness peaks in adolescence, and teenagers
# are the second group this is for after the old. So they get a friend their
# OWN age, who remembers them — and the remembering is theirs to switch on.
# --------------------------------------------------------------------------- #


def test_a_teenager_is_remembered_without_being_asked_anything(client):
    """ON, like it is for everybody. A question that pops up unasked is a
    checkpoint wearing friendlier clothes, and this app has no checkpoints —
    the switch lives in Settings for whoever goes looking for it."""
    young.remember(U, "15")
    assert young.keeps_nothing(U) is False

    _say(client)
    assert SCRIBE_RAN == [U]


def test_a_teenager_can_switch_it_off_and_back_on(client):
    """The switch is the whole feature. Off means off from that moment, and it
    can be undone — it is a setting, not a door that locks behind them."""
    young.remember(U, "15")

    assert young.allow(U, False) is False
    assert young.keeps_nothing(U) is True
    _say(client)
    assert SCRIBE_RAN == []

    assert young.allow(U, True) is True
    assert young.keeps_nothing(U) is False
    _say(client)
    assert SCRIBE_RAN == [U]


def test_a_child_has_no_such_switch(client):
    """Consent somebody cannot give is not consent. A switch that pretended
    otherwise would be worse than none at all — it would look like a choice,
    and it would be the one thing COPPA's parental-consent rule is actually
    about rather than a technicality in it."""
    young.remember(U, "9")
    assert young.allow(U, True) is False
    assert young.keeps_nothing(U) is True

    _say(client)
    assert SCRIBE_RAN == []


def test_an_adult_has_nothing_to_answer(client):
    """Their friend has always remembered them, and no switch appears."""
    assert young.allow(U, True) is False
    assert young.keeps_nothing(U) is False


def test_how_he_speaks_and_what_is_kept_are_two_decisions():
    """The easiest thing here to collapse into one flag, and it would be wrong:
    a sixteen-year-old who switches memory OFF is still sixteen, and is still
    spoken to accordingly."""
    young.remember(U, "16")
    young.allow(U, False)

    assert young.keeps_nothing(U) is True         # not remembered…
    assert young.is_young(U) is True              # …and still a teenager
    assert "НЕТ ВОСЕМНАДЦАТИ" in young.block(U)


def test_the_answer_reaches_the_server_over_the_wire(client):
    young.remember(U, "15")
    r = client.post("/api/memory/keep", json={"allow": False}, headers=AUTH)
    assert r.status_code == 200 and r.json()["keeps"] is False
    assert young.allowed(U) is False

    r = client.post("/api/memory/keep", json={"allow": True}, headers=AUTH)
    assert r.json()["keeps"] is True
    assert young.allowed(U) is True


def test_a_teenager_gets_a_friend_their_own_age():
    """Without this the ten sketches span «от двадцати с лишним до восьмидесяти
    с лишним» by construction, and no roll of the dice can find a peer in a list
    that has none. Said in the block that is «закон» at every stage, so both the
    sketches and the deep write get it."""
    from app import matchmaker

    story = matchmaker._their_story("люблю рисовать", "", "15", "", "", band=young.TEEN)
    assert "РОВЕСНИКОМ" in story
    assert "закон" in story

    grown = matchmaker._their_story("люблю рыбалку", "", "70", "", "", band="")
    assert "РОВЕСНИКОМ" not in grown
