"""The brain: Claude (claude-opus-4-8).

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
    async with client.messages.stream(
        model=config.BRAIN_MODEL,
        max_tokens=config.MAX_REPLY_TOKENS,
        system=system_prompt,
        messages=history,
    ) as stream:
        message = await stream.get_final_message()

    return "".join(b.text for b in message.content if b.type == "text").strip()
