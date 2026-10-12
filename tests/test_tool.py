"""Tests of todo.py. Recurrence and date logic without memory; workflows against a real, temporary memory with a
fixed clock (--now). Synthetic data only."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import date, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "skill" / "todo" / "scripts" / "todo.py"
sys.path.insert(0, str(TOOL.parent))
import todo  # noqa: E402

BY = "person:test"
NOW = "2026-10-12T09:00"  # a Monday


def find_helper() -> Path | None:
    for c in (os.environ.get("HOWWARE_MEMORY_HELPER"), ROOT.parent / "long-term-memory-for-AI" / "db" / "memory.py",
              Path.home() / ".claude/skills/project-memory/scripts/memory.py"):
        if c and Path(c).is_file():
            return Path(c)
    return None


HELPER = find_helper()


class RecurrenceTest(unittest.TestCase):
    def nxt(self, rule: str, previous: str) -> str:
        return todo.next_occurrence(todo.check_rule(rule), date.fromisoformat(previous)).isoformat()

    def test_rules(self):
        cases = [
            ("daily", "2026-10-12", "2026-10-13"),
            ("days:14", "2026-10-12", "2026-10-26"),
            ("weekly:tue", "2026-10-12", "2026-10-13"),
            ("weekly:tue", "2026-10-13", "2026-10-20"),
            ("weekly:mon,thu", "2026-10-12", "2026-10-15"),
            ("monthly:10", "2026-10-10", "2026-11-10"),
            ("monthly:10", "2026-10-13", "2026-11-10"),
            ("monthly:31", "2026-01-31", "2026-02-28"),
            ("monthly:31", "2026-02-28", "2026-03-31"),
            ("monthly:last", "2026-02-28", "2026-03-31"),
            ("monthly:last-fri", "2026-10-30", "2026-11-27"),
            ("monthly:1-mon", "2026-10-05", "2026-11-02"),
            ("yearly:02-29", "2027-03-01", "2028-02-29"),
            ("yearly:02-29", "2026-03-01", "2027-02-28"),
            ("yearly:04-30", "2026-04-30", "2027-04-30"),
        ]
        for rule, previous, expected in cases:
            self.assertEqual(self.nxt(rule, previous), expected, f"{rule} after {previous}")

    def test_rejects_unknown_rules(self):
        for rule in ("every monday", "monthly:32", "weekly:", "days:0", "monthly:5-fri", "yearly:13-01"):
            with self.assertRaises(todo.ToolError, msg=rule):
                todo.check_rule(rule)

    def test_due_parsing(self):
        tz = todo.parse_offset("-06:00")
        due, has_time = todo.parse_due("2026-10-13", tz)
        self.assertEqual((due.hour, has_time), (12, False))
        due, has_time = todo.parse_due("2026-10-13 18:30", tz)
        self.assertEqual((due.hour, due.minute, has_time), (18, 30, True))
        for bad in ("mañana", "13/10/2026", "2026-13-01"):
            with self.assertRaises(todo.ToolError, msg=bad):
                todo.parse_due(bad, tz)

    def test_overdue_rules(self):
        tz = todo.parse_offset("-06:00")
        now = todo.datetime(2026, 10, 12, 9, 0, tzinfo=tz)
        same_day_no_time = todo.describe_due(*todo.parse_due("2026-10-12", tz), now)
        self.assertFalse(same_day_no_time["overdue"])          # a date without time is due all day
        earlier_today = todo.describe_due(*todo.parse_due("2026-10-12 08:00", tz), now)
        self.assertTrue(earlier_today["overdue"])
        self.assertEqual(todo.describe_due(*todo.parse_due("2026-10-09", tz), now)["days_overdue"], 3)


class ContractTest(unittest.TestCase):
    def run_tool(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(TOOL), *args], capture_output=True, text=True, encoding="utf-8")

    def test_version_and_now(self):
        self.assertIn("todo.py ", self.run_tool("--version").stdout)
        out = json.loads(self.run_tool("--tz=-06:00", "--now", NOW, "now").stdout)
        self.assertEqual((out["date"], out["weekday"], out["tomorrow"]), ("2026-10-12", "mon", "2026-10-13"))

    def test_bad_clock_is_a_json_error(self):
        proc = self.run_tool("--now", "yesterday", "now")
        self.assertEqual(proc.returncode, 2)
        self.assertEqual(json.loads(proc.stdout)["error"]["code"], 2)


@unittest.skipUnless(HELPER, "project-memory is not installed")
class WorkflowTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = str(Path(self.tmp.name) / "memory.sqlite")
        subprocess.run([sys.executable, str(HELPER), "--db", self.db, "init", "--owner-name", "Test",
                        "--owner-key", BY], check=True, capture_output=True)
        self.tool("setup", "--by", BY)

    def tearDown(self):
        self.tmp.cleanup()

    def tool(self, *args: str, code: int = 0, now: str = NOW) -> dict:
        proc = subprocess.run([sys.executable, str(TOOL), "--mem", str(HELPER), "--db", self.db, "--tz=-06:00",
                               "--now", now, *args], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(proc.returncode, code, proc.stdout + proc.stderr)
        return json.loads(proc.stdout)

    def capture(self, title: str) -> str:
        return self.tool("capture", "--title", title, "--by", BY)["task"]

    def test_capture_is_idempotent_and_lands_in_inbox(self):
        key = self.capture("Call the accountant")
        again = self.tool("capture", "--title", "Call the accountant", "--by", BY)
        self.assertEqual(again["task"], key)
        self.assertFalse(again["created"])
        brief = self.tool("brief")
        self.assertEqual([t["task"] for t in brief["inbox"]], [key])
        self.assertEqual(brief["counts"]["inbox"], 1)

    def test_areas_are_the_owners_and_contexts_resolve_by_alias(self):
        key = self.capture("Pay electricity")
        error = self.tool("clarify", key, "--area", "Casa", "--by", BY, code=2)
        self.assertIn("add-area", error["error"]["message"])
        self.tool("add-area", "--name", "Casa", "--by", BY)
        task = self.tool("clarify", key, "--state", "next", "--area", "Casa", "--context", "Computadora", "--by", BY)
        self.assertEqual((task["area"], task["context"]), ("area:casa", "context:computer"))
        listed = self.tool("list", "--area", "casa")["tasks"]
        self.assertEqual([t["task"] for t in listed], [key])

    def test_overdue_postpone_and_recurring_series(self):
        key = self.capture("Pay electricity")
        self.tool("clarify", key, "--state", "next", "--due", "2026-10-10", "--deadline", "hard", "--every",
                  "monthly:10", "--by", BY)
        overdue = self.tool("brief")["overdue"]
        self.assertEqual((overdue[0]["task"], overdue[0]["days_overdue"]), (key, 2))
        moved = self.tool("postpone", key, "--to", "2026-10-13 18:00", "--reason", "no time today", "--by", BY)
        self.assertEqual((moved["due"], moved["times_postponed"], moved["overdue"]), ("2026-10-13 18:00", 1, False))
        done = self.tool("complete", key, "--by", BY)
        nxt = done["next_occurrence"]
        # the series keeps its own schedule: the 10th, without the postponed time
        self.assertEqual((nxt["task"], nxt["due"], nxt["has_time"], nxt["times_postponed"]),
                         (f"{key}~2026-11-10", "2026-11-10", False, 0))
        self.assertEqual(self.tool("complete", nxt["task"], "--by", BY)["next_occurrence"]["due"], "2026-12-10")
        self.tool("complete", key, "--by", BY, code=2)        # already done

    def test_waiting_project_review_and_stats(self):
        a = self.capture("Get the tax return from the accountant")
        self.tool("clarify", a, "--state", "waiting", "--waiting-on", "the accountant", "--project", "Annual taxes",
                  "--by", BY)
        b = self.capture("Buy a gift")
        self.tool("clarify", b, "--state", "someday", "--by", BY)
        self.capture("Fix the faucet")
        review = self.tool("review")
        self.assertEqual(len(review["1_inbox"]), 1)
        self.assertEqual([p["name"] for p in review["4_projects_without_next_action"]], ["Annual taxes"])
        self.assertEqual([t["task"] for t in review["5_waiting"]], [a])
        self.assertEqual([t["task"] for t in review["7_someday"]], [b])
        self.assertIsNone(self.tool("brief")["days_since_review"])
        self.tool("review", "--mark-done", "--by", BY)
        self.assertIsNotNone(self.tool("brief")["last_review"])
        c = self.capture("Send invoice")
        self.tool("clarify", c, "--state", "next", "--due", "2026-10-15", "--by", BY)
        self.tool("complete", c, "--by", BY)
        stats = self.tool("stats")
        self.assertEqual(stats["completed"], 1)
        self.assertEqual(stats["timing_by_task"][0]["avg_days_from_due"], -3.0)

    def test_invalid_input_is_rejected(self):
        key = self.capture("Something")
        for args in (["--due", "mañana"], ["--every", "cada lunes"], ["--energy", "huge"], ["--deadline", "maybe"],
                     ["--state", "doing"], ["--estimate", "0"], []):
            self.tool("clarify", key, *args, "--by", BY, code=2)
        self.tool("complete", "task:missing", "--by", BY, code=2)


if __name__ == "__main__":
    unittest.main()
