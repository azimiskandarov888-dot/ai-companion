"""The brain: Claude (claude-opus-4-8).

Holds the companion's personality, reads memory before each reply, and answers
in warm, simple Russian. Replies are intentionally short — they will be spoken
aloud to an elderly listener.
"""

from __future__ import annotations

from anthropic import AsyncAnthropic

from . import companion, config

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
    memory_context: str = "",
    facts_context: str = "",
) -> str:
    """Given the conversation so far, produce the companion's spoken reply.

    history: list of {"role": "user"|"assistant", "content": str}, oldest first,
             ending with the latest user message.
    """
    client = _get_client()
    system_prompt = companion.build_system_prompt(
        memory_context=memory_context, facts_context=facts_context
    )

    # Streaming keeps us safe against timeouts and lets us add sentence-level
    # TTS streaming later. For now we collect the full reply.
    async with client.messages.stream(
        model=config.BRAIN_MODEL,
        max_tokens=config.MAX_REPLY_TOKENS,
        system=system_prompt,
        messages=history,
    ) as stream:
        message = await stream.get_final_message()

    reply_parts = [
        block.text for block in message.content if block.type == "text"
    ]
    return "".join(reply_parts).strip()
