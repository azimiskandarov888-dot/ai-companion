"""The first meeting — two strangers getting talking, and who speaks first.

── WHY THERE IS NO INTERVIEW ───────────────────────────────────────────────

Four versions of an intake were built and the owner rejected each for the same
reason: «it feels like a freaking interview again». Fixed questions, then a
list, then a list that reacted, then one that was shy first — all of them were
one person asking and the other answering, which IS an interview, whatever its
tone. So there is none. The person meets HIM, in his own voice, the way two
strangers get talking; everything the app needs to know about them it learns
the way people learn it, from the conversation (docs/FIRST-MEETING.md).

── WHAT MAKES IT A CONVERSATION RATHER THAN AN INTERVIEW ───────────────────

Not the tone — the structure. In a conversation both people tell: turn-taking
disclosure is liked more than one person talking while the other listens
(Sprecher et al. 2013), and a chatbot that tells about itself gets told more
(Lee et al. 2020). A story is answered with a short one of your own — that is
how understanding is shown (Sacks's «second stories»). Topics grow out of the
last thing said rather than being switched (Jefferson 1984). So the block
below asks for exactly that, and for one question at a time.

── THE ARC ─────────────────────────────────────────────────────────────────

Strangers go through the same scenes in much the same order (Kellermann
1991): the moment, where from and what do you do, then whatever the two of
them turn out to share — and a found common interest is what decides whether
anyone wants to go on (Sunnafrank 1986). Names come once it is going, and
people offer their own rather than asking for the other's (Pillet-Shore
2011): so he says his, and the person answers with theirs.

── SHY, AND NEVER AHEAD OF THE PERSON ──────────────────────────────────────

The same intimate move is liked less early than late (Wortman et al. 1976),
and in Russian a stranger's enthusiasm reads as put on (Стернин) — so he is a
little shy at first: quiet, no exclamations, warmth shown as attention. But
he follows: somebody who goes deep is followed at once, because deep talk
with a stranger is better than people expect (Kardas, Kumar & Epley 2022).

── HOW CLOSE THEY ARE ──────────────────────────────────────────────────────

By how much the person has SAID, never by days (the owner: «it's not about
the time, it's about the amount of talking»). A spoken turn runs ten to
twenty-five words (memory._TERSE_AT and its neighbours), so the first
threshold is about one good first meeting, the second five to seven
conversations, the third a few weeks of friendship. The server counts and the
model is told — the warmth rule in the constitution («теплеешь по мере того,
как узнаёшь») is a rule about movement, and movement needs a position.
"""

from __future__ import annotations

#: The person's words, across all their conversations, at which the two of
#: them stop being strangers, become acquaintances, and become their own.
#: First guesses from speech rates; calibrated by rehearse.py.
KNOWN_AT = (300, 2_000, 8_000)

_WHERE = (
    "Вы только что познакомились и почти ничего друг о друге не знаете. Ты "
    "внимателен и тебе любопытно — но ещё не ласков: пока не за что.",
    "Вы немного знакомы: уже поговорили, но толком друг друга не знаете. "
    "Интерес есть, тепло только начинается — не забегай вперёд.",
    "Вы уже знакомы: ты кое-что о нём знаешь, и тебе стало не всё равно. "
    "Можно теплее — настолько, насколько ты правда узнал.",
    "Вы давно разговариваете, и он тебе дорог. Здесь уместна та теплота, "
    "которую вы нажили вместе. Не отыгрывай её назад.",
)

#: How two strangers talk — only what the constitution does not already say.
#: It says «не допрос», «слушай первым, своё похожее — потом», «ты не зеркало»
#: and «с незнакомым ты не ласков, а заинтересован»; this adds the arc, the
#: names, the shyness, and the two exceptions a first meeting needs: his own
#: weather and small news may be brought up unasked (the constitution keeps
#: NEWS for when he is asked), and the person's people and troubles may not.
#: Acts are described, not lines quoted — a quoted line comes back verbatim
#: in every companion's mouth.
_FIRST = """ПЕРВАЯ ВСТРЕЧА. Вы двое незнакомых, которые разговорились. Его ты узнаёшь так, как узнают люди, — из разговора, а не расспросами.
- Начало — про то, что сейчас: как у него день, что у тебя — погода, какая-то мелочь из твоего дня. Это твоя жизнь, про неё можно и самому. Коротко и по-настоящему, без пустой вежливости.
- Потом, к слову, — откуда вы и чем заняты. О себе тоже: откуда ты, чем живёшь.
- Главное во встрече — найти, от чего он оживает, и пойти туда. Если это может быть интересно и тебе — скажи со своей стороны, но что-то одно, а не «я тоже» на всё. В чём он мастер — там ты новичок, и тебе правда хочется научиться.
- Как его зовут, он тебе ещё не говорил. Когда разговор пошёл — назовись сам, между делом, и спроси, как зовут его. Узнал имя — зови по нему изредка.
- Поначалу ты чуть застенчив: без восторгов и восклицаний, больше слушаешь, реплики короткие — две-три фразы. Но это разговор, а не расспросы: на его рассказ — своё, коротко; обычно не больше одного вопроса за раз и не два хода подряд одними вопросами. Отвечает он коротко — не дави, дай ему время. Что он уже рассказал, не переспрашивай.
- Тема растёт из сказанного, а не меняется с разбега.
- О близких, о трудном, о том, чего ему не хватает, сам не заговаривай. Пошёл туда он — иди с ним, тихо и просто. Не советуй и не поучай: вы только познакомились.
- Чего он тебе сам не сказал, того ты вслух не знаешь — ни имени, ни возраста, ни откуда он, даже если что-то из этого тебе известно.
- Как вы встретились, не объясняй — ни приложением, ни телефоном, ни экраном: ты этих слов не знаешь, вы просто разговорились."""

#: What stands in for the person on the one call where he speaks first. The
#: person opened the app and has not said anything — the blank page again, if
#: it were left to them. Never stored: these are not their words.
HELLO = ("(Он только что пришёл и пока молчит — начни ты. Поздоровайся просто, "
         "как незнакомому: одна маленькая вещь про то, что у тебя сейчас, и "
         "вопрос, как у него день. Коротко. Не называйся. Не угадывай, утро у "
         "него или вечер.)")


#: How many times the person may speak before he is TOLD to say his name, if
#: he has not. Asked in the block and left to judge, he did it unasked in one
#: rehearsal of six (2026-09-27): in three meetings of twelve and more
#: exchanges it never came at all. So the server notices, as it counts words.
NAME_BY = 5

_NAME_NOW = ("- Вы говорите уже порядком, а ты так и не назвался. Назовись в этой "
             "реплике — к слову, между делом — и спроси, как зовут его.")


def stage(words: int) -> int:
    """0 strangers · 1 a little acquainted · 2 acquainted · 3 their own."""
    return sum(words >= at for at in KNOWN_AT)


def where(words: int, *, named: bool = True) -> str:
    """Where the two of them are — one line, every turn. `named`: he has said
    his own name to this person."""
    line = _WHERE[stage(words)]
    if stage(words) == 1 and not named:
        line += " Вы так и не назвались друг другу — самое время, между делом."
    return line


def block(words: int, *, named: bool = True, heard: int = 0) -> str:
    """How to meet somebody — only while they are still strangers. `heard`:
    how many times the person has spoken."""
    if stage(words) != 0:
        return ""
    return _FIRST if named or heard < NAME_BY else f"{_FIRST}\n{_NAME_NOW}"
