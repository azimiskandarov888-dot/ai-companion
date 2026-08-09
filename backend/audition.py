#!/usr/bin/env python3
"""Hear several voices say the same line, and pick him.

    python3 audition.py --openai                 # all 8 OpenAI voices worth trying
    python3 audition.py --openai ash onyx fable  # just these
    python3 audition.py <fish-voice-id> ...      # Fish Audio voices
    python3 audition.py --text "Своя фраза" ...  # your own line

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


async def audition(voice_ids: list[str], line: str, quiet: bool, openai: bool) -> None:
    if openai:
        if not config.OPENAI_API_KEY:
            sys.exit("OPENAI_API_KEY is not set. Add it to backend/.env first.")
    elif not config.FISH_API_KEY:
        sys.exit(
            "FISH_API_KEY is not set.\n"
            "Add it to backend/.env, or use --openai to audition with the key\n"
            "you already have for the ears."
        )

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"\n  Provider:  {'OpenAI' if openai else 'Fish Audio'}")
    print(f'  Line:  "{line}"')
    print(f"  Saving to:  {OUT_DIR}\n")

    was_provider = config.TTS_PROVIDER
    was_fish_voice = config.FISH_VOICE_ID
    was_openai_voice = config.OPENAI_VOICE
    results: list[tuple[str, Path]] = []

    try:
        for i, voice_id in enumerate(voice_ids, start=1):
            # Point the real tts module at this candidate, so this goes through
            # exactly the code path the app uses — same model, same settings.
            if openai:
                config.TTS_PROVIDER = "openai"
                config.OPENAI_VOICE = voice_id
            else:
                config.TTS_PROVIDER = "fish"
                config.FISH_VOICE_ID = voice_id

            print(f"  {i}. {voice_id}")
            try:
                audio = await tts.synthesize(line)
            except Exception as e:
                print(f"     ✗ {e}\n")
                continue

            path = OUT_DIR / f"{i}-{voice_id[:12]}.mp3"
            path.write_bytes(audio)
            results.append((voice_id, path))
            print(f"     saved  {path.name}  ({len(audio) // 1024} KB)")

            if not quiet:
                play(path)
            print()
    finally:
        config.TTS_PROVIDER = was_provider
        config.FISH_VOICE_ID = was_fish_voice
        config.OPENAI_VOICE = was_openai_voice

    if not results:
        sys.exit("  Nothing was generated. Check the voice IDs and the API key.")

    print("  ── Listen again, in order, before deciding ──\n")
    for i, (voice_id, path) in enumerate(results, start=1):
        print(f"  {i}. {voice_id}")
        print(f"     {path}")

    setting = "OPENAI_VOICE" if openai else "FISH_VOICE_ID"
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
    parser.add_argument(
        "--openai", action="store_true",
        help="audition OpenAI voices using the key you already have",
    )
    parser.add_argument("--text", default=DEFAULT_LINE, help="line to say")
    parser.add_argument(
        "--quiet", action="store_true", help="save the files without playing them"
    )
    args = parser.parse_args()

    voices = args.voice_ids
    if not voices:
        if not args.openai:
            parser.error("give at least one voice ID, or use --openai")
        voices = OPENAI_VOICES

    asyncio.run(audition(voices, args.text, args.quiet, args.openai))


if __name__ == "__main__":
    main()
