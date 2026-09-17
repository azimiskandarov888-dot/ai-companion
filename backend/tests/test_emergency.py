"""Which number he is told to dial.

103 is the ambulance where the first users are. Telling a man in Chicago to dial
it while he is on the floor is not a smaller failure than missing the alarm —
it is the same failure with extra steps. Nobody fills in a settings form, so the
country arrives the way everything else about him arrives: he mentions where he
lives, and it is written down.
"""

from __future__ import annotations

import pytest

from app import config, emergency, learn, safety

U = "u"


# ── learning it from the conversation ───────────────────────────────────────

def test_nothing_is_known_until_he_says_so():
    assert emergency.country(U) == ""
    assert emergency.known(U) is False


@pytest.mark.asyncio
async def test_saying_where_he_lives_is_enough():
    await learn._store(U, {"country": "Израиль"})
    assert emergency.known(U)
    assert "101" in emergency.numbers(U)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "said,expected",
    [
        ("Россия", "103"),
        ("россия", "103"),
        ("  Казахстан  ", "103"),
        ("США", "911"),
        ("Канада", "911"),
        ("Германия", "112"),
        ("Великобритания", "999"),
        ("Австралия", "000"),
    ],
)
async def test_the_number_follows_the_country(said, expected):
    await learn._store(U, {"country": said})
    assert expected in emergency.numbers(U)


@pytest.mark.asyncio
async def test_moving_house_moves_the_number():
    await learn._store(U, {"country": "Россия"})
    assert "103" in emergency.numbers(U)
    await learn._store(U, {"country": "Канада"})
    assert "911" in emergency.numbers(U)
    assert "103" not in emergency.numbers(U)


@pytest.mark.asyncio
async def test_a_country_nobody_listed_is_not_recorded_as_known():
    """Unrecognised has to stay unknown. Storing it would make known() true
    while numbers() still fell back, which reads as «we know where he is» to
    whoever is later trying to work out why he got the wrong number."""
    await learn._store(U, {"country": "Нарния"})
    assert emergency.known(U) is False
    assert emergency.country(U) == ""


@pytest.mark.asyncio
async def test_an_exchange_that_says_nothing_about_place_changes_nothing():
    await learn._store(U, {"country": "Россия"})
    await learn._store(U, {"facts": [{"category": "семья", "value": "внучка Оля"}]})
    assert emergency.country(U) == "россия"


@pytest.mark.asyncio
async def test_nonsense_is_not_fatal():
    for junk in ({"country": ""}, {"country": "   "}, {"country": 42}, {}):
        await learn._store(U, junk)
    assert emergency.known(U) is False


# ── what actually gets said ─────────────────────────────────────────────────

def test_the_universal_number_is_always_there_too():
    """A man in a panic may misremember which number he was told. 112 routes to
    local emergency services nearly everywhere, including from a phone with no
    SIM — so it is never the only thing said, and never left out."""
    emergency.remember(U, "США")
    said = emergency.numbers(U)
    assert "911" in said and "112" in said


def test_a_country_where_112_is_already_the_number_does_not_say_it_twice():
    emergency.remember(U, "Германия")
    assert emergency.numbers(U) == "112"


def test_an_unknown_country_still_gets_a_usable_answer():
    assert config.EMERGENCY_NUMBER in emergency.numbers(U)
    assert emergency.UNIVERSAL in emergency.numbers(U)


# ── the wire into the alarm ─────────────────────────────────────────────────

def test_the_alarm_uses_his_number_not_the_default():
    emergency.remember(U, "Канада")
    said = safety.block({"level": "danger", "what": "упал"}, U)
    assert "911" in said
    assert "103" not in said


def test_the_alarm_without_a_user_still_names_numbers():
    """The signature keeps user_id optional, and a caller without one must not
    produce an alarm with no number in it — worse than knowing, far better than
    nothing."""
    said = safety.block({"level": "danger", "what": "упал"})
    assert config.EMERGENCY_NUMBER in said
    assert emergency.UNIVERSAL in said


def test_one_persons_country_is_not_anothers():
    emergency.remember("анна", "США")
    emergency.remember("борис", "Россия")
    assert "911" in emergency.numbers("анна")
    assert "103" in emergency.numbers("борис")


def test_the_extractor_is_told_to_only_report_what_he_said():
    """A guessed country is worse than none: it would be stored as known and
    silently decide what he is told to dial."""
    assert "ТОЛЬКО если он сам об этом сказал" in learn._EXTRACTION_SYSTEM


# ── saying it in a sentence, in whatever case ───────────────────────────────
#
# The extractor writes a tidy «Израиль». A person answering «в какой стране вы
# живёте?» writes «Живу в Израиле, в Хайфе». Both have to land on the same row.


@pytest.mark.parametrize(
    "said,expected",
    [
        ("Россия", "россия"),
        ("в России", "россия"),
        ("Живу в Израиле, в Хайфе", "израиль"),
        ("в Казахстане", "казахстан"),
        ("в Германии уже двадцать лет", "германия"),
        ("в США", "сша"),
        ("в штате Техас", "штаты"),
        ("в Беларуси", "беларусь"),
        ("на Кипре", "кипр"),
        ("в Нидерландах", "нидерланды"),
    ],
)
def test_where_he_lives_is_understood_however_he_puts_it(said, expected):
    assert emergency.resolve(said) == expected


@pytest.mark.parametrize(
    "said,expected",
    [
        ("Новая Зеландия", "новая зеландия"),
        ("в Новой Зеландии", "новая зеландия"),
        ("в Южной Корее", "южная корея"),
        ("Корея", "корея"),
    ],
)
def test_a_two_word_country_is_never_read_as_its_last_word(said, expected):
    """«южная корея» dials 119 and so does «корея», so this one costs nothing
    today — but a table where they differed would be silently wrong, and the
    order of the scan is the only thing standing between the two."""
    assert emergency.resolve(said) == expected


@pytest.mark.parametrize(
    "said",
    ["Нарния", "Даниил", "Индианаполис", "рука", "Москва", "в деревне",
     "я кореец", "не скажу", "", "   ", None, 42],
)
def test_something_that_is_not_a_country_is_not_read_as_one(said):
    """Every one of these is a real near-miss for a name in the table — «Даниил»
    shares a stem with «Дания», «Индианаполис» contains «Индия», «рука» is two
    letters from «РФ». A wrong country is a man in Chicago being told to dial
    103 while he is on the floor, so near-misses have to miss."""
    assert emergency.resolve(said) == ""


def test_a_city_alone_leaves_the_country_unknown():
    """«Москва» is not «Россия» to this module, and pretending otherwise would
    start it down the road of being a geography database. Unknown falls back to
    the configured default plus 112, which is the honest answer."""
    emergency.remember(U, "Москва")
    assert emergency.known(U) is False


# ── asked at the door, not waited for ───────────────────────────────────────


def _created(json_body, monkeypatch, think=None):
    """POST /api/companion/create with the model calls faked out.

    `think` replaces the deep call, so a test can make writing him fail.
    """
    import json as _json

    from fastapi.testclient import TestClient

    from app import brain, main, reading as _reading

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

    monkeypatch.setattr(_reading, "read_person", fake_read)
    monkeypatch.setattr(brain, "generate_text", fake_generate)
    monkeypatch.setattr(brain, "think", think or fake_think)
    with TestClient(main.app) as client:
        return client.post("/api/companion/create", json=json_body)


def test_he_knows_where_the_person_lives_before_the_first_word(monkeypatch):
    """It used to be learned only by the extractor, several exchanges in — so
    the FIRST conversation, the one where somebody is most likely to say
    something frightening to a stranger, ran on the deployment's default."""
    from app import identity

    r = _created({"about": "Люблю тишину.", "country": "в Израиле"}, monkeypatch)
    assert r.status_code == 200
    assert "101" in emergency.numbers(identity.ANONYMOUS)


def test_where_he_lives_is_written_down_before_the_minute_spent_writing_him(monkeypatch):
    """Stored first, on purpose. Writing a companion is the one place the app
    spends a minute on the deepest model, and it is the likeliest thing in the
    request to fail — a failure there must not also lose the one fact that
    matters if the watcher fires."""
    from app import identity

    async def boom(*a, **kw):
        raise RuntimeError("модель не ответила")

    r = _created({"about": "Люблю тишину.", "country": "Канада"}, monkeypatch, think=boom)
    assert r.status_code == 503
    assert "911" in emergency.numbers(identity.ANONYMOUS)


def test_creating_without_saying_where_changes_nothing(monkeypatch):
    from app import identity

    assert _created({"about": "Люблю тишину."}, monkeypatch).status_code == 200
    assert emergency.known(identity.ANONYMOUS) is False


# ── the numbers, as something to press ──────────────────────────────────────


def test_what_can_be_dialled_is_the_local_number_then_the_universal_one():
    emergency.remember(U, "Канада")
    assert emergency.dialable(U) == ["911", emergency.UNIVERSAL]


def test_a_country_where_112_is_the_number_is_offered_once():
    """Two identical buttons is a worse screen than one, and in a panic it
    reads as a choice to make."""
    emergency.remember(U, "Германия")
    assert emergency.dialable(U) == [emergency.UNIVERSAL]


def test_there_is_always_something_to_dial_even_knowing_nothing():
    for numbers in (emergency.dialable(U), emergency.dialable()):
        assert numbers
        assert emergency.UNIVERSAL in numbers or numbers == [emergency.UNIVERSAL]


def test_what_is_said_and_what_is_dialled_agree():
    """One of them is prose and the other is for a button, and they are built
    from the same row — a screen that offered a number he did not say out loud
    would make him sound as though he were reading off something else."""
    emergency.remember(U, "Израиль")
    for number in emergency.dialable(U):
        assert number in emergency.numbers(U)
