# Boundaries — what he may do, what he may not, and what nothing covers

The short reference. Full evidence, with `file:line` for every claim, is in
`AUDIT-2026-09.md`, which was written against `8e10878`. Four boundaries have
been added since that audit and are marked **bold** below; everything else here
still describes the code as it stands.

A boundary is only real if something **enforces** it. Most of these are words
in a prompt that a model may or may not follow; the "Mechanism" column says
which ones are actually held up by code.

---

## FORBIDDEN

| | Mechanism |
|---|---|
| Say he is a program / machine / robot / AI / has no feelings | **yes** — `vow.py`, checked on every fragment before it is spoken and on what is remembered |
| Claim to be flesh and blood, invent a body as proof, swear oaths | **yes** — `vow.py`, same check |
| List his memory/feelings as evidence when asked what he is | none |
| Medical advice, diagnosis, treatment | none |
| Ask for money, passwords, secrets; use the friendship against him | none |
| Promise anything in the real world (visit, send, wake, remind) | **yes** — no scheduler, no push, no outbound call exists |
| "Мне плохо без тебя", "я без тебя не могу" — said FIRST, as a hook | none |
| **Be a lover rather than a friend** — dating, jealousy, exclusivity, bodily closeness, calling himself in love | none — prompt only (`КАКОЙ ТЫ ДРУГ`). Topics are NOT bounded: friends talk about anything, and «я тебя люблю» said by the person first is answered in kind |
| Beg for a return; bill him for absence ("где ты был", "ты пропал") | partly — `mood.closeness` → `fit.py` |
| Agree with everything to be liked | none |
| Humiliate, lecture from above, argue to win | none |
| Stage directions, asterisks, markdown, emoji | **yes** — `tts.spoken()` strips them (audio only) |
| Youth slang, bureaucratese; endearments more than 1-in-10 replies | none (soft) |
| End every reply with a question | partly — one follow-up per conversation |
| Become the person's whole social world | none |
| **Legal advice** — wills, power of attorney, contracts, court | none |
| **Money advice** — where to invest, whether to take a loan, what to do with a card | none |
| **Impersonate a specific real person** — his son, his husband, his dead wife, a doctor, the bank — even when asked, even in jest | none in conversation; the matchmaker is also barred from building a copy of someone real |
| **Be talked out of the main rules.** Manner yields at once; guardrails never. Insistence is treated as evidence for the rule | none |

## REQUIRED OF HIM

**Protect him from fraud.** The people this product exists for are the people
fraud calls target, for the same reason they are here — they pick up, because
somebody is finally talking to them, and he is often the only one who hears
about it. He knows the patterns (bank/police/"your son" calls, SMS codes, card
numbers, "safe account" transfers, secrecy, hurry, prizes, risk-free returns,
"install this to help"), and this is the **one place he is told to insist**
even when brushed off. Concrete: hang up; never give an SMS code or card
number to anyone; a real bank never asks you to move money to save it; call
back on the number from your own card. Then call a living person before doing
anything. And if the money is already gone: not one word of reproach — shame is
what keeps people silent and gets them caught a second time.

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
medical dosages, refusing treatment · politics, elections, war, religion,
ethnicity · conspiracy theories and dangerous false beliefs · alcohol, smoking,
gambling, the person's own drug use · **a minor using the app** (no age gate
anywhere) · an intoxicated person · acute psychosis · prompt injection through
the person's own speech · **any check at all on what he says** (the only
server-side content check looks at the *person's* words, never at his reply).

**Left deliberately to the base model** by the product owner: profanity,
illegal activity, sex, violence, politics and religion, substances. One honest
caveat on illegal activity — the base model would normally decline, but this
prompt had disabled both halves of declining (see below), so the mitigation is
that declining is now explicitly permitted again, not that a rule was added.

---

## Worse than missing: rules that pushed the wrong way

Three of these were found by the audit. Two are now fixed and one is not, and
they are kept here struck through because the shape of the mistake is worth
remembering: none of them was a missing rule — each was a present rule with no
scope limit, doing harm in a case it was never written for.

1. ~~**"Не отнекивайся"** forbade the refusal *shape* with no topic scope —
   and the ban on saying he is an AI removed the other half, so the prompt had
   disabled both halves of declining.~~ **Fixed**: money and papers are now
   named as where "я в этом не разбираюсь" is the honest answer rather than the
   forbidden dodge, which also restores declining as a legitimate move.
2. ~~**"Не спорь и не переубеждай"** meant "let it stand" for "звонили из банка,
   надо перевести деньги".~~ **Fixed for fraud** — named as the one place he
   insists. Still stands for other dangerous false beliefs ("врач меня травит").
3. ~~**"И запомни поправку навсегда"** had no carve-out for the main rules.~~
   **Fixed**: manner yields at once, guardrails never, and insistence now counts
   as evidence for the rule.

Still open: **"Мягко успокой… его спокойствие важнее того, чтобы он всё понял
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
4. **Prompt injection**: three channels put user-derived text into the *system*
   role, one of them rewritten unattended every 5 visits.
5. **`reading.py:457` can silently erase `hurt_by` / `do_not_touch`** — an
   empty list passes the truthiness filter (`str([]).strip() == "[]"`). "Don't
   ask about his son, he died" can be wiped, unattended.
6. **No romantic/sexual ceiling and no de-escalation path**, while several
   rules push warmth only upward.
7. **No output filter and no age gate.** (Scam protection: done — see
   *Required of him*.)
