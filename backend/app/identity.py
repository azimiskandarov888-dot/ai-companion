"""Who is talking — the one question the whole server used to have no answer to.

Everything was single-user by construction: one `persona.json`, one diary row
pinned with `CHECK (id = 1)`, memory tables with no column for whose memory it
was, and a session id that was the literal string "default" on every device.
Two phones pointed at one backend didn't get two friends — they got the same
friend, mid-conversation, each believing the other's history was its own.

── THE IDENTITY ────────────────────────────────────────────────────────────

A phone generates 32 random bytes once, keeps them in the Keychain (which
survives deleting the app), and sends them on every request:

    Authorization: Bearer <token>

There is no login, no password, no account server, and nothing to remember.
The token IS the identity and IS the credential — a capability: whoever holds
it is that person, and nobody else can be.

Three properties make that safe enough to put a lonely person's inner life
behind, and each of them is load-bearing:

1. UNGUESSABLE. 256 bits from the OS CSPRNG. There is no enumerating your way
   to somebody else's friend.

2. THE DATABASE NEVER HOLDS THE TOKEN. Everything is keyed by
   sha256(token) — so a stolen database yields no usable credentials, only
   opaque ids. The user id cannot be turned back into a token.

3. IT TRAVELS IN A HEADER, NEVER A URL. Query strings end up in access logs,
   proxy logs and browser history; `Authorization` headers do not. This is
   why there is no `?user=` anywhere in this codebase.

── WHY A BAD TOKEN IS NEVER THE ANONYMOUS ONE ──────────────────────────────

Only a request carrying NO token at all is anonymous. Anything else — even a
token that got truncated, mangled by a proxy, or typed by hand — is hashed
into its own bucket.

That asymmetry is deliberate and it is a privacy rule, not a nicety. The
anonymous bucket is not empty: it holds the data from before multi-user
existed, i.e. one real person's life. A "this doesn't look like a valid
token, fall back to anonymous" branch would hand that person's memories to
whoever's token got damaged in transit. Falling into your own empty bucket
means meeting a new friend — sad, recoverable, private. Falling into the
anonymous one means reading a stranger's diary. Only one of those is a bug we
can live with.

── WHAT THIS IS NOT ────────────────────────────────────────────────────────

It is not authentication in the sense of proving who someone is — it proves
only that this caller holds this token. For an app whose entire content is
"your own friend and your own memories", that is exactly the right shape:
there is nothing to gain by being someone else except their private life, and
the token is the only key to it. Losing the phone AND the Keychain loses the
friend, which is the honest trade for having no accounts.

When real accounts arrive (sign in with Apple), they slot in above this: the
account becomes a way to RECOVER the token, and everything below keeps
working unchanged.
"""

from __future__ import annotations

import hashlib
import re

from . import config

#: The single-user era. Requests with no token — the browser dev page, older
#: builds of the app, curl — land here, and inherit the data that already
#: existed before any of this. Keeping it is what makes the migration
#: invisible rather than a wipe.
ANONYMOUS = "default"

#: A real user id is 32 lowercase hex characters. It can therefore never
#: collide with ANONYMOUS, and never contain a path separator, a dot, or
#: anything else that means something to a filesystem.
_SAFE_ID = re.compile(r"^[a-f0-9]{32}$")

#: sha256 gives 64 hex chars; 32 of them is 128 bits of the digest. Far beyond
#: any collision concern (birthday bound ~2^64) and short enough to read in a
#: log line when something needs debugging.
_ID_LEN = 32


def user_id_from_token(token: str | None) -> str:
    """The stable, filesystem-safe id for whoever holds this token.

    The same token always gives the same id; the id can never be turned back
    into the token. Nothing here raises — a person mid-conversation should
    never meet an auth error, and the app has no screen that could show one.
    The failure mode is "you look like a new person", never a 401.

    Accepts the raw header value, so `Authorization: Bearer <token>` and a
    bare token both work.
    """
    raw = (token or "").strip()
    # Split the scheme off rather than matching a "bearer " prefix: the header
    # has already been stripped, so an empty credential arrives as the bare
    # word "Bearer" with no trailing space, and a prefix match would miss it
    # and hash the scheme name itself into a perfectly valid user.
    scheme, _, rest = raw.partition(" ")
    if scheme.lower() == "bearer":
        raw = rest.strip()
    if not raw:
        return ANONYMOUS
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:_ID_LEN]


def is_anonymous(user_id: str) -> bool:
    return user_id == ANONYMOUS


def user_dir(user_id: str, create: bool = False):
    """Where this person's files live — their friend, and the reading of them.

    Kept as files rather than blobs in the database on purpose: `persona.json`
    is meant to be openable and editable by a family who wants to correct
    something, and that has been true since the first version.

    Nothing is created unless `create=True`. Reading a path must never leave a
    directory behind, or every stray request would litter the disk with empty
    folders — and the writers (`persona.save_persona`, `reading.save`) create
    their own parents anyway.
    """
    # Belt and braces: a user id only ever comes from the hash above, but this
    # value becomes a directory name, and a directory name built from request
    # data gets checked. Anything unexpected is treated as no id at all.
    safe = user_id if _SAFE_ID.fullmatch(user_id or "") else ANONYMOUS
    # The pre-multi-user layout put persona.json straight in data/. Leaving
    # the anonymous user there means every existing install keeps its friend
    # without a migration step that could lose one.
    path = config.DATA_DIR if safe == ANONYMOUS else config.DATA_DIR / "users" / safe
    if create:
        path.mkdir(parents=True, exist_ok=True)
    return path


def persona_path(user_id: str):
    """The friend this person met. One file per person."""
    if is_anonymous(user_id):
        return config.PERSONA_PATH
    return user_dir(user_id) / "persona.json"


def reading_path(user_id: str):
    """The reading of this person. Outlives any one companion."""
    if is_anonymous(user_id):
        return config.READING_PATH
    return user_dir(user_id) / "reading.json"
