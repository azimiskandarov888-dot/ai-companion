#!/usr/bin/env python3
"""Hear several voices say the same line, and pick him.

    python3 audition.py --compare                # ALL configured providers, side by side
    python3 audition.py --yandex                 # Russian voices, made for Russian
    python3 audition.py --openai                 # uses the key you already have
    python3 audition.py --eleven <voice-id> ...  # warmest, and the priciest
    python3 audition.py <fish-voice-id> ...      # Fish Audio
    python3 audition.py --openai --text "Своя фраза"
    python3 audition.py --cost                   # what each one costs, in Russian

Why not just use the samples on the providers' sites: those are whatever text
the voice's creator chose — often theatrical, often not even Russian. They are
good enough to reject a voice and not good enough to choose one.

This puts every candidate through EXACTLY the path the app uses (app/tts.py), on
exactly the kind of sentence he will really say, so what you hear in this
audition is what your users will hear. Files are kept, so you can go back and
compare a day later rather than trusting your memory of the third one.

── FINDING FISH VOICES ─────────────────────────────────────────────────────

fish.audio/discovery is the library. Open a voice, copy its model id (it is in
the page URL, and there is a copy button), and pass it here as a positional
argument. That id is what goes in FISH_VOICE_ID.

Do read --cost before settling on Fish for Russian.

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

#: Yandex voices to try, best guess first.
#:
#: These are CANDIDATES, not a promise. Yandex's published voice lists and its
#: actual API have drifted apart — the `:premium` suffix that half the
#: documentation still shows (`filipp:premium`) is rejected outright with a
#: 400, and which names exist appears to vary by account. So the list is
#: deliberately wide and a rejection is not an error: it prints one quiet line
#: and moves on, and the summary at the end tells you what your account really
#: has. Trust that summary over any list, including this one.
#:
#: `filipp` and `alena` are the premium-tier voices — no suffix, just the name.
#: The rest are standard tier, which is half the price and audibly so.
#: BOTH genders, because you need to choose two. About half the companions the
#: app invents are women (matchmaker.py), and each phone's friend speaks in
#: whichever voice matches — YANDEX_VOICE and YANDEX_VOICE_FEMALE.
YANDEX_VOICES = [
    # male
    "filipp",       # believed premium tier
    "ermil",
    "zahar",
    "madirus",
    "anton",
    "alexander",
    "kirill",
    # female
    "alena",        # believed premium tier
    "jane",
    "omazh",
    "oksana",
]

#: One voice per provider for the side-by-side. The point of --compare is to
#: answer "which of these should I even be shortlisting", so it wants the best
#: guess from each camp, not every voice in one.
COMPARE = [
    ("yandex", "filipp:premium"),
    ("yandex", "filipp"),
    ("openai", "ash"),
    ("fish", config.FISH_VOICE_ID or ""),
    ("elevenlabs", config.ELEVENLABS_VOICE_ID or ""),
]

# ── What an hour of him actually costs ──────────────────────────────────────
#
# Every provider quotes a headline price per character, or per "1M UTF-8
# bytes", and for English those are the same number. For Russian they are not:
# Cyrillic is TWO bytes per character, so anyone billing bytes charges double
# their advertised rate here, on every sentence, forever. That single fact
# reorders the whole list.
#
# ~55 000 characters is about an hour of speech.
CHARS_PER_HOUR = 55_000

#: (label, roubles per 1M chars | None, dollars per 1M chars | None, note)
COSTS = [
    ("yandex  (standard)", 600, None, "Russian-made voices. The cheapest, by a distance."),
    ("yandex  (premium)", 1200, None, "Noticeably better. Still cheaper than the rest."),
    ("openai  gpt-4o-mini-tts", None, 13.0, "Same key as the ears. Takes a direction on HOW to speak."),
    ("fish    s1 / s2-pro", None, 30.0, "$15 per 1M BYTES — and Russian is 2 bytes a letter."),
    ("elevenlabs", None, 150.0, "Warmest of the lot, and it shows up on the bill."),
]


def show_costs() -> None:
    print("\n  What one hour of his voice costs, in RUSSIAN:\n")
    for label, rub, usd, note in COSTS:
        hour = (
            f"{rub * CHARS_PER_HOUR / 1_000_000:>6.0f} ₽/час"
            if rub is not None
            else f"{usd * CHARS_PER_HOUR / 1_000_000:>6.2f} $/час"
        )
        print(f"  {label:<26} {hour}   {note}")
    print(
        "\n  A person using their whole daily allowance is on the order of 1.5M\n"
        "  characters a month. That is roughly $45 on Fish and roughly $11 on\n"
        "  Yandex standard — the difference between the voice eating the\n"
        "  subscription and the voice being a rounding error.\n"
        "\n  None of that decides it. Listen first: --compare.\n"
    )


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


NEEDS = {
    "openai": (lambda: bool(config.OPENAI_API_KEY), "OPENAI_API_KEY"),
    "yandex": (lambda: bool(config.YANDEX_API_KEY and config.YANDEX_FOLDER_ID),
               "YANDEX_API_KEY and YANDEX_FOLDER_ID"),
    "elevenlabs": (lambda: bool(config.ELEVENLABS_API_KEY), "ELEVENLABS_API_KEY"),
    "fish": (lambda: bool(config.FISH_API_KEY), "FISH_API_KEY"),
}

SETTING = {
    "openai": "TTS_PROVIDER=openai + OPENAI_VOICE",
    "yandex": "TTS_PROVIDER=yandex + YANDEX_VOICE",
    "elevenlabs": "TTS_PROVIDER=elevenlabs + ELEVENLABS_VOICE_ID",
    "fish": "TTS_PROVIDER=fish + FISH_VOICE_ID",
}


def _point_at(provider: str, voice_id: str) -> None:
    """Aim the real tts module at one candidate, so the audition goes through
    exactly the code path the app uses — same model, same settings."""
    config.TTS_PROVIDER = provider
    if provider == "openai":
        config.OPENAI_VOICE = voice_id
    elif provider == "yandex":
        config.YANDEX_VOICE = voice_id
    elif provider == "elevenlabs":
        config.ELEVENLABS_VOICE_ID = voice_id
    else:
        config.FISH_VOICE_ID = voice_id


async def audition(
    candidates: list[tuple[str, str]], line: str, quiet: bool, skip_unconfigured: bool
) -> None:
    missing = {p for p, _ in candidates if not NEEDS[p][0]()}
    if missing and not skip_unconfigured:
        names = ", ".join(sorted(NEEDS[p][1] for p in missing))
        sys.exit(
            f"{names} is not set — add it to backend/.env.\n"
            "Or use --openai, which works with the key you already have for the ears."
        )
    candidates = [(p, v) for p, v in candidates if NEEDS[p][0]()]
    if not candidates:
        sys.exit("  No voice provider is configured. Add a key to backend/.env.")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f'\n  Line:  "{line}"')
    print(f"  Saving to:  {OUT_DIR}\n")

    was = (config.TTS_PROVIDER, config.FISH_VOICE_ID, config.OPENAI_VOICE,
           config.YANDEX_VOICE, config.ELEVENLABS_VOICE_ID)
    results: list[tuple[str, str, Path]] = []

    try:
        for i, (provider, voice_id) in enumerate(candidates, start=1):
            _point_at(provider, voice_id)
            label = f"{provider} · {voice_id}" if voice_id else f"{provider} · (default voice)"
            print(f"  {i}. {label}")
            try:
                audio = await tts.synthesize(line)
            except Exception as e:
                # A rejected voice NAME is ordinary here — this is a shortlist
                # of candidates, and finding out which ones your account has is
                # the point. Anything else is a real problem and gets the full
                # message, hints and all.
                if "400" in str(e):
                    print("     — не годится: такого голоса у вашего аккаунта нет\n")
                else:
                    print(f"     ✗ {e}\n")
                continue

            safe = voice_id.replace(":", "-")[:16] or "default"
            path = OUT_DIR / f"{provider}-{i}-{safe}.mp3"
            path.write_bytes(audio)
            results.append((provider, voice_id, path))
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
    for i, (provider, voice_id, path) in enumerate(results, start=1):
        print(f"  {i}. {provider} · {voice_id or '(default)'}")
        print(f"     {path}")

    print(
        "\n  Ask of each one:\n"
        "    · Would you believe this person is in the room?\n"
        "    · Does the question sound asked, or recited?\n"
        "    · Could you listen to it for an hour?\n"
        "\n  Then put the winner in backend/.env:\n"
    )
    for provider in dict.fromkeys(p for p, _, _ in results):
        print(f"    {provider:<12} → {SETTING[provider]}")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Hear several voices say the same line, and pick him."
    )
    parser.add_argument(
        "voice_ids", nargs="*",
        help="voice IDs (Fish) or voice names (OpenAI). Empty with --openai "
             "auditions the whole shortlist.",
    )
    parser.add_argument("--compare", action="store_true",
                        help="one voice from every provider you have a key for, "
                             "side by side — start here")
    parser.add_argument("--cost", action="store_true",
                        help="what an hour of each one costs IN RUSSIAN, and why "
                             "the headline prices mislead")
    parser.add_argument("--openai", action="store_true",
                        help="OpenAI voices — uses the key you already have")
    parser.add_argument("--yandex", action="store_true",
                        help="Yandex SpeechKit — Russian voices made for Russian")
    parser.add_argument("--eleven", action="store_true",
                        help="ElevenLabs — the warmest, and the priciest")
    parser.add_argument("--text", default=DEFAULT_LINE, help="line to say")
    parser.add_argument(
        "--quiet", action="store_true", help="save the files without playing them"
    )
    args = parser.parse_args()

    if args.cost:
        show_costs()
        if not (args.compare or args.openai or args.yandex or args.eleven or args.voice_ids):
            return

    if args.compare:
        # Anything without a key is skipped rather than fatal: the whole point
        # is to hear what you actually have.
        asyncio.run(audition(COMPARE, args.text, args.quiet, skip_unconfigured=True))
        return

    provider = ("openai" if args.openai else
                "yandex" if args.yandex else
                "elevenlabs" if args.eleven else "fish")

    voices = args.voice_ids
    if not voices:
        defaults = {"openai": OPENAI_VOICES, "yandex": YANDEX_VOICES}
        if provider not in defaults:
            parser.error(
                f"give at least one voice ID for {provider} (fish.audio/discovery "
                "→ open a voice → copy its id), or use --compare / --openai / "
                "--yandex to hear a ready-made shortlist"
            )
        voices = defaults[provider]

    asyncio.run(
        audition(
            [(provider, v) for v in voices],
            args.text,
            args.quiet,
            skip_unconfigured=False,
        )
    )


if __name__ == "__main__":
    main()
