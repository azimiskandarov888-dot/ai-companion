"""The brain: Claude — one model for BEING him, another for WRITING him.

Every turn of conversation is a race against silence: the listener said
something and is waiting. So conversation runs on CHAT_MODEL (Haiku — fast),
with the character it plays fully written in advance. The slow, deep work —
creating the person, rewriting the diary, distilling memory — runs on
BRAIN_MODEL (Sonnet) where nobody is waiting mid-sentence.

Two further speed decisions live here:

  · The web-search tool is attached ONLY when the message actually asks about
    the current world (news, weather, prices). A tool that is merely available
    invites the model to consider it, and a search turn costs seconds. When it
    is needed, the turn runs on BRAIN_MODEL, which supports the tool — those
    turns are rare and inherently slow anyway.

  · The system prompt's stable head (behavior rules + persona) is marked for
    provider-side caching. It is identical every turn, so Claude re-reads it
    from cache instead of re-processing ~3k tokens of character each time —
    faster and about 10× cheaper for that part.
"""

from __future__ import annotations

from anthropic import AsyncAnthropic

from . import config

_client: AsyncAnthropic | None = None

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
#: now, which his own written life can't answer. Deliberately narrow: a missed
#: match just means he answers from his own head — which is what a person
#: without a phone in his hand would do anyway, and perfectly in character.
_FRESH_INFO_HINTS = (
    "новост",          # новости, новостях…
    "погод",           # погода, погоду…
    "прогноз",
    "температур",
    "курс доллара",
    "курс евро",
    "курс рубля",
    "что в мире",
    "что происходит в мире",
    "что нового в мире",
)


def wants_fresh_info(text: str) -> bool:
    """Does this message need the real, current world (news/weather/prices)?"""
    lowered = text.lower()
    return any(hint in lowered for hint in _FRESH_INFO_HINTS)


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
    client = _get_client()

    model = config.BRAIN_MODEL if fresh_info else config.CHAT_MODEL
    tools = [_WEB_SEARCH_TOOL] if fresh_info else []

    messages = list(history)
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
        # If the server-side search loop paused, feed its progress back and
        # continue; otherwise we're done.
        if message.stop_reason != "pause_turn":
            break
        messages = messages + [{"role": "assistant", "content": message.content}]

    if message is None:
        return ""
    return "".join(b.text for b in message.content if b.type == "text").strip()


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
    client = _get_client()
    text = ""
    async with client.messages.stream(
        model=config.CHAT_MODEL,
        max_tokens=config.MAX_REPLY_TOKENS,
        system=_system_blocks(system_stable, system_variable),
        messages=list(history),
        timeout=_LIVE_REPLY_TIMEOUT,
    ) as stream:
        async for event in stream:
            if event.type == "text":
                text += event.text
                yield text


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
) -> str:
    """One-shot writing call (no tools, no history).

    Used for composed writing rather than conversation: creating the friend,
    the diary about him, distilling memory. Defaults to the deep model —
    nobody is waiting mid-sentence — but `model` lets a caller pick the fast
    one for work that is broad rather than deep (sketching ten strangers),
    which keeps the arriving screen short.

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
    async with client.messages.stream(
        model=model or config.BRAIN_MODEL,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": user_text}],
        **extra,
    ) as stream:
        message = await stream.get_final_message()
    return "".join(b.text for b in message.content if b.type == "text").strip()
