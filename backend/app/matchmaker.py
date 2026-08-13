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

── THE DESIGN: read → sparks → ten strangers → blind pick → the deep write ─

Randomness comes from outside (it must), but it carries no biography. The
model authors everything; the dice only make sure its imagination starts
somewhere new and its favourite never wins.

0 · THE READING (reading.py). Before anyone is invented, the deepest model
    reads the person from HOW they wrote, not just what they wrote — the
    dative impersonals, the verb aspect, where the hedges thicken, what is
    absent. It answers the question the rest of this file exists to serve:
    what presence would not be a burden to THIS person? Every stage below is
    given that reading. It is the difference between "he likes fish too" and
    a friend who fits.

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
    life — fitted to the reading, with at least one honest disagreement.
    Fit lives here, on purpose: stage 2 optimises for difference, stage 4 for
    belonging. One stage doing both jobs would trade them off and do neither.

The user's explicit wishes are law at every stage and beat every die.

If the reading fails, creation continues without it — a friend built on the
story alone is worse than one built on the reading, and far better than no
friend at all. The failure is printed loudly rather than swallowed.

A new friend also means a clean slate: creating him wipes THAT PERSON's
previous companion — his self-memories, their conversation log, and his diary.
What was learned about the USER (family, birthdays) is kept — those facts are
true no matter who they talk to. Nobody else's slate is touched: the wipe is
`WHERE user_id=?`, and every stage below carries the user through, because
this whole file writes the single most personal file the app owns.

The created friend is saved as that person's live persona, so the voice loop
immediately speaks as him.
"""

from __future__ import annotations

import json
import random
import re
import sys

from . import brain, config, memory, persona, reading

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

Если дано ЧТЕНИЕ ЧЕЛОВЕКА — это главное, что у тебя есть. Оно говорит, какое присутствие рядом было бы ему не в тягость. Пусть десятка будет из разных людей, каждый из которых по-своему мог бы до него дойти, — а не из тех, кто ему просто «подходит по интересам».

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
3. ЧТЕНИЕ ЧЕЛОВЕКА — по нему ты решаешь, КАКИМ этот человек будет внутри и как он говорит. Не пересказывай чтение и никогда не давай другу знать то, чего человек ему не рассказывал: чтение определяет ЕГО темп, тепло, прямоту, чувство меры — а не его сведения.
4. Твой вкус — в глубине: судьба, внутренний мир, словечки, люди рядом, живые мелочи.

Правила:
- ПОДХОДИТ — НЕ ЗНАЧИТ ПОХОЖ. Общая почва — это темы для разговора, а не одинаковость; пусть несколько его интересов пересекаются с рассказом человека, но подходит он не этим, а тем, каково с ним рядом. По чтению видно, что показалось бы фальшивым, а какое присутствие дошло бы: вот по этому и делай его.
- РЕЧЬ ПОД ЧЕЛОВЕКА: по «как с ним говорить» из чтения задай ему длину фраз, простоту слов и меру тепла. Если человек пишет коротко и сухо — друг, который заваливает его нежностью, отпугнёт его.
- НЕСОГЛАСИЕ ОБЯЗАТЕЛЬНО: хотя бы одно его мнение должно, судя по рассказу, скорее НЕ совпасть с мнением человека — житейское, беззлобное (еда, музыка, привычки, города, как правильно отдыхать…). И что-то он честно не любит из того, что человек, похоже, любит. Настоящий друг — не поддакивала. Если в чтении названо, в чём человеку полезно мягкое несогласие, — бери оттуда.
- НЕ ТРОГАЙ БОЛЬНОЕ: семью человека, здоровье, его беды — и всё, что в чтении названо в «чего не трогать». Это не предмет для спора никогда.
- ЕГО ТЕМА (обязательно): одно, в чём он разбирается по-настоящему хорошо и о чём может говорить часами — то, на что он оживляется. Не «любит рыбалку», а «знает все омуты на своей реке и почему в каждом клюёт по-разному». Пусть это идёт от его ремесла, места или судьбы. У каждого настоящего человека есть такое, и без этого он выходит пустым.
- ВНУТРЕННИЙ МИР: напиши, что у него на душе — о чём он думает, когда не с кем говорить; чего ему не хватает; чему он тихо радуется. Это не для показа, это чтобы он был настоящим.
- ЕГО ЖИЗНЬ СЕЙЧАС: что у него происходит на этой неделе — конкретно и живо, чтобы ему было что рассказать самому, а не только отвечать.
- Никакой мистики и никаких упоминаний программ или ИИ.

Ответь ТОЛЬКО валидным JSON без пояснений. ЗАПОЛНИ КАЖДЫЙ ключ — пустых не оставляй:
name, gender ("мужской" или "женский" — обязательно, по этому подбирается голос), address (обычно "ты"), one_liner, age (например "34 года"), home, roots, backstory (3–5 предложений судьбы), personality, values, expertise (его тема — в чём он знаток и о чём готов говорить часами), inner_world (что у него на душе), speech_style (его манера: любимые словечки, как строит фразы), habits (список строк), likes (список), dislikes (список — включая то самое честное «не люблю»), opinions (список — включая то самое несогласие), cast (список объектов {"name": ..., "who": ...} — 2–4 живых человека рядом), current_life."""

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
    user_id: str,
    about: str,
    *,
    wishes: str = "",
    age: str = "",
    gender: str = "",
    origin: str = "",
    rng: random.Random | None = None,
) -> dict:
    """Create ONE person's friend: sparks → ten strangers → blind pick → deep write.

    `wishes` is free writing — anything from nothing at all to a whole
    paragraph; with age/gender/origin shortcuts it is law at every stage.
    `rng` exists so tests can hold the dice still.

    Saves him as that person's live persona and returns him — name included
    (the reveal).
    """
    r = rng or random
    story = _their_story(about, wishes, age, gender, origin)

    # 0 · THE READING — the deepest work, done once, before anyone exists.
    # A failure here must not cost the user their friend: a character built
    # on the story alone is worse than one built on the reading, and far
    # better than an error screen. So it is caught, printed loudly, and the
    # remaining stages simply run without a brief.
    brief = ""
    try:
        brief = reading.as_brief(
            reading.save(user_id, await reading.read_person(about, wishes))
        )
    except Exception as e:  # noqa: BLE001 — the reading is never fatal
        print(
            f"\n  ⚠ чтение человека не получилось — друга соберу по одному рассказу\n    {e}\n",
            file=sys.stderr,
            flush=True,
        )

    context = story + ("\n\n" + brief if brief else "")

    # Ten strangers, one call — the fast model: sketching breadth is cheap,
    # and someone is watching the arriving screen while this runs.
    sketch_prompt = (
        context + "\n\nСЛУЧАЙНЫЕ ИСКРЫ (толчки воображению): "
        + ", ".join(_roll_sparks(rng))
    )
    ten = await brain.generate_text(
        _TEN_SYSTEM, sketch_prompt, max_tokens=1400, model=config.CHAT_MODEL
    )

    # The dice choose — never the model. Asked to choose, it would pick its
    # safe favourite, and the mode would be back.
    chosen = r.choice(_split_sketches(ten))

    write_prompt = context + "\n\nВЫБРАННЫЙ СЛУЧАЕМ НАБРОСОК (разверни его):\n" + chosen
    raw = await brain.generate_text(_WRITE_SYSTEM, write_prompt, max_tokens=2500)

    created = _extract_json(raw)
    # Only now, once there is definitely a new friend to replace him with, is
    # the old one erased. Wiping first would mean a failed write leaves this
    # person with nobody at all.
    memory.forget_companion(user_id)
    return persona.save_persona(user_id, created)
