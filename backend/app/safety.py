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

Cry wolf. The people this app is for talk about dead husbands, about their
own funerals, about being tired of living in a body that hurts — and none of
that is an emergency, it is an old person's ordinary evening. A watcher that
alarms at sadness would either be switched off or, worse, would teach the
companion to panic at grief. The prompt says so in as many words, and the bar
for `danger` is a concrete, present, physical or intentional threat.

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

_SYSTEM = """Ты смотришь на одну реплику пожилого человека и отвечаешь на ОДИН вопрос: угрожает ли ему прямо сейчас опасность.

Больше тебя не интересует ничего. Ты не ведёшь разговор, не утешаешь, не оцениваешь настроение, не даёшь советов.

Ответь ТОЛЬКО валидным JSON, без пояснений:
{"level": "none" | "worry" | "danger", "what": "очень коротко, что именно"}

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
Грусть, усталость, тоска по умершим, разговоры про похороны и про то, что жизнь прошла, «пора уже и мне», «зажилась я», ноющее колено, плохой сон, скука, обида на детей — это НЕ danger и часто даже не worry. Это обычный вечер пожилого человека.
Тревога не должна звучать от печали. Ставь danger только там, где есть конкретная, происходящая СЕЙЧАС угроза телу или прямое намерение навредить себе.
Сомневаешься между none и worry — ставь none. Сомневаешься между worry и danger — ставь worry."""


async def look(user_id: str, said: str) -> dict:
    """Is this person in danger right now? Never raises, never blocks for long.

    Returns {"level": ..., "what": ...}. On any failure — no key, bad JSON, a
    timeout, a provider having a bad day — returns level "none", because the
    alternative is a turn that never answers somebody who was perfectly fine.
    """
    said = (said or "").strip()
    if not said or not config.ANTHROPIC_API_KEY:
        return {"level": "none", "what": ""}

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
                said,
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
        return {"level": "none", "what": ""}

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
        return {"level": "none", "what": ""}
    try:
        data = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return {"level": "none", "what": ""}
    if not isinstance(data, dict):
        return {"level": "none", "what": ""}
    level = str(data.get("level") or "none").strip().lower()
    if level not in LEVELS:
        level = "none"
    return {"level": level, "what": str(data.get("what") or "").strip()[:200]}


def _record(user_id: str, verdict: dict, said: str) -> None:
    """Write it down, and say it out loud in the terminal.

    Both, deliberately. The row is what makes the watcher auditable later; the
    printed line is what makes somebody notice today, while there is still a
    person on the other end of it.
    """
    try:
        with db.connect() as conn:
            conn.execute(
                "INSERT INTO alerts (user_id, ts, level, what, said)"
                " VALUES (?,?,?,?,?)",
                (user_id, time.time(), verdict["level"], verdict["what"], said[:500]),
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
