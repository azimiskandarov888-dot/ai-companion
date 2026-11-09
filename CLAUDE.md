# CLAUDE.md — read first, every session

## What this project is
**«Боб»** — an iOS voice companion for lonely people of any age. The person talks; he answers out loud, in Russian, as a friend with his own life, history and character. Backend: Python + FastAPI (`backend/`). App: SwiftUI (`ios/`). The full picture, measured numbers and settled reasoning live in `docs/HANDOVER.md` — where it disagrees with other docs, it wins.

## How we work: orchestrator and workers (Omega)
- You (the main session) are the orchestrator. You plan, write briefs and check results. You don't do bulk work yourself when a worker can do it.
- Workers are subagents on Haiku (`builder`, `reviewer` in `.claude/agents/`). Every brief states the goal, the files to read, and a "Done when:" check that can be run or seen.
- Before accepting any worker's output, run its check yourself. If it fails, send it back with the failure. Never pass on a worker's report unchecked.
- Start of every session: read CLAUDE.md and the three docs. End of every session: update progress.md, add new decisions and gotchas, and propose skill edits with the evidence from this session (`reflect` skill). The owner approves them before you apply them.

## Where everything lives
```
CLAUDE.md               this file: what the project is, the rules, the map
docs/progress.md        where we are: done, next, a dated log line per session
docs/decisions.md       what's settled, with the date and why
docs/known-issues.md    gotchas and their fixes
docs/HANDOVER.md        the full state of the project (source of truth)
docs/*.md               who Bob is, his soul, voice research, boundaries, audits
PLAN.md                 the family's original plan
backend/                Python + FastAPI server (app/, tests/, static/, run.sh)
ios/                    SwiftUI iPhone app (BobCompanion/, project.yml, DESIGN.md)
tools/                  helper scripts (voice, world build, asset cutting)
assets/                 art sources (raw/, cut/, manifest.json)
.claude/agents/         worker agents, each with model: haiku and one job
.claude/skills/         one folder per repeatable task, each with a SKILL.md
```
