"""Russian voices, side by side and blind: the same words in every voice
(docs/VOICES-RU.md). Everything goes through the OpenRouter key, except the
app's own Fish voices.

    python voices_ru.py            make every clip, loudness-matched, numbered blind
    python voices_ru.py --only L   remake one (by label)

Male and female voices are shuffled separately (М1…, Ж1…); the key is the
hidden .key.json beside them. Two of the voices are the app's current Fish
voices — the ones the owner called horrible — as an anchor: if they come out
at the bottom again, the test is hearing what he hears.
"""
import argparse
import asyncio
import json
import random
import subprocess
import sys
import tempfile
from pathlib import Path

import httpx
from dotenv import dotenv_values

BACKEND = Path(__file__).resolve().parent
OUT = BACKEND / "data/listen/voices-ru"
ENV = dotenv_values(BACKEND / ".env")
ROUTER = "https://openrouter.ai/api/v1/audio/speech"

#: What Bob says — lively, then soft. «здорово» is a trap: «это здо́рово»
#: (great) and «здоро́во» (hi) are different words, and voices get it wrong.
TEXT = ("Ого, сам программу пишешь? Слушай, это же… ну, это здорово! А про что она?\n\n"
        "М-м… понимаю. Тяжёлый день, да? Ничего. Давай просто посидим, поговорим.")

#: Gemini takes a delivery style; nobody else here does.
STYLE = "warm, relaxed and natural, like a friend talking in person — not a narrator"

#: Tried on 2026-10-02 and left out after the first pass, so nobody tries them
#: blind again: Qwen-Audio 3.0 reads «…» out loud as «точка»; MiniMax's
#: Russian_PessimisticGirl mumbled «как а как как» after the last word;
#: ByteDance Seed Audio takes ~35 s a phrase, which no live conversation can
#: wait for. Not Russian at all: Deepgram, Kokoro, Orpheus, Sesame, Voxtral.
MALE = [
    ("mai-lev", "microsoft/mai-voice-2.1", "ru-RU-Lev:MAI-Voice-2.1"),
    ("mai-grant", "microsoft/mai-voice-2.1", "ru-RU-Grant:MAI-Voice-2.1"),
    ("gemini-achird", "google/gemini-3.8-flash-tts", "Achird"),
    ("gemini-zubenelgenubi", "google/gemini-3.8-flash-tts", "Zubenelgenubi"),
    ("gemini-umbriel", "google/gemini-3.8-flash-tts", "Umbriel"),
    ("minimax-reliable", "minimax/speech-2.8-hd", "Russian_ReliableMan"),
    ("minimax-childhood-friend", "minimax/speech-2.8-hd", "Russian_HandsomeChildhoodFriend"),
    ("minimax-attractive", "minimax/speech-2.8-hd", "Russian_AttractiveGuy"),
    ("grok-rex", "x-ai/grok-voice-tts-1.0", "rex"),
    ("grok-leo", "x-ai/grok-voice-tts-1.0", "leo"),
    ("fish-now-male", "fish", "male"),
]
FEMALE = [
    ("mai-masha", "microsoft/mai-voice-2.1", "ru-RU-Masha:MAI-Voice-2.1"),
    ("mai-harper", "microsoft/mai-voice-2.1", "ru-RU-Harper:MAI-Voice-2.1"),
    ("gemini-sulafat", "google/gemini-3.8-flash-tts", "Sulafat"),
    ("gemini-callirrhoe", "google/gemini-3.8-flash-tts", "Callirrhoe"),
    ("gemini-vindemiatrix", "google/gemini-3.8-flash-tts", "Vindemiatrix"),
    ("minimax-bright", "minimax/speech-2.8-hd", "Russian_BrightHeroine"),
    ("minimax-ambitious", "minimax/speech-2.8-hd", "Russian_AmbitiousWoman"),
    ("grok-ara", "x-ai/grok-voice-tts-1.0", "ara"),
    ("grok-eve", "x-ai/grok-voice-tts-1.0", "eve"),
    ("fish-now-female", "fish", "female"),
]


async def via_router(client: httpx.AsyncClient, model: str, voice: str) -> tuple[bytes, str]:
    gemini = model.startswith("google/")
    body = {"model": model, "input": TEXT, "voice": voice, "response_format": "pcm" if gemini else "mp3"}
    if gemini:
        body["provider"] = {"options": {"google-ai-studio": {"speech_metadata": {"style": STYLE}}}}
    r = await client.post(ROUTER, json=body, headers={"Authorization": f"Bearer {ENV['OPENROUTER_API_KEY']}"},
                          timeout=180)
    if r.status_code != 200:
        raise RuntimeError(f"{r.status_code} {r.text[:300]}")
    return r.content, "pcm" if gemini else "mp3"


async def via_fish(voice: str) -> tuple[bytes, str]:
    sys.path.insert(0, str(BACKEND))
    from app import config, tts
    config.LANGUAGE = "ru"
    chosen = config.FISH_VOICE_ID if voice == "male" else config.FISH_VOICE_ID_FEMALE
    return await tts.synthesize(TEXT, voice=chosen), "mp3"


def level(raw: bytes, kind: str, out: Path) -> None:
    """The same loudness for everyone (EBU R128, -16 LUFS): the louder of two
    voices sounds better in a side-by-side, whatever it is."""
    with tempfile.NamedTemporaryFile(suffix="." + kind) as f:
        f.write(raw)
        f.flush()
        src = ["-f", "s16le", "-ar", "24000", "-ac", "1", "-i", f.name] if kind == "pcm" else ["-i", f.name]
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *src, "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
                        "-ar", "44100", "-ac", "1", "-b:a", "160k", str(out)], check=True)


async def main(only: str | None) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    keyfile = OUT / ".key.json"
    key = json.loads(keyfile.read_text()) if keyfile.exists() else {}
    if not key:
        rng = random.Random(2026100223)
        for prefix, group in (("М", MALE), ("Ж", FEMALE)):
            order = list(group)
            rng.shuffle(order)
            for i, (label, model, voice) in enumerate(order, 1):
                key[f"{prefix}{i:02}"] = {"label": label, "model": model, "voice": voice}
        keyfile.write_text(json.dumps(key, ensure_ascii=False, indent=1))
    async with httpx.AsyncClient() as client:
        for name, v in key.items():
            if only and v["label"] != only:
                continue
            out = OUT / f"{name}.mp3"
            if out.exists() and not only:
                continue
            try:
                raw, kind = (await via_fish(v["voice"]) if v["model"] == "fish"
                             else await via_router(client, v["model"], v["voice"]))
                level(raw, kind, out)
                print(f"{name} ← {v['label']}: ok", flush=True)
            except Exception as e:  # noqa: BLE001 — one voice failing does not stop the rest
                print(f"{name} ← {v['label']}: FAILED {e}", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--only")
    asyncio.run(main(ap.parse_args().only))
