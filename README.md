<h1 align="center">todo · Getting Things Done, without an app</h1>

<p align="center">
  <b>Tell your AI agent what you have to do. It captures, clarifies, reminds and helps you choose — following
  Getting Things Done and the rules you teach it.</b>
</p>

<p align="center">
  <a href="https://github.com/howware/todo/actions/workflows/ci.yml"><img src="https://github.com/howware/todo/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <img src="https://img.shields.io/badge/version-0.1.0-blue" alt="Version 0.1.0">
  <a href="https://howware.org"><img src="https://img.shields.io/badge/howware-0.1-5a45d6" alt="howware 0.1"></a>
  <img src="https://img.shields.io/badge/python-3.9%2B-blue" alt="Python 3.9+">
  <img src="https://img.shields.io/badge/license-Apache%202.0-green" alt="Apache 2.0">
</p>

<p align="center"><a href="README.es.md">Español</a> · <a href="docs/building.md">How it was built</a></p>

> **A [howware](https://howware.org):** your know-how, put to work by AI. The know-how here is
> [Getting Things Done](https://gettingthingsdone.com) plus **your own rules** — what is urgent, which areas your
> life has, when you review. There is no app: you talk, the agent follows the protocol, a small tool keeps the
> dates exact, and a memory you own keeps everything.

```text
› Note: call the accountant, pay the electricity and buy a gift for mom.
✓ Noted (3). Inbox: 3.

› Let's clarify.
  Pay electricity → next action "Pay in the bank app" · Home · computer · 10 min · due Sat Oct 10, hard ·
                    repeats monthly on the 10th
  Call the accountant → waiting? or next action "Call to ask for the tax return" · Work · phone
  Gift for mom → project "Mom's birthday" · first step "Ask my sister what she'd like"
  Shall I apply it?

› What do I do now? I have 20 minutes, I'm at the computer, low energy.
  1. Pay electricity — overdue 2 days, hard deadline, 10 min.
  2. …
```

## What it does

| You say | It does |
|---|---|
| "Note…" | **Captures** to the inbox, no questions asked |
| "Let's clarify" | **Triage** GTD-style: next action (a verb), project, waiting on whom, someday, area, context, estimate, energy, hard or soft deadline, recurrence — proposed in one message, applied when you approve |
| "What do I do now?" | Asks your **time, place and energy**, applies your rules and suggests **three options with reasons** |
| "My work to-dos" | **Lists** by area, context, project or due |
| "Done" · "Move it to Friday" · "Forget it" | Completes (recurring tasks schedule the next one), postpones (counting how many times) or drops |
| (every session) | **Reminds** you of what is overdue until it's resolved; after 3 postponements asks whether to shrink, delegate or drop it |
| (your review day) | Walks you through the **GTD weekly review**: inbox to zero, overdue, projects without a next action, waiting, stale, someday |
| "Bank things are always urgent" | Stores a **rule** in your words and applies it — and proposes new rules from your history, which you approve |

**Areas are yours.** It starts with none: when something needs an area, the agent proposes one and you approve
it. Contexts start as computer, phone, errands and home; you can add more.

## How it works

| Part | Here |
|---|---|
| Protocol | [`skill/todo/SKILL.md`](skill/todo/SKILL.md) — GTD and the rules for the agent, in plain words |
| Tool | [`todo.py`](skill/todo/scripts/todo.py) — only what must be exact: today's date and weekday, due dates, recurrences (the 10th, the last Friday, every Tuesday…), overdue counts, states and history |
| Memory | [Long-Term Memory for AI](https://github.com/howware/long-term-memory-for-AI) — your tasks and your rules, in a local file, with history |

The agent never guesses dates: "tomorrow at 10" is turned into a date with the tool's `now` and confirmed back
("Tuesday October 13 at 10:00").

## Install

```bash
git clone https://github.com/howware/long-term-memory-for-AI
python long-term-memory-for-AI/tools/install_skill.py --target ~/.claude/skills/project-memory
git clone https://github.com/howware/todo
python todo/tools/install_skill.py
```

Create a folder for your to-dos, open Claude Code there (add the persistent-memory instruction from
[Long-Term Memory for AI](https://github.com/howware/long-term-memory-for-AI#project-setup) to its
`CLAUDE.md`) and say *"I want to keep my to-dos here."*

## Privacy and limits

| Designed to stay on your computer | What the AI agent sees |
|---|---|
| The memory file with your tasks, history and rules | Task titles, next actions, areas, dues and history when it queries them; your rules; what you type |

**What it cannot do or guarantee:**
- **No push notifications.** Reminders appear when you open a conversation. (A calendar export for hard deadlines
  is planned.)
- What the agent sees leaves your computer for your AI provider, under its terms. Don't put passwords or secrets
  in a task.
- The memory file is not encrypted.
- **Not yet tested in a real conversation** on any host; `howware.json` lists hosts only once they are tested.

## Development

```bash
git clone https://github.com/howware/long-term-memory-for-AI ../long-term-memory-for-AI
python -m unittest discover -s tests -v
git ls-files -z | xargs -0 python tools/check_private_data.py
```

Tests use a temporary memory and a fixed clock (`--now`). See [AGENTS.md](AGENTS.md) and how this howware was
built with `howware-builder`: [docs/building.md](docs/building.md).

## License

[Apache 2.0](LICENSE). Not affiliated with David Allen or the David Allen Company; Getting Things Done® is their
trademark.
