"""A person on the live channel, timed: hears his hello, then says three recorded
things in real time (u1–u3.pcm, 16 kHz mono), and times each answer from the end
of their speech to his first sound — end to end, with the real services.

    python live_check/client.py [ws://127.0.0.1:8765/api/live]

Start the server first (`.claude/launch.json`, «live-backend»). docs/LATENCY.md."""
import asyncio
import json
import sys
import time
import uuid
from pathlib import Path

from websockets.asyncio.client import connect

HERE = Path(__file__).parent
FRAME = 2560           # 80 ms at 16 kHz, 16-bit
ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
URL = ARGS[0] if ARGS else "ws://127.0.0.1:8765/api/live"
ROUNDS = int(next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--rounds=")), "1"))
#: His first sounds (first_sound.py) — not words.
SOUNDS = {"М-м…", "Хм…", "Так…", "Да…", "Ну…", "(вдох)", "Mm…", "Hmm…", "So…", "Yeah…", "Well…", "(breath)"}
#: The server's own marks, in the order they happen (live.Session._answer).
STEPS = [("draft_started", "«похоже, договорил» — черновик начат"),
         ("brain_asked", "промпт собран, мозг спрошен"),
         ("first_words", "мозг: первые слова"),
         ("first_piece", "первый кусок готов (до первой паузы)"),
         ("voice_asked", "голос спрошен"),
         ("voice_ready", "голос: первый звук"),
         ("first_audio", "первое слово ушло на телефон")]


async def main() -> None:
    token = f"probe-{uuid.uuid4()}"
    async with connect(URL, max_size=2**24) as ws:
        await ws.send(json.dumps({"type": "start", "token": token, "hello": True, "duplex": True}))
        state = {"audio": 0.0, "rate": 44100, "first_audio": None, "heard": None, "done": None,
                 "speech_end": None, "timing_heard": None, "timing_done": None, "reply": "", "ready": False,
                 "word_said": False, "first_word": None}
        done_event = asyncio.Event()

        async def reader():
            async for raw in ws:
                now = time.monotonic()
                if isinstance(raw, bytes):
                    state["audio"] += len(raw) / (2 * state["rate"])
                    if state["first_audio"] is None:
                        state["first_audio"] = now
                    if state["word_said"] and state["first_word"] is None:
                        state["first_word"] = now
                    continue
                m = json.loads(raw)
                kind = m.get("kind")
                if kind == "ready":
                    state["ready"] = True
                elif kind == "say":
                    state["rate"] = m.get("rate", state["rate"])
                    if m["text"] not in SOUNDS:
                        state["word_said"] = True
                    print(f"      say «{m['text']}» @{m.get('rate')}", flush=True)
                elif kind == "heard":
                    state["heard"] = now
                    state["timing_heard"] = m.get("timing")
                    print(f"   heard «{m['transcript']}» {m.get('timing')}", flush=True)
                elif kind == "done":
                    state["done"] = now
                    state["timing_done"] = m.get("timing")
                    state["reply"] = m.get("reply")
                    done_event.set()
                elif kind in ("trouble", "asleep", "daily_limit", "idle", "replaced", "alarm", "interrupted"):
                    print("   !!", m, flush=True)
                    if kind == "trouble":
                        done_event.set()

        read_task = asyncio.create_task(reader())
        while not state["ready"]:
            await asyncio.sleep(0.05)

        async def silence(seconds):
            for _ in range(int(seconds / 0.08)):
                await ws.send(bytes(FRAME))
                await asyncio.sleep(0.08)

        async def wait_reply_and_play():
            """Keep the microphone streaming (silence) until he is done, then
            'play' what he sent in real time and report it played."""
            began = time.monotonic()
            while not done_event.is_set():
                await ws.send(bytes(FRAME))
                await asyncio.sleep(0.08)
            played_until = began + state["audio"] + 0.1
            while time.monotonic() < played_until:
                await ws.send(bytes(FRAME))
                await asyncio.sleep(0.08)
            await ws.send(json.dumps({"type": "played"}))

        print("HELLO", flush=True)
        await wait_reply_and_play()
        print(f"   hello: «{state['reply']}» (audio {state['audio']:.1f}s)", flush=True)

        results = []
        for n in [1, 2, 3] * ROUNDS:
            for k in ("first_audio", "heard", "done", "speech_end", "first_word"):
                state[k] = None
            state["word_said"] = False
            state["audio"] = 0.0
            done_event.clear()
            await silence(0.8)
            speech = (HERE / f"u{n}.pcm").read_bytes()
            print(f"TURN {n}", flush=True)
            for i in range(0, len(speech), FRAME):
                await ws.send(speech[i:i + FRAME].ljust(FRAME, b"\0"))
                await asyncio.sleep(0.08)
            state["speech_end"] = time.monotonic()
            await wait_reply_and_play()
            end = state["speech_end"]
            r = {
                "heard": state["heard"] - end if state["heard"] else None,
                "first_audio": state["first_audio"] - end if state["first_audio"] else None,
                "first_word": state["first_word"] - end if state["first_word"] else None,
                "done": state["done"] - end if state["done"] else None,
                "server_heard": state["timing_heard"], "server_done": state["timing_done"],
            }
            results.append(r)
            print(f"   reply: «{state['reply']}»", flush=True)
            if r["first_audio"] is not None and r["done"] is not None:
                print(f"   → end of speech → heard {r['heard']:.2f}s, FIRST AUDIO {r['first_audio']:.2f}s, "
                      f"all sent {r['done']:.2f}s | server {r['server_done']}", flush=True)
        await ws.send(json.dumps({"type": "stop"}))
        read_task.cancel()
        firsts = sorted(r["first_audio"] for r in results if r["first_audio"])
        print("\nFIRST AUDIO after end of speech:", ", ".join(f"{x:.2f}s" for x in firsts))
        report(results)


def report(results: list[dict]) -> None:
    """Each step's moment after the end of their speech: the median, and the range."""
    def row(label: str, values: list[float]) -> str:
        values = sorted(v for v in values if v is not None)
        if not values:
            return f"  {label:44} —"
        mid = values[len(values) // 2]
        return f"  {label:44} {mid:5.2f} с   ({values[0]:.2f}–{values[-1]:.2f})"

    print("\nПО ШАГАМ — секунды от конца фразы человека (медиана, разброс):")
    for key, label in STEPS:
        print(row(label, [(r["server_done"] or {}).get(key) for r in results]))
    print(row("«договорил» точно (уши)", [(r["server_heard"] or {}).get("end_of_turn") for r in results]))
    print(row("телефон: первый звук («м-м» или слово)", [r["first_audio"] for r in results]))
    print(row("телефон: первое СЛОВО", [r["first_word"] for r in results]))


asyncio.run(main())
