# «Не слышит» — what it actually means

The companion screen has exactly one thing to say when something is wrong:
**«не слышит»**. That is on purpose and it isn't going to change — a lonely
person must never be shown an error code, a status bar, or a retry button.

But that one phrase covers at least six unrelated problems whose fixes have
nothing in common. This page is how you tell them apart.

**The app will never tell you which one it is on the main screen. Go to
Настройки → Сервер → «Проверить связь».** That screen is the only place in the
app allowed to be technical, and it names the problem in plain words.

---

## Read the phone first, then the terminal

Two places hold the answer, and they hold different halves of it.

| Where | Shows |
|---|---|
| Настройки → Сервер → «Проверить связь» | Can the phone reach the Mac at all |
| The Terminal running `./run.sh` | Why the Mac refused, once it was reached |

---

## 1 · iOS is blocking the app from your home network

The single most common one, and the most misleading.

```
Error Domain=NSURLErrorDomain Code=-1009 "The Internet connection appears to be offline."
_NSURLErrorNWPathKey=unsatisfied (Local network prohibited), interface: en0[802.11]
```

The phone is plainly online. iOS reports a **blocked local network** with the
same error code as **no internet at all**, so `localizedDescription` sends you
to the Wi-Fi settings — the one place the fix isn't. The real tell is the
`(Local network prohibited)` clause.

**Fix:** Настройки → Приложения → Боб → **«Локальная сеть»** → on.

If Боб isn't in that list, iOS never asked. Delete the app, install it again,
and allow it when the prompt appears. The prompt appears once, on the app's
first attempt to reach a local address — and the request that triggers it
*fails*, which is normal. The next one succeeds.

## 2 · The address is stale

Your Mac's address on the Wi-Fi changes whenever the router feels like it —
after a reboot, after a lease expires, after switching networks.

```bash
ipconfig getifaddr en0
```

Put exactly that, with `http://` and `:8000`, into Настройки → Сервер.

Note that the address in the **backend's** log is the *phone's*, not the Mac's:

```
INFO:  192.168.0.107:59760 - "POST /api/talk HTTP/1.1" 503
       └── this is the iPhone
```

So seeing a different number there than the one you typed is not a mismatch —
it's the two ends of the same conversation.

## 3 · The server isn't running

`«По этому адресу никто не отвечает»`. The Terminal window with `./run.sh` was
closed, or the Mac slept. Both ends must be awake and on the same Wi-Fi.

## 4 · The turn took too long

Every turn is three round trips — ears (Whisper), brain (Claude), voice (Fish) —
and on home Wi-Fi that lands at 8–15 seconds more often than it looks like it
should. The client waits 30 s before giving up (`BackendClient.talk`). If you
see «не слышит» *after a long think* rather than immediately, this is it, and
the answer is a faster voice provider, not a longer timeout.

## 5 · A key is refused or out of credit

This is the one that produces a **503** in the Terminal. The line uvicorn prints
by itself tells you nothing:

```
INFO:  192.168.0.107:59760 - "POST /api/talk HTTP/1.1" 503 Service Unavailable
```

Since `app/main.py` grew `_unavailable()`, the reason is printed directly above
it, naming which of the three parts failed:

```
  ✗ 🗣️ the voice failed
    Fish Audio TTS failed (402): insufficient balance
```

The stage name is the diagnosis:

| Stage in the log | What's wrong |
|---|---|
| `👂 the ears (Whisper)` | `OPENAI_API_KEY` missing, refused, or out of credit |
| `🧠 the brain (Claude) / 🗣️ the voice` | `ANTHROPIC_API_KEY`, or the voice provider said no |
| `🗣️ the voice` | the voice provider alone — usually credit, or a dead voice ID |

To test all three for real, without waiting for a conversation to fail:

```bash
cd backend
source .venv/bin/activate
python check_keys.py
```

**`check_keys.py` now actually makes the voice speak.** It used to print
`🗣️ Голос: fish настроен` whenever a key was present — a statement about the
`.env` file, not about the voice. A key can be present and still be refused,
out of credit, or pointed at a voice ID that no longer exists, and all three
look identical from the outside. It costs a fraction of a cent to say two words
and know.

The same caveat applies to `/api/health`, and so to «Проверить связь»: it
reports whether keys are **present**, not whether they **work**. That is why it
says «ключи на месте» and never «всё работает».

### If it's the voice, don't fix it — swap it

The voice is the only one of the three with a spare already paid for. The ears
and the brain each have exactly one supplier, so a broken one has to be
repaired. The voice does not: **OpenAI does text-to-speech with the same key
that already does the ears.**

```bash
cd backend
source .venv/bin/activate
python switch_voice.py openai
```

That changes one line in `.env` — the line naming the provider — then says two
words out loud to prove it. Keys are never read, printed, or moved, and every
other line of the file comes out byte for byte identical.

So a dead Fish balance, a Fish outage, or a voice ID that was deleted are all
about ninety seconds of inconvenience, not a blocked day. Choosing the voice
you actually want is a separate job, done later and calmly, with
`python audition.py`.

## 6 · The microphone

If he never even reaches «думает», he isn't hearing the room. Настройки →
Приложения → Боб → Микрофон. The app also offers this itself the first time.

---

## The order to check things in

1. Настройки → Сервер → **«Проверить связь»**. Fixes 1, 2 and 3.
2. If it says the server is on the air, look at the **Terminal** and find the
   `✗` line above the 503. Fixes 5.
3. If there is no 503 and no `✗`, but he thinks for a long time and then says
   «не слышит» — that's 4.
