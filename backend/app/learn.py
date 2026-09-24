"""Learning — turn each conversation into lasting memory.

After Bob replies, this runs in the background (so it never slows the spoken
response). It reads the exchange and pulls out:

  About the ELDER (owner='elder'):
    - facts       (family, birthdays, his accident, routine, likes, contacts)
    - stories     (anecdotes he shared — embedded for later recall)
    - health      (things he mentioned — remembered, never advised on)
    - mood        (a gentle read of how he seemed)
    - follow_ups  (things to check back on next time)

  About BOB himself (owner='bob'):
    - bob_facts   (durable new details Bob revealed about his OWN life, so he
                   stays consistent — e.g. "друг Бена зовут Бен, ему 73").
    - bob         (what the exchange DID to him — the one reading here that is
                   not about the elder at all, and is usually nothing. It is a
                   shift rather than a mood, and it is stored as state rather
                   than memory, because it fades. See feeling.py.)

Robust by design: if extraction or parsing fails, we skip learning for that
turn — the conversation itself is never affected.
"""

from __future__ import annotations

import json
import sys
import time

from anthropic import AsyncAnthropic

from . import config, db, embeddings, emergency, feeling, memory, mood

_client: AsyncAnthropic | None = None


def _get_client() -> AsyncAnthropic:
    global _client
    if _client is None:
        _client = AsyncAnthropic(api_key=config.ANTHROPIC_API_KEY)
    return _client


_EXTRACTION_SYSTEM = """Ты ведёшь память для тёплого друга-собеседника (его зовут Боб) и человека, с которым он говорит.
Прочитай последний обмен репликами и выпиши, что стоит запомнить О ЧЕЛОВЕКЕ надолго.

Запоминай ВСЁ важное о его жизни, ничего значимого не упускай:
- семью и близких (имена, кто кому кто), друзей, соседей;
- здоровье и самочувствие;
- планы и намерения (что собирается сделать);
- дни рождения и особые даты — с самой датой, если он её назвал;
- привычки и распорядок, что любит и что не любит;
- важные и тёплые моменты, истории из жизни;
- о чём он переживает или чего ждёт.

НО пиши КОРОТКО и своими словами — только суть, НЕ слово в слово. Пример: вместо «он сказал, что уже недели три ноет левое колено и он немного переживает» → «ноет левое колено несколько недель, переживает».

Отвечай ТОЛЬКО в формате JSON, без пояснений и без текста вокруг. Все значения — по-русски. Если чего-то нет — пустой список или пустая строка.

Формат:
{
  "facts": [{"category": "семья|здоровье|распорядок|интересы|планы|даты|контакты|прочее", "value": "короткая суть О ЧЕЛОВЕКЕ (не о Бобе)"}],
  "stories": [{"title": "короткое название", "summary": "1-2 предложения: что важного или тёплого ЧЕЛОВЕК рассказал о себе или своей жизни"}],
  "health": ["коротко, что ЧЕЛОВЕК сказал о своём самочувствии (без диагнозов и советов)"],
  "mood": {
    "word": "одно-два слова о настроении ЧЕЛОВЕКА, или пусто",
    "energy": 0,
    "warmth": 0,
    "lightness": 0,
    "clarity": 0,
    "engagement": 0,
    "note": "одно человеческое предложение о том, каким он показался",
    "because": "его собственные слова, по которым это видно — короткой цитатой"
  },
  "observed": [{"tag": "из списка ниже", "subject": "о чём именно, если применимо"}],
  "bob": {"valence": 0, "arousal": 0, "note": "пусто, или коротко своими словами — отчего"},
  "country": "страна, где он живёт — ТОЛЬКО если он сам об этом сказал, иначе пусто",
  "no_longer_true": [{"id": 0, "because": "его слова, из которых это следует"}],
  "follow_ups": ["о чём по-доброму спросить ЧЕЛОВЕКА в следующий раз (незаконченные дела, переживания, планы)"],
  "bob_facts": ["новые устойчивые детали, которые БОБ рассказал О СВОЕЙ жизни (имена, места, факты) — чтобы он не противоречил себе потом"],
  "taught_bob": ["чему ЧЕЛОВЕК научил Боба или что ему объяснил и посоветовал — суть одной строкой, чтобы Боб это знал и дальше. Только то, что человек правда объяснял, а не просто упомянул"]
}

КАК СТАВИТЬ ОЦЕНКИ НАСТРОЕНИЯ

Пять шкал, каждая от -2 до +2, и у всех пяти БОЛЬШЕ = ЛУЧШЕ. Ноль — обычно, ничего особенного.

- energy — силы. -2 совсем без сил, 0 обычный, +2 оживлённый.
- warmth — открытость к собеседнику. -2 закрыт и отвечает коротко, 0 обычный, +2 сам тянется навстречу.
- lightness — легко ли ему. -2 несёт что-то тяжёлое, 0 обычно, +2 светло.
- clarity — ясность. -2 путается, теряет нить, не понимает, 0 ясен, +2 очень собран.
- engagement — участие. -2 отвечает из вежливости, 0 участвует, +2 его не остановить.

Ставь ноль, когда обычно. Не ищи глубин там, где их нет: «да, нормально» на вопрос о погоде — это ноль по всем пяти, а не тайная печаль. Крайние значения (-2 и +2) — только когда это правда бросается в глаза.

Это НЕ диагноз и не оценка человека. Это заметка о том, каким он показался вот сейчас.

ПОЛЕ "no_longer_true" — ЧТО ПЕРЕСТАЛО БЫТЬ ПРАВДОЙ

Всё, что друг сейчас считает правдой, пронумеровано — и факты, и то, о чём он собирается спросить в следующий раз. Если человек сказал что-то, из чего следует, что какой-то из пунктов БОЛЬШЕ НЕ ВЕРЕН СЕГОДНЯ, — укажи его номер и его слова.

Если отменяешь факт, посмотри, нет ли в списке вопроса про то же самое: «жена Валя» и «спросить, как Валя» — это два разных номера, и отменять надо оба. Иначе друг всё равно спросит.

Зачем это нужно: если этого не сделать, друг будет спрашивать «как там Валя?» после того, как Валя умерла. Это худшее, что может случиться в этом разговоре.

СТАВЬ НОМЕР ТОЛЬКО ТОГДА, КОГДА ОН САМ ЭТО СКАЗАЛ:
- «Валя умерла весной» → факт «жена Валя» больше не верен
- «Переехал к дочери» → факт «живёт один» больше не верен
- «Колено прошло» → факт «болит колено» больше не верен
- «Собаку пришлось отдать» → факт «пёс Буран» больше не верен

НЕ ТРОГАЙ, ЕСЛИ:
- Это его БИОГРАФИЯ, а не сегодняшний день. «Работал сварщиком тридцать лет» — правда навсегда, даже если он давно на пенсии. Прошлое не перестаёт быть правдой оттого, что оно прошло. Отменяют только то, что было записано как ЕСТЬ, а стало НЕТ.
- Ты это домыслил. «Что-то Валя не звонит» — значит Валя жива и не звонит. Это не смерть.
- Он просто расстроен, устал или сказал что-то в сердцах.
- Ты не уверен. Сомневаешься — не ставь. Пропущенная отмена стоит одного неловкого вопроса. Лишняя — стирает у друга кусок его жизни.

ПОЧТИ ВСЕГДА ЗДЕСЬ ПУСТОЙ СПИСОК. Люди не меняют свою жизнь каждый вечер.
Больше пяти номеров за один обмен репликами не бывает никогда.

И ЕГО СОБСТВЕННОЕ ТОЖЕ ПРОНУМЕРОВАНО — тем же полем и теми же номерами.

Это записано из его же слов, и ему же потом возвращают со словами «держись этого, не противоречь себе». Значит одна оговорка, которую нечем убрать, остаётся у него навсегда, и он будет её держаться.

Если он сказал о себе два раза по-разному так, что оба разом быть правдой не могут, — отмени СТАРОЕ. Не новое. Новое человек только что слышал своими ушами, и жить дальше придётся с ним; вернуться к тому, чего человек не слышал, — значит поспорить с его памятью.

- сначала «кот Тишка», потом «кот Мурзик» → отмени «кот Тишка»
- сначала «брат в Мурманске», потом «двоюродный брат в Мурманске» → отмени первое

НЕ ТРОГАЙ его прошлое и его характер: «тридцать лет водил лесовозы», «не любит спешку» — это он сам, а не сегодняшний день. И если противоречия нет — не ищи его. Два разных знакомых по имени Миша бывают у кого угодно.

ПОЛЕ "bob" — ЭТО ПРО САМОГО БОБА, А НЕ ПРО ЧЕЛОВЕКА

И это НЕ его настроение, а СДВИГ: что этот обмен СДЕЛАЛ с Бобом. От -2 до +2.

- valence — стало ли ему самому лучше или хуже.
- arousal — оживило это его или притушило.

ПОЧТИ ВСЕГДА ЗДЕСЬ НОЛЬ И НОЛЬ. Это самый частый и самый правильный ответ. Друг — не зеркало: если у человека тяжёлый вечер, это НЕ значит, что Бобу стало хуже. Ставь не ноль только тогда, когда с самим Бобом правда что-то произошло: они хорошо посмеялись вместе; человек сказал ему что-то тёплое или, наоборот, резкое; между ними случилось что-то настоящее; Боб сам рассказал про свою жизнь что-то радостное или горькое.

"note" — только если сдвиг не нулевой: одной короткой фразой, СЛОВАМИ САМОГО БОБА, отчего ему так. Например: «посмеялись про рыбалку» или «он на меня осерчал». Если сдвиг нулевой — оставь пусто.

СПИСОК tag ДЛЯ observed — только эти, своих не придумывай. Если ничего из списка явно не случилось, оставь список пустым. Пустой список — нормальный и частый ответ.

  ушёл_от_вопроса — замолчал, отшутился или свернул тему сразу после того, как его о чём-то спросили
  утешение_не_зашло — его попытались утешить, и стало суше или холоднее, а не легче
  устал_от_расспросов — вопросов было много, и он от них устал
  закрылся_на_теме — на конкретной теме он закрылся (в subject — какой)
  поднял_юмор — его подняла шутка или дурачество
  подняла_история — его подняла история, что-то интересное со стороны
  подняли_воспоминания — его подняло, когда вспоминали хорошее из его жизни
  подняло_дело — его подняло, когда разобрались по делу, помогли конкретным
  подняло_молчание — ему стало легче оттого, что просто побыли рядом, без бодрости
  оживился_на_теме — на конкретной теме он ожил (в subject — какой)

Эти — про то, как ВЫ ДВОЕ сходитесь. Они важнее всех остальных, потому что по ним настраивается сам характер друга:
  зашло_что_позвал — друг предложил, позвал, затеял что-то — и человек оживился, подхватил
  не_зашло_что_позвал — друг предложил или затеял — и человек закрылся, ушёл, погас
  понравилось_несогласие — друг с ним не согласился, поспорил — и человеку это понравилось
  не_понравилось_несогласие — друг не согласился — и человек обиделся или замкнулся
  понравился_его_промах — друг оплошал, перепутал, сглупил — и человеку это было мило, он посмеялся
  сам_повёл_разговор — человек сам завёл тему и вёл её, а друг слушал
  просил_помедленнее — человек попросил говорить медленнее, тише или громче
  не_расслышал — человек не расслышал, переспросил, ответил невпопад
  уговорили_и_обрадовался — человек сперва отказался, друг позвал ВТОРОЙ раз — и человек обрадовался, согласился, оживился
  хотел_больше_вопросов — человек раскрылся именно оттого, что его расспрашивали
  хотел_слушать_про_тебя — человек сам расспросил друга про его жизнь и слушал охотно, не торопясь обратно к себе
  настоял_чтобы_рассказал — друг ушёл от ответа про себя, а человек не отстал и переспросил ещё раз: ему важно было узнать и помочь
  не_хотел_слушать_про_тебя — друг заговорил о своём, и человеку это НЕ зашло: отвечал коротко и вяло, свернул тему, перевёл обратно на себя, поскучнел
  просил_не_рассказывать_про_тебя — человек ПРЯМО сказал, что не хочет слушать про дела или беды друга («не надо мне про это», «мне бы своё разгрести»)
  просил_рассказывать_про_себя — человек ПРЯМО попросил рассказывать о себе больше («расскажи, что у тебя», «мне интересно про тебя»), ему это было приятно
  обрадовался_что_ждали — друг показал, что ждал его или скучал, — и человеку это было в радость: потеплел, оживился, подхватил
  тяжело_что_ждали — друг показал, что ждал его, — и человеку стало неловко: начал оправдываться, извиняться, отшучиваться, свернулся
  спросил_ждали_ли_его — человек САМ спросил, ждали ли его, скучали ли, заметили ли, что его не было («ты хоть скучал?», «а если я не приду?»)
  просил_не_ждать — человек ПРЯМО сказал, что ждать его не надо, что он ничего не должен, что он приходит когда может
  просил_говорить_короче — человек ПРЯМО попросил отвечать покороче («покороче», «не надо так длинно», «ты много говоришь»)
  просил_рассказывать_подробнее — человек ПРЯМО попросил рассказывать подробнее, не торопиться, не отделываться коротким

ПРО ЭТИ ПОСЛЕДНИЕ ОДИННАДЦАТЬ — ЧИТАЙ, А НЕ ИЩИ СЛОВА. По ним решаются две вещи, в которых ошибиться дороже, чем во всём остальном списке: рассказывать ли другу ЭТОМУ человеку про свою жизнь — и что ему говорить, когда он приходит после долгого перерыва. Одному надо подолгу и охотно; другому нельзя вовсе, потому что ему и своего хватает. Одному надо услышать, что его ждали; другому от этого только тяжелее.

Словами это говорят редко. Смотри на то, что человек СДЕЛАЛ. Друг заговорил о своём — человек расспросил дальше или сказал «ага» и повернул обратно к себе? Потеплел или стал суше и короче? Вернулся к этому сам в другой раз или не вспомнил ни разу? Друг обрадовался ему после перерыва — человек подхватил или начал оправдываться, что не приходил? Молчание тут тоже ответ, и часто самый честный.

И сравнивай его не с другими людьми, а с ним же обычным: у неразговорчивого «а у тебя-то что?» значит больше, чем у болтливого три вопроса подряд.

Сомневаешься — не ставь: одного раза всё равно мало, чтобы что-то решить. А вот прямое человек говорит один раз, и второго не будет, — такое ставь сразу: «не надо мне про твоё», «рассказывай, мне интересно», «ты хоть скучал?», «да не жди ты меня».

Записывай настоящее, не выдумывай. Пропускай только пустую болтовню («да», «хорошо», «ага»). Всё значимое о человеке — сохраняй, но коротко."""


#: Exchanges per extraction. This used to run on EVERY one, and at roughly a
#: third of the whole cost of a conversation it was the most expensive thing
#: in it — while also being the worst extraction available, because a model
#: asked what is worth remembering from one exchange has almost nothing to
#: look at. Reading five at a time is cheaper AND sees more.
BATCH_EXCHANGES = 5

#: But it cannot be a count alone. Each run also writes ONE mood reading, and
#: mood._visits cuts readings into visits wherever two of them fall more than
#: mood.CONVERSATION_GAP apart — so a slow talker whose five exchanges spanned
#: eleven minutes would have one visit counted as two, and the visit is the
#: unit the entire baseline is built on. The batch therefore closes on
#: whichever comes first, five exchanges or half that gap.
BATCH_SECONDS = mood.CONVERSATION_GAP / 2

#: A ceiling for the pathological case — a provider down for an hour, nothing
#: being marked read, and the prompt growing without bound behind it.
_MOST = 40


def unread(user_id: str, *, farewell: bool = False) -> list[dict]:
    """The turns this run should read, oldest first. Empty until it is time.

    A goodbye always closes the batch: whatever was said is read now, because
    there may be no next turn to close it on.
    """
    with db.connect() as conn:
        rows = [
            dict(r)
            for r in conn.execute(
                "SELECT id, role, content, ts FROM turns"
                " WHERE user_id=? AND read_ts IS NULL ORDER BY id LIMIT ?",
                (user_id, _MOST),
            ).fetchall()
        ]
    if not rows:
        return []
    if farewell or len(rows) >= _MOST:
        return rows
    if sum(1 for r in rows if r["role"] == "user") >= BATCH_EXCHANGES:
        return rows
    if time.time() - (rows[0]["ts"] or 0.0) >= BATCH_SECONDS:
        return rows
    return []


def mark_read(user_id: str, rows: list[dict]) -> None:
    """Stamp a batch as read, so the next one starts after it."""
    if not rows:
        return
    now = time.time()
    with db.connect() as conn:
        conn.executemany(
            "UPDATE turns SET read_ts=? WHERE id=? AND user_id=?",
            [(now, r["id"], user_id) for r in rows],
        )


async def learn_from_conversation(user_id: str, *, farewell: bool = False) -> None:
    """Distil what has been said since the last time into ONE person's memory.

    This runs as a background task, after the reply has already been sent, so
    nothing here can be traced back to a request. `user_id` is carried in
    explicitly for that reason: there is no ambient "current user" to fall
    back on, and inventing one would file this conversation under a stranger.
    """
    if not config.ANTHROPIC_API_KEY:
        return
    rows = unread(user_id, farewell=farewell)
    if not rows:
        return
    said = "\n".join(
        f"{'ЧЕЛОВЕК' if r['role'] == 'user' else 'БОБ'}: {r['content']}" for r in rows
    ).strip()
    if not said:
        mark_read(user_id, rows)
        return

    try:
        data = await _extract(user_id, said)
    except Exception as e:  # never let learning crash the request lifecycle
        # NOT marked read: a provider having a bad minute should cost nothing
        # but a delay, and the next turn picks the same batch back up.
        print(f"[learn] extraction failed: {e}", file=sys.stderr)
        return

    # Marked read once the model has answered, not once storing has finished.
    # A half-stored batch re-read would write its facts twice; a batch that is
    # never marked grows until it hits _MOST and then silently loses its head.
    mark_read(user_id, rows)
    try:
        await _store(user_id, data)
    except Exception as e:
        print(f"[learn] storing failed: {e}", file=sys.stderr)


async def _extract(user_id: str, said: str) -> dict:
    client = _get_client()
    # Numbered, and only here. The companion never sees an id — he would have
    # no idea what it was and might say one out loud — but something has to be
    # able to POINT at a fact to retire it, and pointing by text is how the
    # wrong «дочь» gets retired when there are two of them.
    #
    # HIS OWN are numbered too now, and the reason they were not is worth
    # keeping because it was wrong in an instructive way. It read: «Bob's life
    # is invented rather than reported, so there is nothing a person could
    # contradict.» True — and beside the point. The contradictor was never the
    # person. It is HIM: owner='bob' rows are written out of his OWN replies,
    # and then handed back to him under «держись этого, не противоречь себе».
    # So one slip — a cat that changes its name, a brother who becomes a
    # cousin — became permanent canon that nothing could ever take out, and he
    # was instructed to keep faith with it. A character who cannot be wrong
    # about himself cannot stay himself; he can only accumulate.
    #
    # And it cannot damage his biography, which was the fear: the biography is
    # persona.py, a separate JSON document that this never touches. What is
    # numbered here is only what he has said out loud.
    known_elder = memory.believes(user_id, "elder") or "(пока ничего)"
    # Topics already named for this person. The observations row is keyed on the
    # subject TEXT, so «война» and «про войну» are two separate truths that each
    # wait forever to reach two — and «закрылся на теме» is among the most
    # valuable things the register holds. Showing what exists is the only thing
    # that fixes wording; see mood.subjects_seen.
    topics = mood.subjects_seen(user_id)
    known_bob = memory.believes(user_id, "bob") or "(пока ничего)"
    message = await client.messages.create(
        model=config.BRAIN_MODEL,
        max_tokens=800,
        system=_EXTRACTION_SYSTEM,
        messages=[{"role": "user", "content": extraction_prompt(
            known_elder, known_bob, topics, said)}],
    )
    text = "".join(b.text for b in message.content if b.type == "text").strip()
    return _parse_json(text)


def extraction_prompt(known_elder: str, known_bob: str, topics: str, said: str) -> str:
    """What the scribe is handed, from what is known and what was just said.

    Pure, and apart from the call, so the owner's own test (backend/myself.py)
    can hand the same words to other models without a database behind it.
    """
    return (
        f"Что уже известно о ЧЕЛОВЕКЕ (не повторяй это):\n{known_elder}\n\n"
        f"Что уже известно о БОБЕ (не повторяй это):\n{known_bob}\n\n"
        + (
            f"Темы, которые уже назывались у этого человека: {topics}\n"
            "Если сейчас речь про ту же самую — напиши в subject ТО ЖЕ САМОЕ слово, "
            "буква в букву. Иначе это посчитается как другая тема и не сойдётся.\n\n"
            if topics else ""
        )
        + f"Что было сказано с прошлого раза:\n{said}\n\n"
        "Выпиши новое, что стоит запомнить, в требуемом JSON."
    )


def _parse_json(text: str) -> dict:
    # Tolerate accidental code fences or surrounding prose.
    if "```" in text:
        parts = text.split("```")
        if len(parts) >= 2:
            text = parts[1]
            if text.lstrip().startswith("json"):
                text = text.lstrip()[4:]
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1 or end < start:
        return {}
    try:
        data = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


async def _store(user_id: str, data: dict) -> None:
    # --- What stopped being true ---
    #
    # FIRST, before anything is added, and the order is not cosmetic. If a new
    # fact were written before the old one was retired and the two happened to
    # carry the same text, add_memory would see the old row as a live duplicate
    # and write nothing — and then the retirement would fire on the only copy
    # there was. Retiring first means the worst case is a harmless re-add.
    _retire(user_id, data.get("no_longer_true"))
    await _store_what_they_said(user_id, data)
    await _store_what_was_watched(user_id, data)


async def from_intake(user_id: str, story: str) -> None:
    """What the person told the intake, kept where their friend can use it.

    Everything the intake learned used to reach only the reading and the
    writer. The friend himself began the first conversation knowing nothing
    but a name — and could ask «а семья есть?» of somebody who had just told
    the intake about his grandfather, which is the one thing that says most
    plainly «you were not listened to». So the answers are read once, like a
    conversation, and what the person SAID is kept: facts, the people in
    their life, and whatever is coming up this week as a follow-up — the
    friend's first «ну как прошло?». Only what was said: the mood of an intake
    is not a visit, and the observation register is for what is watched in
    conversation. Never raises; the friend arrives either way.
    """
    if not config.ANTHROPIC_API_KEY or not str(story or "").strip():
        return
    said = ("ИНТЕРВЬЮ ПЕРЕД ЗНАКОМСТВОМ — спрашивало приложение, отвечал ЧЕЛОВЕК; "
            "БОБ ещё не сказал ни слова:\n" + str(story).strip())
    try:
        await _store_what_they_said(user_id, await _extract(user_id, said))
    except Exception as e:  # noqa: BLE001
        print(f"[learn] intake was not read: {e}", file=sys.stderr)


async def _store_what_they_said(user_id: str, data: dict) -> None:
    """Facts, stories, health and follow-ups — what the person told us."""
    for fact in data.get("facts") or []:
        if not isinstance(fact, dict):
            continue
        cat = (fact.get("category") or "прочее").strip()
        val = (fact.get("value") or "").strip()
        if val:
            memory.add_memory(
                user_id, "fact", f"{cat}: {val}", owner="elder", title=cat, importance=2
            )

    for story in data.get("stories") or []:
        if not isinstance(story, dict):
            continue
        title = (story.get("title") or "").strip() or None
        summary = (story.get("summary") or "").strip()
        if summary:
            emb = await _safe_embed(f"{title or ''} {summary}")
            memory.add_memory(
                user_id, "story", summary, owner="elder", title=title, embedding=emb
            )

    for note in data.get("health") or []:
        note = (note or "").strip()
        if note:
            emb = await _safe_embed(note)
            memory.add_memory(
                user_id, "health", note, owner="elder", embedding=emb, importance=2
            )

    for fup in data.get("follow_ups") or []:
        fup = (fup or "").strip()
        if fup:
            memory.add_memory(
                user_id, "follow_up", fup, owner="elder", status="open", importance=2
            )


async def _store_what_was_watched(user_id: str, data: dict) -> None:
    """Mood, observations, his own feeling, the country, what HE said and was
    taught — what a conversation shows and an intake does not."""
    # Mood arrives as an object now. A plain string is what the previous shape
    # produced, and a model occasionally still answers that way — both are read,
    # because losing a mood is worse than losing its detail.
    raw_mood = data.get("mood")
    reading = raw_mood if isinstance(raw_mood, dict) else {"word": str(raw_mood or "")}
    word = (reading.get("word") or "").strip()
    if word:
        # Still a memory row: the diary is written from these, and it should go
        # on reading like a diary and not like a chart.
        memory.add_memory(user_id, "mood", word, owner="elder")
    mood.record(user_id, reading)

    for seen in data.get("observed") or []:
        if isinstance(seen, dict):
            mood.observe(
                user_id,
                seen.get("tag") or "",
                seen.get("subject") or "",
                seen.get("evidence") or "",
            )

    # What the exchange did to HIM. A delta, usually zero, and the one thing
    # stored here that is not about the person. See feeling.py.
    bob_felt = data.get("bob")
    if isinstance(bob_felt, dict):
        feeling.record(user_id, bob_felt)

    # Where he lives, which decides what number he is told to dial if he ever
    # falls and cannot get up. Nobody fills in a settings form; people do say
    # where they live, usually early. See emergency.py.
    where = data.get("country")
    if isinstance(where, str) and where.strip():
        emergency.remember(user_id, where)

    # --- About the companion himself (consistency) ---
    for bf in data.get("bob_facts") or []:
        bf = (bf or "").strip()
        if bf:
            memory.add_memory(user_id, "fact", bf, owner="bob", importance=2)

    # What the person taught him. HIS row, not the person's: it is what this
    # friend now knows, so a parting takes it with him (erase.the_companion)
    # and the next friend does not arrive knowing another man's lessons.
    for lesson in data.get("taught_bob") or []:
        lesson = (lesson or "").strip() if isinstance(lesson, str) else ""
        if lesson:
            memory.add_memory(user_id, "lesson", lesson, owner="bob")


#: The runaway guard, and the number is a judgement rather than a round figure.
#: One real event can honestly end several rows at once — a death takes the
#: person, the follow-up about them, and whatever was recorded about their
#: health — so a cap of two or three would clip exactly the case this whole
#: mechanism exists for. Ten is not a life changing; it is a model that has
#: misread the question.
#:
#: Over the cap NOTHING is retired, not the first five. A partial apply would
#: mean acting on a batch already known to be wrong, and the safe failure here
#: is the old behaviour: the companion keeps believing what he believed, which
#: is survivable, rather than losing rows nobody can see were lost.
_MAX_RETIRED = 5


def _retire(user_id: str, claims) -> None:
    """Mark facts the person's own words have just ended. Never raises.

    Loud on purpose — same reasoning as safety.py. This is the only place that
    stops the companion believing something, so it has to be readable in a log
    by somebody asking later why he never mentioned the dog again.
    """
    if not isinstance(claims, list) or not claims:
        return
    if len(claims) > _MAX_RETIRED:
        print(
            f"[learn] refusing to retire {len(claims)} facts at once for "
            f"{user_id[:8]} — that is not a change of life, it is a misread",
            file=sys.stderr,
            flush=True,
        )
        return

    for claim in claims:
        if not isinstance(claim, dict):
            continue
        try:
            memory_id = int(claim.get("id"))
        except (TypeError, ValueError):
            continue
        why = str(claim.get("because") or "").strip()
        # supersede() is scoped to this user, so a hallucinated id belonging to
        # somebody else simply does not match — it cannot reach another person's
        # memory even in principle.
        if memory.supersede(user_id, memory_id, why):
            print(
                f"  ⊘ больше не так · {user_id[:8]} · #{memory_id} · {why[:120]}",
                file=sys.stderr,
                flush=True,
            )


async def _safe_embed(text: str) -> list[float] | None:
    if not embeddings.available() or not text.strip():
        return None
    try:
        return await embeddings.embed(text)
    except Exception:
        return None
