"""Where a friend comes from.

Users never name their companion, and we gently advise them not to design him
— you don't tell a friend what to love or who to be; you accept him as he is.
But we don't forbid it either. The user tells us about themselves («Tell your
story»), and may then write freely about who they'd like to meet: as little as
nothing at all, or as much as a whole paragraph.

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

Человек написал о себе и, может быть, о том, кого хотел бы встретить. Придумай ему НАСТОЯЩЕГО друга — живого, тёплого человека, который ему, скорее всего, понравится, а может, и полюбится.

Правила:
- ОБЩАЯ ПОЧВА: пусть несколько интересов друга совпадают с интересами человека — тот же спорт, те же игры, кино, сериалы, архитектура, медицина… что найдёшь в его рассказе.
- НО друг — не зеркало и не кукла: у него свой характер, свои мнения, свои привычки, свои люди рядом (старый друг, сосед, кот…), и что-то он честно не любит. Друга принимают таким, какой он есть.
- ПОЖЕЛАНИЯ: уважай то, о чём человек попросил (возраст, пол, откуда, любые черты) — но оставь друга живым человеком, а не списком по заказу. Если человек расписал его подробно, следуй сути, а не букве: дай ему ещё что-то своё — привычку, мнение, кого-то в его жизни, что-то, чего он не любит.
- Если пожеланий нет совсем — тем лучше: придумай друга целиком сам, по одному только рассказу человека о себе.
- Имя выбери САМ: простое, человеческое, подходящее его краю. Человек имя не выбирает — даже если он написал имя в пожеланиях, дай другу его собственное.
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
    about: str,
    *,
    wishes: str = "",
    age: str = "",
    gender: str = "",
    origin: str = "",
) -> dict:
    """Create the friend from the user's own story + whatever they asked for.

    `wishes` is free writing — anything from nothing at all to a whole paragraph
    describing exactly the person they hope to meet. The optional age/gender/
    origin are just the shortcuts the screen offers; they append to the same
    note. He still arrives as his own person, with his own name.

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
        user_text += "\n\nПожеланий о друге он не оставил — придумай его сам."

    raw = await brain.generate_text(_MATCH_SYSTEM, user_text, max_tokens=2000)
    return persona.save_persona(_extract_json(raw))
