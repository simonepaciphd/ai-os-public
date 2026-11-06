"""Set one task's status in a plan, rebuild its page, and optionally commit and push.

Usage:
    python plan_status.py <planning-dir> <T-###> <status> --as lane --lane <slug> [--evidence TEXT]
    python plan_status.py <planning-dir> <T-###> <status> --as integrator [--evidence TEXT] [--approval TEXT]
    options: [--note TEXT] [--out PAGE.html] [--date YYYY-MM-DD] [--dry-run] [--commit [--push]]

What it does (planning-protocol v0.8):
  1. Refuses unless the plan passes `plan_viewer.py --check` before the edit.
  2. Checks who may set what:
       --as lane        own task only (--lane must equal the task's lane): in-progress, blocked, verified
       --as integrator  any status; only the integrator marks complete
     verified and complete need --evidence (a PR/commit link or a path).
     complete on a task with a human decision gate (researcher lane, or a non-empty
     `Researcher gates` cell / card line) also needs --approval: the user's words with the
     date, `YYYY-MM-DD: "<the user's words>"`.
  3. Writes the status word into the Task graph `Status` cell (authoritative) and the card's
     `Status:` line (word + date, who, evidence, approval, note). Nothing else in PLAN.md changes.
  4. Re-runs the check (restores PLAN.md if it now fails), refreshes the PLAN.md hash in
     Plan-Labels.json only when the labels were current before the edit (a status change does
     not change any label), and rebuilds the page.
  5. --commit commits only PLAN.md, Plan-Labels.json and the page (refused if any of them had
     uncommitted changes before the run). --push pushes that commit to the current branch's
     upstream; the plan page publishes only from the default branch.

Exit: 0 ok; 1 plan errors; 2 usage/IO; 3 refused (authority, evidence, approval); 4 git failure.
Standard library only; imports plan_viewer.py from this folder.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import plan_viewer as pv  # noqa: E402

LANE_STATUSES = ("in-progress", "blocked", "verified")
NEEDS_EVIDENCE = ("verified", "complete")
APPROVAL_RE = re.compile(r'^\d{4}-\d{2}-\d{2}\s*:?\s*".+"\s*$', re.DOTALL)
GATES_LINE_RE = re.compile(r"^\s*[-*+]\s*Researcher gates\s*:\s*(.*?)\s*$", re.IGNORECASE)
STATUS_LINE_RE = re.compile(r"^(\s*)Status\s*:", re.IGNORECASE)


class Refused(Exception):
    """Authority, evidence or approval check failed (exit 3)."""


def cell_spans(line: str) -> list[tuple[int, int]]:
    """(start, end) of each cell's text in a Markdown table row, honouring `\\|` escapes."""
    bars = [i for i, ch in enumerate(line) if ch == "|" and (i == 0 or line[i - 1] != "\\")]
    if not bars:
        return []
    lead = line[:bars[0]].strip() == ""
    trail = line[bars[-1] + 1:].strip() == ""
    cuts = bars if lead else [-1] + bars
    if not trail:
        cuts = cuts + [len(line)]
    return [(cuts[k] + 1, cuts[k + 1]) for k in range(len(cuts) - 1)]


def set_cell(line: str, col: int, value: str) -> str:
    spans = cell_spans(line)
    a, b = spans[col]
    return line[:a] + f" {value} " + line[b:]


def header_index(lines: list[str], row_idx: int) -> dict[str, int]:
    """Column name -> index for the table containing lines[row_idx] (header is above the separator)."""
    i = row_idx
    while i > 0 and not pv.SEP_RE.match(lines[i].strip()):
        i -= 1
    head = lines[i - 1]
    return {pv._split_row(head)[k].strip().lower(): k for k in range(len(pv._split_row(head)))}


def is_gated(task: dict, card_lines: list[str], row: list[str], cols: dict[str, int]) -> bool:
    if task["lane"] == pv.RESEARCHER:
        return True
    k = cols.get("researcher gates")
    if k is not None and k < len(row) and row[k].strip().lower() not in pv.NONE_VALUES:
        return True
    for ln in card_lines:
        m = GATES_LINE_RE.match(ln)
        if m and m.group(1).strip().lower() not in pv.NONE_VALUES:
            return True
    return False


def card_range(lines: list[str], card_line: int) -> tuple[int, int]:
    """0-based [start, end) of a card: its heading to the next level-2/3 heading."""
    lo = card_line - 1
    hi = lo + 1
    while hi < len(lines) and not re.match(r"^#{2,3}\s", lines[hi]):
        hi += 1
    return lo, hi


def check(planning_dir: Path):
    model, problems = pv.parse_planning(planning_dir)
    problems = problems + pv.validate(model)
    return model, [p for p in problems if p.is_error]


def git(repo: Path, *args, check_rc=True):
    p = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if check_rc and p.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {(p.stderr or p.stdout).strip()}")
    return p


def default_page(planning_dir: Path) -> Path:
    if (planning_dir / "page").is_dir() or not (planning_dir / pv.OUT_NAME).exists():
        return planning_dir / "page" / pv.OUT_NAME  # v0.7+ layout
    return planning_dir / pv.OUT_NAME  # older flat layout keeps its page path


def run(a) -> int:
    pdir = a.planning_dir.resolve()
    plan_path = pdir / pv.PLAN
    if not plan_path.is_file():
        print(f"error: no {pv.PLAN} in {pdir}", file=sys.stderr)
        return 2
    if a.status not in pv.STATUSES:
        print(f"error: status must be one of {', '.join(pv.STATUSES)}", file=sys.stderr)
        return 2
    date = a.date or _dt.date.today().isoformat()

    model, errors = check(pdir)
    if errors:
        for p in errors:
            print(p, file=sys.stderr)
        print(f"{len(errors)} error(s) before the edit; fix the plan first (nothing written)", file=sys.stderr)
        return 1
    task = next((t for t in model["plan"]["tasks"] if t["id"] == a.task), None)
    if task is None:
        print(f"error: {a.task} is not in the Task graph", file=sys.stderr)
        return 1
    card = model["plan"]["cards"].get(a.task)

    raw = plan_path.read_bytes()
    text = raw.decode("utf-8-sig")
    bom = raw.startswith(b"\xef\xbb\xbf")
    nl = "\r\n" if "\r\n" in text else "\n"
    lines = text.split(nl)
    row_i = task["line"] - 1
    cols = header_index(lines, row_i)
    if "status" not in cols:
        print(f"error: the Task graph has no Status column; add one (template PLAN.md) first", file=sys.stderr)
        return 1
    row = pv._split_row(lines[row_i])
    c_lo, c_hi = card_range(lines, card["line"]) if card else (0, 0)
    gated = is_gated(task, lines[c_lo:c_hi], row, cols)

    # Authority (C1, C2)
    if a.role == "lane":
        if a.status not in LANE_STATUSES:
            raise Refused(f"a lane may set only {', '.join(LANE_STATUSES)}; '{a.status}' is the integrator's")
        if not a.lane:
            raise Refused("--as lane needs --lane <your lane slug>")
        if a.lane != task["lane"]:
            raise Refused(f"{a.task} belongs to lane '{task['lane']}', not '{a.lane}'; a lane sets only its own tasks")
    if a.status in NEEDS_EVIDENCE and not (a.evidence or "").strip():
        raise Refused(f"'{a.status}' needs --evidence (PR/commit link or path)")
    if a.status == "complete" and gated:
        if not a.approval or not APPROVAL_RE.match(a.approval.strip()):
            raise Refused(f'{a.task} has a human decision gate: complete needs --approval \'YYYY-MM-DD: "<the user\'s words>"\'')

    # Edit: table cell (authoritative) + card line
    new_lines = list(lines)
    new_lines[row_i] = set_cell(lines[row_i], cols["status"], a.status)
    who = f"lane {a.lane}" if a.role == "lane" else "integrator"
    parts = [f"{date}, {who}"]
    if a.evidence:
        parts.append(f"evidence: {a.evidence.strip()}")
    if a.approval:
        parts.append(f"approval: {a.approval.strip()}")
    if a.note:
        parts.append(f"note: {a.note.strip()}")
    status_line = f"Status: {a.status} — " + "; ".join(parts)
    if card:
        if card.get("status_line"):
            k = card["status_line"] - 1
            indent = STATUS_LINE_RE.match(new_lines[k]).group(1)
            new_lines[k] = indent + status_line
        else:
            new_lines[c_lo + 1:c_lo + 1] = ["", status_line]
    new_text = nl.join(new_lines)
    if new_text == text:
        print(f"{a.task} already '{a.status}' with the same record; nothing to do")
        return 0

    if a.dry_run:
        print(f"row:  {new_lines[row_i].strip()}")
        print(f"card: {status_line}")
        return 0

    repo = None
    paths = []
    if a.commit:
        top = git(pdir, "rev-parse", "--show-toplevel", check_rc=False)
        if top.returncode != 0:
            print("error: --commit needs the plan to be in a git repo", file=sys.stderr)
            return 4
        repo = Path(top.stdout.strip())
        out_path = (a.out or default_page(pdir)).resolve()
        paths = [plan_path, out_path] + ([pdir / pv.LABELS] if (pdir / pv.LABELS).exists() else [])
        rel = [os.path.relpath(p, repo) for p in paths]
        dirty = git(repo, "status", "--porcelain", "--", *rel).stdout.strip()
        if dirty:
            print(f"error: uncommitted changes in plan files; commit or stash them first:\n{dirty}", file=sys.stderr)
            return 4

    old_sha = hashlib.sha256(raw).hexdigest()
    new_raw = (b"\xef\xbb\xbf" if bom else b"") + new_text.encode("utf-8")
    tmp = plan_path.with_name(plan_path.name + ".tmp-status")
    tmp.write_bytes(new_raw)
    os.replace(tmp, plan_path)

    _, errors = check(pdir)
    if errors:
        plan_path.write_bytes(raw)
        for p in errors:
            print(p, file=sys.stderr)
        print("the edit broke the plan check; PLAN.md restored", file=sys.stderr)
        return 1

    labels_note = ""
    lab_path = pdir / pv.LABELS
    if lab_path.exists():
        lt = lab_path.read_text(encoding="utf-8-sig")
        if old_sha in lt:
            new_sha = hashlib.sha256(new_raw).hexdigest()
            lab_path.write_text(lt.replace(old_sha, new_sha), encoding="utf-8", newline="")
            labels_note = "; label hash refreshed"
        else:
            labels_note = "; labels were already stale (writer pass due)"

    out = (a.out or default_page(pdir)).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    rc = pv.main([str(pdir), "-o", str(out)])
    if rc != 0:
        print("page build failed after the status edit; PLAN.md keeps the new status", file=sys.stderr)
        return rc
    print(f"{a.task}: {task.get('status') or '?'} -> {a.status}{labels_note}")

    if a.commit:
        rel = [os.path.relpath(p, repo) for p in paths if p.exists()]
        try:
            git(repo, "add", "--", *rel)
            msg = f"{a.task}: status -> {a.status}\n\n{status_line}\n\nSet with plan_status.py ({who})."
            git(repo, "commit", "-m", msg, "--", *rel)
            print("committed: " + git(repo, "rev-parse", "--short", "HEAD").stdout.strip())
            if a.push:
                branch = git(repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
                head = git(repo, "symbolic-ref", "--short", "refs/remotes/origin/HEAD", check_rc=False).stdout.strip()
                if head and head.split("/", 1)[-1] != branch:
                    print(f"note: on '{branch}', not the default branch '{head}'; the page publishes only from the default branch")
                git(repo, "push")
                print("pushed")
        except RuntimeError as e:
            print(f"error: {e}\n(the status edit and page are written; if the push was rejected, "
                  f"`git pull --rebase` and push again)", file=sys.stderr)
            return 4
    return 0


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="backslashreplace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(prog="plan_status.py", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("planning_dir", type=Path)
    ap.add_argument("task")
    ap.add_argument("status")
    ap.add_argument("--as", dest="role", choices=("lane", "integrator"), required=True)
    ap.add_argument("--lane")
    ap.add_argument("--evidence")
    ap.add_argument("--approval")
    ap.add_argument("--note")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--date")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--commit", action="store_true")
    ap.add_argument("--push", action="store_true")
    a = ap.parse_args(argv)
    if a.push and not a.commit:
        print("error: --push needs --commit", file=sys.stderr)
        return 2
    if a.date and not pv.DATE_RE.match(a.date):
        print("error: --date must be YYYY-MM-DD", file=sys.stderr)
        return 2
    for name in ("evidence", "approval", "note"):
        v = getattr(a, name)
        if v and ("\n" in v or "\r" in v):
            print(f"error: --{name} must be one line", file=sys.stderr)
            return 2
    try:
        return run(a)
    except Refused as e:
        print(f"refused: {e}", file=sys.stderr)
        return 3
    except OSError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
