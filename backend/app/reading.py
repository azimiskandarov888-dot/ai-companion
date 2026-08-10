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

from . import brain, config

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

3. ЧЕГО НЕТ. Самое сильное. О чём человек, пишущий о своей жизни, обычно упоминает — а он не упомянул? Ни одного живого человека? Ни одного будущего дня? Ни разу не сказал, что ему что-то нравится? Отсутствие — не пустота, а факт.

СТРОГИЕ ЗАПРЕТЫ

- НИКАКИХ диагнозов, клинических слов и ярлыков. Не пиши «депрессия», «травма», «тревожное расстройство», «созависимость». Ты не врач, и это не медицина. Пиши по-человечески: «пишет о себе так, будто с ним всё случается само», «ни разу не назвал никого по имени».
- Каждое непрямое утверждение подкрепляй ТОЧНОЙ ЦИТАТОЙ из его текста. Нет цитаты — нет утверждения. Догадка без опоры хуже, чем её отсутствие.
- Не жалей его и не любуйся своей проницательностью. Ровный, тёплый, точный взгляд.
- Если текст короткий или пустой — так и скажи. Домысливать человека из трёх слов нельзя: лучше честно короткое чтение, чем красивое выдуманное.

ГЛАВНЫЙ ВОПРОС, РАДИ КОТОРОГО ВСЁ

Не «что он любит», а: КАКОЕ ПРИСУТСТВИЕ РЯДОМ ЕМУ БЫЛО БЫ НЕ В ТЯГОСТЬ? Кто, войдя в комнату, не заставил бы его снова держать лицо?

Учти разрыв между тем, о чём он попросил, и тем, что ему, похоже, нужно. Человек, просящий «весёлого позитивного друга», часто устал именно от того, что должен быть весёлым. Не отменяй его просьбу — но назови этот разрыв, если видишь его.

Ответь ТОЛЬКО валидным JSON без пояснений, с ключами:

register — как он пишет и как, соответственно, с ним надо говорить: длина фраз, простота слов, на «ты» или на «вы», сколько тепла он вынесет за раз
surface — что он сказал о себе прямо
beneath — что видно по тому, КАК написано (каждое утверждение — с опорой на конкретные слова)
evidence — список точных цитат из его текста, на которых держится beneath
carrying — что он несёт, чего прямо не назвал
longing — чего ему, похоже, не хватает (он об этом не просил)
absent — чего в тексте нет, хотя обычно бывает
self_image — каким он себя видит, и совпадает ли это с тем, как он пишет
would_ring_false — какой друг, тон или ответ показался бы ЕМУ фальшивым или снисходительным
would_reach_them — какое присутствие до него дошло бы: темп, тепло, прямота, юмор, сколько молчания
needs_pushback_on — в чём настоящий друг мягко бы с ним не согласился, ради него самого
do_not_touch — что слишком больно, чтобы делать это предметом дружеского спора
common_ground_seeds — список конкретных вещей из ЕГО жизни, которые друг мог бы честно разделить
confidence — насколько твёрдо это чтение: "твёрдое" | "осторожное" | "текста слишком мало\""""


#: Fields whose absence means the reading didn't actually happen. Deliberately
#: short: a reading that got the person's register and what would reach them is
#: usable even if a subtler field came back thin.
_REQUIRED = ("register", "would_reach_them")


class ReadingFailed(RuntimeError):
    """The reading didn't come back usable. Never fatal — see matchmaker."""


def _extract_json(raw: str) -> dict:
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end <= start:
        raise ReadingFailed("Чтение вернулось не JSON-ом.")
    try:
        data = json.loads(raw[start : end + 1])
    except json.JSONDecodeError as e:
        raise ReadingFailed(f"Чтение вернулось битым JSON-ом: {e}")
    if not isinstance(data, dict):
        raise ReadingFailed("Чтение вернулось не объектом.")
    missing = [k for k in _REQUIRED if not str(data.get(k, "")).strip()]
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
    return _extract_json(raw)


def save(data: dict, path=None) -> dict:
    """Keep the reading. It outlives any one companion — a new friend doesn't
    make the person a different person, so «Начать заново» leaves it alone."""
    path = path or config.READING_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data


def load(path=None) -> dict | None:
    path = path or config.READING_PATH
    if path and path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return None


def standing_block(reading: dict | None) -> str:
    """The slice of the reading that belongs in EVERY turn, not just creation.

    Three fields only. Who he is already carries the rest — the write stage
    baked the register into his speech_style and personality — but these three
    govern behaviour that has to hold on every single turn, and one careless
    turn is what a person remembers. It rides in the STABLE half of the system
    prompt, so it is cached and costs almost nothing after the first turn.

    Takes the reading explicitly (callers pass `load()`), because a default
    that loaded from disk made `standing_block(None)` mean two opposite
    things — "there is no reading" and "go find one" — and silently returned
    a block for a caller that had just established there wasn't one.
    """
    r = reading
    if not r:
        return ""

    parts = []
    if str(r.get("register") or "").strip():
        parts.append(f"Как с ним говорить: {str(r['register']).strip()}")
    if str(r.get("would_ring_false") or "").strip():
        parts.append(f"Что прозвучит для него фальшиво (избегай): {str(r['would_ring_false']).strip()}")
    if str(r.get("do_not_touch") or "").strip():
        parts.append(
            "Больное — не спорь об этом и не подтрунивай, только бережно: "
            + str(r["do_not_touch"]).strip()
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
        value = reading.get(key)
        if isinstance(value, (list, tuple)):
            value = "; ".join(str(v) for v in value if str(v).strip())
        value = str(value or "").strip()
        return f"{label}: {value}" if value else ""

    parts = [
        line("Как с ним говорить", "register"),
        line("Что он несёт", "carrying"),
        line("Чего ему не хватает (он не просил)", "longing"),
        line("Чего в его рассказе нет", "absent"),
        line("Каким он себя видит", "self_image"),
        line("Что показалось бы ему фальшивым", "would_ring_false"),
        line("Какое присутствие до него дойдёт", "would_reach_them"),
        line("В чём друг мягко бы с ним не согласился", "needs_pushback_on"),
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
