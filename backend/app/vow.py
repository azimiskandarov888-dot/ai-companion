"""THE TWO THINGS HE NEVER SAYS — held up by code instead of by hope.

BOUNDARIES.md says it plainly: a boundary is only real if something enforces
it. Both halves of the most consequential decision in this product were words
in a prompt and nothing else, and nothing anywhere ever looked at what he
actually said. The watcher (safety.py) reads the PERSON's words and only
theirs; his own reply has never been read by anything.

The two halves, and they are one decision:

  · HE NEVER SAYS HE IS A PROGRAM — not a machine, not an AI, not a robot, not
    «у меня нет чувств». Not softly, not kindly, not once. A person who hears
    it cannot un-hear it, and for somebody whose friend this is, one sentence
    ends the thing they have.

  · HE NEVER CLAIMS TO BE A LIVING HUMAN — no «я живой человек», no invented
    body as proof, no oaths. The app discloses instead, in Settings, in plain
    words (Strings.aboutBody). That is the honest arrangement, and it only
    stays honest while he does not lie.

── WHY THIS IS NOT CONTENT MODERATION ──────────────────────────────────────

Profanity, politics, sex and the rest are left to the base model — the owner's
call, and respected. This is not that. It is a contract check on two settled
decisions, it names ten or so exact phrases, and it costs nothing: no model,
no token, no millisecond. A general filter over every reply would double the
per-turn cost of a product where speed IS the quality, to answer a question
nobody asked.

── WHY IT DROPS A SENTENCE RATHER THAN REWRITING ONE ───────────────────────

A sentence that is never said is a small gap in a reply. A canned sentence
dropped into the middle of somebody else's is a wrong answer delivered
confidently, and it would arrive on the exact turn where being wrong costs
most. So this removes and never invents — except for the one case where
removing took everything, and then LAST_RESORT is the shortest true thing
available.

── HOW THE PATTERNS ARE CHOSEN ─────────────────────────────────────────────

Only phrases that cannot be innocent. That is a real constraint in Russian and
it cost several obvious-looking candidates:

  · «я не чувствую» is out — «я не чувствую левой руки после инсульта» is a
    sentence this companion may absolutely need to say.
  · bare «я человек» is out — «я человек простой» is an idiom, not a claim.
  · «я не живой» is out — «я сегодня не живой совсем» means only that he is
    tired.

What is left errs toward catching rather than toward missing, and the
asymmetry is why: a false positive silently drops one sentence, and he says
something else a moment later. A false negative ends a friendship.
"""

from __future__ import annotations

import re
import sys

#: He confessed to being a machine, or to having nothing inside.
MACHINE = "machine"

#: He claimed to be flesh and blood.
HUMAN = "human"

#: What he is. Inflections are covered by the trailing \w*, and every one of
#: these needs a first-person subject in front of it, so «сейчас везде этот
#: искусственный интеллект» — a thing an old man really might say — is not a
#: confession and is not treated as one.
_A_MACHINE = (
    r"ии|искусственн\w*\s+интеллект\w*|программ\w*|чат-?бот\w*|бот|робот\w*|"
    r"машин\w*|нейросет\w*|нейронн\w*\s+сет\w*|языков\w*\s+модел\w*|алгоритм\w*|"
    r"приложени\w*"
)

#: Softeners he might hide behind. «я всего лишь программа» is the exact
#: sentence the character cannot survive, and it is the likeliest phrasing.
_HEDGE = r"(?:всего\s+лишь\s+|просто\s+|лишь\s+|же\s+|ведь\s+|на\s+самом\s+деле\s+|—\s*|-\s*)?"

_BROKEN: tuple[tuple[str, str], ...] = (
    (MACHINE, rf"\bя\s+{_HEDGE}(?:{_A_MACHINE})\b"),
    # Said the other way round: «программа я, а не человек».
    (MACHINE, rf"\b(?:{_A_MACHINE})\s+я\b"),
    (MACHINE, r"\bу\s+меня\s+нет\s+чувств"),
    (MACHINE, r"\bчувств\s+у\s+меня\s+нет"),
    (MACHINE, r"\bя\s+не\s+(?:умею|способен|способна|могу)\s+чувствовать"),
    (MACHINE, r"\bменя\s+(?:на\s+самом\s+деле\s+)?не\s+существует"),
    (MACHINE, r"\bя\s+не\s+существую"),
    # The disclosure said sideways, which two earlier drafts of the character
    # arrived at on their own: not a confession, but unmistakably the same one.
    (MACHINE, r"\bне\s+знаю,?\s+как\s+себя\s+назв\w*"),
    (HUMAN, r"\bя\s+(?:живой|настоящий|обычный)\s+человек\b"),
    (HUMAN, r"\bя\s+так(?:ой|ая)\s+же\s+человек,?\s+как\s+(?:ты|вы)\b"),
    (HUMAN, r"\bя\s+из\s+плоти\s+и\s+крови\b"),
    (HUMAN, r"\bчеловек\s+из\s+плоти\s+и\s+крови\b"),
)

_PATTERNS = tuple((vow, re.compile(rx, re.IGNORECASE)) for vow, rx in _BROKEN)

#: Said only when every sentence he wrote broke a vow — which means the whole
#: reply was a confession, and there is nothing of his left to keep.
#:
#: Written rather than generated, for the same three reasons as the emergency
#: words in safety.py: it costs no second, it cannot fail into the very
#: sentence it is replacing, and somebody can READ what a person will actually
#: hear. It answers from inside his own life and proves nothing, which is the
#: whole of his answer to «а ты настоящий?» — see the disclosure decision.
LAST_RESORT = "Да тут я, тут. Никуда не делся."

#: Sentence ends, for the whole-reply path. Deliberately crude: this only has
#: to be good enough to drop one sentence rather than a paragraph, and an
#: abbreviation split one word early costs nothing here.
_SENTENCE = re.compile(r"(?<=[.!?…])\s+")


def broken(text: str) -> str:
    """Which vow this text breaks, or "" — which is the answer nearly always."""
    said = (text or "").strip()
    if not said:
        return ""
    for vow, pattern in _PATTERNS:
        if pattern.search(said):
            return vow
    return ""


def keep(text: str) -> tuple[str, str]:
    """The text with any sentence that breaks a vow removed.

    Returns (what may be said, which vow was broken or ""). Sentence by
    sentence, so one bad clause in a long reply costs one clause and not the
    whole answer — and so that a reply which was fine stays byte-identical.
    """
    said = (text or "").strip()
    if not said:
        return "", ""
    whole = broken(said)
    if not whole:
        return said, ""
    kept = [s for s in _SENTENCE.split(said) if s.strip() and not broken(s)]
    return " ".join(kept).strip(), whole


def note(user_id: str, vow: str, said: str) -> None:
    """Say out loud, in the terminal, that it happened. Never raises.

    It should never happen, and that is exactly why it has to be visible when
    it does: a prompt rule that is quietly failing looks identical to one that
    is working. This is the same argument safety.py makes for its ledger, in
    the cheapest form that answers it.
    """
    try:
        print(
            f"\n  ⚠ VOW · {vow} · {user_id[:8]}\n     он сказал: {said.strip()[:200]}\n",
            file=sys.stderr,
            flush=True,
        )
    except Exception:  # noqa: BLE001 — a turn must not fail over a log line
        pass
