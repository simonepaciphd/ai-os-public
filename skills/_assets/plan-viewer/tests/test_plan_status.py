"""Tests for plan_status.py (standard library only). Usage: python test_plan_status.py

Each test copies the `ok/` fixture into a temporary folder (never the fixtures themselves);
git tests use a throwaway repo with a local bare remote.
"""
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOL = HERE.parent / "plan_status.py"
VIEWER = HERE.parent / "plan_viewer.py"
OK = HERE / "ok"
APPROVAL = '2026-10-31: "ok, the model run is done"'


def run(*args, cwd=None):
    p = subprocess.run([sys.executable, str(TOOL), *map(str, args)], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", cwd=cwd, timeout=120)
    return p.returncode, p.stdout + p.stderr


def git(repo, *args):
    p = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, encoding="utf-8")
    assert p.returncode == 0, p.stderr
    return p.stdout


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="plan-status-"))
        self.pdir = self.tmp / "repo" / "planning"
        shutil.copytree(OK, self.pdir)
        for f in self.pdir.glob("Plan-Visual.html"):
            f.unlink()
        self.plan = self.pdir / "PLAN.md"

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def text(self):
        return self.plan.read_text(encoding="utf-8")

    def row(self, tid):
        return next(l for l in self.text().splitlines() if l.startswith(f"| {tid} |"))

    def card_status(self, tid):
        t = self.text()
        i = t.index(f"### {tid} ")
        return next(l for l in t[i:].splitlines() if l.startswith("Status:"))

    def check_ok(self):
        p = subprocess.run([sys.executable, str(VIEWER), "--check", str(self.pdir)], capture_output=True,
                           text=True, encoding="utf-8")
        return p.returncode, p.stdout + p.stderr


class Authority(Base):
    def test_lane_sets_own_task_in_progress(self):
        before = hashlib.sha256(self.plan.read_bytes()).hexdigest()
        code, out = run(self.pdir, "T-002", "in-progress", "--as", "lane", "--lane", "analysis", "--date", "2026-10-31")
        self.assertEqual(code, 0, out)
        self.assertIn("| T-002 | analysis | W2 | in-progress |", self.row("T-002"))
        self.assertTrue(self.card_status("T-002").startswith("Status: in-progress — 2026-10-31, lane analysis"))
        self.assertTrue((self.pdir / "page" / "Plan-Visual.html").is_file())
        rc, chk = self.check_ok()
        self.assertEqual(rc, 0, chk)
        self.assertNotIn("W-STALE-LABELS", chk)
        self.assertNotIn("W-STATUS-SYNC", chk)
        labels = json.loads((self.pdir / "Plan-Labels.json").read_text(encoding="utf-8"))
        self.assertNotEqual(labels["sources"]["PLAN.md"], before)
        page = (self.pdir / "page" / "Plan-Visual.html").read_text(encoding="utf-8")
        self.assertIn('"st":"in-progress"', page)

    def test_only_status_lines_change(self):
        old = self.text().splitlines()
        code, out = run(self.pdir, "T-002", "blocked", "--as", "lane", "--lane", "analysis")
        self.assertEqual(code, 0, out)
        new = self.text().splitlines()
        self.assertEqual(len(old), len(new))
        changed = [i for i, (a, b) in enumerate(zip(old, new)) if a != b]
        self.assertEqual(len(changed), 2, changed)

    def test_lane_refused_on_other_lane(self):
        before = self.plan.read_bytes()
        code, out = run(self.pdir, "T-001", "in-progress", "--as", "lane", "--lane", "analysis")
        self.assertEqual(code, 3, out)
        self.assertEqual(self.plan.read_bytes(), before)

    def test_lane_cannot_complete(self):
        code, out = run(self.pdir, "T-002", "complete", "--as", "lane", "--lane", "analysis", "--evidence", "x")
        self.assertEqual(code, 3, out)

    def test_lane_needs_lane_flag(self):
        code, out = run(self.pdir, "T-002", "blocked", "--as", "lane")
        self.assertEqual(code, 3, out)

    def test_verified_needs_evidence(self):
        code, out = run(self.pdir, "T-002", "verified", "--as", "lane", "--lane", "analysis")
        self.assertEqual(code, 3, out)
        code, out = run(self.pdir, "T-002", "verified", "--as", "lane", "--lane", "analysis",
                        "--evidence", "https://github.com/o/r/pull/7")
        self.assertEqual(code, 0, out)
        self.assertIn("evidence: https://github.com/o/r/pull/7", self.card_status("T-002"))

    def test_integrator_completes_ungated(self):
        code, out = run(self.pdir, "T-002", "complete", "--as", "integrator", "--evidence", "PR #7")
        self.assertEqual(code, 0, out)
        self.assertIn("| complete |", self.row("T-002"))

    def test_gated_complete_needs_approval(self):
        # T-005 has researcher gates T-003, T-004; T-003 is a researcher-lane task
        for tid in ("T-005", "T-003"):
            code, out = run(self.pdir, tid, "complete", "--as", "integrator", "--evidence", "PR #9")
            self.assertEqual(code, 3, out)
            code, out = run(self.pdir, tid, "complete", "--as", "integrator", "--evidence", "PR #9",
                            "--approval", "ok")
            self.assertEqual(code, 3, out)
            code, out = run(self.pdir, tid, "complete", "--as", "integrator", "--evidence", "PR #9",
                            "--approval", APPROVAL)
            self.assertEqual(code, 0, out)
            self.assertIn("approval: " + APPROVAL, self.card_status(tid))

    def test_bad_status_and_unknown_task(self):
        self.assertEqual(run(self.pdir, "T-002", "done", "--as", "integrator")[0], 2)
        self.assertEqual(run(self.pdir, "T-999", "blocked", "--as", "integrator")[0], 1)

    def test_dry_run_writes_nothing(self):
        before = self.plan.read_bytes()
        code, out = run(self.pdir, "T-002", "blocked", "--as", "lane", "--lane", "analysis", "--dry-run")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.plan.read_bytes(), before)
        self.assertFalse((self.pdir / "page").exists())


class Formats(Base):
    def test_qualified_cell_and_missing_card_line(self):
        t = self.text()
        t = t.replace("| T-002 | analysis | W2 | pending |", "| T-002 | analysis | W2 | pending; artifact absent |")
        i = t.index("### T-002 ")
        j = t.index("Status: pending", i)
        t = t[:j] + t[j + len("Status: pending\n"):]
        self.plan.write_text(t, encoding="utf-8", newline="\n")
        code, out = run(self.pdir, "T-002", "blocked", "--as", "lane", "--lane", "analysis", "--note", "waiting on RS-003")
        self.assertEqual(code, 0, out)
        self.assertIn("| T-002 | analysis | W2 | blocked |", self.row("T-002"))
        self.assertIn("note: waiting on RS-003", self.card_status("T-002"))
        rc, chk = self.check_ok()
        self.assertEqual(rc, 0, chk)
        self.assertNotIn("W-STATUS-SYNC", chk)

    def test_crlf_preserved(self):
        self.plan.write_bytes(self.plan.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
        code, out = run(self.pdir, "T-002", "blocked", "--as", "lane", "--lane", "analysis")
        self.assertEqual(code, 0, out)
        raw = self.plan.read_bytes()
        self.assertNotIn(b"\n", raw.replace(b"\r\n", b""))

    def test_flat_layout_keeps_page_path(self):
        (self.pdir / "Plan-Visual.html").write_text("old", encoding="utf-8")
        code, out = run(self.pdir, "T-002", "blocked", "--as", "lane", "--lane", "analysis")
        self.assertEqual(code, 0, out)
        self.assertNotEqual((self.pdir / "Plan-Visual.html").read_text(encoding="utf-8"), "old")
        self.assertFalse((self.pdir / "page").exists())

    def test_refuses_broken_plan(self):
        self.plan.write_text(self.text().replace("## Task cards", "## Cards"), encoding="utf-8")
        before = self.plan.read_bytes()
        code, out = run(self.pdir, "T-002", "blocked", "--as", "lane", "--lane", "analysis")
        self.assertEqual(code, 1, out)
        self.assertEqual(self.plan.read_bytes(), before)


class Git(Base):
    def setUp(self):
        super().setUp()
        self.repo = self.tmp / "repo"
        self.remote = self.tmp / "remote.git"
        subprocess.run(["git", "init", "--bare", "-q", "-b", "main", str(self.remote)], check=True)
        git(self.repo, "init", "-q", "-b", "main")
        git(self.repo, "config", "user.email", "t@example.invalid")
        git(self.repo, "config", "user.name", "test")
        (self.repo / "other.txt").write_text("a\n", encoding="utf-8")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "init")
        git(self.repo, "remote", "add", "origin", str(self.remote))
        git(self.repo, "push", "-q", "-u", "origin", "main")

    def test_commit_and_push_only_plan_files(self):
        (self.repo / "other.txt").write_text("dirty\n", encoding="utf-8")
        code, out = run(self.pdir, "T-002", "verified", "--as", "lane", "--lane", "analysis",
                        "--evidence", "PR #3", "--commit", "--push")
        self.assertEqual(code, 0, out)
        files = git(self.repo, "show", "--name-only", "--format=", "HEAD").split()
        self.assertEqual(sorted(files), ["planning/PLAN.md", "planning/Plan-Labels.json", "planning/page/Plan-Visual.html"])
        self.assertIn("T-002: status -> verified", git(self.repo, "log", "-1", "--format=%s"))
        self.assertEqual(git(self.remote, "rev-parse", "main").strip(), git(self.repo, "rev-parse", "HEAD").strip())
        self.assertIn("other.txt", git(self.repo, "status", "--porcelain"))

    def test_commit_refused_when_plan_dirty(self):
        self.plan.write_text(self.text() + "\n", encoding="utf-8")
        code, out = run(self.pdir, "T-002", "blocked", "--as", "lane", "--lane", "analysis", "--commit")
        self.assertEqual(code, 4, out)


if __name__ == "__main__":
    unittest.main(verbosity=1)
