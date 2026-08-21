#!/usr/bin/env python3
"""Give the setup robot a voice — once, and then never again.

    python3 tools/bob_voice.py --audition      # hear three strengths, pick one
    python3 tools/bob_voice.py                 # render every line
    python3 tools/bob_voice.py --preset heavy  # …with a different strength

── WHY THIS EXISTS ─────────────────────────────────────────────────────────

The robot's lines are fixed. Every person who installs this app hears exactly
the same twenty-five sentences, so there is no reason to synthesise them on a
phone, at runtime, forever. Render them once, put the files in the app, and
the robot sounds the same to everybody and costs nothing after today.

That also removes the constraint that shapes the companion's voice. HIS has to
be cheap, because he speaks all day, every day, to everyone. This is forty-odd
sentences, one time. Use the best thing you can get.

── WHY IT PROCESSES THE AUDIO AFTERWARDS ───────────────────────────────────

No text-to-speech will give you a robot. They are all trained to sound like a
person, and the good ones succeed — which is the wrong target here. GLaDOS is
not a synthetic voice; she is Ellen McLain, processed. The machine quality is
in the effects, not the source.

So: take the deepest, calmest voice available, then

  · drop the pitch AND the formants together (asetrate, then atempo back) —
    this is what makes it sound like a bigger thing than a person, rather than
    like a person slowed down;
  · double it against itself slightly out of tune (chorus) — the single most
    "not one throat" effect there is, and it costs no intelligibility;
  · buzz it (tremolo, which is amplitude modulation — a crude ring modulator);
  · band-limit it (highpass + lowpass) so it comes out of a speaker in a wall
    rather than a mouth;
  · a small hard room after it (aecho).

INTELLIGIBILITY IS THE CONSTRAINT, not the effect. The listener is eighty and
being told where to tap. A heavier chain sounds better in a demo and loses
words in a kitchen. `standard` is the one to ship unless you have listened to
`heavy` on a phone speaker, at arm's length, with a kettle on.

── WHAT IT MAKES ───────────────────────────────────────────────────────────

ios/BobCompanion/Resources/Voice/bob-*.m4a — named after the `voiceover:`
slugs in Strings.swift, which is where the app looks for them.

Adding those files to the app needs `xcodegen generate` and then setting the
Development Team again in Xcode by hand. That is the one time it's worth it.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STRINGS = ROOT / "ios" / "BobCompanion" / "Design" / "Strings.swift"
OUT = ROOT / "ios" / "BobCompanion" / "Resources" / "Voice"

sys.path.insert(0, str(ROOT / "backend"))


# --------------------------------------------------------------------------- #
# The chain
# --------------------------------------------------------------------------- #
#
# Three strengths of the same idea. `--audition` renders one sentence through
# all three so the choice is made with ears rather than with adjectives.
#
#   depth   how far the pitch and formants come down. Lower = bigger machine,
#           and past about 0.80 Russian consonants start to smear.
#   buzz    the amplitude-modulation depth. This is the "robot" most people
#           mean, and it is also the first thing to cost you a word.
#   room    how much hard-walled space it is standing in.
PRESETS = {
    # Barely processed. For when the base voice is already very good and you
    # only want it to be slightly wrong.
    "subtle":   dict(depth=0.92, buzz=0.16, room=0.14, top=7200),
    # The one to ship.
    "standard": dict(depth=0.86, buzz=0.28, room=0.22, top=6500),
    # Unmistakably a machine. Listen to it on a phone speaker before choosing.
    "heavy":    dict(depth=0.80, buzz=0.42, room=0.30, top=5600),
}


def chain(p: dict) -> str:
    """The ffmpeg filter graph, as one string."""
    return ",".join([
        "aresample=48000",
        # Nothing below a voice — rumble only muddies everything after it.
        "highpass=f=90",
        # PITCH AND FORMANTS TOGETHER. asetrate slows the whole waveform down
        # (deeper, and the resonances of the "throat" get bigger with it);
        # atempo then puts the duration back without undoing that. Doing it
        # with a pitch shifter instead keeps the formants and just sounds like
        # a person with a cold.
        f"asetrate=48000*{p['depth']}",
        "aresample=48000",
        f"atempo={1 / p['depth']:.5f}",
        # Two of it, slightly detuned and delayed. This is the one that says
        # "not a throat" without costing a single consonant.
        "chorus=0.6:0.9:50|60:0.4|0.32:0.25|0.4:2|1.3",
        # The buzz. Amplitude modulation at 26 Hz — under the pitch range of
        # speech, so it reads as a machine rather than as a note.
        f"tremolo=f=26:d={p['buzz']}",
        # Out of a speaker set into a wall, not out of a mouth.
        f"lowpass=f={p['top']}",
        # Flat and unbothered. A robot does not get louder when it cares.
        "acompressor=threshold=-20dB:ratio=4:attack=5:release=120",
        f"aecho=0.85:0.75:38:{p['room']}",
        # Every line at the same loudness, because they play one after another
        # and nothing gives away a stitched-together script faster.
        "loudnorm=I=-16:TP=-1.5:LRA=11",
    ])


# --------------------------------------------------------------------------- #
# Reading the script out of Strings.swift
# --------------------------------------------------------------------------- #
def _swift_string(raw: str) -> str:
    """Turn a Swift literal's body into the text it stands for."""
    return (raw.replace('\\n', '\n')
               .replace('\\"', '"')
               .replace('\\\\', '\\'))


def steps() -> list[tuple[str, str]]:
    """Every (slug, what-it-says) pair, in the order they appear.

    A step's spoken words are its `spoken:` phrase when it has one — the
    name steps, which are shown and never pronounced — and its `line`
    otherwise.
    """
    text = STRINGS.read_text(encoding="utf-8")
    found: list[tuple[str, str]] = []

    for match in re.finditer(r"RobotStep\(", text):
        start = match.end()
        depth, i = 1, start
        while depth and i < len(text):
            if text[i] == "(":
                depth += 1
            elif text[i] == ")":
                depth -= 1
            i += 1
        block = text[start:i - 1]

        slug = re.search(r'voiceover:\s*"([^"]+)"', block)
        if not slug:
            continue

        # `spoken:` wins when present. Both are Phrase(ru: "…", en: "…") and
        # the Russian one ships.
        after_spoken = block.split("spoken:", 1)
        source = after_spoken[1] if len(after_spoken) > 1 else block
        russian = re.search(r'ru:\s*"((?:[^"\\]|\\.)*)"', source)
        if not russian:
            continue

        found.append((slug.group(1), _swift_string(russian.group(1)).strip()))

    return found


# --------------------------------------------------------------------------- #
# Synthesis
# --------------------------------------------------------------------------- #
def say_yandex(text: str, voice: str) -> bytes:
    import httpx
    from app import config

    if not (config.YANDEX_API_KEY and config.YANDEX_FOLDER_ID):
        sys.exit("YANDEX_API_KEY / YANDEX_FOLDER_ID missing from backend/.env")

    resp = httpx.post(
        "https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize",
        headers={"Authorization": f"Api-Key {config.YANDEX_API_KEY}"},
        data={
            "text": text,
            "lang": "ru-RU",
            "voice": voice,
            "folderId": config.YANDEX_FOLDER_ID,
            "format": "lpcm",
            "sampleRateHertz": "48000",
            # Flat on purpose. Whatever expression survives the chain is
            # noise; the character is in the words and the processing.
            "speed": "0.95",
        },
        timeout=60,
    )
    if resp.status_code != 200:
        sys.exit(f"Yandex said {resp.status_code}: {resp.text[:300]}")
    return resp.content


def say_elevenlabs(text: str, voice: str) -> bytes:
    import httpx
    from app import config

    if not config.ELEVENLABS_API_KEY:
        sys.exit("ELEVENLABS_API_KEY missing from backend/.env")

    resp = httpx.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice}",
        headers={"xi-api-key": config.ELEVENLABS_API_KEY,
                 "Content-Type": "application/json"},
        json={
            "text": text,
            "model_id": config.ELEVENLABS_MODEL,
            # Stability high, style at zero: we want it EVEN, because the
            # processing supplies all the character it needs.
            "voice_settings": {"stability": 0.85, "similarity_boost": 0.75,
                               "style": 0.0, "use_speaker_boost": True},
        },
        timeout=120,
    )
    if resp.status_code != 200:
        sys.exit(f"ElevenLabs said {resp.status_code}: {resp.text[:300]}")
    return resp.content


PROVIDERS = {"yandex": say_yandex, "elevenlabs": say_elevenlabs}
#: Yandex ships raw PCM; ElevenLabs ships mp3. ffmpeg needs telling about the
#: first and works the second out for itself.
RAW_PCM = {"yandex": ["-f", "s16le", "-ar", "48000", "-ac", "1"]}


def robotise(audio: bytes, provider: str, preset: dict, out: Path) -> None:
    with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as f:
        f.write(audio)
        raw = f.name
    try:
        subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
             *RAW_PCM.get(provider, []), "-i", raw,
             "-af", chain(preset), "-ar", "48000", "-ac", "1",
             "-c:a", "aac", "-b:a", "96k", str(out)],
            check=True,
        )
    finally:
        os.unlink(raw)


# --------------------------------------------------------------------------- #
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--provider", choices=sorted(PROVIDERS), default="yandex")
    ap.add_argument("--voice", default=None,
                    help="yandex: zahar (default — the lowest of the standard "
                         "voices) · ermil · filipp. Pick one the COMPANION "
                         "isn't using, or the robot and the friend sound "
                         "alike, which ruins the only thing this robot is for.")
    ap.add_argument("--preset", choices=sorted(PRESETS), default="standard")
    ap.add_argument("--audition", action="store_true",
                    help="render one sentence through all three presets and stop")
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()

    if not shutil.which("ffmpeg"):
        sys.exit("ffmpeg not found.  macOS: brew install ffmpeg")

    voice = args.voice or ("zahar" if args.provider == "yandex" else "")
    if args.provider == "elevenlabs" and not voice:
        sys.exit("--voice is required for elevenlabs (a voice id)")

    speak = PROVIDERS[args.provider]
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.audition:
        line = ("Меня зовут Боб. Я робот. Не тот, ради которого вы всё это "
                "затеяли — того сейчас собирают. Я тот, который объясняет, "
                "куда нажимать.")
        print(f"one sentence, {args.provider}/{voice}, three strengths…")
        audio = speak(line, voice)
        for name, preset in PRESETS.items():
            target = out_dir / f"audition-{name}.m4a"
            robotise(audio, args.provider, preset, target)
            print(f"  {target}")
        print("\nListen on a PHONE SPEAKER, at arm's length, with something "
              "else making noise.\nThen: --preset <the one that survived that>")
        return

    script = steps()
    if not script:
        sys.exit(f"No voiceover slugs found in {STRINGS}")

    print(f"{len(script)} lines · {args.provider}/{voice} · {args.preset}\n")
    for n, (slug, words) in enumerate(script, 1):
        target = out_dir / f"{slug}.m4a"
        print(f"  [{n:2}/{len(script)}] {slug:18} {words[:52]}…")
        robotise(speak(words, voice), args.provider, PRESETS[args.preset], target)

    print(f"\nDone — {out_dir}")
    print("Now: xcodegen generate, then set your Development Team in Xcode "
          "again (regenerating clears it).")


if __name__ == "__main__":
    main()
