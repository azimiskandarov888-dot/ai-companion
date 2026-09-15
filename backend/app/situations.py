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


def block(user_text: str, history: list[dict] | None = None) -> str:
    """The rules this particular turn actually needs. Usually empty."""
    parts = []
    if _playing(user_text, history):
        parts.append(_GAMES)
    if brain.wants_fresh_info(user_text or ""):
        parts.append(_NEWS)
    return "\n\n".join(parts)
