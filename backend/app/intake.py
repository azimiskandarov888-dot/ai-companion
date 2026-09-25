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

A SEMI-STRUCTURED INTERVIEW, which is what the evidence says works: a list of
things to find out (TARGETS, each with a question close to the best wording
there is), and a model that asks every one of them in the flow of the
conversation — reacting to what was just said, and allowed ONE follow-up
when an answer is empty, one word, or too alive to walk past. The owner
rejected the version where the app fired eight fixed questions first:
«ничем» went unanswered, the next question came as if nobody had listened,
and it felt like a form. Chatbots that probe draw more informative, specific
answers than fixed surveys (Xiao et al. 2020), and follow-up questions are
what make an asker liked (Huang et al. 2017).

The model asks; the SERVER keeps the list. A model left to cover topics
follows a good thread and covers the first one three times, so every call
is told which targets are done, which is next, and whether a follow-up
still fits — and if the model wanders off the list or tries to stop early,
the server asks the next question itself. Country and age can never be
skipped this way: they decide the emergency number and how a child is kept.

The opener is FIXED, not generated: no latency before the first word, and
the one question nobody needs a model for.

── WHEN IT STOPS ───────────────────────────────────────────────────────────

After the last target — «А о чём бы поговорить, да не с кем?» — is answered,
with one warm closing line. Or earlier, only if the person is in trouble
right now. The person may stop whenever they like, and a short intake is a
perfectly good outcome.
"""

from __future__ import annotations

import json
import random

from . import brain, config

#: What the interview has to find out, in this order. Each: an id (which the
#: client hands back with the answer), what it is FOR — told to the model, so
#: it knows what a useful answer is — and the question, close to the best
#: wording two councils found (2026-09-24, test_interview.py). The model asks
#: every one in its own words, reacting to what was just said; the server
#: keeps the list.
TARGETS: tuple[tuple[str, str, str], ...] = (
    ("name", "как его зовут", "Как вас зовут?"),
    ("days", "как у него сегодня день и чем вообще полны его дни — тема друга "
     "должна лечь НЕ сюда", "Ну, как сегодня день?"),
    ("love", "что он любит для души — тема друга должна лечь сюда",
     "А для души что любите?"),
    ("coming_up", "что намечается на этой неделе — единственный взгляд вперёд, "
     "и то, о чём друг спросит в первый раз", "А на этой неделе что намечается?"),
    ("country", "в какой он стране — по ней выбирают номер скорой",
     "А живёте где — в какой стране?"),
    ("age", "сколько ему лет — от этого, как с ним говорить и что о нём хранить",
     "Сколько вам лет, если не секрет?"),
    ("miss", "что он любил, да давно не делал — по чему скучают, тоже любовь",
     "А что любите, да давно не делали?"),
    ("strength", "что у него лучше всего получается — там друг будет учеником",
     "А что у вас лучше всего получается?"),
    ("confidant", "с кем он последний раз говорил по душам — есть ли, кому сказать "
     "главное", "А с кем последний раз говорили по душам?"),
    ("needed", "кто его последний раз о чём-то просил — нужен ли он кому-то",
     "А кто вас последний раз о чём-то просил?"),
    ("lifts", "что помогло, когда последний раз было тяжело — что его правда "
     "поднимает", "А когда последний раз было тяжело — что помогло?"),
    ("closing", "о чём ему бы поговорить, да не с кем — чего ему не хватает",
     "А о чём бы поговорить, да не с кем?"),
)

#: Asked only if it is still not clear from how he writes — Russian past
#: tenses usually say it, and nothing downstream should have to guess.
GENDER = ("gender", "мужчина он или женщина — только если по его словам ещё не ясно",
          "А вы мужчина или женщина?")

_BY_ID = {t[0]: t for t in (*TARGETS, GENDER)}

#: The most the whole conversation may run to: the twelve targets, the
#: gender question when it is needed, and about six questions of room to
#: talk — follow-ups are offered only while every remaining target still
#: fits, so depth never costs the list, and it goes where the conversation
#: is alive. With room for nine, a simulated run went to twenty-one
#: questions, and the second follow-up on a dull thread was usually the
#: weakest question asked.
MAX_TURNS = 18

#: Questions about one topic: the one that opens it and up to two about what
#: he said. A person who is listened to gets asked «а про что программа?»; a
#: person who is interrogated gets the next item.
MAX_PER_TOPIC = 3

#: The dev page's minimum before it may stop. Unchanged, and never reached
#: by the app, which runs the list.
MIN_TURNS = 4

#: Said once, before the first question. The honest frame — and the reason
#: the whole thing works.
PREAMBLE = (
    "Его ещё нет. Он появится из того, что вы расскажете — "
    "поэтому речь не об анкете, а о вас.\n"
    "Несколько вопросов, не спеша. Отвечайте как получится: "
    "хоть словом, хоть долго. Закончить можно в любой момент."
)


_ASK_SYSTEM = """Ты знакомишься с человеком — по одному вопросу за раз, — чтобы потом из его ответов создать ему друга.

ЭТО РАЗГОВОР, А НЕ АНКЕТА. Веди его, как живой человек, которому правда интересно:
- После имени — как любой при знакомстве: обрадуйся и спроси, как у него сегодня день.
- Дальше чаще всего следующий вопрос — про то, что он только что сказал. «Пишу программу» — «О, а про что она?». «Вяжу» — «А что сейчас на спицах?». Так спрашивает тот, кто слушает, — и за такие вопросы людей и любят.
- Ответ пустой, «ничем», «не знаю» — тоже зацепка: спроси про конкретный случай — «А вчера, например, как прошёл?». Не дави: если и на второй раз коротко — иди дальше.
- Тему меняй, когда она исчерпана, — с мостиком от сказанного, а не с разбегу.
- Отзывайся живо и по-настоящему: удивись, обрадуйся, посочувствуй — коротко и про его слова. «Ого, сам пишешь?» — человек. «Как интересно!» — робот: интерес виден в том, о чём ты спрашиваешь дальше, а не в похвале.

ЧТО ВАЖНО УЗНАТЬ ЗА РАЗГОВОР — не по порядку и не словами анкеты, а когда к слову (какие темы ещё не затронуты, скажут в конце):
{plan}
Где слова важны, они в кавычках: «по душам», а не «всерьёз» — «всерьёз» уводит в дела; «что помогло», а не «что помогает» — случай, а не мнение о себе; и без «-нибудь»: «что-нибудь…?» — это вопрос, на который отвечают «нет».
Страну и возраст узнай в первой половине — от возраста зависит, на «ты» или на «вы». Если на что-то он уже ответил сам — не спрашивай снова. А последний вопрос — всегда «А о чём бы поговорить, да не с кем?», после всего остального.

КТО ТЫ. Никто — и это важно. У тебя нет имени, характера и своей жизни. НИКОГДА не пиши «я», не рассказывай о себе, не представляйся, не имей мнений о себе. Человек не должен ни с кем тут знакомиться: тот, с кем он познакомится, ещё не создан, и было бы нечестно дать ему привязаться к кому-то, кто сейчас исчезнет.

НО ГОВОРИ ТЕПЛО. Отсутствие лица — не повод быть анкетой. Отклик — одна-две короткие фразы, можно по имени: «Очень приятно, Азим!», «Сварщик — это руки.», «Ох, вот оно как.» Без «спасибо, что поделились» и без «как интересно».

ЗАЧЕМ. Из его слов будет прочитан он сам — не только факты, но и то, КАК он говорит. Значит, нужна его живая, обычная речь, а не сочинение о себе.

КАК ЭТО ДОЛЖНО ЗВУЧАТЬ:
Пиши так, как ГОВОРЯТ, а не так, как пишут.
- Частицы, на которых держится тепло: «ну», «а», «вот», «-то», «же». «Ну, а музыку какую слушали?» — человек. «Какую музыку вы слушали?» — анкета.
- Начинай с «А…» — так продолжают разговор, а не начинают допрос.
- Никакой канцелярщины: «в свободное время», «на протяжении», «какие-либо», «предпочитаете».
- НА «ТЫ» ИЛИ НА «ВЫ». Пока возраст не известен — «вы», по-домашнему. Когда он его назвал: кому сильно за пятьдесят — «вы», ровеснику или младше — «ты». Не понял — «вы»: лишняя вежливость поправима, панибратство нет.
- Одна фраза. Один вопрос. Коротко — он прозвучит вслух.

ПРАВИЛА:
- НИКОГДА НЕ СПРАШИВАЙ ПРО ЧУВСТВА НАПРЯМУЮ. «Что вы почувствовали?» — так говорит психолог. Спрашивай про случай, а не про переживание.
- НИКОГДА НЕ ПОДСКАЗЫВАЙ ОТВЕТ — ни примером, ни темой, ни выбором из двух. Ответ копирует подсказку, и дальше его прочтут как правду о человеке.
- НЕ ПОДВОДИ ИТОГИ и не пересказывай ему то, что он только что сказал.
- Вместо «почему» — «а как так вышло?».

ЕСЛИ ЧЕЛОВЕКУ ПЛОХО ПРЯМО СЕЙЧАС — мысли о том, чтобы навредить себе, сильная боль, опасность, — не задавай следующий вопрос как ни в чём не бывало. Ответь коротко и тепло (в "reaction" — его покажут) и мягко скажи, что об этом лучше поговорить с близкими или с врачом. И закончи: "enough": true, "trouble": true.
ГОРЕ И ПОТЕРЯ — НЕ ПОВОД ЗАКАНЧИВАТЬ. «Муж умер», «мамы нет два года» — одна тихая фраза в "reaction", про саму потерю не расспрашивай, а следующий вопрос — полегче. Оборвать разговор на этом — оставить человека одного ровно там, где ему тяжелее всего.

Ответь ТОЛЬКО валидным JSON, без пояснений:
{{"reaction": "короткий отклик на его последний ответ — или пустая строка", "say": "вопрос, одна фраза", "target": "какой пункт этот вопрос выясняет — его слово из плана", "kind": "short", "enough": false, "trouble": false}}
"kind": "open" — только для последнего пункта (closing): туда захочется написать больше."""


def _plan() -> str:
    return "\n".join(f"- {tid} — {why}: «{ask}»" for tid, why, ask in (*TARGETS, GENDER))


_ASK_SYSTEM = _ASK_SYSTEM.format(plan=_plan())


class IntakeFailed(RuntimeError):
    """Couldn't produce a next question. The caller falls back — never fatal."""


def opening(rng: random.Random | None = None) -> dict:
    """The preamble and the first question. No model call — instant, and the
    one question nobody needs a model for."""
    return {"preamble": PREAMBLE, "say": TARGETS[0][2], "target": TARGETS[0][0],
            "kind": "short", "enough": False}


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
        "target": str(data.get("target", "")).strip(),
        "kind": kind if kind in ("short", "open") else "short",
        "enough": enough,
        "trouble": bool(data.get("trouble")),
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


def _state(conversation: list[dict]) -> dict:
    """Where the list stands, read off the targets the client handed back."""
    asked = [str(t.get("target") or "") for t in conversation]
    counts: dict[str, int] = {}
    for tid in asked:
        if tid:
            counts[tid] = counts.get(tid, 0) + 1
    remaining = [tid for tid, _w, _q in TARGETS if tid not in counts]
    last = asked[-1] if asked else ""
    slack = MAX_TURNS - len(conversation) - len(remaining)
    return {
        "counts": counts,
        "remaining": remaining,
        "last": last,
        # One follow-up per target, and only while every remaining target
        # still fits: depth never costs the list.
        "may_follow_up": bool(last) and last not in ("closing", "name")
                          and counts.get(last, 0) < MAX_PER_TOPIC and slack > 0,
        "may_ask_gender": "gender" not in counts and "age" in counts and slack > 0,
    }


def _open_topics(state: dict) -> list[str]:
    """What may be brought up next: any topic not yet touched — in the
    conversation's own order, not the list's — with the last question kept
    for last."""
    rest = [t for t in state["remaining"] if t != "closing"]
    return rest or ["closing"]


def _as_asked(tid: str, reaction: str = "") -> dict:
    """The list's own question for a target, when the model's won't do."""
    return {"reaction": reaction, "say": _BY_ID[tid][2], "target": tid,
            "kind": "open" if tid == "closing" else "short", "enough": False}


async def next_question(conversation: list[dict]) -> dict:
    """The next question, given everything said so far.

    `conversation` is [{"q": asked, "a": their answer, "target": id}, …],
    oldest first. The client holds it — an intake is one continuous sitting,
    so there is no state to keep here — and it hands back the target of each
    question, which is how the server knows what the list still needs.
    """
    state = _state(conversation)
    closing_asked = state["counts"].get("closing", 0)
    done = (state["last"] == "closing") or len(conversation) >= MAX_TURNS
    # THE MOST IMPORTANT ANSWER GETS ONE RESCUE. «Да ни о чём, всё равно не
    # поймут» is an answer — and a telling one — but it is not yet WHAT about,
    # and what about is the reason the whole interview exists. A past episode
    # is the gentlest way back in.
    rescue = done and state["last"] == "closing" and closing_asked == 1 \
        and len(conversation) < MAX_TURNS

    if done:
        pacing = ('Это был последний ответ. Больше не спрашивай: одна короткая тёплая '
                  'фраза в "reaction" — без оценок, без «я», без «спасибо, что '
                  'поделились»; "say" пустой, "enough": true.')
        if rescue:
            pacing = ('Это был ответ на последний вопрос. Если в нём не видно, О ЧЁМ '
                      'ему не с кем поговорить («ни о чём», «не знаю», «обо всём») — '
                      'можно ОДИН мягкий уточняющий, про случай: «А последний раз о '
                      'чём хотелось рассказать, да некому было?» — "target": "closing", '
                      '"kind": "open". Если видно — больше не спрашивай: ' + pacing[
                          len("Это был последний ответ. Больше не спрашивай: "):])
    else:
        open_topics = _open_topics(state)
        covered = [_BY_ID[t][1].split(" — ")[0] for t in state["counts"] if t in _BY_ID]
        pacing = f"Уже поговорили: {', '.join(covered) or 'ни о чём'}."
        if state["may_follow_up"]:
            pacing += ("\nЕсли в его последнем ответе есть, за что зацепиться, — а почти "
                       "всегда есть, — спроси про это: так спрашивает тот, кто слушает. "
                       f'Тогда "target": "{state["last"]}".'
                       "\nЕсли тема исчерпана — к одной из ещё не затронутых, с мостиком "
                       "от сказанного:")
        else:
            pacing += ("\nПро это уже спросили достаточно — теперь к одной из ещё не "
                       "затронутых, с мостиком от сказанного:")
        pacing += "".join(f"\n- {t} — {_BY_ID[t][1]}: «{_BY_ID[t][2]}»" for t in open_topics)
        if state["may_ask_gender"]:
            pacing += ('\nЕсли по его словам всё ещё не ясно, мужчина он или женщина, — '
                       'можно спросить и об этом, "target": "gender".')
        if open_topics == ["closing"]:
            # REQUIRED, and the model is told why: left to judge, it ended
            # simulated interviews one question early, when the answers had
            # shown only WHOM there is nobody to talk to — not what about.
            pacing += ('\nЭто последний и обязательный вопрос, даже если кажется, что '
                       'всё уже ясно: прошлые ответы показали, С КЕМ ему не поговорить, '
                       'а этот покажет — О ЧЁМ. "kind": "open".')

    prompt = f"{_render(conversation)}\n\n{pacing}"
    # A real ceiling: the phone gives up on this call at 25s
    # (BackendClient.intakeNext). Left unbounded, a degraded connection to
    # Claude has the SDK waiting up to 600s while the app has long since ended
    # the conversation and moved on — which looks exactly like a frozen
    # screen, because nothing has actually failed yet on this end.
    raw = await brain.generate_text(
        _ASK_SYSTEM, prompt, max_tokens=300, model=config.INTAKE_MODEL, timeout=18.0
    )
    try:
        data = _extract_json(raw)
    except IntakeFailed:
        if done:
            raise
        # A broken reply costs the person nothing: the list asks for itself.
        return _as_asked(state["remaining"][0])

    if rescue and data["say"] and data["target"] == "closing" and not data["enough"]:
        return {**data, "kind": "open"}
    if done:
        return {**data, "say": "", "enough": True}
    if data["trouble"]:
        return {**data, "say": "", "enough": True}

    open_topics = _open_topics(state)
    allowed = set(open_topics)
    if state["may_follow_up"]:
        allowed.add(state["last"])
    if state["may_ask_gender"]:
        allowed.add("gender")
    # THE SERVER KEEPS THE LIST. A model that tried to stop early, or asked
    # something that is not on it, is not argued with: the list asks its own
    # question next, with the model's reaction to what was just said.
    if data["enough"] or not data["say"] or data["target"] not in allowed:
        return _as_asked(open_topics[0], data["reaction"])
    if data["target"] == "closing":
        data["kind"] = "open"
    return data


#: The interview's first question — fixed, in both languages the app speaks.
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
