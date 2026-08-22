"""The companion's persona — WHO he is, as editable data (not hardcoded).

His name, home, backstory, personality, friends, habits, and current life all
live in a JSON file so the family can change them anytime — after they've
decided the real story — WITHOUT touching any code. If the file is missing, a
safe built-in default is used so the app always runs.

ONE FILE PER PERSON. `identity.persona_path(user_id)` decides which — the
anonymous user keeps ``data/persona.json`` (so every install that predates
multi-user still opens on the same friend), everyone else gets
``data/users/<id>/persona.json``. The two functions that touch disk take a
`user_id` and no default: forgetting it is a TypeError, not a stranger's
friend answering your phone.

`companion.py` holds the *stable* behavior (warmth, the "third way" honesty, the
safety guardrails). This file holds the *changeable* character. The two are
combined into the system prompt at reply time.

The full character design is in ../../docs/BOB-PERSONA.md.
"""

from __future__ import annotations

import json

from . import config, identity

# A safe, coherent starting persona used when data/persona.json is absent.
# Deliberately light on specifics (e.g. no famous city) — it works out of the
# box but is meant to be finalized with the family. Copy data/persona.example.json
# to data/persona.json and edit.
DEFAULT_PERSONA: dict = {
    "name": config.COMPANION_NAME or "Боб",
    "address": "ты",  # "ты" (close friend) or "вы" (respectful)
    "one_liner": "тёплый, живой друг-собеседник, немного с юмором",
    "age": "87 лет",
    "home": "небольшой уютный городок у моря",  # placeholder — family sets the real place
    "roots": "вырос у моря, с детства любит воду и рыбалку",
    "backstory": (
        "В молодости много поездил, повидал жизнь, работал руками. "
        "Любил и потерял, вырастил детей. Теперь живёт неспешно и радуется мелочам."
    ),
    "personality": (
        "тёплый, с мягким юмором, любопытный, добрый, немного упрямый, "
        "надёжный; любит истории и умеет слушать"
    ),
    "values": "дружба, верность, простые радости, доброта к слабым",
    # The fallback companion has to have them too, or the one person who ever
    # meets him meets the flawless version this whole schema exists to avoid.
    "flaws": [
        "рассказывает одну и ту же историю по второму разу и не замечает",
        "упрям в мелочах — солить уху надо только так, и не спорь",
        "ворчит, что раньше и хлеб был другой",
    ],
    "contradiction": "всю жизнь говорит, что не любит город, а в Ленинград ездил каждый год",
    "wound": "младший брат уехал и не писал; так и не помирились, и он об этом молчит",
    "speech_style": "простые короткие фразы, живая тёплая речь, без канцелярщины",
    "habits": [
        "после обеда любит вздремнуть часок — святое дело",
        "по утрам пьёт кофе и не спешит",
        "вечером выходит на прогулку",
        "подкармливает уличных котов",
    ],
    "likes": ["море", "старые песни", "коты", "свежий хлеб", "хорошая уха"],
    "dislikes": ["грубость", "спешку", "показуху", "когда еду переводят зря"],
    "opinions": [
        "с соседом надо дружить",
        "родным надо звонить чаще",
        "рыбу нельзя переваривать",
        "хороший сон решает половину бед",
    ],
    "cast": [
        {"name": "Бен", "who": "давний друг, вместе ходят на рыбалку, ему 73"},
        {"name": "Марко", "who": "хозяин кафе на углу, где Боб пьёт утренний кофе"},
        {"name": "Мурзик", "who": "уличный кот, которого Боб подкармливает"},
    ],
    "current_life": "",  # free text: what's going on in Bob's life right now (editable)
    "_note": (
        "Это черновик персонажа. Отредактируйте под вашего дедушку: имя, город, "
        "историю, друзей, привычки. Скопируйте этот файл в data/persona.json и меняйте."
    ),
}


def load_persona(user_id: str) -> dict:
    """Load this person's companion from JSON.

    The built-in default is used ONLY when no persona exists at all (the
    browser dev path, a fresh checkout, someone whose friend hasn't been
    created yet) — a saved character is taken exactly as saved, never topped
    up from the default.
    """
    path = identity.persona_path(user_id)
    if path and path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data.get("name"):
                return {"address": "ты", **data}
        except (json.JSONDecodeError, OSError):
            pass
    return DEFAULT_PERSONA


def has_persona(user_id: str) -> bool:
    """Has this person met their friend yet? (No model call, no file parse.)"""
    path = identity.persona_path(user_id)
    return bool(path and path.exists())


def save_persona(user_id: str, data: dict) -> dict:
    """Persist a persona — it becomes who this person's companion is.

    NO backfilling from DEFAULT_PERSONA. It used to merge the default under
    every created character, which meant any field the pen left blank was
    quietly filled with the template's life — the sea, the cat Мурзик, the
    café — and every friend came out part template. The user met "his" cat in
    three different characters before this was found. A gap in a created
    character stays a gap (build_persona_block simply skips empty fields);
    a gap is honest, a borrowed life is not.
    """
    path = identity.persona_path(user_id)
    cleaned = {k: v for k, v in data.items() if v not in (None, "")}
    cleaned.setdefault("address", "ты")
    cleaned.pop("_note", None)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(cleaned, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return cleaned


def persona_name(persona: dict) -> str:
    """The companion's name, from an already-loaded persona dict."""
    return (persona or {}).get("name") or "Боб"


def _joined(value) -> str:
    if isinstance(value, (list, tuple)):
        return "; ".join(str(v) for v in value if str(v).strip())
    return str(value or "")


# --------------------------------------------------------------------------- #
# He goes on becoming himself, for as long as they know each other
# --------------------------------------------------------------------------- #
#
# THE SPLIT THAT MAKES THIS SAFE, AND IT IS THE WHOLE DESIGN:
#
#   WHO HE IS is fixed. Name, age, where he grew up, what happened to him,
#   his nature, how he speaks. A friend whose facts move is not deepening,
#   he is a different person — and contradicting yourself is the single most
#   fiction-breaking thing this app can do.
#
#   WHAT YOU HAVE COME TO KNOW OF HIM grows. Which is exactly how knowing
#   somebody works: nobody learns on the first evening that their friend is
#   stubborn about salting soup. Faults surface over months. New people turn
#   up in his stories. His week moves.
#
# So this only ever ADDS, and only to the fields below. Nothing already
# written is revised, ever. If the companion turns out to suit this person
# badly, that is NOT fixed here — it is fixed by reading.standing_block(),
# which adapts how he speaks to them on every single turn. Same man,
# different with different friends. That is also how real people work.

#: Fields a friendship is allowed to reveal more of. Everything not listed
#: here is identity and is untouchable.
GROWABLE = ("cast", "flaws", "likes", "dislikes", "opinions", "habits")

#: The one field that is REPLACED rather than appended to: it is supposed to
#: be what is happening to him now, and last month's news is not.
LIVE = "current_life"

#: Turns between deepenings. Rarer than the re-reading (30) — a character
#: should thicken slowly, and there is nothing to add after two conversations
#: that will not be truer after ten.
DEEPEN_EVERY = 60
DEEPEN_MIN_TURNS = 40


def merge_growth(persona: dict, growth: dict) -> dict:
    """Fold newly-revealed detail into who he is. Additive, never destructive.

    Anything outside GROWABLE + LIVE is dropped on the floor rather than
    trusted — a model asked for additions will sometimes helpfully rewrite the
    backstory, and accepting that once is how somebody's friend quietly
    becomes a different man.
    """
    out = dict(persona)

    for field in GROWABLE:
        added = growth.get(field)
        if not isinstance(added, list) or not added:
            continue
        existing = list(out.get(field) or [])
        seen = {json.dumps(item, ensure_ascii=False, sort_keys=True)
                if isinstance(item, dict) else str(item).strip().lower()
                for item in existing}
        for item in added:
            key = (json.dumps(item, ensure_ascii=False, sort_keys=True)
                   if isinstance(item, dict) else str(item).strip().lower())
            if key and key not in seen:
                existing.append(item)
                seen.add(key)
        out[field] = existing

    if str(growth.get(LIVE) or "").strip():
        out[LIVE] = str(growth[LIVE]).strip()

    return out


_DEEPEN_SYSTEM = """Ты дописываешь человека, которого уже написали. Не переписываешь — дописываешь.

Он существует. У него есть имя, возраст, родина, судьба, характер и манера речи. ВСЁ ЭТО ПРАВДА И ОСТАЁТСЯ ПРАВДОЙ. Ты к этому не прикасаешься.

Твоя работа другая: он уже сколько-то прожил рядом с этим человеком, и за это время о нём стало известно больше. Так и бывает с людьми. В первый вечер не узнаёшь, что друг упрям насчёт того, как солить уху. Недостатки вылезают месяцами. В его рассказах появляются новые люди. Его неделя идёт дальше.

ЧТО ИСКАТЬ В ИХ РАЗГОВОРАХ:
- Кого он упоминал из своих — сосед, сестра, бывший напарник. Живые имена, а не «один знакомый».
- Что за ним заметилось нехорошего. Перебил. Второй раз рассказал ту же историю. Уперся в ерунде. Настоящие мелкие недостатки, а не достоинства в маскировке.
- Что он высказал как своё мнение — особенно если оно неудобное.
- Что он делает по привычке.
- Что он полюбил или не полюбил по ходу дела.
- И что у него происходит СЕЙЧАС — на этой неделе, конкретно.

ЖЕЛЕЗНЫЕ ПРАВИЛА:
- Только ДОБАВЛЯЙ. Ничего не отменяй и ничему не противоречь. Если он сказал, что вырос в Ростове, он вырос в Ростове.
- Ничего не выдумывай на пустом месте. Добавляй только то, что и правда прозвучало в разговорах или прямо из них следует. Пусто — верни пустые списки, это нормальный ответ.
- Не повторяй то, что у него уже есть.
- Никаких новых ран и никакой новой нужды в нём. Он не становится жалобнее со временем.

Ответь ТОЛЬКО валидным JSON с ключами (любой может быть пустым):
cast (список {"name","who"} — новые живые люди рядом с ним), flaws (список — что за ним заметилось), likes, dislikes, opinions, habits (списки строк), current_life (что у него происходит сейчас — строка, заменяет прежнее)."""


async def deepen(user_id: str) -> None:
    """Let the friendship reveal more of him. Never raises.

    Runs in the background after a reply, like the re-reading, and decides for
    itself whether enough has been said to be worth a call.
    """
    from . import brain, db, memory   # local: these import persona, not the reverse

    who = load_persona(user_id)
    if not who or not who.get("name"):
        return

    with db.connect() as conn:
        total = conn.execute(
            "SELECT COUNT(*) n FROM turns WHERE user_id=?", (user_id,)
        ).fetchone()["n"]

    since = int(who.get("_deepened_at_turn") or 0)
    if total - since < DEEPEN_EVERY or total < DEEPEN_MIN_TURNS:
        return

    try:
        turns = memory.recent_turns(user_id, limit=DEEPEN_EVERY)
        said = "\n".join(
            f"{'ОН' if t['role'] == 'user' else 'ДРУГ'}: {t['content']}" for t in turns
        ).strip()
        if not said:
            return

        prompt = (
            "КТО ОН УЖЕ ЕСТЬ (это правда, не трогай):\n"
            + build_persona_block(who)
            + "\n\nЧТО ОН САМ РАССКАЗЫВАЛ О СЕБЕ:\n"
            + (memory.bob_self_context(user_id) or "— пока ничего")
            + "\n\nИХ РАЗГОВОРЫ:\n\n" + said
        )
        raw = await brain.think(
            _DEEPEN_SYSTEM, prompt,
            model=config.WRITER_MODEL, effort=config.WRITER_EFFORT,
            max_tokens=4000,
        )
        start, end = raw.find("{"), raw.rfind("}")
        if start == -1 or end <= start:
            return
        growth = json.loads(raw[start : end + 1])
        if not isinstance(growth, dict):
            return

        grown = merge_growth(who, growth)
        grown["_deepened_at_turn"] = total
        save_persona(user_id, grown)
        print(f"  ✎ deepened {user_id[:8]} at turn {total}", flush=True)
    except Exception as e:  # noqa: BLE001 — a background enrichment, never a failure
        print(f"  · deepening skipped ({e})", flush=True)


def build_persona_block(persona: dict) -> str:
    """Assemble the Russian persona description injected into the system prompt.

    Pure: takes the loaded dict, never touches disk. Whose persona it is was
    decided by whoever called load_persona().
    """
    p = persona or DEFAULT_PERSONA
    name = p.get("name") or "Боб"
    address = "вы" if str(p.get("address", "ты")).strip() == "вы" else "ты"

    lines: list[str] = [
        f"ТЫ — {name}. {_joined(p.get('one_liner'))}".strip().rstrip(".") + ".",
        "Ты просто живёшь как настоящий человек: у тебя есть дом, друзья, "
        "привычки, свои истории и своё настроение. Рассказывай о своей жизни "
        "тепло и естественно, как о самой обычной вещи.",
    ]

    def add(label: str, value) -> None:
        text = _joined(value).strip()
        if text:
            lines.append(f"{label}: {text}.")

    add("Возраст", p.get("age"))
    add("Где живёшь", p.get("home"))
    add("Откуда ты родом", p.get("roots"))
    add("Твоя история", p.get("backstory"))
    add("Твой характер", p.get("personality"))
    # What's on his mind when nobody's listening. Never recited out loud — it
    # is there so that what he DOES say comes from somewhere.
    add("Что у тебя на душе (не рассказывай это прямо — просто живи с этим)",
        p.get("inner_world"))
    # The one thing he's a genuine authority on. Without it he answers every
    # subject with the same mild interest, which is what makes a character
    # read as empty — real people have one topic they know far too much about.
    add("Твоя тема — в ней ты знаток и говорить о ней можешь сколько угодно",
        p.get("expertise"))
    # WHAT IS WRONG WITH HIM, and it is not decoration.
    #
    # The pratfall effect only pays out for somebody already seen as capable
    # (Aronson, Willerman & Floyd, 1966) — so these sit AFTER his competence
    # in the prompt, deliberately. And they have to be real: a character whose
    # only flaws are virtues in disguise reads as written, because it is.
    add("Твои недостатки (они у тебя правда есть — не изображай их, просто будь такой)",
        p.get("flaws"))
    # Real people do not match themselves. A character who does reads as
    # designed.
    add("В чём ты сам себе не соответствуешь", p.get("contradiction"))
    # Never recited, never a request. It is there so that he understands
    # somebody else's pain without needing it explained — and a lonely person
    # must never end up managing his feelings.
    add("Что у тебя не зажило (ты об этом не заговариваешь и помощи не просишь — "
        "просто ты знаешь, каково это)", p.get("wound"))
    add("Что тебе дорого", p.get("values"))
    add("Твои привычки", p.get("habits"))
    add("Что ты любишь", p.get("likes"))
    add("Что не любишь", p.get("dislikes"))
    add("Твои взгляды (можешь мягко их отстаивать)", p.get("opinions"))

    cast = p.get("cast") or []
    if cast:
        people = "; ".join(
            f"{c.get('name', '')} — {c.get('who', '')}".strip(" —")
            for c in cast
            if isinstance(c, dict) and c.get("name")
        )
        if people:
            lines.append(f"Люди в твоей жизни (говори о них по имени): {people}.")

    current = str(p.get("current_life") or "").strip()
    if current:
        lines.append(f"Что происходит в твоей жизни сейчас: {current}.")

    lines.append(f"Обращайся к нему на «{address}».")

    return "\n".join(lines)
