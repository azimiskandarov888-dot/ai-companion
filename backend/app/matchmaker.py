"""Where a friend comes from.

Users never design their companion — and never name him. You don't tell a
friend what to love or who to be; you accept him as he is. Instead, the user
tells us about themselves («Tell us about you and your likings») and chooses
only who they'd be WITH: age, gender, maybe where he's from.

From that, this module lets a real person walk in: warm, alive, with common
ground with the user (the same sport, games, films found in their story) — but
with his own character, his own likes and dislikes, his own people and habits.
Even his name is his own: chosen here, never by the user.

The created friend is saved as the live persona (data/persona.json), so the
whole voice loop immediately speaks as him.
"""

from __future__ import annotations

import json

from . import brain, persona

_MATCH_SYSTEM = """Ты знакомишь людей с будущими друзьями.

Человек написал о себе и о том, кого хотел бы встретить (возраст, пол, откуда). Придумай ему НАСТОЯЩЕГО друга — живого, тёплого человека, который ему, скорее всего, понравится, а может, и полюбится.

Правила:
- ОБЩАЯ ПОЧВА: пусть несколько интересов друга совпадают с интересами человека — тот же спорт, те же игры, кино, сериалы, архитектура, медицина… что найдёшь в его рассказе.
- НО друг — не зеркало: у него свой характер, свои мнения, свои привычки, свои люди рядом (старый друг, сосед, кот…), и что-то он честно не любит. Друга принимают таким, какой он есть.
- Уважай пожелания: возраст, пол, откуда (если указано — пусть он будет оттуда, даже если это совсем другая страна).
- Имя выбери САМ: простое, человеческое, подходящее его краю. Человек имя не выбирает.
- Никакой мистики и никаких упоминаний программ или ИИ: это просто человек со своей жизнью.

Ответь ТОЛЬКО валидным JSON без пояснений, с ключами:
name, address (обычно "ты"), one_liner, age (например "34 года"), home, roots, backstory, personality, values, speech_style, habits (список строк), likes (список), dislikes (список), opinions (список), cast (список объектов {"name": ..., "who": ...}), current_life."""

_FAIL = "Не удалось создать друга — попробуйте ещё раз."


def _extract_json(raw: str) -> dict:
    """Pull the persona JSON out of the reply (tolerating code fences/prose)."""
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end <= start:
        raise RuntimeError(_FAIL)
    try:
        data = json.loads(raw[start : end + 1])
    except json.JSONDecodeError:
        raise RuntimeError(_FAIL)
    if not isinstance(data, dict) or not str(data.get("name", "")).strip():
        raise RuntimeError(_FAIL)
    return data


async def create_companion(
    about: str, *, age: str = "", gender: str = "", origin: str = ""
) -> dict:
    """Create the friend from the user's own story + their few choices.

    Saves him as the live persona and returns him — name included (the reveal).
    """
    wishes = [
        w
        for w in (
            f"возраст: {age}" if age else "",
            f"пол: {gender}" if gender else "",
            f"откуда: {origin}" if origin else "",
        )
        if w
    ]
    user_text = "Человек о себе:\n" + about.strip()
    if wishes:
        user_text += "\n\nКого он хотел бы встретить — " + "; ".join(wishes) + "."

    raw = await brain.generate_text(_MATCH_SYSTEM, user_text, max_tokens=2000)
    return persona.save_persona(_extract_json(raw))
