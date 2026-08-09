#!/usr/bin/env python3
"""Hear several voices say the same line, and pick him.

    python3 audition.py <voice-id> <voice-id> ...
    python3 audition.py --text "Своя фраза" <voice-id> ...

Why not just use the samples on fish.audio: those are whatever text the voice's
creator chose — often theatrical, often not even Russian. They are good enough
to reject a voice and not good enough to choose one.

This puts every candidate through EXACTLY the path the app uses (app/tts.py), on
exactly the kind of sentence he will really say, so what you hear in this
audition is what your users will hear. Files are kept, so you can go back and
compare a day later rather than trusting your memory of the third one.

Needs FISH_API_KEY in .env. Each audition line costs a fraction of a cent.
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


async def audition(voice_ids: list[str], line: str, quiet: bool) -> None:
    if not config.FISH_API_KEY:
        sys.exit(
            "FISH_API_KEY is not set.\n"
            "Add it to backend/.env first — see docs/BACKGROUND-VOICE-TEST.md."
        )

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f'\n  Line:  "{line}"')
    print(f"  Saving to:  {OUT_DIR}\n")

    original = config.FISH_VOICE_ID
    results: list[tuple[str, Path]] = []

    try:
        for i, voice_id in enumerate(voice_ids, start=1):
            # Point the real tts module at this candidate, so this goes through
            # exactly the code path the app uses — same model, same settings.
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
        config.FISH_VOICE_ID = original

    if not results:
        sys.exit("  Nothing was generated. Check the voice IDs and the API key.")

    print("  ── Listen again, in order, before deciding ──\n")
    for i, (voice_id, path) in enumerate(results, start=1):
        print(f"  {i}. {voice_id}")
        print(f"     {path}")

    print(
        "\n  Ask of each one:\n"
        "    · Would you believe this person is in the room?\n"
        "    · Does the question sound asked, or recited?\n"
        "    · Could you listen to it for an hour?\n"
        "\n  Then put the winner in backend/.env as FISH_VOICE_ID.\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Hear several Fish Audio voices say the same line."
    )
    parser.add_argument("voice_ids", nargs="+", help="Fish Audio voice IDs")
    parser.add_argument("--text", default=DEFAULT_LINE, help="line to say")
    parser.add_argument(
        "--quiet", action="store_true", help="save the files without playing them"
    )
    args = parser.parse_args()

    asyncio.run(audition(args.voice_ids, args.text, args.quiet))


if __name__ == "__main__":
    main()
