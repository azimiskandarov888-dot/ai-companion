"""The brain: Claude (model from config — Sonnet 5 by default, for speed).

Given the conversation and a fully-assembled system prompt (behavior + persona +
memory), it produces Bob's spoken reply in warm, simple Russian. Replies are
intentionally short — they will be spoken aloud to an elderly listener.

The system prompt is built by the caller (main.py, via companion.build_system_prompt)
so this module stays focused on the API call.
"""

from __future__ import annotations

from anthropic import AsyncAnthropic

from . import config

_client: AsyncAnthropic | None = None

# Web search lets Bob share real, current news and weather when the elder asks —
# woven into his own casual talk (see companion.py "НОВОСТИ И ПОГОДА"). Claude
# only uses it when current info is genuinely needed, so ordinary chat adds no
# search latency or cost. Capped so one question can't spiral into many searches.
# (web_search_20260209 is supported on the default model, Sonnet 5, and on Opus.)
_WEB_SEARCH_TOOL = {"type": "web_search_20260209", "name": "web_search", "max_uses": 3}


def _get_client() -> AsyncAnthropic:
    global _client
    if not config.ANTHROPIC_API_KEY:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set — the 'brain' (Claude) is not configured."
        )
    if _client is None:
        _client = AsyncAnthropic(api_key=config.ANTHROPIC_API_KEY)
    return _client


async def generate_reply(
    history: list[dict[str, str]],
    system_prompt: str,
) -> str:
    """Produce Bob's spoken reply.

    history: list of {"role": "user"|"assistant", "content": str}, oldest first,
             ending with the latest user message.
    system_prompt: the fully-assembled system prompt.
    """
    client = _get_client()

    # Streaming keeps us safe against timeouts and lets us add sentence-level
    # TTS streaming later. For now we collect the full reply.
    messages = list(history)
    message = None
    for _ in range(3):  # allow a couple of server-side web-search continuations
        async with client.messages.stream(
            model=config.BRAIN_MODEL,
            max_tokens=config.MAX_REPLY_TOKENS,
            system=system_prompt,
            messages=messages,
            tools=[_WEB_SEARCH_TOOL],
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
    """One-shot writing call (no tools, no history).

    Used for composed writing rather than conversation: the companion's diary
    about his friend, and creating the friend from the user's story.
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
