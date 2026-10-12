# Changelog

## Unreleased

- README: `todo` can share its memory with [bitacora](https://github.com/howware/bitacora) 0.2, which sends the
  things to do said in the journal to the inbox.
- Private-data guard from the howware template: in English, blocks invoice XMLs, allows the SAT's public
  generic RFCs.

## 0.1.1

- Follows [howware specification 0.2](https://github.com/howware/howware/blob/main/docs/spec.md): `howware.json`
  lists the memory as an **adapter** (`adapters`); the installer prints the adapters to install.

## 0.1.0 — first version

- Protocol for Getting Things Done without an app: capture, clarify (triage), what to do now, lists, done /
  postpone / drop, overdue escalation, GTD weekly review, rules the owner teaches, approval.
- `todo.py`: `now`, `capture`, `clarify`, `add-area`, `add-context`, `complete`, `postpone`, `list`, `brief`,
  `review` (and `--mark-done`), `stats`. Exact recurrences; a recurring series keeps its schedule when one
  occurrence is postponed. Errors as JSON with exit codes 2 and 3.
- No predefined areas; contexts computer, phone, errands and home (with Spanish aliases).
- Built with `howware-builder`; the process is recorded in `docs/building.md`.
