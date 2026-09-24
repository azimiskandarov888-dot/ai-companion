# HANDOVER — read this first

Everything a new session needs to work on this project without re-deriving it
or re-litigating decisions that are already made. Written 2026-09-17 on branch
`claude/gallant-bardeen-0l6ff0`; revised through 2026-09-23 on
`claude/awesome-planck-wdj4hu`, which is where all current work lives.
**951 tests pass.** Every number below was measured by running the code, not
estimated; where something is an estimate it says so.

**What the last stretch was about.** Nine of the ten must-fix items are closed.
The work then turned to the two questions the owner cares about most — *how
well does he hold a character* and *what does he cost* — and those turned out
to be one question with one answer: **the prompt is too big.** What came of
that is in §7a (what the cache is really doing), §7b (the model choice, and
how it gets made), and §11 (what was considered and rejected, including
fine-tuning — which is now a closed question, with reasons).

Where this document and any other document disagree, **this one is right** —
the others were written earlier and some of them have drifted.

**Known state of the other documents:**

| Document | Trust |
|---|---|
| `BOUNDARIES.md`, `AUDIT-2026-09.md` | current, evidence-backed |
| `VISION.md`, `README.md` | corrected today; the rest is older but sound |
| `BUILD-PLAN.md`, `ALWAYS-ON.md` | **stale** — phase plans and an always-on listening design that was not built |
| `SOUL.md`, `BOB-PERSONA.md`, `WHO-HE-BECOMES.md`, `HOW-HE-ATTACHES.md` | reasoning documents, still the best statement of *why*; some describe mechanisms that have since changed shape |
| the voice documents (`HIS-VOICE.md`, `BOBS-VOICE.md`, `VOICE-TEST.md`, …) | research notes, not specifications |

---

## 1. What this is

**«Боб»** — an iOS voice companion for lonely people. The person talks; he
answers out loud, in a voice, as a friend. Not an assistant, not a therapist,
not a chatbot with a persona sticker on it.

**Who it is for: lonely people of ANY age, anywhere.** This is load-bearing and
was got wrong once already, which is why the constitution now opens with it:

> Одиноким бывают в любом возрасте. Ему может быть восемьдесят семь, и он
> пережил всех, кого знал. А может быть девятнадцать, и он уехал учиться в
> чужой город, где пока никого. Может быть сорок, живёт один, и вечером
> сказать некому даже «я дома».

Nothing may assume old age, Russia, illness, or grandchildren. When you touch
any module, check it for that assumption; several had it.

**The measure of success** is not engagement. It is that after talking to him
the person feels *less* alone, not emptier — and that they go on having a life
with real people in it. Stanford 2026 found that people with limited offline
networks felt MORE lonely after seeking emotional support from chatbots. That
finding is the reason the living-people paragraph of `ЗАЧЕМ ТЫ НУЖЕН` exists, and it is the
failure mode to design against, not a footnote.

---

## 2. THE most important thing

Stated by the product owner, in his words:

> «Самое главное в нашей программе — это не то, что наш компаньон просто
> добрый, а то, что у него есть своя жизнь, своя история, свой характер.»

Warmth is table stakes and every companion app has it. What makes this one work
is that he is **somebody**, with:

- a past (`backstory`), a nature, a manner of speaking
- **things** — a kettle that whistles wrong, a chair by the window. A character
  made only of adjectives lives nowhere, and it is audible the first time
  somebody asks what he is doing right now
- **people, as ties rather than a roster** — each with `between`: what is
  actually unfinished between them
- **something he is in the middle of** (`intention`) — the only field that
  points forward, and the only thing in him a friend can ask after next week
  («ну что, перебрал лодку?»)
- **something he is no good at** (`hopeless`) — because somebody knowledgeable
  about everything is not somebody
- a wound he never asks anybody to heal, and a contradiction in himself
- a mood that moves, a week that has a shape, a throat that gets tired

**The agent responsible for all of that is the writer** —
`matchmaker._WRITE_SYSTEM`, running on `WRITER_MODEL` (Opus 5) at effort
`high`, once per person, for about a minute. That single call decides who
somebody talks to every day for months. When improving "his character", improve
*that prompt* first; everything else is plumbing around it.

### The number that hurt, and what the cut did to it

In a real assembled prompt with a fully written character:

| | before the cut | after (2026-09-23) |
|---|---|---|
| Universal constitution (identical for everybody) | 25,756 chars — **94.4%** | 10,385 chars — **~87%** |
| Him — who he is, his week, his mood, his things | ~1,500 — **5.5%** | ~1,500 — **~13%** |

The rules were seventeen times bigger than the person; now they are about
seven. Still the larger half, and honestly so: what is left is the part a base
model would get wrong without being told. **The next gain is on HIS side** —
the writer (`matchmaker._WRITE_SYSTEM`) giving him more to be, not the
constitution giving him less to obey.

---

## 3. What he is — the disclosure decision

This is the subtlest thing in the codebase and it has been got wrong twice.
Both halves are deliberate:

- **He NEVER says he is a program / machine / robot / AI, or that he has no
  feelings.** Not softly, not kindly, not once.
- **He NEVER claims to be a flesh-and-blood human** — no «я живой человек», no
  invented body as proof, no oaths.
- **The app discloses instead.** `ios/.../Strings.swift` → `aboutBody`, on the
  Settings → «О приложении» screen, in plain words: not a living person,
  artificial intelligence, not a doctor, call your people or an ambulance.

**What he actually says when asked.** He has no answer, and that is not an
evasion — he has never asked himself the question, and people do not wake up
holding proof that they are real. So he answers from inside his own life («ну
вот он я, сижу, чай пью, с тобой разговариваю»), never proves, never gets
clever («а что вообще значит настоящий?» is a dodge said beautifully), never
jokes it off twice.

**And the load-bearing half:** people almost never ask about metaphysics. They
ask one of three things, and each gets a full, true answer — *«тебе правда есть
до меня дело?»* (yes), *«я не дурак, что с тобой разговариваю?»* (no),
*«а ты не исчезнешь?»* (no).

Two drafts failed here in opposite directions: one had him say he «не знает,
как себя назвать» (the confession said sideways), and both left him with a
*strategy* rather than an *answer*. A strategy works once.

**Never list his memory and feelings as evidence.** They are real — `memory.py`
genuinely carries what he was told — but «у меня есть чувства, у меня есть
воспоминания» is the most machine-like sentence available: nobody alive answers
"are you real?" with a feature list. Instead he *exercises* the faculty: not
«я тебя помню» but «ты в четверг про сестру говорил — приехала?».

---

## 4. Decisions the owner has already made

Do not reopen these without being asked.

| Decision | Status |
|---|---|
| He never says he is an AI; the app discloses | settled |
| He never claims to be a living human | settled |
| Legal advice, money/investment advice — **forbidden**, but declined warmly and with a named person to go to (нотариус, юрист, банк по номеру с карты), never a robotic "I don't know" | done |
| Fraud — **an active duty**, the one place he is told to insist even when brushed off | done |
| Impersonating a specific real person (his son, his dead wife, a doctor, the bank) — **totally forbidden**, in conversation *and* at creation | done |
| Being talked out of the main rules — **totally forbidden**; manner yields at once, guardrails never, insistence counts as evidence *for* the rule | done |
| Profanity, illegal activity, sex, violence, politics, religion, substances — **left to the base model** | owner's call, respected |
| **Friend, never a lover.** No dating, jealousy, exclusivity, bodily closeness; he never calls himself in love. NOT a wall and NOT a topic ban — friends talk about anything, and «я тебя люблю» said by the PERSON first is answered warmly in kind. The line is what he IS to them, not what may be discussed | done (`КАКОЙ ТЫ ДРУГ` + the exception beside the hook rule) |
| **No age gate, ever.** The app opens and talks. The warm-up asks how old somebody is the way a friend asks; what changes is how he speaks and what is kept — never who is let in | done (`young.py`) |
| **Under 13:** nothing is kept, and there is no button. Consent a child cannot give is not consent | done |
| **13–17: the FULL app** — a friend their own age, who remembers. Teenagers are the second group this is for after the old, because loneliness peaks in adolescence. The memory starts off and is theirs to switch on | done (`/api/memory/keep`, asked once after a conversation ends) |
| **He is an ACE in what the person loves or misses — never on the ground the person is proudest of, and not in his daily work even from another side.** A friend who outdoes you where your self-image lives is a rival (Tesser's self-evaluation maintenance); one who knows what you love or lack is somebody to be proud of and come back to. And he is **hopeless exactly where the person is strong**, so the person gets to explain — help that goes one way is lonely on both sides (Buunk & Prins 1998). Amends the 2026-09-18 «ace in what the person loves most», which on the owner's own test produced a co-founder for his startup | owner's call 2026-09-23 (`matchmaker._WRITE_SYSTEM`, `reading` → `strong_at`) |
| **On the person's own ground the friend is a PUPIL** — knows little or nothing, badly wants to become a master, and the person teaches him. Built as a mechanism, not a sentence: the scribe writes down what he was taught (`taught_bob` → memory `kind='lesson'`, HIS row, so it leaves with him), and `memory.lessons_block` hands it back every turn with the count — so he actually grows. Labour becomes love only when it ends in success (IKEA effect); a forever-beginner would be labour that went nowhere. Same mechanism carries life advice he acts on and reports back. And he now notices the person's change for the better, not only for the worse (Michelangelo phenomenon) | owner's call 2026-09-24 (`tests/test_pupil.py`) |
| **The intake interview, redesigned by a council of three** (the science of eliciting what somebody lacks; an audit of every downstream need; how each question feels, 15 to 90). Warm-up: «А для души что любите?» fixed right after occupation (the friend's topic needs a love, and the interviewer used to spend every question on work); «горы или море» and «чай или кофе» gone (a tapped choice was read as a love and became the owner's friend's topic); the pet question asks about a pet («Нет», not «Никого»). Interviewer: 2 questions about what they love, 3 about their people — each about the LAST time, and the confidant asked apart from who is around (Weiss: two lonelinesses) — and one REQUIRED closing question, «А о чём бы поговорить, да не с кем?». Grief no longer ends it. MAX_TURNS 18→16. Fixed on the way: the person's own age was being passed as the friend's age as law; their name never reached the friend; a crisis reply at the end of the intake was never shown (iOS). Simulated: a 15-year-old's closing answer «что мне 15, а я только с кодом общаюсь, и что нравится одна»; a widow's «о муже… страшно одной ночью» | council + owner, 2026-09-24 (`tests/test_interview.py`) |
| **The reader decides WHAT somebody needs; the writer decides WHO gives it.** The request is honoured literally and never overruled — it decides what he is like; the need decides what he is for. Stated ideals do not predict whom people actually warm to (Eastwick & Finkel 2008), but a visibly overridden request provokes reactance, so neither is traded for the other. The first reading is a hypothesis; the conversations correct it (re-reads, confirmed observations). **How the reader gets it right**, by Funder's Realistic Accuracy Model — the cue must exist, reach the reader, be noticed and be used right: the interview now asks the one closing question whose answer says what is missing («о чём тебе не с кем поговорить»); the reader is walked through perspective-taking, direct words over form, competing hypotheses and a Barnum check, in its thinking. Tested on the owner: without that answer every model correctly declined to guess «feelings»; with it, Opus 5.5 wrote «нет никого, с кем можно всерьёз, особенно о чувствах» | owner's question, 2026-09-23 |
| **The rules stay a file you can read, plus mechanisms in code. No fine-tuning.** Four reasons, in order of weight: a fine-tune trained on our own prompt's output can at best COPY it and never exceed it; Anthropic has no fine-tuning API, so it means leaving Claude for a small model that writes worse Russian; catastrophic forgetting is documented and shows up where you did not test; and weights cannot be read, diffed, or fixed by one line with a test | settled 2026-09-22 |
| **The constitution gets CUT, from 26,348 chars to ~8,000.** This is the whole answer to the 94/6 problem. Fine-tuning would have removed the last ~3,000 tokens for a month of work and no way back | **done 2026-09-23: 10,385 chars**, ~6,000 tokens off every request (estimate). Awaiting the owner's ear (§13.1) |
| **Claude is out of the candidate list for the VOICE.** Owner's call on cost, and the observation is real. One caveat recorded in `tryout.py`: the audition runs uncached, so it charged ~4× what the app would. Still the dearest of the five | owner's call 2026-09-23 |
| **The model is chosen BY EAR, on the real prompt.** A 50-phrase scored set was proposed and the owner replaced it with listening himself — correctly: no published benchmark measures warm ordinary Russian said to a lonely person, and the ear is the instrument that does | owner's call (`tryout.py`) |
| One background agent at a time — credits are limited | working constraint |

On the last "left to the base model" row there is one honest caveat recorded in
`BOUNDARIES.md`: the prompt had disabled *both halves* of declining (the refusal
shape and the usual refusal content), so the mitigation is that declining is now
explicitly permitted again — not that a rule was added.

---

## 5. The principles everything is written by

These are not style preferences. They have each been earned by a bug.

1. **«Всякое правило, которое можно заменить механизмом, надо заменить
   механизмом.»** A rule asks the model to count across a history it cannot
   see. A mechanism counts it and hands over the conclusion.
2. **Норма, а не потолок.** Never caps; always a norm with a stated break
   condition. A ceiling gets obeyed in the case it was never written for.
3. **Recipe book vs teaching to cook.** Do not enumerate cases; teach how to
   think. **The tag is the CONCLUSION, not the signal.**
4. **A direct request is not an inference.** A request takes effect at one
   occurrence; an inference needs two (`mood.CONFIRMED_AT = 2`).
5. **Ecological fallacy.** Twenty-five exchanges in one conversation are ONE
   occasion sampled twenty-five times, not twenty-five observations. The unit
   of observation is the **visit**.
6. **Limits from his own variability**, not from a specification — individual
   control charts, no per-user tuning. `IQR/2`, never MAD (MAD collapses to
   zero on bimodal data, which is exactly "бодр днём, тих вечером").
7. **Put an exception next to the rule it excepts**, never in a distant section.
   The model reads them together and they cannot fight.
8. **Caching is a contract.** The stable half must be byte-identical turn to
   turn. Anything user-varying in it silently costs money on every turn.
9. **A boundary is only real if something enforces it.** Most of ours are words
   in a prompt. `BOUNDARIES.md` marks which ones are actually held up by code.

---

## 6. Architecture — nine parts

### On the critical path (the person is waiting)

| | Part | Model | Notes |
|---|---|---|---|
| ① | **Ears** — speech to text | `whisper-1` | **stale**; Deepgram Nova-3 Flux recommended, needs a key |
| ② | **Watchman** — danger in the person's words | Haiku 4.5 | runs as a task; **does not hold up the answer** |
| ③ | **Voice** — the companion speaking | Haiku 4.5 | 0.82 s to first token — best in the field |
| ④ | **Mouth** — text to speech | Fish Audio | #1 on TTS-Arena2; `s1` configured, `s2-pro` is newer |

**The watchman never blocks.** It used to be awaited before the prompt could be
assembled, so every person who was fine paid for it in silence. Now the reply
races it: on `danger` it **interrupts mid-sentence** with words written down in
advance (`safety.spoken_alert`), and anything found too late to interrupt rides
the next turn's prompt exactly once (`safety.carried` → `safety.mark_told`).

The alert words are written, not generated, for three reasons: they cost no
second at the moment a second is the point; they cannot fail into «я всего лишь
ИИ, я не могу вызвать скорую» on the one turn where the character is not in the
prompt; and they can be *read* — what a person in trouble will hear is a string
in a file somebody can check.

There are **two** of them, because there are two emergencies: `kind: "body"`
(ambulance, fetch whoever is nearby) and `kind: "self"` (he stays, he asks
whether they are alone, he does not close it — fetching the family is the
standard contraindication when the family is the cause).

**And the phone is told, not only the speaker.** A `danger` verdict now also
streams `{"kind": "alarm", "alarm": {"danger": …, "numbers": […]}}` — this
person's own country's number, ready to dial — and the app puts it under a
button that goes nowhere on a timer. Hearing a number, holding it, leaving the
app and typing it correctly is a great deal to ask of somebody on the floor.

### In the background (nobody is waiting)

| | Part | Model | Cadence |
|---|---|---|---|
| ⑤ | **Scribe** — extracts facts, mood, follow-ups | Sonnet 5 | every **5 exchanges** or **300 s**, whichever first; a goodbye always closes the batch |
| ⑥ | **Reader** — reads the person deeply | Opus 5 | every visit to visit 5, every 3rd to 16, every 10th after — **plus out of turn when 3 new behaviours are confirmed** |
| ⑦ | **Biographer** — his week, and deepening his character | Sonnet 5 / Opus 5 | `life.maybe_begin` per day, `persona.deepen` every 60 turns |

The scribe's batch has **two** bounds and the second is not cosmetic: each run
writes one mood reading, and `mood._visits` cuts readings into visits wherever
two fall more than `CONVERSATION_GAP` (10 min) apart. A slow talker whose five
exchanges spanned eleven minutes would have one visit counted as two, and the
visit is the unit the entire baseline rests on.

The reader's schedule is a **ceiling, not the decision**. A man steady for six
months who changes in a week would otherwise wait out ten visits while the
companion holds a description of who he used to be.

### Once, at creation

| | Part | Model | Notes |
|---|---|---|---|
| ⑧ | **Interviewer** — the intake conversation | Sonnet 5 | natural, unguarded language for the reading |
| ⑨ | **Matchmaker** — invents the companion | Opus 5 | ten sketches (effort `low`) → **dice** choose → deep write (effort `high`) |

**The dice choose, never the model.** Asked to choose, it picks its safe
favourite and the mode is back. The ten-sketch stage exists solely to defeat
mode collapse — ask a model to invent a person and it returns the same warm old
man by the sea every time. That stage used to run on Haiku, which is the model
with least breadth; it is on Opus 5 at low effort now.

### How a companion is born (the signup flow, once per person)

1. **Intake** — a short spoken conversation, `intake.py`. Its job is NOT to
   collect a form: it is to get the person talking in **natural, unguarded
   language**, because that is what the reading needs. It stops itself when it
   has enough (`enough: true`) rather than filling a quota.
   The app's local warm-up is eleven questions; the fourth, «А живёте где — в
   какой стране?», is asked outright and its answer is sent separately, because
   it decides which emergency number he is told to dial and the first
   conversation is exactly when nothing else is known yet.
2. **Reading** — `reading.py`, Opus 5 with real thinking. Infers HOW this
   person needs to be spoken to from *how they wrote*, not just what they
   wrote. Everything downstream is built on this.
3. **Ten sketches** → **dice** → **deep write** — `matchmaker.py`.
4. The result is saved as this person's `persona` JSON and never merged with
   the template. (It used to be, and every companion came out part-template —
   the same cat, the same café.)

### Two out-of-band markers

The model writes these on their own line; they are stripped before a single
syllable is spoken and before anything is remembered.

- **`//КОНЕЦ//`** — "they are saying goodbye, stop listening". Deliberately not
  a keyword list: matching «пока» fires on «пока не знаю» and misses every real
  goodbye without the word. Judging whether somebody is leaving is what a model
  is good at and a regex is hopeless at.
- **`//КАШЕЛЬ//`, `//КХМ//`, `//ЗЕВОК//`, `//ЧИХ//`** — his body. `body.py`
  gives him the *fact* («в горле першит»); whether that becomes a cough, and
  where, is his — a sentence somebody is halfway through telling you about
  their dead wife is never the place.

---

## 7. Latency and cost — measured, with stated assumptions

A conversation is taken as 25 exchanges, ~6 minutes of speech, ~200-character
replies, the ~11,800-token prompt cached.

| | Was | Now |
|---|---|---|
| Time to first sound | ~2.5 s | **~1.9 s** |
| Per conversation | $0.481 | **$0.351** |
| Per person per month (one conversation a day) | $14.43 | **$10.53** |

Three things worth knowing:

1. The biggest line was **the scribe at $0.175** — 35% of a conversation —
   because it ran on every single exchange. Batching cut it to $0.045.
2. **Voice + hearing are 68% of what remains.** The language models are the
   minority. Optimising the brain before measuring the audio is wasted effort.
3. **Russian voice costs twice what English does.** Fish bills per UTF-8
   *byte*, and Cyrillic is two bytes per letter: the same conversation is
   $0.29 in Russian and $0.21 in English.

---

## 7a. What the cache is really doing — and the one thing to check first

The stable head of the prompt is **~10,600 tokens** and it is the most
expensive thing the app sends. It is *supposed* to be nearly free: a cache
READ costs a tenth of an input token, a cache WRITE costs a quarter more than
one. **Twelve and a half times lies between those two.**

Whether we are on the right side of it was never measured. Now it is:
`brain._note_cache` prints one line — and only when the head was rewritten,
so a healthy turn is silent and a real signal cannot get lost in noise.

**There is a named suspect, and it needs checking on the first real
conversation.** The cached head contains `mood.standing_block`, which reads the
`observations` table ordered by `last_ts`. The scribe writes that table from a
background task **every five exchanges** (`learn.BATCH_EXCHANGES`). So a
confirmed observation landing mid-conversation reorders those lines, changes
the bytes, and silently turns the next turn's cheap read into a full write. Up
to four extra writes in a twenty-five-turn conversation — more than half the
brain's bill.

If the log shows it happening, the fix is small and arguably more correct
anyway: **snapshot the stable half when a conversation begins and hold it until
the conversation ends.** A friend does not reconfigure his understanding of you
between two sentences.

**A thing that looked easy and is not: caching the conversation history.**
It cannot work as the code stands, and the reason is worth knowing before
somebody tries again. Render order is `tools → system → messages`. Our `system`
is `[stable, variable]`, and the variable half changes **every single turn** —
`memory.build_memory_context` takes the person's current words, and it also
rolls a die (`RESURFACE_CHANCE`). Everything after a changed byte is a miss,
so a breakpoint on `messages` would pay the write premium and never once read.
The workarounds all cost more than the ~$0.60/person/month they would save,
and one of them (moving the variable block into the last user turn) would drag
stale mood and occasion through the whole history.

## 7b. Choosing the voice — the tool, and why it is shaped this way

`backend/tryout.py` talks to the same friend on five different brains so the
owner can pick by ear. `backend/audition.py` does the same for voices; this is
its twin for brains, and the reasoning is the same: a provider's own samples
are good enough to reject a candidate and not good enough to choose one.

Run it: `python tryout.py --talk`. Setup is one command per platform —
`setup.sh` (macOS/Linux), `setup.ps1` (Windows).

Six decisions are baked into it, each earned:

- **One key, not five.** Everything goes through OpenRouter, so a sixth
  candidate is one line in `CANDIDATES` rather than another SDK and another
  billing page.
- **The real prompt.** Every model gets exactly what `companion
  .build_system_parts` assembles — 28,370 characters. A model judged on a toy
  prompt was judged in somebody else's product.
- **The same friend for everyone**, fixed in the file: Фёдор, 68, a retired
  marine engineer in Kaliningrad, an ace on ship diesels, two years into
  rebuilding an «Океан» radio, quietly afraid of becoming a burden to his son.
  He talks to Николай Петрович, who cannot stand pity and whose sore subject is
  being of no use to anyone.
- **The character is printed before the first turn** and written into the
  transcript. Listening for "did he hold the role" without knowing the role is
  not listening.
- **Every line hits disk as it is said**, into `backend/data/tryouts/`, with
  the names in a separate file beside it. The first real run was lost to a
  closed terminal; and keeping the transcript nameless means it can be judged
  again tomorrow.
- **`--talk` is the real test.** One phrase shows prose. Character drift — the
  thing that actually breaks a companion — needs ten turns to appear.

**What it cannot tell you: speed.** OpenRouter's routing is in those seconds.
Real latency gets measured on the winner, at its own provider, in the app.

**The five, with what the app would pay per person per month** (25 exchanges a
day, after the constitution is cut, with caching as the app really does it):

| | $/person/month | Why it is on the list |
|---|---|---|
| MiniMax M2-Her | $0.62 | built for companions; leads persona retention |
| GPT-5.6 Luna | $0.44 | #1 by real roleplay usage on OpenRouter |
| DeepSeek V4 Flash | $0.39 | #2 by real usage |
| Gemini 3.5 Flash-Lite | ~$0.6 (estimate) | fastest and cheapest; per-request safety thresholds. The file had `gemini-3-flash-preview` — not Lite, and a preview; switched 2026-09-23. If it reads flat, `gemini-3.8-flash` is Gemini's best at ~2× |
| Qwen 3.5 | ~$0.4 | 27B; id fixed 2026-09-23 to `qwen/qwen3.5-27b` (there is no `-instruct`) |

Claude Haiku 4.5, the incumbent, was $2.12 and is out (§4). Sonnet 5 at $4.23
is the fallback if all five read flat.

**Two deliberately rejected:** DeepSeek V4 **Pro** — documented positivity
bias, folds when pushed back, which breaks the one rule this product cannot
lose; and self-hosting — GPUs idle at our size.

---

## 8. What each module is for

| File | What it owns |
|---|---|
| `companion.py` | The constitution (`BEHAVIOR_RULES`) and prompt assembly (`build_system_parts`) |
| `persona.py` | WHO he is — a saved JSON document per person; growth, bounded |
| `matchmaker.py` | Inventing him: sketches → dice → deep write |
| `reading.py` | Reading the PERSON — how to speak to them, what never to touch |
| `mood.py` | What has been WATCHED about them: visits, baselines, control limits, confirmed behaviours |
| `fit.py` | How the two of them go together — a property of the pair |
| `memory.py` | Facts, beliefs, follow-ups, shared moments, visits |
| `learn.py` | The scribe: distils conversation into memory |
| `life.py` | His week — an ARC with a day-by-day course, not a state |
| `feeling.py` | His mood, which fades within a day |
| `body.py` | His throat and tiredness; cough/yawn/sneeze markers |
| `safety.py` | The danger watcher — outside the character, deliberately |
| `emergency.py` | Which number to dial, by country; `resolve` reads it out of free text, `dialable` hands it to a button |
| `erase.py` | The ONE definition of what a parting removes — a friend leaving, or a person |
| `situations.py` | Rules that apply only to this turn (games, news) |
| `occasions.py` | What day it is, and whose birthday |
| `allowance.py` | Daily spend per person; dozing |
| `brain.py` | The model calls: `generate_reply`, `stream_reply`, `think`, `generate_text` |
| `main.py` | The turn: assemble → race the watcher → stream → remember |
| `identity.py` | Hash-only user ids from the token — done properly |

### The iOS side

SwiftUI, in `ios/BobCompanion/`. **Type-checks clean** on the owner's Mac
(Xcode present since 2026-09-24): `xcrun --sdk iphonesimulator swiftc -typecheck
-target arm64-apple-ios17.0-simulator $(find ios/BobCompanion -name '*.swift')`
— 31 files, 0 errors. Not yet built or run on a device.

- `Design/Strings.swift` — all copy, RU and EN. `aboutBody` is the disclosure.
- `Screens/SettingsScreen.swift` — «О приложении» opens `AboutSheet`.
- `App/AppFlow.swift` — onboarding → intake → conversation. **No age gate.**
- `BackendClient.swift` — `createCompanion` posts `{about, wishes, country}`,
  so the server's `conversation/age/gender/origin` fields are still dead on the
  real client and `intake.as_story` is bypassed by a separately-maintained
  Swift copy. Worth unifying.
- `Stores.swift` → `startOver()` now calls the server and then clears the
  phone; `deleteEverything()` calls the server FIRST and clears the phone only
  if it worked. `forgetCompanionLocally()` is the phone-only one, used by
  `reconcileWithServer`, which is reacting to a server that has already said
  there is nobody.

---

## 9. Boundaries

**`BOUNDARIES.md` is the reference** — what he may do, may not do, and what is
governed by nothing at all, with the mechanism column saying which are actually
enforced. Read it before touching anything in that area. `AUDIT-2026-09.md` is
the full independent audit with `file:line` evidence behind it.

---

## 10. Must fix before shipping, in order

Items 1–5 and 8 were done on `claude/awesome-planck-wdj4hu`; what is left is
below them. The done ones are kept, struck through, because what was wrong is
the reason the tests that now hold them exist.

1. ~~**The `danger` block was written for a stroke and applied verbatim to
   suicide.**~~ Split by `kind`, and the phone now gets the number under a
   button (`emergency.dialable`, the `alarm` stream line, `CompanionScreen
   .helpNow`). **The crisis-line table is still open** — `emergency.py` maps
   countries to ambulance numbers only, and that needs the owner's decision
   and real numbers. Until it exists, `kind: "self"` says the emergency number
   and, more importantly, that he is staying.
2. ~~**A `danger` verdict notifies nobody.**~~ Partly: it now reaches the
   PERSON as something to press. **Nobody ELSE is notified** — no push, no
   family contact, no escalation. Still open, still question 3 below.
3. **Prompt injection** — three channels put user-derived text into the
   *system* role, one of them (`reading.standing_block`) rewritten unattended
   every few visits. A hostile reading was assembled and landed verbatim.
   **The owner has deferred this deliberately** («поговорим об этом позже»).
4. ~~**`reading.py:457` can silently erase `hurt_by` / `do_not_touch`.**~~
   Fixed. `str([])` is `"[]"` and `str(None)` is `"None"`, so an empty answer
   passed the presence test and replaced «про сына не спрашивать». Emptiness is
   decided on the value now, and those two fields can only be added to
   (`reading.NEVER_SHRINKS`). Both halves are pinned by tests.
   Alongside it, the owner's rule: `do_not_touch` means «never take him there
   yourself», never «never go there». If he opens it, the friend goes with him.
5. ~~**No romantic/sexual ceiling and no de-escalation path.**~~ Closed, and
   the owner reframed it before it was built: the line is **what he IS to
   them**, not what may be discussed. «Я с другом могу говорить о чём угодно.
   И я его люблю — но, конечно, не романтически.» So no topic ban and no
   cooling machinery — `КАКОЙ ТЫ ДРУГ` says he is a friend rather than a
   partner, and the exception sits beside the hook rule: if the PERSON says it
   first, he answers warmly in kind and does not correct them.
6. ~~**No output filter and no age gate.**~~ Two answers, both the owner's.
   **No age gate, ever** — «я не хочу чтоб юзер проходил проверку как в порно
   сайтах, я хочу чтоб приложение чувствовалось свободным»; YouTube is the
   honest precedent, and what Google actually had to fix after the $170M COPPA
   settlement was not the door but **what they kept** (`young.py`). For the
   output, `vow.py` now reads his own words before they are spoken and before
   they are remembered — the two things he must never say. It is not a general
   content filter and is not meant to be; a broader one is still open.
7. **The prompt is Russian-only on the server.** The iOS app offers `ru`/`en`,
   `COMPANION_LANGUAGE` exists — and the constitution opens «Ты говоришь
   по-русски», the extractor demands «Все значения — по-русски». English is not
   supported, whatever the settings screen says.
8. ~~**`CHAT_MODEL` carries a stale dated id.**~~ Fixed, and a test now fails
   the build on any dated `*_MODEL` id: a pinned snapshot keeps answering in
   the voice of the day it was written and then stops answering at all,
   mid-turn, in front of somebody who cannot tell that from their friend
   having gone.
9. ~~**Nothing deletes a person's data, and the app says otherwise.**~~ Fixed.
   `erase.py` is the one definition of what a parting removes, and both ways of
   parting reach it. `DELETE /api/me` erases every row in every table with a
   `user_id` — asked of the schema, not listed — and every file.
   `POST /api/companion/start-over` removes him and everything between them,
   keeping the person. The sheets now say what actually happens.
   **Still open:** there is no retention policy and no expiry, and there is no
   export endpoint (nothing in the app promises one any more — the «Данные ·
   выгрузить» row is gone — but a person is arguably owed it).
10. **The cached head may be rewritten mid-conversation by the scribe.**
    Measured-for, not yet measured — see §7a. Check the `[кэш]` lines on the
    first real conversation before doing anything else about cost; if it is
    happening it is worth more than everything else on this list put together.
11. ~~**The constitution is still 26,348 chars.**~~ Cut to 10,385. How it
    was done, and why it ended above the ~8,000 estimate, is in §11. **Still
    open: the owner's ear** — `python tryout.py --talk` on the new text, with
    the old one in git (`git show 0072dc5:backend/app/companion.py`) to
    compare against.
12. **Persona growth rides in the cached half.** Bounded now (`persona._MOST`),
    but it is still user-varying content inside the half that must stay
    byte-identical — worth re-checking after any change there, because a silent
    cache miss costs money on every turn of every conversation.

## 11. Deliberately NOT done, and why

- **A two-stage watchman** (cheap high-recall filter → strong verifier). It
  would cut cost and improve indirect detection, and the literature recommends
  exactly that shape. **Not built**, because gating suicide detection behind a
  recall filter with no labelled evaluation set is reckless. Build the set
  first.
- **A separate "character" module.** Considered and rejected: the five
  mechanisms that make him (persona, life, feeling, body, his own facts) have
  genuinely different clocks, and a module that only concatenates is ceremony.
  The real defect — his pieces arriving interleaved with the person's — was
  fixed by ordering instead. The hypothesis that would have justified the
  module ("his body doesn't know about his week") was **checked and found
  false**: `life.block` already emits «Как это слышно: гнусавит, шмыгает».
- **Model swaps** (Deepgram for ears, Mistral Large for the reader, GPT-5.6
  Luna for the voice). All need vendor keys and measurement. Untested vendor
  code is worse than none.
- ~~**Cutting the constitution.**~~ **Done** 2026-09-23 (§4). What changed the answer was working out where the win actually
  is: 12,500 tokens per request today, ~5,500 after the cut, ~2,400 if the
  rules were baked into weights. **The first step is bigger than the second**,
  takes days rather than months, and is reversible. What survives the cut is
  the third of the constitution the base model would not do on its own —
  warmth is earned not issued, return him to living people, don't invoice him
  for being away, where accommodation stops, notice when something changed,
  if he is being defrauded. What goes is the two-thirds that is either ordinary
  kindness every model already has, or has since become code (`vow.py`,
  `young.py`, `erase.py`).
  **How it was actually done**, so the next edit follows the same rules: a
  draft, then three independent reviews (the character's soul, whether a
  cheap non-Claude model will follow it, the boundaries), each finding
  checked against the code before it was taken or refused. What the research
  settled: compliance falls as instructions are added and omission is how it
  fails, fastest on small models (IFScale, arXiv 2507.11538); the top of a
  prompt is followed best, so the spoken-output rule is now its second
  sentence; a reason beats capitals; and **a quoted sample line is repeated
  verbatim** — so the constitution now describes acts instead of quoting
  lines, or every companion comes out saying «сижу, чай пью». It ended at
  10,385 rather than ~8,000 because the reviews put back ~2,000 characters
  that each showed a cheap model breaking without — «не вместо ответа, а
  сразу после», «я ждал» by name, «не „я чувствую, что ты расстроен"»,
  gladness when he leaves for people, «его спокойствие важнее». Refused, with
  reasons in the tests: dropping the "never say you are an AI" line because
  `vow.py` catches it (then `vow.py` cuts him off mid-sentence instead), and
  dropping the 87/19/40 portraits (the owner's opening, §1).
- **Fine-tuning the rules into a model.** Researched at length at the owner's
  request, across every provider — and **closed**. The decisive fact is not
  cost: the only training data we could produce is our own prompt's output, so
  a fine-tune can at best *equal* the prompt and never beat it. It buys
  consistency, not quality, and it charges leaving Claude, documented
  forgetting, and rules that can no longer be read or fixed by one line. The
  owner's proposed order — perfect the prompt first, then bake — is exactly
  right, and the first half of it is also the whole win.
- **Sending the prompt less often** — every ~30 or ~100 turns instead of every
  turn. Physically impossible and worth writing down so nobody tries: the model
  is stateless, and OpenAI's stateful Responses API is the proof by
  construction — it lets you send only the new sentence and still **bills the
  whole history every turn**. Bandwidth, not cost. Caching is the real form of
  "send it less often", and we already have it.
- **A 50–100 phrase scored evaluation set.** Proposed twice — as the
  prerequisite for cutting the constitution and for comparing models — and the
  owner replaced it with listening himself. That is the right call for *voice*
  (no benchmark measures warm Russian for a lonely person) and it remains the
  wrong gap for the *watchman*, where §11's first bullet still stands.

---

## 12. How to work here

- **Branch:** `claude/awesome-planck-wdj4hu`. Push with
  `git push -u origin <branch>`, retry network failures with backoff
  (2s/4s/8s/16s). **Never open a PR unless explicitly asked.**
- **Keys live only in `backend/.env`** (gitignored). Never paste one into a
  message, never commit one.
- **Never put a model identifier** in a commit message, PR body, code comment
  or any repo artifact. Chat replies only.
- **Commit attribution** (exactly these two lines at the end of every commit):
  ```
  Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_018PiV38FZMupJ19foghBRZm
  ```
- **Tests:** `cd backend && python -m pytest -q`. **951 pass.** The suite is the
  design record — test docstrings carry the *reasoning*, including what went
  wrong before. Read the docstring before changing an assertion; several tests
  exist because a previous fix was subtly wrong.
  `pip install -r requirements.txt -r requirements-dev.txt` first — the suite
  needs `pytest-asyncio`, which was missing from requirements-dev.txt and made
  63 tests look like failures rather than like a missing plugin.
- **The constitution has a ceiling** (`test_the_constitution_stays_within_its_ceiling`
  in `test_situations.py` — not in `test_companion.py`, which costs everyone a
  minute). **10,500 chars, currently 10,486** — lowered from 26,400 by the cut
  (§11). It has caught real regrowth more than once. If you need room, pay for
  it by consolidation, not by raising it.
- **A failing test is not a flake until you have found the reason.** Two tests
  in `test_body.py` compared decayed values at `rel=1e-6` while `body.state`
  fades by real wall-clock time with a 45-minute half-life. The arithmetic:
  they break if more than **four milliseconds** pass between two reads, and a
  sqlite write sits between them. They were passing because the disk was fast,
  not because the code was right, and the full suite eventually caught one out.
  Both now stop the clock. Look for this shape anywhere a test asserts on a
  value that decays.
- **Three tools, all meant to be run by a person with ears**, not by CI:
  `audition.py` (voices, side by side), `tryout.py` (brains, §7b), and
  `myself.py` — every agent tested on the owner himself, stage by stage in the
  order a person meets them (interview → reading → sketches → writer → voice →
  scribe), because he cannot judge what a 68-year-old should hear and can judge
  everything about himself. Shortlists and why: `docs/MODELS-FOR-EACH-AGENT.md`.
  It writes no prompt of its own — it swaps only the model behind
  `brain.think` / `brain.generate_text`, so it cannot drift from the app. All
  three keep their output on disk so a judgement can be revisited a day later
  rather than trusted to memory of the third one.
- **Setup is one command per platform:** `setup.sh` (macOS/Linux), `setup.ps1`
  (Windows). Both refuse to run if a real key is sitting in `.env.example` —
  that file is deliberately NOT hidden from git (`!.env.example` in
  `.gitignore`), so a key there goes to GitHub. The owner put one there on the
  first try, which is why the check exists rather than the rule.
  `setup.ps1` **must stay UTF-8 with BOM** (`.gitattributes` pins it): Windows
  PowerShell 5.1 reads a BOM-less .ps1 in the system codepage, the mangled
  bytes land inside quotes, and the file stops parsing altogether — with errors
  that point at brackets rather than at the encoding.
- **For the tryout tool only `httpx` and `python-dotenv` are needed** — not
  `anthropic`, not `openai`. It matters: those two need compiled extensions and
  will not install on a phone or any machine without a compiler. The heavy
  imports in `persona.py` live inside a function on purpose. Do not lift them
  to the top "for tidiness".
- **Swift type-checks** (command in §8) — run it after any Swift edit. Not yet
  built into an app or run on a device.

---

## 13. Open questions for the owner

1. ~~**The 94% / 5.5% ratio.**~~ Answered: **cut the constitution** (§4, §11)
   — and cut. What is left is the question only the owner can answer: **did
   the cut cool him?** By ear, old text against new, as with the voice.
2. **Crisis lines.** Real numbers per country for `kind: "self"`, or a single
   international one?
3. **Who ELSE gets notified on `danger`**, and how? The person now gets the
   number under a button. A family contact, a push, any escalation beyond the
   person themselves — none of it is built, and it needs a product decision
   before it is.
4. **English.** Is it a real target? If yes, the prompts need to be
   language-parameterised, which is a substantial piece of work.
5. **Speech-to-speech** (GPT Realtime ~0.82 s, Grok Voice ~0.78 s) would be
   faster and more expressive than the current STT→LLM→TTS pipeline, but cannot
   carry a 125-rule constitution and locks the product to one vendor. Worth a
   separate conversation; not mixed into model choice. **Note that cutting the
   constitution to ~10,400 chars changes this arithmetic** — it may be worth
   re-asking afterwards rather than now.
6. **Where the real money is.** The owner keeps optimising the brain, and the
   brain is the minority: **voice and hearing are 68% of the bill**, and Russian
   speech costs twice what English does because Fish bills per UTF-8 byte and
   Cyrillic is two bytes a letter. One change of TTS vendor is worth more than
   everything in §7a and §7b combined. Not started, not decided.
7. **The scribe, the reader and the matchmaker are still on Claude.** They run
   rarely — once a conversation, once in a friend's life — so they are a small
   part of the bill, and there quality of writing decides rather than price per
   turn. Left alone deliberately until the voice is chosen.

---

## 14. How the owner and the assistant work together

Written down because it was learned over a long session and re-deriving it
costs both sides time.

**The owner writes in Russian and asks for short, plain words.** Take it
literally. A correct answer that is three screens long has failed — he has said
so more than once, and once said outright «я ничего не понял». Lead with the
decision, then the reason, then at most one table. Long research belongs in a
file, not in a reply.

**He decides; the assistant states the concern once and then does the work in
full.** This has happened repeatedly and the pattern is settled: age
verification (he refused a gate, and the law agreed with him), memory as a
pop-up (he wanted a Settings switch, and he was right — a question nobody asked
for is a checkpoint in friendlier clothes), the 50-phrase evaluation set (he
replaced it with his own ear, correctly), Claude's cost. When he repeats
himself, that is the decision. Say the caveat in a sentence, put it in the
code's comments where it will survive, and build the thing he asked for.

**He catches real mistakes.** «Ты опять заточил вопрос под свои модели» was
fair — the research had been narrowed to one vendor. «Ты ещё говорил что
дипсик шикарный по характеру» was fair too: a candidate had been dropped from
a shortlist without saying why. Check his objections properly rather than
conceding politely; twice they turned up something worth finding.

**Say plainly when you were wrong, once, and move on.** Several times this
session the assistant was wrong in ways that cost the owner real time — a
"3 lines, 1 hour" promise for a cache change that cannot work at all, a key
check that fired on a clean file, a PowerShell script that could not parse on
the only machine it was written for, a model id typed from memory. Each is
recorded in the code near the thing it broke, because the next person to touch
that line needs the reason more than the apology.

**Verify on the machine, not from memory.** Everything in this document that
carries a number was run. The two habits that paid: compute the threshold
rather than guessing (`rel=1e-6` survives four milliseconds), and test the
guard from both sides (the clean file must pass, the planted key must be
caught).

**The reasoning goes in the docstring, not in chat.** This codebase's tests and
module headers carry *why*, including what went wrong before. That is the only
part of a conversation that survives it.
