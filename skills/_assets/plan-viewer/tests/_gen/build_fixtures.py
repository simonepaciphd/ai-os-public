"""Generate plan-viewer test fixtures from source/*.md. Labels hashes are written last.

Usage: python build_fixtures.py [out-dir]   (default out-dir: the tests/ folder above this one)
Rewrites ok/ and every fail-*/warn-* variant folder in out-dir.
"""
import hashlib, json, shutil, sys
from pathlib import Path

GEN = Path(__file__).resolve().parent
SRC = GEN / "source"
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else GEN.parent
SOURCES = ["SPEC.md", "RESOURCES.md", "PLAN.md"]

LABELS = {
    "T-001": ("Clean the survey data", "Combine both survey waves into one tidy file with one row per person."),
    "T-002": ("Describe the sample", "Summarise who answered the survey, variable by variable."),
    "T-003": ("Approve the models", "You confirm the models match what was promised in the pre-registration."),
    "T-004": ("Set exclusion rule", "You decide whether inattentive respondents stay in the sample."),
    "T-005": ("Estimate main models", "Run the three pre-registered models and record the estimates."),
    "T-006": ("Chart trust by arm", "Draw average trust for each group, split by survey wave."),
    "T-007": ("Draft the paper", "Write the working paper around the tables and figures."),
    "T-008": ("Draft the slides", "Build a short talk that presents the main result."),
    "T-009": ("Package for replication", "Bundle code and data so anyone can rebuild every output."),
    "D-001": ("Analysis dataset", "The cleaned survey data the analysis runs on."),
    "D-002": ("Descriptive table", "Averages and ranges for each background variable."),
    "D-003": ("Main results table", "The estimates from the three models."),
    "D-004": ("Coefficient plot", "The key estimates drawn as points with error bars."),
    "D-005": ("Trust by arm chart", "Average trust in each group, by wave."),
    "D-006": ("Working paper", "The written report of the study."),
    "D-007": ("Conference slides", "The talk version of the paper."),
    "D-008": ("Replication package", "Everything needed to reproduce the results."),
    "D-009": ("Online appendix", "Extra tables and the full survey wording."),
    "RS-001": ("Wave 1 responses", "Raw answers from the first survey wave."),
    "RS-002": ("Wave 2 responses", "Raw answers from the second survey wave."),
    "RS-003": ("Survey codebook", "What each survey variable means."),
}

CLASSES = {
    "format": "decision-classes-v1",
    "classifier": {"name": "subagent", "version": "example-model-2026-01",
                   "run_at": "2025-12-14T09:30:00-08:00",
                   "definition_sha256": "3f1c2a9b8e7d6c5b4a39281706f5e4d3c2b1a09f8e7d6c5b4a3928170f6e5d4c"},
    "threshold": 0.5,
    "items": {
        "DP-001": {"task": "T-002", "substantive": 0.81, "procedural": 0.22, "class": "substantive",
                   "gate_task": "T-004", "raw": {"rationale": "Changes the analysis sample."}},
        "DP-002": {"task": "T-005", "substantive": 0.08, "procedural": 0.93, "class": "procedural",
                   "gate_task": None, "raw": {"rationale": "File naming only."}},
        "DP-003": {"task": "T-006", "substantive": 0.21, "procedural": 0.77, "class": "procedural",
                   "gate_task": None, "raw": {"rationale": "Presentation choice."}},
        "DP-004": {"task": "T-009", "substantive": 0.34, "procedural": 0.70, "class": "procedural",
                   "gate_task": None, "raw": {"rationale": "Packaging format."}},
        "DP-005": {"task": "T-005", "substantive": 0.74, "procedural": 0.62, "class": "substantive",
                   "gate_task": "T-003", "raw": {"rationale": "Fixes the estimand; the rule itself is set by the pre-registration."}},
    },
    "plan_sha256_before": "9a8b7c6d5e4f30211f2e3d4c5b6a79880a1b2c3d4e5f60718293a4b5c6d7e8f9",
}


def dump(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def labels_obj(labels):
    return {"format": "plan-labels-v1",
            "written_by": {"harness": "claude-code", "model": "example-model-2026-01"},
            "date": "2025-12-15",
            "sources": {n: "0" * 64 for n in SOURCES},
            "labels": {k: {"label": a, "plain": b} for k, (a, b) in labels.items()}}


def rehash(folder):
    p = folder / "Plan-Labels.json"
    obj = json.loads(p.read_text(encoding="utf-8"))
    obj["sources"] = {n: hashlib.sha256((folder / n).read_bytes()).hexdigest() for n in SOURCES}
    dump(p, obj)


def sub(folder, name, old, new, count=1):
    p = folder / name
    s = p.read_text(encoding="utf-8")
    n = s.count(old)
    assert n == count, f"{folder.name}/{name}: expected {count} match(es) of {old!r}, found {n}"
    p.write_text(s.replace(old, new), encoding="utf-8", newline="\n")


def edit_json(folder, name, fn):
    p = folder / name
    obj = json.loads(p.read_text(encoding="utf-8"))
    fn(obj)
    dump(p, obj)


def card_block(text, tid):
    start = text.index(f"### {tid} ")
    end = text.index("\n### ", start + 1)
    return text[start:end + 1]


VARIANTS = {}

def variant(name, rehash_after=True):
    def deco(fn):
        VARIANTS[name] = (fn, rehash_after)
        return fn
    return deco

@variant("fail-E-STRUCTURE")
def _(f):  # duplicate resource ID
    row = "| RS-003 | docs/codebook.pdf | document | Survey codebook with variable definitions | Survey vendor | none | VERIFIED | unregistered |\n"
    sub(f, "RESOURCES.md", row, row + row.replace("docs/codebook.pdf", "docs/codebook-v2.pdf"))

@variant("fail-E-STRUCTURE-dp")
def _(f):  # DP-003 has no Default sub-bullet
    sub(f, "PLAN.md", "  - Default: Use the house palette and the arm order in the codebook.\n", "")

@variant("fail-E-CARD")
def _(f):  # T-008 row has no card
    s = (f / "PLAN.md").read_text(encoding="utf-8")
    sub(f, "PLAN.md", card_block(s, "T-008"), "")

@variant("fail-E-NO-VERIFY")
def _(f):  # T-008 verification section empty
    sub(f, "PLAN.md", "- Self-check: the main-result slide uses the same estimate as the paper.\n", "")

@variant("fail-E-UNKNOWN-REF")
def _(f):  # T-006 cites an unknown resource
    sub(f, "PLAN.md", "| T-005 | T-007, T-008 | RS-005 | D-005 |", "| T-005 | T-007, T-008 | RS-099 | D-005 |")

@variant("fail-E-CYCLE")
def _(f):  # T-003 <-> T-004 (both gates in W2, so no schedule error)
    sub(f, "PLAN.md", "| T-003 | researcher | W2 | pending | T-001 | none | T-005 |",
        "| T-003 | researcher | W2 | pending | T-001, T-004 | none | T-004, T-005 |")
    sub(f, "PLAN.md", "| T-004 | researcher | W2 | pending | T-001 | none | T-005 |",
        "| T-004 | researcher | W2 | pending | T-001, T-003 | none | T-003, T-005 |")

@variant("fail-E-SCHEDULE")
def _(f):  # T-007 moved to W4, before its hard dependency T-005 (W3-W4) ends
    sub(f, "PLAN.md", "| T-007 | writing | W5 |", "| T-007 | writing | W4 |")

@variant("fail-E-EDGE-SYNC")
def _(f):  # T-001 Enables omits T-006, which Requires T-001
    sub(f, "PLAN.md", "| T-002, T-003, T-004, T-006 |", "| T-002, T-003, T-004 |")

@variant("fail-E-LABEL-ID")
def _(f):  # label for an unknown task
    edit_json(f, "Plan-Labels.json", lambda o: o["labels"].update(
        {"T-099": {"label": "Unknown task", "plain": "No such task exists."}}))

@variant("fail-E-CLASSES")
def _(f):  # classification for an unknown decision point
    edit_json(f, "Decision-Classes.json", lambda o: o["items"].update(
        {"DP-099": {"task": "T-005", "substantive": 0.1, "procedural": 0.9, "class": "procedural",
                    "gate_task": None, "raw": {}}}))

@variant("fail-E-CLASSES-gatemode")
def _(f):  # T-004 says approve, but DP-001 (substantive 0.81, procedural 0.22) gives decide
    sub(f, "PLAN.md", "Gate-mode: decide\n", "Gate-mode: approve\n")

@variant("warn-W-TYPE-FIELDS")
def _(f):  # malformed type fields: unknown chart kind (D-005); one-element inputs row (D-008)
    sub(f, "SPEC.md", "kind: bar\n", "kind: pie\n")
    sub(f, "SPEC.md", '["wave2.csv", "Survey vendor, wave 2 delivery"]', '["wave2.csv"]')

@variant("warn-W-NO-LABEL")
def _(f):  # T-006 has no label
    edit_json(f, "Plan-Labels.json", lambda o: o["labels"].pop("T-006"))

@variant("warn-W-STALE-LABELS", rehash_after=False)
def _(f):  # PLAN.md edited after the labels were written
    sub(f, "PLAN.md", "| D-002 | output/descriptives/ |", "| D-002 | output/descriptives/tables/ |")

@variant("warn-W-STATUS")
def _(f):  # T-002 status word outside the v0.8 list (table and card agree, so no W-STATUS-SYNC)
    sub(f, "PLAN.md", "| T-002 | analysis | W2 | pending |", "| T-002 | analysis | W2 | done |")
    _card_status(f, "T-002", "pending", "done")

@variant("warn-W-STATUS-SYNC")
def _(f):  # card line says verified, Task graph says pending
    _card_status(f, "T-002", "pending", "verified")

@variant("warn-W-NO-PRODUCER")
def _(f):  # D-005 delivered by no task
    sub(f, "PLAN.md", "| RS-005 | D-005 |", "| RS-005 | none |")


PHASES = [("PH-1", "Data preparation", "Get the survey data clean and described.",
            ["T-001", "T-002"]),
           ("PH-2", "Analysis", "Settle the sample and models, then estimate them.",
            ["T-003", "T-004", "T-005", "T-006"]),
           ("PH-3", "Writing and release", "Write it up, present it and package it for replication.",
            ["T-007", "T-008", "T-009"])]


def _add_phases(o, phases=PHASES):
    o["phases"] = [{"id": i, "name": n, "plain": p} for i, n, p, _ in phases]
    for i, _, _, ts in phases:
        for t in ts:
            o["labels"][t]["phase"] = i


@variant("ok-phases")
def _(f):  # every task has a phase (FORMAT.md section 6)
    edit_json(f, "Plan-Labels.json", _add_phases)

@variant("fail-E-PHASE")
def _(f):  # phases declared, T-006 has none
    def fn(o):
        _add_phases(o)
        o["labels"]["T-006"].pop("phase")
    edit_json(f, "Plan-Labels.json", fn)

@variant("fail-E-PHASE-unknown")
def _(f):  # T-006 names an undeclared phase
    def fn(o):
        _add_phases(o)
        o["labels"]["T-006"]["phase"] = "PH-9"
    edit_json(f, "Plan-Labels.json", fn)

@variant("fail-E-PHASE-undeclared")
def _(f):  # a task label carries a phase, but no phases are declared
    edit_json(f, "Plan-Labels.json", lambda o: o["labels"]["T-001"].update({"phase": "PH-1"}))

@variant("warn-W-PHASE-EMPTY")
def _(f):  # PH-4 declared, no task in it
    edit_json(f, "Plan-Labels.json", lambda o: _add_phases(
        o, PHASES + [("PH-4", "Online appendix", "Extra material.", [])]))


def _card_status(f, tid, old, new):
    """Change the `Status:` line of card `tid` from `old` to `new` (first such line after its heading)."""
    p = f / "PLAN.md"
    t = p.read_text(encoding="utf-8")
    i = t.index(f"### {tid} ")
    j = t.index(f"Status: {old}", i)
    p.write_text(t[:j] + f"Status: {new}" + t[j + len(f"Status: {old}"):], encoding="utf-8", newline="\n")


def main():
    ok = OUT / "ok"
    if ok.exists():
        shutil.rmtree(ok)
    ok.mkdir(parents=True)
    for n in SOURCES:
        (ok / n).write_bytes((SRC / n).read_bytes().replace(b"\r\n", b"\n"))
    dump(ok / "Plan-Labels.json", labels_obj(LABELS))
    dump(ok / "Decision-Classes.json", CLASSES)
    rehash(ok)  # last step for ok/
    for name, (fn, rh) in VARIANTS.items():
        d = OUT / name
        if d.exists():
            shutil.rmtree(d)
        shutil.copytree(ok, d)
        fn(d)
        if rh:
            rehash(d)
    print("wrote", 1 + len(VARIANTS), "fixture folders")


if __name__ == "__main__":
    main()
