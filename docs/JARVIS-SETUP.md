# Claude drives the browser

The art loop today is: Claude writes a prompt → you copy it → you open the
generator → you save the PNG → you rename it → you drop it in `assets/raw/` →
you tell Claude it's there. Seven steps, six of them yours.

This document is how to delete your six. It is also honest about which one step
should never be automated, and why.

---

## The thing that has to be true first

**Claude Code has to be running on your machine.** Not in a browser tab, not on
a server somewhere. The session you are reading this from runs in a container in
a datacentre — it has no screen, no Chrome, no access to your desktop, and it
cannot get any. Nothing described below works from there.

So: install Claude Code locally, open this repo in it, and everything on this
page is available in about two minutes.

```bash
# on the Mac (or the PC)
npm install -g @anthropic-ai/claude-code
cd path/to/ai-companion
claude
```

The `.mcp.json` and `.claude/settings.json` in this repo are already written.
Claude Code will ask once, on first start, whether to trust the MCP server in
this project. Say yes. That is the whole install.

---

## The three ways, and which one to pick

| | what it is | you watch | logins |
|---|---|---|---|
| **Playwright MCP** ← *this repo uses this* | Claude launches its own Chrome window and drives it | a real window on your screen | its own profile — log in by hand once, it sticks |
| **Chrome DevTools MCP** | Claude attaches to the Chrome you already have open | your actual browser, your actual tabs | already logged in everywhere |
| **Claude in Chrome** | Anthropic's extension, Claude works inside your browser | your actual browser | already logged in everywhere |

Playwright MCP is the default here for one reason: **a separate window is
safer.** Claude clicking around in the browser that holds your bank tabs, your
Apple Developer session and your email is a different risk than Claude clicking
around in a window that only ever had one site open in it. The separate profile
costs you one manual login per site, once, ever.

Switch to Chrome DevTools MCP if that trade stops being worth it:

```jsonc
// .mcp.json — the alternative
{
  "mcpServers": {
    "browser": {
      "command": "npx",
      "args": ["-y", "chrome-devtools-mcp@latest", "--browserUrl=http://127.0.0.1:9222"]
    }
  }
}
```

…having started Chrome yourself with `--remote-debugging-port=9222`.

---

## What you actually see

Headed is the default — there is no `--headless` in `.mcp.json`, and that is
deliberate. When Claude does anything with the browser:

1. A Chrome window opens on your screen and stays open.
2. You watch the cursor move, the fields fill, the pages load. Real time, real
   speed, nothing sped up or replayed.
3. In the terminal, every single action is printed before it happens —
   `browser_click`, `browser_type`, the URL, the element.
4. Anything that changes state on a website stops and asks you first. You press
   `y` or `n`. Nothing happens until you do.

Point 4 is the part worth understanding properly, so it has its own section.

---

## Permission — three lists

`.claude/settings.json` sorts every browser action into one of three buckets.

| bucket | what's in it | what happens |
|---|---|---|
| `allow` | navigate, screenshot, read the page, read the console | runs silently |
| `ask` | click, type, fill a form, upload a file, run JavaScript | **stops and asks, every time** |
| `deny` | reading `.env`, anything matching a secrets filename | refused, no prompt, no override |

Reading is free. Writing asks. Secrets are walled off even from Claude itself,
which matters here because `backend/.env` holds the Anthropic, OpenAI and Fish
Audio keys.

If you get tired of approving the same click twenty times in one session, press
`Shift+Tab` to cycle the session into accept-edits mode, or add the specific
tool to `allow`. Don't run `--dangerously-skip-permissions` on a machine that
has a browser logged into anything you care about.

> A rule that names a tool that doesn't exist simply never matches, and the
> action falls through to asking. So a typo in that file makes Claude *more*
> cautious, never less. Nothing there can fail open.

---

## The login problem, solved the other way round

You asked for: Claude opens the site, then **stops and waits while you type the
password**. That works — but it is the worse version, because it happens every
single time.

`--user-data-dir=${HOME}/.claude-browser-profile` in `.mcp.json` is the better
version. That directory is a real, persistent Chrome profile. Cookies and
sessions survive between runs. So:

- **First time on a site:** Claude navigates, hits the login wall, and stops —
  it cannot type a password it does not have. You type it in the window that is
  already open in front of you. You tell Claude to carry on.
- **Every time after:** the session is still there. No login, no stopping, no
  password.

One manual login per site, for the life of that profile. If you want it wiped,
delete the folder.

**Never put a password in the chat, in a file in this repo, or in `.env` for
Claude to type.** Type it yourself, in the browser window, where it goes into
Chrome's own password store and nowhere near a transcript.

---

## Midjourney: the one you named, and the one to avoid

Midjourney has no public API — deliberately, not as a missing feature — and
their terms say plainly: *you may not use automated tools to access, interact
with, or generate Assets.* Accounts get banned for it, including people whose
only crime was wiring it into an automation tool.

A browser being driven by an agent is exactly what that rule is about. So this
is not a "be careful" — driving Midjourney with the setup on this page is a good
way to lose the Midjourney account.

The good news is that this costs the project almost nothing, because of what
`HOW-THE-ART-IS-MADE.md` already decided:

> **Finding the look — Midjourney v7.** … **Producing the assets — Scenario.**

Midjourney's job here is *step 1 only*: twenty style plates, and **you** pick
one. That is a single human judgement call, made once, that no automation should
be making anyway. Run it by hand, in the normal way, like a person. It is the
one blocking step in the whole build and it stays blocking.

**Scenario — the tool this project already picked for the other twenty assets —
has a REST API.** So does every other production-side generator worth using
(Ideogram, Recraft, Flux via fal.ai or Replicate). Those need no browser at all,
break no rules, and are faster than clicking.

---

## What this project's loop should actually be

Here is the thing worth noticing: **the pipeline is already automated except for
one step.**

```
prompt  →  generator  →  assets/raw/<exact-name>.png  →  cut_assets.py  →  build_world.py
   ^           ^                    ^                        already          already
   |           |                    |                        automated        automated
   |           |                    └── this is the only manual step
   |           └── needs an API key, not a browser
   └── already written, in HOW-THE-ART-IS-MADE.md
```

`tools/cut_assets.py` already keys the magenta, feathers the edge and measures
the base row. `tools/build_world.py` already bakes the sprites into the page.
`assets/raw/README.md` already fixes the exact filename for every asset. Nobody
needs to automate any of that — it's done.

What's missing is one script, roughly eighty lines: take an asset name from
`assets/raw/README.md`, build the prompt from the template in
`HOW-THE-ART-IS-MADE.md`, POST it, poll, save the PNG under the correct name,
then run the two tools that already exist. After that:

```
you:     "regenerate tree-pine-13, the crown is too dense"
claude:  [generates, cuts, rebuilds, opens the world, screenshots it]
you:     [look at it]
```

Zero copy-paste. Zero renaming. Zero attaching pictures to chats. That is the
Jarvis version of this repo, and it is a `SCENARIO_API_KEY` and an afternoon
away — not a browser-automation problem at all.

---

## So what is the browser genuinely for

Plenty, just not the art:

- **Apple Developer portal** — certificates, identifiers, provisioning profiles
  for sideloading onto his iPhone. No API, endless clicking, perfect for this.
- **Fish Audio** — auditioning Russian voices, which is a listen-and-pick job.
- **Picovoice console** — training the custom Russian wake word.
- **The world page itself** — Claude opens `build_world.py`'s output, walks
  around in it, screenshots it, and looks at what it just built. This is the one
  that changes how the art gets made: right now the loop needs *your* eyes to
  see whether a plate works in motion.

That last one is the real unlock. It closes step 3 of the sequence in
`HOW-THE-ART-IS-MADE.md` — *look at real art in the real world before generating
the other sixteen* — without you being the one who has to look.
