# Many people, one server

> *"I started it on the new iPhone, but it's still the same companion that I
> had on my phone. Even after writing an absolutely new story about the
> client. It was even continuing our conversation from where we stopped last
> time."*

That is not a bug report about a screen. It is a report that one person was
reading another person's friend, and their conversation, and their memories.
The app is for lonely people; the entire content of it is somebody's inner
life. Getting this wrong is the worst thing this codebase can do.

This document is what was wrong, what the shape of the fix is, and the rules
that keep it fixed.

---

## What was actually wrong

Four separate things, none of which looked like a bug with one user:

| | Before | Now |
|---|---|---|
| The friend | one `data/persona.json` on the server | `data/users/<id>/persona.json` |
| The reading | one `data/reading.json` | `data/users/<id>/reading.json` |
| Memory | `memories` had no column for whose | `user_id` on every row, on every query |
| The conversation | `turns.session_id`, sent by the client as the literal string `"default"` | `turns.user_id`, derived server-side from the token |
| The diary | one row, pinned by `CHECK (id = 1)` | `user_id PRIMARY KEY` — one book each |
| The daily allowance | keyed by a client-chosen string | keyed by the person |
| «Начать заново» | `DELETE FROM turns` — no `WHERE` | `WHERE user_id=?` |
| `/api/memory` | `SELECT * FROM memories` — no `WHERE` | scoped to the caller |

The last two deserve naming. One person meeting a new friend wiped **every
conversation on the server**. And a single unauthenticated `GET /api/memory`
returned **everybody's** distilled private life.

---

## The identity

A phone makes 32 random bytes once, keeps them in the Keychain, and sends
them on every request:

```
Authorization: Bearer <token>
```

The server hashes it — `sha256(token)[:32]` — and that hash is the person.
No login, no password, no account server, nothing to remember.

Four properties, each load-bearing:

1. **Unguessable.** 256 bits from the OS CSPRNG. Nobody enumerates their way
   to somebody else's friend.
2. **The database never holds the token.** Only the hash. A stolen database
   yields opaque ids and no usable credentials; the id cannot be turned back
   into a token.
3. **It travels in a header, never a URL.** Query strings end up in access
   logs, proxy logs and browser history. `Authorization` headers don't. There
   is no `?user=` anywhere in this codebase, and the old `session_id` body
   field is gone.
4. **The caller cannot choose who they are.** Identity enters the server in
   exactly one place — the `_user` dependency in `main.py` — and never from a
   body, form, or query string. An identity the caller picks is an identity
   anyone can borrow.

### Why no accounts

The people this is for cannot be asked to remember a password, and every
account screen is a place to give up at. The token *is* the identity and *is*
the credential — a capability: whoever holds it is that person.

The honest cost: lose the phone and the Keychain, lose the friend. The
Keychain item is stored `AfterFirstUnlock` and **not** `ThisDeviceOnly`, so it
survives an encrypted backup and comes back on a restored iPhone. When real
accounts arrive (Sign in with Apple) they slot in *above* this: the account
becomes a way to recover the token, and everything below keeps working
unchanged.

### Why iCloud Keychain sync is deliberately OFF

Syncing would carry the friend to a new phone automatically, which is
lovely — and wrong here. Among the people this app is for, a son setting up
both parents' phones with **his own Apple ID** is completely ordinary. Sync
would hand those two phones one shared friend: the exact bug this token
exists to end. (`AppConfig.swift`)

### A damaged token is never the anonymous one

Only a request with **no** token at all is anonymous. Anything else — even a
token truncated in transit — is hashed into its own bucket.

That asymmetry is a privacy rule. The anonymous bucket is not empty: it holds
the data from before multi-user existed, i.e. one real person's life. A
"this doesn't look valid, fall back to anonymous" branch would hand that
person's memories to whoever's request got mangled. Falling into your own
empty bucket means meeting a new friend — sad, private, recoverable. Falling
into theirs means reading a stranger's diary.

---

## The rule that keeps it fixed

**Every function that touches a person's life takes `user_id` first, and none
of them has a default for it.**

That is the whole safety model, and it is worth more than any amount of
care. A default of `"default"` would make every forgotten call site a privacy
bug that never raises — silently reading somebody else's memories, forever,
with no symptom. Required arguments turn the same mistake into a `TypeError`
the first time the code runs.

When this landed, 32 tests failed instantly with `missing 1 required
positional argument`. Every one was a real call site that would otherwise
have leaked.

Do not add a default to `memory.add_memory`, `facts_context`, `log_turn`,
`persona.load_persona`, `reading.save`, `diary.get_diary`, or anything like
them. The inconvenience is the feature.

---

## Migration: nobody loses a friend

`db.init_db()` runs on every server start and upgrades an older database in
place. It is idempotent and lossless:

- `memories` gains `user_id`, defaulting to `'default'`.
- `turns.session_id` and `usage.session_id` are **renamed** to `user_id` —
  the values were already right (every device sent `"default"`), and the
  rename makes it impossible to keep believing this id comes from the client.
- `diary` cannot be altered in place (its primary key was `CHECK (id = 1)`),
  so it is rebuilt and the existing book handed to `'default'`.

Everything that existed before multi-user belonged to one person, so it all
lands under the anonymous id — which is exactly what that person's phone
keeps sending until it gets the build with the token in it. Their friend,
their conversation, their diary and their spent allowance all survive.

`tests/test_db.py` builds the real prior schemas by hand and runs the upgrade
over them, because the only database that has ever held a real person's life
is one of those.

---

## Cost, which is a multi-user problem

With one user it did not matter that `/api/companion/create` was unmetered.
It runs the deepest model in the app with real thinking time, then two more
calls. On a shared server an unmetered paid endpoint is a bill anyone can run
up.

So both paid entry points are now counted against the caller's daily
allowance, the same meter the conversation uses:

- `/api/companion/create` — refuses with 429 when the person has nothing left
  today, spends the real elapsed time otherwise.
- `/api/intake/next` — ends the conversation kindly (`enough: true`) rather
  than erroring; whatever they've already said is enough to build a friend
  from.

Every free-text field that reaches a model also has a length cap. The numbers
are far past anything the app itself can produce, so no real person meets
one.

---

## Performance

Every index leads with `user_id`:

```sql
CREATE INDEX idx_turns_user            ON turns(user_id, id);
CREATE INDEX idx_memories_user_owner_kind   ON memories(user_id, owner, kind, status);
CREATE INDEX idx_memories_user_owner_created ON memories(user_id, owner, created_ts);
```

Nothing is ever read across users, so a user-first index turns every lookup
into a scan of one person's rows — which is what keeps a server with many
people on it as fast as the server that had one.

SQLite runs in WAL with `synchronous=NORMAL` and a 30-second busy timeout:
readers never block the writer, the writer never blocks readers, and a spoken
turn doesn't wait on an fsync. The alternative, with several people talking
at once, is «database is locked» in the middle of somebody's sentence.

The diary's fingerprint is computed over **that person's** memory rows only.
Computed globally, every book on the server would go stale the moment anyone
else spoke, and each would be rewritten — a paid model call — on next open.

---

## Checking it

`backend/tests/test_multiuser.py` is written entirely from the outside,
through HTTP, with nothing but a bearer token to tell two callers apart —
because that is all the server gets, and a test that reaches past the
endpoint proves nothing about what a phone actually experiences.

It pins: two phones meet two different friends; a fresh phone starts with
nobody; conversations never cross; starting over touches only that person;
the memory dump and the diary and the allowance are each per-person; identity
cannot be chosen by the caller; and a build that predates the token still
finds its friend.
