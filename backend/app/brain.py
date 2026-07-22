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


async def compose_opening(
    stage_direction: str,
    memory_context: str = "",
    facts_context: str = "",
) -> str:
    """Compose a proactive opener (good morning / spontaneous) — the companion
    speaks first. `stage_direction` describes the moment (time, occasion, a warm
    memory to raise, a follow-up to ask) in Russian.
    """
    client = _get_client()
    system_prompt = companion.build_system_prompt(
        memory_context=memory_context, facts_context=facts_context
    )
    system_prompt += (
        "\n\nСЕЙЧАС ТЫ НАЧИНАЕШЬ РАЗГОВОР ПЕРВЫМ. Поздоровайся тепло, коротко и "
        "по-человечески (1–3 коротких предложения). Не вываливай всё сразу — "
        "выбери что-то одно тёплое, с чего начать беседу."
    )

    async with client.messages.stream(
        model=config.BRAIN_MODEL,
        max_tokens=config.MAX_REPLY_TOKENS,
        system=system_prompt,
        messages=[{"role": "user", "content": stage_direction}],
    ) as stream:
        message = await stream.get_final_message()

    return "".join(b.text for b in message.content if b.type == "text").strip()
