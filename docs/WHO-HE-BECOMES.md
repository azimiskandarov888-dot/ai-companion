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
