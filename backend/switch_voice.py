#!/usr/bin/env python3
"""Change which company provides his voice — one word, one command.

    python switch_voice.py openai      # uses the OpenAI key you already have
    python switch_voice.py fish        # Fish Audio
    python switch_voice.py yandex      # Yandex SpeechKit
    python switch_voice.py             # just tells you what's set now

Why this exists: the voice is the ONE part of the app that has a real
alternative already paid for. The ears (Whisper) and the brain (Claude) each
have exactly one supplier, so if either is broken you have to fix it. The voice
does not — OpenAI does text-to-speech with the *same key* that already does the
ears. So when the voice is the thing that's broken, you are never stuck: you
switch suppliers and he talks today.

It changes exactly ONE line in .env — the line that names the provider. It
never reads, prints, moves, or touches an API key, and every other line in the
file comes out byte for byte identical.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ENV_PATH = Path(__file__).resolve().parent / ".env"

PROVIDERS = {
    "openai": "OpenAI — тем же ключом, что уже слушает. Ничего не нужно заводить.",
    "fish": "Fish Audio — нужен FISH_API_KEY.",
    "yandex": "Yandex SpeechKit — нужны YANDEX_API_KEY и YANDEX_FOLDER_ID.",
    "elevenlabs": "ElevenLabs — лучшее качество и самая дорогая.",
    "none": "Никакой — телефон озвучит сам, бесплатно и хуже.",
}


def read_lines() -> list[str]:
    if not ENV_PATH.exists():
        sys.exit(
            f"Файла {ENV_PATH} нет.\n\n"
            "Он создаётся из образца:\n"
            "    cp .env.example .env\n"
            "и туда вписываются ключи."
        )
    return ENV_PATH.read_text(encoding="utf-8").splitlines(keepends=True)


def current_provider(lines: list[str]) -> str:
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("TTS_PROVIDER="):
            return stripped.split("=", 1)[1].strip().strip("\"'").lower() or "none"
    return "fish"  # what config.py falls back to when the line is absent


def write_provider(lines: list[str], provider: str) -> None:
    """Replace the TTS_PROVIDER line, or add one. Nothing else is touched."""
    new_line = f"TTS_PROVIDER={provider}\n"
    replaced = False
    out: list[str] = []

    for line in lines:
        if line.strip().startswith("TTS_PROVIDER=") and not replaced:
            out.append(new_line)
            replaced = True
        else:
            out.append(line)

    if not replaced:
        if out and not out[-1].endswith("\n"):
            out[-1] += "\n"
        out.append(new_line)

    ENV_PATH.write_text("".join(out), encoding="utf-8")


def try_speaking(provider: str) -> bool:
    """Say two words for real, so the answer isn't a guess.

    Import happens here, AFTER .env is written, so the reload picks up the new
    line rather than whatever was set when this script started.
    """
    if provider == "none":
        print("\n🗣️  Голос выключен — телефон озвучит сам. Это бесплатно.")
        return True

    from app import config, tts

    config.TTS_PROVIDER = provider  # config already read .env; point it at the new one

    if not config.tts_configured():
        print(f"\n⚠️  Для «{provider}» не хватает ключа в .env.")
        print(f"    {PROVIDERS[provider]}")
        return False

    print(f"\nПробую сказать вслух голосом «{provider}»…")
    try:
        audio = asyncio.run(tts.synthesize("Проверка связи."))
    except Exception as error:  # noqa: BLE001 — a report, not a crash
        print(f"\n❌ Не получилось:\n   {error}\n")
        if provider != "openai":
            print("   Совет: попробуйте  python switch_voice.py openai")
            print("   — это тот же ключ, которым он уже вас слышит.\n")
        return False

    print(f"✅ Голос работает ({len(audio) // 1024} КБ звука).")
    return True


def main() -> None:
    lines = read_lines()
    now = current_provider(lines)

    if len(sys.argv) < 2:
        print(f"\nСейчас голос: {now}")
        print(f"  {PROVIDERS.get(now, '')}\n")
        print("Поменять:  python switch_voice.py openai")
        print("Варианты:  " + " · ".join(PROVIDERS) + "\n")
        return

    wanted = sys.argv[1].strip().lower()
    if wanted not in PROVIDERS:
        sys.exit(
            f"Не знаю голос «{wanted}».\n"
            "Варианты: " + " · ".join(PROVIDERS)
        )

    if wanted == now:
        print(f"\nГолос уже «{now}» — ничего менять не надо.")
    else:
        write_provider(lines, wanted)
        print(f"\n✏️  В .env поменял одну строку:  TTS_PROVIDER={wanted}")
        print("   Ключи не тронуты.")

    ok = try_speaking(wanted)

    print()
    if ok:
        print("Теперь перезапустите сервер, чтобы он это увидел:")
        print("   1. в окне, где идёт ./run.sh — нажмите Control и C вместе")
        print("   2. наберите  ./run.sh  и Enter")
    else:
        print("Исправьте написанное выше и запустите ещё раз.")
    print()


if __name__ == "__main__":
    main()
