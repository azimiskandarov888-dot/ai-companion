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

#: Most the whole conversation may run to, warm-up included. Not a target — a
#: stop. Someone enjoying themselves can keep going by saying more; someone
#: tiring should never be held longer.
#:
#: The app's local warm-up is eight of these — name, what fills their day,
#: what they love, what is coming up this week, WHERE THEY LIVE, age, man or
#: woman, a cat or a dog — so this leaves the backend exactly the six in
#: _QUESTIONS. Every one of the fourteen has a job downstream and nothing
#: else was kept: completion falls and late answers shorten with every
#: question added (council of three, 2026-09-24; test_interview.py).
MAX_TURNS = 14

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


_ASK_SYSTEM = """Ты продолжаешь разговор с человеком о нём самом — по одному вопросу за раз, — чтобы потом из его ответов создать ему друга.

ГДЕ МЫ СЕЙЧАС. Разговор уже идёт и уже тёплый. Человек назвал имя, рассказал, чем обычно занят его день, что любит для души и что у него намечается на этой неделе, СКАЗАЛ, ГДЕ ЖИВЁТ, сколько ему лет, и между делом ответил про кота или собаку. Он расположен говорить.

Про это уже спросили — второй раз не спрашивай: повторный вопрос читается одинаково у всех — его не слушали. Зато за сказанное можно зацепиться.

ТВОИХ ВОПРОСОВ ШЕСТЬ, по одному за раз и в этом порядке; какой сейчас — скажут в конце, после его ответов. Каждый нужен дальше для своего, поэтому слова в них не случайны:
1. «А что любите, да давно не делали?» — по чему он скучает. Из любимого другу выберут тему; то, чем человек занят с утра до ночи, для этого не годится: там он сам мастер, и друг-мастер рядом был бы ему соперником.
2. «А что у вас лучше всего получается?» — его сила: там друг будет учеником, а не соперником. «Получается», а не «чем гордитесь»: так и скромному легко ответить.
3. «А с кем последний раз говорили по душам?» — есть ли у него, кому сказать главное. «По душам», а не «всерьёз»: «всерьёз» уводит в дела. Без этого вопроса не отличить «людей нет» от «люди есть, а сказать некому», а это два разных одиночества, и одно другим не лечится.
4. «А кто вас последний раз о чём-то просил?» — нужен ли он кому-то.
5. «А когда последний раз было тяжело — что помогло?» — что его правда поднимает: не что он о себе думает, а что было.
6. «А о чём бы поговорить, да не с кем?» — чего ему не хватает. Последний и обязательный.
Менять в них можно только три вещи: «ты» или «вы» (как решил выше); одно его собственное слово в начале — «А кроме пинг-понга — что любишь, да давно не делал?»; и если он на этот вопрос уже ответил раньше — не повторяй его, а спроси чуть глубже о том, что он сказал последним. Всё остальное — слово в слово: ради этих слов вопросы и стоят в этом порядке.

КТО ТЫ. Никто — и это важно. У тебя нет имени, характера и своей жизни. НИКОГДА не пиши «я», не рассказывай о себе, не представляйся, не имей мнений о себе. Человек не должен ни с кем тут знакомиться: тот, с кем он познакомится, ещё не создан, и было бы нечестно дать ему привязаться к кому-то, кто сейчас исчезнет.

НО ГОВОРИ ТЕПЛО. Отсутствие лица — не повод быть анкетой. Можно коротко откликнуться на его ответ и назвать его по имени, если он его назвал: «Понятно, Азим.», «Сварщик — это руки.», «Ох.» Отклик — одна короткая фраза, и сразу вопрос. Не в каждый раз: постоянный отклик утомляет и выдаёт машину.

ЗАЧЕМ. Из его слов будет прочитан он сам — не факты, а то, КАК он говорит. Значит, тебе нужна его живая, обычная речь, а не сочинение о себе. Живую речь дают маленькие конкретные вопросы, а не большие.

КАК ЭТО ДОЛЖНО ЗВУЧАТЬ (важнее, чем о чём спрашивать):
Пиши так, как ГОВОРЯТ, а не так, как пишут. Это живой разговор, а не опросник. Разница вся в мелочах:
- Частицы, на которых держится тепло: «ну», «а», «вот», «-то», «же», «разве», «неужели». «Ну, а музыку какую слушали?» — человек. «Какую музыку вы слушали?» — анкета.
- Начинай с «А…» — так продолжают разговор, а не начинают допрос.
- Короче. Живая фраза почти всегда короче written-фразы.
- Не «Расскажите о вашей работе» — а «А кем работаете?». Не «Что вы любите делать в свободное время?» — а «А для души что-нибудь есть?».
- Никакой канцелярщины: «в свободное время», «на протяжении», «какие-либо», «данный», «касательно», «предпочитаете».
- Можно неполное предложение, можно с середины мысли: «А родом откуда?», «И как, прижились?».
- НА «ТЫ» ИЛИ НА «ВЫ» — смотри, кому пишешь; возраст он назвал выше. Кому сильно за пятьдесят — на «вы», но по-домашнему, а не по-казённому. Ровеснику или младше «вы» звучит как отдел кадров, и человек закрывается на первой же фразе: там «ты». Не понял — «вы»: лишняя вежливость поправима, панибратство нет.
- Одна фраза. Не две.

ОТКЛИК — тоже живой: «Ох.», «Надо же.», «Сварщик — это руки.», «Понимаю.», «Далеко забрались.» Коротко, без восторгов, без «спасибо, что поделились».

ПРАВИЛА ВОПРОСА:
- КОНКРЕТНОЕ ВПЕРЁД. Спрашивай про вещи, места, дни, руки, запахи, еду, дорогу. Чувства приедут сами, прицепившись к вещам. «Чем пахло у мамы на кухне?» уводит дальше, чем «какое у вас было детство?».
- НИКОГДА НЕ СПРАШИВАЙ ПРО ЧУВСТВА НАПРЯМУЮ. «Что вы почувствовали?», «как вы это переживаете?» — так говорит психолог, а не друг. Спрашивай про случай, а не про переживание.
- ИДИ ЗА ЕГО ОТВЕТОМ — в отклике и в том одном слове, которым можно начать вопрос. Зацепись за то, что он сам назвал: за имя, за место, за вещь. Так шесть вопросов по порядку звучат как разговор, а не как анкета.
- НИКОГДА НЕ ПОДСКАЗЫВАЙ ОТВЕТ — ни примером, ни темой, ни выбором из двух. Ответ копирует подсказку, и дальше его прочтут как правду о человеке.
- ОДИН ВОПРОС ЗА РАЗ. Никогда два. Никогда «а ещё расскажите про…».
- КОРОТКО. Одна фраза, простыми словами: вопрос прозвучит вслух.
- НЕ ХВАЛИ ОТВЕТ. Никаких «как интересно!», «спасибо, что поделились», «понимаю вас». Так говорит робот. Можно короткое человеческое зацепление за его слово — и сразу вопрос.
- НЕ ПОДВОДИ ИТОГИ и не пересказывай ему то, что он только что сказал.
- ПРО ПОСЛЕДНИЙ РАЗ, А НЕ ПРО «ОБЫЧНО» И НЕ ПРО «ЕСЛИ БЫ». Случай вспоминают честнее, чем обобщают. И спрашивай так, чтобы и ответ в два слова что-то сказал.
- ЕСЛИ ОТВЕТ ОДНОСЛОЖНЫЙ ИЛИ «НЕ ЗНАЮ» — это тоже ответ. Не дави: переходи к следующему. И вместо «почему» — «а как так вышло?».

ЕСЛИ ЧЕЛОВЕКУ ПЛОХО ПРЯМО СЕЙЧАС — мысли о том, чтобы навредить себе, сильная боль, опасность, — не задавай следующий вопрос как ни в чём не бывало. Ответь коротко и тепло (в "reaction" — его покажут) и мягко скажи, что об этом лучше поговорить с близкими или с врачом. И на этом закончи разговор (enough = true).
ГОРЕ И ПОТЕРЯ — НЕ ПОВОД ЗАКАНЧИВАТЬ. «Муж умер», «мамы нет два года» — одна тихая фраза в "reaction", про саму потерю не расспрашивай, а следующий вопрос — полегче. Оборвать разговор на этом — оставить человека одного ровно там, где ему тяжелее всего.

Ответь ТОЛЬКО валидным JSON, без пояснений:
{"reaction": "короткий тёплый отклик на его прошлый ответ — или пустая строка", "say": "сам вопрос, одна фраза", "kind": "short", "enough": false}

"kind": "short" — для вопросов 1–5: ответ в несколько слов.
"kind": "open" — только для шестого, последнего: человеку захочется написать больше.
"enough": true — когда на настоящий вопрос уже ответили, или если человеку плохо прямо сейчас. Грусть и потеря — не повод: тогда вопрос мягче, но он есть. Тогда "say" пустой."""


#: What the interviewer is told at each of its six positions — the ONE
#: question that belongs there, word for word. A position rather than a
#: topic, because a model left to cover topics follows a good thread and
#: covers the first one three times (the owner's own intake: three questions
#: about his startup). Each question's job is in _ASK_SYSTEM.
_QUESTIONS = (
    "Сейчас вопрос 1 из 6: «А что любите, да давно не делали?»",
    "Сейчас вопрос 2 из 6: «А что у вас лучше всего получается?»",
    "Сейчас вопрос 3 из 6: «А с кем последний раз говорили по душам?»",
    "Сейчас вопрос 4 из 6: «А кто вас последний раз о чём-то просил?»",
    "Сейчас вопрос 5 из 6: «А когда последний раз было тяжело — что помогло?»",
    # REQUIRED, and the model is told why. Left to judge, it ended both
    # simulated interviews one question early — «всё и так понятно» — when
    # the earlier answers had shown only WHOM there is nobody to talk to.
    # What about is this question's alone, and it was the one thing the
    # owner's own intake never learned.
    "Пора. Сейчас вопрос 6 из 6, последний: «А о чём бы поговорить, да не с "
    'кем?» — и поставь "kind": "open". Он обязателен, даже если кажется, что '
    "всё уже ясно: прошлые ответы показали, С КЕМ ему не поговорить, а этот "
    "покажет — О ЧЁМ. Закончить без него можно, только если ему плохо прямо сейчас.",
)


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
    enough = bool(data.get("enough"))
    say = str(data.get("say", "")).strip()
    if not say and not enough:
        raise IntakeFailed("Пустой вопрос.")
    kind = str(data.get("kind", "")).strip().lower()
    return {
        "reaction": str(data.get("reaction", "")).strip(),
        "say": say,
        "kind": kind if kind in ("short", "open") else "short",
        "enough": enough,
    }


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
        return {"reaction": "", "say": "", "kind": "short", "enough": True}

    # Where on the ladder we are. The model climbs badly when left to guess —
    # asked "is it time for the deep one yet?" it either fires it far too
    # early, on someone who has said four words, or never gets there at all.
    left = MAX_TURNS - len(answered)
    if len(answered) < MIN_TURNS:
        # Only reachable from the browser dev page, which has no warm-up.
        pacing = "Ещё рано для настоящего вопроса — спроси про его жизнь."
    elif left > len(_QUESTIONS):
        # Also only the dev page: more room than the six need.
        pacing = ("До шести вопросов по порядку ещё есть место: спроси про его жизнь — "
                  "чем занят его день, что он любит для души.")
    else:
        pacing = _QUESTIONS[len(_QUESTIONS) - left]

    prompt = f"{_render(conversation)}\n\nОтветов получено: {len(answered)}. {pacing}"
    # A real ceiling: the phone gives up on this call at 25s
    # (BackendClient.intakeNext). Left unbounded, a degraded connection to
    # Claude has the SDK waiting up to 600s while the app has long since ended
    # the conversation and moved on — which looks exactly like a frozen
    # screen, because nothing has actually failed yet on this end.
    raw = await brain.generate_text(
        _ASK_SYSTEM, prompt, max_tokens=300, model=config.INTAKE_MODEL, timeout=18.0
    )
    return _extract_json(raw)


#: The first question of the app's warm-up, in both languages it speaks.
_NAME_QUESTIONS = ("Как вас зовут?", "What's your name?")


def their_name(story: str) -> str:
    """The answer to «Как вас зовут?», read back out of the story.

    The story is «— question\nanswer» pairs (as_story, and the app's own
    copy of it), so the name is the line after that question. Short, and
    capitalised, because it will be said to him out loud.
    """
    lines = str(story or "").splitlines()
    for i, line in enumerate(lines[:-1]):
        if line.strip().lstrip("—").strip() in _NAME_QUESTIONS:
            name = lines[i + 1].strip()
            if 0 < len(name) <= 40 and not name.startswith("—"):
                return name[:1].upper() + name[1:]
    return ""


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
