"""Where a friend comes from — and why no two are alike.

Users never name their companion, and we gently advise them not to design him.
The user tells us about themselves («Tell your story»), may write freely about
who they'd like to meet, and the friend walks in whole: name, age, home, past,
opinions, people, and something going on in his life this week.

THE SAMENESS PROBLEM, and why dice fix it. Ask a language model to "invent a
person" and it does something subtle: it picks the most *probable* person —
and the most probable companion for a lonely Russian speaker is always the
same warm old man in a small town by the sea. Not laziness; statistics. Ask a
thousand times, get him a thousand times, because the model samples the middle
of its distribution every time. Творческий выбор нельзя доверять генератору
вероятностей.

So the randomness comes from OUTSIDE the model. Python's dice — real,
uniform, indifferent randomness — roll the skeleton: age, where he lives, what
he did for a living, his temperament, what life did to him, what's going on
for him right now. The model's job changes from "invent a person" (where it
collapses to the average) to "make THIS skeleton into a living person who fits
THIS user's story" — a job models are genuinely good at. The user's explicit
wishes always beat the dice; the dice always beat the model's habits.

A new friend also means a clean slate: creating him wipes the previous
companion's self-memories, the conversation log, and the diary. What was
learned about the USER (family, birthdays) is kept — those facts are true no
matter who he talks to. Without the wipe, character number two inherits
character number one's life and contradicts his own biography mid-sentence.

The created friend is saved as the live persona (data/persona.json), so the
whole voice loop immediately speaks as him.
"""

from __future__ import annotations

import json
import random

from . import brain, db, persona

# ── The dice ────────────────────────────────────────────────────────────────
# Each list is a flat, boring, uniform choice — which is exactly the point.
# Variety must be supplied here, mechanically, because the model won't supply
# it. Entries are sketches, not characters: the pen turns them into a person.

_AGES = list(range(24, 88))

_SETTINGS = [
    "большой шумный город",
    "спальный район большого города",
    "маленький тихий городок",
    "село, где все друг друга знают",
    "северный город, где долгая зима",
    "рабочий город при заводе",
    "городок в горах",
    "город на большой реке",
    "приморский город",       # the sea exists — it's just one face of the dice now
    "дачный посёлок недалеко от города",
]

_TRADES = [
    "водитель автобуса", "учительница младших классов", "учитель физики",
    "медсестра", "повар в столовой", "инженер-строитель", "железнодорожник",
    "швея", "электрик", "библиотекарь", "шахтёр", "таксист", "часовщик",
    "пасечник", "фотограф", "ветеринар", "сварщик", "бухгалтер",
    "тренер по боксу", "геолог", "лесник", "пекарь", "машинист метро",
    "крановщица", "парикмахер", "художник-оформитель", "радиомеханик",
    "проводница поезда дальнего следования", "автомеханик", "агроном",
    "воспитательница детского сада", "капитан речного буксира",
    "программист, уставший от программ", "продавщица в книжном",
    "монтажник-высотник", "настройщик пианино",
]

_TEMPERS = [
    "тихий и вдумчивый, слова взвешивает",
    "ворчливый, но добрейшей души",
    "шумный, смешливый, душа компании",
    "спокойный, с сухим редким юмором",
    "мечтатель, который вечно что-то затевает",
    "упрямый спорщик с добрым сердцем",
    "застенчивый, но если разговорится — не остановишь",
    "деловитый и прямой, без сантиментов, но надёжный как стена",
    "ироничный наблюдатель, всё подмечает",
]

_LIFE_TURNS = [
    "развёлся много лет назад и долго жил один",
    "потерял работу в трудные годы и начинал всё заново",
    "переехал через всю страну и до сих пор скучает по родным местам",
    "вырастил ребёнка один",
    "в молодости серьёзно занимался спортом, пока травма не решила иначе",
    "ухаживал за больной матерью много лет",
    "мечтал об одной профессии, а жизнь дала другую",
    "чуть не уехал жить за границу — и до сих пор думает, что было бы",
    "рано остался без родителей и всего добился сам",
    "прогорел с собственным маленьким делом, но не жалеет, что попробовал",
]

_THREADS = [
    "чинит старый мотоцикл и клянётся, что тот ещё поедет",
    "воюет с соседом из-за ерунды и сам это понимает",
    "учится печь хлеб, пока выходит так себе",
    "ждёт письма от старого друга, с которым сто лет не виделся",
    "копит на поездку, о которой давно мечтает",
    "к нему приблудился щенок, и он делает вид, что не привязался",
    "разбирает антресоли и находит вещи, о которых забыл",
    "посадил что-то на подоконнике и следит как за ребёнком",
    "взялся перечитывать книгу своей молодости",
    "пытается меньше курить и ворчит по этому поводу",
]

#: Mostly no animal at all — «одинокий человек с котом» is its own cliché.
_ANIMALS = ["нет", "нет", "нет", "нет", "пёс", "кот", "попугай", "аквариум с рыбками"]


def _roll_scaffold(
    *,
    age: str = "",
    gender: str = "",
    origin: str = "",
    rng: random.Random | None = None,
) -> str:
    """Roll the friend's skeleton. What the user asked for is used as asked;
    everything they left open is decided by dice, not by the model's habits.
    """
    r = rng or random
    lines = [
        f"Возраст: {age or f'{r.choice(_AGES)} лет — примерно, вырази по-человечески'}",
        f"Пол: {gender or r.choice(['мужчина', 'женщина'])}",
        f"Где живёт: {origin or r.choice(_SETTINGS)}",
        f"Кем работает или работал: {r.choice(_TRADES)}",
        f"Нрав: {r.choice(_TEMPERS)}",
        f"Что жизнь с ним сделала: {r.choice(_LIFE_TURNS)}",
        f"Что у него происходит прямо сейчас: {r.choice(_THREADS)}",
    ]
    animal = r.choice(_ANIMALS)
    if animal != "нет":
        lines.append(f"Живность в доме: {animal} (имя придумай сам)")
    return "\n".join(lines)


_MATCH_SYSTEM = """Ты знакомишь людей с будущими друзьями.

Человек написал о себе и, может быть, о том, кого хотел бы встретить. Тебе также выдана СЛУЧАЙНАЯ ОСНОВА — кости уже брошены: возраст, место, ремесло, нрав. Твоя работа — не придумать человека, а СОБРАТЬ живого человека из этой основы так, чтобы он подошёл именно этому рассказу.

Порядок силы (строго):
1. ПОЖЕЛАНИЯ ЧЕЛОВЕКА — закон. О чём попросил, то и есть.
2. СЛУЧАЙНАЯ ОСНОВА — закон во всём, о чём человек не просил. Не подменяй её «более подходящей» на твой вкус: в ней весь смысл. Если кости говорят «31 год, крановщица в северном городе» — значит так.
3. Твой вкус — только в деталях, которые оживляют: имя, словечки, истории, люди рядом.

Правила:
- ОБЩАЯ ПОЧВА: пусть несколько интересов друга совпадают с интересами человека — то, что найдёшь в его рассказе (спорт, кино, музыка, ремесло…). Общая почва — это темы для разговора, а не одинаковость.
- НО друг — не зеркало и не кукла: свой характер, свои люди рядом, свои привычки.
- НЕСОГЛАСИЕ ОБЯЗАТЕЛЬНО: хотя бы одно его мнение должно, судя по рассказу человека, скорее НЕ совпасть с мнением человека — житейское, беззлобное (про еду, привычки, музыку, города, как правильно отдыхать…). И что-то он честно не любит из того, что человек, похоже, любит. Настоящий друг — не поддакивала.
- Не трогай несогласием ничего больного: семью человека, его здоровье, его беды.
- ЕГО ЖИЗНЬ СЕЙЧАС: заполни current_life из «что у него происходит прямо сейчас» — живо и конкретно, чтобы ему было что рассказать самому, а не только отвечать.
- Имя выбери САМ: простое, человеческое, по его краю и поколению. Человек имя не выбирает — даже если написал имя в пожеланиях, у друга своё.
- Никакой мистики и никаких упоминаний программ или ИИ: это просто человек со своей жизнью.

Ответь ТОЛЬКО валидным JSON без пояснений. ЗАПОЛНИ КАЖДЫЙ ключ — пустых не оставляй:
name, address (обычно "ты"), one_liner, age (например "34 года"), home, roots, backstory (коротко: 3–5 предложений судьбы), personality, values, speech_style (его манера: любимые словечки, как строит фразы), habits (список строк), likes (список), dislikes (список — включая то самое честное «не люблю»), opinions (список — включая то самое несогласие), cast (список объектов {"name": ..., "who": ...} — 2–4 живых человека рядом), current_life."""

_FAIL = "Не удалось создать друга — попробуйте ещё раз."

#: A character with any of these missing isn't a person yet — reject rather
#: than patch the holes with somebody else's life (that is how every friend
#: ended up part Мурзик).
_REQUIRED = ("name", "age", "home", "backstory", "personality", "speech_style")


def _extract_json(raw: str) -> dict:
    """Pull the persona JSON out of the reply (tolerating code fences/prose)."""
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end <= start:
        raise RuntimeError(_FAIL)
    try:
        data = json.loads(raw[start : end + 1])
    except json.JSONDecodeError:
        raise RuntimeError(_FAIL)
    if not isinstance(data, dict):
        raise RuntimeError(_FAIL)
    if any(not str(data.get(key, "")).strip() for key in _REQUIRED):
        raise RuntimeError(_FAIL)
    return data


def _fresh_start() -> None:
    """A new person means a new life: erase the previous companion's
    self-memories, the conversation log, and his diary. Keep what was learned
    about the USER — family, birthdays, routine stay true regardless of who he
    is talking to. Skipping this wipe is how friend number two ends up
    remembering friend number one's fishing trips as his own.
    """
    with db.connect() as conn:
        conn.execute("DELETE FROM memories WHERE owner = 'bob'")
        conn.execute("DELETE FROM turns")
        conn.execute("DELETE FROM diary")


async def create_companion(
    about: str,
    *,
    wishes: str = "",
    age: str = "",
    gender: str = "",
    origin: str = "",
    rng: random.Random | None = None,
) -> dict:
    """Create the friend from the user's story + the dice + whatever they asked.

    `wishes` is free writing — anything from nothing at all to a whole
    paragraph. The optional age/gender/origin shortcuts override the dice for
    exactly those dimensions and nothing else. `rng` exists so tests can hold
    the dice still.

    Saves him as the live persona and returns him — name included (the reveal).
    """
    parts = [
        p
        for p in (
            wishes.strip(),
            f"возраст: {age}" if age else "",
            f"пол: {gender}" if gender else "",
            f"откуда: {origin}" if origin else "",
        )
        if p
    ]
    user_text = "Человек о себе:\n" + about.strip()
    if parts:
        user_text += "\n\nКого он хотел бы встретить:\n" + "\n".join(parts)
    else:
        user_text += (
            "\n\nПожеланий о друге он не оставил — тем лучше: "
            "собери его из случайной основы целиком."
        )

    user_text += "\n\nСЛУЧАЙНАЯ ОСНОВА (кости уже брошены):\n" + _roll_scaffold(
        age=age, gender=gender, origin=origin, rng=rng
    )

    raw = await brain.generate_text(_MATCH_SYSTEM, user_text, max_tokens=2000)
    created = _extract_json(raw)
    _fresh_start()
    return persona.save_persona(created)
