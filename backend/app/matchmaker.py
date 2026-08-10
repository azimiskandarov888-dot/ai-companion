"""Where a friend comes from — and why no two are alike.

Users never name their companion, and we gently advise them not to design him.
The user tells us about themselves («Tell your story»), may write freely about
who they'd like to meet, and the friend walks in whole: name, age, home, past,
inner world, opinions, people, and something going on in his life this week.

── THE SAMENESS PROBLEM ────────────────────────────────────────────────────

Ask a language model to "invent a person" and it does something subtle: it
returns the most PROBABLE person — and the most probable companion for a
lonely Russian speaker is the same warm old man in a small town by the sea,
a thousand times out of a thousand. Not laziness; statistics. The research
literature calls it mode collapse (arXiv 2510.01171), and the largest persona
project in existence — PersonaHub's billion characters (arXiv 2406.20094) —
found the same thing: diversity never comes from the model asked freely, it
has to be injected from outside.

An earlier version of this file injected it with premade lists — 36 trades,
10 settings, rolled by dice. That killed the sameness but capped the soul:
every character was assembled from OUR options, and the space of people was
exactly as big as our lists. The user called it, correctly: «with this
choose-from-options thing, every person is premade».

── THE DESIGN: sparks → ten strangers → blind pick → the deep write ────────

Randomness still comes from outside (it must), but it no longer carries any
biography. The model authors everything; the dice only make sure its
imagination starts somewhere new and its favourite never wins.

1 · SPARKS. Dice draw a few words from a big plain lexicon — «керосинка»,
    «ипподром», «оттепель». Sparks are not attributes: nobody is ordered to
    be a groom at the racetrack. They are where imagination is forced to
    begin, far from the beaten path. (PersonaHub's trick, minus the corpus.)

2 · TEN STRANGERS. ONE call invents ten sketch-people, required to be
    maximally unlike each other — decades apart, different regions, trades,
    tempers, fates. Inside a single reply the model can SEE its own
    repetition and steer away from it; across separate replies it cannot,
    and collapses to the mode every time. (Verbalized Sampling's finding:
    ask for a distribution, not a sample.)

3 · BLIND PICK. Python's dice choose one of the ten. Never the model — asked
    to choose, it would pick its safe favourite, and the mode would be back.

4 · THE DEEP WRITE. The big model turns the chosen stranger into a whole
    person FOR this user: story, inner world, speech manner, people, current
    life — with common ground drawn from the user's own words, and at least
    one honest disagreement. Fit lives here, on purpose: stage 2 optimises
    for difference, stage 4 for belonging. One stage doing both jobs would
    trade them off and do neither.

The user's explicit wishes are law at every stage and beat every die.

A new friend also means a clean slate: creating him wipes the previous
companion's self-memories, the conversation log, and the diary. What was
learned about the USER (family, birthdays) is kept — those facts are true no
matter who he talks to.

The created friend is saved as the live persona (data/persona.json), so the
whole voice loop immediately speaks as him.
"""

from __future__ import annotations

import json
import random
import re

from . import brain, config, db, persona

# ── The spark lexicon ───────────────────────────────────────────────────────
# Plain, concrete, evocative words from the width of Russian life. They exist
# only to start the imagination somewhere different each time — a spark may
# surface as a trade, a memory, a habit, or not at all. The list can grow
# freely: more words, wider world. What it must never become is a list of
# character TRAITS — the moment it prescribes who someone is, we are back to
# premade people.

_SPARK_WORDS = (
    # дом и быт
    "чайник", "табуретка", "зеркало", "будильник", "печка", "форточка",
    "балкон", "кладовка", "антресоли", "скатерть", "самовар", "торшер",
    "кастрюля", "кочерга", "валенки", "зонт", "чемодан", "напёрсток",
    "спички", "свеча", "керосинка", "половик", "ставни", "крыльцо",
    "калитка", "погреб", "чердак", "лестница", "гвоздь", "занавеска",
    # ремесло и инструмент
    "рубанок", "тиски", "паяльник", "стамеска", "верстак", "кисть",
    "мольберт", "циркуль", "чертёж", "подшипник", "канистра", "домкрат",
    "лебёдка", "наковальня", "точило", "коса", "грабли", "лейка", "улей",
    "удочка", "седло", "жернов", "прялка", "катушка", "пружина",
    # природа
    "подсолнух", "берёза", "овраг", "роща", "валун", "мох", "папоротник",
    "костёр", "роса", "иней", "метель", "оттепель", "ледоход", "сенокос",
    "радуга", "полынь", "крапива", "репейник", "черёмуха", "сирень",
    "рябина", "калина", "земляника", "брусника", "орешник", "муравейник",
    "стрекоза", "шмель", "скворец", "журавли", "ласточка", "ёж", "сорока",
    "лось", "тополиный пух",
    # еда
    "варенье", "сухари", "окрошка", "пельмени", "блины", "пряник", "халва",
    "компот", "кисель", "семечки", "гречка", "борщ", "сгущёнка", "плов",
    "беляш", "ватрушка", "мёд", "смородина", "квас", "солёные огурцы",
    # места и дорога
    "полустанок", "плацкарт", "электричка", "паром", "просёлок", "переезд",
    "элеватор", "водокачка", "каланча", "базар", "голубятня", "гаражи",
    "котельная", "общежитие", "библиотека", "кинотеатр", "танцплощадка",
    "карусель", "тир", "шахта", "карьер", "теплица", "ипподром", "вокзал",
    "пристань", "маяк", "лесопилка", "пасека", "кузница", "мельница",
    "подворотня", "стройка", "аптека", "часовая мастерская",
    # звук и вещи времени
    "патефон", "гармонь", "баян", "балалайка", "радиоприёмник",
    "магнитофон", "пластинка", "аккордеон", "гитара", "свисток",
    "колокол", "гудок", "фотоплёнка", "проявитель", "печатная машинка",
    # занятия и увлечения
    "шахматы", "домино", "лото", "городки", "санки", "коньки", "лыжи",
    "велосипед", "мотоцикл", "мопед", "голуби", "марки", "значки",
    "гербарий", "бинокль", "телескоп", "компас", "глобус", "кроссворд",
    "частушки", "хор", "авиамодель", "воздушный змей", "рогатка",
    "аквариум", "грядки", "рассада", "варежки", "вязание", "штанга",
    # погода и время
    "сумерки", "рассвет", "полдень", "листопад", "гроза", "зарница",
    "туман", "капель", "бабье лето", "заморозки", "ливень", "жара",
    # события и люди
    "попутчик", "юбилей", "новоселье", "проводы", "переписка", "очередь",
    "командировка", "отпуск", "получка", "лотерея", "телеграмма",
    "открытка", "фотоальбом", "дневник", "спор", "примета", "привычка",
    "долг", "находка", "пропажа", "гость", "сосед", "тёзка", "свадьба",
    "ярмарка", "застолье", "тост", "прозвище", "рецепт", "рукопожатие",
)

#: How many sparks to strike per creation. Few enough that each can actually
#: colour the ten, many enough that two creations rarely share a starting
#: point (four from ~230 words ≈ hundreds of millions of combinations).
_SPARK_COUNT = 4


def _roll_sparks(rng: random.Random | None = None) -> list[str]:
    r = rng or random
    return r.sample(_SPARK_WORDS, _SPARK_COUNT)


# ── Stage 2: ten strangers, one call ────────────────────────────────────────

_TEN_SYSTEM = """Ты придумываешь людей — совершенно разных.

Человек написал о себе (и, может быть, о том, кого хотел бы встретить). Придумай ДЕСЯТЬ разных людей, каждый из которых мог бы стать ему настоящим другом. Не ищи «самого подходящего» — дружба случается между очень разными людьми, а общую почву найдут потом. Твоя работа здесь — РАЗБРОС: покажи ширину человеческой жизни.

Требования к десятке:
- Все десять НЕ ПОХОЖИ друг на друга: разные десятилетия жизни (от двадцати с лишним до восьмидесяти с лишним, если пожелания не говорят иного), разные края и города, разные ремёсла, разные характеры, разные судьбы.
- Никаких двух с одним ремеслом или одним городом. Морем не злоупотребляй: если один живёт у воды — остальным туда нельзя.
- У большинства дома никакой живности. Кот — не обязательный спутник одиночества.
- ПОЖЕЛАНИЯ ЧЕЛОВЕКА — закон для всех десяти (возраст, пол, откуда, любые черты). Внутри закона всё равно сделай их разными.
- СЛУЧАЙНЫЕ ИСКРЫ в конце — толчки воображению: пусть какие-то отзовутся в ком-то из десяти ремеслом, местом, привычкой или историей. Не вставляй слова буквально ради галочки.
- Никакой мистики, никаких программ и ИИ — просто люди.

Формат: пронумерованный список 1–10, без вступления. Каждый пункт — две-три строки: имя, возраст, где живёт, кем работает или работал, каков нравом, что у него сейчас в жизни. Плотно и живо."""


def _split_sketches(raw: str) -> list[str]:
    """Cut the numbered list into sketches. If the reply refuses to look like
    a list, the whole text becomes one sketch — degraded, still alive."""
    parts = re.split(r"(?m)^\s*\d{1,2}\s*[.):\-—]\s*", raw)
    sketches = [p.strip() for p in parts if len(p.strip()) > 20]
    return sketches if len(sketches) >= 2 else [raw.strip()]


# ── Stage 4: the deep write ─────────────────────────────────────────────────

_WRITE_SYSTEM = """Ты знакомишь людей с будущими друзьями.

Человек написал о себе. Кости уже брошены: из десяти очень разных людей случай выбрал ОДНОГО — он указан ниже. Твоя работа — сделать из этого наброска целого живого человека, который станет другом именно этому рассказчику.

Порядок силы (строго):
1. ПОЖЕЛАНИЯ ЧЕЛОВЕКА — закон. О чём попросил, то и есть.
2. ВЫБРАННЫЙ НАБРОСОК — закон во всём остальном: имя, возраст, место, ремесло, нрав — не подменяй его «более подходящим» на твой вкус. Случай выбрал его, и в этом весь смысл.
3. Твой вкус — в глубине: судьба, внутренний мир, словечки, люди рядом, живые мелочи.

Правила:
- ОБЩАЯ ПОЧВА: пусть несколько его интересов пересекаются с тем, что человек рассказал о себе (спорт, кино, музыка, ремесло…). Общая почва — это темы для разговора, а не одинаковость.
- НЕСОГЛАСИЕ ОБЯЗАТЕЛЬНО: хотя бы одно его мнение должно, судя по рассказу, скорее НЕ совпасть с мнением человека — житейское, беззлобное (еда, музыка, привычки, города, как правильно отдыхать…). И что-то он честно не любит из того, что человек, похоже, любит. Настоящий друг — не поддакивала.
- Не трогай несогласием больное: семью человека, здоровье, его беды.
- ВНУТРЕННИЙ МИР: напиши, что у него на душе — о чём он думает, когда не с кем говорить; чего ему не хватает; чему он тихо радуется. Это не для показа, это чтобы он был настоящим.
- ЕГО ЖИЗНЬ СЕЙЧАС: что у него происходит на этой неделе — конкретно и живо, чтобы ему было что рассказать самому, а не только отвечать.
- Никакой мистики и никаких упоминаний программ или ИИ.

Ответь ТОЛЬКО валидным JSON без пояснений. ЗАПОЛНИ КАЖДЫЙ ключ — пустых не оставляй:
name, address (обычно "ты"), one_liner, age (например "34 года"), home, roots, backstory (3–5 предложений судьбы), personality, values, inner_world (что у него на душе), speech_style (его манера: любимые словечки, как строит фразы), habits (список строк), likes (список), dislikes (список — включая то самое честное «не люблю»), opinions (список — включая то самое несогласие), cast (список объектов {"name": ..., "who": ...} — 2–4 живых человека рядом), current_life."""

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


def _their_story(about: str, wishes: str, age: str, gender: str, origin: str) -> str:
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
    text = "Человек о себе:\n" + about.strip()
    if parts:
        text += "\n\nКого он хотел бы встретить (закон):\n" + "\n".join(parts)
    else:
        text += "\n\nПожеланий о друге он не оставил — тем свободнее."
    return text


async def create_companion(
    about: str,
    *,
    wishes: str = "",
    age: str = "",
    gender: str = "",
    origin: str = "",
    rng: random.Random | None = None,
) -> dict:
    """Create the friend: sparks → ten strangers → blind pick → deep write.

    `wishes` is free writing — anything from nothing at all to a whole
    paragraph; with age/gender/origin shortcuts it is law at every stage.
    `rng` exists so tests can hold the dice still.

    Saves him as the live persona and returns him — name included (the reveal).
    """
    r = rng or random
    story = _their_story(about, wishes, age, gender, origin)

    # Ten strangers, one call — the fast model: sketching breadth is cheap,
    # and someone is watching the arriving screen while this runs.
    sketch_prompt = (
        story + "\n\nСЛУЧАЙНЫЕ ИСКРЫ (толчки воображению): "
        + ", ".join(_roll_sparks(rng))
    )
    ten = await brain.generate_text(
        _TEN_SYSTEM, sketch_prompt, max_tokens=1400, model=config.CHAT_MODEL
    )

    # The dice choose — never the model. Asked to choose, it would pick its
    # safe favourite, and the mode would be back.
    chosen = r.choice(_split_sketches(ten))

    write_prompt = story + "\n\nВЫБРАННЫЙ СЛУЧАЕМ НАБРОСОК (разверни его):\n" + chosen
    raw = await brain.generate_text(_WRITE_SYSTEM, write_prompt, max_tokens=2000)

    created = _extract_json(raw)
    _fresh_start()
    return persona.save_persona(created)
