# The soul — how a friend is made, and how he thinks fast

The most important subsystem in the app, and the user said it exactly right:

> *"Real human does not speak randomly about life that he's never lived
> before. He's talking about life that he's lived, and that is already
> sitting in his memory."*

That sentence is the architecture. Thinking splits into two completely
different jobs, done at two completely different moments:

| | WRITING him | BEING him |
|---|---|---|
| When | Once, on the arriving screen | Every turn, out loud |
| What | A whole person: past, opinions, manner, people, current life | One or two warm sentences AS that person |
| Time budget | 20–30 s is fine — the screen is beautiful | Every second is a silence someone sits through |
| Model | `BRAIN_MODEL` (Sonnet — deep) | `CHAT_MODEL` (Haiku — fast) |
| Where | `matchmaker.py` → `data/persona.json` | `main.py → brain.py`, persona injected |

He does **not** invent his life while talking. His life is a document,
written once, and conversation *inhabits* it. Inventing at reply time is what
made him slow; a fully-written persona is what makes the fast model warm.

---

## Why every friend was the same person

Three separate bugs and one deep property of language models stacked on top
of each other. All four had to fall.

**1 · The template leak.** `persona.py` carries `DEFAULT_PERSONA` — a safe
fallback character so the browser dev page works on a fresh checkout. That
fallback is *literally* the 87-year-old by the sea with the cat Мурзик and
the café owner Марко. Talk to the backend before any character is created
(the localhost test) and that is who answers.

**2 · The merge backfill.** Worse: `save_persona` used to merge
`DEFAULT_PERSONA` *underneath* every created character. Any field the pen
left blank arrived pre-filled with the template's life. Three different
friends, one identical cat. Now a created character contains only what was
created — a gap stays a gap, and `build_persona_block` simply skips it. A
gap is honest; a borrowed life is not.

**3 · The inherited memory.** Creating a new friend never erased the old
friend's self-memories, conversation log, or diary. Friend number two
remembered friend number one's fishing trips as his own and contradicted his
own biography mid-sentence. `matchmaker._fresh_start()` now wipes his side —
`owner='bob'` memories, `turns`, `diary` — and keeps the elder's: the user's
birthday is true no matter who they talk to.

**4 · Mode collapse — the deep one.** Ask a language model to "invent a
person" and it picks the most *probable* person. The most probable companion
for a lonely Russian speaker is the warm old man in a small town by the sea —
ask a thousand times, get him a thousand times. This is not laziness;
it is what sampling the middle of a probability distribution means.
**Творческий выбор нельзя доверять генератору вероятностей.**

## The fix for 4: dice on the outside

Randomness must come from *outside* the model. In `matchmaker.py`, Python's
`random` — real, uniform, indifferent — rolls the skeleton before the model
is ever consulted:

- **age** — 24 to 87, flat. Old is one face of the dice, not the default
- **place** — big noisy city, northern town, village, mountain settlement…
  the sea is *one* entry in the list
- **trade** — 36 of them: bus driver, crane operator, beekeeper, boxing
  coach, metro driver, piano tuner…
- **temper** — including *ворчливый, но добрейшей души* and *упрямый спорщик*
- **what life did to him** — divorce, a lost job, a move he still misses,
  raising a child alone…
- **what's happening right now** — the motorcycle that will ride again, the
  neighbour feud he knows is silly, the puppy he pretends not to love
- **animal** — usually *none*: the lonely-man-with-a-cat is its own cliché

The model's job changes from "invent a person" (where it collapses to the
average) to "make THIS skeleton into a living person who fits THIS user's
story" — constraint satisfaction, which models are genuinely good at.

**The order of power is strict:** the user's wishes beat the dice; the dice
beat the model's habits. Wish for "около 30, женщина, с Урала" and exactly
those dice are taken off the table; everything else still rolls.

**Disagreement is mandatory.** The genesis prompt requires at least one
opinion that — judging from the user's own story — the user will probably
*not* share, plus something he honestly dislikes that the user seems to love.
Gentle, живейское: food, music, habits, how to rest. Never their family,
their health, their griefs. A friend who agrees with everything is furniture.

**Incomplete is rejected, not patched.** If the pen returns a character
missing name / age / home / backstory / personality / speech_style, creation
fails and is retried — the holes are never filled from a template again.

---

## The speed of a reply

What actually happens between "he stops talking" and "Боб starts":

```
end-of-speech pause (app VAD)      1.2 s   fixed, tunable
Whisper (ears)                    ~1 s
memory recall (embeddings)        ~0.3 s
Claude (the reply)                 2–6 s   ← was the big one
TTS (the voice)                    1–3 s   scales with reply length
```

What changed, in order of impact:

1. **Fast model for turns.** Chat runs on `CHAT_MODEL` (Haiku 4.5) — it
   answers markedly faster than Sonnet, and because the character arrives
   fully written, it plays him rather than writing him. Deep work (genesis,
   diary, learning) stays on `BRAIN_MODEL` (Sonnet), where nobody waits.
   `CHAT_MODEL=claude-sonnet-5` in `.env` reverts every turn to the big brain.

2. **Web search only when asked-for.** The search tool used to be attached
   to *every* turn; an available tool invites the model to consider it, and a
   search costs seconds. Now `brain.wants_fresh_info()` gates it on the
   message actually mentioning news / weather / prices — and those rare turns
   run on Sonnet (which carries the tool). A missed keyword just means he
   answers from his own head, like any person without a phone in his hand.

3. **The character is cached provider-side.** The system prompt splits at a
   hard boundary (`companion.build_system_parts`): the *stable* head (rules +
   persona, ~3k tokens, byte-identical every turn) carries
   `cache_control: ephemeral`, so Claude re-reads it from cache instead of
   re-processing it; the *variable* tail (memory, occasion, mood) rides
   uncached behind it. Moving a changing field into the head breaks nothing
   visibly — the cache just misses every turn and buys nothing. Don't.

4. **Shorter history window.** 20 turns → 12. Spoken chat doesn't thread
   further back than that, and anything that mattered was distilled into
   memory and returns through recall.

### The next big win (not built yet): speaking in sentences

The chain above is serial: the voice can't start until the *whole* reply is
written. The known fix is sentence streaming — stream the reply, cut at the
first sentence boundary, synthesize and play *that* while the rest is still
being written. It cuts felt latency roughly in half but needs the app to play
chunked audio, so it's a protocol change for later, noted here so it isn't
forgotten.

---

## What "Начать заново" must mean

Recreating the friend goes through `POST /api/companion/create`, which now
implies the clean slate (`_fresh_start`). An existing install that met Мурзик
has him **baked into its `data/persona.json`** — the file was saved through
the old merging code. The escape is simply to create a new friend once on the
new code: настройки → «Начать заново».
