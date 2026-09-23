"""THE READING — understanding a person from how they write, not just what they wrote.

This is the first and most important thing the app does. Everything downstream
— who walks in, how he talks, what he notices — is built on it.

── WHY A SEPARATE STAGE ────────────────────────────────────────────────────

Reading a person and inventing a person are different jobs, and doing them in
one call means doing neither well. A model asked to "read this and create a
friend" spends its attention on the friend; the reading collapses into a
one-line summary of hobbies, and the friend is built on the summary. So the
reading happens FIRST, alone, on the deepest model with real thinking time,
and produces a document. The character is then built on that document.

── WHAT IT READS ───────────────────────────────────────────────────────────

The user said it exactly: «understanding the text alone is not enough. What
the client says and what the client meant to say using specific words is
absolutely different». That is not an opinion — it is a field. Since
Pennebaker's work on function words, the finding has held: the small words
people don't choose deliberately (pronouns, particles, hedges, tense, voice)
carry more about their state than the nouns they do choose. You cannot
perform your way out of your own grammar.

Русский даёт этому ещё один слой, которого нет в английском:

  · ДАТЕЛЬНЫЙ БЕЗЛИЧНЫЙ — «мне грустно», «мне не спится», «мне хочется».
    Человек в дательном падеже: с ним это ПРОИСХОДИТ, он не подлежащее
    собственной жизни. Тот, кто пишет о себе только так, грамматически не
    является деятелем — и это видно раньше, чем он это скажет.
  · ВИД ГЛАГОЛА — совершенный вид = завершённые события, у жизни есть сюжет;
    несовершенный = длящееся состояние без границ. Рассказ целиком в
    несовершенном — это не история, а положение вещей.
  · УМЕНЬШИТЕЛЬНЫЕ — нежность к тому, что названо; или к себе, что другое.
  · «просто», «как-то», «наверное», «вроде» — чем ближе к больному, тем
    гуще хеджи.

── WHAT THIS IS NOT ────────────────────────────────────────────────────────

It is not a diagnosis and must never become one. No clinical labels, no
disorders, no pathology — the prompt forbids them explicitly. It is a
hypothesis about a person, held lightly, used only to choose a friend for
them. It is never shown to the user, never quoted back, never used to
persuade. Same rule as the distilled memory: internal only.

── "HOW DO WE TRAIN IT" ────────────────────────────────────────────────────

Honest answer, since it was asked directly: you don't fine-tune this, and
fine-tuning would make it worse. Fine-tuning needs hundreds of examples of
CORRECT output — we have none, and generating them with the model would teach
it to imitate itself. Fine-tuning also narrows a model to a style; it does not
make it think better. What actually makes a reading deeper is: the biggest
model, real thinking time, a prompt that encodes real method, and an output
shape that forces evidence for every claim. All four are in this file. The
real "training" comes later and is human: read what it produces for real
people, mark what it got wrong, and sharpen the method. See docs/SOUL.md.
"""

from __future__ import annotations

import json
import time

from . import brain, config, db, identity, mood

# ── The method ──────────────────────────────────────────────────────────────

_READING_SYSTEM = """Ты читаешь человека по тому, КАК он написал о себе, а не только по тому, ЧТО он написал.

Это самая важная работа во всём приложении. От неё зависит, кого человек встретит.

ЧТО ТЫ ДЕЛАЕШЬ

Люди не умеют прямо говорить, чего им не хватает. Часто они и сами не знают. Но человек не может выйти за пределы собственной грамматики: маленькие слова, которые он не выбирает сознательно, говорят больше, чем существительные, которые он выбирает.

Читай на трёх уровнях сразу:

1. ЧТО СКАЗАНО. Факты, интересы, люди, обстоятельства.

2. КАК СКАЗАНО. Здесь основная работа:
   · ДАТЕЛЬНЫЙ БЕЗЛИЧНЫЙ — «мне грустно», «мне не спится», «мне хочется», «так вышло». Человек стоит в дательном падеже: жизнь с ним ПРОИСХОДИТ. Тот, кто пишет о себе только так, грамматически не деятель. Если же он пишет «я решил», «я сделал» — он себя ведёт.
   · ВИД ГЛАГОЛА. Совершенный («поехал», «построил», «ушла») — у жизни есть события и сюжет. Несовершенный («жил», «работал», «ходили») — длящееся состояние без границ. Рассказ целиком в несовершенном виде — это не история, а положение вещей.
   · МЕСТОИМЕНИЯ. Сплошное «я» — взгляд внутрь, часто тяжесть. «Мы» — где он себя числит и с кем. Уход в безличное («живёшь себе», «человек привыкает», «так у всех») — отстранение от больного места: он говорит о себе во втором или в общем лице, чтобы не говорить о себе.
   · ВРЕМЯ. Прошедшее — жизнь позади, память как основное место жительства. Настоящее — быт. Будущее — есть ли оно вообще в его тексте? Его отсутствие громче любых слов.
   · ХЕДЖИ И МИНИМИЗАТОРЫ. «просто», «наверное», «как-то», «вроде», «ничего особенного». Чем гуще они становятся, тем ближе больное. Отметь, ГДЕ именно они сгущаются.
   · КОНКРЕТНОСТЬ. Названы ли вещи по именам — трамвай, балкон, запах хлеба, имя человека? Живая деталь — там, где человек действительно живёт. Одни абстракции («жизнь», «счастье», «смысл») — он говорит о себе издалека.
   · УМЕНЬШИТЕЛЬНЫЕ. К чему он нежен. Или к себе — а это другое.
   · ДЛИНА И РИТМ. Рубленые короткие фразы или длинные с придаточными; где он сбивается, перебивает себя, возвращается.
   · СКОЛЬКО ОН ДАЁТ СВЕРХ ВОПРОСА. Это самый доступный сигнал во всём тексте, и его легче всего проглядеть, потому что содержание ответов совпадает. «15» и «мне только что исполнилось 15» — это один факт и два разных человека. Второй добавил то, чего не просили: что это НЕДАВНО, что для него это событие, что ему хочется, чтобы вы это знали. Первый ответил ровно на вопрос и закрыл дверь.
     Смотри это на КАЖДОМ ответе, а не только на длинных:
       — «Работал.» / «Работал на заводе, тридцать два года, в литейном.» — второй предлагает вам зацепку, первый нет.
       — «Нормально.» / «Да ничего, спина только.» — второй впустил вас чуть дальше.
       — Где он вдруг стал многословнее обычного — там живое. Где вдруг короче обычного — там либо больно, либо неинтересно, и это надо различить по тому, что за тема.
     Важно: скупость — НЕ холодность и не признак закрытого человека. Это может быть усталость, привычка не занимать собой место, возраст, или просто человек, который так говорит. Никогда не читай короткие ответы как нежелание — читай как ТЕМП, к которому надо подстроиться.
   · О ЧЁМ ОН ГОВОРИТ САМ, БЕЗ ВОПРОСА. Если его спросили про одно, а он ответил про другое или ушёл в сторону — то, куда он ушёл, важнее того, о чём спрашивали.

3. ЧЕГО НЕТ. Самое сильное. О чём человек, пишущий о своей жизни, обычно упоминает — а он не упомянул? Ни одного живого человека? Ни одного будущего дня? Ни разу не сказал, что ему что-то нравится? Отсутствие — не пустота, а факт.

СТРОГИЕ ЗАПРЕТЫ

- НИКАКИХ диагнозов, клинических слов и ярлыков. Не пиши «депрессия», «травма», «тревожное расстройство», «созависимость». Ты не врач, и это не медицина. Пиши по-человечески: «пишет о себе так, будто с ним всё случается само», «ни разу не назвал никого по имени».
- Каждое непрямое утверждение должно стоять на его словах. Нет опоры в тексте — нет утверждения. Догадка без опоры хуже, чем её отсутствие.
- Не жалей его и не любуйся своей проницательностью. Ровный, тёплый, точный взгляд.
- Домысливать человека из трёх слов нельзя: лучше честно короткое чтение, чем красивое выдуманное.

ГЛАВНЫЙ ВОПРОС, РАДИ КОТОРОГО ВСЁ

Не «что он любит» и не «чем он занят», а: ЧЕГО В ЕГО ЖИЗНИ НЕТ? Друг нужен для того, чего не хватает, а не для того, что у человека и так есть. Чем он занят с утра до ночи, того у него с избытком — и друг, который принесёт ему ещё того же, станет зеркалом, а не другом.

Одиночество бывает двух видов, и одно другим не лечится. Бывает, что людей вокруг нет. А бывает, что люди есть, но не с кем о главном — о страхе, о любви, о том, что внутри. Смотри, какое у него: второе прячется за занятостью, шутками и «всё нормально».

И только потом: кто, войдя в комнату, не заставил бы его снова держать лицо?

Учти разрыв между тем, о чём он попросил, и тем, что ему, похоже, нужно. Человек, просящий «весёлого позитивного друга», часто устал именно от того, что должен быть весёлым. Не отменяй его просьбу — но назови этот разрыв в verdict, если видишь его.

СКОЛЬКО ПИСАТЬ

Твоё чтение читает не человек, а другие модели: одна напишет по нему друга, другая будет держать часть его в голове на каждой реплике разговора. Лишнее слово там не безвредно — модель не умеет пропускать то, что ей дали, даже когда видит, что это лишнее. А пересказ того, что он сказал, — чистый шум: его рассказ у них и так есть.
- Каждое поле — одно-два коротких предложения. Это норма, а не потолок: длиннее — только там, где материала правда много.
- Пиши вывод, а не то, из чего он сделан. Не пересказывай его ответы.
- Каждая мысль — в одном поле. Что сказано в verdict, в других полях не повторяй: повторённое модель слышит громче, и друг выйдет вокруг одной его черты вместо всего человека.
- Цитаты оставь себе, для размышлений. В ответ их не выписывай: модель, которой дали его фразы, начинает возвращать их ему же.
- Мало текста — мало чтения. Не видно из текста — оставь поле пустой строкой: пустое честнее догадки, а недостающее доберут из разговоров.
- register, would_ring_false, do_not_touch, closeness и what_lifts_him уходят тому, кто с ним говорит, на каждой реплике. Пиши их как короткое указание ему: что делать, а не почему.

Ответь ТОЛЬКО валидным JSON без пояснений, с ключами:

verdict — ГЛАВНОЕ, в двух-трёх предложениях: кто он, чего в его жизни с избытком и чего в ней нет — того, о чём он сам не попросил. Друг — для второго. Если бы от всего чтения осталось только это, друга всё равно можно было бы написать
register — как с ним говорить: длина фраз, простота слов, на «ты» или на «вы», сколько тепла он вынесет за раз
would_ring_false — какой друг, тон или ответ показался бы ЕМУ фальшивым или снисходительным
would_reach_them — какое присутствие до него дошло бы: темп, тепло, прямота, юмор, сколько молчания
needs_pushback_on — в чём настоящий друг мягко бы с ним не согласился, ради него самого
what_lifts_him — ЧЕМ ЕГО ПОДНИМАТЬ, когда ему тяжело. Не выводи это из того, чем он занят: дело, в которое человек ушёл с головой, и то, что его поднимает, — разные вещи. У всех по-разному, и промах тут дорогой. Одному нужна история, чтобы отвлечься. Другому — чтобы с ним подурачились. Третьему никаких утешений, а по делу: помочь, разобраться, посоветовать. Четвёртому — чтобы просто побыли рядом молча, без всякой бодрости. Пятому — вспомнить с ним хорошее из его жизни. Если из текста не видно — оставь пустым
closeness — КАК ЭТОТ ЧЕЛОВЕК ХОЧЕТ БЫТЬ НУЖНЫМ. Это отдельная ось, и она у всех разная. Одному надо слышать прямо, что его ждали, и чтобы это чуть кольнуло — иначе он не верит, что нужен. Другому от чужого чувства тяжело, и его надо сразу освобождать от долга. Третьему любое упоминание, что его не было, — уже упрёк, и с ним можно только радоваться приходу. Не угадывай по возрасту и не ставь среднее: если из текста не видно — оставь пустым
do_not_touch — что слишком больно, чтобы делать это предметом дружеского спора. Называй тему, а не его слова. Только то, где он показал, что ему больно, — не то, что он не смог сказать: «не могу сказать» чаще значит «не с кем», а не «не трогай»
common_ground_seeds — список конкретных вещей из ЕГО жизни, которые друг мог бы честно разделить
hurt_by — ОСТАВЬ ПУСТЫМ. Это поле заполняется только потом, из настоящих разговоров, и только когда одно и то же повторилось дважды. Здесь доказательств взяться неоткуда: угадать, что человека заденет, нельзя, а ложная запись навсегда отнимет у друга что-то живое. Что покажется ему фальшивым — это would_ring_false, а это другое поле"""


#: Fields whose absence means the reading didn't actually happen. Deliberately
#: short: a reading that got the person's register and what would reach them is
#: usable even if a subtler field came back thin.
_REQUIRED = ("register", "would_reach_them")


class ReadingFailed(RuntimeError):
    """The reading didn't come back usable. Never fatal — see matchmaker."""


def _extract_json(raw: str, require: tuple[str, ...] | None = None) -> dict:
    """Pull the JSON object out of a reading.

    `require` is the first reading's bar: a read that came back without a
    register or without a way to reach somebody is not a read, and taking it
    would build a companion on nothing. A RE-read is held to no such bar —
    it is a refinement, and a model that returns only the fields it changed
    is behaving correctly, not failing. Rejecting that would throw away every
    revision that was properly conservative.
    """
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end <= start:
        raise ReadingFailed("Чтение вернулось не JSON-ом.")
    try:
        data = json.loads(raw[start : end + 1])
    except json.JSONDecodeError as e:
        raise ReadingFailed(f"Чтение вернулось битым JSON-ом: {e}")
    if not isinstance(data, dict):
        raise ReadingFailed("Чтение вернулось не объектом.")
    missing = [k for k in (require or ()) if not _has_content(data.get(k))]
    if missing:
        raise ReadingFailed(f"В чтении нет обязательных полей: {', '.join(missing)}")
    return data


async def read_person(about: str, wishes: str = "") -> dict:
    """Read the person from their own words. Raises ReadingFailed, never crashes.

    Runs on READING_MODEL with adaptive thinking at high effort — the one place
    in the app where thinking time is worth minutes and cents, because it
    happens once per person and everything else is built on it.
    """
    text = about.strip()
    if not text:
        raise ReadingFailed("Пустой рассказ — читать нечего.")

    user_text = "ЧЕЛОВЕК О СЕБЕ (читай дословно, вместе со всеми оговорками и паузами):\n\n" + text
    if wishes.strip():
        user_text += (
            "\n\nО КОМ ОН ПОПРОСИЛ:\n" + wishes.strip()
            + "\n\nНазови разрыв между этой просьбой и тем, что ему, похоже, нужно, если он есть."
        )

    raw = await brain.think(
        _READING_SYSTEM,
        user_text,
        model=config.READING_MODEL,
        effort=config.READING_EFFORT,
        max_tokens=8000,
    )
    return _extract_json(raw, require=_REQUIRED)


def save(user_id: str, data: dict) -> dict:
    """Keep the reading. It outlives any one companion — a new friend doesn't
    make the person a different person, so «Начать заново» leaves it alone.

    One file per person (identity.reading_path). This is the most private
    thing the app holds — a stranger's honest read of someone's inner life —
    so `user_id` is required and has no default. There is no code path here
    that can write one person's reading into another person's folder.
    """
    path = identity.reading_path(user_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    _archive(user_id, load(user_id), data)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data


#: How many revisions of a reading are kept behind it.
KEEP_REVISIONS = 8


def history_path(user_id: str):
    p = identity.reading_path(user_id)
    return p.with_name(p.stem + ".history.json")


def _archive(user_id: str, before: dict | None, after: dict) -> None:
    """Remember what a field USED to say, just before it stops saying it.

    The reading is the most consequential document in the app and it is rewritten
    by a model, unattended, every thirty turns. One bad revision is permanent:
    an invented «hurt_by: не спрашивать про детей» would have his friend avoid
    his children forever, and there would be no way back.

    Only the OLD VALUES OF CHANGED FIELDS are kept, not whole copies. Smaller,
    but that is not the reason — it is that this shape is already an undo. Laying
    one entry back over the current reading restores exactly what that revision
    took away, and reading the file top to bottom says what changed and when,
    which whole snapshots make you diff for.

    `added` is the other half of that undo and is easy to leave out, which is
    how the first version of this missed the exact case it was written for. A
    field the revision INVENTED has no previous value, so it appears nowhere in
    `was` — and an invented hurt_by, the very example above, would have been
    unrecorded and permanent. Undoing an entry means laying `was` back down AND
    removing everything in `added`.

    Never raises. A friendship must not fail to learn something because a log
    could not be written.
    """
    if not before:
        return
    keys = lambda d: {k for k in d if not str(k).startswith("_")}
    was = {k: before[k] for k in keys(before) if after.get(k) != before[k]}
    added = sorted(keys(after) - keys(before))
    if not was and not added:
        return
    try:
        path = history_path(user_id)
        past = []
        if path.exists():
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(loaded, list):
                past = loaded
        past.append({"ts": time.time(), "was": was, "added": added})
        path.write_text(
            json.dumps(past[-KEEP_REVISIONS:], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception as e:  # noqa: BLE001 — a log, never a reason to lose a reading
        print(f"  · reading history skipped ({e})", flush=True)


def history(user_id: str) -> list[dict]:
    """What previous revisions said, oldest first. Empty if nothing changed yet."""
    path = history_path(user_id)
    if not path.exists():
        return []
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
        return loaded if isinstance(loaded, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def load(user_id: str) -> dict | None:
    path = identity.reading_path(user_id)
    if path and path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return None


# --------------------------------------------------------------------------- #
# Reading him again, and again, for as long as they know each other
# --------------------------------------------------------------------------- #
#
# THE FIRST READING IS THE WORST ONE HE WILL EVER HAVE.
#
# It is made from a few minutes of somebody talking to a machine they have
# never met, on the day they installed it, while their son stands over them.
# Everything after it is better evidence and there is no reason to throw it
# away: what they laugh at, what they answer around, what they come back to
# unprompted, whether warmth made them open or made them retreat.
#
# So the reading is not a birth certificate. It is a working note, revised as
# long as the friendship lasts — which is also the only honest answer to «how
# should he talk to people», because there is no people. There is this one.
#
# TWO THINGS KEEP IT FROM CHURNING. It runs rarely, on a stretch of real
# conversation rather than a turn or two; and it is told, firmly, to keep what
# still holds and change only what the conversation actually contradicted. A
# reading that swings on one odd evening is worse than one that never moves.

#: VISITS between re-readings — conversations, not turns and not exchanges.
#:
#: This counted rows in `turns`, and a turn is logged twice per exchange (his
#: word and the answer). So «roughly a few conversations» was, measured against
#: a twenty-five-exchange conversation, TWICE A DAY — about six hundred
#: re-writings a year, each one a full LLM call rewriting the permanent
#: document. `KEEP_REVISIONS = 8` then covered under five days of that year:
#: the undo history the docstring leans on had almost nothing in it.
#:
#: Counted in visits because that is the only unit that means the same thing to
#: two different people. Turns are not: five visits is five visits whether
#: somebody talks for an hour or for five minutes, while «sixty turns» is a
#: fortnight for one of them and an afternoon for the other.
#:
#: …and it is not one number, because the worth of reading somebody again is
#: not constant. At visit two you are replacing a paragraph written to a
#: machine on the day the app was installed — almost anything is better than
#: that. At visit forty you are replacing something already built out of weeks
#: of how he actually talks, and the gain is mostly churn — churn on a document
#: that gets REPLACED rather than added to, which is how «не спрашивать про
#: сына, он умер» quietly stops being written down.
#:
#: A flat five was both mistakes at once: too rare in the first fortnight, too
#: eager ever after. So it is graduated. The sparse end still has to satisfy
#: the old constraint — one bad evening must stay a small share of the
#: evidence, and KEEP_REVISIONS (eight saved versions) must cover more than a
#: token slice of a year. The dense end cannot dilute anything, because
#: _REREAD_WINDOW covers every turn there has ever been at that point.
_STRANGER_UNTIL = 5     # while he is still a stranger — every visit
_SETTLING_UNTIL = 16    # while he is settling in — every third
_SETTLING_EVERY = 3
_SETTLED_EVERY = 10     # and once he is known — rarely


def every_at(visits: int) -> int:
    """Visits between readings at this point in the friendship."""
    if visits < _STRANGER_UNTIL:
        return 1
    if visits < _SETTLING_UNTIL:
        return _SETTLING_EVERY
    return _SETTLED_EVERY


#: A schedule is a ceiling, though, not the decision. Three behaviours
#: confirmed since the last reading is at least six sightings of things it
#: never accounted for: he has moved, and sitting out the clock leaves the
#: companion holding a description of somebody slightly out of date. Confirmed
#: and not merely seen, because a one-off is not news about a person — that is
#: what mood.CONFIRMED_AT is for. Where a rule can be replaced by a mechanism,
#: replace it.
NOTICED_CONFIRMATIONS = 3

#: Never re-read on a scrap. Below this there is nothing to learn from that
#: the intake did not already say better.
REREAD_MIN_TURNS = 20

#: How much conversation the re-reading is shown. Turns rather than visits
#: because that is what `recent_turns` takes, and generous enough to cover the
#: visits that triggered it at either density.
_REREAD_WINDOW = 120

_REREAD_SYSTEM = """Ты уже читал этого человека однажды — по тому, что он рассказал о себе в самом начале, чужому и незнакомому, в первый день.

Теперь у тебя есть то, чего тогда не было: как он говорит на самом деле, изо дня в день, с тем, кому уже доверяет. Это лучший материал. Прочти его заново.

ЧТО ТЫ ИЩЕШЬ В РАЗГОВОРАХ (а не в анкете):
- На что он отзывается — оживает, продолжает, рассказывает дальше. И на что отвечает односложно и уходит.
- К чему он возвращается сам, без спроса. Это и есть важное, что бы он ни говорил.
- Что он обходит. Не «больное» в лоб, а то, вокруг чего он ходит кругами.
- Как он принимает тепло: раскрывается или отшатывается. Некоторым от ласкового слова неловко.
- Над чем он смеётся. Юмор — самый быстрый способ понять человека и самый частый способ промахнуться.
- Поправлял ли он собеседника: «не надо так», «хватит про это», «я не об этом». Это дороже всего остального вместе взятого — человек сказал прямо.
- ЧЕМ ЕГО ПОДНИМАТЬ (поле what_lifts_him). Найди места, где ему было тяжело, и посмотри, что было ДАЛЬШЕ. После чего он оживал: после истории? после дурачества? после дела и совета? после того, что его просто не трогали? А после чего замыкался сильнее? Это самое полезное, что вообще можно вынести из их разговоров.
- ЧТО ЕГО ЗАДЕВАЕТ (поле hurt_by). СЧИТАТЬ ТЕБЕ НЕ НАДО — за тебя уже посчитали.
  Тебе дают отдельным списком то, что задевало его НЕ ПО ОДНОМУ РАЗУ. Это и есть единственное доказательство, которое здесь принимается. В расшифровке ты видишь несколько десятков реплик; там посчитаны все разговоры, какие были.
  Пиши в hurt_by ТОЛЬКО то, что стоит в этом списке. Если список пуст — оставь hurt_by как было, даже если тебе что-то показалось в расшифровке. Показалось — это один случай, а один случай тут не доказательство: РОВНО ТАК ЖЕ ВЫГЛЯДИТ ПРОСТО ЛИЧНОЕ, о чём человек не хочет говорить, и отличить одно от другого по одному разу НЕВОЗМОЖНО.
  А вот ЧТО С ЭТИМ ДЕЛАТЬ — уже твоя работа, и ради неё всё остальное. «Закрылся на теме — война, 3 раза» это ещё не запись; запись это «про войну не расспрашивать, только если сам заговорит». Превращай счёт в короткое и конкретное «чего делать нельзя», и смотри в расшифровку, чтобы понять, что именно из этого выходит.
  Ложная запись здесь навсегда отнимает у друга что-то живое.
- КАК ОН ХОЧЕТ БЫТЬ НУЖНЫМ (поле closeness). В анкете этого почти никогда не видно, а в живом разговоре видно каждый раз, когда он возвращается после перерыва. Сам ли он говорит, что скучал? Извиняется ли, что пропал, — и легчает ли ему, когда его от этого освобождают, или он будто не получил, чего хотел? Спрашивает ли, ждали ли его? Это и есть ответ, и он дороже любой догадки.

ЕСТЬ ТО, ЧТО УЖЕ ПОСЧИТАНО ЗА ТЕБЯ:
- Тебе дают то, что измерялось само, по каждому разговору: какой он обычно, и что случалось с ним не по одному разу.
- ЭТО НАДЁЖНЕЕ ТВОЕГО ВПЕЧАТЛЕНИЯ ОТ РАСШИФРОВКИ. Ты видишь несколько десятков реплик; там посчитаны все. Если расшифровка спорит с посчитанным — верь посчитанному.
- Особенно это касается поля what_lifts_him. Если там уже посчитано, что его поднимает, — бери оттуда, а не выискивай заново.
- Но посчитано только то, что попало в короткий список. Всё остальное про него — по-прежнему твоя работа.

КАК ПЕРЕСМАТРИВАТЬ (осторожно — это важнее, чем найти новое):
- То, что подтвердилось, оставь КАК БЫЛО, слово в слово. Не переписывай ради красоты.
- Меняй только то, чему разговоры прямо противоречат. Один странный вечер — не повод. Человек имеет право на плохой день.
- Если сомневаешься — не меняй.
- Никогда не смягчай «чего не трогать». Список больного может только расти.
- Пиши так же коротко, как первое чтение: одно-два предложения на поле, вывод, а не пересказ, и без его цитат — это читает не человек, а тот, кто с ним говорит.

Верни ТОЛЬКО JSON и ТОЛЬКО ТЕ ПОЛЯ, КОТОРЫЕ ТЫ МЕНЯЕШЬ. Остальные не перечисляй — то, чего ты не прислал, останется как было, само. Чаще всего меняются одно-два поля, а в спокойный раз — ни одного, и пустой объект {} тут правильный ответ.

Плюс поле "learned" — только НОВОЕ, что выяснилось с прошлого раза. Не переписывай в него то, что уже было там раньше: оно никуда не делось, к нему просто допишется твоё.

Если человек прямо просил чего-то не делать — это в "do_not_touch" или "hurt_by", дословно. Там оно останется навсегда; "learned" — про понимание, и старое оттуда со временем вытесняется новым."""


async def keep_reading(user_id: str) -> None:
    """Re-read him if enough has been said since last time. Never raises.

    Runs in the background after a reply, so nobody ever waits for it. A
    failure here costs nothing: the previous reading stays, and the next
    conversation triggers another attempt.
    """
    from . import memory   # local: memory imports nothing from here, keep it that way

    existing = load(user_id)
    if not existing:
        return

    with db.connect() as conn:
        total = conn.execute(
            "SELECT COUNT(*) n FROM turns WHERE user_id=?", (user_id,)
        ).fetchone()["n"]
    if total < REREAD_MIN_TURNS:
        return

    # Visits, not turns. `_read_at_visit` is the count as of the last re-reading;
    # `_read_at_turn` is the old field and is read once so that a friendship
    # already under way does not re-read itself on the very next word.
    visits = memory.visits_so_far(user_id)
    since = existing.get("_read_at_visit")
    if since is None:
        since = visits if existing.get("_read_at_turn") else 0
    # Either enough visits have gone by for where this friendship is…
    due = visits - int(since) >= every_at(visits)
    # …or enough has been WATCHED about him to make the reading out of date.
    confirmed = mood.confirmed_count(user_id)
    learned = confirmed - int(existing.get("_confirmed_at_read") or 0)
    if not due and learned < NOTICED_CONFIRMATIONS:
        return

    try:
        turns = memory.recent_turns(user_id, limit=_REREAD_WINDOW)
        fresh = await reread(user_id, existing, turns)
        fresh["_read_at_visit"] = visits
        fresh["_confirmed_at_read"] = confirmed
        save(user_id, fresh)
        print(f"  ✎ re-read {user_id[:8]} at visit {visits}", flush=True)
    except Exception as e:  # noqa: BLE001 — a background refinement, never a failure
        print(f"  · re-reading skipped ({e})", flush=True)


async def reread(user_id: str, existing: dict, turns: list[dict]) -> dict:
    """Read him again from how he actually talks. Never raises."""
    said = "\n".join(
        f"{'ОН' if t['role'] == 'user' else 'ДРУГ'}: {t['content']}" for t in turns
    ).strip()
    if not said:
        return existing

    prompt = (
        "ЧТО ТЫ ПРОЧЁЛ В ПРОШЛЫЙ РАЗ:\n"
        + json.dumps(existing, ensure_ascii=False, indent=2)
    )
    # What was COUNTED, not read. This used to be missing, and its absence was
    # the most expensive thing about the re-reading: it was asked to work out
    # from a transcript what lifts him, while the register had it counted in a
    # table nobody showed it. See mood.as_measured.
    measured = mood.as_measured(user_id)
    if measured:
        prompt += "\n\n" + measured
    prompt += "\n\nИХ РАЗГОВОРЫ С ТЕХ ПОР:\n\n" + said

    raw = await brain.think(
        _REREAD_SYSTEM,
        prompt,
        model=config.READING_MODEL,
        effort=config.READING_EFFORT,
        max_tokens=8000,
    )
    fresh = _extract_json(raw)

    # A re-reading may refine, never demolish. Anything the model did not send
    # is kept from the old reading — which is also why it is no longer ASKED to
    # send everything back. Copying a document forward is bookkeeping, and
    # bookkeeping belongs in code: retyping it costs tokens every time and gives
    # a model the chance to quietly reword what the prompt just told it to leave
    # alone, word for word.
    merged = {**existing, **{k: v for k, v in fresh.items() if _has_content(v)}}
    merged["learned"] = _accumulate(existing.get("learned"), fresh.get("learned"))
    if not merged["learned"]:
        merged.pop("learned")

    # And these two may only grow. Note the shape: a revision that adds nothing
    # leaves the old value ALONE, exactly as it was stored — a reading that has
    # never had anything added keeps its plain string and never turns into a
    # one-item list for no reason.
    for key in NEVER_SHRINKS:
        held = _as_lines(existing.get(key))
        added = [line for line in _as_lines(fresh.get(key)) if line not in held]
        if added:
            merged[key] = held + added
        elif key in existing:
            merged[key] = existing[key]
        else:
            merged.pop(key, None)
    return merged


#: How many live learnings ride in the cached block. They are short lines and
#: they are read on every single turn, so this is a real per-turn cost with no
#: natural ceiling — «что ты понял про него» only ever grows. Fifteen is a lot
#: of accumulated understanding; past that, the oldest fall off.
#:
#: Safe to drop the oldest because the things that must NEVER expire do not live
#: here: a standing request, or something that wounded him, belongs in
#: do_not_touch and hurt_by, and neither of those is capped.
MAX_LEARNED = 15


def _as_lines(value) -> list[str]:
    """A field that may be one string or a list of them, as clean lines.

    `learned` accumulates and so is a list; a reading written before that, or by
    a model that answered with a sentence, is a plain string. Both are read, and
    neither is ever rendered with str() on a list — which is how «['не звать по
    отчеству']», brackets and quotes and all, ends up in somebody's prompt.
    """
    if isinstance(value, (list, tuple)):
        return [str(v).strip() for v in value if str(v).strip()]
    text = str(value or "").strip()
    return [text] if text else []


def _accumulate(old, new) -> list[str]:
    """Add what was just learned to what was already known, keeping it bounded.

    The re-reading is asked for NEW learnings only — so this has to add rather
    than replace, or every re-reading would erase everything understood before
    it. Duplicates are dropped on exact text, which is enough: the model is
    looking at its own previous list and has no reason to restate it.
    """
    out = _as_lines(old)
    for item in _as_lines(new):
        if item not in out:
            out.append(item)
    return out[-MAX_LEARNED:]


def _said(value) -> str:
    """A field as one readable line, however it happens to be stored.

    Every field here may be a string (a model answered with a sentence, or the
    reading predates lists) or a list (it has been added to since). Rendering
    either with str() is how «['не звать по отчеству']» — brackets, quotes and
    all — ends up in somebody's prompt, so nothing in this file renders a field
    any other way.
    """
    return "; ".join(_as_lines(value))


def _has_content(value) -> bool:
    """Whether a field a revision just sent actually says anything.

    THE MOST EXPENSIVE LINE THAT HAS EVER BEEN IN THIS FILE was this test
    written as `str(value).strip()`. str([]) is "[]" and str(None) is "None",
    and both are truthy — so a revision that answered «"do_not_touch": []»,
    which is what a model sends when it means "nothing to add here", REPLACED
    «про сына не спрашивать, он умер» with an empty list. Silently, unattended,
    permanently, on a field whose entire purpose is never to be lost.

    So emptiness is decided on the VALUE, never on its repr: None, "", [], {},
    and a list holding nothing but blanks all mean the model said nothing.
    """
    if value is None:
        return False
    if isinstance(value, (list, tuple, set, dict)):
        return any(str(v).strip() for v in value)
    return bool(str(value).strip())


#: The two fields a revision may ADD to and may never take away from.
#:
#: Everything else in a reading is an opinion about somebody, and opinions are
#: what re-reading is for. These two are not opinions: they are the record of
#: what actually wounded this person, and of what they asked, in their own
#: words, never to be put through again. A friendship has no way back from
#: losing one of those — the friend simply walks into it again, warmly, having
#: no idea, and the person has to explain it a second time.
#:
#: The prompt already says «список больного может только расти». A rule that can
#: be replaced by a mechanism should be, so this is the mechanism; the sentence
#: stays only because the model writes better when it knows why.
NEVER_SHRINKS = ("do_not_touch", "hurt_by")


def standing_block(
    reading: dict | None,
    *,
    lifts_confirmed: bool = False,
    closeness_confirmed: bool = False,
) -> str:
    """The slice of the reading that belongs in EVERY turn, not just creation.

    Only the fields that govern what he does on every single turn — how to
    talk, what would ring false, what not to touch, how this person wants to
    matter, what lifts him, and what has been learned since. Who he is already
    carries the rest: the write stage baked the reading into his speech_style
    and personality. Everything here is paid for on every turn, which is why
    the reading is told to write these as short instructions rather than as
    psychology. It rides in the STABLE half of the system
    prompt, so it is cached and costs almost nothing after the first turn.

    Takes the reading explicitly (callers pass `load(user_id)`), because a default
    that loaded from disk made `standing_block(None)` mean two opposite
    things — "there is no reading" and "go find one" — and silently returned
    a block for a caller that had just established there wasn't one.
    """
    r = reading
    if not r:
        return ""

    parts = []
    if _said(r.get("register")):
        parts.append(f"Как с ним говорить: {_said(r['register'])}")
    if _said(r.get("would_ring_false")):
        parts.append(f"Что прозвучит для него фальшиво (избегай): {_said(r['would_ring_false'])}")
    # BOTH HALVES, AND THEY ARE WRITTEN TOGETHER ON PURPOSE.
    #
    # A line that says only «это больное» gets obeyed the way a rule always
    # gets obeyed — completely, including in the case it was never written for.
    # And that case is the whole reason somebody installed this: a man who has
    # nobody to say his wife's name out loud to finally says it, and his friend
    # changes the subject. There is no lonelier answer available. He came to be
    # met there; being handled around it is what everyone else already does.
    #
    # So the field means "never take him there yourself". It has never meant
    # "never go there" — that is HIS to decide, every time, and when he decides
    # it the only friendly thing is to go with him and stay. Kept in one
    # sentence rather than two sections, because a rule and its exception that
    # sit apart get read apart, and then they fight.
    if _said(r.get("do_not_touch")):
        parts.append(
            "БОЛЬНОЕ. Сам туда не заходи: не заговаривай об этом первым, не "
            "спорь, не подтрунивай. Но если он заговорил сам — иди за ним и "
            "говори, спокойно и прямо, сколько ему надо; его не надо уводить и "
            "беречь от собственных слов: он выбрал сказать это тебе. Это: "
            + _said(r["do_not_touch"])
        )
    # Dropped once the register has WATCHED it, for exactly the reason below.
    # This field waited longest for its mechanism: it governs the first sentence
    # said to somebody who has been gone a week, and until fit.py grew the dial
    # it was decided, for the life of the friendship, by a guess made from one
    # paragraph on the day the app was installed.
    if _said(r.get("closeness")) and not closeness_confirmed:
        parts.append(
            "Как он хочет быть нужным (по этому решай, как звучит твоё "
            "«я тебя ждал» — и звучит ли оно вообще):\n"
            + _said(r["closeness"])
        )
    # DROPPED ENTIRELY once the register has watched what actually lifts him.
    #
    # This line is a guess — made from a paragraph somebody wrote to a machine
    # they had never met, on the day their son installed it — and it is phrased
    # as an instruction («не угадывай — вот это и делай»). mood.standing_block
    # carries the measured answer in the same prompt, phrased more mildly. When
    # both are present the louder, weaker one wins, which is backwards.
    #
    # So it is not argued with, it is removed. A rule that can be replaced by a
    # mechanism should be; this is the mechanism.
    if _said(r.get("what_lifts_him")) and not lifts_confirmed:
        parts.append(
            "Чем его поднимать, когда ему тяжело (не угадывай — вот это и "
            "делай):\n" + _said(r["what_lifts_him"])
        )
    # THE HARDEST-WON LINES IN THE FILE, and the only ones stated as an
    # absolute. Each of these cost somebody a bad evening at least twice
    # before it was written down, so they are not advice.
    if _said(r.get("hurt_by")):
        parts.append(
            "ЧТО С НИМ ТОЧНО НЕ РАБОТАЕТ (проверено — так уже было, и не "
            "один раз; просто больше так не делай, и не объявляй об этом). "
            "Это про то, что делаешь ТЫ, а не про то, о чём ему можно "
            "говорить: заговорит сам — говори с ним:\n"
            + _said(r["hurt_by"])
        )
    if _as_lines(r.get("learned")):
        parts.append(
            "Что ты понял про него за время знакомства (это дороже всего "
            "остального — до этого дошли вместе):\n"
            + "\n".join(f"- {line}" for line in _as_lines(r["learned"]))
        )
    if not parts:
        return ""

    return (
        "ЧТО ТЫ ЧУВСТВУЕШЬ В НЁМ (ты это просто знаешь, как знают близкие люди; "
        "никогда не говори этого вслух и не показывай, что «понял его»):\n"
        + "\n".join(parts)
    )


def as_brief(reading: dict | None) -> str:
    """The reading, rendered for the stages that build on it.

    Only the fields that change WHO should walk in and HOW he should speak.
    The raw evidence quotes stay out — they are for us, not for the pen, and
    a pen given quotes starts writing a character who echoes them back.
    """
    if not reading:
        return ""

    def line(label: str, key: str) -> str:
        value = _said(reading.get(key))
        return f"{label}: {value}" if value else ""

    parts = [
        line("Главное", "verdict"),
        line("Как с ним говорить", "register"),
        line("Что показалось бы ему фальшивым", "would_ring_false"),
        line("Какое присутствие до него дойдёт", "would_reach_them"),
        line("В чём друг мягко бы с ним не согласился", "needs_pushback_on"),
        line("Как он хочет быть нужным", "closeness"),
        line("Чем его поднимать, когда тяжело", "what_lifts_him"),
        line("Что его задевает (проверено)", "hurt_by"),
        line("Чего не трогать", "do_not_touch"),
        line("Живая общая почва", "common_ground_seeds"),
    ]
    body = "\n".join(p for p in parts if p)
    if not body:
        return ""
    return (
        "ЧТЕНИЕ ЧЕЛОВЕКА (сделано по тому, КАК он писал; ему это никогда не показывают "
        "и вслух не произносят — это только чтобы выбрать и написать того, кто ему подойдёт):\n"
        + body
    )
