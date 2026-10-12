"""todo — the exact operations of the todo howware (Getting Things Done, without an app).

Commands (JSON on stdout; errors as {"ok": false, "error": {"code", "message"}}):
  setup        load predicates, starting contexts and vocabularies into the memory
  now          current date, time and weekday — the agent never guesses them
  capture      put something in the inbox, without questions
  clarify      turn an item into a next action / project step / waiting / someday / done / dropped
  add-area     create an area of the owner's life (only after the owner approves it)
  add-context  create a context (where or with what a task can be done)
  complete     mark done; a recurring task schedules its next occurrence
  postpone     move a due date, counting postponements and keeping the reason
  list         open tasks, filtered, with exact overdue / due-in figures
  brief        what to show at the start of a session
  review       the data for the GTD weekly review; --mark-done records that it happened
  stats        history the agent uses to propose rules (it never changes rules by itself)

Exit codes: 0 ok · 2 invalid input · 3 memory problem.
No network, no prompts, standard library only. Dates without a time are stored at noon local time.
"""

from __future__ import annotations

import argparse
import calendar
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import unicodedata
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

__version__ = "0.1.0"
HERE = Path(__file__).resolve().parent
SEED = HERE / "seed.json"
MIN_MEMORY = (0, 3, 0)
OK, BAD_INPUT, MEMORY_ERROR = 0, 2, 3
STATES = ("inbox", "next", "waiting", "someday", "done", "dropped")
OPEN_STATES = ("inbox", "next", "waiting", "someday")
WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
ENERGY = ("low", "medium", "high")
DEADLINES = ("hard", "soft")


class ToolError(Exception):
    def __init__(self, message: str, code: int = BAD_INPUT):
        super().__init__(message)
        self.code = code


# -- memory ------------------------------------------------------------------------------
def find_helper(explicit: str | None) -> Path:
    for c in (explicit, os.environ.get("HOWWARE_MEMORY_HELPER"),
              Path.home() / ".claude/skills/project-memory/scripts/memory.py",
              Path.home() / ".codex/skills/project-memory/scripts/memory.py"):
        if c and Path(c).is_file():
            return Path(c)
    raise ToolError("project-memory is not installed (or pass --mem / HOWWARE_MEMORY_HELPER).", MEMORY_ERROR)


class Memory:
    def __init__(self, helper: Path, db: str | None):
        self.helper, self.db = helper, db

    def run(self, *args: str, stdin: dict | None = None) -> Any:
        for attempt in (1, 2):
            cmd = [sys.executable, str(self.helper)] + (["--db", self.db] if self.db else []) + list(args)
            proc = subprocess.run(cmd, input=json.dumps(stdin, ensure_ascii=False) if stdin is not None else None,
                                  capture_output=True, text=True, encoding="utf-8")
            if proc.returncode == 0:
                return json.loads(proc.stdout) if proc.stdout.strip() else None
            message = (proc.stderr or proc.stdout).strip()
            # The memory compares validity per second: two changes to the same fact in one second wait one.
            if attempt == 1 and "at least one second" in message:
                time.sleep(1.1)
                continue
            raise ToolError(f"memory {args[0]} failed: {message[-600:]}", MEMORY_ERROR)

    def check_version(self) -> None:
        out = subprocess.run([sys.executable, str(self.helper), "--version"], capture_output=True, text=True).stdout
        found = re.search(r"(\d+)\.(\d+)\.(\d+)", out or "")
        if not found or tuple(int(x) for x in found.groups()) < MIN_MEMORY:
            raise ToolError(f"project-memory >= {'.'.join(map(str, MIN_MEMORY))} is required (found: {out.strip()}).",
                            MEMORY_ERROR)

    def rows(self, *args: str) -> list[dict]:
        return self.run("list", *args, "--limit", "1000")["rows"]


# -- time --------------------------------------------------------------------------------
def parse_offset(text: str) -> timezone:
    m = re.fullmatch(r"([+-])(\d{2}):?(\d{2})", text.strip())
    if not m:
        raise ToolError(f"Time zone offset must look like -06:00, not {text!r}")
    minutes = int(m.group(2)) * 60 + int(m.group(3))
    return timezone(timedelta(minutes=minutes if m.group(1) == "+" else -minutes))


def local_offset() -> str:
    z = datetime.now().astimezone().strftime("%z")
    return f"{z[:3]}:{z[3:]}"


def current(args) -> datetime:
    tz = parse_offset(args.tz)
    if args.now:
        try:
            return datetime.fromisoformat(args.now).replace(tzinfo=tz)
        except ValueError as error:
            raise ToolError(f"--now must be YYYY-MM-DDTHH:MM, not {args.now!r}") from error
    return datetime.now(tz)


def parse_due(text: str, tz: timezone) -> tuple[datetime, bool]:
    """'YYYY-MM-DD' (no time: stored at noon) or 'YYYY-MM-DD HH:MM' / 'YYYY-MM-DDTHH:MM'."""
    text = text.strip().replace(" ", "T")
    try:
        if "T" in text:
            return datetime.fromisoformat(text[:16]).replace(tzinfo=tz), True
        return datetime.combine(date.fromisoformat(text), datetime.min.time().replace(hour=12), tz), False
    except ValueError as error:
        raise ToolError(f"Due must be YYYY-MM-DD or YYYY-MM-DD HH:MM, not {text!r}") from error


def iso(dt: datetime) -> str:
    return dt.isoformat(timespec="seconds")


def describe_due(due: datetime, has_time: bool, now: datetime) -> dict:
    due = due.astimezone(now.tzinfo)
    days = (due.date() - now.date()).days
    overdue = due < now if has_time else due.date() < now.date()
    return {"due": due.strftime("%Y-%m-%d %H:%M") if has_time else due.strftime("%Y-%m-%d"),
            "weekday": WEEKDAYS[due.weekday()], "has_time": has_time, "overdue": overdue,
            "days_overdue": max(0, -days) if overdue else 0, "due_in_days": days}


# -- recurrence --------------------------------------------------------------------------
RULE_HELP = ("daily · days:N · weekly:mon[,thu] · monthly:D (1-31, clamped to the month's end) · monthly:last · "
             "monthly:N-<weekday> (N = 1..4 or last, e.g. monthly:last-fri) · yearly:MM-DD")


def check_rule(rule: str) -> str:
    rule = rule.strip().lower()
    ok = (rule == "daily" or re.fullmatch(r"days:[1-9]\d{0,2}", rule)
          or re.fullmatch(r"weekly:(mon|tue|wed|thu|fri|sat|sun)(,(mon|tue|wed|thu|fri|sat|sun))*", rule)
          or re.fullmatch(r"monthly:(last|([1-9]|[12]\d|3[01])|([1-4]|last)-(mon|tue|wed|thu|fri|sat|sun))", rule)
          or re.fullmatch(r"yearly:(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])", rule))
    if not ok:
        raise ToolError(f"Unknown recurrence {rule!r}. Use: {RULE_HELP}")
    return rule


def _nth_weekday(year: int, month: int, n: str, weekday: int) -> date:
    days = [d for d in range(1, calendar.monthrange(year, month)[1] + 1) if date(year, month, d).weekday() == weekday]
    return date(year, month, days[-1] if n == "last" else days[int(n) - 1])


def _add_month(d: date, k: int = 1) -> tuple[int, int]:
    m = d.month - 1 + k
    return d.year + m // 12, m % 12 + 1


def next_occurrence(rule: str, previous: date) -> date:
    """The first date of the rule strictly after the previous due date."""
    kind, _, arg = rule.partition(":")
    if kind == "daily":
        return previous + timedelta(days=1)
    if kind == "days":
        return previous + timedelta(days=int(arg))
    if kind == "weekly":
        wanted = {WEEKDAYS.index(w) for w in arg.split(",")}
        d = previous + timedelta(days=1)
        while d.weekday() not in wanted:
            d += timedelta(days=1)
        return d
    if kind == "monthly":
        for k in (0, 1, 2):
            y, m = _add_month(previous, k)
            last = calendar.monthrange(y, m)[1]
            if arg == "last":
                d = date(y, m, last)
            elif arg.isdigit():
                d = date(y, m, min(int(arg), last))
            else:
                n, _, wd = arg.partition("-")
                d = _nth_weekday(y, m, n, WEEKDAYS.index(wd))
            if d > previous:
                return d
    if kind == "yearly":
        mm, dd = (int(x) for x in arg.split("-"))
        for y in (previous.year, previous.year + 1, previous.year + 2):
            d = date(y, mm, min(dd, calendar.monthrange(y, mm)[1]))
            if d > previous:
                return d
    raise ToolError(f"Could not compute the next occurrence of {rule!r}")


# -- helpers -------------------------------------------------------------------------------
def slug(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "x"


def source(by: str, content: str, kind: str = "user_statement") -> dict:
    return {"type": kind, "content": content, "provided_by": by, "captured_at": "now"}


def write(mem: Memory, by: str, content: str, **sections) -> dict:
    return mem.run("write", stdin={"source": source(by, content), "performed_by": by, **sections})


def task_key(ref: str) -> str:
    return ref if ref.startswith("task:") else f"task:{ref}"


TASK_COLUMNS = ["key", "fact:task_title", "fact:task_state", "fact:task_state/since", "fact:next_action",
                "fact:in_area/key", "fact:in_context/key", "fact:in_project/key", "fact:in_project/name",
                "fact:due_at", "fact:due_has_time", "fact:deadline_kind", "fact:estimate_minutes", "fact:energy",
                "fact:waiting_on", "fact:recurrence", "fact:times_postponed", "fact:series_due_at",
                "fact:series_has_time"]


def load_tasks(mem: Memory, states: tuple[str, ...], now: datetime, key: str | None = None) -> list[dict]:
    where = ["--where", f"fact:task_state in {'|'.join(states)}"]
    if key:
        where += ["--where", f"key = {key}"]
    cols = [x for c in TASK_COLUMNS for x in ("--column", c)]
    out = []
    for r in mem.rows("--entity-type", "task", *where, *cols):
        t = {"task": r["key"], "title": r["fact:task_title"], "state": r["fact:task_state"],
             "next_action": r["fact:next_action"], "area": r["fact:in_area/key"], "context": r["fact:in_context/key"],
             "project": r["fact:in_project/name"], "project_key": r["fact:in_project/key"],
             "deadline": r["fact:deadline_kind"], "estimate_minutes": r["fact:estimate_minutes"],
             "energy": r["fact:energy"], "waiting_on": r["fact:waiting_on"], "recurrence": r["fact:recurrence"],
             "times_postponed": r["fact:times_postponed"] or 0,
             "series_due_at": r["fact:series_due_at"], "series_has_time": r["fact:series_has_time"]}
        since = r["fact:task_state/since"]
        t["days_in_state"] = (now.date() - datetime.fromisoformat(since).astimezone(now.tzinfo).date()).days if since else None
        if r["fact:due_at"]:
            t.update(describe_due(datetime.fromisoformat(r["fact:due_at"]), bool(r["fact:due_has_time"]), now))
        out.append({k: v for k, v in t.items() if v is not None and not k.startswith("series_")} | (
            {"_series": (t["series_due_at"], bool(t["series_has_time"]))} if t["series_due_at"] else {}))
    out.sort(key=lambda t: (not t.get("overdue", False), t.get("due") is None, t.get("due") or "", t["task"]))
    return out


def public(t: dict) -> dict:
    return {k: v for k, v in t.items() if not k.startswith("_")}


def one_task(mem: Memory, ref: str, now: datetime, states: tuple[str, ...] = STATES) -> dict:
    found = load_tasks(mem, states, now, task_key(ref))
    if not found:
        raise ToolError(f"No task {task_key(ref)} in states {', '.join(states)}.")
    return found[0]


def entity_exists(mem: Memory, etype: str, key: str) -> bool:
    return bool(mem.rows("--entity-type", etype, "--where", f"key = {key}", "--column", "key"))


def resolve(mem: Memory, etype: str, ref: str) -> str:
    """A key (area:home), or a name or alias in any language (Casa, home): exactly one match or an error."""
    if ref.startswith(f"{etype}:"):
        if entity_exists(mem, etype, ref):
            return ref
        raise ToolError(f"There is no {etype} {ref}. Propose it to the owner and run add-{etype} first.")
    wanted = slug(ref)
    found = {m["external_key"] for m in mem.run("search", ref, "--type", etype) or []
             if wanted in {slug(m["name"])} | {slug(a) for a in (m.get("aliases") or "").split(",") if a.strip()}}
    if len(found) == 1:
        return found.pop()
    if not found:
        raise ToolError(f"There is no {etype} called {ref!r}. Propose it to the owner and run add-{etype} first.")
    raise ToolError(f"{ref!r} matches several {etype}s: {', '.join(sorted(found))}. Use the key.")


# -- commands ------------------------------------------------------------------------------
def cmd_setup(mem: Memory, args, now: datetime) -> dict:
    seed = json.loads(SEED.read_text(encoding="utf-8"))
    result = mem.run("write", stdin={"source": source(args.by, f"todo seed v{seed['seed_version']}", "helper_command"),
                                     "performed_by": args.by,
                                     "predicates": [{**p, "distinct_from_similar": True} for p in seed["predicates"]],
                                     "entities": seed["entities"]})
    for predicate, values in seed["vocabularies"].items():
        mem.run("define-values", "--predicate", predicate, *[x for v in values for x in ("--value", v)], "--by", args.by)
    for event_type in seed["high_volume_event_types"]:
        mem.run("define-event-type", "--type", event_type, "--high-volume", "--by", args.by)
    return {"ok": True, "seed_version": seed["seed_version"],
            "contexts": [e["key"] for e in seed["entities"] if e["type"] == "context"],
            "warnings": result.get("warnings", [])}


def cmd_now(mem: Memory, args, now: datetime) -> dict:
    iso_year, iso_week, _ = now.isocalendar()
    return {"ok": True, "date": now.strftime("%Y-%m-%d"), "time": now.strftime("%H:%M"),
            "weekday": WEEKDAYS[now.weekday()], "iso_week": iso_week, "tz": args.tz,
            "tomorrow": (now.date() + timedelta(days=1)).isoformat()}


def cmd_capture(mem: Memory, args, now: datetime) -> dict:
    title = args.title.strip()
    if not title:
        raise ToolError("A task needs a title.")
    key = "task:" + hashlib.sha256(f"{title.lower()}|{now.date()}".encode()).hexdigest()[:12]
    result = write(mem, args.by, args.source or title,
                   entities=[{"key": key, "type": "task", "name": title[:120]}],
                   facts=[] if entity_exists(mem, "task", key) else [
                       {"subject": key, "predicate": "task_title", "value": title, "valid_from": "now"},
                       {"subject": key, "predicate": "task_state", "value": "inbox", "valid_from": "now"},
                       {"subject": key, "predicate": "times_postponed", "value": 0, "valid_from": "now"}],
                   events=[{"key": f"CAP_{key[5:]}", "type": "task_captured", "occurred_at": "now",
                            "summary": f"Captured: {title}"[:160], "links": [{"predicate": "about_task", "entity": key}]}])
    return {"ok": True, "task": key, "title": title, "state": "inbox",
            "created": bool(result.get("events", {}).get("created"))}


def cmd_add_named(mem: Memory, args, now: datetime, etype: str) -> dict:
    key = args.key or f"{etype}:{slug(args.name)}"
    if not key.startswith(f"{etype}:"):
        raise ToolError(f"The key of a {etype} must start with {etype}:")
    existed = entity_exists(mem, etype, key)
    write(mem, args.by, args.source or f"new {etype} {args.name}",
          entities=[{"key": key, "type": etype, "name": args.name, "aliases": args.alias or []}])
    return {"ok": True, etype: key, "name": args.name, "created": not existed}


def cmd_clarify(mem: Memory, args, now: datetime) -> dict:
    key = task_key(args.task)
    one_task(mem, key, now)
    tz = parse_offset(args.tz)
    facts, entities = [], []

    def fact(predicate: str, value: Any) -> None:
        facts.append({"subject": key, "predicate": predicate, "value": value, "valid_from": "now"})

    if args.state:
        if args.state not in STATES:
            raise ToolError(f"State must be one of {', '.join(STATES)}")
        fact("task_state", args.state)
    if args.title:
        fact("task_title", args.title.strip())
    if args.next_action:
        fact("next_action", args.next_action.strip())
    for flag, etype, predicate in ((args.area, "area", "in_area"), (args.context, "context", "in_context")):
        if flag:
            fact(predicate, resolve(mem, etype, flag))
    if args.project:
        pkey = f"project:{slug(args.project)}"
        entities.append({"key": pkey, "type": "gtd_project", "name": args.project.strip()})
        fact("in_project", pkey)
    if args.due:
        due, has_time = parse_due(args.due, tz)
        fact("due_at", iso(due))
        fact("due_has_time", has_time)
    if args.deadline:
        if args.deadline not in DEADLINES:
            raise ToolError("Deadline must be hard (it costs if missed) or soft.")
        fact("deadline_kind", args.deadline)
    if args.estimate is not None:
        if args.estimate <= 0:
            raise ToolError("Estimate is in minutes and must be positive.")
        fact("estimate_minutes", args.estimate)
    if args.energy:
        if args.energy not in ENERGY:
            raise ToolError(f"Energy must be one of {', '.join(ENERGY)}")
        fact("energy", args.energy)
    if args.waiting_on:
        fact("waiting_on", args.waiting_on.strip())
    if args.every:
        fact("recurrence", check_rule(args.every))
    if args.due or args.every:
        current_task = one_task(mem, key, now)
        if args.due:
            base, base_has_time = parse_due(args.due, tz)
        elif "due" in current_task:
            base, base_has_time = parse_due(current_task["due"], tz)
        else:
            base = None
        if base is not None:
            fact("series_due_at", iso(base))
            fact("series_has_time", base_has_time)
    if not facts:
        raise ToolError("Nothing to clarify: pass at least one field.")
    write(mem, args.by, args.source or f"clarify {key}", entities=entities, facts=facts,
          events=[{"type": "task_clarified", "occurred_at": "now", "summary": f"Clarified {key}",
                   "links": [{"predicate": "about_task", "entity": key}]}])
    return {"ok": True, **public(one_task(mem, key, now))}


def cmd_complete(mem: Memory, args, now: datetime) -> dict:
    t = one_task(mem, args.task, now, OPEN_STATES)
    key, tz = t["task"], parse_offset(args.tz)
    attrs = {}
    if "due" in t:
        attrs["days_from_due"] = -t["due_in_days"]          # positive = done late, negative = early
    write(mem, args.by, args.source or f"done {key}",
          facts=[{"subject": key, "predicate": "task_state", "value": "done", "valid_from": "now"}],
          events=[{"type": "task_completed", "occurred_at": "now", "summary": f"Done: {t['title']}"[:160],
                   "attributes": attrs, "links": [{"predicate": "about_task", "entity": key}]}])
    out: dict[str, Any] = {"ok": True, "task": key, "state": "done", **({"days_from_due": attrs["days_from_due"]} if attrs else {})}
    if t.get("recurrence") and ("_series" in t or "due" in t):
        # The series keeps its own schedule: a postponement moves this occurrence, not the next one.
        if "_series" in t:
            base, base_has_time = datetime.fromisoformat(t["_series"][0]).astimezone(tz), t["_series"][1]
        else:
            base, base_has_time = parse_due(t["due"], tz)
        nxt = next_occurrence(t["recurrence"], base.date())
        nxt_dt = datetime.combine(nxt, base.time(), tz)
        series = key.split("~")[0]
        new_key = f"{series}~{nxt.isoformat()}"
        facts = [{"subject": new_key, "predicate": p, "value": v, "valid_from": "now"} for p, v in (
            ("task_title", t["title"]), ("task_state", "next"), ("times_postponed", 0), ("due_at", iso(nxt_dt)),
            ("due_has_time", base_has_time), ("series_due_at", iso(nxt_dt)), ("series_has_time", base_has_time), ("recurrence", t["recurrence"]), ("next_action", t.get("next_action")),
            ("in_area", t.get("area")), ("in_context", t.get("context")), ("in_project", t.get("project_key")),
            ("deadline_kind", t.get("deadline")), ("estimate_minutes", t.get("estimate_minutes")),
            ("energy", t.get("energy"))) if v is not None]
        if not entity_exists(mem, "task", new_key):
            write(mem, args.by, f"next occurrence of {series}",
                  entities=[{"key": new_key, "type": "task", "name": t["title"][:120]}], facts=facts)
        out["next_occurrence"] = public(one_task(mem, new_key, now))
    return out


def cmd_postpone(mem: Memory, args, now: datetime) -> dict:
    t = one_task(mem, args.task, now, OPEN_STATES)
    due, has_time = parse_due(args.to, parse_offset(args.tz))
    count = int(t.get("times_postponed", 0)) + 1
    write(mem, args.by, args.source or args.reason or f"postpone {t['task']}",
          facts=[{"subject": t["task"], "predicate": "due_at", "value": iso(due), "valid_from": "now"},
                 {"subject": t["task"], "predicate": "due_has_time", "value": has_time, "valid_from": "now"},
                 {"subject": t["task"], "predicate": "times_postponed", "value": count, "valid_from": "now"}],
          events=[{"type": "task_postponed", "occurred_at": "now", "summary": f"Postponed: {t['title']}"[:160],
                   "attributes": {"reason_text": args.reason} if args.reason else {},
                   "links": [{"predicate": "about_task", "entity": t["task"]}]}])
    return {"ok": True, **public(one_task(mem, t["task"], now))}


def cmd_list(mem: Memory, args, now: datetime) -> dict:
    states = tuple(args.state.split(",")) if args.state else ("inbox", "next", "waiting")
    bad = [s for s in states if s not in STATES]
    if bad:
        raise ToolError(f"Unknown state {bad[0]!r}; use {', '.join(STATES)}")
    tasks = [public(t) for t in load_tasks(mem, states, now)]
    if args.area:
        area = resolve(mem, "area", args.area)
        tasks = [t for t in tasks if t.get("area") == area]
    if args.context:
        context = resolve(mem, "context", args.context)
        tasks = [t for t in tasks if t.get("context") == context]
    if args.project:
        tasks = [t for t in tasks if t.get("project_key") == f"project:{slug(args.project)}"]
    if args.due == "overdue":
        tasks = [t for t in tasks if t.get("overdue")]
    elif args.due == "today":
        tasks = [t for t in tasks if "due" in t and t["due_in_days"] <= 0]
    elif args.due == "week":
        tasks = [t for t in tasks if "due" in t and t["due_in_days"] <= 7]
    elif args.due == "none":
        tasks = [t for t in tasks if "due" not in t]
    return {"ok": True, "now": now.strftime("%Y-%m-%d %H:%M"), "count": len(tasks), "tasks": tasks}


def last_review(mem: Memory, now: datetime) -> dict:
    rows = mem.rows("--event-type", "review_done", "--column", "occurred_at", "--order-by", "desc:occurred_at")
    if not rows:
        return {"last_review": None, "days_since_review": None}
    when = datetime.fromisoformat(rows[0]["occurred_at"]).astimezone(now.tzinfo)
    return {"last_review": when.strftime("%Y-%m-%d"), "days_since_review": (now.date() - when.date()).days}


def cmd_brief(mem: Memory, args, now: datetime) -> dict:
    tasks = [public(t) for t in load_tasks(mem, ("inbox", "next", "waiting"), now)]
    week = now.date() + timedelta(days=7)
    return {"ok": True, **cmd_now(mem, args, now),
            "overdue": [t for t in tasks if t.get("overdue")],
            "today": [t for t in tasks if "due" in t and not t["overdue"] and t["due_in_days"] == 0],
            "hard_deadlines_next_7_days": [t for t in tasks if t.get("deadline") == "hard" and "due" in t
                                           and not t["overdue"] and 0 < t["due_in_days"] <= (week - now.date()).days],
            "inbox": [t for t in tasks if t["state"] == "inbox"],
            **last_review(mem, now),
            "counts": {s: sum(1 for t in tasks if t["state"] == s) for s in ("inbox", "next", "waiting")}}


def completed_since(mem: Memory, since: date) -> list[dict]:
    rows = mem.rows("--event-type", "task_completed", "--since", since.isoformat(),
                    "--column", "occurred_at", "--column", "link:about_task/key", "--column", "link:about_task/name",
                    "--column", "link:about_task/fact:in_area/key", "--column", "attr:days_from_due")
    return [{"task": r["link:about_task/key"], "title": r["link:about_task/name"], "done_at": r["occurred_at"],
             "area": r["link:about_task/fact:in_area/key"], "days_from_due": r["attr:days_from_due"]} for r in rows]


def cmd_review(mem: Memory, args, now: datetime) -> dict:
    if args.mark_done:
        if not args.by:
            raise ToolError("--mark-done needs --by person:<id>")
        write(mem, args.by, "weekly review done",
              events=[{"key": f"REVIEW_{now.date().isoformat()}", "type": "review_done", "occurred_at": "now",
                       "summary": "Weekly review done"}])
        return {"ok": True, "review_done": now.strftime("%Y-%m-%d")}
    tasks = [public(t) for t in load_tasks(mem, OPEN_STATES, now)]
    open_next = [t for t in tasks if t["state"] == "next"]
    projects = {}
    for p in mem.rows("--entity-type", "gtd_project", "--column", "key", "--column", "name"):
        projects[p["key"]] = {"project": p["key"], "name": p["name"],
                              "next_actions": sum(1 for t in open_next if t.get("project_key") == p["key"]),
                              "open": sum(1 for t in tasks if t.get("project_key") == p["key"])}
    return {"ok": True, **cmd_now(mem, args, now),
            "1_inbox": [t for t in tasks if t["state"] == "inbox"],
            "2_overdue": [t for t in tasks if t.get("overdue")],
            "3_next_14_days": [t for t in tasks if "due" in t and not t["overdue"] and t["due_in_days"] <= 14],
            "4_projects_without_next_action": [p for p in projects.values() if p["open"] and not p["next_actions"]],
            "5_waiting": [t for t in tasks if t["state"] == "waiting"],
            "6_stale_next_actions": [t for t in open_next if (t.get("days_in_state") or 0) >= 14 and "due" not in t],
            "7_someday": [t for t in tasks if t["state"] == "someday"],
            "8_done_last_7_days": completed_since(mem, now.date() - timedelta(days=7)),
            "projects": list(projects.values()), **last_review(mem, now)}


def cmd_stats(mem: Memory, args, now: datetime) -> dict:
    done = completed_since(mem, now.date() - timedelta(days=args.days))
    by_weekday = {d: 0 for d in WEEKDAYS}
    by_area: dict[str, int] = {}
    series: dict[str, list[int]] = {}
    for d in done:
        by_weekday[WEEKDAYS[datetime.fromisoformat(d["done_at"]).astimezone(now.tzinfo).weekday()]] += 1
        by_area[d["area"] or "no area"] = by_area.get(d["area"] or "no area", 0) + 1
        if d["task"] and d["days_from_due"] is not None:
            # a recurring task's occurrences share the key before "~": its timing pattern
            series.setdefault(d["task"].split("~")[0], []).append(d["days_from_due"])
    open_tasks = [public(t) for t in load_tasks(mem, ("inbox", "next", "waiting"), now)]
    return {"ok": True, "days": args.days, "completed": len(done), "completed_by_weekday": by_weekday,
            "completed_by_area": by_area,
            "most_postponed_open": sorted((t for t in open_tasks if t.get("times_postponed")),
                                          key=lambda t: -t["times_postponed"])[:10],
            "timing_by_task": [{"task": k, "completions": len(v), "avg_days_from_due": round(sum(v) / len(v), 1)}
                               for k, v in series.items()],
            "note": "Patterns to propose as rules; the owner approves them before they are stored."}


# -- CLI ---------------------------------------------------------------------------------------
def main() -> None:
    p = argparse.ArgumentParser(prog="todo.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--version", action="version", version=f"todo.py {__version__}")
    p.add_argument("--mem", help="Path to project-memory's memory.py")
    p.add_argument("--db", help="Path to the memory (default: the current project's)")
    p.add_argument("--tz", default=os.environ.get("HOWWARE_TZ") or local_offset(), help="UTC offset, e.g. --tz=-06:00")
    p.add_argument("--now", default=os.environ.get("TODO_NOW"), help=argparse.SUPPRESS)  # fixed clock for tests
    sub = p.add_subparsers(dest="command", required=True)

    def by(s, source=True):
        s.add_argument("--by", required=True, help="person:<id> of the owner")
        if source:
            s.add_argument("--source", help="The owner's literal words")
        return s

    by(sub.add_parser("setup"), source=False)
    sub.add_parser("now")
    s = by(sub.add_parser("capture"))
    s.add_argument("--title", required=True)
    for name in ("add-area", "add-context"):
        s = by(sub.add_parser(name))
        s.add_argument("--name", required=True)
        s.add_argument("--key")
        s.add_argument("--alias", action="append")
    s = by(sub.add_parser("clarify"))
    s.add_argument("task")
    s.add_argument("--state", help=" | ".join(STATES))
    s.add_argument("--title")
    s.add_argument("--next-action")
    s.add_argument("--area")
    s.add_argument("--context")
    s.add_argument("--project")
    s.add_argument("--due", help="YYYY-MM-DD or YYYY-MM-DD HH:MM")
    s.add_argument("--deadline", help="hard | soft")
    s.add_argument("--estimate", type=int, help="minutes")
    s.add_argument("--energy", help="low | medium | high")
    s.add_argument("--waiting-on")
    s.add_argument("--every", help=RULE_HELP)
    s = by(sub.add_parser("complete"))
    s.add_argument("task")
    s = by(sub.add_parser("postpone"))
    s.add_argument("task")
    s.add_argument("--to", required=True, help="YYYY-MM-DD or YYYY-MM-DD HH:MM")
    s.add_argument("--reason")
    s = sub.add_parser("list")
    s.add_argument("--state", help="comma-separated; default inbox,next,waiting")
    s.add_argument("--area")
    s.add_argument("--context")
    s.add_argument("--project")
    s.add_argument("--due", choices=["overdue", "today", "week", "none"])
    sub.add_parser("brief")
    s = sub.add_parser("review")
    s.add_argument("--mark-done", action="store_true", help="record that the weekly review was done today")
    s.add_argument("--by")
    s = sub.add_parser("stats")
    s.add_argument("--days", type=int, default=90)
    args = p.parse_args()

    commands = {"setup": cmd_setup, "now": cmd_now, "capture": cmd_capture, "clarify": cmd_clarify,
                "complete": cmd_complete, "postpone": cmd_postpone, "list": cmd_list, "brief": cmd_brief,
                "review": cmd_review, "stats": cmd_stats,
                "add-area": lambda m, a, n: cmd_add_named(m, a, n, "area"),
                "add-context": lambda m, a, n: cmd_add_named(m, a, n, "context")}
    try:
        now = current(args)
        if args.command == "now":
            result = cmd_now(None, args, now)  # type: ignore[arg-type]
        else:
            mem = Memory(find_helper(args.mem), args.db)
            mem.check_version()
            result = commands[args.command](mem, args, now)
        code = OK
    except ToolError as error:
        result, code = {"ok": False, "error": {"code": error.code, "message": str(error)}}, error.code
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(code)


if __name__ == "__main__":
    main()
