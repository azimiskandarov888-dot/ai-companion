# HANDOVER — read this first

Everything a new session needs to work on this project without re-deriving it
or re-litigating decisions that are already made. Written 2026-09-17 on branch
`claude/gallant-bardeen-0l6ff0` and revised the same day on
`claude/awesome-planck-wdj4hu`, where must-fix items 1–5 and 8 were done.
**808 tests pass.** Every number below was measured by running the code, not
estimated; where something is an estimate it says so.

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
finding is the reason `ТЫ ВОЗВРАЩАЕШЬ ЕГО К ЖИВЫМ ЛЮДЯМ` exists, and it is the
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

### The number that still hurts

In a real assembled prompt with a fully written character:

| | chars | share |
|---|---|---|
| Universal constitution (identical for everybody) | 25,756 | **94.4%** |
| Him — who he is, his week, his mood, his things | ~1,500 | **5.5%** |

The rules about how to be kind are seventeen times bigger than the person. This
is measured, not estimated. Reducing it means cutting constitution that
currently works, so it should be done by measurement, not by eye. **It is the
biggest open problem in the product.**

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
| **He is an ACE in the one thing the person loves most.** Not «also interested» — a knower who always has something beyond what was asked. Warmth on its own runs out; a subject does not, and it is what gives a conversation a tomorrow. The one place they overlap on purpose — everything else about him stays his own | done (`matchmaker._WRITE_SYSTEM` → `expertise`, carried into every turn by `persona.py`) |
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

SwiftUI, in `ios/BobCompanion/`. Structurally verified only — **no Xcode build
has ever been run in this environment**, so treat any Swift change as unproven.

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
5. **No romantic/sexual ceiling and no de-escalation path**, while several
   rules push warmth only upward and forbid ever cooling.
6. **No output filter and no age gate.** The only server-side content check
   looks at the *person's* words, never at his reply.
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
10. **Persona growth rides in the cached half.** Bounded now (`persona._MOST`),
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
- **Cutting the constitution to fix the 94/5.5 ratio.** Everything left in it
  works; cutting by eye would trade a measured problem for an unmeasured one.

---

## 12. How to work here

- **Branch:** `claude/gallant-bardeen-0l6ff0`. Push with
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
- **Tests:** `cd backend && python -m pytest -q`. 808 pass. The suite is the
  design record — test docstrings carry the *reasoning*, including what went
  wrong before. Read the docstring before changing an assertion; several tests
  exist because a previous fix was subtly wrong.
  `pip install -r requirements.txt -r requirements-dev.txt` first — the suite
  needs `pytest-asyncio`, which was missing from requirements-dev.txt and made
  63 tests look like failures rather than like a missing plugin.
- **The constitution has a ceiling** (`test_the_constitution_stays_within_its_ceiling`,
  26,000 chars, currently 25,756). It has caught real regrowth more than once.
  It has moved exactly once, deliberately, and the reason is recorded in the
  test. If you need room, pay for it by consolidation, not by raising it.
- **Swift is structurally verified only.** No Xcode build has ever been run in
  this environment.

---

## 13. Open questions for the owner

1. **The 94% / 5.5% ratio.** How do we make him a larger share of what the
   model reads? Cutting the constitution, or re-anchoring him closer to
   generation, or both — and measured how?
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
   separate conversation; not mixed into model choice.
