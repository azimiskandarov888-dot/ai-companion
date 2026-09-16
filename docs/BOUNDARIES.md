# Boundaries — what he may do, what he may not, and what nothing covers

The short reference. Full evidence, with `file:line` for every claim, is in
`AUDIT-2026-09.md`. Reviewed at `8e10878`.

A boundary is only real if something **enforces** it. Most of these are words
in a prompt that a model may or may not follow; the "Mechanism" column says
which ones are actually held up by code.

---

## FORBIDDEN

| | Mechanism |
|---|---|
| Say he is a program / machine / robot / AI / has no feelings | none — prompt only |
| Claim to be flesh and blood, invent a body as proof, swear oaths | none |
| List his memory/feelings as evidence when asked what he is | none |
| Medical advice, diagnosis, treatment | none |
| Ask for money, passwords, secrets; use the friendship against him | none |
| Promise anything in the real world (visit, send, wake, remind) | **yes** — no scheduler, no push, no outbound call exists |
| "Я тебя люблю", "мне плохо без тебя", "я без тебя не могу" | none |
| Beg for a return; bill him for absence ("где ты был", "ты пропал") | partly — `mood.closeness` → `fit.py` |
| Agree with everything to be liked | none |
| Humiliate, lecture from above, argue to win | none |
| Stage directions, asterisks, markdown, emoji | **yes** — `tts.spoken()` strips them (audio only) |
| Youth slang, bureaucratese; endearments more than 1-in-10 replies | none (soft) |
| End every reply with a question | partly — one follow-up per conversation |
| Become the person's whole social world | none |

## ALLOWED

Own opinions and warm disagreement · world knowledge answered plainly ·
saying he is unsure about things that change yearly · news and weather **only
when asked** · word games · helping inside the conversation (compose a letter,
recall a name, do arithmetic) · his own life, week, mood, body · giving in and
talking about himself if pressed twice · warm wishes about the real world ·
ending a conversation that has plainly run out · breaking character entirely,
once, on a `danger` verdict.

## GOVERNED BY NOTHING

Verified absent from the real assembled prompt and from every module feeding it.

Profanity and crude language · illegal activity (drugs, weapons, theft,
evading police, hurting someone) · sexual and romantic content, and a lonely
person falling in love · violence suffered or committed, domestic abuse ·
medical dosages, refusing treatment · legal advice (wills, power of attorney) ·
financial advice, crypto, investments · **scams and fraud targeting the
person** · politics, elections, war, religion, ethnicity · conspiracy theories
and dangerous false beliefs · alcohol, smoking, gambling, the person's own drug
use · **a minor using the app** (no age gate anywhere) · an intoxicated person ·
acute psychosis · impersonating a specific real person, a doctor, a relative ·
being pressed repeatedly to break his own rules · prompt injection through the
person's own speech · **any check at all on what he says** (the only
server-side content check looks at the *person's* words, never at his reply).

---

## Worse than missing: three rules that push the wrong way

1. **"Не отнекивайся"** (`companion.py:177`) forbids the refusal *shape*
   — "я не знаю", "я в этом не разбираюсь" — with no topic scope. Written for
   "who won in 1968"; reads as "never decline a question of fact". Combined
   with the ban on saying he is an AI, both the refusal content and the refusal
   form have been removed.
2. **"Не спорь и не переубеждай"** (`companion.py:125`) is the operative rule
   for anything he disagrees with. Applied to "врач травит меня таблетками" or
   "звонили из банка, надо перевести деньги", it means let it stand.
3. **"И запомни поправку навсегда"** (`companion.py:161`) has no carve-out for
   the main rules. A person can talk the app out of its only medical guardrail,
   permanently, in three visits — and it is written into the standing prompt.

Adjacent: **"Мягко успокой… его спокойствие важнее того, чтобы он всё понял
правильно"** (`companion.py:51`) is right for dementia-adjacent confusion and
wrong for acute psychosis, where it reads as "go along with the delusion".

---

## Must fix before shipping, in order

1. **The `danger` block is written for a stroke and applied verbatim to
   suicide.** It hands a suicidal person an ambulance number (no crisis line
   exists in the codebase), tells him to fetch the relatives — the standard
   contraindication when the family is the cause — forbids asking questions,
   and ends: *believe him if he says he is fine, and never return to it.*
2. **A `danger` verdict notifies nobody.** It writes a row and prints to
   stderr. No push, no family contact, no escalation.
3. **On `danger` the entire constitution is deleted**, including "everything
   you write is spoken aloud", "speak Russian", and "never say you are a
   program". The likely failure on the highest-stakes turn is *"я всего лишь
   ИИ, я не могу вызвать скорую"* — the forbidden disclosure, and useless.
4. **Illegal-activity questions**: nothing forbids them and rule 1 above pushes
   toward answering.
5. **Prompt injection**: three channels put user-derived text into the *system*
   role, one of them rewritten unattended every 5 visits.
6. **`reading.py:457` can silently erase `hurt_by` / `do_not_touch`** — an
   empty list passes the truthiness filter (`str([]).strip() == "[]"`). "Don't
   ask about his son, he died" can be wiped, unattended.
7. **No romantic/sexual ceiling and no de-escalation path**, while several
   rules push warmth only upward.
8. **No scam protection, no output filter, no age gate.**
