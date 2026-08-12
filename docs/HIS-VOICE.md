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
