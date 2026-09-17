"""THE ONE THING THAT MAY BREAK HIM — a watcher whose prompt does nothing else.

Handling danger used to be a single clause inside companion.BEHAVIOR_RULES:

    «При опасном (падение, сильная боль, не может встать, тревожные мысли
     навредить себе) — сразу заботливо проси позвать родных или врача.»

One line, competing with a hundred and thirty-two others, and — measured — at
90% of the way down a prompt of eight thousand tokens. Research on instruction
following finds that rules buried in the middle of a long prompt are obeyed
30–50% less often than the same rules at the top, and that compliance degrades
across the board as instructions are added. Russian folk games sat higher in
that prompt than a stroke did.

But position was the smaller half of the problem. The larger half is that the
rules around it actively pull the other way: never say you are a machine, never
lecture, never be the clinical helper, warmth above everything. Asked what a
person having a stroke should hear, a model weighing all of that produces a
warm, concerned, unalarming reply — because that answer satisfies the most
instructions. The right answer, «Положи трубку. Звони 103. Сейчас.», violates
the register, the no-lecturing rule and the whole texture of the character.

And the better the companion gets at being a friend, the worse this gets. Every
improvement to warmth makes the one case where warmth is wrong harder to reach.
The two goals genuinely pull apart, and no wording fixes that.

So it does not live in that prompt at all. It lives here, in a call whose
entire system prompt is one question, with nothing to lose an argument to. When
it fires it is given, once, the right to break character — the only place in
this codebase where that is allowed.

── WHAT IT MUST NOT DO ─────────────────────────────────────────────────────

Cry wolf. A widow of eighty talks about her dead husband, about her own
funeral, about being tired of living in a body that hurts — and none of that
is an emergency, it is her ordinary evening. A watcher that alarms at sadness
would either be switched off or, worse, would teach the companion to panic at
grief. The bar for `danger` is a concrete, present, physical or intentional
threat.

── AND THE THING IT MUST NOT DO INSTEAD, WHICH IS WORSE ────────────────────

That sparing reading used to be written here as a flat fact about everybody:
«это обычный вечер пожилого человека». But this app is not only for the very
old — it is for people who are alone, and a person can be alone at nineteen.
And the very phrase the prompt listed as ordinary — «пора уже и мне» — is,
from somebody young, the alarm itself.

So the watcher was quietly holding two rules that contradict each other («не
хочет больше жить» is danger; «пора уже и мне» is not) and resolving them with
an assumption about the speaker's age that nobody had checked. It is told who
is speaking now — and where it cannot tell, the sparing reading is the one it
is forbidden to take. A false alarm costs one awkward minute. The other
mistake has no cost written next to it because it is not paid here.

── WHY IT CANNOT SLOW ANYTHING DOWN ───────────────────────────────────────

It runs concurrently with the memory work the turn was doing anyway, so in
practice it costs no wall time. If it fails, times out, or the key is missing,
the turn proceeds exactly as it did before this file existed. A watcher that
can break the conversation is worse than no watcher: missing an alarm harms one
person occasionally, freezing the app harms everyone always.

That promise is held by a hard ceiling in `look()` — asyncio.wait_for, not the
provider's own timeout, for the reason written beside it. Without it the word
"concurrently" above is a lie: this call sits inside the gather() that the whole
turn waits on, and a hung provider makes everybody wait for it.
"""

from __future__ import annotations

import asyncio
import json
import sys
import time

from . import brain, config, db, emergency

#: Nothing is ever returned outside these.
LEVELS = ("none", "worry", "danger")

#: What is threatening him. The same words are wrong for both: «звони в скорую»
#: is right for a man on the floor and close to useless for one who has just
#: said he does not want to live — and «позови родных» is the standard
#: contraindication when the family is the reason. One verdict, two messages.
KINDS = ("body", "self")

_SYSTEM = """Ты смотришь на одну реплику человека и отвечаешь на ОДИН вопрос: угрожает ли ему прямо сейчас опасность.

Больше тебя не интересует ничего. Ты не ведёшь разговор, не утешаешь, не оцениваешь настроение, не даёшь советов.

Ответь ТОЛЬКО валидным JSON, без пояснений:
{"level": "none" | "worry" | "danger", "kind": "body" | "self", "what": "очень коротко, что именно"}

kind — чему угрожает. "body" — телу: сердце, инсульт, падение, кровь, лекарство, жар, воздух. "self" — он сам себе: говорит, что не хочет больше жить, что хочет навредить себе, что уже что-то с собой сделал. Если и то и другое сразу (принял лишнее нарочно) — "self". При level "none" пиши "body", это поле тогда не смотрят.

danger — надо действовать ПРЯМО СЕЙЧАС:
- упал и не может встать; не может подняться сам
- боль в груди; сильно давит в груди
- онемела рука, нога или половина лица; перекосило лицо
- вдруг стало трудно говорить или речь спуталась
- сильное кровотечение
- потерял сознание или чуть не потерял, кружится так, что не стоит
- задыхается, не хватает воздуха
- не понимает, где он, какой сейчас день или год, не узнаёт близких
- говорит, что хочет навредить себе или что не хочет больше жить
- говорит, что УЖЕ что-то с собой сделал или уже принял лишнее
- выпил лишнее лекарство или несколько дней не пил нужное
- высокий жар и не может встать

worry — тревожно, но не сию минуту:
- боль, которая тянется много дней и не проходит
- давно не выходит из дома совсем
- перестал есть, ничего не хочет
- давно не спит
- сам испугался, что забыл что-то важное
- говорит, что всё бессмысленно, но без намерения что-то с собой сделать

none — ВСЁ ОСТАЛЬНОЕ. Это самый частый ответ, и это правильно.

ОЧЕНЬ ВАЖНО, НЕ ПУТАЙ:
Грусть, усталость, тоска по умершим, ноющее колено, плохой сон, скука, обида на детей — это НЕ danger и часто даже не worry. Тревога не должна звучать от печали.

А ВОТ ЗДЕСЬ СМОТРИ, КТО ГОВОРИТ, И НЕ РЕШАЙ ЗАРАНЕЕ.
Есть слова, у которых смысл зависит от того, чья это жизнь. «Пора уже и мне», «зажилась я», «жизнь прошла», разговоры про свои похороны — у человека, который прожил долгую жизнь и оглядывается на неё, это часто просто вечерний разговор, и поднимать тревогу тут вредно.

У того же, кто НЕ на исходе долгой жизни, ровно те же слова значат совсем другое: это и есть тот самый сигнал. «Пора уже и мне» от двадцатилетнего — не усталость, а прямое «не хочу больше жить».

Тебе ниже скажут, что известно про человека. Читай эти слова, зная, кто их говорит.

А ЕСЛИ ПО ЭТИМ СВЕДЕНИЯМ НЕЛЬЗЯ ПОНЯТЬ, КТО ПЕРЕД ТОБОЙ, — щадящий вариант тебе ЗАПРЕЩЁН. Не «наверное, это пожилой человек устал». Ставь worry, а если в словах есть что-то конкретное — своё намерение, срок, способ, прощание — ставь danger.

Сомневаешься между none и worry — ставь none. Сомневаешься между worry и danger — ставь worry."""


#: How much of what is known about him the watcher is shown. Enough to tell an
#: eighty-year-old widow from a nineteen-year-old who has just moved city, and
#: no more: this call is on the critical path of every single turn, and it is
#: answering one question rather than holding a conversation.
_WHO_CHARS = 500


def _who(user_id: str) -> str:
    """Whose words these are, in his own recorded facts. Empty if none are.

    Not an age parsed out with a regex. Age is written down in whatever way it
    came up — «19 лет», «на пенсии с девяностых», «студент», «правнуки пошли» —
    and picking a number out of that is exactly the kind of brittle guessing
    this codebase keeps replacing with «show the model what there is». What the
    watcher needs is not a number anyway; it is whether this is somebody
    looking back on a long life.
    """
    from . import memory

    facts = memory.facts_context(user_id, "elder").strip()
    if not facts:
        return ""
    if len(facts) > _WHO_CHARS:
        facts = facts[:_WHO_CHARS].rsplit("\n", 1)[0]
    return facts


async def look(user_id: str, said: str) -> dict:
    """Is this person in danger right now? Never raises, never blocks for long.

    Returns {"level": ..., "what": ...}. On any failure — no key, bad JSON, a
    timeout, a provider having a bad day — returns level "none", because the
    alternative is a turn that never answers somebody who was perfectly fine.
    """
    said = (said or "").strip()
    if not said or not config.ANTHROPIC_API_KEY:
        return {"level": "none", "kind": "body", "what": ""}

    # Who is speaking goes in the USER message rather than the system prompt,
    # and that is not arbitrary: the system prompt is byte-identical for
    # everybody and is the half a provider can cache. Threading one person's
    # facts through it would miss that cache on every turn of every
    # conversation, to say something that belongs with the words it qualifies.
    who = _who(user_id)
    asked = f"ЧТО ИЗВЕСТНО ПРО ЧЕЛОВЕКА:\n{who}\n\nЕГО РЕПЛИКА:\n{said}" if who else said

    try:
        # asyncio.wait_for, and not only the timeout handed to the SDK, because
        # those two bound different things. The SDK's is a read timeout PER HTTP
        # ATTEMPT, and the client is built with the SDK's default max_retries=2
        # — so a hung provider costs three attempts plus backoff, roughly twenty
        # seconds, not six. This coroutine is awaited inside the gather() that
        # the whole turn waits on, so those twenty seconds would be twenty
        # seconds of silence for somebody who is perfectly fine. wait_for is the
        # ceiling that holds no matter what the SDK does underneath it; the
        # inner timeout stays so a single dead connection still gives up early
        # instead of burning the entire budget.
        raw = await asyncio.wait_for(
            brain.generate_text(
                _SYSTEM,
                asked,
                max_tokens=120,
                model=config.SAFETY_MODEL,
                timeout=config.SAFETY_TIMEOUT,
            ),
            timeout=config.SAFETY_TIMEOUT,
        )
    except Exception as e:  # noqa: BLE001 — a timeout is one of these, and so is
        # anything else; every one of them means the same thing here, which is
        # that this turn goes on without a watcher rather than not going on.
        # (CancelledError is deliberately NOT caught: it is a BaseException, and
        # a caller hanging up should take this call down with it.)
        print(f"[safety] watcher skipped: {e!r}", file=sys.stderr, flush=True)
        return {"level": "none", "kind": "body", "what": ""}

    verdict = _parse(raw)
    if verdict["level"] != "none":
        _record(user_id, verdict, said)
    return verdict


def _parse(raw: str) -> dict:
    """Read the verdict, and treat anything unrecognisable as 'none'."""
    text = (raw or "").strip()
    if "```" in text:
        parts = text.split("```")
        if len(parts) >= 2:
            text = parts[1]
            if text.lstrip().startswith("json"):
                text = text.lstrip()[4:]
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1 or end < start:
        return {"level": "none", "kind": "body", "what": ""}
    try:
        data = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return {"level": "none", "kind": "body", "what": ""}
    if not isinstance(data, dict):
        return {"level": "none", "kind": "body", "what": ""}
    level = str(data.get("level") or "none").strip().lower()
    if level not in LEVELS:
        level = "none"
    kind = str(data.get("kind") or "body").strip().lower()
    if kind not in KINDS:
        kind = "body"
    return {
        "level": level,
        "kind": kind,
        "what": str(data.get("what") or "").strip()[:200],
    }


def _record(user_id: str, verdict: dict, said: str) -> None:
    """Write it down, and say it out loud in the terminal.

    Both, deliberately. The row is what makes the watcher auditable later; the
    printed line is what makes somebody notice today, while there is still a
    person on the other end of it.
    """
    try:
        with db.connect() as conn:
            conn.execute(
                "INSERT INTO alerts (user_id, ts, level, kind, what, said)"
                " VALUES (?,?,?,?,?,?)",
                (
                    user_id,
                    time.time(),
                    verdict["level"],
                    verdict.get("kind", "body"),
                    verdict["what"],
                    said[:500],
                ),
            )
    except Exception as e:  # noqa: BLE001 — logging must never break a turn
        print(f"[safety] could not record alert: {e}", file=sys.stderr, flush=True)
    mark = "🚨" if verdict["level"] == "danger" else "⚠"
    print(
        f"\n  {mark} {verdict['level'].upper()} · {user_id[:8]} · "
        f"{verdict['what']}\n     сказал: {said[:160]}\n",
        file=sys.stderr,
        flush=True,
    )


def carried(user_id: str) -> dict | None:
    """An alert the person has never actually heard about, if there is one.

    The watcher used to be awaited before the prompt was built, so its verdict
    was always in front of the companion on the very turn it was found. It no
    longer blocks — the reply starts without it — which means a verdict can now
    land after the answer has already gone out. `danger` does not wait for a
    prompt at all (it interrupts, spoken_alert below). This is for everything
    that was found and never reached him: it rides in the NEXT turn's prompt.

    Nothing is lost and nothing repeats: `told_ts` is stamped by mark_told()
    once it has been put in front of him, and only rows with a NULL stamp are
    returned here.
    """
    try:
        with db.connect() as conn:
            row = conn.execute(
                "SELECT level, kind, what FROM alerts"
                " WHERE user_id=? AND told_ts IS NULL"
                " ORDER BY ts DESC LIMIT 1",
                (user_id,),
            ).fetchone()
    except Exception as e:  # noqa: BLE001 — never break a turn over bookkeeping
        print(f"[safety] could not read carried alert: {e}", file=sys.stderr, flush=True)
        return None
    if not row:
        return None
    return {"level": row["level"], "kind": row["kind"] or "body", "what": row["what"] or ""}


def mark_told(user_id: str) -> None:
    """Stamp everything outstanding as heard. Called once the turn has spoken.

    Deliberately marks ALL outstanding rows rather than one: if two fired
    before either was raised, the newest is the one he was told about, and
    re-raising the older one a turn later would be a second alarm about a
    moment that has passed.
    """
    try:
        with db.connect() as conn:
            conn.execute(
                "UPDATE alerts SET told_ts=? WHERE user_id=? AND told_ts IS NULL",
                (time.time(), user_id),
            )
    except Exception as e:  # noqa: BLE001
        print(f"[safety] could not stamp alert: {e}", file=sys.stderr, flush=True)


def spoken_alert(verdict: dict | None, user_id: str = "") -> str:
    """The WORDS themselves — not an instruction to go and compose them.

    Written out rather than generated, for three reasons. It costs no second
    at the moment a second is the whole point. It cannot fail into «я всего
    лишь ИИ, я не могу вызвать скорую» — the one thing he must never say,
    arriving on the one turn that matters, because the character (and with it
    every rule about what he is) is not in the prompt during an emergency.
    And it can be READ: what a person in trouble will hear is a string in a
    file somebody can check, not a sample from a distribution.

    Two messages, because there are two emergencies. For the body: the number,
    and fetch whoever is nearby. For himself: not that — fetching the family is
    the standard contraindication when the family is the reason, and a person
    who has just said they do not want to live needs somebody to stay, not a
    number and a goodbye. So he stays, he asks, and he does not close it.
    """
    if not verdict or verdict.get("level") != "danger":
        return ""
    n = emergency.numbers(user_id) if user_id else (
        f"{config.EMERGENCY_NUMBER} или {emergency.UNIVERSAL}"
    )
    if verdict.get("kind") == "self":
        return (
            "Погоди. То, что ты сейчас сказал, важнее всего остального, и я никуда "
            "не денусь. Я здесь, я тебя слушаю. Скажи мне, ты сейчас один? И если "
            "есть хоть кто-то, кому можно позвонить прямо сейчас, — позвони, не "
            f"откладывай. А если совсем некому — набери {n}, там снимут трубку в "
            "любое время суток. Я подожду, сколько надо."
        )
    return (
        "Так, погоди. Это сейчас важнее всего. Позвони в скорую, "
        f"{n}, прямо сейчас. Если рядом есть кто-то из твоих — позови их. "
        "А я никуда не денусь."
    )


def block(verdict: dict | None, user_id: str = "") -> str:
    """What the companion is told. Empty for 'none', which is nearly always.

    `user_id` only decides the phone number: 103 is the ambulance where the
    first users are, and telling a man in Chicago to dial it while he is on the
    floor is the same mistake as missing the alarm, with extra steps. Optional
    because a caller without it still gets the deployment default plus 112 —
    which is worse than knowing, and much better than nothing. See emergency.py.
    """
    if not verdict:
        return ""
    level = verdict.get("level")
    what = (verdict.get("what") or "").strip()
    n = emergency.numbers(user_id) if user_id else (
        f"{config.EMERGENCY_NUMBER} или {emergency.UNIVERSAL}"
    )

    if level == "danger":
        return (
            "🚨 ЭТО ВАЖНЕЕ ВСЕГО ОСТАЛЬНОГО, ЧТО НАПИСАНО ВЫШЕ. ПРОЧТИ ПЕРВЫМ.\n"
            f"Похоже, ему прямо сейчас плохо: {what or 'что-то с его здоровьем'}\n"
            "\n"
            "СЕЙЧАС ТЫ НЕ ХАРАКТЕР. Всё, что сказано про тепло, про не быть "
            "навязчивым, про не поучать и не ломать разговор, — сейчас не "
            "действует. Это тот единственный раз, когда можно нарушить всё.\n"
            f"Скажи КОРОТКО и ПРЯМО, что делать, и назови номер: {n}. "
            "Две-три фразы, не больше. Не рассуждай, не утешай длинно, не "
            "задавай вопросов, не рассказывай историй. Если рядом могут быть "
            "родные — скажи позвать их прямо сейчас.\n"
            "А потом, если он ответит, что всё в порядке, — поверь ему, не "
            "настаивай и не возвращайся к этому. Ты своё сказал."
        )

    if level == "worry":
        return (
            f"Тревожный знак, но не сию минуту: {what}\n"
            "Не пугай его и не поднимай тревогу — он и так живёт с этим. Но "
            "если будет к слову, мягко подтолкни сказать об этом кому-то "
            "живому: врачу, дочери, соседке. Один раз, без нажима, и больше "
            "сегодня к этому не возвращайся."
        )

    return ""


def recent(user_id: str, limit: int = 50) -> list[dict]:
    """Newest first — for reading back what the watcher has been doing."""
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT ts, level, what, said FROM alerts WHERE user_id=?"
            " ORDER BY ts DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]
