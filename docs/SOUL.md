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

Creation costs two calls: the ten sketches run on the fast model (breadth is
cheap, and someone is watching the arriving screen), the deep write on the
big one.

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

## The fix for 4 — and the wrong turn taken first

**The wrong turn.** The first attempt injected diversity with *premade
lists*: 36 trades, 10 settings, 9 tempers, rolled by dice. It killed the
sameness and it capped the soul — every character was assembled from OUR
options, and the space of possible people was exactly as large as our lists.
The user rejected it in one sentence, and was right:

> *"So has all of that created by the AI, or is just premade options that you
> choose from randomly? … I thought that AI would create a character with the
> tone, everything. Memory, wishes, story, meaning, soul, thoughts on life.
> So every time it would be absolutely different person, unlimited types."*

The lesson is precise: **randomness must come from outside the model, but it
must not carry biography.** The old scaffold did both jobs; only the first
was legitimate.

### The design: read → sparks → ten strangers → blind pick → the deep write

**0 · The reading** (`reading.py`) — the deepest work the app does, and the
stage everything else is built on. Before anyone is invented, the biggest
model reads the person from *how* they wrote. Its own section is below.

**1 · Sparks.** Dice draw four words from a lexicon of ~231 ordinary Russian
nouns — «керосинка», «ипподром», «оттепель», «плацкарт». That is 115 million
distinct strikings, and *not one of them describes a person*. A spark may
surface as a trade, a memory, a habit, or not at all. They exist only to make
imagination start somewhere new instead of setting off down its usual road.
The rule that keeps this honest: **sparks are nouns, never traits.** The
moment a list entry prescribes who someone *is*, we are back to premade
people — there's a test enforcing it.

**2 · Ten strangers, one call.** The model invents ten sketch-people at once,
required to be maximally unlike each other — decades apart, different
regions, trades, tempers, fates, no two sharing a city or a job. This is the
single most important mechanic, and the reason is not obvious: **inside one
reply the model can see its own repetition and steer away from it; across
separate replies it cannot, and returns its favourite every time.** This is
Verbalized Sampling's finding (arXiv 2510.01171) — ask for a distribution,
not a sample — measured at 1.6–2.1× diversity in creative writing.

**3 · Blind pick.** Python chooses one of the ten. Never the model: asked to
choose, it picks its safe favourite and the mode walks straight back in.

**4 · The deep write.** The big model turns that sketch into a whole person
*for this user* — story, inner world, speech manner, people around him,
what's happening this week — with common ground drawn from the user's own
words and at least one honest disagreement. **Fit lives here on purpose:**
stage 2 optimises for difference, stage 4 for belonging. One stage doing both
would trade them off and do neither well.

Everything about the person — every trait, every memory, every opinion — is
authored by the model. The dice never touch biography; they only choose
*where to look* and *which of ten to keep*.

**The order of power is strict:** the user's wishes are law at every stage
(a wish ignored while sketching is a wish that never had a chance), then the
dice, then the model's taste.

**Disagreement is mandatory.** The genesis prompt requires at least one
opinion that — judging from the user's own story — the user will probably
*not* share, plus something he honestly dislikes that the user seems to love.
Gentle, житейское: food, music, habits, how to rest. Never their family,
their health, their griefs. A friend who agrees with everything is furniture.

**Inner world is written and never recited.** `inner_world` records what's on
his mind when nobody's listening. It reaches the system prompt labelled
*«не рассказывай это прямо — просто живи с этим»*: it is there so that what he
does say comes from somewhere.

**Incomplete is rejected, not patched.** If the pen returns a character
missing name / age / home / backstory / personality / speech_style, creation
fails — the holes are never filled from a template again.

---

## «Пока его нет» — the conversation that replaced the blank page

> *"I genuinely don't like it because there is nothing where the client can
> start from. Why are they gonna talk about themselves? What are they gonna
> write? … With a new blank, you just need to write something about you —
> that's strange and not good."*

Correct, and it was the weakest thing in the app. A sheet of parchment saying
«Расскажите о себе» is a **form**, and a form is the one thing this app must
not put in front of a lonely person. Three failures at once:

1. **Nobody knows where to start.** "Tell me about yourself" freezes people,
   and freezes an isolated eighty-year-old hardest of all.
2. **What gets written is a résumé.** «Люблю рыбалку и тишину.» Nothing to
   read there.
3. **It destroys the reading.** A composed paragraph is the single register in
   which none of the psycholinguistic signals survive — no dative impersonals,
   no thickening hedges, no telling absence. The blank page was actively
   sabotaging the most important stage in the app.

Ask the same person *«что видно у вас из окна?»* and they talk for five
minutes, in their own voice, and every signal is right there.

### Who is asking — the trap, and the answer

The obvious build is the one the request described: a blank "interviewer
companion" with no personality. It is a trap twice over.

- **A personality-less interviewer IS an AI questionnaire with a voice** —
  precisely the thing the app's one law forbids.
- **A fake person is worse.** You would tell a stranger your life, and then
  that stranger would evaporate and be replaced by someone else. A small
  betrayal, at the worst possible moment.

So: **questions with no questioner.** No name, no "I", no character, nothing
to meet and lose. Just questions arriving one at a time — and one honest
sentence first:

> «Его ещё нет. Он появится из того, что вы расскажете — поэтому не о анкете
> речь, а о вас.»

That frame is **true**, which is why it works. It turns the tedious part into
the consequential part: you are not filling in a profile, you are the material
he is made of. People answer that very differently from how they answer a form.

### How the questions are built

The **opener is fixed, never generated** — no latency before the first word,
and no chance that the one question deciding whether someone engages comes out
badly. Every opener asks about a *thing*, in the present, within arm's reach
(a test enforces that none of them mentions feelings, life, or the self).
Everything after it is generated from what was actually said.

The rules that matter (`intake.py` → `_ASK_SYSTEM`):

- **Concrete before abstract.** Ask about things; feelings arrive attached.
  «Чем пахло у мамы на кухне?» goes further than «какое у вас было детство?».
- **Never ask about a feeling directly.** That is a therapist, not a friend.
- **Follow what they gave you** — a script produces a survey.
- **One question, short, speakable aloud.**
- **Never praise the answer.** «Как интересно!» is what a bot says.
- **A one-word answer means the next question gets *smaller*, not more
  serious.** They aren't refusing; they're finding it hard to start.
- **Notice absence quietly.** Several answers with no living person in them is
  the most important thing learned so far — ask about someone, gently, without
  pointing at it.

It stops when there's enough to read a person, not at a count. `MAX_TURNS` is
a stop, not a target; `MIN_TURNS` stops it bailing at the door. Unanswered
questions don't count toward the cap — skipping three questions is not three
turns of talking. And it may be ended at any time: three real sentences give
the reading more than the old blank page ever did.

**On the screen: one question, and nothing else.** No transcript above, no
progress bar, no counter — re-reading your own answers isn't the point, and a
counter turns a conversation back into a form.

**Safety:** if real distress appears in an answer, the intake does not ask the
next question as though nothing happened. It responds warmly, points toward
family or a doctor, and ends.

**When it breaks, nobody is stranded.** A failed question ends the
conversation gracefully and builds on whatever was already said; a failure on
the very first question falls back to the fixed opener. Somebody halfway
through telling you about their life must never see an error screen.

---

## The reading — the stage the rest exists to serve

> *"Understanding the text alone is not enough. What the client says and what
> the client meant to say using specific words is absolutely different. …
> I mean it not just that the client likes fish and the companion also likes
> seafood. It is much deeper — it is human psychology."*

That is correct, and it is not a matter of opinion — it is a field. The
finding that has held since Pennebaker's work on function words is that the
small words people *don't* choose deliberately — pronouns, particles, hedges,
tense, voice — carry more about their state than the nouns they do choose.
**You cannot perform your way out of your own grammar.** Someone determined to
sound fine will still write like someone who isn't.

### Why it is its own call, on its own model

Reading a person and inventing a person are different jobs. Asked to do both
at once, a model spends its attention on the invention; the reading collapses
to a list of hobbies and the character gets built on the list. So the reading
runs **first, alone**, on `READING_MODEL` (Opus) with adaptive thinking at
high effort — the one place in the app where minutes and cents are worth it,
because it happens once per person and everything downstream is built on its
output. Conversation still runs on the fast model; nothing about a turn slows
down.

### What it actually reads

Russian carries a layer English doesn't, and the prompt is built on it:

- **Dative impersonals** — «мне грустно», «мне не спится», «мне хочется». The
  person sits in the *dative case*: life happens **to** them. Someone who
  writes about themselves only this way is, grammatically, not the subject of
  their own life — and it shows before they'd ever say it.
- **Verb aspect** — perfective («поехал», «построил») means life has events and
  a plot; imperfective («жил», «работал») means an unbounded state. A story
  told entirely in the imperfective isn't a story, it's a condition.
- **Retreat into the impersonal** — «живёшь себе», «так у всех». Speaking about
  yourself in the second or general person to avoid speaking about yourself.
- **Where the hedges thicken** — «просто», «наверное», «как-то». Their density
  rises as the text nears what hurts. The *location* is the signal.
- **Concreteness** — naming the tram, the balcony, the smell of bread, a person
  by name. Concrete detail is where someone actually lives; pure abstraction
  («жизнь», «счастье») is talking about yourself from a distance.
- **Tense, and whether a future appears at all.** Its absence is louder than
  anything said.
- **What is missing.** The strongest signal. A whole page and not one living
  person named. Absence is a fact, not a gap.

### The output, and why it has that shape

The reading answers one question: **what presence would not be a burden to
this person?** The schema forces a different piece of work per field —
`register`, `carrying`, `longing`, `absent`, `would_ring_false`,
`would_reach_them`, `needs_pushback_on`, `do_not_touch`, and
`common_ground_seeds`. Two constraints keep it honest:

- **Every indirect claim must carry an exact quote** from their text. No quote,
  no claim — a guess without evidence is worse than no guess.
- **No clinical language, ever.** No "depression", no "trauma", no disorder
  names. This is not medicine and it is never a diagnosis. It is a hypothesis
  about a person, held lightly, used only to choose them a friend.

It also names the **gap between what they asked for and what they seem to
need** — the person requesting "someone cheerful and positive" is often
exhausted by having to be cheerful. The request still wins; the gap is just
made visible to the pen.

### Where it goes, and where it must never go

The reading is **internal, like the distilled memory** — never shown, never
quoted back, never used to persuade. Two slices leave it:

- **To the pen, at creation** (`as_brief`) — judgement only. The evidence
  quotes are deliberately withheld: handed someone's own sentences, a model
  writes a character who echoes them back, which is the most alarming thing
  this app could do — a stranger repeating your words to you on the first
  evening.
- **To every turn** (`standing_block`) — three fields only: how to speak to
  them, what would ring false, and what must never be teased or argued with.
  These govern behaviour that has to hold on *every* turn, and one careless
  turn is what a person remembers. It rides in the **cached half** of the
  system prompt, so after the first turn it is very nearly free.

It is saved to `data/reading.json` and **outlives any one companion** —
«Начать заново» gives you a new friend, not a new self.

**If it fails, a friend still walks in.** A character built on the story alone
is worse than one built on the reading, and far better than an error screen.
The failure prints loudly in the terminal rather than vanishing.

### "How can we really train it?"

Asked directly, so answered directly: **you don't fine-tune this, and
fine-tuning would make it worse.**

- Fine-tuning needs hundreds to thousands of examples of *correct output*. We
  have none. Generating them with the model teaches it to imitate itself — it
  cannot become more perceptive by studying its own guesses.
- Fine-tuning is for **style and format consistency**, not for making a model
  reason better. It *narrows* a model toward a distribution. Depth of insight
  is the one thing it does not buy.
- What genuinely deepens a reading is four things, and all four are already in
  place: **the biggest model** (`READING_MODEL`), **real thinking time**
  (adaptive thinking at high effort), **a prompt encoding actual method**
  (the psycholinguistics above, not "be insightful"), and **an output shape
  that forces evidence** for every claim.

There *is* a real training path, and it is human, not automatic: once real
people have used it, read what the model wrote about them, mark what it got
wrong or reached too far on, and sharpen the method — the marker list, the
schema, the evidence rule. That is an eval set built from reality, and it is
worth far more than fine-tuning would be. It requires the test month first.

### Why not simply turn the temperature up

The obvious knob, and it doesn't work. Temperature perturbs *word choice*,
not *concept selection*: a hot sample gives the same old man by the sea
described in odder words, and past ~1.0 prose degrades before variety
arrives. Mode collapse lives in the shape of the distribution — a bias toward
familiar text baked in during alignment training — so the fix has to change
what is *asked*, not how the tokens are drawn.

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
