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

Robust by design: if extraction or parsing fails, we skip learning for that
turn — the conversation itself is never affected.
"""

from __future__ import annotations

import json
import sys

from anthropic import AsyncAnthropic

from . import config, embeddings, memory, mood

_client: AsyncAnthropic | None = None


def _get_client() -> AsyncAnthropic:
    global _client
    if _client is None:
        _client = AsyncAnthropic(api_key=config.ANTHROPIC_API_KEY)
    return _client


_EXTRACTION_SYSTEM = """Ты ведёшь память для тёплого друга-собеседника (его зовут Боб) и его пожилого собеседника.
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
  "observed": [{"tag": "из списка ниже", "subject": "о чём именно, если применимо", "evidence": "короткая цитата"}],
  "follow_ups": ["о чём по-доброму спросить ЧЕЛОВЕКА в следующий раз (незаконченные дела, переживания, планы)"],
  "bob_facts": ["новые устойчивые детали, которые БОБ рассказал О СВОЕЙ жизни (имена, места, факты) — чтобы он не противоречил себе потом"]
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

Записывай настоящее, не выдумывай. Пропускай только пустую болтовню («да», «хорошо», «ага»). Всё значимое о человеке — сохраняй, но коротко."""


async def learn_from_exchange(
    user_id: str, user_text: str, assistant_text: str
) -> None:
    """Distil one exchange into ONE person's memory.

    This runs as a background task, after the reply has already been sent, so
    nothing here can be traced back to a request. `user_id` is carried in
    explicitly for that reason: there is no ambient "current user" to fall
    back on, and inventing one would file this conversation under a stranger.
    """
    if not config.ANTHROPIC_API_KEY:
        return
    try:
        data = await _extract(user_id, user_text, assistant_text)
    except Exception as e:  # never let learning crash the request lifecycle
        print(f"[learn] extraction failed: {e}", file=sys.stderr)
        return

    try:
        await _store(user_id, data)
    except Exception as e:
        print(f"[learn] storing failed: {e}", file=sys.stderr)


async def _extract(user_id: str, user_text: str, assistant_text: str) -> dict:
    client = _get_client()
    known_elder = memory.facts_context(user_id, "elder") or "(пока ничего)"
    known_bob = memory.bob_self_context(user_id) or "(пока ничего)"
    prompt = (
        f"Что уже известно о ЧЕЛОВЕКЕ (не повторяй это):\n{known_elder}\n\n"
        f"Что уже известно о БОБЕ (не повторяй это):\n{known_bob}\n\n"
        f"Последний обмен репликами:\n"
        f"ЧЕЛОВЕК: {user_text}\n"
        f"БОБ: {assistant_text}\n\n"
        "Выпиши новое, что стоит запомнить, в требуемом JSON."
    )
    message = await client.messages.create(
        model=config.BRAIN_MODEL,
        max_tokens=800,
        system=_EXTRACTION_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(b.text for b in message.content if b.type == "text").strip()
    return _parse_json(text)


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
    # --- About the person ---
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

    for fup in data.get("follow_ups") or []:
        fup = (fup or "").strip()
        if fup:
            memory.add_memory(
                user_id, "follow_up", fup, owner="elder", status="open", importance=2
            )

    # --- About the companion himself (consistency) ---
    for bf in data.get("bob_facts") or []:
        bf = (bf or "").strip()
        if bf:
            memory.add_memory(user_id, "fact", bf, owner="bob", importance=2)


async def _safe_embed(text: str) -> list[float] | None:
    if not embeddings.available() or not text.strip():
        return None
    try:
        return await embeddings.embed(text)
    except Exception:
        return None
