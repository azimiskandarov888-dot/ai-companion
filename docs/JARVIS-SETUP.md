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

## Talking to it, and doing it from the phone

Two things that are not browser automation and are worth having first.

**Voice, at the desk.** Claude Code has built-in dictation. Hold **spacebar**,
talk, release. `/voice tap` switches to tap-to-start if holding gets old. It
wants a local microphone, so it works where you are sitting and not over SSH.

**The phone.** This is the one that changes how the day goes:

```bash
cd ~/ai-companion
claude remote-control        # prints a session URL; press SPACE for a QR code
```

Scan the QR. The Claude app on the phone — or claude.ai/code in a browser — is
now a window into the session **running on this machine**. Not a copy in the
cloud: the same process, the same filesystem, the same `assets/` folder, the
same MCP servers as the section above. Terminal, browser and phone stay in sync,
so you can start something at the desk and finish it from the sofa.

Then run `/config` and turn on **Push when actions required**. The `ask` list in
`.claude/settings.json` becomes a notification on the phone: it buzzes, you
approve the click, it carries on. Sleep and dropped wifi are survivable — the
prompts queue and arrive when the machine is back. What is not survivable is the
machine being *off*: nothing here runs in the cloud.

### The consequence for choosing art

A browser window only works if you are in front of it. So the choosing step is
not a screen — it is **a picture Claude sends**, which renders the same in the
terminal, in the browser and on the phone.

That is what `tools/generate_variants.py` builds: one contact sheet, every
candidate labelled A B C D with its measurements printed underneath, on a
checkerboard so a background that never came off is obvious. You say *"B and
D"*. The browser stays useful for watching, and stops being required.

---

## The loop, as built

The pipeline was already automated except for one step — getting a correctly
named PNG into `assets/raw/`. `cut_assets.py` keys the magenta, measures the
base row and writes the cut-out; `build_world.py` bakes the sprites into a page;
`assets/raw/README.md` fixes the exact filename for every asset. All of that was
done. Only the middle was hand work.

Four scripts close it:

| | |
|---|---|
| `tools/recraft.py` | the API client — generate, remove background, create a style |
| `tools/generate_variants.py` | prompt → n candidates → cut → measure → **reject** → contact sheet |
| `tools/accept_variant.py` | the chosen letter → `raw/`, `cut/`, and the manifest |
| `tools/inspect_assets.py` | the same checks over the whole finished set |

```bash
pip install -r tools/requirements.txt
# put RECRAFT_API_TOKEN=... in backend/.env (already gitignored)

python3 tools/generate_variants.py tree-leafy-11 --note "lighter crown"
python3 tools/accept_variant.py tree-leafy-11 B --build
```

Two things about this are worth more than the automation itself.

**Recraft returns real alpha.** `removeBackground` gives a transparent PNG
directly, so the magenta ground and the whole de-spilling half of
`cut_assets.py` stop being necessary for anything generated this way. That file
stays exactly as it is for the nineteen plates already made the old way.

**Bad candidates never reach you.** Every variant is measured against the grain
band for its kind before the contact sheet is built, so a canopy that came out
as one undifferentiated mass is dropped silently. Four shown is four worth
looking at. `--keep-all` overrides it when you want to see the rejects.

The anchor style from `HOW-THE-ART-IS-MADE.md` lives in `assets/style.json` as a
Recraft `style_id`. That document budgeted fifteen approved images and a
twenty-minute training run for it; this takes up to five and returns
immediately:

```bash
python3 tools/recraft.py assets/cut/tree-leafy-8.png assets/cut/tree-leafy-9.png
```

### What it costs

A V4.1 raster image is about 35 API units and a thousand units is a dollar, so
four variants runs to roughly fifteen cents. Check Recraft's own pricing before
a large batch.

### The one honest gap

Midjourney is not in any of this, on purpose. It has no public API by design and
its terms forbid automated access outright — accounts get banned for exactly the
setup on this page. That costs the project almost nothing, because
`HOW-THE-ART-IS-MADE.md` gave Midjourney *step 1 only*: twenty style plates
where a human picks one. Run that by hand, like a person. It is the one blocking
step in the build and it stays blocking.

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
