# His voice — which one, what it costs, and why he answers faster now

Two separate problems that both live in the mouth of the app.

---

## 1 · What Russian actually costs

Every provider quotes a headline price per character, or per "1M UTF-8 bytes".
For English those are the same number. **For Russian they are not: Cyrillic is
two bytes per character in UTF-8.** A provider that bills bytes charges exactly
double its advertised rate for this app, on every sentence, forever.

That single fact reorders the whole list. An hour of speech is roughly 55 000
characters:

| | per hour of Russian | notes |
|---|---|---|
| **Yandex SpeechKit** (standard) | **~33 ₽** | Russian voices made by Russians |
| **Yandex SpeechKit** (premium) | ~66 ₽ | noticeably better; still the cheapest tier of anyone else |
| OpenAI `gpt-4o-mini-tts` | ~$0.71 | same key as the ears; takes a direction on *how* to speak |
| Fish Audio `s1` / `s2-pro` | **~$1.65** | $15 per 1M **bytes** — so ~$30 per 1M Russian characters |
| ElevenLabs | ~$8.25 | warmest of the lot, and it shows up on the bill |

A person using their whole daily allowance is on the order of 1.5M characters
a month: about **$45 on Fish** against about **$11 on Yandex standard**. That
is the difference between the voice eating the subscription and the voice being
a rounding error.

Fish is a genuinely excellent model — its S2 wins blind preference tests
against ElevenLabs. It is simply the most expensive way to speak Russian, and
it was chosen here believing it was the cheapest.

**None of that decides it.** The person who has to listen for an hour a day
decides it. So:

```bash
cd backend
python3 audition.py --cost        # the table above, from the code
python3 audition.py --compare     # one voice per provider, same sentence, back to back
python3 audition.py --yandex      # the Russian male voices, best first
python3 audition.py <fish-id>     # a Fish voice — fish.audio/discovery → copy its id
```

Every candidate goes through the real `app/tts.py`, on a sentence chosen to
expose synthetic warmth (a greeting, a question, a dash, and an ordinary
thought). The files are kept, so you can compare again a day later instead of
trusting your memory of the third one.

---

## 1b · "Can't I just self-host it and pay nothing?"

Mostly no, and the exceptions are not the ones you'd expect.

| | self-host? |
|---|---|
| **ElevenLabs** | **No.** Closed weights, API only. There is nothing to host. |
| **Yandex SpeechKit** | **No.** Cloud only. |
| **OpenAI** | **No.** |
| **Fish Audio** | **Not usefully.** The weights on HuggingFace are `openaudio-s1-mini` — the small 0.5B distilled model, under **CC-BY-NC-SA-4.0, which is non-commercial**. The full S1 (4B, the one you're actually paying for) is cloud-only. Real self-hosting is an Enterprise contract with them. |

So "self-hosting ElevenLabs" and "self-hosting the Fish voice you picked" are
not things that exist. Nothing you can download is the voice you heard.

### Two things people get wrong about the economics

**Self-hosting is not free — it moves the cost from per-word to per-month.** A
neural TTS model wants a GPU, and a rented GPU is roughly €150–200/month
*whether or not anyone speaks*. At Yandex standard rates that same money buys
around 500 hours of speech a month. So a GPU only starts winning past roughly
50 heavy users. With two phones on it, renting a GPU costs about twenty times
more than the API.

**The one that IS free is a CPU model.** [Silero](https://github.com/snakers4/silero-models)
is made by a Russian team, is Russian-first (v5 does automatic stress placement
and homograph resolution, which is exactly what makes synthetic Russian sound
wrong), and runs fast on plain CPU — the same €4–8/month box the backend was
already going to live on. Licensing is the catch and it is worth reading
carefully: the repository is CC-BY-NC (non-commercial), **but the
`v5_cis_base` and `v5_cis_base_nostress` models are MIT**, which is the only
combination here that is both free to run and legal in a paid app.

Quality is a step below Yandex premium. It is the right escape hatch — if
Yandex ever becomes unreachable or unaffordable, this is where to go — and the
wrong place to start.

**Start on Yandex.** It is cheap enough that self-hosting cannot pay for itself
until there are a lot of people using this, and by then the decision will be
made with real numbers instead of guesses.

---

## 1c · Setting up Yandex, step by step

You need a Yandex account and a card. Budget about fifteen minutes. Nothing
here involves writing code.

**1. Sign in to the console.** Go to <https://console.yandex.cloud> and sign in
with your Yandex account.

**2. Set up billing.** It will ask you to create a billing account and attach a
card. There is a trial grant, so the first while is free. Speech synthesis is
billed per character — for testing, this is pennies.

**3. Find your folder ID.** On the console home page you'll see a cloud with a
folder inside it, usually called `default`. Click it. The folder ID is on that
page, near the top — a string like `b1gc1t4cb638xxxxxxxx`. **Copy it.**

**4. Make a service account.** In the left menu of that folder, open
**Identity and Access Management → Service accounts → Create service account**.

- Name it `speechkit-sa`
- Click **Add role** and choose **`ai.speechkit-tts.user`**
- Click **Create**

> Then go back to the **folder** page → **Access bindings** and check that
> `speechkit-sa` is actually listed there with that role. The dialog in the
> create-service-account flow silently fails to save the binding often enough
> that this is worth thirty seconds — it is the single most common reason for
> the 401 below.

**5. Make an API key.** Click the service account you just made. Find the
**API keys** section → **Create API key**.

> If it offers a **scope**, leave it unrestricted. A key narrowed to the wrong
> scope is refused no matter what roles the account has, and the error looks
> exactly like a missing role.

> The key is shown **once**. Copy it now. If you lose it, delete it and make
> another — no harm done.

**6. Put both into `backend/.env`.** Open that file and add three lines:

```ini
TTS_PROVIDER=yandex
YANDEX_API_KEY=<the key from step 5>
YANDEX_FOLDER_ID=<the folder id from step 3>
```

Leave `FISH_API_KEY` where it is. Nothing removes it, and switching back is one
word (`TTS_PROVIDER=fish`).

**7. Restart the server** — stop `./run.sh` with `Ctrl-C` and start it again.
The `.env` file is only read at startup.

**8. Listen before you commit to a voice:**

```bash
cd backend
python3 audition.py --yandex
```

That speaks the same sentence in each of the male voices, best first, and
saves the files so you can compare again tomorrow. Put the winner in `.env`:

```ini
YANDEX_VOICE=filipp
```

### The voices

**Bare names — there is no `:premium` suffix.** A great deal of Yandex's own
documentation still shows `filipp:premium`, and the live API rejects it with
a 400. `filipp` on its own **is** the premium male voice.

| tier | voices | price |
|---|---|---|
| premium | `filipp` (m) · `alena` (f) | ~66 ₽/hour |
| standard | `ermil` · `zahar` · `jane` · `omazh` · `oksana` | ~33 ₽/hour |

Which names your account actually accepts varies, so don't trust that table
either — `python3 audition.py --yandex` tries a wide shortlist, skips what
comes back 400, and prints what really worked.

`YANDEX_SPEED=0.95` is set slightly under 1.0 on purpose — kinder to an older
listener.

### "Emotion off" means MORE expression, not less

`YANDEX_EMOTION` is empty by default and should usually stay that way. It is
easy to read that as "he'll speak flatly", and it is the opposite.

`emotion` is a **crude override**: one of `neutral | good | evil`, applied to a
whole utterance, and supported only on the **standard** voices (in Russian,
`jane` and `omazh`). The **premium** voices refuse the parameter — because they
already do, properly, the thing it approximates. Yandex's own description: a
premium voice *evaluates the entire text before synthesis and selects the
intonation characteristic of human speech.*

So:

| | |
|---|---|
| `filipp`, no emotion | reads the sentence, decides how it should sound |
| `jane` + `emotion=good` | every line pinned to the same cheerful tone |

Pinning every sentence a lonely person hears to "good" is exactly what makes
synthetic speech sound like a call centre. The code sends `emotion` only when
you have explicitly set it *and* the voice can actually use it, and if the API
rejects it anyway it says so once in the terminal and carries on speaking
rather than going silent.

One honest cost of the streaming (§2): a premium voice plans intonation across
the text it is given, and it is now given one sentence at a time. Intonation
*within* each sentence — the bulk of it — is unaffected; what is lost is the
lean from one sentence into the next.

### If he says 401

```
Yandex SpeechKit failed (401): {"error_code":"UNAUTHORIZED",
"error_message":"rpc error: code = PermissionDenied desc = Permission to
[resource-manager.folder …, resource-manager.cloud …] denied"}
```

**This is not a bad key.** `UNAUTHORIZED` on the outside with
`PermissionDenied` on the inside means the key was read perfectly well and the
request was refused anyway. **Four** unrelated mistakes produce this identical
message, and nothing in the response distinguishes them.

**0. The billing account isn't active — check this first.** It is the one
cause that has nothing to do with anything you configured, and on a brand-new
cloud it is the likeliest. SpeechKit requires the billing account to be
`ACTIVE` or `TRIAL_ACTIVE`. Anything else — no card attached yet, a trial that
was never activated, `TRIAL_SUSPENDED` (the grant went to an earlier account
of yours), `TRIAL_EXPIRED`, `PAYMENT_REQUIRED` — denies permission to
everything in the cloud, and says so in exactly the words above.

Console → **Billing (Биллинг)** → look at the status. If it is not `ACTIVE` or
`TRIAL_ACTIVE`, activate the paid version and top up the minimum amount. Then
retry; nothing else needs changing.

**1. The service account has no role.** The commonest of the configuration
ones. In the console it is
easy to open the "add role" dialog and close it without the binding actually
saving. Check: **folder → Access bindings** (Права доступа). Your
`speechkit-sa` must be listed there with `ai.speechkit-tts.user`. If it isn't,
add it *from the folder's page* rather than from the service account's.

**2. The role is on a different folder than `YANDEX_FOLDER_ID`.** Also very
common — a cloud usually has more than one folder, and the service account was
made in one while the ID was copied from another. The folder id in the error
message is the one your request used: confirm the role is on **that** folder.

Careful: folder IDs and cloud IDs both start with `b1g…` and are easy to swap.
The folder ID is on the folder's own overview page, not the cloud's.

**3. The API key has a restricted scope.** Newer Yandex API keys let you narrow
what they may be used for. A key scoped to anything that isn't SpeechKit is
refused no matter what roles exist. Delete it and create one with **no scope
restriction**.

To tell which it is without touching the app, ask Yandex directly — and
**read the body**, because that is where the answer is:

```bash
curl -s -X POST https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize \
  -H "Authorization: Api-Key ВАШ_КЛЮЧ" \
  -d "text=проверка" -d "lang=ru-RU" -d "voice=filipp" \
  -d "folderId=ВАШ_FOLDER_ID" -d "format=mp3" \
  -o /tmp/test.mp3 -w "HTTP %{http_code}\n"

cat /tmp/test.mp3        # ← the actual reason lives here
```

`-o` sends the *response* to the file, and on a failure the response is the
error text, not audio. `HTTP 200` plus a `/tmp/test.mp3` that plays means the
credentials are fine and the problem is in `.env`. Anything else, and `cat`
prints the JSON that says which of the four it is.

### The other errors

`400` almost always means `YANDEX_FOLDER_ID` is missing or the voice name
doesn't exist. `429` means too many requests at once, or the billing account
has run out of credit.

### If Yandex won't take your card

It happens outside Russia and Kazakhstan. The fallback is **OpenAI**, using the
key you already have for the ears — about $0.71 an hour, still less than half
of Fish:

```ini
TTS_PROVIDER=openai
OPENAI_VOICE=ash
```

`OPENAI_VOICE_STYLE` in `config.py` is where his warmth is set: it takes a
plain-language direction for *how* to speak, not just what to say, and it is
the single most powerful knob on that provider.

---

## 2 · Why he answers faster

A turn used to be three waits laid end to end:

```
hear it all ─────▶ think it all ─────▶ say it all ─────▶ send
   1.5 s              2.4 s              0.9 s
                                                     ↑ first sound: 4.8 s
```

The listener sat through the sum. Now the last two overlap — the first
sentence is spoken aloud while the second is still being written:

```
hear it all ─▶ ┌ think ──────────────────────▶
               └ say ─▶ say ─▶ say ─▶
                    ↑ first sound: 2.6 s
```

Measured on the real server with realistic delays (`backend/` — Whisper 1.5 s,
Haiku ~2.4 s to write, voice 0.45 s + 0.006 s/char):

```
STREAMING            WHOLE REPLY (before)
 +2.61s Доброе утро.        4.83s  ← nothing at all until here
 +3.19s Как спалось?
 +4.67s Мне сегодня снилось море, не знаю почему.
```

**He starts speaking 2.2 seconds sooner**, and the pieces arrive faster than
they can be spoken, so there is no gap in the middle.

### Three decisions worth knowing about

**Sentence chunks, not a provider's live socket.** Fish has a WebSocket
streaming API and it works. Using it would bind the app to Fish — the one
provider we most need to be able to leave. Cutting the reply at sentence
boundaries and calling the ordinary REST endpoint per sentence gets the same
user-visible result and works identically on all four providers. It also means
plain MP3 files played back to back, with no gapless audio engine, because of
*where* the cuts are: at full stops, where a person draws breath anyway. A seam
between two sentences is not a glitch — it is a pause.

**The chunk floor was 90 characters, and that was measurably wrong.** The
reasoning was that a short chunk is a wasted round trip. But a high floor makes
the *second* piece swallow the whole rest of the reply, and the rest of the
reply cannot exist until it has been written — so he said «Доброе утро.» and
then stopped for a second and a half. The round trip a low floor costs is paid
while the previous sentence is still being spoken, where nobody can hear it.
The gap a high floor costs happens in the middle of him talking, where
everybody can. It is 12 now: near enough one sentence at a time.

**Writing and speaking are two tasks, not one loop.** The obvious version —
read a token, and when a sentence finishes go and synthesise it — looks like
streaming and is not. An async generator only advances when it is asked to, so
every half-second waiting on the voice is a half-second in which Claude is not
being read; the two serialise and most of the win evaporates. The writer now
runs flat out into a queue and the consumer takes fragments to the voice.
`test_the_voice_never_holds_up_the_writing` pins it.

### The wire

`POST /api/talk` with `Accept: application/x-ndjson` — one JSON object per line:

```
{"kind":"heard","transcript":"…"}
{"kind":"say","text":"Доброе утро.","audio_base64":"…"}
{"kind":"say","text":"Как спалось?","audio_base64":"…"}
{"kind":"done","reply":"…","seconds_left":9840}
{"kind":"trouble","detail":"…"}          ← only if it broke mid-sentence
```

Content negotiation rather than a second URL: the phone has one address to
know, and a client that has never heard of streaming cannot accidentally
receive one. Ask for anything else and you get the original single JSON object,
unchanged — which is how the browser dev page, curl, and every build that
predates this keep working.

`trouble` exists because a streaming response has already sent its status line
by the time anything can go wrong, so a 503 is no longer available. That is an
improvement rather than a workaround: some of his answer may already have been
heard, and the phone keeps it instead of throwing the turn away.

Two turns deliberately do **not** stream: a question that needs a web search
(the answer can still change after the search returns, by which time half of it
would have been said aloud), and anyone out of their daily allowance. Both fall
back to the whole-reply path, and the phone handles either shape.

### On the phone

`AudioPlayer` is a queue: pieces play back to back, in order, and
`waitUntilQuiet()` is only correct *after* the stream has ended — during it,
the queue running dry between two sentences would look like him having
finished. A piece that won't decode is skipped rather than allowed to stall the
rest of the sentence behind it: losing one fragment is bad, losing the
remainder is worse.
