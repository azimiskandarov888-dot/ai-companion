"""Gemini Live, timed exactly as live_check/client.py times Bob: the same three
recorded phrases (u1–u3.pcm), sent in real time, and the seconds from the end
of each phrase to the model's first sound — with Bob's own instructions, in his
own voice. The owner, 2026-10-03: «i want to see exactly where we lose our
time» (docs/WHY-LIVE-IS-FAST.md).

    python live_check/gemini_live.py [model] [--client-end]

  model         gemini-3.8-live (default), gemini-2.5-flash-native-audio-latest, …
  --client-end  say «finished» the moment the phrase ends (Google's own ears
                off, activityStart/activityEnd from us), as the benchmarks do;
                without it Google's ears decide, after their default ~0.8 s of
                silence — as a person would meet it.
  --no-think    the model may not think before it speaks (thinkingBudget 0).

Needs GEMINI_API_KEY in backend/.env. Never prints it.
"""
import asyncio
import base64
import json
import sys
import tempfile
import time
from pathlib import Path

from websockets.asyncio.client import connect

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent))
from dotenv import dotenv_values  # noqa: E402

KEY = dotenv_values(HERE.parent / ".env").get("GEMINI_API_KEY")
URL = "wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent"
FRAME = 2560           # 80 ms at 16 kHz, 16-bit — as client.py sends them
ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
MODEL = ARGS[0] if ARGS else "gemini-3.8-live"
CLIENT_END = "--client-end" in sys.argv
NO_THINK = "--no-think" in sys.argv


async def bobs_instructions() -> str:
    """His real prompt for a first meeting — the same the app would send."""
    from app import config, db, main, persona, safety
    from rehearse import COMPANIONS

    async def quiet(*_a, **_k):
        return None

    tmp = Path(tempfile.mkdtemp(prefix="gemini-live-"))
    config.DATA_DIR, config.DB_PATH = tmp, tmp / "x.db"
    config.PERSONA_PATH, config.READING_PATH = tmp / "p.json", tmp / "r.json"
    db.init_db()
    safety.look = quiet
    persona.save_persona("gemini-live", COMPANIONS["mark"])
    stable, variable, _history, _voice, _w = await main._assemble(
        "gemini-live", "Привет.", pending=True, marks=[], by_ear=True)
    return f"{stable}\n\n{variable}"


async def main() -> None:
    if not KEY:
        sys.exit("Нужен GEMINI_API_KEY в backend/.env")
    instructions = await bobs_instructions()
    setup = {"setup": {
        "model": f"models/{MODEL}",
        "generationConfig": {"responseModalities": ["AUDIO"],
                             "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": "Zubenelgenubi"}}}},
        "systemInstruction": {"parts": [{"text": instructions}]},
        "inputAudioTranscription": {},
        "outputAudioTranscription": {},
    }}
    if CLIENT_END:
        setup["setup"]["realtimeInputConfig"] = {"automaticActivityDetection": {"disabled": True}}
    if NO_THINK:
        setup["setup"]["generationConfig"]["thinkingConfig"] = {"thinkingBudget": 0}
    async with connect(URL, additional_headers={"x-goog-api-key": KEY}, max_size=2**24) as ws:
        began = time.monotonic()
        await ws.send(json.dumps(setup))
        while True:
            reply = json.loads(await ws.recv())
            if "setupComplete" in reply:
                break
            if "error" in reply:
                sys.exit(f"setup refused: {reply}")
        print(f"{MODEL}: ready in {time.monotonic() - began:.2f} s "
              f"({'end said by us' if CLIENT_END else 'Google decides the end'})", flush=True)

        state = {"first_audio": None, "done": asyncio.Event(), "heard": "", "said": ""}

        async def reader() -> None:
            async for raw in ws:
                message = json.loads(raw)
                content = message.get("serverContent") or {}
                for part in (content.get("modelTurn") or {}).get("parts") or []:
                    if (part.get("inlineData") or {}).get("data") and state["first_audio"] is None:
                        state["first_audio"] = time.monotonic()
                if text := (content.get("inputTranscription") or {}).get("text"):
                    state["heard"] += text
                if text := (content.get("outputTranscription") or {}).get("text"):
                    state["said"] += text
                if content.get("turnComplete"):
                    state["done"].set()

        async def send(pcm: bytes) -> None:
            data = {"data": base64.b64encode(pcm).decode(), "mimeType": "audio/pcm;rate=16000"}
            # The 2.5 native-audio models take the older form of the same message.
            body = {"mediaChunks": [data]} if MODEL.startswith("gemini-2.5") else {"audio": data}
            await ws.send(json.dumps({"realtimeInput": body}))

        listening = asyncio.create_task(reader())
        results = []
        for n in (1, 2, 3):
            state.update(first_audio=None, heard="", said="")
            state["done"].clear()
            for _ in range(10):                                   # 0.8 s of quiet first
                await send(bytes(FRAME))
                await asyncio.sleep(0.08)
            speech = (HERE / f"u{n}.pcm").read_bytes()
            if CLIENT_END:
                await ws.send(json.dumps({"realtimeInput": {"activityStart": {}}}))
            for i in range(0, len(speech), FRAME):
                await send(speech[i:i + FRAME].ljust(FRAME, b"\0"))
                await asyncio.sleep(0.08)
            end = time.monotonic()
            if CLIENT_END:
                await ws.send(json.dumps({"realtimeInput": {"activityEnd": {}}}))
            while not state["done"].is_set() and time.monotonic() - end < 20:
                if not CLIENT_END:
                    await send(bytes(FRAME))                      # the room, quiet, as a microphone hears it
                await asyncio.sleep(0.08)
            first = state["first_audio"] - end if state["first_audio"] else None
            results.append(first)
            print(f"  TURN {n}: heard «{state['heard'].strip()}» → said «{state['said'].strip()[:90]}»", flush=True)
            print(f"          FIRST SOUND {first:.2f} s after the end of the phrase" if first else
                  "          no sound", flush=True)
            await asyncio.sleep(0.5)
        listening.cancel()
        got = sorted(r for r in results if r is not None)
        if got:
            print(f"\n{MODEL}: first sound {', '.join(f'{x:.2f}' for x in got)} s — median {got[len(got) // 2]:.2f} s")


asyncio.run(main())
