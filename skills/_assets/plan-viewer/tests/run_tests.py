"""Fixture tests for plan_viewer.py (standard library only).

Usage: python run_tests.py
Runs `plan_viewer.py --check` on every fixture folder beside this file and a
determinism check on ok/, plus a static check of the replication-package
tree in template.html. Exits non-zero on any failure.
"""
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOL = HERE.parent / "plan_viewer.py"
MSG_RE = re.compile(r"^(ERROR|WARN) ([EW]-[A-Z-]+):", re.MULTILINE)
BASE_WARN = {"W-UNTYPED"}  # ok/ has one untyped deliverable; every copy inherits it
# folder -> {rule: IDs that must each appear in one of that rule's messages}
MUST_NAME = {"warn-W-TYPE-FIELDS": {"W-TYPE-FIELDS": ["D-005", "D-008"]},
             "fail-E-STRUCTURE-dp": {"E-STRUCTURE": ["DP-003"]},
             "fail-E-CLASSES-gatemode": {"E-CLASSES": ["items.DP-001"]},
             "fail-E-PHASE": {"E-PHASE": ["T-006"]},
             "fail-E-PHASE-unknown": {"E-PHASE": ["T-006"]},
             "fail-E-PHASE-undeclared": {"E-PHASE": ["T-001"]}}
OK_FOLDERS = ("ok", "ok-phases")


def expected(folder):
    """(exit code, expected errors, expected warnings or None = not checked)."""
    if folder in OK_FOLDERS:
        return 0, set(), set(BASE_WARN)
    kind, rule = folder.split("-", 1)
    rule = re.sub(r"-[a-z][a-z0-9-]*$", "", rule)  # fail-E-STRUCTURE-dp -> E-STRUCTURE
    if kind == "fail":
        return 1, {rule}, None
    if kind == "warn":
        return 0, set(), BASE_WARN | {rule}
    raise ValueError(folder)


def run(args):
    p = subprocess.run([sys.executable, str(TOOL), *args], capture_output=True,
                       text=True, encoding="utf-8", errors="replace", timeout=120)
    return p.returncode, p.stdout + p.stderr


def check_folder(folder):
    want_code, want_err, want_warn = expected(folder.name)
    out_html = folder / "Plan-Visual.html"
    existed = out_html.exists()
    code, out = run(["--check", str(folder)])
    errs = {r for k, r in MSG_RE.findall(out) if k == "ERROR"}
    warns = {r for k, r in MSG_RE.findall(out) if k == "WARN"}
    problems = []
    if code != want_code:
        problems.append(f"exit {code}, expected {want_code}")
    missing = (want_err | (want_warn or set())) - (errs | warns)
    if missing:
        problems.append("missing " + ", ".join(sorted(missing)))
    if errs - want_err:
        problems.append("unexpected errors " + ", ".join(sorted(errs - want_err)))
    if want_warn is not None and warns - want_warn:
        problems.append("unexpected warnings " + ", ".join(sorted(warns - want_warn)))
    for rule, ids in MUST_NAME.get(folder.name, {}).items():
        lines = [ln for ln in out.splitlines() if f" {rule}:" in ln]
        unnamed = [i for i in ids if not any(f" {i}:" in ln for ln in lines)]
        if unnamed:
            problems.append(f"{rule} does not name " + ", ".join(unnamed))
    if not existed and out_html.exists():
        problems.append("--check wrote Plan-Visual.html")
    seen = ", ".join(sorted(errs | warns)) or "-"
    return not problems, seen, "; ".join(problems), out


def check_determinism(folder):
    with tempfile.TemporaryDirectory() as tmp:
        outs = [Path(tmp) / f"build{i}.html" for i in (1, 2)]
        for o in outs:
            code, out = run([str(folder), "-o", str(o), "--built", "2026-01-01"])
            if code != 0 or not o.is_file():
                return False, f"build exit {code}: {out.strip()[-300:]}"
        a, b = (o.read_bytes() for o in outs)
        if a != b:
            return False, "outputs differ"
        if b"/*__PLAN_DATA__*/null" in a:
            return False, "data placeholder not replaced"
        return True, f"identical ({len(a)} bytes)"


def page_data(folder):
    """Build `folder` and return the injected page JSON (FORMAT.md section 10)."""
    with tempfile.TemporaryDirectory() as tmp:
        o = Path(tmp) / "p.html"
        code, out = run([str(folder), "-o", str(o), "--built", "2026-01-01"])
        if code != 0:
            raise RuntimeError(f"build exit {code}: {out.strip()[-300:]}")
        html = o.read_text(encoding="utf-8")
    m = re.search(r"const PLAN = (\{.*?\});\n", html, re.DOTALL)
    return json.loads(m.group(1).replace("<\\/", "</"))


def check_phases():
    """Phases reach the page from ok-phases/; ok/ (no phases) emits an empty list and null `ph`."""
    p, q = page_data(HERE / "ok-phases"), page_data(HERE / "ok")
    problems = []
    if [x["k"] for x in p.get("phases", [])] != ["PH-1", "PH-2", "PH-3"]:
        problems.append(f"ok-phases phases {p.get('phases')}")
    if {t["id"]: t["ph"] for t in p["tasks"]}.get("T-006") != "PH-2":
        problems.append("ok-phases T-006 ph is not PH-2")
    if q.get("phases") != [] or any(t.get("ph") is not None for t in q["tasks"]):
        problems.append("ok/ should emit phases [] and ph null")
    return not problems, "; ".join(problems) or "ok-phases: 3 phases, T-006 in PH-2; ok/: none"


def check_repl_tree():
    """Static check of the replication-package tree in template.html (FORMAT.md §3)."""
    src = (TOOL.parent / "template.html").read_text(encoding="utf-8")
    m = re.search(r"function mockRepl\(f\)\{(.*?)\n\}\n", src, re.DOTALL)
    if not m:
        return False, "mockRepl not found in template.html"
    body = m.group(1)
    order = ["dir('data/'", "dir('inputs/'", "dsets.map(x => file(", "dir('outputs/'",
             "dir('scripts/'", "dir('ai-disclosure/', 'AI-use disclosure (system-dependent)'"]
    pos = [body.find(s) for s in order]
    problems = [f"missing {s}" for s, p in zip(order, pos) if p < 0]
    if not problems and pos != sorted(pos):
        problems.append("tree order is not data/{inputs/, datasets} outputs/ scripts/ ai-disclosure/")
    if body.count("dir('inputs/'") != 1:
        problems.append("inputs/ must appear once, inside data/")
    if "archive/" in body:
        problems.append("archive/ must not be drawn")
    return not problems, "; ".join(problems) or "data/inputs/, datasets in data/, ai-disclosure/"


def main():
    if not TOOL.is_file():
        print(f"plan_viewer.py not found at {TOOL}")
        return 2
    folders = sorted(p for p in HERE.iterdir()
                     if p.is_dir() and (p.name in OK_FOLDERS or p.name.startswith(("fail-", "warn-"))))
    rows, failed = [], 0
    for f in folders:
        try:
            ok, seen, why, out = check_folder(f)
        except subprocess.TimeoutExpired:
            ok, seen, why, out = False, "-", "timed out", ""
        rows.append((f.name, "PASS" if ok else "FAIL", seen, why))
        if not ok:
            failed += 1
            if out:
                rows.append(("", "", "", "output: " + " | ".join(out.strip().splitlines()[:6])))
    try:
        ok, why = check_determinism(HERE / "ok")
    except subprocess.TimeoutExpired:
        ok, why = False, "timed out"
    rows.append(("ok (build x2)", "PASS" if ok else "FAIL", "-", why))
    failed += not ok
    try:
        ok, why = check_determinism(HERE / "ok-phases")
    except subprocess.TimeoutExpired:
        ok, why = False, "timed out"
    rows.append(("ok-phases (build x2)", "PASS" if ok else "FAIL", "-", why))
    failed += not ok
    try:
        ok, why = check_phases()
    except Exception as e:  # noqa: BLE001 - report, do not crash the table
        ok, why = False, f"{type(e).__name__}: {e}"
    rows.append(("phase page data", "PASS" if ok else "FAIL", "-", why))
    failed += not ok
    ok, why = check_repl_tree()
    rows.append(("replication tree", "PASS" if ok else "FAIL", "-", why))
    failed += not ok

    w =[max(len(r[i]) for r in rows + [("Fixture", "Result", "Rules seen", "")]) for i in range(3)]
    print(f"{'Fixture':<{w[0]}}  {'Result':<{w[1]}}  {'Rules seen':<{w[2]}}  Notes")
    for r in rows:
        print(f"{r[0]:<{w[0]}}  {r[1]:<{w[1]}}  {r[2]:<{w[2]}}  {r[3]}")
    total = len(folders) + 4
    print(f"\n{total - failed}/{total} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
