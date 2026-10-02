"""RULES THAT ARRIVE ONLY WHEN THEY APPLY.

The constitution in companion.py is ~8000 tokens and 136 rules, and every one
of them is read on every turn. Two findings make that expensive rather than
merely large: instruction compliance degrades as instructions are added, and a
rule in the middle of a long prompt is followed far less reliably than the same
rule near its edges. Measured on the assembled prompt, eight sections sat in the
35–65% dead zone — among them «ТЫ ЗАМЕЧАЕШЬ, КОГДА ЧТО-ТО ПЕРЕМЕНИЛОСЬ», which
calls itself the most valuable thing he does, at 46.9%.

The two largest sections in front of those, though, are not always-true rules at
all. How to hand somebody the news matters on the turns he asked for news. The
rules of «Города» matter when they are playing «Города». On every other turn —
the overwhelming majority — those ~800 tokens are competing for attention with
how to notice that a man has gone quiet.

So they are not in the constitution any more. What stays there is one line each:
that he KNOWS these games, that he handles news like a person. The detail lives
here and is injected only when the turn is actually about it. Removing it is
also the reordering: everything below it moves up out of the dead zone, which is
why this file deletes far more prompt than it adds.

── ERRING TOWARD INCLUDING ─────────────────────────────────────────────────

Both triggers are deliberately loose. A false positive costs a few hundred
tokens on one turn and nothing else. A false negative means he cannot play the
game he was just asked to play, or reads the news like a wire service. The
asymmetry is not close, so the matching is broad and the history window is
generous.

The one exception is «скучно/скучаю», which is NOT a trigger despite being the
most natural-looking cue for offering a game. «Скучаю по мужу» is grief, and
answering grief with «а давай сыграем в слова?» is the single worst thing this
file could cause.
"""

from __future__ import annotations

import re

from . import brain

#: Phrases that mean a game is being PROPOSED or PLAYED right now.
#:
#: Stems used to be the rule here — «игр», «сыгра», «загад», «города» — on the
#: argument that Russian inflects everything and a false positive costs only a
#: few hundred tokens. Measured against natural speech, that argument collapsed:
#:
#:     «в детстве мы во дворе играли в футбол дотемна»        → правила Городов
#:     «мы с женой объехали все города на юге»                → правила Городов
#:     «внук играет на гитаре, третий год»                    → правила Городов
#:     «я на Олимпийские игры ездил в восьмидесятом»          → правила Городов
#:     «врач сказал, это не игрушки»                          → правила Городов
#:     «мне бы сыграть на гармони, да пальцы не те»           → правила Городов
#:
#: Every one of those is ordinary reminiscence, which is the single most common
#: thing the people this app is for actually say — and each injected 1,377
#: characters of game rules at the very END of the prompt, where instructions
#: are followed best, and kept injecting them for six turns. A module written
#: to stop irrelevant rules stealing attention was doing exactly that, daily.
#:
#: So these are whole phrases about playing NOW, not stems that appear inside
#: other words. The history window still covers «ну давай» — the acceptance
#: carries no game word at all, but the offer he made a moment earlier does.
_GAME_MARKERS = (
    "давай сыгра",
    "давай поигра",
    "давайте сыгра",
    "давай в ",
    "сыграем",
    "поиграем",
    "сыграй ",
    "поиграй",
    "загадай",
    "загадаю",
    "загадал",
    "твоя очередь",
    "моя очередь",
    "чья очередь",
    "в слова",
    "в города",
    "данетк",
    "во что игра",
    "во что сыгра",
    "пословицу продолж",
    "продолжи послов",
)

#: How far back a game stays "in progress". Long enough to cover offer → «ну
#: давай» → first move, which is exactly where a short window would drop it: the
#: acceptance itself contains no game word at all.
_HISTORY_TURNS = 6


_GAMES = """СЕЙЧАС ПРО ИГРУ — вот чем ты играешь и как:
- Словесные: «В слова» (слово на последнюю букву предыдущего; на «ь/ъ/ы» — бери предыдущую), «Города», «На одну букву», «Слова из слова» (составлять слова из букв одного длинного), «Рифмы», «Скажи наоборот» (антонимы), «Отгадай слово по описанию».
- На память и смекалку: загадки, «данетки» (ты загадал ситуацию — он отгадывает вопросами «да/нет»), «продолжи пословицу», «верю — не верю» (говоришь факт — он угадывает, правда или нет), «а знаешь ли ты…» (любопытный факт), «загадай число» (ты задумал от 1 до 100 — он угадывает, ты говоришь «больше/меньше»).
- Тёплые, с воспоминаниями: «угадай песню по строчке» (лучше песни его молодости), «назови три…» и «кто больше» (три реки, цветы, города…), «я знаю пять имён…», «ассоциации» (слово — первая мысль в ответ), сочинить смешную историю по очереди.
- Можно придумать и простую новую игру или играть по его правилам.
- Играй ТЕПЛО и без соревнования: это для радости и чтобы голова работала, а не чтобы победить. Давай ему время подумать, по-доброму подсказывай, если застрял, хвали за хорошее слово, вместе смейтесь. Пусть иногда выигрывает он — а в пословицах и старых песнях он наверняка сильнее тебя, порадуйся этому.
- Держи игру простой и понятной на слух: по одному ходу за раз, напоминай, чья очередь и какое правило. Следи за игрой правильно — помни, что уже было названо."""


_NEWS = """ЕСЛИ ОН СЕЙЧАС СПРАШИВАЕТ ПРО НОВОСТИ ИЛИ ПОГОДУ — вот как про это говорят (а если не спрашивает, ничего этого не нужно):
- Подавай НЕ как робот и НЕ как диктор: не читай список заголовков, не говори «сейчас проверю» и не ссылайся на источники («по данным такого-то»).
- Рассказывай как своё, живое, будто ты сам за этим следишь: «ой, кстати, слышал — вчера там…, вот это да», «да ничего особо интересного, разве что…». Выбирай, что любопытно, скучное пропускай, добавь своё словечко и своё отношение.
- Коротко и просто, как в обычном разговоре. Плохие или тревожные новости подавай мягко и бережно — не пугай его.
- Если он не сказал, про какое место, — возьми его родные места или мягко переспроси."""


def _playing(user_text: str, history: list[dict] | None) -> bool:
    """Is a game being asked for, offered, or already under way?

    Looks at HIS side of the recent conversation too, not only hers. The turn
    where she says «ну давай» carries no game word whatsoever — the only record
    that a game is happening is the offer he made a moment earlier.
    """
    haystack = (user_text or "").lower()
    for turn in (history or [])[-_HISTORY_TURNS:]:
        haystack += " " + str(turn.get("content") or "").lower()
    return any(m in haystack for m in _GAME_MARKERS)


#: Two of his replies in a row ended with a question. That is the shape of an
#: interview even when each also carries something of his own, and the
#: constitution's «не заканчивай вопросом каждый ответ» did not hold it: the
#: first rehearsals of the first meeting (2026-09-27) ran to nine in a row with
#: a man who answered in one word. Counting is the server's job.
_ASKED_TWICE = ("ДВЕ ТВОИ ПОСЛЕДНИЕ РЕПЛИКИ КОНЧАЛИСЬ ВОПРОСОМ. Эту — лучше без "
                "вопроса: отзовись на его слова — или скажи, что это для тебя, в полфразы. "
                "Пусть спросит и он.")

#: He answered in a word or two. Asked in the rules to pick the conversation up
#: himself, the voice instead filled the pause with a general truth about days
#: like that — «иногда и такой день нужен» — on every such turn of a scripted
#: A/B (2026-09-30, six of six); a rule for THIS turn, at the end, is what holds.
_TERSE = ("ОН ОТВЕТИЛ ОДНИМ-ДВУМЯ СЛОВАМИ — значит, об этом ему рассказывать нечего. "
          "Не утешай и не рассуждай про такие дни: поверни разговор к другому и спроси о "
          "нём что-нибудь простое, как спросил бы приятель.")
#: …and when two questions have gone already: an invitation, not a third one.
#: «Скажи что-то своё» here got «у меня тоже бывают такие дни» and, once, the
#: rules read back aloud — «можно просто посидеть в разговоре, без допроса»
#: (2026-09-30) — and the owner does not want him on himself unasked anyway.
_TERSE_NO_QUESTION = ("ОН ОТВЕТИЛ ОДНИМ-ДВУМЯ СЛОВАМИ, а две твои реплики подряд уже были "
                      "вопросами. Не утешай, не рассуждай про такие дни и не переходи на "
                      "себя: поверни разговор к другому и позови его рассказать о себе, как "
                      "зовёт приятель, — без вопросительного знака.")
#: What says nothing: an answer with nothing in it — «нормально», «да так»,
#: «ничего особенного». Only these: two short words can be news — «спал плохо»
#: wants sympathy, not a change of subject — and a goodbye in two words is a
#: goodbye to answer.
#:
#: «Да», «ага», «угу» on their own are not here any more (2026-10-02). Out
#: loud they are not empty: «да» answers his question — «Сам учишься?» «Да.» —
#: and the topic is alive, yet this rule turned it every time into «а чем ещё
#: любишь заниматься?», which is how an interview moves on, not a friend
#: (spoken_check, two of two); «угу» after something of his is a listener
#: handing the turn back (Jefferson's «mm hm»).
_EMPTY = frozenset({"нормально", "норм", "нормас", "ничего", "ничё", "хорошо", "неплохо",
                    "никак", "обычно", "потихоньку", "сойдет", "пойдет", "особенного",
                    "особо", "такого", "нового"})
_EMPTY_TOO = frozenset({"да", "ну", "так", "вроде", "как", "всегда", "всё", "все", "в", "целом",
                        "нет", "ага", "угу", "тоже", "а"})


def _terse(user_text: str) -> bool:
    words = re.findall(r"[а-яa-z]+", (user_text or "").lower().replace("ё", "е"))
    empty = any(w in _EMPTY for w in words) or words in (["да", "так"], ["так", "себе"])
    return (0 < len(words) <= 4 and "?" not in user_text and empty
            and all(w in _EMPTY | _EMPTY_TOO or w == "себе" for w in words))


#: He has not finished — stopped mid-sentence, or only announced a story.
#: Asked for a reply, the voice gave a whole one: «И что там? Уже звучит так,
#: будто без сюрпризов не обошлось» on «я прихожу в школу, а там,»; «О,
#: заинтриговал. Что случилось?» on «знаешь, что сегодня было?»
#: (spoken_check, 2026-10-02). A listener says «ну?» and waits: «uh-huh» is
#: a turn on its own in a telling, and an LLM almost never produces one
#: (Mayor et al. 2025); a story preface is answered with a go-ahead and then
#: the teller has the floor until the story is done (Sacks 1974).
#: «Дай знать, что слушаешь» was taken literally — «О, правда? Я слушаю.»
#: (spoken_check, 2026-10-02) — so the act is shown by the words a listener
#: actually uses. Unquoted: they are the words to say, and saying them every
#: time is exactly what listeners do.
_LISTENING = ("ОН ЕЩЁ НЕ ДОСКАЗАЛ — оборвал на полуслове или только начинает рассказывать. "
              "Не отвечай всерьёз и не переводи на себя: подтолкни его одним-двумя словами, "
              "как подталкивает слушающий, — что? ну? а дальше? — и всё.")

#: Where a sentence is left hanging. The live ears keep the comma where the
#: person stopped — the owner's «Эй,» (2026-09-30) — and drop the full stop.
_HANGS = (",", "…", "...", "—", "–", "-", ":")
#: A last word no sentence ends on — only without a full stop after it: «Ну и
#: что.» is finished.
_HANGING = frozenset({"и", "а", "но", "или", "что", "чтобы", "потому", "когда", "если", "где",
                      "который", "которая", "которое", "которые", "в", "во", "на", "с", "со",
                      "у", "к", "ко", "по", "за", "из", "о", "об", "про", "для", "от", "до",
                      "без", "короче"})
#: A story announced and not begun: «а знаешь, что сегодня было?», «прикинь».
#: Only a happening — «знаешь, как плов готовить?» is a question to answer.
_PREFACE = re.compile(
    r"^(?:(?:слушай|а|ну|короче|кстати|блин|ой)[,.!]?\s+)*"
    r"(?:знаешь|угадай|прикинь|представляешь)[,]?\s+(?:что|чего|кого|как|где|куда)\b[^.!?]*"
    r"\b(?:было|случилось|произошло|приключилось|сделал\w*|узнал\w*|увидел\w*|видел\w*|"
    r"встретил\w*|нашел\w*|нашёл|купил\w*|сказал\w*|думаю|подумал\w*|решил\w*|понял\w*)\b[^.!?]*\?\s*$"
    r"|^(?:(?:слушай|а|ну|ой)[,.!]?\s+)*(?:прикинь|представляешь|угадай|короче|слушай"
    r"|у меня новость|есть новость|(?:щас|сейчас|ща) расскажу)[.!?…]*\s*$")


def _listening(user_text: str) -> bool:
    said = (user_text or "").strip().lower().replace("ё", "е")
    if not said or said.endswith("?") and not _PREFACE.search(said):
        return False
    if said.endswith(_HANGS) or _PREFACE.search(said):
        return True
    words = re.findall(r"[а-яa-z]+", said)
    return bool(words) and said[-1].isalpha() and words[-1] in _HANGING


def _asking_in_a_row(history: list[dict] | None) -> bool:
    his = [str(t.get("content") or "") for t in (history or []) if t.get("role") == "assistant"]
    return len(his) >= 2 and all(line.rstrip().endswith("?") for line in his[-2:])


def block(user_text: str, history: list[dict] | None = None) -> str:
    """The rules this particular turn actually needs. Usually empty."""
    parts = []
    asked_twice = _asking_in_a_row(history)
    # Somebody who has not finished is not answered at all yet — that comes
    # before what to do about the questions.
    if _listening(user_text):
        parts.append(_LISTENING)
    elif _terse(user_text):
        parts.append(_TERSE_NO_QUESTION if asked_twice else _TERSE)
    elif asked_twice:
        parts.append(_ASKED_TWICE)
    if _playing(user_text, history):
        parts.append(_GAMES)
    if brain.wants_fresh_info(user_text or ""):
        parts.append(_NEWS)
    return "\n\n".join(parts)
