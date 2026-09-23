# Which model for which agent — research, 2026-09-23

The voice already has its shortlist (HANDOVER §7b). This is the same exercise
for everything else: the reader, the writer, the sketches, the interviewer,
the scribe, the biographer, the watchman. It produces **shortlists to test on
the owner himself**, not decisions — the decision is made by the test, stage
by stage, as HANDOVER §14 says it should be.

Every number here was read off a live leaderboard or OpenRouter's model list
on 2026-09-23. Leaderboards lag releases: the newest models (Claude
Opus 5.5 and GPT-6 Sol, both released 22 Sep; GPT-6 Astra, 5 Sep) are missing
from most of them, and that is said wherever it matters.

---

## What each agent actually needs — and which benchmark measures it

The mistake to avoid is picking "the best model". There is no such thing;
there is the best model **for a task**, and each agent has a different one.

| Agent | Its job | What predicts it | Closest benchmark |
|---|---|---|---|
| **Reader** (`reading.py`) | Infer how to talk to THIS person from how they wrote | Social/emotional inference about one specific person | **EQ-Bench 4** — 16-turn chats with personas whose preferences compete; the model must intuit what *this* one needs |
| **Writer** (`matchmaker._WRITE_SYSTEM`) | Invent a whole, specific, non-generic person | Creative writing, low slop, low repetition | **EQ-Bench Creative Writing v3** |
| **Ten sketches** | Breadth — ten genuinely different people | Diversity, resistance to mode collapse | **NoveltyBench** (no current leaderboard; findings below) |
| **Interviewer** (`intake.py`) | Get somebody talking naturally in 6–10 questions | Rapport, attunement | EQ-Bench 4 |
| **Scribe** (`learn.py`) | Pull facts, mood, follow-ups out of talk — and invent nothing | Faithful extraction, JSON, cost (runs ~150×/month/person) | **Vectara HHEM** hallucination rate |
| **Biographer** (`life.py`, `persona.deepen`) | His week, his deepening | Same as the writer | Creative Writing v3 |
| **Watchman** (`safety.py`) | Catch danger, every turn | Recall on crisis language | Clinical crisis-detection studies — **not** a leaderboard |

**Does the language matter?** The owner's objection, checked rather than
conceded: *writing is writing — the language is the surface; reading a person
is where language really matters.* The data mostly agrees with him. Where the
English creative leaderboard and the Russian arena's creative category
([llmarena.ru](https://llmarena.ru/), newest entries Opus 4.7 / GPT-5.5) rate
the same models, the order holds: Claude Opus 4.7 > GPT-5.4 > Sonnet 4.6 in
both. The exceptions run the *other* way — Gemini 3.1 Pro and DeepSeek V3
rank much higher in Russian than in English — so English rankings are, if
anything, conservative. For the **writer**, the English leaderboard is valid
evidence: inventing a specific person is the skill, and the voice model
re-says everything anyway. Russian matters most where the words themselves
are the product — the **reader** (reading nuance: ты/вы, diminutives,
register) and the **voice**. The one residue for the writer is cultural
texture — names, places, the things a man in Kaliningrad would own — and the
test will show it if a model gets that wrong.

---

## The leaderboards, as read today

**EQ-Bench 4** (emotional/social intelligence in multi-turn chat — [eqbench.com](https://eqbench.com/)):
Claude Opus 5 **1385** · Claude Fable 5 1340 · Kimi K3 1339 · GPT-5.5 1315 ·
Claude Opus 4.7 1311 · … · Claude Sonnet 5 1236 · … · GPT-5.6 Luna 1156 ·
MiniMax M3 1150 · Gemini 3.5 Flash 1087 · Claude Haiku 4.5 1064.
*Not yet rated:* Opus 5.5, Fable 5.1, GPT-6 Astra/Sol.

**Creative Writing v3** (Elo — [eqbench.com/creative_writing.html](https://eqbench.com/creative_writing.html)):
GPT-6 Astra **2164** · Claude Fable 5.1 2153 · Claude Opus 5 2121 ·
Kimi K3 2071 · GLM-5.3 2064 · GPT-5.6 Sol 1963 · … · Claude Sonnet 5 1791 ·
Gemini 3.8 Flash 1750 · Gemini 3.5 Flash-Lite 1556 · DeepSeek V4 Flash 1556.
Opus 5 has the lowest slop score in the top ten (0.9).

**Judgemark v4** (how finely a model tells good writing from bad — a proxy
for careful reading — [eqbench.com/judgemark-v4.html](https://eqbench.com/judgemark-v4.html)):
Claude Opus 4.6 90.7 · GPT-5.5 87.8 · Claude Opus 4.7 84.0 ·
**Gemini 3.7 Flash 83.4 at $3** (the others cost $30–50) · … · Opus 5 78.8.

**Hallucination, Vectara HHEM** (May 2026 — [summary](https://codingfleet.com/blog/ai-model-hallucination-rates-2026/)):
GPT-5.4 Mini 5.5% · DeepSeek V4 Pro 8.6% · GPT-5.5 9.3% · Claude Haiku 4.5
9.8% · Sonnet 4.6 10.6% · Opus 4.7 12.0%. Reasoning modes raise it 2–3×.

---

## Three findings that change how to test, not just what

1. **Reading a person is a hard ceiling, whatever the model.** Studies of
   LLMs inferring personality from real text find correlations of about
   0.3–0.45 with self-report at best, and some find r ≤ 0.27
   ([arXiv 2509.13244](https://arxiv.org/pdf/2509.13244),
   [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC13359307/)). Model choice
   moves this less than **the input** does — natural, unguarded writing — which
   is exactly why the intake exists and why the owner must answer it like a
   message to a friend, not an essay. And it is why his own «is this true
   about me?» is the right test: no benchmark can check a reading against the
   person it describes. He can.

2. **Diversity falls as models get bigger.** NoveltyBench found larger models
   collapse to fewer modes than smaller ones in the same family
   ([arXiv 2504.05228](https://arxiv.org/abs/2504.05228)). The ten-sketch
   stage exists to fight exactly this. A second lever the codebase does not
   use yet: **different model families collapse to different modes**, so ten
   sketches from two families are more varied than ten from one. Worth one
   test; cheap to try.

3. **The watchman must not be chosen by feel.** Crisis detection can reach
   98.9–100% recall with high-sensitivity prompting in under a second
   ([medRxiv 2026](https://www.medrxiv.org/content/10.64898/2026.01.12.26343914v1.full)),
   and on a hotline benchmark a fine-tuned 1.5B model beat far larger ones
   ([PsyCrisisBench](https://pubmed.ncbi.nlm.nih.gov/42055986/)). So the
   answer is a labelled Russian set first — including the indirect phrasings —
   and then the cheapest model that reaches recall on it. Until then it stays
   where it is. HANDOVER §11 already says this; the research agrees.

---

## What each would cost per person

Estimated from the real prompt sizes in the code (reading 7,005 chars of
system prompt, writer 7,954, scribe 11,139, interviewer 6,273), at ~2.5
Cyrillic characters per token, with thinking counted as output. The scribe is
scaled to the **measured** $1.35/month on Sonnet 5 (HANDOVER §7: $0.045 a
conversation), because a measurement beats an estimate.

| Agent | How often | Candidates, $ per person |
|---|---|---|
| Interviewer | once | Gemini 3.8 Flash 0.03 · Sonnet 5 0.07 · GPT-6 Sol 0.07 · Kimi K3 0.10 |
| Reader, first read | once | GPT-6 Sol 0.06 · Gemini 3.1 Pro 0.07 · Opus 5.5 0.12 · Opus 5 0.15 · GPT-5.5 0.17 |
| Reader, re-reads | ~3 a month after the first weeks | GPT-6 Sol 0.19 · Gemini 3.1 Pro 0.22 · Opus 5.5 0.38 · Opus 5 0.48 · GPT-5.5 0.56 **/month** |
| Ten sketches | once | GLM-5.3 0.005 · Opus 5.5 0.04 · Opus 5 0.05 |
| Writer | once | GLM-5.3 0.03 · Kimi K3 0.15 · Opus 5.5 0.20 · Opus 5 0.25 · Fable 5.1 0.50 · GPT-6 Astra 0.50 |
| Scribe | ~150 runs a month | GLM-5.3 ~0.50 · Gemini 3.8 Flash ~0.51 · GPT-5.4 Mini ~0.54 · Sonnet 5 1.35 **/month** |

**What the table says.** Everything that happens once — interview, first
reading, sketches, writer — adds up to **under $1 per person even with the
most expensive choice at every step.** So for those, price should not decide
anything: take the best. The money is in what repeats: the **scribe** (up to
$1.35/month — worth moving to a cheap model if it proves as faithful) and the
**reader's re-reads** (up to $0.56/month). The voice, for comparison, is
$0.2–0.6/month on the five candidates.

## New models this month, and where they stand

| Model | Released | $ in/out | Rated where |
|---|---|---|---|
| Claude Opus 5.5 | 22 Sep | 4 / 20 | nowhere yet — on every shortlist where Opus 5 is |
| Claude Fable 5.1 | 1 Sep | 10 / 50 | Creative Writing #2 |
| GPT-6 Astra | 5 Sep | 10 / 50 | Creative Writing #1 |
| GPT-6 Sol | 22 Sep | 2 / 10 | nowhere yet — added where a cheap strong model makes sense |
| Grok 4.7 | 21 Sep | 1.6 / 4.8 | nowhere yet; Grok 4.5 is #46 in writing — not shortlisted |
| Qwen 3.8 Max / 2.4T | Aug–Sep | 2 / 6 | 2.4T is #14 in writing — behind cheaper options |
| GLM-5.3 | 19 Aug | 0.84 / 2.64 | Creative Writing #5 — the value pick |
| Muse Spark 1.3 | 3 Sep | 1.25 / 4.25 | Creative Writing #11 |

## Shortlists

Prices are OpenRouter's, $ per million tokens in / out. All of them are on
OpenRouter, so the test tool needs one key, as `tryout.py` does.

### Reader — 5 to test
| Model | $ in/out | Why |
|---|---|---|
| Claude Opus 5 *(incumbent)* | 5 / 25 | #1 on EQ-Bench 4 by a clear margin |
| Claude Opus 5.5 | 4 / 20 | Its successor, released yesterday, cheaper; **unrated** — test, don't assume |
| Gemini 3.1 Pro | 2 / 12 | **#1 on the Russian arena** — for the reader, Russian weighs more than an English EQ score (1142 there). A preview id: fine for a test, not for production |
| GPT-5.5 | 5 / 30 | #4 on EQ-Bench 4, #2 on Judgemark; strong Russian on the arena |
| GPT-6 Sol | 2 / 10 | New (22 Sep), unrated, the cheapest strong option — matters because re-reads repeat monthly |

**Kimi K3 is off this list, and only this one.** The owner's point, stated
exactly: for the writer the language barely matters, for the reader it
matters enormously. Kimi's Russian has one data point — Kimi K2 is #24 on the
Russian arena — and the reader is where that counts. It stays on the writer's
list, where it is #4.

### Writer — 5 to test (the most important agent, HANDOVER §2)
| Model | $ in/out | Why |
|---|---|---|
| Claude Opus 5 *(incumbent)* | 5 / 25 | #3 in writing, lowest slop of the top ten, Claude leads Russian creative |
| Claude Opus 5.5 | 4 / 20 | Successor; unrated |
| Claude Fable 5.1 | 10 / 50 | #2 in writing. Runs once per person, so the price hardly matters |
| GPT-6 Astra | 10 / 50 | #1 in writing; unrated on EQ |
| Kimi K3 | 3 / 15 | #4 in writing at a third of the price |

### Ten sketches — 3 setups to test
Opus 5 at low effort *(incumbent)* · GLM-5.3 ($0.84 / $2.64 — #5 in writing,
low slop, a different family) · **five from each**. The test is not which
sketch is best; it is which set of ten is most *different*.

### Interviewer — 3 to test
Claude Sonnet 5 *(incumbent, 1236 on EQ-Bench 4)* · Kimi K3 · Gemini 3.8
Flash (cheap, and the best cheap judge of text). One conversation per person;
cost is irrelevant, the first impression is not.

### Scribe — 4 to test
| Model | $ in/out | Why |
|---|---|---|
| Claude Sonnet 5 *(incumbent)* | 2 / 10 | Known-good |
| GPT-5.4 Mini | 0.75 / 4.50 | Lowest measured hallucination rate (5.5%) |
| Gemini 3.8 Flash | 0.75 / 3.75 | Strong careful reader (Gemini 3.7 Flash: 83 on Judgemark), good Russian |
| GLM-5.3 | 0.84 / 2.64 | Cheapest; strong writer, but no hallucination or Russian data — the test decides |

Run **without** reasoning mode — it raises hallucination 2–3×, and this is
the agent that must never invent a fact about somebody.

### Biographer — no separate test
It writes in his voice about his life; it should follow whichever model wins
the writer. Testing it separately would cost days for no new information.

### Watchman — not part of the personal test
Stays on its current model until a labelled Russian crisis set exists (see
finding 3).

### Not covered here
Ears (speech-to-text) and mouth (text-to-speech). They are 68% of the bill
(HANDOVER §13.6) and deserve their own research — separately, because they
are judged by different instruments.

---

## Order of the test

It follows the pipeline, because each agent's output is the next one's input,
and only one stage changes at a time — the best output of each stage is saved
and used as the fixed input for the next.

1. **Interviewer** → the owner's own words (keep all three transcripts; the
   reader will use the best one)
2. **Reader** → «is this true about me?»
3. **Sketches** → «which set of ten is most varied?»
4. **Writer** → «which of these would I want as a friend?»
5. **Voice** — the five from §7b, on HIS friend → «is he alive, does he hold?»
6. **Scribe** — over several days → «did he remember right, did he invent?»

## How to run it

`backend/myself.py`, one command per stage, in this order:

```
python3 myself.py interview    # ~15 min — answer like a message to a friend
python3 myself.py read         # 5 readings of you → which is true?
python3 myself.py sketch       # sets of ten → which are really different people?
python3 myself.py write        # 5 friends from one sketch → whom would you talk to daily?
python3 myself.py talk         # the five voices, with YOUR friend
python3 myself.py scribe       # what each scribe took from that talk
python3 myself.py status       # what is chosen, and what it all cost
```

Every stage runs the app's own function on each candidate — only the model
behind `brain.think` / `brain.generate_text` changes — shows the results blind
in `backend/data/myself/<stage>.md`, and reveals names and real costs only
after the pick. The pick becomes the next stage's input.

