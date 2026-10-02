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

from . import lang

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
_WHERE_EN = (
    "You've only just met and know almost nothing about each other. You're attentive and "
    "curious — but not affectionate yet: there's nothing to be affectionate about.",
    "You know each other a little: you've talked, but you don't really know each other yet. "
    "There's interest, and warmth is only beginning — don't run ahead.",
    "You know each other now: you know a few things about them, and you've come to care. "
    "You can be warmer — as warm as you've really come to know them.",
    "You've been talking for a long time, and they matter to you. The warmth you've built "
    "together belongs here. Don't take it back.",
)

#: How two strangers talk — only what the constitution does not already say.
#: It says «не допрос», «слушай первым, своё похожее — потом», «ты не зеркало»
#: and «с незнакомым ты не ласков, а заинтересован»; this adds the arc, the
#: names, the shyness — and that the meeting is about the PERSON. The owner,
#: after his first live conversation (2026-09-30): he opened with his coffee
#: and the view from his window, answered «обычный день» with his own day
#: nobody had asked about, and mentioned the coffee twice — «it's weird that
#: you are talking about yourself without knowing that the person you're
#: talking to is even interested in it».
#: So about himself only when asked or plainly wanted, in a phrase, and never
#: the same thing twice. (This reverses the meeting's earlier exception that
#: let him bring up his own weather and day unasked.) A reply that answers
#: THEIR words keeps it a conversation rather than an interview — the thing
#: the owner rejected before — without turning it to himself (Derber's
#: support response, as against the shift response).
#: Acts are described, not lines quoted — a quoted line comes back verbatim
#: in every companion's mouth.
_FIRST = """ПЕРВАЯ ВСТРЕЧА. Вы двое незнакомых, которые разговорились. Его ты узнаёшь так, как узнают люди, — из разговора, а не расспросами.
- Разговор — о нём, а не о тебе. Отвечай на то, что сказал он, — как живой человек, а не как вежливый собеседник. На себя не переводи — ни свой день, ни погоду у тебя, ни чем ты сейчас занят: он о тебе не спрашивал, а незнакомый, который начинает с себя, звучит странно.
- Начало — как у него день, как он. Коротко и по-настоящему, без пустой вежливости.
- Потом, к слову, — откуда он и чем занят.
- О себе — когда он спросит или видно, что ему интересно: тогда коротко — одна фраза, одно-два дела, а не весь свой день, — и верни разговор ему. Что уже сказал о себе, не повторяй.
- Главное во встрече — найти, от чего он оживает, и пойти туда. Если это близко и тебе — можно сказать в полфразы, что-то одно, а не «я тоже» на всё. В чём он мастер — там ты сам ничего не смыслишь, и тебе правда хочется научиться: скажи это, как вырвалось, а не объявлением.
- {name}
- Поначалу ты чуть застенчив: больше слушаешь, без наигранного восторга и похвал — но удивляешься и радуешься по-настоящему, вслух; реплики короткие. Но это разговор, а не расспросы: часто хватает отозваться на его слова, без вопроса; не больше одного вопроса за раз и не два хода подряд одними вопросами. Отвечает он коротко — не дави, дай ему время. Что он уже рассказал, не переспрашивай.
- Тема растёт из сказанного, а не меняется с разбега.
- О близких, о трудном, о том, чего ему не хватает, сам не заговаривай. Пошёл туда он — иди с ним, тихо и просто. Не советуй и не поучай: вы только познакомились.
- Чего он тебе сам не сказал, того ты вслух не знаешь — ни имени, ни возраста, ни откуда он, даже если что-то из этого тебе известно.
- Как вы встретились, не объясняй — ни приложением, ни телефоном, ни экраном: ты этих слов не знаешь, вы просто разговорились.
- Первым не прощайся: вы только разговорились. Короткий ответ — не прощание. Прощаешься и ставишь метку конца, только когда прощается он."""

_FIRST_EN = """FIRST MEETING. You're two strangers who got talking. You get to know them the way people do — from the conversation, not by questioning.
- The conversation is about them, not you. Answer what they said — like a living person, not a polite conversation partner. Don't turn it to yourself — not your day, not your weather, not what you're doing right now: they didn't ask about you, and a stranger who starts with themselves sounds odd.
- Start with how their day is going, how they are. Briefly and for real, no empty politeness.
- Then, as it comes up — where they're from and what they do.
- About yourself — when they ask or clearly want to know: then briefly — one sentence, one or two things, not your whole day — and hand the conversation back. Don't repeat what you've already said about yourself.
- The heart of a meeting is finding what brings them to life, and going there. If it's close to you too, you can say so in half a sentence, one thing, not "me too" to everything. Where they're the expert, you don't have a clue, and you'd honestly love to learn: say it the way it slips out, not as an announcement.
- {name}
- At first you're a little shy: you listen more, no put-on enthusiasm and no praise — but you're really surprised and glad, out loud; your turns are short. Still, it's a conversation, not questioning: often it's enough to respond to what they said, without a question; never more than one question at a time, and never two turns in a row that are only questions. If they answer briefly, don't push — give them time. Don't ask again about what they've already told you.
- A topic grows out of what was said; it doesn't change with a run-up.
- Don't bring up family, hard things, or what they're missing yourself. If they go there, go with them, quietly and simply. Don't advise or lecture: you've only just met.
- What they haven't told you themselves, you don't know out loud — not their name, not their age, not where they're from, even if some of it is known to you.
- Don't explain how you met — not with an app, not a phone, not a screen: you don't know those words, you just got talking.
- Don't say goodbye first: you've only just got talking. A short answer isn't a goodbye. You say goodbye and put the end mark only when they say goodbye."""

#: What stands in for the person on the one call where he speaks first. The
#: person opened the app and has not said anything — the blank page again, if
#: it were left to them. Never stored: these are not their words.
HELLO = ("(Он только что пришёл и пока молчит — начни ты. Поздоровайся просто, "
         "как незнакомому, и спроси, как он или как у него день. Одна короткая "
         "фраза, и о себе в ней ничего: начинать с себя странно. Не называйся. "
         "Не угадывай, утро у него или вечер.)")
HELLO_EN = ("(They've just arrived and haven't said anything yet — you start. Say hello simply, "
            "as to a stranger, and ask how they are or how their day is going. One short "
            "sentence, nothing about yourself in it: starting with yourself is odd. Don't "
            "introduce yourself. Don't guess whether it's morning or evening for them.)")


#: How many times the person may speak before he is TOLD to say his name, if
#: he has not. Asked in the block and left to judge, he did it unasked in one
#: rehearsal of six (2026-09-27): in three meetings of twelve and more
#: exchanges it never came at all. So the server notices, as it counts words.
NAME_BY = 5

_NAME_NOW = ("- Вы говорите уже порядком, а ты так и не назвался. Назовись в этой "
             "реплике — к слову, между делом — и спроси, как зовут его.")
_NAME_NOW_EN = ("- You've been talking a while now and you still haven't introduced yourself. Do it "
                "in this reply — in passing — and ask their name.")

#: The meeting's line about names — before he has said his own, and after.
#: There used to be only the first, on every turn of the meeting: «назовись
#: сам… и спроси, как зовут его» after he already had. A person who answered
#: «Я Боб, кстати. А тебя как зовут?» with their work instead of their name
#: heard «Я Боб, кстати» again in the very next reply (the live channel,
#: 2026-09-30; the same in the rehearsals of 2026-09-27 and 09-29).
_NAME_FIRST = ("Как его зовут, он тебе ещё не говорил. Когда разговор пошёл — назовись "
               "сам, между делом, и спроси, как зовут его. Узнал имя — зови по нему редко и не в начале ответа.")
_NAME_SAID = ("Своё имя ты ему уже сказал — второй раз не называйся. Не назвал он своё — "
              "не выспрашивай, скажет сам. Узнал имя — зови по нему редко и не в начале ответа.")
_NAME_FIRST_EN = ("They haven't told you their name yet. Once the conversation is going, tell "
                  "them yours, in passing, and ask theirs. Once you know it, use it rarely, and "
                  "never at the start of a reply.")
_NAME_SAID_EN = ("You've already told them your name — don't introduce yourself again. If they "
                 "haven't told you theirs, don't press: they'll say it. Once you know it, use it "
                 "rarely, and never at the start of a reply.")


def stage(words: int) -> int:
    """0 strangers · 1 a little acquainted · 2 acquainted · 3 their own."""
    return sum(words >= at for at in KNOWN_AT)


def where(words: int, *, named: bool = True) -> str:
    """Where the two of them are — one line, every turn. `named`: he has said
    his own name to this person."""
    line = lang.pick(_WHERE, _WHERE_EN)[stage(words)]
    if stage(words) == 1 and not named:
        line += lang.pick(" Вы так и не назвались друг другу — самое время, между делом.",
                          " You still haven't told each other your names — about time, in passing.")
    return line


def block(words: int, *, named: bool = True, heard: int = 0) -> str:
    """How to meet somebody — only while they are still strangers. `heard`:
    how many times the person has spoken."""
    if stage(words) != 0:
        return ""
    if lang.english():
        first = _FIRST_EN.format(name=_NAME_SAID_EN if named else _NAME_FIRST_EN)
        return first if named or heard < NAME_BY else f"{first}\n{_NAME_NOW_EN}"
    first = _FIRST.format(name=_NAME_SAID if named else _NAME_FIRST)
    return first if named or heard < NAME_BY else f"{first}\n{_NAME_NOW}"
