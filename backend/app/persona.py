"""Bob's persona — WHO he is, as editable data (not hardcoded).

His name, home, backstory, personality, friends, habits, and current life all
live in a JSON file (``data/persona.json``) so the family can change them anytime
— after they've decided the real story — WITHOUT touching any code. If the file
is missing, a safe built-in default is used so the app always runs.

`companion.py` holds the *stable* behavior (warmth, the "third way" honesty, the
safety guardrails). This file holds the *changeable* character. The two are
combined into the system prompt at reply time.

The full character design is in ../../docs/BOB-PERSONA.md.
"""

from __future__ import annotations

import json

from . import config

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


def load_persona(path=None) -> dict:
    """Load the persona from JSON. The built-in default is used ONLY when no
    persona exists at all (the browser dev path, a fresh checkout) — a saved
    character is taken exactly as saved, never topped up from the default.
    """
    path = path or config.PERSONA_PATH
    if path and path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data.get("name"):
                return {"address": "ты", **data}
        except (json.JSONDecodeError, OSError):
            pass
    return DEFAULT_PERSONA


def save_persona(data: dict, path=None) -> dict:
    """Persist a persona to data/persona.json — it becomes who the companion is.

    NO backfilling from DEFAULT_PERSONA. It used to merge the default under
    every created character, which meant any field the pen left blank was
    quietly filled with the template's life — the sea, the cat Мурзик, the
    café — and every friend came out part template. The user met "his" cat in
    three different characters before this was found. A gap in a created
    character stays a gap (build_persona_block simply skips empty fields);
    a gap is honest, a borrowed life is not.
    """
    path = path or config.PERSONA_PATH
    cleaned = {k: v for k, v in data.items() if v not in (None, "")}
    cleaned.setdefault("address", "ты")
    cleaned.pop("_note", None)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(cleaned, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return cleaned


def persona_name(persona: dict | None = None) -> str:
    return (persona or load_persona()).get("name") or "Боб"


def _joined(value) -> str:
    if isinstance(value, (list, tuple)):
        return "; ".join(str(v) for v in value if str(v).strip())
    return str(value or "")


def build_persona_block(persona: dict | None = None) -> str:
    """Assemble the Russian persona description injected into the system prompt."""
    p = persona or load_persona()
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
