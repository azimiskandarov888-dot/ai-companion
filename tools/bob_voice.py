#!/usr/bin/env python3
"""Give the setup robot a voice — once, and then never again.

    python3 tools/bob_voice.py --audition --lang en    # hear them, pick one
    python3 tools/bob_voice.py --lang en               # render every line

Two knobs when it's close but not right:

    --speed 1.15    brisker. Tempo only; the pitch does not move.
    --depth 0.98    less deep. 1.0 leaves the pitch alone entirely.

── WHY THIS EXISTS ─────────────────────────────────────────────────────────

The robot's lines are fixed. Every person who installs this app hears exactly
the same forty-five sentences, so there is no reason to synthesise them on a
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
words in a kitchen. `subtle` is the default and the one to ship unless you
have listened to something heavier on a phone speaker, at arm's length, with
a kettle on.

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
# Four strengths of the same idea. `--audition` renders one sentence through
# all of them and plays them, so the choice is made with ears rather than
# with adjectives.
#
#   depth   how far the pitch and formants come down. Lower = bigger machine,
#           and past about 0.85 consonants start to smear. 1.0 = untouched.
#   buzz    the amplitude-modulation depth. This is the "robot" most people
#           mean, and it is also the first thing to cost you a word.
#   room    how much hard-walled space it is standing in.
PRESETS = {
    # NOTHING but the room and the loudness. For a base voice that was already
    # DIRECTED into character — gpt-4o-mini-tts reads ROBOT_DIRECTION and acts
    # on it — where filters only make a good performance muddy.
    "clean":    dict(depth=1.00, buzz=0.00, room=0.10, top=9000),
    # THE DEFAULT, and the one that survived a listen. Just enough to be
    # wrong; not enough to be a special effect.
    "subtle":   dict(depth=0.96, buzz=0.14, room=0.14, top=7600),
    "standard": dict(depth=0.92, buzz=0.24, room=0.20, top=6800),
    # Unmistakably a machine. Listen on a phone speaker before choosing it.
    "heavy":    dict(depth=0.86, buzz=0.38, room=0.28, top=6000),
}


def chain(p: dict, speed: float = 1.0) -> str:
    """The ffmpeg filter graph, as one string.

    `speed` rides on top of the tempo correction: 1.0 keeps the voice exactly
    as fast as it arrived, 1.15 is fifteen per cent brisker.
    """
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
        f"atempo={speed / p['depth']:.5f}",
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


def steps(lang: str = "ru") -> list[tuple[str, str]]:
    """Every (slug, what-it-says) pair, in the order they appear.

    A step's spoken words are its `spoken:` phrase when it has one — the
    name steps, which are shown and never pronounced — and its `line`
    otherwise. `lang` picks which half of the Phrase to read: "ru" or "en".
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
        said = re.search(rf'{lang}:\s*"((?:[^"\\]|\\.)*)"', source)
        if not said:
            continue

        found.append((slug.group(1), _swift_string(said.group(1)).strip()))

    return found


# --------------------------------------------------------------------------- #
# Synthesis
# --------------------------------------------------------------------------- #
#: What to tell a provider that takes direction. `gpt-4o-mini-tts` reads this
#: and acts on it, which does more for the character than the whole filter
#: chain below — direction beats processing every time, when it's available.
ROBOT_DIRECTION = (
    "You are an automated announcement system in an old research facility. "
    "Speak FLAT and EVEN. Never warm, never enthusiastic, never rising at the "
    "end of a sentence, no smile in the voice at all. "
    "BRISK AND MATTER-OF-FACT: normal conversational pace, do not drag, do "
    "not linger on words, do not leave long pauses between sentences. Get "
    "through it. "
    "You are a machine and you have no feelings about that."
)
# The first version of that said "UNHURRIED" and "leave a beat between
# sentences", and the result was unbearably slow — which read as a problem
# with the filter chain and was nothing of the kind. `atempo` restores the
# duration `asetrate` took exactly; it cannot make anything slow. When a
# directed voice comes out wrong, suspect the direction first.


def say_openai(text: str, voice: str, lang: str) -> bytes:
    """Best English by a distance, and the only one you can DIRECT.

    `onyx` is the deep one. The `instructions` field is the reason this is
    first choice for English: you describe the performance in words instead of
    trying to bolt it on afterwards with filters.
    """
    import httpx
    from app import config

    if not config.OPENAI_API_KEY:
        sys.exit("OPENAI_API_KEY missing from backend/.env")

    resp = httpx.post(
        "https://api.openai.com/v1/audio/speech",
        headers={"Authorization": f"Bearer {config.OPENAI_API_KEY}"},
        json={
            "model": "gpt-4o-mini-tts",
            "voice": voice or "onyx",
            "input": text,
            "instructions": ROBOT_DIRECTION,
            "response_format": "mp3",
        },
        timeout=120,
    )
    if resp.status_code != 200:
        sys.exit(f"OpenAI said {resp.status_code}: {resp.text[:300]}")
    return resp.content


def say_fish(text: str, voice: str, lang: str) -> bytes:
    """The one the Minecraft mod uses — and it is worth the fuss.

    Fish bills by BYTE, and Cyrillic is two bytes a letter, which is why it is
    the wrong choice for the companion who talks all day in Russian. For
    forty-five sentences rendered once, that objection evaporates entirely.

    `--voice` is a reference_id from the Fish voice library. Pick a deep,
    even, unexcited one; the chain does the rest.
    """
    import httpx
    from app import config

    if not config.FISH_API_KEY:
        sys.exit("FISH_API_KEY missing from backend/.env")

    payload: dict = {"text": text, "format": "mp3", "mp3_bitrate": 128,
                     "normalize": True, "latency": "normal"}
    if voice:
        payload["reference_id"] = voice

    resp = httpx.post(
        "https://api.fish.audio/v1/tts",
        headers={"Authorization": f"Bearer {config.FISH_API_KEY}",
                 "Content-Type": "application/json",
                 "model": config.FISH_MODEL},
        json=payload,
        timeout=120,
    )
    if resp.status_code != 200:
        sys.exit(f"Fish said {resp.status_code}: {resp.text[:300]}")
    return resp.content


def say_yandex(text: str, voice: str, lang: str) -> bytes:
    import httpx
    from app import config

    if not (config.YANDEX_API_KEY and config.YANDEX_FOLDER_ID):
        sys.exit("YANDEX_API_KEY / YANDEX_FOLDER_ID missing from backend/.env")

    resp = httpx.post(
        "https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize",
        headers={"Authorization": f"Api-Key {config.YANDEX_API_KEY}"},
        data={
            "text": text,
            "lang": "ru-RU" if lang == "ru" else "en-US",
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


def say_elevenlabs(text: str, voice: str, lang: str) -> bytes:
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


PROVIDERS = {
    "openai": say_openai,          # best English, and the only one you can direct
    "fish": say_fish,              # what the Minecraft mod uses
    "elevenlabs": say_elevenlabs,
    "yandex": say_yandex,          # best RUSSIAN, but the standard voices are rough
}

#: A sensible starting voice per provider, when none is given.
DEFAULT_VOICE = {"openai": "onyx", "yandex": "zahar", "fish": "", "elevenlabs": ""}
#: Yandex ships raw PCM; ElevenLabs ships mp3. ffmpeg needs telling about the
#: first and works the second out for itself.
RAW_PCM = {"yandex": ["-f", "s16le", "-ar", "48000", "-ac", "1"]}
#: openai / fish / elevenlabs all return a container ffmpeg reads by itself.


def play(files) -> bool:
    """Play files one after another, if this machine can. macOS always can."""
    player = shutil.which("afplay") or shutil.which("ffplay")
    if not player:
        return False
    for f in files:
        print(f"\n  ▶ {Path(f).stem}")
        if player.endswith("ffplay"):
            subprocess.run([player, "-nodisp", "-autoexit", "-loglevel",
                            "error", str(f)], check=False)
        else:
            subprocess.run([player, str(f)], check=False)
    return True


def robotise(audio: bytes, provider: str, preset: dict, out: Path,
             speed: float = 1.0) -> None:
    with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as f:
        f.write(audio)
        raw = f.name
    try:
        subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
             *RAW_PCM.get(provider, []), "-i", raw,
             "-af", chain(preset, speed), "-ar", "48000", "-ac", "1",
             "-c:a", "aac", "-b:a", "96k", str(out)],
            check=True,
        )
    finally:
        os.unlink(raw)


# --------------------------------------------------------------------------- #
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--provider", choices=sorted(PROVIDERS), default="openai")
    ap.add_argument("--lang", choices=["ru", "en"], default="ru",
                    help="which half of each Phrase to speak. English TTS is "
                         "markedly better than Russian across every provider, "
                         "so test in English first if the Russian disappoints "
                         "— it tells you whether the problem is the voice or "
                         "the language.")
    ap.add_argument("--voice", default=None,
                    help="openai: onyx (deepest) · ash · echo. "
                         "yandex: zahar · ermil · filipp. "
                         "fish/elevenlabs: a voice id. "
                         "Whatever you pick, it must NOT be the voice the "
                         "COMPANION uses — if the robot and the friend sound "
                         "alike, the only thing this robot exists for is gone.")
    ap.add_argument("--preset", choices=sorted(PRESETS), default="subtle")
    ap.add_argument("--speed", type=float, default=1.0,
                    help="1.0 leaves the pace alone; 1.15 is brisker; 0.9 "
                         "slower. Tempo only — the pitch does not move.")
    ap.add_argument("--depth", type=float, default=None,
                    help="override the preset's pitch drop. 1.0 = untouched, "
                         "0.96 = a little lower, 0.86 = a lot. Below about "
                         "0.85 consonants start to smear.")
    ap.add_argument("--audition", action="store_true",
                    help="render one sentence through EVERY strength, play them, and stop")
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()

    if not shutil.which("ffmpeg"):
        sys.exit("ffmpeg not found.  macOS: brew install ffmpeg")

    voice = args.voice or DEFAULT_VOICE.get(args.provider, "")
    if args.provider == "elevenlabs" and not voice:
        sys.exit("--voice is required for elevenlabs (a voice id)")

    speak = lambda text: PROVIDERS[args.provider](text, voice, args.lang)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.audition:
        line = {
            "ru": ("Меня зовут Боб. Я робот. Не тот, ради которого вы всё это "
                   "затеяли — того сейчас собирают. Я тот, который объясняет, "
                   "куда нажимать."),
            "en": ("My name is Bob. I'm a robot. Not the one you went to all "
                   "this trouble for — that one is being put together as we "
                   "speak. I'm the one who explains where to press."),
        }[args.lang]
        print(f"one sentence · {args.provider}/{voice or 'default'} · "
              f"{args.lang} · every strength…\n")
        audio = speak(line)
        made = []
        for name, preset in sorted(PRESETS.items(),
                                   key=lambda kv: -kv[1]["depth"]):
            target = out_dir / f"audition-{name}.m4a"
            robotise(audio, args.provider, preset, target, args.speed)
            made.append((name, target))
            print(f"  {name:9} {target}")

        # PLAY THEM. This script writes files and plays nothing, which read as
        # "it did nothing" the first time somebody ran it — they were waiting
        # for a sound and looking at their phone. Auditioning is the one mode
        # whose entire purpose is to be heard, so it plays.
        if not play(t for _, t in made):
            print("\n  (couldn't play them here — open them yourself)")

        print("\n" + "─" * 66)
        print("Now listen again on a PHONE SPEAKER, at arm's length, with a "
              "kettle on.\nThe one that survives THAT is the one to ship:\n")
        print(f"    python3 tools/{Path(__file__).name} --lang {args.lang} "
              f"--provider {args.provider} --preset subtle\n")
        print("Too slow?  add  --speed 1.15      Too low?  add  --depth 0.98")
        print("Nothing has reached the app yet. These are files on this Mac.")
        return

    script = steps(args.lang)
    if not script:
        sys.exit(f"No voiceover slugs found in {STRINGS}")

    preset = dict(PRESETS[args.preset])
    if args.depth is not None:
        preset["depth"] = args.depth
    print(f"{len(script)} lines · {args.provider}/{voice or 'default'} · "
          f"{args.lang} · {args.preset} · depth {preset['depth']} · "
          f"speed {args.speed}\n")
    for n, (slug, words) in enumerate(script, 1):
        target = out_dir / f"{slug}.m4a"
        print(f"  [{n:2}/{len(script)}] {slug:18} {words[:52]}…")
        robotise(speak(words), args.provider, preset, target, args.speed)

    print("\n" + "─" * 66)
    print(f"{len(script)} files written to\n    {out_dir}\n")
    print("NOTHING HAS REACHED THE APP YET. These are files on this Mac.")
    print("To hear one:      afplay " + str(out_dir / f"{script[0][0]}.m4a"))
    print("To get them in:   cd ios && xcodegen generate")
    print("                  …then set your Development Team in Xcode again —")
    print("                  regenerating clears it. Then build.")


if __name__ == "__main__":
    main()
