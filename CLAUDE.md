# CLAUDE.md — read first, every session

## What this project is
**«Боб»** — an iOS voice companion for lonely people of any age. The person talks; he answers out loud, in Russian, as a friend with his own life, history and character. Backend: Python + FastAPI (`backend/`). App: SwiftUI (`ios/`). The full picture, measured numbers and settled reasoning live in `docs/HANDOVER.md` — where it disagrees with other docs, it wins.

## How we work: orchestrator and workers (Omega)
- You (the main session) are the orchestrator. You plan, write briefs and check results. You don't do bulk work yourself when a worker can do it.
- Workers are subagents on Haiku (`builder`, `reviewer` in `.claude/agents/`). Every brief states the goal, the files to read, and a "Done when:" check that can be run or seen.
- Before accepting any worker's output, run its check yourself. If it fails, send it back with the failure. Never pass on a worker's report unchecked.
- Start of every session: read CLAUDE.md and the three docs. End of every session: update progress.md, add new decisions and gotchas, and propose skill edits with the evidence from this session (`reflect` skill). The owner approves them before you apply them.

## Checking
Every piece of work is checked by the owner's global `verifier` agent (Opus, read-only; rules in `~/.claude/CLAUDE.md`). For this project it also uses the matching checklist in `.claude/checklists/` (backend, ios, world).

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
.claude/checklists/     what "right" means for backend, ios, world
```

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- When graphify-out/graph.json exists, run `graphify query "<question>"` before your first grep, search or source-file read for a codebase question, and put this rule in every subagent prompt that explores code. Read raw files only for lines the graph or an earlier read already located. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
- A committed graphify-out/graph.json is rewritten whole on every build, so a large diff to it in a pull request is expected. Do not flag it as churn or suggest skipping the graph rebuild or its hooks.
