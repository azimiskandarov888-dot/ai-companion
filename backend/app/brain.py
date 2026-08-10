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


async def generate_text(
    system_prompt: str, user_text: str, max_tokens: int = 1500
) -> str:
    """One-shot writing call (no tools, no history) — always the deep model.

    Used for composed writing rather than conversation: creating the friend,
    the diary about him, distilling memory. Nobody is waiting mid-sentence.
    """
    client = _get_client()
    async with client.messages.stream(
        model=config.BRAIN_MODEL,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": user_text}],
    ) as stream:
        message = await stream.get_final_message()
    return "".join(b.text for b in message.content if b.type == "text").strip()
