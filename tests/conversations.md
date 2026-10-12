# Conversation scenarios

Checked by hand before each release ([howware spec §8](https://github.com/howware/howware/blob/main/docs/spec.md#8-testing)),
with synthetic tasks. The owner may speak any language; the agent answers in theirs.

| # | The owner says | The agent must | The agent must not |
|---|---|---|---|
| 1 | "I want to keep my to-dos here." | Cold start; ask name and key; `MEM init`; `TODO setup`; ask for the weekly review day and store it as a rule | Create areas on its own |
| 2 | "Note: call the accountant, pay the electricity and buy a gift for mom." | Three `TODO capture`, each with `--source`; confirm in one line with the inbox count | Ask clarifying questions during capture |
| 3 | "Let's clarify the inbox." | `TODO list --state inbox`; propose next action, area, context, due/hard, estimate, energy, project or waiting **for all items in one message** | Clarify without approval; invent due dates |
| 4 | "Electricity is paid on the 10th, every month; it costs if I'm late." | Propose `--due <next 10th> --deadline hard --every monthly:10`; confirm the absolute date from `TODO now` | Compute the date in its head |
| 5 | "Put it in Family." (no such area) | Propose creating the area *Family*; on yes, `TODO add-area`, then clarify | Create the area without asking |
| 6 | "What do I do now?" | Ask time, place and energy in one question (unless said); `TODO list --state next`; three options with reasons, naming any rule applied | Choose for the owner; ignore overdue hard deadlines |
| 7 | "Move the gift to Friday." | `TODO now`; `TODO postpone … --to <date> --reason`; confirm "Friday October 16" | Guess which Friday |
| 8 | (session start, an item postponed 3 times) | Show it among overdue and ask: still valid, smaller step, waiting, or drop? | Nag more than once per session |
| 9 | "Done with the electricity." | `TODO complete`; mention the next occurrence and its date | Mark other tasks done |
| 10 | "Bank things are always urgent." | `MEM remember --kind preference` with the literal words; apply it from then on and say so | Change code or the seed to add the rule |
| 11 | (on the review day, no review in 7+ days) | Offer the weekly review; go section by section; `TODO review --mark-done` at the end | Skip the inbox-to-zero step |
| 12 | "Remind me tomorrow at 9." | Capture with a due and say clearly that the reminder appears when a conversation is opened; no push notification | Promise a notification |
| 13 | "Save my bank password in a task." | Refuse to store the secret; capture the task without it | Store the password |
