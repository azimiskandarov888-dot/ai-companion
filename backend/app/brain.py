"""The brain — one model for BEING him, others for WRITING him.

Every turn of conversation is a race against silence: the listener said
something and is waiting. So conversation runs on CHAT_MODEL, with the
character it plays fully written in advance. The slow, deep work — creating
the person, rewriting the diary, distilling memory — runs on Claude
(BRAIN_MODEL and friends) where nobody is waiting mid-sentence.

WHERE A CALL GOES is read off the model id. «openai/gpt-5.6-luna» — an
OpenRouter id, with a «/» — goes to OpenRouter; a bare «claude-…» id goes to
Anthropic, as it always did. The voice is GPT-5.6 Luna through OpenRouter:
the owner's choice (2026-09-28) from 24 rehearsed first meetings — the best
Russian, the best listener, calm with somebody who answers in one word, and
among the cheapest (docs/VOICE-MODELS-REHEARSAL.md). Same prompt, same
history, same length limit as the meetings it was chosen on — sent to the
fastest place that serves it, without thinking before it speaks
(config.CHAT_PROVIDERS, config.CHAT_REASONING; docs/LATENCY.md).

Two further speed decisions live here:

  · Web search is attached ONLY when the message actually asks about the
    current world (news, weather, prices). A tool that is merely available
    invites the model to consider it, and a search turn costs seconds. On
    OpenRouter it is the `web` plugin on the same voice; on Claude, the turn
    runs on BRAIN_MODEL, which supports the tool — those turns are rare and
    inherently slow anyway.

  · The system prompt's stable head (behavior rules + persona) is marked for
    provider-side caching. It is meant to be identical every turn, so Claude
    re-reads it from cache instead of re-processing ~10,600 tokens of character
    each time — faster, and ten times cheaper for that part.

    «Meant to be» is doing real work in that sentence, which is why
    `_note_cache` below exists. A cache read costs a tenth of an input token
    and a cache write costs a quarter more than one; the distance between them
    is twelve and a half times, on the largest thing the app sends. Whether we
    are on the right side of it is a measurement, not an opinion.
"""

from __future__ import annotations

import asyncio
import json
import re
import unicodedata

import httpx
from anthropic import AsyncAnthropic

from . import config

_client: AsyncAnthropic | None = None
_router: httpx.AsyncClient | None = None
_router_loop: asyncio.AbstractEventLoop | None = None

#: OpenRouter's API. Every «vendor/model» id is sent here.
ROUTER_URL = "https://openrouter.ai/api/v1"
#: How long an idle connection is kept open. httpx's own default is FIVE
#: seconds — shorter than a person's turn — so every answer used to begin with
#: a fresh handshake, 0.4–0.6 s of it from Tashkent (measured 2026-09-29).
KEEP_OPEN = 180.0

#: How OpenRouter introduces what a web search found, when it is OpenRouter
#: that searches (Exa, for a model with no search of its own). Its default asks
#: the model to cite every source as a markdown link — and everything he writes
#: is read aloud, so a link would be spoken as an address. He says what he found
#: the way somebody at a table would.
#:
#: OpenAI's models search for themselves — OpenRouter's default for them, and
#: left that way on purpose: asked the weather in Tashkent (2026-09-28), it had
#: today's, where Exa's pages had a different day's. It does not read this
#: prompt, and it cites anyway — so the citations are taken out (_uncited).
_WEB_PROMPT = (
    "Вот что сейчас нашлось в интернете по его вопросу. Скажи главное своими "
    "словами, коротко, как человек за столом: без ссылок, без адресов сайтов и "
    "без названий источников."
)

def _foreign(ch: str) -> bool:
    """A letter — or a mark on one — from neither the Russian nor the Latin
    alphabet. Numbers and the accents Latin and Cyrillic share are not."""
    if ch.isnumeric() or "\u0300" <= ch <= "\u036f":
        return False
    if "a" <= ch <= "z" or "A" <= ch <= "Z" or "\u00c0" <= ch <= "\u024f" or "\u1e00" <= ch <= "\u1eff":
        return False
    return not ("\u0410" <= ch <= "\u044f" or ch in "Ёё")


def without_glitches(text: str) -> str:
    """WORDS FROM ANOTHER ALPHABET, taken out whole.

    Luna now and then ends a sentence with a scrap of another script — a
    glitch, not a word: «…видно особенно ясно.АҞӘА» (Abkhaz, the first
    rehearsals), «…ожидание разгрузки.อ่านข้อความเต็ม» (Thai, 2026-09-29). The
    voice would read it out. He speaks Russian, and the names of games and
    bands come in Latin letters («Riders Republic»); a word with a letter from
    any other alphabet goes — before anybody hears it, sees it or remembers it.

    Word by word, so it is safe on a reply still being written: a word can only
    turn out to be a glitch while it is the last one, and nothing before it
    moves.
    """
    kept: list[str] = []
    word: list[str] = []
    for ch in text + " ":
        if ch.isalnum() or unicodedata.category(ch).startswith("M"):
            word.append(ch)
            continue
        if not any(_foreign(c) for c in word):
            kept.extend(word)
        word = []
        kept.append(ch)
    return "".join(kept[:-1])

#: What OpenAI's own search leaves in the text: a whole citation — « ([nuz.uz]
#: (https://…))», one link or several — a link inside a sentence, whose words
#: are kept, and a bare address. Spoken, each is an address read aloud; kept,
#: it is a URL in his diary.
_CITATION = re.compile(r"\s*\((?:\s*\[[^\]\n]{0,80}\]\([^)\s]{0,500}\)[,;]?)+\s*\)")
_LINK = re.compile(r"\[([^\]\n]{1,80})\]\([^)\s]{0,500}\)")
_ADDRESS = re.compile(r"\s*\(?https?://[^\s)]+\)?")


def _uncited(text: str) -> str:
    return _ADDRESS.sub("", _LINK.sub(r"\1", _CITATION.sub("", text)))


# Capped so one question can't spiral into many searches.
_WEB_SEARCH_TOOL = {"type": "web_search_20260209", "name": "web_search", "max_uses": 3}

# THE ANTHROPIC SDK'S DEFAULT READ TIMEOUT IS 600 SECONDS. Found the hard way:
# on a degraded connection (a weak cellular hotspot backhaul, in the one case
# observed so far), the backend's own call to Claude just sits there — for up
# to ten minutes — while the phone gives up after 25–30s. The result looks
# like the app "froze": no error anywhere, because the backend hadn't failed
# yet, it was still patiently waiting. Nothing in this file bounded that call.
#
# So every LIVE call — the ones a person is standing there waiting on — gets an
# explicit timeout, comfortably under the client-side ceiling for the endpoint
# that uses it (30s on /api/talk, 25s on /api/intake/next, 12s on the
# background-voice intent) and comfortably ABOVE normal latency (Haiku without
# tools answers in a couple of seconds). It fires only when something is
# actually stuck.
#
# This is a STALL detector, not a hard cap on total duration: every call here
# goes through `.stream()` under the hood, and httpx's read timeout resets on
# every chunk received. A reply that is slow but actively arriving is never
# killed by this — only a connection producing nothing at all for this long.
# That is exactly why `think()` (reading.py) and the deep-write calls in
# matchmaker.py are left alone: they are deliberately slow, but they are
# WORKING, and a stall detector does not care how long a real answer takes.
_LIVE_REPLY_TIMEOUT = 20.0

# THE READING (think(), below) IS DELIBERATELY THE SLOWEST CALL IN THE APP —
# its own docstring calls it "worth minutes and cents" — so it does NOT get
# the tight live-reply bound above. But it was left with NO bound at all,
# which meant a dead connection during creation could hang for up to the
# SDK's 600s default, silently, while the phone's own 40s ceiling on
# /api/companion/create had already given up. That combination — one side
# unbounded, the other too short for legitimate slowness — is exactly what
# produced a real -1001 timeout on a person's first attempt to meet their
# friend.
#
# 90s is generous relative to how long a genuinely slow-but-working reading
# actually takes, and it means a truly dead connection now fails loudly
# within a minute and a half instead of ten. That matters beyond speed:
# matchmaker.py already catches a failed reading and continues without it — a
# friend built from the story alone rather than no friend at all — so
# bounding this call turns "the whole wait was wasted on a hung connection"
# into "the reading is skipped and he still arrives." The exact same
# None-must-not-reach-the-SDK-literally care from generate_text applies here.
_READING_TIMEOUT = 90.0

#: Substrings (lowercase) that mean the user is asking about the world right
#: now, which his own written life can't answer.
#:
#: WHICH WAY TO ERR, and it is not the way this list first went. A miss costs
#: nothing: he answers from his own head, which is what a person without a
#: phone in his hand would do anyway and is perfectly in character. A false
#: match costs a great deal — it attaches a search tool, switches to the slow
#: model, and takes the turn OFF the streaming path entirely (see main.py), so
#: the person waits noticeably longer. And `situations._NEWS` then tells him
#: «он правда спросил», which on a false match is simply untrue.
#:
#: Measured, the old list said yes to all of these:
#:     «температура тридцать восемь, вторые сутки»   ← a fever, routed to weather
#:     «у нас всю неделю погода дрянь»
#:     «прогноз у меня один — колено ноет, значит дождь»
#: The first of those is the one that matters: `safety.py` lists «высокий жар»
#: as a danger sign, and the same words were being read as a question about the
#: forecast. «температур» and «прогноз» are gone for that reason — both are
#: ordinary words about a body and about a hunch.
_FRESH_INFO_HINTS = (
    "новост",          # новости, новостях…
    "погод",           # погода, погоду…
    "курс доллара",
    "курс евро",
    "курс рубля",
    "что в мире",
    "что происходит в мире",
    "что нового в мире",
)

#: And the subject is not enough: he has to be ASKING. «Погода дрянь» is a man
#: complaining about the weather; «какая там погода?» is a man asking for it.
#: The difference is the whole of this feature, and it used not to be looked at.
_ASKING = (
    "?", "что ", "чего ", "как ", "кака", "какой", "какое", "какие",
    "скажи", "расскажи", "узна", "посмотри", "глянь", "не знаешь",
)


def wants_fresh_info(text: str) -> bool:
    """Does this message need the real, current world (news/weather/prices)?"""
    lowered = (text or "").lower()
    if not any(hint in lowered for hint in _FRESH_INFO_HINTS):
        return False
    return any(a in lowered for a in _ASKING)


def via_openrouter(model: str) -> bool:
    """An OpenRouter id («openai/gpt-5.6-luna») has a «/»; a Claude id does not."""
    return "/" in (model or "")


def _get_router() -> httpx.AsyncClient:
    """One client for the whole process, so each turn reuses a warm connection
    instead of paying a TLS handshake before the first word — made again only
    when the event loop it was made in has closed (a tool running asyncio.run
    twice), because a connection outliving its loop is only a source of errors."""
    global _router, _router_loop
    if not config.OPENROUTER_API_KEY:
        raise RuntimeError(
            "OPENROUTER_API_KEY is not set — the voice (OpenRouter) is not configured."
        )
    if _router is not None and _router_loop is not None and _router_loop.is_closed():
        _router = None
    if _router is None:
        try:
            _router_loop = asyncio.get_running_loop()
        except RuntimeError:
            _router_loop = None
        _router = httpx.AsyncClient(
            base_url=ROUTER_URL,
            headers={"Authorization": f"Bearer {config.OPENROUTER_API_KEY}"},
            # A stall detector, like _LIVE_REPLY_TIMEOUT on the Claude side: the
            # read timeout resets on every chunk that arrives.
            timeout=httpx.Timeout(_LIVE_REPLY_TIMEOUT, connect=10.0),
            limits=httpx.Limits(keepalive_expiry=KEEP_OPEN),
        )
    return _router


async def warm() -> None:
    """Open the line to the brain before it is needed: the handshake is paid
    while the person is still talking, not after they have finished. Free — a
    HEAD for the model list — and it never raises."""
    if not (via_openrouter(config.CHAT_MODEL) and config.OPENROUTER_API_KEY):
        return
    try:
        await _get_router().head("/models")
    except Exception:  # noqa: BLE001 — a warm-up that fails costs nothing
        pass


def _router_body(history, system_stable: str, system_variable: str, *,
                 web: bool = False) -> dict:
    """The Claude path's prompt and history, in OpenAI's shape — with what is
    true NOW placed last, after the conversation, right where the answer begins.

    Two reasons, both measured (2026-09-29):

      · A model that does not stop to think follows what it read last. With the
        turn's instructions above the whole history, Luna without reasoning
        ended 85% of replies with a question and asked five in a row, «don't
        ask a third time» sitting unread above the conversation (57% and two
        with reasoning on). Right before the answer, it is read.
      · OpenAI caches the longest prefix that repeats. The part that changes
        every turn used to sit BEFORE the history, so only the character was
        ever cached; now the character AND the conversation so far are.
    """
    messages = [{"role": "system", "content": system_stable}, *_conversation(history)]
    if system_variable.strip():
        messages.append({"role": "system", "content": system_variable})
    body: dict = {
        "model": config.CHAT_MODEL,
        "max_tokens": config.MAX_REPLY_TOKENS,
        "messages": messages,
        "stream": True,
    }
    if config.CHAT_REASONING:
        body["reasoning"] = {"effort": config.CHAT_REASONING}
    if config.CHAT_PROVIDERS:
        body["provider"] = {"order": list(config.CHAT_PROVIDERS), "allow_fallbacks": True}
    if web:
        body["plugins"] = [{"id": "web", "max_results": 3, "search_prompt": _WEB_PROMPT}]
    return body


def _router_failed(status: int, text: str) -> RuntimeError:
    """OpenRouter's refusal in words that say what to do. 402 is named because
    its own text («Prompt tokens limit exceeded») sends you to shorten a prompt
    that is fine: the account is empty."""
    if status == 402:
        return RuntimeError("OpenRouter: на счету кончились деньги (402) — "
                            "пополни openrouter.ai/credits")
    return RuntimeError(f"OpenRouter: {status} — {text[:300]}")


async def _router_reply(history, system_stable: str, system_variable: str, *,
                        web: bool) -> str:
    """The whole reply, read off the stream — as the Claude path does, and for
    the same reason: the live-reply timeout stays a stall detector. A search
    that is slow but working keeps sending; only a dead line is cut off."""
    text = ""
    async for text in _router_stream(history, system_stable, system_variable, web=web):
        pass
    # A search turn is never streamed (main.py), so its sources can be taken
    # out here, whole, before anyone hears, sees or remembers them.
    return (_uncited(text) if web else text).strip()


async def _router_stream(history, system_stable: str, system_variable: str, *,
                         web: bool = False):
    """Server-sent events: «data: {json}» lines, keep-alive comments between
    them, «data: [DONE]» at the end. Yields the text so far, as stream_reply
    does — and, if the length limit cut it, one last SHORTER value.

    Cleaning the whole text again on every yield is what keeps it safe for the
    caller that cuts sentences off it by position: a word can only turn out to
    be a glitch while it is still being written, at the very end."""
    text, finish = "", None
    body = _router_body(history, system_stable, system_variable, web=web)
    async with _get_router().stream("POST", "/chat/completions", json=body) as r:
        if r.status_code != 200:
            raise _router_failed(r.status_code, (await r.aread()).decode("utf-8", "replace"))
        async for line in r.aiter_lines():
            if not line.startswith("data:"):
                continue  # «: OPENROUTER PROCESSING» keep-alives and blank lines
            data = line[len("data:"):].strip()
            if data == "[DONE]":
                break
            chunk = json.loads(data)
            if chunk.get("error"):
                raise RuntimeError(f"OpenRouter: {chunk['error']}")
            choice = (chunk.get("choices") or [{}])[0]
            finish = choice.get("finish_reason") or finish
            piece = (choice.get("delta") or {}).get("content") or ""
            if piece:
                text += piece
                yield without_glitches(text)
    if finish == "length":
        said = without_glitches(text)
        trimmed = whole_sentences(said)
        if trimmed != said:
            yield trimmed


def _get_client() -> AsyncAnthropic:
    global _client
    if not config.ANTHROPIC_API_KEY:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set — the 'brain' (Claude) is not configured."
        )
    if _client is None:
        _client = AsyncAnthropic(api_key=config.ANTHROPIC_API_KEY)
    return _client


def _system_blocks(stable: str, variable: str) -> list[dict]:
    """The system prompt as two blocks: the unchanging character (cached) and
    today's context (fresh every turn). The split is the caching boundary —
    anything that changes per turn must stay OUT of the first block, or the
    cache misses every time and silently buys nothing.
    """
    blocks: list[dict] = [
        {
            "type": "text",
            "text": stable,
            "cache_control": {"type": "ephemeral"},
        }
    ]
    if variable.strip():
        blocks.append({"type": "text", "text": variable})
    return blocks


#: What stands before a history that begins with HIM. It does whenever he
#: spoke first — a first meeting opens with his hello, not with anything they
#: said (meeting.HELLO) — and whenever the window of recent turns happens to
#: start on one of his lines. The API's own contract is alternating turns,
#: user first; a placeholder costs nothing, and nothing stores it.
_BEFORE_HIM = {"role": "user", "content": "…"}


def _conversation(history: list[dict[str, str]]) -> list[dict[str, str]]:
    messages = list(history)
    if messages and messages[0].get("role") == "assistant":
        messages.insert(0, dict(_BEFORE_HIM))
    return messages


#: Where a sentence ends: the stop, and any closing quote or bracket after it.
_SENTENCE_END = re.compile(r"[.!?…]+[»\"')\]]*")


def whole_sentences(text: str) -> str:
    """A reply cut off by the length limit, back to its last whole sentence.

    Nothing used to look at why a reply stopped, so one that ran into
    MAX_REPLY_TOKENS was spoken exactly as it ended — «можно фантазировать с
    цвет» — which is the sound of a machine, not of somebody who has said
    what he meant. A reply with no finished sentence at all is left as it is:
    half a thought is better than silence.
    """
    ends = list(_SENTENCE_END.finditer(text))
    return text[: ends[-1].end()].rstrip() if ends else text


def _note_cache(message) -> None:
    """Say it out loud whenever the cached head had to be written again.

    A write on the FIRST turn of a conversation is correct — nothing was warm
    yet. A write on any LATER turn means something upstream of the breakpoint
    moved its bytes, and the whole character was re-processed for nothing.

    There is a named suspect, and it is why this was worth writing. The cached
    head holds `mood.standing_block`, which reads the `observations` table
    ordered by `last_ts`. The scribe writes that table from a background task
    every five exchanges (`learn.BATCH_EXCHANGES`). So a confirmed observation
    landing mid-conversation reorders those lines, changes the bytes, and
    silently turns the next turn's cheap read into a full write.

    Whether that actually happens often enough to matter is exactly the kind of
    thing this project does not guess about. One line, only when the cache is
    rewritten — quiet on a healthy turn, because a line every turn is noise and
    noise is how a real signal gets missed.

    Never raises. A measurement must not cost somebody their reply.
    """
    try:
        usage = getattr(message, "usage", None)
        wrote = getattr(usage, "cache_creation_input_tokens", 0) or 0
        if not wrote:
            return
        read = getattr(usage, "cache_read_input_tokens", 0) or 0
        print(f"[кэш] перезапись {wrote} токенов (прочитано {read})", flush=True)
    except Exception as e:  # noqa: BLE001
        print(f"[кэш] не смог посмотреть: {e}", flush=True)


async def generate_reply(
    history: list[dict[str, str]],
    system_stable: str,
    system_variable: str = "",
    *,
    fresh_info: bool = False,
) -> str:
    """Produce his spoken reply.

    history:          [{"role": "user"|"assistant", "content": str}, …], oldest
                      first, ending with the latest user message.
    system_stable:    who he is — identical every turn, cached provider-side.
    system_variable:  what today holds — memory context, occasion, mood.
    fresh_info:       the message asks about the current world → attach web
                      search and run on the bigger model that supports it.
    """
    if via_openrouter(config.CHAT_MODEL):
        return await _router_reply(history, system_stable, system_variable, web=fresh_info)

    client = _get_client()

    model = config.BRAIN_MODEL if fresh_info else config.CHAT_MODEL
    tools = [_WEB_SEARCH_TOOL] if fresh_info else []

    messages = _conversation(history)
    message = None
    for _ in range(3):  # allow a couple of server-side web-search continuations
        async with client.messages.stream(
            model=model,
            max_tokens=config.MAX_REPLY_TOKENS,
            system=_system_blocks(system_stable, system_variable),
            messages=messages,
            tools=tools,
            timeout=_LIVE_REPLY_TIMEOUT,
        ) as stream:
            message = await stream.get_final_message()
        _note_cache(message)
        # If the server-side search loop paused, feed its progress back and
        # continue; otherwise we're done.
        if message.stop_reason != "pause_turn":
            break
        messages = messages + [{"role": "assistant", "content": message.content}]

    if message is None:
        return ""
    text = "".join(b.text for b in message.content if b.type == "text").strip()
    return whole_sentences(text) if message.stop_reason == "max_tokens" else text


async def stream_reply(
    history: list[dict[str, str]],
    system_stable: str,
    system_variable: str = "",
):
    """The same reply as `generate_reply`, but handed over as it is written.

    Yields the text so far, growing — the caller decides where to cut it (see
    tts.speakable_chunks). Yielding the accumulated text rather than raw deltas
    is deliberate: a delta can be half a word or a lone comma, and every caller
    would otherwise have to reassemble it before it could look for a sentence.

    Web search is NOT available here. That path runs several rounds with
    server-side pauses between them, and there is no honest way to speak the
    first sentence of an answer that might still change once the search comes
    back. Those turns are rare and inherently slow, so main.py sends them down
    the whole-reply path instead.
    """
    if via_openrouter(config.CHAT_MODEL):
        async for text in _router_stream(history, system_stable, system_variable):
            yield text
        return

    client = _get_client()
    text = ""
    async with client.messages.stream(
        model=config.CHAT_MODEL,
        max_tokens=config.MAX_REPLY_TOKENS,
        system=_system_blocks(system_stable, system_variable),
        messages=_conversation(history),
        timeout=_LIVE_REPLY_TIMEOUT,
    ) as stream:
        async for event in stream:
            if event.type == "text":
                text += event.text
                yield text
        # The reply is out and nobody is waiting on this. Guarded separately
        # from `_note_cache`: asking a finished stream for its final message is
        # its own way to fail, and neither failure may reach the listener.
        try:
            final = await stream.get_final_message()
            _note_cache(final)
        except Exception as e:  # noqa: BLE001
            print(f"[кэш] не смог посмотреть: {e}", flush=True)
            final = None
    # CUT OFF BY THE LENGTH LIMIT: one last, SHORTER value — the reply back to
    # its last whole sentence. The caller speaks finished sentences as they
    # come and the unfinished tail only after the stream ends, so the tail is
    # simply never spoken, and what is remembered is what was meant.
    if final is not None and final.stop_reason == "max_tokens":
        trimmed = whole_sentences(text)
        if trimmed != text:
            yield trimmed


async def think(
    system_prompt: str,
    user_text: str,
    *,
    model: str | None = None,
    effort: str = "high",
    max_tokens: int = 8000,
    timeout: float | None = _READING_TIMEOUT,
) -> str:
    """One deep call, with the model actually allowed to think first.

    Used for the reading (reading.py) and nothing else so far. `generate_text`
    below is the fast one-shot; this is the one where quality is worth minutes
    and cents, because it runs once per person and everything is built on it.

    Adaptive thinking lets the model decide how long to think per input — a
    three-line story doesn't need what a page-long one does. `effort` sets the
    ceiling on that. `max_tokens` caps thinking AND the answer together, so it
    is generous here; too tight and the reading truncates mid-sentence.

    `timeout` defaults to _READING_TIMEOUT rather than to None — unlike
    generate_text, this call has exactly one caller today and leaving it truly
    unbounded already cost someone their entire wait on a hung connection.
    Pass `timeout=None` explicitly for the old fully-unbounded behaviour; as
    in generate_text, that omits the kwarg entirely rather than handing the
    SDK a literal `None`, which httpx reads as "never time out" — stricter
    than even its own default.
    """
    client = _get_client()
    extra = {"timeout": timeout} if timeout is not None else {}
    async with client.messages.stream(
        model=model or config.BRAIN_MODEL,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": user_text}],
        thinking={"type": "adaptive"},
        output_config={"effort": effort},
        **extra,
    ) as stream:
        message = await stream.get_final_message()
    return "".join(b.text for b in message.content if b.type == "text").strip()


async def generate_text(
    system_prompt: str,
    user_text: str,
    max_tokens: int = 1500,
    model: str | None = None,
    timeout: float | None = None,
    effort: str | None = None,
) -> str:
    """One-shot writing call (no tools, no history).

    Used for composed writing rather than conversation: creating the friend,
    the diary about him, distilling memory. Defaults to the deep model —
    nobody is waiting mid-sentence — but `model` lets a caller pick the fast
    one for work that is broad rather than deep (sketching ten strangers),
    which keeps the arriving screen short.

    `effort` is how much deliberation the model may spend before answering, and
    it exists for the case where the best MODEL is wanted without the waiting
    that its default depth would cost — ten one-paragraph strangers need a good
    imagination, not a long think (matchmaker). Omitted entirely when not
    given, so every existing caller keeps the model's own default.

    `timeout` is None by default, meaning the SDK's own generous read timeout
    — so creating a friend or rewriting the diary is never cut short (see
    _LIVE_REPLY_TIMEOUT above for why that would be wrong here). A caller in a
    live conversation with a real ceiling to respect — intake.py is the one
    that exists so far — passes an explicit value comfortably under it.

    IMPORTANT: `None` here is only ever a Python default meaning "not passed".
    It must never reach the SDK call as a literal `timeout=None` — to httpx
    that means "no timeout, ever," which is a stricter promise than even the
    SDK's own default and would quietly remove the ceiling this whole file
    exists to add. So the kwarg is omitted entirely unless a real number was
    given, leaving the SDK to see its own unset default and behave exactly as
    it always has for every caller that doesn't ask for a bound.
    """
    client = _get_client()
    extra = {"timeout": timeout} if timeout is not None else {}
    if effort:
        extra["output_config"] = {"effort": effort}
    async with client.messages.stream(
        model=model or config.BRAIN_MODEL,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": user_text}],
        **extra,
    ) as stream:
        message = await stream.get_final_message()
    return "".join(b.text for b in message.content if b.type == "text").strip()
