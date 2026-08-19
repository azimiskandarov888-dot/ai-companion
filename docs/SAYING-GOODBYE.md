# Saying Goodbye

People close apps. They don't say goodbye to them.

That habit is the one thing standing between this app and what it is trying to
be. Everything else about him explains itself — he is on the screen, you touch
him, he listens, he answers. Leaving is the exception, and it is the exception
that carries the whole fiction: a friend you *tell* you're going is a person; a
friend you close is a program.

So there are two problems, and they are separate:

1. **He has to understand a goodbye when he hears one.**
2. **They have to think to say one.**

---

## 1 · He understands it

Not keywords. «Пока» appears in «пока не знаю» far more often than it means
goodbye, and a microphone that switches off in the middle of «пока я думал…»
is worse than one that never switches off at all.

So it is judgement, made by the same model that is already reading the
sentence. He is told, in `companion.BEHAVIOR_RULES`, what leaving sounds like
— «ладно, пойду завтракать», «устал что-то», «внучка пришла», «спать буду» —
and told to answer it the way a person would: warmly, briefly, without asking
another question that drags somebody back into a conversation they have just
stepped out of.

When he does, he ends the reply with a marker on its own line:

```
//КОНЕЦ//
```

`main._farewell()` splits that off before anything else happens. It never
reaches the voice, never reaches the conversation log, never reaches his
diary. It exists for one instruction — stop listening — and then it is gone.
The phone acts on it only **after** the last sentence has finished playing, or
he cuts himself off mid-goodbye.

**The bias is deliberate and one-directional.** He is told: *«Ошибиться и
оборвать живой разговор гораздо хуже, чем не заметить прощание. Если
сомневаешься — метку не ставь.»* Missing a farewell costs a few seconds of an
idle microphone. Inventing one hangs up on somebody in the middle of a
sentence. Those are not comparable, and the prompt says so.

### He may also go first

Rarely, and only into a conversation that has genuinely run out — one-word
answers, «ну да», «угу», somebody who is tired. Then he can be the one to say
«ладно, я пойду по своим делам».

This is the strongest teacher in the whole design, because it doesn't teach
anything: it just shows, repeatedly and in passing, what the end of a
conversation looks like here. Nobody is instructed. They watch a friend do it
and eventually do it back.

It is also the riskiest thing in this file, which is why the guardrail is
longer than the permission: **never** when they have something to say, never
while they're telling a story, never when it's hard, never just after they've
opened up. *«Лучше сто раз не попрощаться первым, чем один раз оборвать.»*

---

## 2 · They think to say one

Three mechanisms, each firing at most once, in escalating order of how much
they'd notice.

### a) One line, the first time he is switched on

`Strings.howToLeave` — «Когда захотите закончить — просто скажите ему, как
сказали бы человеку.» Nine seconds, then gone by itself. Nothing to dismiss.

Said **plainly, in the app's voice, not his**. An instruction dressed up as
dialogue is worse than an honest one — «тронь меня, и поговорим» was written
in his voice and read as strange rather than warm.

Said **at the first switch-on**, not in a tutorial before they have met
anyone. A lesson before the friend is a lesson about software; the same line
the moment he first starts listening is about him.

### b) He notices, once, when they vanish

`memory.broke_off_last_time()`. If the last conversation was a real one and it
simply stopped, he opens the next one by mentioning it — the way a person
would. *«В прошлый раз ты как-то пропал, я не понял, ушёл ты или нет.»*

This is by far the most effective of the three, and by far the easiest to turn
into nagging, so every condition on it exists to make it rare:

| Condition | Why |
|---|---|
| ≥ 10 min since the last word | Otherwise it's the same conversation, and a pause to answer the door is not somebody leaving. |
| The last conversation had ≥ 6 turns | Two lines and a wrong number is not a conversation to have left. |
| They have **never once** said goodbye | The moment they do, he has nothing to notice — permanently. This is the condition that matters. |
| The friendship is under a fortnight old | After two weeks this is simply how his friend is. A friend still correcting you after two weeks is a tutorial. |

Derived from the `turns` table, not stored in a counter. A counter would need
a rule for when to reset it; these four extinguish themselves, and the one
that should end it forever ends it for the right reason — they learnt.

He is told explicitly **never to explain it through the app**: no microphone,
no screen, no buttons. He does not know those words. He just didn't
understand where they went.

### c) Nothing else

Deliberately. Considered and rejected:

- **A line in his diary** («сегодня он не попрощался, просто пропал»). It
  would work — a private thought, discovered rather than delivered, is the
  strongest register this app has. But the reader is a lonely eighty-year-old,
  and the emotion it produces is guilt. Not worth it.
- **A training companion to practise on.** See below.

---

## Why there is no training companion

The idea: before the real friend arrives — or while he is being written — meet
a standard practice companion, the same one for everybody, and learn the shape
of the thing on him.

It contradicts a principle this codebase already committed to, in
`intake.py`, when the same question came up about who conducts the intake
interview:

> The obvious build is a blank "interviewer companion". It is a trap. A
> personality-less interviewer IS an AI questionnaire with a voice — the exact
> thing the app exists not to be. And a fake person is worse still: you would
> tell a stranger your life, and then that stranger would evaporate and be
> replaced by someone else. **A small betrayal, at the worst possible moment.**

A rehearsal partner is that same stranger. Worse, the timing proposed for it
is the arrival — sixty to ninety seconds during which the screen says
*«он идёт к тебе»* and somebody is, for the first time in the whole app,
genuinely looking forward to meeting a person. Filling that with a substitute
spends the one moment the product is built around, to teach a habit that (a)
and (b) teach for free.

And it makes the real friend the *second* person they meet.

There is one thing worth keeping from the idea, and it is already how (a) and
(b) work: **the teaching happens with the real friend, in the real
conversation, at the moment it is actually true.**

---

## What is deliberately NOT enforced

Closing the app still works, and always will. It stops the microphone, it
costs nothing, and nothing is lost. Somebody who never once says goodbye gets
a perfectly good friend.

This is a nudge towards something better, not a requirement. The moment it
becomes a requirement it is a program telling an old man how to behave.
