# How this howware was built

A record of building `todo` with the [`howware-builder`](https://github.com/howware/howware/blob/main/skills/howware-builder/SKILL.md)
protocol, step by step, so others can see what building a howware looks like. The owner's words are kept
verbatim, in Spanish, as they were said.

## 1. Interview

The builder asked five groups of questions: how it's done today, the rules, what you'd ask, reminders, and what
must be exact. The owner answered:

| Topic | The owner's words |
|---|---|
| Today | «lo llevo en postips y una libreta y lo que falla es que tengo cosas regadas y no hay recordatorios, se acumulan, se sufre el mal de postergar» |
| Rules | «me gustaria usar conceptos de Get Things Done (GTD), hay cosas de trabajo, personales, de la familia, de la casa. Si tengo pendientes que se repiten como hacer facturas mensuales, pagar agua, luz, contadora. para algo que ya vencio hay que darle un tiempo de recordatorios hasta que se cumpla» |
| Questions | «la lista de mis pendientes de acuerdo a trabajo o en general para ver en el cual quiero trabajar. va a ser necesario hacer un tipo de triage y que el howware vaya aprendiendo para que me vaya sugiriendo en cual trabajar» |
| Reminders | «de acuerdo al triage y a lo vencido» |
| Exact | «si usare horas y si hay errores que cuestan» |

## 2. Does it fit?

Yes. A bare to-do list has little judgment — the whitepaper's own "when not to" case — but GTD is judgment:
clarifying what something is, defining the next action, triage, choosing what to do now, deciding what to do with
overdue items. The exact parts (dates, times, recurrences, overdue counts) are small and well defined.

One limit was stated up front, because "no reminders" was one of the owner's pains: **a howware acts only when a
conversation is opened**; it cannot push a notification. Mitigation in v1: overdue items appear at every session
start until resolved. A calendar export for hard deadlines was proposed and deferred to a later version.

## 3. Design and the owner's decisions

The builder proposed the design (protocol workflows, the tool's exact operations, the memory, privacy, what's
out of scope). The owner decided:

| Question | Decision |
|---|---|
| Areas (work, personal, family, home?) | «dejalo sin areas para que quien lo use vaya agregando poco a poco sus propias areas» → no predefined areas; the agent proposes, the owner approves |
| Contexts (computer, phone, errands, home) | Yes |
| Weekly review | «quiero revision tipo Get things done» → the full GTD weekly review; the day is asked at setup and stored as a rule |
| Calendar file (`.ics`) | «para esta primera version lo aremos sin .ics, luego lo agregamos» |
| Repository | «hay que hacerle su propio repositorio, no hay que revolverlo con los demas para asi ir haciendo como si fueran recetas que podemos ir integrando» |
| "It should learn" | Stated precisely: the model doesn't train; the agent proposes rules from the history (`stats`) and stores only the ones the owner approves |

## 4. Scaffold

```bash
python howware/skills/howware-builder/scripts/new_howware.py --name todo \
  --description "Your to-dos with Getting Things Done, without an app: …" --out .
```

## 5–8. Protocol, tool, memory, privacy

- **Protocol** ([SKILL.md](../skill/todo/SKILL.md)): rules, exactness boundary, cold start, seven workflows
  (capture, clarify, what now, lists, done/postpone/drop, overdue escalation, weekly review), rules the owner
  teaches, approval, presentation.
- **Tool** ([todo.py](../skill/todo/scripts/todo.py)): `now`, `capture`, `clarify`, `add-area`, `add-context`,
  `complete`, `postpone`, `list`, `brief`, `review`, `stats`. Recurrences: daily, every N days, weekdays, day of
  month (clamped), last day, Nth/last weekday, yearly.
- **Memory**: tasks as entities whose state, due and other fields are facts with history; captures, completions
  and postponements as events; the owner's rules as `preference` records, which appear in every session brief.

## What building it taught us

Each of these was found while building, and changed the design:

1. **The builder got the weekday wrong.** While proposing the design, the builder wrote «mañana, domingo 12 de
   octubre». The tool's first run said October 12, 2026 is a **Monday**. That is exactly why rule 1 says the agent
   never guesses dates.
2. **A postponement leaked into the next month.** "Pay electricity" is due on the 10th, with no time. Postponed to
   the 13th at 18:00 and completed, the next occurrence came out as November 10 **at 18:00**. Fix: a recurring task
   keeps its own schedule (`series_due_at`); postponing moves one occurrence, not the series.
3. **"Was the review done this week?" was judgment where it should be exact.** The first protocol asked the agent
   to decide; it had no reliable way to know. Fix: `review --mark-done` records it and `brief` returns
   `days_since_review`.
4. **Names come in the owner's language.** The agent may say "computadora" for `context:computer`. Fix: areas and
   contexts resolve by key, name or alias, and fail with a clear message if ambiguous or missing.
5. **The template was incomplete.** The specification lists `LICENSE` and `SECURITY.md`; the template had neither.
   Fixed in the template too.

## 9. Verification

- 11 automated tests: recurrence edge cases (month ends, leap years, last weekday), due parsing, overdue rules, the
  tool contract, and every workflow against a real memory with a fixed clock (`--now`).
- 13 [conversation scenarios](../tests/conversations.md), to be checked in a real conversation before listing a
  host in `howware.json` (none yet).
- A review against the specification with `howware-review` (see the commit that published 0.1.0).

## Next

- Test in a real conversation (Claude Code first), then list the host.
- Calendar export (`.ics`) with alarms for hard deadlines.
- Sharing tasks with family members — the "teams" stage of the howware roadmap, and a good third example.
