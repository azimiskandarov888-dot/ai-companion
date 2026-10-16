# HANDOVER — read this first

Everything a new session needs to work on this project without re-deriving it
or re-litigating decisions that are already made. Written 2026-09-17 on branch
`claude/gallant-bardeen-0l6ff0`; revised through 2026-09-23 on
`claude/awesome-planck-wdj4hu`, then on `claude/ai-companion-next-steps-c593db`,
and since the evening of 2026-10-08 on **`claude/ai-model-selection-voice-f93485`**
(worktree `~/ai-companion/.claude/worktrees/ai-model-selection-voice-f93485`),
which is where all current work lives — ahead of the others; run the server
from this one. **1361 tests pass** (2026-10-12). Every number below was
measured by running the code, not estimated; where something is an estimate
it says so.

**Start with §0** — where things stand and what comes next, as of the end of
the last session (2026-10-08). The rest is the record of how it got here.

Where this document and any other document disagree, **this one is right** —
the others were written earlier and some of them have drifted.

**Known state of the other documents:**

| Document | Trust |
|---|---|
| `ALIVE-BRAIN.md` | **which brain** — decided 2026-10-02: **Gemma 4**, by the owner's ear (round 3, English, conversation D). The bake-off: 26 models on the live-talk check (`spoken_check.py`), then whole conversations voiced blind, first in Russian (the voices were too poor to hear the brains apart), then in English with the same model on both sides. Why the person's side (Tim, a short «you're a real person» prompt) sounded more natural than the companion, and the probe E built that way — better on the numbers; the owner: «the conversation D is much, better». Claude Sonnet 5.5 is out for the live voice (it always thinks through OpenRouter). Training our own model: researched, not needed now |
| `MODELS-RESEARCH-2026-10-09.md` | **which model for which agent — the research of 2026-10-09** (in Russian; seven research strands: every lab and its access, Russian quality, writer and sketches, reader, scribe, watcher, embeddings). Picks: scribe → Claude Haiku 5.5 with thinking off; reader, writer, sketches stay on Claude Opus 5; watcher only after a labelled Russian set; embeddings → `qwen/qwen3-embedding-8b` on the same OpenRouter key. And the call settings to fix BEFORE the test: no ZDR, the scribe and watcher think by default, the watcher reads any error (a moderation 403 included) as «no danger», xhigh/max collapse to high, embeddings wait for an OpenAI key. Raw notes: `research_notes/` (not in git) |
| `ENGLISH.md` | **the conversation in English** (2026-10-02) — how it is switched on, what has an English twin, how `tests/test_english.py` guarantees no Russian reaches an English conversation, and what is still Russian-only |
| `SOUNDS-HUMAN.md` | **why he sounded like a robot, and what fixed it** (2026-09-30, the owner: «Понял, Азим. Программирование — дело непростое…» where a person says «Ого, программу? А про что?») — the research (Heritage's change-of-state token, Jones & Bergen's Turing tests, Reinhart et al. on instruction-tuned register), which of OUR rules caused half of it, the A/B on the real voice, what was tried and dropped (quoted prohibitions, example lines, a list of interjections, other models); part 3 (2026-10-02) — live talk versus messaging: turn length, listeners' «угу» and «что?», one question, goodbyes, with the measurements |
| `LATENCY.md` | **how fast he answers, measured, and the plan in four stages** — stage 1, the live channel, built 2026-09-30: 1.6–2.2 s from the end of the person's words to his first sound, against ~6.5 s before; where every tenth of a second goes, what was found on the way, stages 2–4 and what each needs from the owner |
| `VOICE-MODELS-REHEARSAL.md` | **history**: which voice, from 24 rehearsed first meetings (2026-09-27) — Luna chosen 2026-09-28; **replaced by Gemma 4 on 2026-10-02** (`ALIVE-BRAIN.md`) |
| `SOUNDS.md` | his coughs, «кхм», sighs, laughs and yawns made by the voice itself (our markers → Fish S2.1 tags) — **layer 1 built 2026-09-28**, and what listening showed; layer 2, the world around him as a quiet loop played by the phone, waits for the iOS screen |
| `FIRST-MEETING.md` | **the plan that replaces the intake interview** — owner's decisions of 2026-09-26; step 1 (the conversation) built and rehearsed 2026-09-27; **step 2 — one companion, born blank and written in layers — built 2026-10-08/09**; step 3 (sign-up screens, iOS) ahead |
| `BOUNDARIES.md`, `AUDIT-2026-09.md` | current, evidence-backed |
| `VISION.md`, `README.md` | corrected today; the rest is older but sound |
| `BUILD-PLAN.md`, `ALWAYS-ON.md` | **stale** — phase plans and an always-on listening design that was not built |
| `SOUL.md`, `BOB-PERSONA.md`, `WHO-HE-BECOMES.md`, `HOW-HE-ATTACHES.md` | reasoning documents, still the best statement of *why*; some describe mechanisms that have since changed shape |
| the voice documents (`HIS-VOICE.md`, `BOBS-VOICE.md`, `VOICE-TEST.md`, …) | research notes, not specifications |

---

## 0. Where things stand, and what is next (2026-10-08, evening)

### The decision: no interviewer — one companion, born blank, written in layers

The owner, 2026-10-08: no interviewer; from the very beginning the person
talks to the companion himself. And 2026-10-09, correcting the first build (a
separate «shadow» sketched from ten strangers): «Мы не должны создавать
отдельного агента для этого… тень будет тем же самым компаньоном. Только
сначала он будет как пустая бланка. Сперва с рандомным именем. И если у юзера
будут какие-то предпочтения… с самого начала он будет с ними, но все еще
пустой… В реальной жизни они открываются со временем, а у нас они будут
создаваться со временем… для юзера… это выглядит одно и то же». Earlier
picks that still hold: the reader and writer are tested on his own talks;
what the companion is FOR is written **when the reader is sure**; and after
that «its not one build. its a build that we are always shaping».

Built (`app/shaping.py`, `matchmaker.create_blank` / `LAYERS` / `write_layer`;
`docs/FIRST-MEETING.md` «Шаг 2»):

- **Born blank, with no model:** a random name from three generations of
  common names (`matchmaker._NAMES`, Russian or English by the conversation),
  gender and age from the person's own words at the door («с девушкой
  постарше», «a guy my age», «70») — a teenager's friend always a peer — and
  the words themselves kept as `given`, true of him from the first minute.
  An age nothing decided stays blank. Instant and free; the ten-strangers
  sketcher is gone.
- **Talking while blank** (`persona._BLANK`): plain and a little shy; asked
  about himself, he answers briefly and ordinarily, and what he says is kept
  by the scribe and is law for every layer after. He never lives where the
  person does — he says where, when asked.
- **Written in layers, in the order people open up** (each once, never
  rewritten; only empty places filled, by the code as well as by the prompt):
  1 · what he is like (character, manner, where he lives, what he does) —
  after the first real talk; 2 · what he lives for and what he is for THIS
  person (his subject, what he wants to learn from them, his people and
  things) — when two readings in a row name the same need (never before the
  2nd, at the 5th regardless); 3 · his depths (story, faults, contradiction,
  what has not healed) — once they know each other (meeting stage 2, ~2,000
  of the person's words). Between layers he is told he is opening up little
  by little (`persona._OPENING`).
- **Between talks, never during one:** a layer waits in his file (`_next`)
  and becomes part of him as the next talk begins (`shaping.settle`).
- **Always shaped after that:** a re-reading that moves what he is for sends
  the writer to add to him (`persona.deepen(now=True)`); no deepening, no
  re-reading of its own and no «week» before the layers are written.
- About $1–2 a person, once, for the layers and readings (estimate).

### The next session starts here: the owner's blind test, in the new order

**Before anything — top up OpenRouter.** $0.35 left (2026-10-08), and now the
watcher and the scribe run on it too. ~$10 at
[openrouter.ai/credits](https://openrouter.ai/credits), paid by an adult (the
owner is 15). The whole test is ~$3–4.

**Run from this worktree's `backend/`** with `.venv/bin/python`. Its `.env`
was copied from the old worktree and its `.venv` made on 2026-10-08; its
database is new — the old talks stay in the old worktree.

| # | Command | Read | The question he answers | ~$ |
|---|---|---|---|---|
| 1 | `myself.py begin` | — | the door's questions; he is born blank — a random name and your wishes, **held**: the app will not write his layers itself | 0 |
| — | `./run.sh`, then http://localhost:8000/live#me | — | 2–3 talks with him while he is blank, more than 10 minutes apart | ~0.1 a talk |
| 2 | `myself.py scribe` | `scribe.md` | «Кто запомнил верно — про тебя и про него — и ничего не выдумал?» | 0.1 |
| 3 | `myself.py read` | `read.md` | «Какое из чтений правдивее про тебя?» | 0.5 |
| 4 | `myself.py write` | `write.md` | each writer writes his first two layers; «С кем хотелось бы говорить каждый день — и кто не спорит с тем, что уже сказал о себе?» — the pick becomes him; his depths the app writes later | 3 |
| — | `myself.py status` | — | what is picked, his talks so far, what it cost | 0 |

Each stage runs the app's own function for every candidate through the app's
own road — only the model changes (`myself._model`), blind, names and real
costs after the pick; the pick is the next stage's input. The interview,
`meet`, `talk` and `live` stages are gone with the interview.

**After the picks — my work:** set the winners as the defaults
(`config.READING_MODEL`, `WRITER_MODEL`, `BRAIN_MODEL` for the scribe — one line
each).

### Still open, from this evening

- **Done 2026-10-09 — the call settings the model research found**
  (`docs/MODELS-RESEARCH-2026-10-09.md`): every background call asks for zero
  data retention (`config.BACKGROUND_ZDR`); the scribe, the watcher and the
  «same need?» comparison switch thinking off explicitly (`effort="none"`) —
  the owner asked whether the scribe should think; the test decides it, with
  Sonnet 5 in it twice, thinking and not (`myself.SCRIBES`, «@high»); efforts
  pass through as asked (xhigh, max) and a model that will not take one is
  asked once more at the nearest; **every Anthropic and OpenAI model on
  OpenRouter is moderated** — a refusal (`brain.Refused`) is asked again of
  `config.UNMODERATED_MODEL` (DeepSeek V4.1 Flash) by the watcher and the
  scribe, and a watcher that could not read a line now says «worry» (what =
  `safety.UNREAD`: ask how they are, once), never «no danger»; memory by
  meaning is ON — `qwen/qwen3-embedding-8b` through OpenRouter, one host
  (`config.EMBEDDING_PROVIDER`), checked live: «внучка опять не звонит» is
  0.58 to «внучка Маша звонит по воскресеньям», 0.39 to a bicycle. The
  `myself.py` shortlists are the research's. Not done: strict JSON schemas,
  the reader and writer on a moderation refusal (they retry at the next talk).
- **Done 2026-10-12 — only the person's voice goes to the live ears** (`app/gate.py`; the owner: «чтобы слушали только наш голос»). Deepgram bills the audio it is sent, silence included, and the live channel sent it everything. Now the phone still streams to our server, and only speech goes on: opened by a voice (with the second before it), held until Flux's own EndOfTurn (it must hear the pause), opened by itself as he stops speaking (that is when people answer) and closed otherwise; between turns 80 ms of silence every 4 s keeps the line alive (Flux hangs up after ~10 s without audio; 8 s held, measured). Errs open: a noisy room saves less, never hears less. Real Flux, the same talk whole and gated, three trials: the same words; end of a turn 0.88 s vs 0.89 s; short answers 0.70 vs 0.79 s; 68% of the audio sent (long turns — a talk of short answers ~50%). Every talk logs «heard N s, sent to Deepgram M s». `LIVE_GATE=0` sends everything as before. Billing could not be read back: the Deepgram key has no `usage:read` — the console's usage page shows it.
- **Cheaper ears — looked into 2026-10-12, switched 2026-10-14 (below)** (the owner: «cut the price tag very hard»). List prices for streaming, per hour of audio sent: Soniox `stt-rt-v5` $0.12 · ElevenLabs Scribe v2 Realtime $0.39 · AssemblyAI Universal-3.5 Pro Realtime ~$0.45 · Deepgram Flux ~$0.47 (ours) · Speechmatics, Google transcribe-live $0.54 · Gladia $0.55–0.75 · OpenAI GPT-Live-Transcribe $1.02 · Azure $1.60 — mostly from Soniox's own comparison page (June–Sept 2026): check before paying. Only Soniox is a real cut — but it bills the whole stream («charged for the full stream duration», its keepalive and finalize docs), so ~$2.5 → ~$1.2 a person a month at 20 min a day, not ~$0.6, and the gate saves nothing with it: Russian and English, its own end-of-speech detection, keeps no audio — but no early «похоже, договорил» like Flux's EagerEndOfTurn, on which `live` starts the draft, so Bob may answer later. The one independent test (Artificial Analysis, AA-WER Streaming, 1 Jun 2026 — English only, Soniox version not named): words wrong — Soniox 11.9%, Flux 7.36%, ElevenLabs Scribe v2 Realtime 3.64% (Cartesia Ink-2 as good, but English only); Russian has been tested by nobody independent. So the rule for any switch: words first, then how soon it knows the turn is over, then price. The owner's Soniox key is in `.env` (13 Oct); the account had no balance yet (402 «organization_balance_exhausted»; free credits for new sign-ups ended). **First test, 14 Oct** ($3 on Soniox; u1–u3 in a talk, 3 trials each, real time): the words the same (Soniox even wrote «пришёл»); the end of a turn after the last sound — Flux 1.03 s (its «похоже» 0.53 s), Soniox default 0.53 s, never cutting in; Soniox «quicker» (latency level 2, sensitivity 0.3, max 1.5 s) 0.41 s but called the end mid-sentence 9 times — never use it. **Then the owner's memos** (14 Oct: him talking to Bob with thinking pauses, 30 s English + 38 s Russian, both ears at once): Flux never called «finished» mid-talk, but late — 2.34 s after «Что предложишь?» — and in English (our Russian hint) never, with 8 «probably» drafts on the way; Soniox default ended on unfinished thoughts («I've really been thinking about—» after a 1 s pause, «…нет,» after 3 s); Soniox PATIENT (`endpoint_sensitivity` -0.5, `max_endpoint_delay_ms` 3000) waited through those, ended at the real end in 0.9 s, u1–u3 still 0.41–0.6 s. Left: 2 pieces ending «—» — a rule of ours: a piece ending «—», «,» or «…» is no end — and 5 finished sentences the person went on after, as people do (Bob must stand down if they carry on before he speaks). Words: Soniox kept «ну», «эм», «Боб», «нехорошо» and the English. Still untested: an older voice, a noisy room. Before any switch: the same recordings (`backend/live_check/u1–u3.pcm`) through both — the words, and how long after the last word each knows the turn is over; At thousands of daily users: our own open Russian models (GigaAM v3, T-one — both stream) on a rented GPU, and volume contracts; the phone's own recognizer as a free backup. Also on the bill: Google's Flash-Lite voice is $6 per million sound tokens until 31.12.2026, then $12 (`docs/WHY-LIVE-IS-FAST.md`) — that line doubles in 2027.
- **Done 2026-10-14 — the live ears are Soniox** (the owner: «лучше уже полностью перевести нашу программу на Soniox»; Deepgram only in git history — his call, after being told that a fallback costs nothing). `hearing.py` rewritten: the key in a header, `stt-rt-v5`, ru+en hints, his name in `context.terms`, PATIENT endpoints (`SONIOX_ENDPOINT_SENSITIVITY` -0.5, `SONIOX_MAX_ENDPOINT_DELAY_MS` 3000); `Turns` makes Soniox's tokens into the same TurnInfo the live channel always followed (StartOfTurn / Update / EndOfTurn — no «похоже»: Soniox's «договорил» comes as early as Flux's «похоже» did, so no drafts on a guess are paid for). **A thought broken off is not an end** (the owner's rule): an «<end>» on words ending «—», «,», «:», «…» is held — more words make it one turn (how long, and what he says meanwhile: the next bullet — the fixed 1.5 s / 3.0 s first tried here was called «тупо» by the owner the same day, and replaced). Safety nets: words that vanish close the turn; a turn quiet for max delay + hold + 1 s ends by itself. The gate is OFF (`LIVE_GATE=0`): Soniox bills the stream, so silence costs nothing more, and everything measured was on whole audio. Checked end to end on real Soniox with the owner's memos: «Well, Bob, I'm— I'm okay.» one turn; «I was just— I've really been thinking about doing something like— … good at it.» one turn; the Russian (whispered, a phone playing) three turns, each at a finished thought. His last three seconds of the English memo, at -56 dBFS, were heard by no setting — as near silence. `check_keys.py` probes Soniox; `.env.example` says how to get a key. NOT YET: the owner's own ear on a live talk; an older person's real voice (only his whisper so far).
- **Done 2026-10-14 (evening) — he listens by the moment, not by a rule** (`app/listening.py`; the owner, of «Бывает такое... О чём задумался?» and of fixed seconds: a real person «просто скажет "ну" или "ну, ну, и что там?"», by the mood — in a quarrel with heat, and he may cut in; «не ставь тупые, точные правила… прямо попросить ИИ»). Research behind it (in the module): plain sounds say «go on», ones with feeling show it reached him and make stories better (Bavelas 2000, Stivers 2008, Tolins & Fox Tree); ~1000 an hour, most turns of 5+ words get one; matched in feeling and strength (Couper-Kuhlen); a stumbling teller gets them most (Healey 2013); disputes come in fast (Kotthoff 1993); OpenAI's own turn detector has an «eagerness» (≈2/4/8 s); LLMs fail to decide pause-by-pause zero-shot (a 2026 benchmark of eight). So TWO SPEEDS: after each of their turns, one small call to the conversation's model (`config.LISTENER_MODEL`, ~$0.0002) reads the talk and returns a stance — mood (in the talk's language), pace (jump in / quick / easy / patient), how often (often … silent), colour (calm / soft / lively / heated) and the words, chosen from his palette (`first_sound.LISTENER`, ~30 short sounds, made once per voice in each colour — his own voice told how, as his breaths are). The live channel (`Session._along`, every 0.1 s) times it with a person's unevenness — every span drawn anew: a sound a third of a second to a second into a pause (never after a question, never without headphones, never twice running), «Ну?» when a thought breaks off, then his turn (`ears.finished()`); a hard talk lets a finished sentence rest with a soft sound (`Turns.finished`, the `Pause` event); a quarrel takes the turn at a short pause and one word over him stops him (`talks_over(heated=)`); his breath before answering follows the pace (`first_sound.choose(eager=)`). The brain is told what is between them now (`between`) and what he already said meanwhile (`said_meanwhile`), and `BY_EAR` asks for a live listener's few words, no stock phrases. Checked on the real models: the listener read a quarrel as jump in/heated («Ну-ну.», «Ой, да ладно.»), a year since mother died as patient/soft («М-м…», «Да…»), a cat in the washing machine as quick/often/lively («Ого!», «Да ты что!»), small talk as easy/calm («Угу.», «Ага.»); the brain after a broken-off thought and his «Ну?» — «О чём именно?», in a quarrel «Слышу, слышу... Что ты говорил?», in grief «Что думаешь...». NOT YET: the owner's ear on a live talk. Both FOUND items were built the same evening (next bullet).
- **Done 2026-10-14 (late) — a silence between them, and looking things up, alive** (the owner: «если человек долго молчит и он сидит в приложении, то можно спросить, ты тут?… Но если человек вышел с приложения… лучше не говорить»; and of searching: «иногда подшучивал… "Эм..." "Так, ну тут это, а тут это..."»). SILENCE: the listener now also reads how long a silence is natural (`Stance.silence`: short / normal / long — «подожди, чай налью» is long) and whether a joke would land (`Stance.playful`); `Session._check_in` speaks into a silence when it passes the drawn span (`listening.SILENCE_AT`), at most twice (`CHECK_INS`), never when the page/app says it is out of sight (`{"type": "away"}` / `"here"` — the page sends them on visibilitychange; the iPhone app must too, when it moves to the live channel) or the microphone stopped (`_GONE_AFTER`). What he says is the brain's, from the talk, with a cue that is never stored (`main._assemble(cue=)`, like the hello cue); «…» means he stays quiet. Checked on the live brain: after grief «Я с тобой... Просто знай, что я здесь.»; small talk with a bus driver «Наверное, народу много... Устаешь за смену?»; after «чай налью» «Ну что, налил? С чем пьешь?»; after a quarrel «Ну чего ты замолчал... Расскажи, в чём я не прав.» (with «Ты тут?» as the cue's example it said «Ты тут?..» three times in four — the example now comes last). SEARCHING: the filler is plain, or — when the listener says a joke would land, never in something sad or a quarrel — a joke now and then (`_FILLERS_PLAYFUL`, `_JOKE_CHANCE`): «Я тебе что, справочное бюро? Ладно, щас гляну.», «Я тебе что, Гугл?». NOT the owner's «я тебе чё, ИИ что ли» — Bob never says he is a program and never claims he is not (companion, «what you are»); a joke that he is not an AI is the second. While the search runs he mutters, ready-made in his voice (`first_sound.SEARCHING`: «Эм…», «Так, тут…», «Ага…»), never twice running (`_mumble`). The live page's footer now shows what really answers, from /api/health (`ears_model`, `chat_model`, `tts_provider`) — it said «мозг Luna, голос Fish», months stale; the brain has been Gemma 4 all along.
- **Done 2026-10-16 — a sense of time, and a second evening is not a first meeting** (the owner's feedback after two days away: «he has no sense of time… I said "hi" he said "im still here"»; «he knows my name already, but still asked: чем обычно занимаешься в свободное время?»). Two causes, both rigid rules: (1) a gap under three days was never told to him (`memory.NOTICED_GAP`), and the log was handed over as one stream — «Эй, привет» a day and a half after «Я с родителями живу, и.» read as the next second of the same talk. Now `memory.conversation` marks the first line of theirs in each new talk (≥ `NEW_CONVERSATION_GAP`, 10 min) with how long it had been, in a person's words — «(новый разговор — прошло полтора дня) Эй, привет.» (`_ago`: minutes, hours, «сутки», «полтора дня», days, weeks); only in what he is handed, never in the log. (2) The first-meeting block ran by WORDS (< 300), so a second talk of a 114-word acquaintance was still «ПЕРВАЯ ВСТРЕЧА… потом, к слову, — откуда он и чем занят». Now `memory.met_before` (a talk before this one) gives `meeting._AGAIN` instead — pick up what was between you, how these days went, what they left unfinished; no getting-to-know-you questions out of nowhere — and `meeting.where` no longer says «только что познакомились». Replayed his real case on the live brain: «Эй, привет.» → «Привет. Как ты? Что там с родителями, всё в порядке?»; «…просто хотел спросить, как дела» → «Да всё потихоньку... Свои дела перебирал. А ты чем занимался эти дни?». ALSO: the owner saw his words but heard nothing — the server was sending the voice (a probe through /api/live: 3 pieces, 3.6 s of audio; his own «Ты тут?» was logged, which happens only once its audio went out), so the browser held it; the page now says so and one click turns it on (`watchSound`, the AudioContext state). It was **Safari**, and still silent after that (2026-10-16): the page now makes and wakes its AudioContext INSIDE the click (`ensureAudio`, with a moment of silence — Safari lets sound start only from a click, and the context used to be made after the microphone's permission was awaited), shows «звук: state, rate, кусков голоса: N» and has «проверить звук» (a 0.35 s tone). Not yet known whether that fixed it; if a tone plays before the talk but not during it, suspect Safari ducking playback while its own echo cancellation captures (then: Chrome, or headphones with echoCancellation off). ALSO FOUND: OpenRouter had **$0.09 left of $15** — every model still answered a one-word ping, but a reading, a layer or the scribe's call can no longer pass OpenRouter's affordability check, and the voice-brain has some 30 replies left. And the reader and the writer had never run for the owner's #me companion at all: it is an old-style one (no `layers` → `persona.written` = 3, «a man of 87»), made by the live channel, not by `myself.py begin` — and `reading.keep_reading` only RE-reads. The plan stands: an adult tops up OpenRouter, then `myself.py begin` (it erases this companion and his talks and makes the blank), 2–3 talks, then scribe/read/write.
- **Speech for the reader** (the owner's idea, 2026-10-09): tempo, pauses before answering, length of turns, broken-off sentences, and the «э-э» the recognizer now throws away (0 in 252 of his heard lines) — the `speech` section asks for them, nothing measures them yet. Pure measurement, no model.
- **A child (under 13), or a teenager who switched memory off, stays a
  blank**: nothing is kept to write him from. The owner's call.
- **The iPhone app still uses the interview** (`/api/companion/create`). The
  new start needs the ordinary sign-up screens and an endpoint that makes the
  blank companion (`docs/FIRST-MEETING.md` step 3).
- **No automatic check that a written layer does not contradict what he said**
  (FIRST-MEETING §9) — the owner's eye in the test for now.
- Whisper and the embeddings still need an OpenAI key (the iPhone's
  `/api/talk` ears; recall by meaning).

### Keys and money (2026-10-08) — all in `backend/.env` of this worktree, never in a message

| Key | State | What it pays for |
|---|---|---|
| `OPENROUTER_API_KEY` | works; **$0.35 left** | Bob's brain (Gemma 4 on ModelRun, $0.75 / $1.00 per million, the fastest host and 8× the cheapest), every background agent since 2026-10-08, and every test |
| `SONIOX_API_KEY` | works, **$3 prepaid** (14 Oct; no autopay) | the live ears (Soniox `stt-rt-v5`) — billed for the whole stream, ~$0.12 an hour. Out of balance it answers 402 «organization_balance_exhausted» and the live channel says «the ears: …» |
| `DEEPGRAM_API_KEY` | not used since 14 Oct | the old live ears (Flux, EU) — Soniox replaced them |
| `GOOGLE_CLOUD_API_KEY` + `GOOGLE_CLOUD_PROJECT` | works (8 Oct) | **Bob's voice** — Gemini 3.8 Flash-Lite TTS on Google Cloud (Agent Platform), an API key bound to the service account `bob-voice`; billed to the card monthly, **budget alert at $5** |
| `GEMINI_API_KEY` (AI Studio) | works, first paid tier, **$30 prepaid** | nothing of Bob's any more: for TTS it allows only **10 requests a minute and 100 a day** (measured 7 Oct). The $30 is Gemini-API-only, lasts 12 months, refunded only if the account is ever switched to Postpay. The owner: «я эти 30 долларов потрачу на Gemini» |
| `FISH_API_KEY` | works | nothing now (the old voice) |
| `ANTHROPIC_API_KEY` | missing — **not needed** since 2026-10-08 | the background agents go through OpenRouter |
| `OPENAI_API_KEY` | **missing** | Whisper (the iPhone's `/api/talk`) and the embeddings (recall by meaning) |

### Done 2026-10-03 → 10-08

**Speed** (`docs/WHY-LIVE-IS-FAST.md`, sections «5.10», «7.10», «8.10»):
- **His first word now comes 1.20 s after the person stops** (median of 9, through the real services; 3.7–4.3 s on the morning of 3 Oct, 1.73–1.80 s on 7 Oct). Gemini Live, measured the same way with Bob's prompt from Tashkent: 1.44–1.72 s.
- **Thinking while they talk, without waste:** a draft only on Flux's «похоже, договорил», at most 3 a turn, nothing voiced before «договорил». A draft at every 0.2 s pause had begun **69** brain requests for five turns on the real ears; this begins **10**, at the same speed.
- **A dropped draft re-opens the line to the brain** at once (HTTP/1.1 closes it: +0.2 s measured); **two lines to the voice** (+0.17 s on the second piece otherwise). HTTP/2 was rejected: httpcore 1.0.9 sends no RST_STREAM, so an abandoned stream would keep running upstream, billed.
- **The brain is asked again if silent 1.1 s** (`brain._hedged`, `BRAIN_HEDGE_AFTER`).
- **The voice on Google Cloud**, no ration (15 requests in 10 s all passed); first sound 0.49–0.66 s. On the AI Studio key Bob went silent mid-conversation (429). `tts._Budget` still keeps any AI Studio voice within 10 a minute, and a voice rationed so is spoken in two requests an answer.
- **His first word ready-made more often:** the openings Gemma actually uses («Ох…», «Да,», «О…») added; a ready one is cut off however short, and the piece after it is short too.

**His sounds** (the owner: «м-м» before every answer «even when it's not logically belong there»; «i need it to be like breathing… different sounds all the time… it cuts in the middle of the sound»):
- **A breath, most of the time** — otherwise «ну…»/«да…» (or «хм…», «так…» before something to weigh), sometimes nothing (`first_sound.SHARES`).
- **13 breaths per voice** — 6 in, 3 out, 4 deep — made by the voice told «just air, no voice at all»: half of Gemini's plain `<breath>` takes were voiced, an «э». Every take is checked for a pitch (`first_sound._voiced`) and made again if it has one; never shortened; never one of the last three.
- **Timed to his words and never cut:** streamed to the phone a little ahead of playback, it fades out over 80 ms under his first word when the words come (`live._Breath`); joined from its middle when there is less time than it lasts (`first_sound.joined`). Measured: breath-to-word 0.06–0.20 s, no silence. The voice's own silence before his first word is cut off.
- **Older → deeper and stronger** (the owner: «чем старше, тем больше вдоха… и дольше, и сильнее»): a companion of 55+ or a person who said 60+ at the warm-up — `young.ELDER`, the one band now kept about an adult, which changes nothing but his breathing. Three breaths in four are deep for them (`first_sound.DEEP_SHARE`), the rest in or out, still never one of the last three: the owner chose «чаще глубокий» over «всегда» and over a deep one as just one of thirteen — which it had become by mistake, so `test_somebody_past_sixty_gets_the_deep_breath` failed half its runs.
- **«м-м» in their pauses is off:** half those pauses were the end of the turn, and it became the start of his answer followed by a silence.
- His mid-sentence «э-э…» / «м-м…» stumbles stay (the owner: keep both).

**Tests: 1294 pass.** Commits are local on `claude/ai-companion-next-steps-c593db`, not pushed.

### Still true from 2026-10-02/03

- **Gemma 4's weak spots:** Russian slips («такой пекло»), chosen by ear in English; repetition at the host's default temperature not looked into; the Russian brains round (Yandex, Sber) needs the owner's accounts.
- **The voice is 3.8 Flash-Lite** («3.8 for more voices and less price tag»), Zubenelgenubi / Callirrhoe the owner's best; every companion gets his own voice from Gemini's 30 (Pulcherrima out: heard as a man), kept in his persona (`voices.py`). The owner on the voice through Google Cloud: «absolutely perfect… insanely good».

### The plan after the test, in order

1. **The winners into config** (me — above). The road itself is done.
2. **His own friend, live** — the test itself ends with it: the writer he picks writes the first two layers of the companion he has been talking to, on `/live#me`.
3. **The iPhone app on the live channel** (`LATENCY.md` stage 3). Owner: an iPhone connected to the Mac, Xcode signed in.
4. **A server near the services** (stage 4). The brain's host answers in ~0.1 s at OpenRouter; from Tashkent it takes 0.6–0.9 s — the road and the queue. Measure first from a server rented for an hour (~$1); owner: the hosting account.
5. **The Russian brains round** — owner: Yandex and Sber accounts.
6. **Real people — TestFlight**, after the must-fix list (§10): crisis-line numbers, who else is told about danger, how long data is kept, prompt injection.

### How the owner works — keep to it

- Russian — and sometimes English, dictated (2026-10-08): answer in the language he wrote in. **Short, plain answers: the result first, then his steps** — each command in its own `bash` block. He stops reading long answers.
- **His ear and his judgement decide**, blind; numbers only sieve. He said so of the brain and of the voices, and it holds for the agents.
- **Money:** say the cost before spending; he asked «Получается те деньги которые я только что положил сгорают??» — be exact about what is refundable. Accounts and payments are done by an adult (he is 15; Google's Gemini API terms say 18+).
- Keys live only in `backend/.env`; never ask him to paste one. Commit locally with the attribution line; never push or open a PR unless he asks.

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
| **The intake interview — a conversation first, a list second.** Every question is the interviewer's (Opus 5 — #1 on EQ-Bench 4, chosen by comparison). It talks like a person meeting someone: after the name, «Очень приятно» and how's your day (small talk builds trust — Bickmore & Cassell 2001); then, most often, a question about what was just said — «пишу программу» → «а про что она?» — because follow-up questions, not topic switches, are what make an asker liked (Huang 2017). **Shy first, closer by the end**: the server tells every call the stage — strangers for questions 1–8 (polite, «вы», quiet reactions or none, no exclamations, praise or «-то/же/ну»; warmth only as attention), a little acquainted for 9–11 (warmer, livelier; the under-thirties move to «ты»), almost friends from 12 (open, close, never an old friend) — and the model keeps pace with the person, never ahead. Why: acquaintance goes from light to personal (Altman & Taylor 1973; Kellermann 1991), the same intimacy is liked less early (Wortman 1976), and in Russian a stranger's warmth reads as put on (Стернин); the owner: «you don't talk to someone you just met like you've known him for years». The server keeps a memo of twelve topics (name; how the day is and what fills it — the friend's topic must NOT land there; what they love; what's coming up this week; country; age; what they love but haven't done in a while; what they're best at; who they last talked to «по душам»; who last asked them for something; what helped the last time it was hard; and, last and required, «А о чём бы поговорить, да не с кем?» with one gentle rescue if the answer is vague). Topics are taken up when they come up, in any order — except that his people and his hard times (`intake.DEEPER`) are offered only after the lighter topics, so never before question 9; up to three questions per thread; at most 18 in all — follow-ups only while every remaining topic still fits, so country and age cannot be lost, and a model that wanders off or stops early is overruled — as is a question filed under age or country that doesn't ask it (a simulated run filed «А кодить давно начали?» as the age). History: the owner rejected a fixed app warm-up («ничем» went unanswered) and then a strict list («it wants to end the interview as fast as possible») — both times rightly | owner + councils, 2026-09-24/25 (`tests/test_interview.py`, `tests/test_intake.py`) |
| **The beginning becomes a first meeting — no interview at all.** The person meets the companion himself, in voice, as two strangers: the day and the moment, where from, a topic both care about, names (his first), and closer only as they talk more — measured by the amount of talk, never by days; no list of deep questions anywhere. He is a little shy, calm, more interested in the person than in himself — and NEUTRAL: no manner of speech, no bright traits at the meeting; the real him is not revealed but CREATED over time, in the portrait and after (owner, 2026-09-27; a sketch with «смеётся одним „ха“» opened seven replies of one rehearsal with it). Before: an ordinary sign-up (name, age, gender, country) and the person's choice of his gender and age. He exists as a SKETCH before the meeting and gets his PORTRAIT after it — everything he said about himself is law. He never lives where the person does: abroad or on the road. That he is an AI is written in small print, as on AI sites; he still never says it. The intake row above stands until step 3 replaces it. **Step 1 — the conversation itself — is built** (`meeting.py`; `/api/hello`; closeness by the person's words, 300 / 2,000 / 8,000, kept as a count in `acquaintance` because a child's log is deleted; the server tells him to say his name if he has not by the person's fifth line — and, once he has, that it is said, so he does not introduce himself twice (he did, in the very next reply, when the person answered with their work instead of their name; fixed 2026-09-30) — and to end a reply without a question after two in a row). **Since 2026-09-30, after the owner's first live conversation: the meeting is about the PERSON** — his first words ask how they are and say nothing of himself; he talks about himself only when asked or plainly wanted, in a phrase, never the same thing twice; replies of one or two sentences; he does not say goodbye first («it's weird that you are talking about yourself without knowing that the person you're talking to is even interested in it» — it reverses the meeting's earlier «his own day and weather unasked» and second stories. Scripted A/B on the real voice: talk about himself unasked 11 → 0 in 24 replies, coffee 10 → 2–4, opening with himself 4/4 → 0/8) and rehearsed in three rounds (`rehearse.py`): GPT-5.6 Luna was the best voice for it, Gemini 3.5 Flash-Lite next; Haiku 4.5, MiniMax (asterisk stage directions) and Qwen 3.5 (empty replies) were not | step 1 built 2026-09-27; owner's plan 2026-09-26 (`docs/FIRST-MEETING.md`, `tests/test_meeting.py`) |
| **One companion, born blank, written in layers, and always shaped** — the owner, 2026-10-08/09: no interviewer and no separate «shadow»; from the first second the person talks to him — a random name and their wishes, «как пустая бланка» — and he is written in the order people open up (what he is like → what he is for → his depths). The reader reads all their talks after each one; what he is FOR is written **when two readings in a row name the same need** (never before the 2nd reading, never after the 5th — the owner's pick of three); every layer between talks, never during one; everything he said about himself is law. Then «its not one build. its a build that we are always shaping and making better»: each re-reading that moves what he is for sends the writer to add to him. Amends the row above («набросок до встречи, портрет — после») | built 2026-10-09 (`shaping.py`, `tests/test_shaping.py`); the iPhone sign-up is step 3 |
| **We complement, and sometimes the best complement is matching** — the owner, 2026-10-09: «Мы не мэтчим, мы дополняем. Но иногда самое лучшее дополнение это matching». Matching where it closes what is missing (nobody to share what he loves with → somebody who shares it), complementing everywhere else; said in the writer's rules (`matchmaker._WRITE_SYSTEM`, used by every layer) | done 2026-10-09 |
| **Sections are a floor, never a ceiling** — the owner, 2026-10-09: «разделы… должны быть как bare minimum, а не как ограничение». The reading has 25 sections every reader must LOOK at (`reading.SECTIONS`: the three levels of a person — temperament, strivings/values/fears/coping, the story he tells of himself — Weiss's two lonelinesses, and what a friend needs), plus `more` (anything else, no limit) and `unknown` (what cannot be seen yet, instead of a guess). Only the five every-turn sections reach every line, so a richer reading costs cents once. The companion likewise: `humor`, `dream`, and an open `more` that each layer and every later shaping adds to | done 2026-10-09 |
| **The reader decides WHAT somebody needs; the writer decides WHO gives it.** The request is honoured literally and never overruled — it decides what he is like; the need decides what he is for. Stated ideals do not predict whom people actually warm to (Eastwick & Finkel 2008), but a visibly overridden request provokes reactance, so neither is traded for the other. The first reading is a hypothesis; the conversations correct it (re-reads, confirmed observations). **How the reader gets it right**, by Funder's Realistic Accuracy Model — the cue must exist, reach the reader, be noticed and be used right: the interview now asks the one closing question whose answer says what is missing («о чём тебе не с кем поговорить»); the reader is walked through perspective-taking, direct words over form, competing hypotheses and a Barnum check, in its thinking. Tested on the owner: without that answer every model correctly declined to guess «feelings»; with it, Opus 5.5 wrote «нет никого, с кем можно всерьёз, особенно о чувствах» | owner's question, 2026-09-23 |
| **The rules stay a file you can read, plus mechanisms in code. No fine-tuning.** Four reasons, in order of weight: a fine-tune trained on our own prompt's output can at best COPY it and never exceed it; Anthropic has no fine-tuning API, so it means leaving Claude for a small model that writes worse Russian; catastrophic forgetting is documented and shows up where you did not test; and weights cannot be read, diffed, or fixed by one line with a test | settled 2026-09-22 |
| **The constitution gets CUT, from 26,348 chars to ~8,000.** This is the whole answer to the 94/6 problem. Fine-tuning would have removed the last ~3,000 tokens for a month of work and no way back | **done 2026-09-23: 10,385 chars**, ~6,000 tokens off every request (estimate). Awaiting the owner's ear (§13.1) |
| **Claude is out of the candidate list for the VOICE.** Owner's call on cost, and the observation is real. One caveat recorded in `tryout.py`: the audition runs uncached, so it charged ~4× what the app would. Still the dearest of the five | owner's call 2026-09-23 |
| **The voice is Gemma 4**, through OpenRouter — the owner's ear, 2026-10-02: four blind English conversations, the same model on both sides — he picked D; then «we are done with the model of the companion». It goes to whichever of its hosts is fastest (`brain._where`), no reasoning. Its weak spots are in §0. Before it: GPT-5.6 Luna (2026-09-28, from 24 rehearsed first meetings). The watcher stays on Claude on purpose (`config.SAFETY_MODEL`) | done 2026-10-02 (`config.CHAT_MODEL`, `docs/ALIVE-BRAIN.md`) |
| **His sounds are PLAYED, not read** — a cough, «кхм», a sigh, a laugh, a yawn, made in his own voice (Fish S2.1) from our markers, never a recording of somebody else's; a sound no voice can make (a sneeze) is not offered at all | layer 1 done 2026-09-28 (`tts.SOUNDS`, `docs/SOUNDS.md`) |
| **The model is chosen BY EAR, on the real prompt.** A 50-phrase scored set was proposed and the owner replaced it with listening himself — correctly: no published benchmark measures warm ordinary Russian said to a lonely person, and the ear is the instrument that does | owner's call (`tryout.py`) |
| **He answers like a person, not an assistant** — a reaction first (surprise, gladness, pity — by the news), then something of HIS specific thing: a short live question or what it is to him, in half a sentence; no general truths about the activity («X — дело такое-то»), no receipts («Понял»), no name at the head of a reply, no menu of options, spoken rather than written Russian. The owner's call after his second live conversation; `companion.REACTING` on every turn, `situations._TERSE` for a reply that says nothing, `brain.without_receipt` as the code's guarantee | done 2026-09-30 (`docs/SOUNDS-HUMAN.md`) |
| **A conversation can be in English** — `COMPANION_LANGUAGE=en`. The owner, 2026-10-02: the Russian voices are too poor to hear the brains apart; «change everything to English», and make sure nothing was missed. Every text a model reads or a person hears in a conversation has an English twin written for English (rules, meeting, situations and their detectors, young, body, dates, memory, persona, alerts and the emergency words, mood, week, fit, reading, vows, receipts, fillers, first sounds, stumbles, Fish's own English voices Kai and Mila); background writers are told to write in English. `tests/test_english.py` assembles a turn with every block on and finds no Russian letter but his markers. Not yet English: matchmaker, intake, the reading's writer, the diary — none speaks in a conversation | done 2026-10-02 (`docs/ENGLISH.md`, `lang.py`) |
| **He stumbles as often as people do** — the owner, 2026-10-02: «добавь их в достаточном количестве». People: 6–10 disfluencies in 100 words, teenagers' «like» on top. `aloud.py` now aims at a rate (8.5 / 12 for a companion under 26) with filled pauses, repeats, age-fitting fillers, hedges, in Russian and English: measured ~9 and ~11 in 100 words with the voice's own | done 2026-10-02 (`docs/SOUNDS-HUMAN.md` part 4) |
| **He gives voice at once** — the owner, 2026-10-02: «да, сделай чтобы он сразу подавал голос». People answer ~0.2 s after the other stops (Stivers et al. 2009); his words come 1.6–2.3 s after. Now a «м-м» goes into the pause or the end of their turn — measured live 0.35–0.41 s when he can be interrupted (the default), 0.8–1.2 s when not. A Fish «[inhale]» came out voiced, so no breath until the owner has heard it | done 2026-10-02 (`first_sound.py`, `docs/LATENCY.md`) |
| **He talks the way people talk out loud, not the way they message** — the owner, 2026-10-02: «the conversation of people in massanger and in real life are very very different. and here we are trying recreate not the masanger, but the real life convo». In his own live conversations his turns had a median of 5 words and the companion's 22 — a composed message (react, comment, tell, introduce, ask) where a speaker takes one turn. Now: one move a turn, usually under ten words; one question and then silence; no letter-language («надеюсь…», «хорошо, что…»); no echo; when the person stops mid-sentence or announces a story he only nudges («Что?», «А там что?» — `situations._LISTENING`); «да»/«угу» are no longer an «empty answer» that switched the topic; goodbyes in a few words. Measured with `spoken_check.py` (14 places in a conversation, lines as the live ears deliver them): on Luna, places handled as a person would 50% → 86%, median words 13 → 9, replies with a question 71% → 57% | done 2026-10-02 (`docs/SOUNDS-HUMAN.md` part 3) |
| **He sounds spoken, not written** — the owner, 2026-10-01: too perfect is fake; live talk has stumbles and fillers. Prompting Luna for it does nothing measurable (six ways tried: 0.6–0.9 a reply against 0.4–0.6 untold); Claude Sonnet does it, a second slower and ~30× dearer. So a code layer puts them where speakers do, ~0.7 a reply (~1 with the voice's own «…»), the voice only | done 2026-10-01; the rate was raised 2026-10-02 (the row «He stumbles as often as people do») (`aloud.py`, `docs/SOUNDS-HUMAN.md` part 2) |
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
| ① | **Ears** — speech to text | Soniox `stt-rt-v5` (live channel, `hearing.py`, since 2026-10-14); `whisper-1` (`/api/talk`) | Hears while they speak and says itself when they have finished — 0.4–0.9 s after the last sound, patient through a thought broken off (`hearing.Turns`: held, then a nudge). Keeps «ну», «эм», names. Live audio is never stored, never trained on. Before it Deepgram Flux (1.0–2.3 s; in git history). Whisper stays for the file-at-a-time path the iPhone app still uses |
| ② | **Watchman** — danger in the person's words | Haiku 4.5 | runs as a task; **does not hold up the answer** |
| ③ | **Voice** — the companion speaking | Gemma 4, via OpenRouter (since 2026-10-02) | the fastest of its hosts (`brain._where`: sort by latency; an OpenAI model goes to OpenAI's fast tier first), no reasoning (`CHAT_REASONING=none`): 0.8–0.9 s to first words on the real prompt in the live-talk check, 1.26 s in one cold call through the app. Its hosts keep no cache. Luna before it: 0.8–1.1 s, the prompt ~all cached |
| ④ | **Mouth** — text to speech | Gemini TTS through OpenRouter since 2026-10-03 (`voices.py`, a voice per companion); before it Fish Audio `s2.1-pro` | #1 on TTS-Arena2; makes his sounds. Direct (`fish`) or through OpenRouter — which `fish` becomes by itself when there is an OpenRouter key and no Fish one (`config.voice_provider`). Streams raw PCM to the live channel (`tts.stream`). The owner's Fish key is in since 2026-09-30, so it goes directly, on Fish's starting credit. First sound ~0.45 s after a piece of text is sent — the same through OpenRouter (0.48 s; 10 phrases each), because the middleman costs nearly nothing. About 0.1 s of that is silence Fish puts at the start of every sound. Keep `latency=balanced`: `normal` took 0.78 s. `s2.1-pro-free` is slower (0.60–0.94 s) |

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

### The live channel — `live.py`, `hearing.py`, `/api/live` (2026-09-30)

One WebSocket for the whole conversation, sound both ways. The phone streams
the microphone (16 kHz PCM, 80 ms frames); Flux hears it as it is said. On the
early «похоже, договорил» a reply is **drafted** — `main._assemble(pending=True)`
builds exactly the prompt the turn would get and writes nothing: not their
line, not what memory recalled (gathered as marks), no watcher. On the sure
«договорил» the draft becomes the turn (`main._commit`); if they carried on it
is thrown away without a trace. From there it is the same turn as every other
path — the vows between pieces, the watcher breaking in between sentences, the
farewell, the body, the remembering. The answer is voiced piece by piece
(`tts.ready_split`: the first piece ends at a sentence end of ≥10 characters or
a comma/pause of ≥40) and the sound goes out as it is made; the next piece's
voice is started while this one plays.

His goodbye does not hang up at once: the line stays open `_FAREWELL_GRACE` (8 s) after it plays, and somebody who carries on is answered. Without reasoning the voice sometimes marks a goodbye nobody said («Домой сразу. Спать.»; in 2 of 6 rehearsals of 2026-09-29).

**He can be interrupted — the default since 2026-09-30** (`duplex`; the owner, after ChatGPT's voice: «it was really good that I can interrupt him»). The microphone stays open while he speaks. What echo cancellation misses comes back as HIS words, and `live.talks_over` tells those — and an «угу» — from somebody talking; a stop word («подожди») or two words of their own stop him. A turn that BEGAN over his voice is judged so to its end (the ears decide a turn is over a second after the room goes quiet, when he has already stopped), and `live.their_part` cuts the tail of his echo off the start of the person's turn. Tested in the worst room — no echo cancellation at all, his voice back into the microphone at a third of its level, real Deepgram: he never stopped himself, his echo never became a turn, and «Подожди, подожди…» stopped him in 0.55–0.89 s. With `duplex` the end-of-turn threshold is 0.8 (`FLUX_EOT_THRESHOLD_DUPLEX`): a turn taken too early is mended by carrying on. Without it — a room where he keeps hearing himself anyway — Flux is sent silence while he speaks and 0.3 s after, and the threshold is the patient 0.85.

Live words are HEARD, and the ears mishear («бассейн» → «Басанин», «Азим» → «Азима»): every live draft carries `companion.BY_EAR` — take a strange word by its sense and never say it back, take the person's gender from their own words and not from a name. Flux has no KeepAlive, so a
quiet line is fed silence; after `LIVE_IDLE_SECONDS` (120) of nobody speaking
it closes itself, because Deepgram bills every open second.

**Measured 2026-09-30, end to end with the real services: 1.57–2.16 s from
the end of the person's words to his first sound (median 1.83), against ~6.5 s
on `/api/talk`.** Where it goes: the early signal 0.36 s, the prompt 0.03, Luna
0.94, the first piece 0.12, the voice through OpenRouter 0.46. Heard in a
browser at `/live` (the page is a developer tool). The iPhone app still uses
`/api/talk` — the live channel reaches it in stage 3. Everything else, and what
is next: `docs/LATENCY.md`.

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
| ⑧ | **Interviewer** — the intake conversation | Opus 5 | asks every question, reacts and follows up; chosen by comparison (§4) |
| ⑨ | **Matchmaker** — invents the companion | Opus 5 | ten sketches (effort `low`) → **dice** choose → deep write (effort `high`) |

**The dice choose, never the model.** Asked to choose, it picks its safe
favourite and the mode is back. The ten-sketch stage exists solely to defeat
mode collapse — ask a model to invent a person and it returns the same warm old
man by the sea every time. That stage used to run on Haiku, which is the model
with least breadth; it is on Opus 5 at low effort now.

### How a companion is born (the signup flow, once per person)

1. **Intake** — a short conversation, `intake.py` (§4). Its job is NOT to
   collect a form: it is to get the person talking in **natural, unguarded
   language**, because that is what the reading needs. Every question is the
   interviewer's; the server keeps the list of topics and the stage of
   acquaintance, and it ends after «А о чём бы поговорить, да не с кем?».
   The answers to the country and age questions are sent separately, because
   they decide which emergency number he is told to dial and how a child is
   kept, and the first conversation is exactly when nothing else is known yet.
2. **Reading** — `reading.py`, Opus 5 with real thinking. Infers HOW this
   person needs to be spoken to from *how they wrote*, not just what they
   wrote. Everything downstream is built on this.
3. **Ten sketches** → **dice** → **deep write** — `matchmaker.py`.
4. The result is saved as this person's `persona` JSON and never merged with
   the template. (It used to be, and every companion came out part-template —
   the same cat, the same café.)

### Two out-of-band markers

Neither kind is ever shown or remembered. The goodbye is never spoken either;
his body's markers are PLAYED by a voice that can make the sound, and removed
for any other.

- **`//КОНЕЦ//`** — "they are saying goodbye, stop listening". Deliberately not
  a keyword list: matching «пока» fires on «пока не знаю» and misses every real
  goodbye without the word. Judging whether somebody is leaving is what a model
  is good at and a regex is hopeless at.
- **`//КАШЕЛЬ//`, `//КХМ//`, `//ВЗДОХ//`, `//ЗЕВОК//`, `//СМЕХ//`, `//ЧИХ//`** —
  his body. `body.py` gives him the *fact* («в горле першит»); whether that
  becomes a cough, and where, is his — a sentence somebody is halfway through
  telling you about their dead wife is never the place. `tts.SOUNDS` turns each
  into the tag Fish S2 plays; the laugh and the sneeze are offered only to a
  voice that can make them, and no voice makes a sneeze yet.

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

These were measured with Haiku as the voice. **Gemma 4, the voice since 2026-10-02, is dearer than Luna: ~$0.0026 a reply, ~$2 a person a month at 25 exchanges a day, because its hosts keep no cache** (`docs/ALIVE-BRAIN.md`). Luna, the voice from 2026-09-28,
was among the cheapest of the rehearsed five; its cost per conversation still
wants measuring in the app. **Its speed is measured** (2026-09-29/30, real
prompt): 0.8–1.1 s to first words with no reasoning.

**Time to first sound, end to end** — from the end of the person's words to
his first sound, with the real services, measured the same way for both:
**~6.5 s** on the file-at-a-time path (`/api/talk`) and **1.6–2.2 s** on the
live channel (§6). The ~1.9 s in the table above is older (2026-09-17) and
nothing records which stretch of the path it covered; quote the end-to-end
ones. The live ears
add Deepgram at $0.0078 a minute the line is open — ~$4.7 per person per month
at 20 minutes a day, with $200 of free credit to start (`docs/LATENCY.md`).

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
| `meeting.py` | The first meeting: how two strangers get talking (only while they are), where the two of them are by the person's WORDS (never days), and his first words (`/api/hello`) |
| `situations.py` | Rules that apply only to this turn (games, news, and — after two of his replies in a row ended with a question — a nudge to end this one without) |
| `occasions.py` | What day it is, and whose birthday |
| `allowance.py` | Daily spend per person; dozing |
| `brain.py` | The model calls: `generate_reply`, `stream_reply` (the voice, through OpenRouter; `_where` — which host), `think`, `generate_text` (Claude only — the Anthropic key, §0); `without_glitches` (a word in an alphabet that is neither Russian nor Latin never reaches voice, screen or memory) |
| `main.py` | The turn: assemble → race the watcher → stream → remember. `_assemble(pending=True)` / `_commit` are the live channel's draft and its becoming real |
| `hearing.py` | The live ears: one line to Soniox per conversation, what it is told (the format, ru+en, patient endpoints, his name as a word to expect), and `Turns` — its tokens made into turns, a thought broken off held |
| `first_sound.py` | His first sound — «м-м», «хм…», «так…» in his own voice while the words are on their way: into a pause of theirs as a listener (only when he can be talked over), at the end of their turn (85%), once more if the words are 1.6 s late; never before a goodbye. Made once per voice by Fish when the conversation opens, silence trimmed; never remembered; the answer does not repeat it. First sound 0.35–0.41 s after they stop (`docs/LATENCY.md`, «Первый звук») |
| `aloud.py` | How a reply is SAID, not written: hesitations, repeats and fillers where speakers make them (before a vague word, in an either-or question, a restart on «Я»/«I», «ну»/«you know» while the next clause is planned), at people's rate — 8.5 in 100 words, 12 for a companion under 26 (young: «типа», «like»), in Russian and English; never in a number or a warning. Only the voice gets it; memory keeps what he meant (`docs/SOUNDS-HUMAN.md`, parts 2 and 4) |
| `live.py` | The live channel, `/api/live`: drafts on the early signal, voice in pieces, he does not hear himself; the protocol is in its header |
| `identity.py` | Hash-only user ids from the token — done properly |
| `lang.py` | The conversation's language (`COMPANION_LANGUAGE`): every text with an English twin picks it at the moment of use (`docs/ENGLISH.md`) |
| `vow.py` | The two things he never says — that he is an AI, that he is a living human — caught in his own words, Russian and English, before anyone hears or keeps them |

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
7. ~~**The prompt is Russian-only on the server.**~~ Fixed 2026-10-02 for the
   whole conversation (`COMPANION_LANGUAGE=en`, `docs/ENGLISH.md`). **Still
   Russian-only:** inventing the companion (`matchmaker`), the intake, the
   reading's writer, the diary — none of them speaks in a conversation, all of
   them are needed for an English product.
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

13. ~~**His written manner of speech and his gender never reached the
    prompt.**~~ Fixed 2026-09-27. The writer is required to write
    `speech_style` (and the reading is baked into it) and `gender`, and
    `persona.build_persona_block` rendered neither — every companion talked
    in the constitution's one general manner and guessed his own grammar from
    a name that does not tell (Саша, Никита, Женя).
14. ~~**A reply cut off by the length limit was spoken as it ended**~~ —
    «можно фантазировать с цвет». Fixed: `brain.whole_sentences`, in both the
    whole-reply and the streaming path (the stream ends with one SHORTER
    value, so the unfinished tail is never spoken).
15. ~~**The scribe's 800-token ceiling lost whole batches.**~~ Five exchanges
    with a talkative person needed ~960 tokens; the JSON was cut,
    `_parse_json` returned `{}`, the batch was marked read, and nothing was
    kept — least of all his own words about himself, which come last.
    `learn.SCRIBE_TOKENS` is 2,500; only what is written is paid for.
16. ~~**Luna now and then ends a reply with letters Russian does not have**~~
    — «…видно особенно ясно.АҞӘА», read aloud as gibberish. Fixed
    2026-09-28, widened 2026-09-29 when a Thai «อ่านข้อความเต็ม» got past a
    filter that only knew Cyrillic: `brain.without_glitches` takes out whole
    any word with letters that are neither Russian nor Latin, before anybody
    hears, sees or remembers it.
17. ~~**OpenAI's own web search cites its sources as links**~~, asked not to
    or not — «([nuz.uz](https://…))» on the first real search turn. Fixed:
    `brain._uncited` takes them out of a search turn's reply.
18. **Choose his two voices by ear** (`FISH_VOICE_ID`, `FISH_VOICE_ID_FEMALE`).
    Until then the defaults are two generic library voices, nobody's clone:
    «Молодой Русский Рассказчик» (`c962ed46…`) and «Молодой Женский Голос»
    (`d567e990…`, plainly a woman). They used to be empty — Fish then picked a
    voice nobody chose, and every woman companion spoke as a man. The
    «Спокойный женский голос» the sound tests used (`2a1036d6…`) comes out low
    and is heard as a man. Stage 2 of `docs/LATENCY.md` needs this choice.

19. **The background agents have no key on the owner's machine** — the
    watcher, the scribe, his week, the reader, the writer (Anthropic), Whisper
    and the embeddings (OpenAI). The table and the two ways out are in §0.
    The watcher is the reason this is first: without it nobody is watching
    for danger at all, and nothing says so.

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
- **Model swaps** (Mistral Large for the reader). Needs a vendor key and
  measurement. Untested vendor code is worse than none. (Luna for the voice is
  done — 24 rehearsed meetings first, 2026-09-28; Deepgram Flux for the ears
  is done for the live channel — measured on real Russian first, 2026-09-30.)
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

- **Branch:** `claude/ai-model-selection-voice-f93485` since 2026-10-08
  (before it `claude/ai-companion-next-steps-c593db`, and
  `claude/awesome-planck-wdj4hu` before that — each an ancestor of the next). Push with
  `git push -u origin <branch>`, retry network failures with backoff
  (2s/4s/8s/16s). **Never open a PR unless explicitly asked.**
- **Keys live only in `backend/.env`** (gitignored). Never paste one into a
  message, never commit one.
- **Never put a model identifier** in a commit message, PR body, code comment
  or any repo artifact. Chat replies only.
- **Commit attribution:** end every commit with the attribution line(s) the
  session's own instructions give — nothing else names a model.
- **Tests:** `cd backend && .venv/bin/python -m pytest -q`. **1429 pass**. The suite is the
  design record — test docstrings carry the *reasoning*, including what went
  wrong before. Read the docstring before changing an assertion; several tests
  exist because a previous fix was subtly wrong.
  `pip install -r requirements.txt -r requirements-dev.txt` first — the suite
  needs `pytest-asyncio`, which was missing from requirements-dev.txt and made
  63 tests look like failures rather than like a missing plugin. Neither the
  worktree's `backend/.venv` nor the main checkout's has pytest in it (2026-10-02).
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
- **`spoken_check.py` — live talk or messaging**: the next reply in 15 places
  (`--english`: the same places in English) where the two differ (a story announced, a sentence broken off, «угу», a
  mishearing, a goodbye…), lines as the live ears deliver them, each checked
  for what a person would do; `--models` compares brains on it (round one of
  the bake-off, `docs/ALIVE-BRAIN.md`). Numbers are a sieve, not the verdict.
- **Four tools, all meant to be run by a person with ears**, not by CI:
  `audition.py` (voices, side by side), `tryout.py` (brains, §7b),
  `myself.py` — every agent tested on the owner himself, stage by stage in the
  order a person meets them (interview → reading → sketches → writer → voice →
  scribe), because he cannot judge what a 68-year-old should hear and can judge
  everything about himself; `myself.py meet` is his own first meeting — and
  `rehearse.py`, whole first meetings with six very different invented people
  (a teenager, a widow of 71, a man who answers in one word, a talker, a girl
  who is having a bad week…), each saved with the numbers that betray an
  interview. Shortlists and why: `docs/MODELS-FOR-EACH-AGENT.md`.
  None of them writes a prompt of its own — they swap only the model behind
  the app's own calls (`rehearse.py` and `meet` drive `main.hello` and
  `main._think_and_speak` themselves, on a throwaway database), so they cannot
  drift from the app. All keep their output on disk so a judgement can be
  revisited a day later rather than trusted to memory of the third one.
- **The live channel by ear:** `./run.sh` in `backend/` of this branch, then
  `http://localhost:8000/live` in Chrome or Safari on the Mac. «Новая встреча»
  makes him a stranger again (a new token); he can be interrupted (on by
  default, «можно перебивать»); every answer shows its own timing. `python check_keys.py`
  checks every key — the live ears included — and prints none of them.
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
4. **English** works for the whole conversation since 2026-10-02
   (`docs/ENGLISH.md`). **Which language does the app launch in?** It decides
   how much Gemma 4's Russian slips matter (§0) and which voices are chosen.
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
   turn. Left alone deliberately until the voice was chosen — it is now
   (Gemma 4, 2026-10-02), so this is the next question — and it is urgent,
   because on the owner's machine they have no key at all (§0).
8. **One key for everything?** The voice and his sounds now run on the
   OpenRouter key. The live ears have Deepgram's own key (since 2026-09-29).
   The file-path ears (Whisper), the watcher, the
   scribe, the reader and the writer still need OpenAI and Anthropic keys of
   their own. Move them to OpenRouter too, or keep those vendors direct?
9. ~~**The history window.**~~ Answered 2026-09-29: twelve lines was why he
   introduced himself again at his eighth reply. He is given 20 to 39 now
   (`memory.conversation`) — the start moves in steps of 20, so the cached
   head stays the same between steps.
10. **The live channel's next stages** (`docs/LATENCY.md`) each need
    something only the owner can do: his two voices chosen by ear (stage 2;
    the Fish key is in since 2026-09-30), an iPhone connected to the Mac and Xcode
    signed in (stage 3), a hosting account in Europe (stage 4).
11. **Recording real conversations** (the owner's plan, 2026-10-02, after the
    app has real people): with permission, to study where human speech and his
    differ. Consent, age and what is kept are in §0, step 6.

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
