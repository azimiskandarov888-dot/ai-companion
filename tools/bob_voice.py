#!/usr/bin/env python3
"""Give the setup robot a voice — once, and then never again.

    python3 tools/bob_voice.py --audition --lang en    # hear them, pick one
    python3 tools/bob_voice.py --lang en               # render every line

Two knobs when it's close but not right:

    --speed 1.15    brisker
    --depth 0.98    less deep. 1.0 leaves the pitch alone entirely.

── CLONING, WHICH IS PROBABLY THE ANSWER ───────────────────────────────────

    python3 tools/bob_voice.py --clone me.m4a --transcript "what I said"

Every text-to-speech voice is an average of thousands of readings, and an
average has no attitude. That is why no amount of directing gets a deadpan
out of one: deadpan is a CHOICE a performer makes, and an average makes no
choices. It is the same reason Portal's announcer works — a real man read it.

So record fifteen to sixty seconds of the performance you want, clone it, and
every one of the forty-five lines comes back in it. What matters is not the
length of the sample but that it IS the performance: read two or three of
Bob's real lines, in character, bored out of your mind.

Record it once. There is nothing to maintain afterwards.

ONE THING THIS WILL NOT DO: clone an actor out of a game. That is a real,
identifiable person's voice, and putting it in a shipped app is a problem no
matter how the audio was obtained. Your own voice is both legal and better —
and if you don't want yours, forty-five lines is an hour of a voice actor's
day, which is not expensive.

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
#   squash  compression ratio. THE ONE THAT KILLS EXPRESSION — a compressor's
#           entire job is to remove dynamic range, which is most of what
#           "expression" means. 1.0 turns it off.
PRESETS = {
    # NOTHING but the room and the loudness. For a base voice that was already
    # DIRECTED into character — gpt-4o-mini-tts reads ROBOT_DIRECTION and acts
    # on it — where filters only make a good performance muddy.
    "clean":    dict(depth=1.00, buzz=0.00, room=0.10, top=9000, squash=1.0),
    # THE DEFAULT, and the one that survived a listen. Just enough to be
    # wrong; not enough to be a special effect.
    "subtle":   dict(depth=0.96, buzz=0.10, room=0.14, top=7600, squash=1.6),
    "standard": dict(depth=0.92, buzz=0.20, room=0.20, top=6800, squash=2.5),
    # Unmistakably a machine. Listen on a phone speaker before choosing it.
    "heavy":    dict(depth=0.86, buzz=0.34, room=0.28, top=6000, squash=4.0),
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
        # WAS THE MAIN REASON HE SOUNDED MONOTONE, and it was hiding in
        # plain sight: a compressor exists to reduce dynamic range, and
        # dynamic range is most of what "expression" is. Squashing the
        # performance flat and then wondering why it had no life in it.
        # Off entirely on `clean`, barely there on `subtle`.
        *([] if p["squash"] <= 1.0 else
          [f"acompressor=threshold=-14dB:ratio={p['squash']}:attack=8:release=180"]),
        f"aecho=0.85:0.75:38:{p['room']}",
        # Every line at the same loudness, because they play one after another
        # and nothing gives away a stitched-together script faster.
        #
        # LRA is the loudness-RANGE target, and it is the second place
        # expression quietly died: at 11 it flattens the difference between a
        # leant-on word and an ordinary one. 20 lets the performance through
        # while still matching the overall level line to line.
        "loudnorm=I=-16:TP=-1.5:LRA=20",
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
    "You are the public-address system of an old research facility, read by a "
    "man who has held this job for thirty years and is not impressed by any "
    "of it. Think of the announcer in Portal 2, or a very tired corporate "
    "training tape. "
    "DRY AND DEADPAN — BUT NOT MONOTONE. Deadpan is a performance, not a flat "
    "line. You still lean on the important word in a sentence. You still let "
    "a sentence fall at the end, like a man who has finished making his "
    "point. You still take the small breath a person takes. "
    "What you never do is sound pleased, eager, warm, or surprised. No smile "
    "in the voice. Nothing is being sold here. "
    "SOME OF THESE LINES ARE JOKES. Play them completely straight — the "
    "flatter the delivery, the better the joke works. Never signal that "
    "something was funny. "
    "Pace: a man reading a notice he has read a thousand times. Brisk, clear, "
    "faintly bored. Not slow, not dragging, no long pauses."
)
# The first version of that said "UNHURRIED" and "leave a beat between
# sentences", and the result was unbearably slow — which read as a problem
# with the filter chain and was nothing of the kind. `atempo` restores the
# duration `asetrate` took exactly; it cannot make anything slow. When a
# directed voice comes out wrong, suspect the direction first.


def say_openai(text: str, voice: str, lang: str, speed: float = 1.0) -> bytes:
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
            # NATIVE speed, not atempo. Stretching finished speech smears the
            # consonants; asking the model to talk faster does not.
            "speed": max(0.25, min(4.0, speed)),
            "response_format": "mp3",
        },
        timeout=120,
    )
    if resp.status_code != 200:
        sys.exit(f"OpenAI said {resp.status_code}: {resp.text[:300]}")
    return resp.content


def clone_with_fish(sample: Path, title: str, transcript: str | None) -> str:
    """Teach Fish a voice from a recording, and hand back its reference_id.

    Fifteen seconds is enough. Sixty is better. What matters far more than
    length is that the sample is the PERFORMANCE you want: record yourself
    reading two or three of Bob's actual lines, in character, and every one of
    the forty-five will come back sounding like that.

    A transcript is optional and worth supplying — it measurably improves the
    clone, and you already have the text.
    """
    import httpx
    from app import config

    if not config.FISH_API_KEY:
        sys.exit("FISH_API_KEY missing from backend/.env")
    if not sample.exists():
        sys.exit(f"No such file: {sample}")

    files = [("voices", (sample.name, sample.read_bytes(), "application/octet-stream"))]
    data = {"title": title, "type": "tts", "train_mode": "fast",
            "visibility": "private"}
    if transcript:
        files.append(("texts", (None, transcript)))

    resp = httpx.post(
        "https://api.fish.audio/model",
        headers={"Authorization": f"Bearer {config.FISH_API_KEY}"},
        data=data, files=files, timeout=300,
    )
    if resp.status_code not in (200, 201):
        sys.exit(f"Fish said {resp.status_code}:\n{resp.text[:600]}")

    body = resp.json()
    ref = body.get("_id") or body.get("id")
    if not ref:
        sys.exit(f"Fish accepted it but returned no id:\n{resp.text[:600]}")
    return ref


def say_fish(text: str, voice: str, lang: str, speed: float = 1.0) -> bytes:
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


def say_yandex(text: str, voice: str, lang: str, speed: float = 1.0) -> bytes:
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
            "speed": f"{max(0.1, min(3.0, speed)):.2f}",
        },
        timeout=60,
    )
    if resp.status_code != 200:
        sys.exit(f"Yandex said {resp.status_code}: {resp.text[:300]}")
    return resp.content


def say_elevenlabs(text: str, voice: str, lang: str, speed: float = 1.0) -> bytes:
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


#: Providers that change tempo THEMSELVES, natively and without artefacts.
#: For these, atempo is left at 1.0 — applying speed twice would be both
#: wrong and audible.
SPEED_AT_SOURCE = {"openai", "yandex"}

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


def tuned(preset: dict, depth: float | None) -> dict:
    """A preset with the pitch drop overridden, if one was asked for."""
    if depth is None:
        return preset
    out = dict(preset)
    out["depth"] = depth
    return out


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
    ap.add_argument("--clone", metavar="AUDIO",
                    help="teach Fish a voice from a recording and print its "
                         "id. 15 seconds is enough; what matters is that the "
                         "sample IS the performance you want.")
    ap.add_argument("--title", default="Bob the setup robot",
                    help="what to call the cloned voice in your Fish library")
    ap.add_argument("--transcript", default=None,
                    help="exactly what is said in --clone's audio. Optional, "
                         "and it measurably improves the clone.")
    args = ap.parse_args()

    if args.clone:
        ref = clone_with_fish(Path(args.clone), args.title, args.transcript)
        print("\n" + "═" * 66)
        print(f"  cloned.  reference_id = {ref}")
        print("═" * 66 + "\n")
        print("Hear it on the real script:\n")
        print(f"    python3 tools/bob_voice.py --audition --lang en \\")
        print(f"        --provider fish --voice {ref}\n")
        print("Keep that id — it is how you render the other 44 lines later.")
        return

    if not shutil.which("ffmpeg"):
        sys.exit("ffmpeg not found.  macOS: brew install ffmpeg")

    voice = args.voice or DEFAULT_VOICE.get(args.provider, "")
    if args.provider == "elevenlabs" and not voice:
        sys.exit("--voice is required for elevenlabs (a voice id)")

    def speak(text: str) -> bytes:
        return PROVIDERS[args.provider](text, voice, args.lang, args.speed)

    # Whoever already handled the tempo must not have it applied again.
    stretch = 1.0 if args.provider in SPEED_AT_SOURCE else args.speed
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

        # SAY EXACTLY WHAT IS ABOUT TO HAPPEN. «Am I even listening to the
        # right voice?» is a fair question to have to ask, and it should never
        # have been possible to ask it — the tool knew, and didn't say.
        print("═" * 66)
        print(f"  provider   {args.provider}")
        print(f"  voice      {voice or '(provider default)'}")
        print(f"  language   {args.lang}")
        print(f"  speed      {args.speed}"
              + ("  (asked of the provider itself)"
                 if args.provider in SPEED_AT_SOURCE else "  (stretched after)"))
        print(f"  depth      {args.depth if args.depth is not None else 'per preset'}")
        if args.provider == "openai":
            print(f"  directed   {ROBOT_DIRECTION[:58]}…")
        print("═" * 66 + "\n")

        audio = speak(line)

        # THE CONTROL. Untouched provider output, no chain at all — and it is
        # played FIRST, because it is the only thing that answers the question
        # that matters: is the raw voice good and am I ruining it, or was it
        # never good to begin with?
        raw = out_dir / "audition-0-RAW-no-effects.m4a"
        subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
             *RAW_PCM.get(args.provider, []), "-i", "pipe:0",
             "-c:a", "aac", "-b:a", "128k", str(raw)],
            input=audio, check=True,
        )
        made = [("RAW (no effects at all)", raw)]

        for name, preset in sorted(PRESETS.items(), key=lambda kv: -kv[1]["depth"]):
            target = out_dir / f"audition-{name}.m4a"
            robotise(audio, args.provider, tuned(preset, args.depth), target,
                     stretch)
            made.append((name, target))

        for name, target in made:
            print(f"  {name:26} {target.name}")

        if not play(t for _, t in made):
            print("\n  (couldn't play them here — open them yourself)")

        print("\n" + "─" * 66)
        print("THE FIRST ONE IS THE CONTROL — raw voice, nothing done to it.")
        print("  · RAW is fine, the rest are worse  → my chain is the problem")
        print("  · RAW is ALSO bad                  → the voice or the")
        print("    direction is the problem, and no filter will save it\n")
        print("Then say WHICH of the five, and what was still wrong with it.\n")
        print("Nothing has reached the app yet. These are files on this Mac.")
        return

    script = steps(args.lang)
    if not script:
        sys.exit(f"No voiceover slugs found in {STRINGS}")

    preset = tuned(PRESETS[args.preset], args.depth)
    print(f"{len(script)} lines · {args.provider}/{voice or 'default'} · "
          f"{args.lang} · {args.preset} · depth {preset['depth']} · "
          f"speed {args.speed}\n")
    for n, (slug, words) in enumerate(script, 1):
        target = out_dir / f"{slug}.m4a"
        print(f"  [{n:2}/{len(script)}] {slug:18} {words[:52]}…")
        robotise(speak(words), args.provider, preset, target, stretch)

    print("\n" + "─" * 66)
    print(f"{len(script)} files written to\n    {out_dir}\n")
    print("NOTHING HAS REACHED THE APP YET. These are files on this Mac.")
    print("To hear one:      afplay " + str(out_dir / f"{script[0][0]}.m4a"))
    print("To get them in:   cd ios && xcodegen generate")
    print("                  …then set your Development Team in Xcode again —")
    print("                  regenerating clears it. Then build.")


if __name__ == "__main__":
    main()
