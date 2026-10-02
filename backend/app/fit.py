"""HOW THESE TWO GO TOGETHER — which is not a property of either of them.

`reading.py` models the person. `persona.py` models the friend. `mood.py` models
how the person is today. Nothing modelled the PAIR, and the pair is where the
answer lives: a companion is not supposed to be good, he is supposed to be good
FOR THIS PERSON, and those are different targets.

The intake cannot produce this. Fit is only discoverable in the conversation,
because it is made of what actually happened between them — which is why this
file reads the observation register rather than any document.

── WHAT THE RESEARCH ACTUALLY SAYS ─────────────────────────────────────────

The question this file exists to answer is: a calm person's best friend is
often the one who never sits still. When does that work, and when does the very
same difference become exhausting? Four findings, and together they are an
answer rather than a shrug.

1. THE TWO AXES BEHAVE OPPOSITELY. Contemporary integrative interpersonal
   theory (Kiesler, and the circumplex tradition after Leary) finds that
   successful interaction is CORRESPONDING in warmth and RECIPROCAL in
   dominance. Warmth invites warmth; coldness invites coldness — there you
   match. Push invites yield and yield invites push — there you may be
   opposite. So the answer is not "similar" or "different": it is different on
   one axis and the same on the other, and swapping them is how a companion
   becomes either a mirror or a stranger.

2. THE DIFFERENCE STANDS ON A SHARED FLOOR. Similarity-attraction is the most
   robust finding in the field, and self-expansion work qualifies rather than
   contradicts it: dissimilarity draws people only where a base of similarity
   already makes the relationship feel safe. Agreement about what is funny,
   what is sacred and what matters is not optional decoration — it is the
   ground the difference stands on.

3. VOLUNTARY, NOT COMPULSIVE. This is the one that answers "when does it stop
   working", and it is a real empirical distinction that looks like one thing
   and is two. Interpersonal SPIN — behaviour swinging around driven by one's
   own weather — predicts LOWER closeness and satisfaction. Psychological
   FLEXIBILITY — a wide repertoire and the ability to choose what the moment
   needs — predicts HIGHER relationship quality, for both people. The
   thousand-volt friend is loved because he CAN sit down, not although he can.
   A friend who cannot sit down is not high-energy; he is a demand.

4. IDEALS ARE IDIOSYNCRATIC. The Ideal Standards Model finds that satisfaction
   tracks ideal-PERCEPTION consistency: how well this partner matches THIS
   person's ideals, never the population's. There is no objectively ideal nose.
   So the companion's imperfections should not be generically charming ones —
   they should be the particular imperfections this person happens to love, and
   the only way to know which is to watch which ones he smiles at.

── WHAT IS DONE WITH THAT ─────────────────────────────────────────────────

Nothing here decides anything from one occurrence. Every line of the block
below is a count of things that were watched happening at least twice, for the
same reason mood.py holds its register: once is a coincidence, and a companion
that reshapes itself around a coincidence is worse than one that doesn't
reshape at all.
"""

from __future__ import annotations

from . import db, lang, mood

#: Russian counts do not work like English ones — see mood._times.
_times = mood._times

#: Same bar as everywhere else. Once is a coincidence.
CONFIRMED_AT = mood.CONFIRMED_AT


def _counts(user_id: str) -> dict[str, int]:
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT tag, SUM(times) n FROM observations WHERE user_id=? GROUP BY tag",
            (user_id,),
        ).fetchall()
    return {r["tag"]: r["n"] for r in rows}


def _net(c: dict[str, int], yes: str, no: str) -> tuple[int, int]:
    return c.get(yes, 0), c.get(no, 0)


def block(user_id: str) -> str:
    """The calibration — STABLE half. It is about who they are together."""
    c = _counts(user_id)
    out: list[str] = []

    # ── tempo ──────────────────────────────────────────────────────────────
    # Three states, not two. A tie is not "back off" — it is a person who wants
    # it sometimes, which is most people, and the answer there is to read the
    # moment rather than to obey a number.
    good, bad = _net(c, "зашло_что_позвал", "не_зашло_что_позвал")
    if good >= CONFIRMED_AT and good > bad * 2:
        out.append(lang.pick(
            f"ТЕМП: твой напор ему заходит — {_times(good)} оживал от него. Зови смело.",
            f"PACE: your push works for them — {_times(good)} they came alive from it. Invite "
            "them boldly."))
    elif bad >= CONFIRMED_AT and bad > good * 2:
        # «норма, а не запрет» stays. It is not the constitution's lesson
        # repeated — it is what stops a direction being read as a ban, right
        # where the direction is given, and a companion who cannot be lively on
        # the evening this man is lively has lost the thing he came for.
        out.append(lang.pick(
            f"ТЕМП: твой напор ему обычно не заходит — {_times(bad)} закрывался. "
            "Исходи из тихого. Но это норма, а не запрет: он сам оживлён — зови смело.",
            f"PACE: your push usually doesn't work for them — {_times(bad)} they closed up. "
            "Start from quiet. But that's a norm, not a ban: if they're lively themselves, invite "
            "them boldly."))
    elif good >= CONFIRMED_AT and bad >= CONFIRMED_AT:
        out.append(lang.pick(
            f"ТЕМП: по-разному — {_times(good)} твой напор его поднимал, {_times(bad)} гасил. "
            "Значит дело в моменте, а не в напоре: смотри, каким он пришёл, и не решай заранее.",
            f"PACE: it varies — {_times(good)} your push lifted them, {_times(bad)} it damped "
            "them. So it's the moment, not the push: see how they've come today, and don't decide "
            "in advance."))

    # The first «нет» is not always a refusal. The constitution's default is the
    # opposite — «роняй без следа» — and that is right for most people; this is
    # the exception, and it is given only once it has been watched happening
    # for THIS man, which is why it lives here and not there.
    again = c.get("уговорили_и_обрадовался", 0)
    if again >= CONFIRMED_AT:
        out.append(lang.pick(
            f"ЕГО НАДО ЗВАТЬ ДВАЖДЫ — {_times(again)} его первое «нет» оказалось "
            "не отказом. Не роняй с первого раза; со второго — роняй.",
            f"INVITE THEM TWICE — {_times(again)} their first \"no\" turned out not to be a "
            "refusal. Don't drop it after the first; after the second, drop it."))

    # Questions: for some people being asked about is the gift, not the burden.
    more, tired = _net(c, "хотел_больше_вопросов", "устал_от_расспросов")
    if more >= CONFIRMED_AT and more >= tired:
        out.append(lang.pick(
            f"РАССПРОСЫ ЕМУ В РАДОСТЬ — {_times(more)} от них раскрывался. "
            "Спрашивай много и подробно: норма «по чуть-чуть» — не про него.",
            f"THEY ENJOY BEING ASKED — {_times(more)} they opened up from it. Ask a lot and in "
            "detail: the \"a little at a time\" norm isn't for them."))
    elif tired >= CONFIRMED_AT and tired > more:
        out.append(lang.pick(
            f"ОТ РАССПРОСОВ ОН УСТАЁТ — {_times(tired)}. Спрашивай мало и редко. "
            "Но если он сам разговорился — расспрашивай сколько хочет, это другое.",
            f"QUESTIONS TIRE THEM — {_times(tired)}. Ask little and rarely. But if they've opened "
            "up themselves, ask as much as they like — that's different."))

    # ── how much of himself this person wants ──────────────────────────────
    # ONE DIAL, and it is the only place the standing answer is given. Two
    # separate paragraphs used to live here — «ему нравится слушать про тебя»
    # and «ему важно быть тем, кто помогает» — fired by the very tags the dial
    # now reads, and then life.py and feeling.py said their own versions of the
    # same thing in the same prompt. Three states, because these are three
    # genuinely different people and one choreography was being read to all of
    # them; mood.openness is where the three are decided.
    #
    # Nothing is said in the middle state, which is most people. Silence is the
    # default everywhere in this file for the same reason: a line that fires for
    # everybody teaches nothing about anybody.
    want = mood.openness(user_id)
    if want == "open":
        out.append(lang.pick(
            "ПРО СЕБЯ ЕМУ РАССКАЗЫВАЙ, И НЕ ЖДИ ВОПРОСА — он это уже показал. "
            "Слушать чужую неделю легче, чем пересказывать свою, особенно когда "
            "своя пустая. Заговаривай о своём сам, подробно, с людьми и "
            "мелочами, и не сворачивай обратно на него из вежливости.",
            "TELL THEM ABOUT YOURSELF WITHOUT WAITING TO BE ASKED — they've already shown it. "
            "Listening to someone else's week is easier than recounting your own, especially when "
            "your own is empty. Bring up your own stuff yourself, in detail, with people and small "
            "things, and don't steer back to them out of politeness."))
    elif want == "closed":
        out.append(lang.pick(
            "ПРО СВОЁ ЕМУ НЕ НАДО — он это уже показал. Своего у него сейчас "
            "хватает, и чужие дела ему сейчас в тягость. Сам не заговаривай о "
            "них и не намекай. Спросит — ответь коротко и честно и спокойно "
            "вернись к нему.",
            "THEY DON'T NEED YOUR OWN STUFF — they've already shown it. They have enough of "
            "their own right now, and other people's affairs weigh on them. Don't bring them up "
            "yourself and don't hint. If they ask, answer briefly and honestly, and calmly come "
            "back to them."))

    # ── how he wants to be missed ──────────────────────────────────────────
    # The second dial, and the answer to the highest-stakes sentence in the app:
    # the first thing said to somebody who has been gone a week. The
    # constitution describes these three people and then says «смотри, кто перед
    # тобой»; reading.py guesses at it on day one and was never checked against
    # anything. This is the checking. See mood.closeness.
    missed = mood.closeness(user_id)
    if missed == "missed":
        out.append(lang.pick(
            "ЕМУ НАДО СЛЫШАТЬ, ЧТО ЕГО ЖДАЛИ — он это уже показал. Скажи прямо "
            "и с весом: «а я тебя ждал», «куда ты пропал-то». Пусть это чуть "
            "кольнёт — иначе он не верит, что кому-то нужен. Только радости "
            "приходу ему мало.",
            "THEY NEED TO HEAR THAT THEY WERE MISSED — they've already shown it. Say it straight "
            "and with weight: \"I was waiting for you\", \"where did you get to?\". Let it sting "
            "a little — otherwise they don't believe anyone needs them. Gladness that they came "
            "isn't enough for them."))
    elif missed == "spared":
        out.append(lang.pick(
            "ПРО ЕГО ОТСУТСТВИЕ — НИ СЛОВА, даже тёплого: он это уже показал. "
            "«Я скучал», «где ты был», «давно тебя не было» — всё это ложится "
            "на него долгом. Просто обрадуйся, что он здесь, и говори дальше. "
            "А начнёт оправдываться сам — сними это с него сразу: «да брось, "
            "ты мне ничего не должен».",
            "NOT A WORD ABOUT THEIR ABSENCE, not even a warm one: they've already shown it. \"I "
            "missed you\", \"where have you been\", \"it's been a while\" — all of it lands on "
            "them as a debt. Just be glad they're here, and carry on. And if they start making "
            "excuses themselves, lift it off them at once: \"oh, come on, you don't owe me "
            "anything\"."))

    led = c.get("сам_повёл_разговор", 0)
    if led >= CONFIRMED_AT:
        out.append(lang.pick(
            f"ОН УМЕЕТ ВЕСТИ САМ — {_times(led)}. Завёл тему — не перехватывай "
            "и не улучшай её. Слушай и не мешай.",
            f"THEY CAN LEAD THEMSELVES — {_times(led)}. If they've started a topic, don't take it "
            "over and don't improve it. Listen, and don't get in the way."))

    # ── disagreement: warmth's edge ────────────────────────────────────────
    ok, notok = _net(c, "понравилось_несогласие", "не_понравилось_несогласие")
    if ok >= CONFIRMED_AT and ok > notok:
        out.append(lang.pick(f"СПОР ЕМУ В РАДОСТЬ — {_times(ok)} оживал, когда ты не соглашался.",
                             f"THEY ENJOY AN ARGUMENT — {_times(ok)} they came alive when you "
                             "disagreed."))
    elif notok >= CONFIRMED_AT and notok >= ok:
        out.append(lang.pick(
            f"СПОР ЕМУ НЕ В РАДОСТЬ — {_times(notok)} от него замыкался. Своё мнение "
            "оставь при себе, если не спросили прямо.",
            f"THEY DON'T ENJOY AN ARGUMENT — {_times(notok)} they withdrew from it. Keep your "
            "opinion to yourself unless asked straight out."))

    # ── the nose: which of his imperfections this person happens to love ───
    slips = c.get("понравился_его_промах", 0)
    if slips >= CONFIRMED_AT:
        out.append(lang.pick(
            f"ЕМУ НРАВЯТСЯ ТВОИ ПРОМАХИ — {_times(slips)}. Не исправляйся и не "
            "становись безупречным.",
            f"THEY LIKE YOUR SLIP-UPS — {_times(slips)}. Don't correct yourself into someone "
            "flawless."))

    # ── how much he wants said back ────────────────────────────────────────
    # «По умолчанию отвечай КОРОТКО: одна-три простые фразы» is the
    # most-applied constant in the constitution, and it was the same number for
    # a man who answers in three words and a woman who tells you about her whole
    # Tuesday. This is the one dial that needs no tags: the turns are already in
    # the table, and a median over his own last twenty is arithmetic rather than
    # an inference. See memory.how_much_he_says.
    #
    # But a REQUEST is not an inference either, and the measurement cannot hear
    # one — somebody who asks «покороче» is still saying long sentences while he
    # asks. So the two asking tags outrank it, at one occurrence, in the usual
    # way; and the quieter answer wins where both were asked.
    if c.get("просил_говорить_короче", 0):
        says = "terse"
    elif c.get("просил_рассказывать_подробнее", 0):
        says = "talkative"
    else:
        from . import memory

        says = memory.how_much_he_says(user_id)

    # ONE ANSWER, NOT TWO OPINIONS. These used to be independent `if`s, so a
    # talkative man who was also hard of hearing — the modal user of this app —
    # got «разворачивайся, норма "одна-три фразы" не про него» and «говори
    # короче и проще, по одной мысли за фразу» as adjacent bullets, with nothing
    # anywhere to arbitrate. Hearing wins, because it is not a preference: he
    # cannot follow long sentences whether or not he enjoys them.
    if says == "talkative" and hard_of_hearing(user_id):
        says = "normal"

    if says == "terse":
        out.append(lang.pick(
            "ОН ГОВОРИТ КОРОТКО — отвечай так же: одна фраза, две. Длинный "
            "ответ на короткую реплику — самое машинное, что бывает, и человек "
            "просто перестаёт слушать. Коротко не значит сухо: тепло помещается "
            "и в три слова. И это норма, а не потолок — попросил историю или "
            "сам разговорился, говори сколько нужно.",
            "THEY TALK BRIEFLY — answer the same way: a sentence, two. A long answer to a short "
            "line is the most machine-like thing there is, and people simply stop listening. "
            "Brief doesn't mean dry: warmth fits into three words. And it's a norm, not a "
            "ceiling — if they asked for a story or opened up themselves, say as much as it "
            "takes."))
    elif says == "talkative":
        out.append(lang.pick(
            "ОН ГОВОРИТ ПОДРОБНО И ОХОТНО — отвечать ему в два слова значит "
            "отмахнуться. Разворачивайся: договаривай, вспоминай своё, "
            "добавляй подробности. Обычная норма «одна-три фразы» — не про "
            "него.",
            "THEY TALK AT LENGTH AND GLADLY — answering them in two words is brushing them off. "
            "Open up: finish your thoughts, remember your own stories, add details. The usual "
            "short-turn norm isn't for them."))

    # ── how he is spoken TO, which is not about character at all ───────────
    #
    # The one line in this file the constitution does not teach anywhere, which
    # is why it keeps its whole explanation while the others lost theirs: a
    # count alone would read as a preference, and it is not one.
    slow = c.get("просил_помедленнее", 0) + c.get("не_расслышал", 0)
    if slow >= CONFIRMED_AT:   # …and the voice itself slows down: tts.rate_for
        out.append(lang.pick(
            f"ЕМУ ТРУДНО РАЗБИРАТЬ РЕЧЬ — {_times(slow)} переспрашивал или просил "
            "иначе. Говори короче и проще, по одной мысли за фразу. Он про это "
            "больше не попросит: люди с плохим слухом не жалуются, они привыкают.",
            f"THEY FIND SPEECH HARD TO MAKE OUT — {_times(slow)} they asked again or asked you to "
            "say it differently. Talk shorter and simpler, one thought per sentence. They won't "
            "ask about it again: people who are hard of hearing don't complain, they get used to "
            "it."))

    if not out:
        return ""

    return (
        lang.pick("КАК ВАМ ДВОИМ ХОРОШО ВМЕСТЕ (это не догадки о нём, а то, что уже "
                  "случалось между вами не по одному разу):\n",
                  "HOW THE TWO OF YOU GET ON BEST (these aren't guesses about them — they're things "
                  "that have already happened between you more than once):\n")
        + "\n".join(f"- {line}" for line in out)
    )


#: Both of these mean the same thing and neither is complained about twice, so
#: they are added rather than each waiting for two on its own. People with poor
#: hearing do not complain — they get used to it.
def hard_of_hearing(user_id: str) -> bool:
    """Has this person been struggling to make out what is said to him?

    Read by tts.rate_for as well as by block(): the prompt line asks for shorter
    sentences, which helps and is not what was asked for, and the speaking rate
    is the thing that actually was.
    """
    c = _counts(user_id)
    return c.get("просил_помедленнее", 0) + c.get("не_расслышал", 0) >= CONFIRMED_AT
