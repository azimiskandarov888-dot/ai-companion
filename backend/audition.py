#!/usr/bin/env python3
"""Hear several voices say the same line, and pick him.

    python3 audition.py --yandex                 # Russian voices, made for Russian
    python3 audition.py --openai                 # uses the key you already have
    python3 audition.py --eleven <voice-id> ...  # the best quality, priciest
    python3 audition.py <fish-voice-id> ...      # Fish Audio
    python3 audition.py --openai --text "Своя фраза"

Why not just use the samples on fish.audio: those are whatever text the voice's
creator chose — often theatrical, often not even Russian. They are good enough
to reject a voice and not good enough to choose one.

This puts every candidate through EXACTLY the path the app uses (app/tts.py), on
exactly the kind of sentence he will really say, so what you hear in this
audition is what your users will hear. Files are kept, so you can go back and
compare a day later rather than trusting your memory of the third one.

Needs the key for whichever provider you are auditioning. Each line costs a
fraction of a cent either way.
"""

from __future__ import annotations

import argparse
import asyncio
import platform
import subprocess
import sys
from pathlib import Path

from app import config, tts

# A line chosen to expose the things that make a voice feel synthetic:
#
#   · a greeting          — where fake warmth is most obvious
#   · a question          — does the pitch actually rise, or is it recited?
#   · a dash and a comma  — does it breathe, or run straight through?
#   · an ordinary thought — the real test. Drama is easy; ordinary is hard.
#
# If a voice survives this sentence it will survive the app.
DEFAULT_LINE = (
    "Доброе утро. Как спалось? "
    "Мне сегодня снилось море — не знаю почему, я ведь там никогда не был."
)

OUT_DIR = config.DATA_DIR / "auditions"

#: The OpenAI voices worth auditioning for an older Russian man, roughly in the
#: order I would try them. `ash` and `onyx` are the deeper, steadier ones;
#: `fable` and `ballad` are gentler; the rest are here so you can hear the range
#: rather than take my word for it.
OPENAI_VOICES = ["ash", "onyx", "fable", "ballad", "echo", "sage", "verse", "alloy"]

#: Yandex's male voices, best first. The `:premium` variants are noticeably
#: better and cost a little more — worth hearing both of the same voice.
YANDEX_VOICES = [
    "filipp:premium", "zahar:premium", "ermil:premium", "anton:premium",
    "filipp", "zahar", "ermil",
]


def play(path: Path) -> None:
    """Play it, on whichever machine this is."""
    system = platform.system()
    try:
        if system == "Darwin":
            subprocess.run(["afplay", str(path)], check=False)
        elif system == "Linux":
            for player in ("paplay", "aplay", "ffplay"):
                if subprocess.run(["which", player], capture_output=True).returncode == 0:
                    args = [player, str(path)]
                    if player == "ffplay":
                        args = ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", str(path)]
                    subprocess.run(args, check=False)
                    return
            print("   (no audio player found — open the file yourself)")
        else:
            print("   (open the file yourself to listen)")
    except Exception:
        print("   (couldn't play it — the file is saved, open it yourself)")


async def audition(voice_ids: list[str], line: str, quiet: bool, provider: str) -> None:
    needs = {
        "openai": (config.OPENAI_API_KEY, "OPENAI_API_KEY"),
        "yandex": (config.YANDEX_API_KEY and config.YANDEX_FOLDER_ID,
                   "YANDEX_API_KEY and YANDEX_FOLDER_ID"),
        "elevenlabs": (config.ELEVENLABS_API_KEY, "ELEVENLABS_API_KEY"),
        "fish": (config.FISH_API_KEY, "FISH_API_KEY"),
    }
    have, name = needs[provider]
    if not have:
        sys.exit(
            f"{name} is not set — add it to backend/.env.\n"
            "Or use --openai, which works with the key you already have for the ears."
        )

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"\n  Provider:  {provider}")
    print(f'  Line:  "{line}"')
    print(f"  Saving to:  {OUT_DIR}\n")

    was = (config.TTS_PROVIDER, config.FISH_VOICE_ID, config.OPENAI_VOICE,
           config.YANDEX_VOICE, config.ELEVENLABS_VOICE_ID)
    results: list[tuple[str, Path]] = []

    try:
        for i, voice_id in enumerate(voice_ids, start=1):
            # Point the real tts module at this candidate, so this goes through
            # exactly the code path the app uses — same model, same settings.
            config.TTS_PROVIDER = provider
            if provider == "openai":
                config.OPENAI_VOICE = voice_id
            elif provider == "yandex":
                config.YANDEX_VOICE = voice_id
            elif provider == "elevenlabs":
                config.ELEVENLABS_VOICE_ID = voice_id
            else:
                config.FISH_VOICE_ID = voice_id

            print(f"  {i}. {voice_id}")
            try:
                audio = await tts.synthesize(line)
            except Exception as e:
                print(f"     ✗ {e}\n")
                continue

            safe = voice_id.replace(":", "-")[:16] or "default"
            path = OUT_DIR / f"{provider}-{i}-{safe}.mp3"
            path.write_bytes(audio)
            results.append((voice_id, path))
            print(f"     saved  {path.name}  ({len(audio) // 1024} KB)")

            if not quiet:
                play(path)
            print()
    finally:
        (config.TTS_PROVIDER, config.FISH_VOICE_ID, config.OPENAI_VOICE,
         config.YANDEX_VOICE, config.ELEVENLABS_VOICE_ID) = was

    if not results:
        sys.exit("  Nothing was generated. Check the voice IDs and the API key.")

    print("  ── Listen again, in order, before deciding ──\n")
    for i, (voice_id, path) in enumerate(results, start=1):
        print(f"  {i}. {voice_id}")
        print(f"     {path}")

    setting = {
        "openai": "OPENAI_VOICE",
        "yandex": "YANDEX_VOICE",
        "elevenlabs": "ELEVENLABS_VOICE_ID",
        "fish": "FISH_VOICE_ID",
    }[provider]
    print(
        "\n  Ask of each one:\n"
        "    · Would you believe this person is in the room?\n"
        "    · Does the question sound asked, or recited?\n"
        "    · Could you listen to it for an hour?\n"
        f"\n  Then put the winner in backend/.env as {setting}.\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Hear several voices say the same line, and pick him."
    )
    parser.add_argument(
        "voice_ids", nargs="*",
        help="voice IDs (Fish) or voice names (OpenAI). Empty with --openai "
             "auditions the whole shortlist.",
    )
    parser.add_argument("--openai", action="store_true",
                        help="OpenAI voices — uses the key you already have")
    parser.add_argument("--yandex", action="store_true",
                        help="Yandex SpeechKit — Russian voices made for Russian")
    parser.add_argument("--eleven", action="store_true",
                        help="ElevenLabs — the best quality, and the priciest")
    parser.add_argument("--text", default=DEFAULT_LINE, help="line to say")
    parser.add_argument(
        "--quiet", action="store_true", help="save the files without playing them"
    )
    args = parser.parse_args()

    provider = ("openai" if args.openai else
                "yandex" if args.yandex else
                "elevenlabs" if args.eleven else "fish")

    voices = args.voice_ids
    if not voices:
        defaults = {"openai": OPENAI_VOICES, "yandex": YANDEX_VOICES}
        if provider not in defaults:
            parser.error(
                f"give at least one voice ID for {provider}, "
                "or use --openai / --yandex to hear a ready-made shortlist"
            )
        voices = defaults[provider]

    asyncio.run(audition(voices, args.text, args.quiet, provider))


if __name__ == "__main__":
    main()
