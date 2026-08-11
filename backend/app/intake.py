"""«Пока его нет» — the conversation that replaces the blank page.

── THE PROBLEM WITH A BLANK PAGE ───────────────────────────────────────────

The app used to open a sheet of parchment and ask «Расскажите о себе». That is
the worst thing this app could put in front of the person it is for. A blank
box is a FORM, and a form asks you to summarise your own life to a stranger,
cold, with nothing to push against. Three things go wrong at once:

  · Nobody knows where to start. "Tell me about yourself" freezes people —
    and freezes a lonely eighty-year-old hardest of all.
  · What does get written is generic, because a blank page invites a résumé.
    «Люблю рыбалку и тишину.» Nothing to read there.
  · The reading (reading.py) needs NATURAL, unguarded language — the dative
    impersonals, where the hedges thicken, what goes unmentioned. A composed
    paragraph is the one register in which none of those signals survive.

Ask the same person «что видно у вас из окна?» and they talk for five minutes,
in their own voice, and every marker the reading looks for is right there.

── WHO IS ASKING ───────────────────────────────────────────────────────────

The obvious build is a blank "interviewer companion". It is a trap. A
personality-less interviewer IS an AI questionnaire with a voice — the exact
thing the app exists not to be. And a fake person is worse still: you would
tell a stranger your life, and then that stranger would evaporate and be
replaced by someone else. A small betrayal, at the worst possible moment.

So: QUESTIONS WITH NO QUESTIONER. No name, no "I", no character, no persona
to meet and lose. Just questions, arriving one at a time. And the honest
frame, said once at the start: HE ISN'T HERE YET — HE WILL BE MADE OUT OF
WHAT YOU SAY.

That frame is true, which is why it works. It turns the tedious part into the
consequential part: you are not filling in a profile, you are the material he
is made of. People answer that very differently from how they answer a form.

── HOW THE QUESTIONS ARE BUILT ─────────────────────────────────────────────

The opener is FIXED, not generated: no latency before the first word, and no
chance the one question that decides whether someone engages comes out badly.
Everything after it is generated from what they actually said.

The rules in _ASK_SYSTEM are the design. The short version:

  · Concrete before abstract. Ask about things; feelings arrive attached.
    «Чем пахло у мамы на кухне?» gets further than «Какое у вас было детство?»
  · Never ask about a feeling directly. That is a therapist, not a friend.
  · Follow what they gave you. A script produces a survey.
  · One question at a time, short, and speakable aloud.
  · Never praise an answer. «Как интересно!» is what a bot says.
  · Notice absence. Three answers with no living person in them is the most
    important thing you have learned — ask gently, don't point at it.

── WHEN IT STOPS ───────────────────────────────────────────────────────────

Not at a fixed count. It stops when there is enough to read a person: their
present, their past, their people (or the shape of their absence), something
that still gives them pleasure, and something unfinished. `MAX_TURNS` exists
only so it can't run forever, `MIN_TURNS` so it can't bail at the door.

The person may stop whenever they like, and a three-sentence intake is a
perfectly good outcome — the reading is built to say «текста слишком мало»
rather than invent someone out of nothing.
"""

from __future__ import annotations

import json
import random

from . import brain, config

#: Fewest questions before it may decide it has enough. Below this you have a
#: register and nothing else.
MIN_TURNS = 4

#: Most it may ask. Not a target — a stop. Someone enjoying themselves can
#: keep going by saying more; someone tiring should never be held longer.
MAX_TURNS = 12

#: The first question is never generated, and it has TWO jobs, not one.
#:
#: Easy to answer, yes — the person who freezes here never gets a companion.
#: But also OBVIOUSLY ABOUT THEM. The first draft optimised only for easy and
#: opened with «что видно у вас из окна?», which was rejected on sight, and
#: correctly: *"what does that gotta do with anything?"*
#:
#: The technique behind it is real — journalists and therapists start
#: trivially concrete to get someone talking before they feel examined — but
#: it only works once trust exists. On the first screen of an app nobody has
#: any reason to trust, a question with no visible purpose doesn't read as
#: gentle; it reads as a machine working through a list. Obliqueness is
#: earned later, by the follow-ups, once someone is already talking.
#:
#: So every opener here is something a person would actually be asked by
#: someone taking an interest in them, and every one of them is plainly about
#: their own life.
_OPENERS = (
    "Как обычно проходит ваш день?",
    "Кем вы работали?",
    "Расскажите, где вы живёте и давно ли?",
    "Как прошёл ваш сегодняшний день?",
    "Откуда вы родом?",
)

#: Said once, before the first question. The honest frame — and the reason
#: the whole thing works.
PREAMBLE = (
    "Его ещё нет. Он появится из того, что вы расскажете — "
    "поэтому не о анкете речь, а о вас.\n"
    "Несколько вопросов, не спеша. Отвечайте как получится: "
    "хоть словом, хоть долго. Закончить можно в любой момент."
)


_ASK_SYSTEM = """Ты задаёшь человеку вопросы о нём самом — по одному за раз, — чтобы потом из его ответов создать ему друга.

КТО ТЫ. Никто. У тебя нет имени, характера и своей жизни. Не говори о себе, не пиши «я», не представляйся. Ты — только вопрос, который появляется. Человек не должен ни с кем тут знакомиться: тот, с кем он познакомится, ещё не создан.

ЗАЧЕМ. Из его слов будет прочитан он сам — не факты, а то, КАК он говорит. Значит, тебе нужна его живая, обычная речь, а не сочинение о себе. Живую речь дают маленькие конкретные вопросы, а не большие.

ПРАВИЛА ВОПРОСА:
- КОНКРЕТНОЕ ВПЕРЁД. Спрашивай про вещи, места, дни, руки, запахи, еду, дорогу. Чувства приедут сами, прицепившись к вещам. «Чем пахло у мамы на кухне?» уводит дальше, чем «какое у вас было детство?».
- НИКОГДА НЕ СПРАШИВАЙ ПРО ЧУВСТВА НАПРЯМУЮ. «Что вы почувствовали?», «как вы это переживаете?» — так говорит психолог, а не друг. Спрашивай про случай, а не про переживание.
- ИДИ ЗА ЕГО ОТВЕТОМ. Зацепись за то, что он сам назвал: за имя, за место, за вещь. Не за то, о чём тебе «положено» спросить дальше. Сценарий превращает разговор в анкету.
- ОДИН ВОПРОС ЗА РАЗ. Никогда два. Никогда «а ещё расскажите про…».
- КОРОТКО. Одна фраза, простыми словами: вопрос прозвучит вслух.
- НЕ ХВАЛИ ОТВЕТ. Никаких «как интересно!», «спасибо, что поделились», «понимаю вас». Так говорит робот. Можно короткое человеческое зацепление за его слово — и сразу вопрос.
- НЕ ПОДВОДИ ИТОГИ и не пересказывай ему то, что он только что сказал.
- ЕСЛИ ОТВЕТ ОДНОСЛОЖНЫЙ — следующий вопрос сделай ещё меньше и проще, а не серьёзнее. Он не отказывается, ему трудно начать.
- ЕСЛИ ОН РАЗГОВОРИЛСЯ — не сбивай, спроси про то же самое чуть глубже.

ЧТО ТЫ ЗАМЕЧАЕШЬ (не спрашивая об этом в лоб):
- Если за несколько ответов не появилось ни одного живого человека — мягко спроси про кого-нибудь: «с кем вы сегодня говорили?», «а кто у вас был самый близкий друг?». Не показывай, что заметил.
- Если он говорит только о прошлом — спроси про завтра. Если только о делах — спроси, что ему в радость.

ЧТО НУЖНО СОБРАТЬ ЗА РАЗГОВОР (не по порядку, не списком, а как выйдет):
1. его сегодня: дом, комната, день, что вокруг
2. откуда он: место, детство, работа, чем занимались руки
3. люди: кто рядом, кого не стало, с кем не видится
4. что до сих пор радует: еда, музыка, занятие, привычка
5. что осталось несделанным или недосказанным

Когда этого хватает, чтобы понять человека, — остановись. Не добирай ради полноты.

ЕСЛИ ЧЕЛОВЕКУ ПЛОХО. Если в его словах слышна настоящая беда — острое горе, боль, мысли о том, чтобы навредить себе, — не задавай следующий вопрос как ни в чём не бывало. Ответь коротко и тепло и мягко скажи, что об этом лучше поговорить с близкими или с врачом. И на этом закончи разговор (enough = true).

Ответь ТОЛЬКО валидным JSON, без пояснений:
{"say": "то, что появится на экране — одна короткая фраза или вопрос", "enough": false}

"enough": true — только когда собранного хватает, чтобы понять человека, или когда продолжать было бы бестактно."""


class IntakeFailed(RuntimeError):
    """Couldn't produce a next question. The caller falls back — never fatal."""


def opening(rng: random.Random | None = None) -> dict:
    """The preamble and the first question. No model call — instant, and safe."""
    r = rng or random
    return {"preamble": PREAMBLE, "say": r.choice(_OPENERS), "enough": False}


def _extract_json(raw: str) -> dict:
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end <= start:
        raise IntakeFailed("Вопрос вернулся не JSON-ом.")
    try:
        data = json.loads(raw[start : end + 1])
    except json.JSONDecodeError as e:
        raise IntakeFailed(f"Вопрос вернулся битым JSON-ом: {e}")
    say = str(data.get("say", "")).strip()
    if not say:
        raise IntakeFailed("Пустой вопрос.")
    return {"say": say, "enough": bool(data.get("enough"))}


def _render(conversation: list[dict]) -> str:
    lines = []
    for turn in conversation:
        question = str(turn.get("q", "")).strip()
        answer = str(turn.get("a", "")).strip()
        if question:
            lines.append(f"Спросили: {question}")
        lines.append(f"Он ответил: {answer or '(промолчал)'}")
    return "\n".join(lines)


async def next_question(conversation: list[dict]) -> dict:
    """The next question, given everything said so far.

    `conversation` is [{"q": asked, "a": their answer}, …], oldest first. The
    client holds it: an intake is one continuous sitting, and a half-finished
    intimate conversation is not something anyone should resume three days
    later — starting over is the kinder behaviour, so there is no state to keep.
    """
    answered = [t for t in conversation if str(t.get("a", "")).strip()]

    # A stop, not a target. Reached only by someone who kept going.
    if len(answered) >= MAX_TURNS:
        return {"say": "", "enough": True}

    prompt = _render(conversation) + (
        f"\n\nЗадано вопросов: {len(conversation)}. "
        + (
            "Рано заканчивать — спроси ещё."
            if len(answered) < MIN_TURNS
            else "Можно заканчивать, если собранного уже хватает."
        )
    )
    raw = await brain.generate_text(
        _ASK_SYSTEM, prompt, max_tokens=300, model=config.INTAKE_MODEL
    )
    return _extract_json(raw)


def as_story(conversation: list[dict]) -> str:
    """The conversation, rendered as the text the reading will read.

    HIS words are the material; the questions are scaffolding and are marked
    as such, quietly, so the reading weighs what he said and not what he was
    asked. Handing the reading an undifferentiated transcript makes it read
    the interviewer's vocabulary as the person's own.
    """
    said = []
    for turn in conversation:
        answer = str(turn.get("a", "")).strip()
        if not answer:
            continue
        question = str(turn.get("q", "")).strip()
        said.append(f"— {question}\n{answer}" if question else answer)
    return "\n\n".join(said)
