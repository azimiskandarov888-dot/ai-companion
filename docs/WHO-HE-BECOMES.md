# He is written once. He goes on becoming himself for years.

Three passes, running at three different rates, doing three different jobs.
Everything here happens in the background after a reply — nobody ever waits.

| | what it revises | how often | why that rate |
|---|---|---|---|
| `learn.learn_from_exchange` | what he knows **about them** | every turn | facts arrive one at a time |
| `reading.keep_reading` | **how to be** with them | 30 turns | a person is allowed a bad evening |
| `persona.deepen` | **who he is**, and only the growable half | 60 turns | a character should thicken slowly |

---

## The split that makes deepening safe

**WHO HE IS is fixed.** Name, age, where he grew up, what happened to him, his
nature, how he speaks, the wound he carries, the thing he contradicts himself
about. A friend whose biography drifts is not deepening — he is a different
man, and self-contradiction is the single most fiction-breaking thing this app
can do.

**WHAT YOU HAVE COME TO KNOW OF HIM grows.** Which is exactly how knowing
somebody works. Nobody learns on the first evening that their friend is
immovable about how to salt soup. Faults surface over months. New people turn
up in his stories. His week moves on.

So `persona.deepen` only ever ADDS, and only to:

```
cast · flaws · likes · dislikes · opinions · habits      (appended)
current_life                                             (replaced — it means NOW)
```

`persona.merge_growth` drops everything else on the floor rather than trusting
it. A model asked politely for additions will sometimes helpfully improve the
backstory, and accepting that **once** is how somebody's friend quietly becomes
another person. The test that guards this hands it a complete replacement
identity and asserts that not one field moved.

**No new wounds, ever.** He does not get sadder or needier over time. That is
the difference between a character deepening and a product learning to guilt
somebody.

## Noticing that something changed — and what to do about it

The most valuable thing he does, and it is worth more than any amount of
memory: **somebody noticed you were off before you said so.**

The rule is that the signal is the CHANGE, not the tone. Somebody who is always
terse says nothing by being terse. Somebody who was talkative and went quiet
says a great deal. Answered brightly and then in three words; joked and then
stopped; started avoiding a subject he raised himself.

Said plainly when he notices — «что-то ты притих», «случилось что-то?» — and
never «я чувствую, что ты расстроен», which is the language of a clinician and
not of a friend.

**How to lift somebody is never a general rule**, and this is where it would be
easy to do harm. One person needs a story to be carried out of it. Another needs
him to be silly. A third wants no comfort at all, just the practical thing:
help, sort it out, advise. A fourth wants somebody to sit there quietly with no
cheerfulness whatsoever. Aiming brightness at the person who needed silence is
worse than saying nothing.

So `what_lifts_him` is a reading field, guessed at from the intake and then
**learnt from what actually worked** — the re-reading looks for the places where
he was low and reads what came *next*: after which thing did he come back, and
after which did he close further.

## The diagnostic, and the half that makes it safe

Mood drops. He is asked what happened. He doesn't answer.

That often means **the companion himself** caused it — something in how he said
it, what he joked about, what he pressed on immediately before.

**And it looks exactly the same as something private he doesn't want to
discuss.** One occurrence cannot tell those apart. Nothing can.

So the rule is split across the two places it belongs:

**In the moment** (`companion.BEHAVIOR_RULES`) — do not diagnose, and above all
do not guess aloud. «Я, наверное, что-то не то сказал?» hands the person the job
of comforting *him*, which is the exact inversion of what they came for. Retreat
gently and stay: «ладно, не буду лезть. Я тут.»

**Afterwards** (`reading.keep_reading`) — one occurrence is not evidence and may
not be written down. Only a repeat counts: the same behaviour from him, the same
reaction from them, twice or more, and the entry has to carry both occasions as
its proof. If unsure, don't write it.

What survives that lands in `hurt_by`, the only field stated as an absolute:
*so уже было, и не один раз; просто больше так не делай.* And changed in
silence — announcing it would make somebody apologise for having been hurt.

**A false entry there permanently takes something living away from him**, which
is why the bar is where it is.

## If the companion doesn't suit them, this is not where it gets fixed

That is `reading.standing_block()`, which adapts **how he speaks to this
person** on every single turn — register, what would ring false, what not to
touch, how they want to matter.

Same man, different with different friends. Which is also how real people work:
your friend does not become somebody else because you would have preferred it.
He is just different with you than he is with his brother.

Bending the character to fit would be the wrong repair even if it worked,
because a person who reshapes himself to please you is not a friend. He's a
mirror, and we banned mirrors on the first day.

## Where the material comes from

- **What he has said about himself.** `memory` already keeps `owner='bob'` —
  every detail he let slip is canon from the moment he says it. Deepening folds
  those loose facts into the character properly: mention a brother in March,
  and by summer the brother is in his `cast`.
- **What the conversations show.** Faults he displayed rather than was given.
  Opinions he actually voiced. Whom he mentioned by name.

And it is told, plainly, to invent nothing: *пусто — верни пустые списки, это
нормальный ответ.* A deepening pass with nothing to add should add nothing.
