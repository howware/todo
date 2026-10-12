---
name: todo
description: The owner's to-dos with Getting Things Done, without an app. Use it when the person wants to note something to do ("anota…", "remind me to…"), process or triage their pending items, ask what to do now, see their to-dos by area, mark something done or postpone it, handle recurring tasks (bills, monthly invoices), or do their weekly review.
---

# todo — Getting Things Done, without an app

A [howware](https://howware.org): the owner's way of handling to-dos, put to work by you. The method is
[Getting Things Done](https://gettingthingsdone.com) (capture → clarify → organize → reflect → engage). The
**owner's rules** — what is urgent, which areas exist, when the weekly review is — live in the memory and grow
over time. Answer in the owner's language.

`TODO` = `python "<this skill's folder>/scripts/todo.py"`; `MEM` = the project-memory helper. Run both from the
owner's folder. All output is JSON. Requires project-memory 0.3.0 or newer.

## Rules (non-negotiable)

1. **Never guess the date, time or weekday.** Run `TODO now` and use what it returns. When you set or move a
   due, say it back in absolute terms: "tomorrow, Tuesday October 13 at 18:00".
2. **Never compute dates or recurrences yourself.** `TODO` validates dues and calculates the next occurrence.
   Translate the owner's words into the tool's formats (`2026-10-13 18:00`, `monthly:last-fri`); if a phrase is
   ambiguous ("next Friday" on a Thursday), ask.
3. **Capture without friction.** When the owner says "note…", capture it as is, confirm in one line, and
   continue. Don't interrogate during capture; clarify later.
4. **The owner decides.** Areas, rules and priorities are theirs: propose, wait for a clear yes, store their
   literal words with `--source`. Never create an area or a rule on your own.
5. **Never mark something done or dropped unless the owner says so.**
6. Nothing outward-facing (sending messages, emails, invites) unless explicitly asked. You organize; you don't
   act on others.
7. Don't store passwords, card numbers or other secrets in a task; if the owner dictates one, warn them and leave
   it out.

## Exactness boundary

| The tool does | You do |
|---|---|
| Today's date, time and weekday (`now`); days since the last weekly review (`brief`) | Turn "tomorrow at 10" or "next payday" into a date, with `now` as reference, and confirm it |
| Validate dues; overdue and due-in days; times postponed (`list`, `brief`) | Decide what deserves attention and say why |
| Next occurrence of a recurring task (`complete`) | Choose the rule with the owner (`monthly:10`, `weekly:tue`) |
| Store states, history and reasons (`capture`, `clarify`, `postpone`, `complete`) | Propose the clarification; wait for approval |
| Completion patterns (`stats`) | Turn patterns into proposed rules |

Exit codes: 0 ok · 2 invalid input (explain `error.message`, fix the value or ask) · 3 memory problem (say what
to install or check). Errors arrive as `{"ok": false, "error": {"code", "message"}}`.

## Cold start

1. `MEM brief --format text` (or the one the session hook injected): the owner's rules appear there as
   preferences and conventions.
2. If there is no memory: follow "Start the memory" of project-memory, then `TODO setup --by person:<id>`. Ask the
   owner which day they want their weekly review and store it as a rule (see Rules the owner teaches).
3. `TODO brief`. Open with, in this order and only if non-empty:
   - **Overdue**, hard deadlines first, with days overdue and times postponed.
   - **Today**, and **hard deadlines in the next 7 days**.
   - **Inbox**: "you have N items to clarify — shall we triage?"
   - If today is the review day (the weekday from `TODO brief` and the stored rule) and `days_since_review` is
     null or 7 or more: offer the weekly review.
4. Keep it short. If there is nothing urgent, say so in one line.

## Workflows

### 1. Capture

`TODO capture --title "<their words>" --by person:<id> --source "<their words>"`. Several items in one message:
one capture each. Confirm: "Noted (3). Inbox: 7."

### 2. Clarify (triage)

When the owner asks, or the inbox has items and they agree. Run `TODO list --state inbox`. For **all** items,
propose in **one message**, grouped:

- **Is it actionable?** If not: `someday` (maybe later), `dropped` (not needed), or reference (tell them to keep
  it elsewhere; drop it here).
- **Two-minute rule:** if it takes less than two minutes, suggest doing it now.
- **Next action:** the very next physical step, starting with a verb ("Email the accountant asking for…"). This
  is the antidote to procrastination: "do my taxes" is not a next action.
- **Project:** if the outcome needs several steps, give it a project name; the item becomes its first next
  action.
- **Waiting:** if someone else must act first, `waiting` with who.
- **Area** (only existing ones; propose new ones explicitly), **context** (computer, phone, errands, home, or
  ones the owner added), **estimate** in minutes, **energy** (low/medium/high).
- **Due:** only if there is a real date. **Hard** = it costs if missed (payments, legal, someone depends on it);
  **soft** otherwise. Recurring: propose the rule.

After approval, one `TODO clarify` per item:

```bash
TODO clarify task:ab12 --state next --next-action "Pay in the bank app" --area area:home --context computer \
  --due 2026-10-10 --deadline hard --estimate 10 --energy low --every monthly:10 --by person:<id> --source "<their words>"
```

A new area: propose it ("I'd create the area *Family*; ok?"); on yes, `TODO add-area --name "Family"`.

### 3. What do I do now?

1. If the owner didn't say: ask **how much time** they have, **where** they are (context) and their **energy**.
   One question, all three.
2. `TODO list --state next` (filter by `--context` or `--area` if they said).
3. Apply, in order: overdue hard deadlines → the owner's rules (from the brief) → due soonest → fits the time and
   energy → postponed most (a small step breaks procrastination).
4. Offer **three** options, each with its reason in one line. If one was postponed 3+ times, offer a smaller
   first step instead.

### 4. Lists

"My to-dos", "work stuff", "what's waiting": `TODO list` with `--area`, `--context`, `--project`,
`--state next,waiting,someday` or `--due overdue|today|week|none`. Present grouped by area (or by context if they
are about to act), overdue first. Keep each line short: next action, due, context.

### 5. Done, postpone, drop

- "Done" → `TODO complete <task>`. If recurring, mention the next occurrence and its date.
- "Move it to Friday" → `TODO now`, then `TODO postpone <task> --to <date> --reason "<their words>"`. Confirm the
  absolute date.
- "Forget it" → confirm, then `TODO clarify <task> --state dropped`.

### 6. Overdue — reminders until it's resolved

Overdue items appear at every session start until they are done, postponed or dropped. Escalate gently:

- Overdue or postponed **3+ times**: ask which it is — still valid? smaller next action? delegate (waiting)? drop?
- Hard deadline overdue: say so first and plainly, with the cost if the owner told you one.
- Never nag in the middle of other work; once per session is enough unless it's due today with a time.

### 7. Weekly review (GTD)

On the owner's review day, or when they ask. Run `TODO review` and go through it **in order**, one section per
message, waiting for the owner each time:

1. **Get clear:** anything on their mind not captured yet? Capture it. Then clarify the inbox (workflow 2) until
   it's empty.
2. **Overdue and next 14 days:** confirm, postpone or drop each.
3. **Projects without a next action:** define one for each, or mark the project someday.
4. **Waiting:** for each, is it time to follow up? (Suggest the follow-up as a next action; don't send anything.)
5. **Stale next actions** (14+ days untouched): still relevant?
6. **Someday:** anything to activate now?
7. **Done last 7 days:** a short acknowledgment.
8. **Learn:** run `TODO stats` and propose at most two rules (see below).

Close with the next review date. Record that the review happened: `TODO review --mark-done --by person:<id>`.

## Rules the owner teaches

Rules are data, not code. When the owner states one, or approves one you proposed from patterns:

```bash
MEM remember --kind preference --text "Bank things are always urgent" --source-text "<their literal words>" --by person:<id>
MEM remember --kind preference --text "Weekly review on Fridays" --by person:<id>
```

To change one: `--supersedes <key of the old one>`. Rules show up in every session brief; apply them in triage,
in "what do I do now?" and in the review, and **say which rule you applied** when you suggest something.

**Learning, stated precisely:** you don't train on anything. You look at the history (`TODO stats`: what gets
done on which weekday, what gets postponed, how early or late recurring tasks are paid) and **propose** rules,
e.g. "You pay the electricity 2 days early every month — shall I put it first that week?". Only approved rules are
stored.

## Approval

| Decision | Proposed | Stored with |
|---|---|---|
| Clarification of inbox items | One message for all, grouped | `TODO clarify` per item, `--source` |
| A new area | Explicitly, by name | `TODO add-area` |
| A new context | Explicitly | `TODO add-context` |
| A rule | Stated by the owner, or proposed from `stats` | `MEM remember --kind preference` |
| Dropping or completing | Only on the owner's word | `TODO clarify --state dropped` / `TODO complete` |

## Presenting results

- Lead with what needs attention; no preamble. Short lines: **next action** · due · context.
- Absolute dates with weekday ("Tue Oct 13, 18:00"), from the tool. Times in 24h unless the owner prefers 12h
  (store that as a rule).
- Group by area when listing; by context when the owner is about to act.
- Never invent tasks, dates or rules. If something doesn't add up, say so.
