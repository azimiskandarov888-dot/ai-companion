"""All 30 Gemini voices in Russian, blind; and one voice as five different people.

    python voices_gemini.py

Every person gets a companion of his own, so every companion needs a voice of
his own — the owner, 2026-10-03: «we are not having 2 ai companions. we need
hundred of them voices, and atleast 10 out of them must be russian». Gemini's
30 voices all speak Russian; the same voice told whom it plays (speech_metadata
.style) becomes a different person. docs/VOICES-RU.md."""
import asyncio, json, random, subprocess, tempfile
from pathlib import Path
import httpx
from dotenv import dotenv_values

BACKEND = Path(__file__).resolve().parent
KEY = dotenv_values(BACKEND / ".env")["OPENROUTER_API_KEY"]
OUT = BACKEND / "data/listen/voices-ru/gemini-all"
MODEL = "google/gemini-3.8-flash-tts"
TEXT = ("Ого, сам программу пишешь? Слушай, это же… ну, это здорово! А про что она?\n\n"
        "М-м… понимаю. Тяжёлый день, да? Ничего. Давай просто посидим, поговорим.")
STYLE = "warm, relaxed and natural, like a friend talking in person — not a narrator"
# Google Cloud's own list (Chirp 3: HD voices), the same 30 voices.
MALE = ["Achird", "Algenib", "Algieba", "Alnilam", "Charon", "Enceladus", "Fenrir", "Iapetus", "Orus", "Puck",
        "Rasalgethi", "Sadachbia", "Sadaltager", "Schedar", "Umbriel", "Zubenelgenubi"]
FEMALE = ["Achernar", "Aoede", "Autonoe", "Callirrhoe", "Despina", "Erinome", "Gacrux", "Kore", "Laomedeia", "Leda",
          "Pulcherrima", "Sulafat", "Vindemiatrix", "Zephyr"]
# One voice, five different people — what a companion's own age and temper do to it.
PEOPLE = [
    ("Zubenelgenubi", "a man in his seventies: slow and unhurried, a little hoarse, kind, a long life behind him"),
    ("Zubenelgenubi", "a calm man of about forty: steady, low, friendly, in no hurry"),
    ("Zubenelgenubi", "a lively nineteen-year-old student: quick, bright, a bit cheeky, easily excited"),
    ("Callirrhoe", "a woman of about eighty: soft, slow, gentle, smiling as she speaks"),
    ("Callirrhoe", "a sixteen-year-old girl: fast, bright, giggly, full of energy"),
]

async def make(client, voice, style, out: Path):
    body = {"model": MODEL, "input": TEXT, "voice": voice, "response_format": "pcm",
            "provider": {"options": {"google-ai-studio": {"speech_metadata": {"style": style}}}}}
    for attempt in range(3):
        r = await client.post("https://openrouter.ai/api/v1/audio/speech", json=body,
                              headers={"Authorization": f"Bearer {KEY}"}, timeout=180)
        if r.status_code == 200:
            break
    r.raise_for_status()
    with tempfile.NamedTemporaryFile(suffix=".pcm") as f:
        f.write(r.content); f.flush()
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "s16le", "-ar", "24000", "-ac", "1", "-i", f.name,
                        "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-ar", "44100", "-ac", "1", "-b:a", "128k", str(out)],
                       check=True)

async def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rng = random.Random(2026100301)
    male, female = MALE[:], FEMALE[:]
    rng.shuffle(male); rng.shuffle(female)
    key = {}
    for i, v in enumerate(male + female, 1):
        key[f"{i:02}"] = {"voice": v, "gender": "male" if v in MALE else "female", "style": STYLE}
    for i, (v, style) in enumerate(PEOPLE, 1):
        key[f"P{i}"] = {"voice": v, "style": style}
    (OUT / ".key.json").write_text(json.dumps(key, ensure_ascii=False, indent=1))
    sem = asyncio.Semaphore(4)
    async with httpx.AsyncClient() as client:
        async def one(name, v):
            async with sem:
                out = OUT / f"{name}.mp3"
                if out.exists():
                    return
                try:
                    await make(client, v["voice"], v["style"], out)
                    print(name, "ok", flush=True)
                except Exception as e:  # noqa: BLE001
                    print(name, "FAILED", e, flush=True)
        await asyncio.gather(*(one(n, v) for n, v in key.items()))

asyncio.run(main())
