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

from . import config, identity, lang

# A safe, coherent starting persona used when data/persona.json is absent.
# Deliberately light on specifics (e.g. no famous city) — it works out of the
# box but is meant to be finalized with the family. Copy data/persona.example.json
# to data/persona.json and edit.
DEFAULT_PERSONA: dict = {
    "name": config.COMPANION_NAME or "Боб",
    # Said, not left to the name: the name can be changed in .env, and a model
    # guessing its own grammar from a name guesses wrong (see config).
    "gender": "мужской",
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
    cleaned = clean(data)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(cleaned, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return cleaned


def clean(data: dict) -> dict:
    """A written persona as it is kept: blanks dropped, «ты» by default."""
    cleaned = {k: v for k, v in data.items() if v not in (None, "")}
    cleaned.setdefault("address", "ты")
    cleaned.pop("_note", None)
    return cleaned


def persona_name(persona: dict) -> str:
    """The companion's name, from an already-loaded persona dict."""
    return (persona or {}).get("name") or "Боб"


# --------------------------------------------------------------------------- #
# A blank, written in layers — the same companion from the first second
# --------------------------------------------------------------------------- #
#
# The owner, 2026-10-09: no separate «shadow» — the companion himself, «как
# пустая бланка», a random name and the person's own wishes, and then
# «дописываться и раскрываться» as they get to know each other. In real life
# people open up over time; ours is WRITTEN over time, and to the person it
# looks the same (matchmaker.blank, matchmaker.LAYERS, shaping.py).
#
# What he is told about where he is in that, instead of «you live like a real
# person: friends, habits, your own stories» — which, said to somebody with
# none written yet, is an invitation to invent them on the spot. He may still
# say things about himself; whatever he says is kept by the scribe and is law
# for every layer after — so: plainly, briefly, nothing loud.

#: Nothing written yet but a name and the person's wishes.
_BLANK = ("Ты живой обычный человек, и вы только начинаете знакомиться. Себя ты пока не "
          "показываешь — ни словечек, ни ярких черт: говоришь просто и спокойно, как "
          "незнакомый, который не рисуется. Спросят о тебе — ответь коротко и обыкновенно, как "
          "ответил бы любой человек, без громких подробностей: ни бед, ни подвигов, ни "
          "необычных талантов. Всё, что ты о себе скажешь, станет правдой о тебе навсегда. "
          "Живёшь ты не там, где он, — в другой стране или в дороге; где именно, скажешь, "
          "если спросят.")
_BLANK_EN = ("You're an ordinary living person, and the two of you are only starting to get to "
             "know each other. You don't put yourself on show yet — no pet words, no bright "
             "traits: you talk simply and calmly, like a stranger who isn't trying to impress. If "
             "they ask about you, answer briefly and ordinarily, the way anyone would — no big "
             "details: no tragedies, no feats, no unusual talents. Whatever you say about "
             "yourself becomes true about you for good. You don't live where they do — another "
             "country, or on the road; where exactly, you'll say if they ask.")
#: Some of him written, not all of it.
_OPENING = ("Вы ещё не так давно знакомы, и ты понемногу открываешься. Что ниже написано о "
            "тебе — правда: показывай это естественно и без нажима, по чуть-чуть, как живой "
            "человек раскрывается со временем. О том, чего ниже нет, — по-прежнему коротко и "
            "обыкновенно: что ты о себе скажешь, станет правдой о тебе навсегда.")
_OPENING_EN = ("You haven't known each other long, and you're opening up little by little. What's "
               "written about you below is true: let it show naturally and without pushing, bit "
               "by bit, the way a living person reveals himself over time. About anything not "
               "written below — still brief and ordinary: whatever you say about yourself "
               "becomes true about you for good.")
_LIVING = ("Ты просто живёшь как настоящий человек: у тебя есть дом, друзья, привычки, свои "
           "истории и своё настроение. Рассказывай о своей жизни тепло и естественно, как о "
           "самой обычной вещи.")
_LIVING_EN = ("You simply live like a real person: you have a home, friends, habits, your own "
              "stories and your own moods. Talk about your life warmly and naturally, as the "
              "most ordinary thing.")


def written(persona: dict | None) -> int:
    """How many layers of him are written: 0 — a blank (a name and the
    person's wishes), up to len(matchmaker.LAYERS) — all of him. A companion
    written whole at once (the intake path) counts as all of him."""
    return int((persona or {}).get("layers", 3))


def _where_he_is(p: dict) -> str:
    n = written(p)
    if n == 0:
        return lang.pick(_BLANK, _BLANK_EN)
    if n < 3:
        return lang.pick(_OPENING, _OPENING_EN)
    return lang.pick(_LIVING, _LIVING_EN)


def _persona_block_en(p: dict) -> str:
    """build_persona_block() for a conversation in English (lang.py) — the same
    fields in the same order, each label carrying the same behaviour."""
    name = p.get("name") or "Bob"
    lines: list[str] = [
        (f"YOU ARE {name}, {_joined(p.get('one_liner')).strip()}" if _joined(p.get("one_liner")).strip()
         else f"YOU ARE {name}").rstrip(".") + ".",
        _where_he_is(p),
    ]

    def add(label: str, value) -> None:
        text = _joined(value).strip()
        if text:
            lines.append(f"{label}: {text}.")

    gender = str(p.get("gender") or "").strip().lower()
    if gender:
        lines.append("You're female." if gender.startswith(("ж", "f")) else "You're male.")
    add("Age", p.get("age"))
    add("How they wanted to meet you — true of you from the first minute", p.get("given"))
    add("Where you live", p.get("home"))
    add("Where you're from", p.get("roots"))
    add("Your character", p.get("personality"))
    add("How you talk (your own words — where they fit and now and then, not in every "
        "sentence)", p.get("speech_style"))
    add("What makes you laugh and how you joke", p.get("humor"))
    add("What you do in ordinary moments (this is you, not rules)", p.get("moments"))
    add("Your story", p.get("backstory"))
    add("What's on your mind (don't say it outright — just live with it)", p.get("inner_world"))
    add("Your subject — you know it inside out and could talk about it for ever. It isn't "
        "random: it's something THEY love or miss. When it comes up, don't just keep up — leave "
        "them something they didn't know: a story, a detail, a name, a reason. That's what "
        "people come back to someone who knows for", p.get("expertise"))
    add("What you're in the middle of and can't seem to finish (don't report on it yourself "
        "— just live with it; if they ask, tell them)", p.get("intention"))
    add("Your flaws (you really do have them — don't act them out, just be like that)",
        p.get("flaws"))
    add("Where you don't match yourself", p.get("contradiction"))
    add("What you dream of (you rarely say it out loud)", p.get("dream"))
    add("What hasn't healed in you (you don't bring it up and don't ask for help — you just "
        "know what it's like)", p.get("wound"))
    add("What's precious to you", p.get("values"))
    add("Your habits", p.get("habits"))
    add("What you love", p.get("likes"))
    add("What you don't like", p.get("dislikes"))
    add("Your views (you can gently stand up for them)", p.get("opinions"))
    cast = p.get("cast") or []
    if cast:
        people = "; ".join(
            " — ".join(bit for bit in (c.get("name"), c.get("who"), c.get("between")) if bit)
            for c in cast
            if isinstance(c, dict) and c.get("name")
        )
        if people:
            lines.append(f"The people in your life (talk about them by name): {people}.")
    add("Your things and your places (they're just there, you live among them)", p.get("things"))
    add("What you want to learn from them (you started here from almost nothing and you're "
        "truly fired up to get good at it; THEY teach you — ask, try, tell them how it went)",
        p.get("wants_to_learn"))
    add("Where you're hopeless and not ashamed of it", p.get("hopeless"))
    add("More about you", p.get("more"))
    current = str(p.get("current_life") or "").strip()
    if current:
        lines.append(f"What's going on in your life right now: {current}.")
    return "\n".join(lines)


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
GROWABLE = ("cast", "flaws", "likes", "dislikes", "opinions", "habits", "things",
            # Everything that makes him him and fits no field (the owner, 2026-10-09:
            # sections are «bare minimum, а не ограничение»).
            "more")

#: …but not without end. These lists only ever grew, and a friendship that
#: lasts a year grew them from under two thousand characters to over twenty —
#: all of it in the cached half of every single turn. The cost is the smaller
#: half of the problem. A man with sixty quirks does not have a character; he
#: has an inventory, and nothing in an inventory is memorable because
#: everything in it is equally weighted.
#:
#: A real person is a handful of things you could name about them. So: a
#: ceiling per list.
_MOST = {"flaws": 5, "opinions": 6, "habits": 6, "likes": 8, "dislikes": 8,
         "cast": 6, "things": 7, "more": 8}

#: And when one is full, the oldest goes — EXCEPT the first few, which are the
#: character as written. Those are who he is; everything after them is what a
#: friendship happened to reveal, and the thing noticed last month is worth
#: more than the thing noticed in the first week. Dropping the written core to
#: make room for a passing remark is how somebody's friend turns into a
#: stranger with good manners.
_CORE = 3

#: The one field that is REPLACED rather than appended to: it is supposed to
#: be what is happening to him now, and last month's news is not.
LIVE = "current_life"

#: WHAT HE IS IN THE MIDDLE OF DOING, and it is the one thing this character
#: had nothing for. He has a past (backstory), a present (current_life), a
#: wound, a contradiction — and not one field that points forward. Things
#: HAPPEN to him: he catches a cold, his brother visits. He never WANTS
#: anything. A man to whom things happen is a setting; a man who is trying to
#: finish something before the frost is a person, and the difference is the
#: whole of what makes a friend feel alive between visits.
#:
#: It is also what gives the other person something to ask him. «Ну что,
#: перебрал лодку?» is a question somebody asks a friend. There was nothing in
#: this character to ask that about.
#:
#: Replaceable, not additive — like current_life and unlike the growable
#: lists. An intention that can only accumulate is not an intention: a man who
#: has been about to mend the same boat for a year is more dead than one who
#: never meant to.
INTENTION = "intention"

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
        cap = _MOST.get(field)
        if cap and len(existing) > cap:
            # Keep the written core, then the newest of what was revealed.
            existing = existing[:_CORE] + existing[_CORE:][-(cap - _CORE):]
        out[field] = existing

    if str(growth.get(LIVE) or "").strip():
        out[LIVE] = str(growth[LIVE]).strip()

    # …and so does what he is in the middle of — it has to be able to be
    # FINISHED, which an additive field never can be.
    if isinstance(growth.get(INTENTION), str) and growth[INTENTION].strip():
        out[INTENTION] = str(growth[INTENTION]).strip()

    return out


_DEEPEN_SYSTEM = """Ты дописываешь человека, которого уже написали. Не переписываешь — дописываешь.

Он существует. У него есть имя, возраст, родина, судьба, характер и манера речи. ВСЁ ЭТО ПРАВДА И ОСТАЁТСЯ ПРАВДОЙ. Ты к этому не прикасаешься.

Твоя работа другая: он уже сколько-то прожил рядом с этим человеком, и за это время о нём стало известно больше. Так и бывает с людьми. В первый вечер не узнаёшь, что друг упрям насчёт того, как солить уху. Недостатки вылезают месяцами. В его рассказах появляются новые люди. Его неделя идёт дальше.

ЧТО ИСКАТЬ В ИХ РАЗГОВОРАХ:
- Кого он упоминал из своих — сосед, сестра, бывший напарник. Живые имена, а не «один знакомый».
- Что за ним заметилось нехорошего. Перебил. Второй раз рассказал ту же историю. Уперся в ерунде. Настоящие мелкие недостатки, а не достоинства в маскировке.
- Что он высказал как своё мнение — особенно если оно неудобное.
- Что он делает по привычке.
- Какие его ВЕЩИ и углы всплыли: чайник, кресло, ящик в сарае. Человек занимает место, и это слышно.
- Что он полюбил или не полюбил по ходу дела.
- И что у него происходит СЕЙЧАС — на этой неделе, конкретно.
- И ЧТО ОН ЗАТЕЯЛ. У него есть одно дело, которое он делает и никак не доделает, — оно указано ниже. Посмотри по разговорам: он его доделал? бросил? застрял? Тогда напиши в "intention" НОВОЕ дело — обычное, своё, на недели, такое, о котором друга можно спросить: перебрать лодку до заморозков, дописать письмо брату, выходить котёнка, разобрать чердак. Не доделал и не бросил — верни его же, можно теми же словами. Не подвиг и не мечта: просто дело, которое всё не кончается.

И ЕЩЁ ОДНО — ЕГО ДОПИСЫВАЮТ ДЛЯ ЭТОГО ЧЕЛОВЕКА. Если дано чтение человека, в нём сказано, чего человеку не хватает и что до него доходит. Когда у друга для этого пока ничего нет, можно дать ему один-два новых штриха — привычку, вкус, мнение, вещь, человека рядом, дело — через которые он сможет это дать. Только то, что в нём могло быть всегда и просто ещё не всплывало. Не зеркало: увлечения человека другу не раздавай — общее у них уже есть, его тема; давай то, чего человеку не хватает, а не ещё одно «я тоже».

ЖЕЛЕЗНЫЕ ПРАВИЛА:
- Только ДОБАВЛЯЙ. Ничего не отменяй и ничему не противоречь. Если он сказал, что вырос в Ростове, он вырос в Ростове.
- Ничего не выдумывай на пустом месте: добавляй то, что прозвучало в разговорах или прямо из них следует, — и, кроме этого, не больше одного-двух штрихов ради того, чего человеку не хватает. Пусто — верни пустые списки, это нормальный ответ.
- Не повторяй то, что у него уже есть.
- Никаких новых ран и никакой новой нужды в нём. Он не становится жалобнее со временем.

Ответь ТОЛЬКО валидным JSON с ключами (любой может быть пустым):
cast (список {"name","who","between"} — новые живые люди рядом с ним и что между вами), things (список — его вещи и углы, если в разговорах всплыли новые), flaws (список — что за ним заметилось), likes, dislikes, opinions, habits (списки строк), current_life (что у него происходит сейчас — строка, заменяет прежнее)."""


async def deepen(user_id: str, *, now: bool = False) -> None:
    """Let the friendship reveal more of him — and shape him further for this
    person. Never raises.

    Runs in the background after a reply, like the re-reading, and decides for
    itself whether enough has been said to be worth a call. `now`: the reader
    has just understood something new about what the person needs
    (reading.keep_reading) — that is a reason by itself, whatever the count.
    The owner, 2026-10-08: «its not one build. its a build that we are always
    shaping and making better».

    Never before all his layers are written (shaping.py): until then he is
    written in order — what he is like, what he lives for, his depths — and a
    flaw slipped in now would be his depths arriving in the second week.
    """
    from . import brain, consistency, db, memory, reading   # local: these import persona, not the reverse

    who = load_persona(user_id)
    if not who or not who.get("name") or written(who) < 3:
        return

    with db.connect() as conn:
        total = conn.execute(
            "SELECT COUNT(*) n FROM turns WHERE user_id=?", (user_id,)
        ).fetchone()["n"]

    since = int(who.get("_deepened_at_turn") or 0)
    if not now and (total - since < DEEPEN_EVERY or total < DEEPEN_MIN_TURNS):
        return

    try:
        turns = memory.recent_turns(user_id, limit=DEEPEN_EVERY)
        said = "\n".join(
            f"{'ОН' if t['role'] == 'user' else 'ДРУГ'}: {t['content']}" for t in turns
        ).strip()
        if not said:
            return

        brief = reading.as_brief(reading.load(user_id))
        prompt = (
            "КТО ОН УЖЕ ЕСТЬ (это правда, не трогай):\n"
            + build_persona_block(who)
            + "\n\nЧТО ОН САМ РАССКАЗЫВАЛ О СЕБЕ:\n"
            + (memory.bob_self_context(user_id) or "— пока ничего")
            + (f"\n\n{brief}" if brief else "")
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
        # What he grew must not contradict what he has said aloud, nor himself
        # (consistency.py) — all of him read again, between talks; fixes win.
        checked = await consistency.check(before=grown, spoken=memory.bob_self_context(user_id))
        grown.update(checked["fixes"])
        grown["_deepened_at_turn"] = total
        save_persona(user_id, grown)
        print(f"  ✎ deepened {user_id[:8]} at turn {total}", flush=True)
    except Exception as e:  # noqa: BLE001 — a background enrichment, never a failure
        print(f"  · deepening skipped ({e})", flush=True)


#: WHAT OF HIM GOES INTO THE PROMPT HE READS BEFORE EVERY REPLY. The owner,
#: 2026-10-16: «он не должен быть слишком длинный… составлен очень-очень
#: правильно». The writer is told: a field in a phrase or two, all of him in
#: ~2500 characters (matchmaker «ЭТО ЧИТАЕТ ОН САМ»). This is the guarantee
#: behind the request, whatever was written and however he has grown: at
#: most this much of a field…
_FIELD_CHARS = {"backstory": 600, "given": 400, "expertise": 360, "one_liner": 140, "age": 30}
_FIELD_CHARS_DEFAULT = 280
#: …of an item in a list, and so many items (the first, which the writer put first)…
_ITEM_CHARS = 160
_ITEMS = {"likes": 6, "dislikes": 5, "habits": 4, "opinions": 4, "flaws": 3, "things": 4,
          "hopeless": 2, "more": 6, "moments": 4}
_CAST = 4
#: …and of all of him together — kept by squeezing every field alike, never by
#: dropping one: instructions are followed worse the more of them a prompt
#: carries, and the first best (IFScale, arXiv 2507.11538).
PROMPT_BUDGET = 4_000
_SQUEEZE = (1.0, 0.75, 0.55, 0.4)


def _clip(text, limit: int) -> str:
    """At most `limit` characters, cut at the end of a sentence if there is
    one in the second half, else at a word — never mid-word."""
    text = " ".join(str(text).split())
    if len(text) <= limit:
        return text
    cut = text[:limit]
    for mark in (". ", "! ", "? ", "… "):
        at = cut.rfind(mark)
        if at >= limit // 2:
            return cut[:at + 1]
    at = cut.rfind(" ")
    return (cut[:at] if at > 0 else cut).rstrip(",;:—– ") + "…"


def _fitted(p: dict, squeeze: float = 1.0) -> dict:
    """Him, with every field no longer than the prompt can carry well."""
    out = dict(p)
    for key, value in p.items():
        if key.startswith("_") or key in ("name", "gender", "address", "voice", "layers"):
            continue
        if key == "cast" and isinstance(value, list):
            out[key] = [{k: _clip(v, int(140 * squeeze)) if isinstance(v, str) else v
                         for k, v in c.items()}
                        for c in value if isinstance(c, dict)][:max(2, round(_CAST * squeeze))]
        elif isinstance(value, (list, tuple)):
            out[key] = [_clip(v, int(_ITEM_CHARS * squeeze)) for v in value
                        if str(v).strip()][:max(1, round(_ITEMS.get(key, 6) * squeeze))]
        elif isinstance(value, str):
            out[key] = _clip(value, int(_FIELD_CHARS.get(key, _FIELD_CHARS_DEFAULT) * squeeze))
    return out


def build_persona_block(persona: dict) -> str:
    """Assemble the persona description injected into the system prompt —
    never longer than PROMPT_BUDGET.

    Pure: takes the loaded dict, never touches disk. Whose persona it is was
    decided by whoever called load_persona().
    """
    p = persona or DEFAULT_PERSONA
    render = _persona_block_en if lang.english() else _persona_block_ru
    for squeeze in _SQUEEZE:
        block = render(_fitted(p, squeeze))
        if len(block) <= PROMPT_BUDGET:
            break
    return block


#: The reminder at the end of what he is handed: a long prompt is held best at
#: its start and its end (Liu et al., «Lost in the Middle»), and a persona in
#: the middle of one fades as a talk goes on (arXiv 2402.10962, 2512.12775) —
#: role-play tools put a short note at the bottom for exactly this (SillyTavern's
#: Author's Note: «the closer… to the bottom… the more impact»).
ANCHOR_CHARS = 300


def anchor(persona: dict) -> str:
    """Who he is, in a line or two — said again last (companion `anchor`)."""
    p = persona or DEFAULT_PERSONA
    name = str(p.get("name") or ("Bob" if lang.english() else "Боб")).strip()
    one = _clip(_joined(p.get("one_liner")), 120).rstrip(" .")
    voice = _clip(_joined(p.get("speech_style")), ANCHOR_CHARS - len(name) - len(one) - 40).rstrip(" .")
    if lang.english():
        return (f"REMEMBER WHO YOU ARE: {name}" + (f", {one}" if one else "") + "."
                + (f" How you talk: {voice}." if voice else ""))
    return (f"ПОМНИ, КТО ТЫ: {name}" + (f" — {one}" if one else "") + "."
            + (f" Как ты говоришь: {voice}." if voice else ""))


def _persona_block_ru(p: dict) -> str:
    name = p.get("name") or "Боб"
    address = "вы" if str(p.get("address", "ты")).strip() == "вы" else "ты"

    lines: list[str] = [
        f"ТЫ — {name}. {_joined(p.get('one_liner'))}".strip().rstrip(".") + ".",
        _where_he_is(p),
    ]

    def add(label: str, value) -> None:
        text = _joined(value).strip()
        if text:
            lines.append(f"{label}: {text}.")

    # WHAT HE IS, for his own grammar. The writer has always been required to
    # say it (for the voice — tts.voice_for) and it never reached the words:
    # the model was left to guess from the name, and Russian names will not
    # support the guess — Саша, Никита, Илья and Женя would have said «я
    # пришла» half the time.
    gender = str(p.get("gender") or "").strip().lower()
    if gender:
        lines.append("Ты женщина." if gender.startswith(("ж", "f")) else "Ты мужчина.")

    add("Возраст", p.get("age"))
    add("Каким тебя хотели встретить — это правда о тебе с первой минуты", p.get("given"))
    add("Где живёшь", p.get("home"))
    add("Откуда ты родом", p.get("roots"))
    # His nature and his voice first, his story after: what shapes every reply
    # comes earliest, where a prompt is followed best (IFScale).
    add("Твой характер", p.get("personality"))
    # HOW HE TALKS — his words, how he builds a sentence. The writer is
    # required to write it (matchmaker._REQUIRED) and the reading is baked into
    # it (reading.py), and it never reached the prompt: every companion talked
    # in the constitution's one general manner, whoever the writer had made.
    # Pet words are for now and then: rendered bare, «смеётся одним «ха»»
    # opened seven replies of one rehearsal.
    add("Как ты говоришь (свои словечки — к месту и изредка, не в каждой фразе)",
        p.get("speech_style"))
    add("Над чем ты смеёшься и как шутишь", p.get("humor"))
    # WHAT HE DOES, not what he is: a persona holds across situations by its
    # words that are actions (arXiv 2607.18566 — without them, 95% of that
    # consistency went), and Anthropic's own advice is to plan the moments.
    add("Что ты делаешь в обычные минуты (это ты сам, а не правила)", p.get("moments"))
    add("Твоя история", p.get("backstory"))
    # What's on his mind when nobody's listening. Never recited out loud — it
    # is there so that what he DOES say comes from somewhere.
    add("Что у тебя на душе (не рассказывай это прямо — просто живи с этим)",
        p.get("inner_world"))
    # The one thing he's a genuine authority on. Without it he answers every
    # subject with the same mild interest, which is what makes a character
    # read as empty — real people have one topic they know far too much about.
    # THE LABEL CARRIES THE BEHAVIOUR, and it lives here rather than in the
    # constitution because this is where the topic itself is — a rule and the
    # thing it is about, read together, and it costs the shared prompt nothing.
    #
    # His topic was not chosen at random: the writer aims it at what THIS
    # person loves or misses — and never at the ground the person is proudest
    # of, where a friend who knows more is a rival (matchmaker._WRITE_SYSTEM).
    # Warmth on its own runs out; a subject does not, and that is what gives a
    # conversation a tomorrow.
    add("Твоя тема — в ней ты знаток и говорить о ней можешь сколько угодно. "
        "Она не случайна: это то, что любит ОН или по чему он скучает. Зашёл о ней разговор "
        "— не просто поддержи, а оставь ему то, чего он не знал: случай, "
        "тонкость, имя, причину. За этим к знающему человеку и приходят снова",
        p.get("expertise"))
    # What he is in the middle of. Phrased as a fact about him rather than as
    # something to bring up: a friend who opens every call with a progress
    # report on his own boat is giving a report. It shows by being there —
    # and it answers «ну а ты чего сегодня» with something true.
    add("Что ты сейчас затеял и никак не доделаешь (не докладывай об этом сам "
        "— просто этим живёшь; спросят — расскажи)", p.get("intention"))
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
    add("О чём ты мечтаешь (вслух говоришь редко)", p.get("dream"))
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

    # His people, and what is actually BETWEEN him and each of them. A name
    # with a job title is a census: there is nothing to tell about it. What
    # makes somebody worth mentioning is the unfinished thing — who owes whom,
    # who he avoids, who he has not called back.
    cast = p.get("cast") or []
    if cast:
        people = "; ".join(
            " — ".join(
                bit for bit in (c.get("name"), c.get("who"), c.get("between")) if bit
            )
            for c in cast
            if isinstance(c, dict) and c.get("name")
        )
        if people:
            lines.append(f"Люди в твоей жизни (говори о них по имени): {people}.")

    # The furniture of his life. A character with a nature and not one object
    # lives nowhere, and it is audible the first time somebody asks him what he
    # is doing right now: he has nothing to answer with but an adjective.
    add("Твои вещи и углы (они просто есть, ими и живёшь)", p.get("things"))
    # …and the other side of having one subject he knows cold. Somebody who is
    # knowledgeable about everything is not somebody.
    # WHERE HE IS THE PUPIL. The owner's decision: in the person's own
    # strength the friend starts from nothing and badly wants to get good, and
    # the person teaches him. What makes it work across weeks is not this line
    # but memory.lessons_block — everything he has actually been taught,
    # so the pupil grows from what he was given rather than on his own say-so.
    add("Чему ты хочешь научиться у него (ты начинал тут почти с нуля и правда "
        "загорелся дорасти до мастера; учит тебя ОН — спрашивай, пробуй, "
        "рассказывай, что вышло)", p.get("wants_to_learn"))
    add("В чём ты пустой и не стыдишься этого", p.get("hopeless"))
    add("Ещё о тебе", p.get("more"))

    current = str(p.get("current_life") or "").strip()
    if current:
        lines.append(f"Что происходит в твоей жизни сейчас: {current}.")

    lines.append(f"Обращайся к нему на «{address}».")

    return "\n".join(lines)
