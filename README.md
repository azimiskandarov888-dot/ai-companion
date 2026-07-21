# AI Companion 🫶

A warm, thoughtful **AI chat companion** powered by Claude — someone to talk to,
think out loud with, or just pass the time. Built with Next.js and streaming
responses so replies feel alive as they arrive.

![tech](https://img.shields.io/badge/Next.js-16-black) ![tech](https://img.shields.io/badge/React-19-blue) ![tech](https://img.shields.io/badge/Claude-Opus_4.8-8A2BE2)

## Features

- 💬 **Real-time streaming** — the companion's replies stream in token by token.
- 🎭 **A real personality** — warm, curious, and present (fully customizable).
- 🧠 **Conversation memory** — remembers the thread of your chat within a session.
- 🎨 **Polished UI** — gradient glass design, typing indicator, auto-growing input.
- 🔒 **Key stays server-side** — your API key never reaches the browser.

## Getting started

### 1. Add your API key

```bash
cp .env.example .env.local
```

Then edit `.env.local` and set your key (get one at
[console.anthropic.com](https://console.anthropic.com/)):

```
ANTHROPIC_API_KEY=sk-ant-...
```

### 2. Install & run

```bash
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) and start talking. 🎉

## Configuration

All optional, set in `.env.local`:

| Variable                     | Default          | What it does                          |
| ---------------------------- | ---------------- | ------------------------------------- |
| `ANTHROPIC_API_KEY`          | _(required)_     | Your Anthropic API key.               |
| `ANTHROPIC_MODEL`            | `claude-opus-4-8`| Which Claude model to use.            |
| `NEXT_PUBLIC_COMPANION_NAME` | `Aria`           | Your companion's name.                |

## How it works

```
Browser (app/page.tsx)
   │  POST /api/chat  { messages: [...] }
   ▼
API route (app/api/chat/route.ts)
   │  streams from Claude via @anthropic-ai/sdk
   ▼
Claude (claude-opus-4-8)  ──►  tokens stream back to the browser
```

- **`lib/companion.ts`** — the companion's name and personality (system prompt).
  This is the file to edit to change who your companion *is*.
- **`app/api/chat/route.ts`** — server route that proxies to Claude and streams
  the response. Your API key lives here, never in the browser.
- **`app/page.tsx`** — the chat interface.

## Make it yours

Want a different vibe? Open `lib/companion.ts` and rewrite the system prompt —
a witty study buddy, a calm mentor, an in-character role-play companion. The
whole personality lives in that one file.

## Project structure

```
app/
  api/chat/route.ts   # streaming Claude endpoint
  layout.tsx          # root layout + metadata
  page.tsx            # chat UI (client component)
  globals.css         # styling
lib/
  companion.ts        # name + personality
```

---

Built with [Claude Code](https://claude.com/claude-code).
