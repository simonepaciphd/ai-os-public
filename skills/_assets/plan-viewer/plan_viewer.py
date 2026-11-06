"""Build a self-contained Plan-Visual.html from a project's planning/ folder.

Usage:
    python plan_viewer.py <planning-dir> [-o <out.html>] [--built YYYY-MM-DD]
    python plan_viewer.py --check <planning-dir>

Reads SPEC.md, RESOURCES.md and PLAN.md (plus the optional Plan-Labels.json and
Decision-Classes.json), checks them against the plan-viewer-format-v1 rules in
FORMAT.md (next to this file), injects the page data into template.html and
prints the file:/// link of the output. Standard library only.

Exit 0 = no errors (warnings allowed); 1 = one or more errors (all listed, no
output written); 2 = usage or IO error.

Importable API (used by classify.py):
    parse_planning(dir) -> (model, problems)
    validate(model) -> problems
    build_page_data(model, built, warnings=None) -> dict
    render(page_data, template_path) -> str
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import NamedTuple

TOOL = "plan-viewer"
VERSION = "1.2.0"
FORMAT_ID = "plan-viewer-format-v1"
TEMPLATE = Path(__file__).with_name("template.html")
MARKER = "/*__PLAN_DATA__*/null"
OUT_NAME = "Plan-Visual.html"

SPEC = "SPEC.md"
RES = "RESOURCES.md"
PLAN = "PLAN.md"
LABELS = "Plan-Labels.json"
CLASSES = "Decision-Classes.json"
SOURCES = (SPEC, RES, PLAN)

RESEARCHER = "researcher"
OWNER_COLOURS = ("o1", "o2", "o3", "o4", "o5")
SPEC_STATUSES = {"OPEN", "APPROVED", "LOCKED"}
PRIORITIES = {"critical-path", "required", "optional"}
NONE_VALUES = {"", "none", "\u2014", "-"}

ID_PATTERNS = {
    "goal": re.compile(r"G-\d+"),
    "deliverable": re.compile(r"D-\d+"),
    "requirement": re.compile(r"R-\d+"),
    "acceptance": re.compile(r"A-\d+"),
    "resource": re.compile(r"RS-\d+"),
    "task": re.compile(r"T-\d+"),
    "wave": re.compile(r"W\d+"),
    "dp": re.compile(r"DP-\d+"),
    "phase": re.compile(r"PH-\d+"),
}

FENCE_OPEN_RE = re.compile(r"^\s{0,3}(`{3,}|~{3,})(.*)$")
FENCE_CLOSE_RE = re.compile(r"^\s{0,3}(`{3,}|~{3,})\s*$")
HEADING_RE = re.compile(r"^(#{1,6})[ \t]+(.*?)[ \t]*$")
HEADER_RE = re.compile(r"^([A-Za-z][A-Za-z0-9 _-]*?)\s*:\s*(.*?)\s*$")
SEP_RE = re.compile(r"^\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)*\|?$")
GOAL_RE = re.compile(r"^\s*[-*+]\s+(G-[^\s:\[]*)\s*(?:\[([^\]]*)\])?\s*:\s*(.*?)\s*$")
CARD_RE = re.compile(r"^(T-\S+?)\s*[\u2014\u2013-]\s*(.+?)$")
WAVES_CELL_RE = re.compile(r"^(W\d+)(?:\s*[-\u2013]\s*(W\d+))?$")
META_RE = re.compile(r"^\s*(priority|generated-from|gate-mode|status)\s*:\s*(.*?)\s*$", re.IGNORECASE)
BULLET_RE = re.compile(r"^([-*+]|\d+[.)])\s+(.*)$")
DP_RE = re.compile(r"^[-*+]\s+(DP-\S*?)\s*:\s*(.*?)\s*$")
DP_SUB_RE = re.compile(r"^[-*+]\s+(default|recommendation)\s*:\s*(.*?)\s*$", re.IGNORECASE)
REC_RE = re.compile(r"^(.+?)\s+[—–-]\s+(.+)$")
GATE_MODES = {"approve", "decide"}
# Task status words (planning-protocol v0.8): the Task graph
# `Status` column is authoritative; the card `Status:` line carries the same word plus evidence.
STATUSES = ("pending", "ready", "blocked", "in-progress", "verified", "complete", "superseded")
STATUS_WORD_RE = re.compile(r"^\s*([A-Za-z][A-Za-z-]*)")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
KEYLINE_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.*)$")


# --------------------------------------------------------------------------- problems

class Problem(NamedTuple):
    kind: str  # "ERROR" | "WARN"
    rule: str
    file: str
    line: int | None
    text: str

    def __str__(self) -> str:
        loc = self.file if self.line is None else f"{self.file}:{self.line}"
        return f"{self.kind} {self.rule}: {loc}: {self.text}"

    @property
    def is_error(self) -> bool:
        return self.kind == "ERROR"


def _err(rule, file, line, text):
    return Problem("ERROR", rule, file, line, text)


def _warn(rule, file, line, text):
    return Problem("WARN", rule, file, line, text)


# --------------------------------------------------------------------------- markdown

class TableError(Exception):
    def __init__(self, line, text):
        super().__init__(text)
        self.line, self.text = line, text


def _split_row(line: str) -> list[str]:
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|") and not s.endswith("\\|"):
        s = s[:-1]
    return [c.strip() for c in re.split(r"(?<!\\)\|", s)]


class Doc:
    """Line-oriented view of one Markdown file; fenced code is opaque."""

    def __init__(self, name: str, text: str):
        self.name = name
        self.lines = text.splitlines()
        n = len(self.lines)
        self.fenced = [False] * n
        self.fences: list[tuple[int, int, str]] = []  # (open idx, close idx, info string)
        i = 0
        while i < n:
            m = FENCE_OPEN_RE.match(self.lines[i])
            if not m:
                i += 1
                continue
            mark, close = m.group(1), n
            for j in range(i + 1, n):
                c = FENCE_CLOSE_RE.match(self.lines[j])
                if c and c.group(1)[0] == mark[0] and len(c.group(1)) >= len(mark):
                    close = j
                    break
            for k in range(i, min(close, n - 1) + 1):
                self.fenced[k] = True
            self.fences.append((i, close, m.group(2).strip()))
            i = close + 1
        self.headings: list[tuple[int, int, str]] = []  # (idx, level, text)
        for i, line in enumerate(self.lines):
            if not self.fenced[i]:
                m = HEADING_RE.match(line)
                if m:
                    self.headings.append((i, len(m.group(1)), m.group(2).strip()))

    def block_end(self, idx: int, level: int, hi: int | None = None) -> int:
        hi = len(self.lines) if hi is None else hi
        for h, lv, _ in self.headings:
            if idx < h < hi and lv <= level:
                return h
        return hi

    def title(self):
        """(idx, text) of the first heading if it is a level-1 heading, else None."""
        if self.headings and self.headings[0][1] == 1:
            return self.headings[0][0], self.headings[0][2]
        return None

    def header(self) -> dict[str, tuple[str, int]]:
        t = self.title()
        if t is None:
            return {}
        end = self.block_end(t[0], 2)
        out: dict[str, tuple[str, int]] = {}
        for i in range(t[0] + 1, end):
            if self.fenced[i]:
                continue
            m = HEADER_RE.match(self.lines[i])
            if m:
                out.setdefault(m.group(1).strip().lower(), (m.group(2).strip(), i + 1))
        return out

    def section(self, name: str, level: int = 2, lo: int = 0, hi: int | None = None):
        """(heading idx, body start, body end) of the first matching heading, else None."""
        hi = len(self.lines) if hi is None else hi
        want = name.strip().lower()
        for h, lv, text in self.headings:
            if lo <= h < hi and lv == level and text.strip().lower() == want:
                return h, h + 1, self.block_end(h, level, hi)
        return None

    def subsections(self, level: int, lo: int, hi: int):
        return [(h, text, h + 1, self.block_end(h, level, hi))
                for h, lv, text in self.headings if lo <= h < hi and lv == level]

    def first_heading(self, lo: int, hi: int) -> int:
        for h, _, _ in self.headings:
            if lo <= h < hi:
                return h
        return hi

    def text(self, lo: int, hi: int) -> str:
        chunk = self.lines[lo:hi]
        while chunk and not chunk[0].strip():
            chunk = chunk[1:]
        while chunk and not chunk[-1].strip():
            chunk = chunk[:-1]
        return "\n".join(line.rstrip() for line in chunk)

    def table(self, lo: int, hi: int):
        for i in range(lo, hi):
            if self.fenced[i] or not self.lines[i].lstrip().startswith("|"):
                continue
            header = _split_row(self.lines[i])
            if i + 1 >= hi or self.fenced[i + 1] or not SEP_RE.match(self.lines[i + 1].strip()):
                raise TableError(i + 1, "table header row is not followed by a separator row")
            if len(_split_row(self.lines[i + 1])) != len(header):
                raise TableError(i + 2, "separator row and header row have different cell counts")
            rows, j = [], i + 2
            while j < hi and not self.fenced[j] and self.lines[j].lstrip().startswith("|"):
                rows.append((j + 1, _split_row(self.lines[j])))
                j += 1
            return {"line": i + 1, "header": header, "rows": rows}
        return None


def status_word(cell) -> str | None:
    """Leading status word of a Status cell or card line, lower-cased ("pending; artifact absent" -> "pending")."""
    m = STATUS_WORD_RE.match(cell or "")
    return m.group(1).lower() if m else None


def _read_table(doc: Doc, section: str, cols: list[str], problems: list, optional=()) -> list[dict] | None:
    sec = doc.section(section)
    if sec is None:
        problems.append(_err("E-STRUCTURE", doc.name, None, f"missing section '## {section}'"))
        return None
    try:
        tbl = doc.table(sec[1], sec[2])
    except TableError as e:
        problems.append(_err("E-STRUCTURE", doc.name, e.line, f"'## {section}': {e.text}"))
        return None
    if tbl is None:
        problems.append(_err("E-STRUCTURE", doc.name, sec[0] + 1, f"section '## {section}' has no table"))
        return None
    index = {}
    for n, h in enumerate(tbl["header"]):
        index.setdefault(h.strip().lower(), n)
    missing = [c for c in cols if c.lower() not in index]
    if missing:
        problems.append(_err("E-STRUCTURE", doc.name, tbl["line"],
                             f"'## {section}' table is missing column(s): {', '.join(missing)}"))
        return None
    out = []
    for line, cells in tbl["rows"]:
        if len(cells) != len(tbl["header"]):
            problems.append(_err("E-STRUCTURE", doc.name, line,
                                 f"'## {section}' row has {len(cells)} cells, header has {len(tbl['header'])}"))
            continue
        if not any(cells):
            continue
        rec = {"_line": line}
        for c in cols:
            rec[c.lower()] = cells[index[c.lower()]]
        for c in optional:
            if c.lower() in index:
                rec[c.lower()] = cells[index[c.lower()]]
        out.append(rec)
    return out


def _id_list(cell: str) -> list[str]:
    if cell.strip().lower() in NONE_VALUES:
        return []
    seen, out = set(), []
    for tok in re.split(r"[,\s]+", cell.strip()):
        if tok and tok not in seen:
            seen.add(tok)
            out.append(tok)
    return out


def _checked_ids(cell, kind, what, file, line, problems) -> list[str]:
    out = []
    for tok in _id_list(cell):
        if ID_PATTERNS[kind].fullmatch(tok):
            out.append(tok)
        else:
            problems.append(_err("E-STRUCTURE", file, line, f"bad {kind} ID '{tok}' in {what}"))
    return out


def _check_id(value, kind, what, file, line, seen: set, problems) -> bool:
    if not ID_PATTERNS[kind].fullmatch(value):
        problems.append(_err("E-STRUCTURE", file, line, f"bad {kind} ID '{value}' in {what}"))
        return False
    if value in seen:
        problems.append(_err("E-STRUCTURE", file, line, f"duplicate {kind} ID '{value}'"))
        return False
    seen.add(value)
    return True


def _title(doc: Doc, prefix: str, problems) -> str | None:
    t = doc.title()
    m = re.match(rf"^{prefix}:\s*(.+)$", t[1]) if t else None
    if not m:
        problems.append(_err("E-STRUCTURE", doc.name, t[0] + 1 if t else None,
                             f"title must be '# {prefix}: <name>'"))
        return None
    return m.group(1).strip()


# --------------------------------------------------------------------------- parse

def _parse_spec(doc: Doc, problems) -> dict:
    spec = {"name": _title(doc, "SPEC", problems), "status": None,
            "goals": [], "deliverables": [], "types": {}, "deliverables_ok": False}
    hdr = doc.header()
    if "status" not in hdr:
        problems.append(_err("E-STRUCTURE", doc.name, None, "header line 'Status:' missing"))
    else:
        val, line = hdr["status"]
        if val.upper() not in SPEC_STATUSES:
            problems.append(_err("E-STRUCTURE", doc.name, line, f"Status must be OPEN, APPROVED or LOCKED, not '{val}'"))
        spec["status"] = val

    sec = doc.section("Goal and success")
    if sec is None:
        problems.append(_err("E-STRUCTURE", doc.name, None, "missing section '## Goal and success'"))
    else:
        seen: set[str] = set()
        for i in range(sec[1], sec[2]):
            if doc.fenced[i]:
                continue
            m = GOAL_RE.match(doc.lines[i])
            if not m:
                continue
            gid, tag, text = m.groups()
            if not _check_id(gid, "goal", "'## Goal and success'", doc.name, i + 1, seen, problems):
                continue
            if not text:
                problems.append(_err("E-STRUCTURE", doc.name, i + 1, f"goal {gid} has no text"))
                continue
            spec["goals"].append({"id": gid, "tag": tag, "text": text, "line": i + 1})
        if not spec["goals"]:
            problems.append(_err("E-STRUCTURE", doc.name, sec[0] + 1, "'## Goal and success' has no '- G-###: <text>' bullet"))

    seen = set()
    rows = _read_table(doc, "Deliverables", ["ID", "Deliverable", "Required contents"], problems)
    spec["deliverables_ok"] = rows is not None
    for r in rows or []:
        if _check_id(r["id"], "deliverable", "'## Deliverables'", doc.name, r["_line"], seen, problems):
            spec["deliverables"].append({"id": r["id"], "name": r["deliverable"],
                                         "req": r["required contents"], "line": r["_line"]})

    sec = doc.section("Deliverable types")
    if sec is not None:
        for open_i, close_i, info in doc.fences:
            if not (sec[1] <= open_i < sec[2]):
                continue
            parts = info.split()
            if not parts or parts[0] != "deliverable":
                continue
            if len(parts) != 2:
                problems.append(_err("E-STRUCTURE", doc.name, open_i + 1, "fence must be '```deliverable D-###'"))
                continue
            did = parts[1]
            if not ID_PATTERNS["deliverable"].fullmatch(did):
                problems.append(_err("E-STRUCTURE", doc.name, open_i + 1, f"bad deliverable ID '{did}' in deliverable block"))
                continue
            if did in spec["types"]:
                problems.append(_err("E-STRUCTURE", doc.name, open_i + 1, f"duplicate deliverable block for {did}"))
                continue
            fields, bad = {}, []
            for j in range(open_i + 1, min(close_i, len(doc.lines))):
                raw = doc.lines[j].strip()
                if not raw or raw.startswith("#"):
                    continue
                m = KEYLINE_RE.match(raw)
                if not m:
                    bad.append(j + 1)
                    continue
                val = m.group(2).strip()
                try:
                    fields[m.group(1)] = json.loads(val)
                except ValueError:
                    fields[m.group(1)] = val
            spec["types"][did] = {"line": open_i + 1, "fields": fields, "bad": bad}
    return spec


def _parse_resources(doc: Doc, problems) -> dict:
    items, seen = [], set()
    rows = _read_table(doc, "Asset inventory", ["Asset ID", "Description"], problems)
    for r in rows or []:
        if _check_id(r["asset id"], "resource", "'## Asset inventory'", doc.name, r["_line"], seen, problems):
            items.append({"id": r["asset id"], "desc": r["description"], "line": r["_line"]})
    return {"items": items, "ok": rows is not None}


def _bullets(text: str) -> list[str]:
    """One item per top-level bullet, marker stripped; text with no bullet is one item."""
    lines = [ln for ln in text.split("\n") if ln.strip()]
    if not any(BULLET_RE.match(ln.strip()) and len(ln) - len(ln.lstrip()) < 2 for ln in lines):
        return [text] if text.strip() else []
    items: list[str] = []
    for line in text.split("\n"):
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip())
        m = BULLET_RE.match(line.strip())
        if m and indent < 2:
            items.append(m.group(2).strip())
        elif items:
            items[-1] += "\n" + line.strip()
        else:
            items.append(line.strip())
    return [s for s in items if s]


def _parse_card(doc: Doc, h: int, lo: int, hi: int, tid: str, name: str, problems, dp_seen: set) -> dict:
    card = {"id": tid, "name": name, "line": h + 1, "priority": None, "from_dp": None,
            "from_dp_line": None, "gate_mode": None, "gate_mode_line": None,
            "out": "", "has_outputs": False, "ver": [], "dps": [], "status": None, "status_line": None}
    pre_end = doc.first_heading(lo, hi)
    for i in range(lo, pre_end):
        if doc.fenced[i]:
            continue
        m = META_RE.match(doc.lines[i])
        if not m:
            continue
        key, val = m.group(1).lower(), m.group(2)
        if key == "status":
            if card["status_line"] is None:
                card["status"], card["status_line"] = status_word(val), i + 1
            continue
        if key == "priority":
            if val.lower() not in PRIORITIES:
                problems.append(_err("E-STRUCTURE", doc.name, i + 1,
                                     f"{tid}: Priority must be critical-path, required or optional, not '{val}'"))
            card["priority"] = val.lower()
        elif key == "gate-mode":
            if val.lower() not in GATE_MODES:
                problems.append(_err("E-STRUCTURE", doc.name, i + 1,
                                     f"{tid}: Gate-mode must be approve or decide, not '{val}'"))
            else:
                card["gate_mode"], card["gate_mode_line"] = val.lower(), i + 1
        else:
            if not ID_PATTERNS["dp"].fullmatch(val):
                problems.append(_err("E-STRUCTURE", doc.name, i + 1, f"{tid}: bad dp ID '{val}' in Generated-from"))
            else:
                card["from_dp"], card["from_dp_line"] = val, i + 1
    subs = {}
    for sh, text, slo, shi in doc.subsections(4, lo, hi):
        subs.setdefault(text.strip().lower(), (sh, slo, shi))
    if "outputs" in subs:
        card["has_outputs"] = True
        card["out"] = doc.text(subs["outputs"][1], subs["outputs"][2])
    else:
        problems.append(_err("E-STRUCTURE", doc.name, h + 1, f"{tid}: card has no '#### Outputs'"))
    if "verification and review" in subs:
        vt = doc.text(subs["verification and review"][1], subs["verification and review"][2])
        if vt.strip().lower() not in NONE_VALUES:
            card["ver"] = _bullets(vt)
    if "decision points" in subs:
        _, slo, shi = subs["decision points"]
        if doc.text(slo, shi).strip().lower() not in NONE_VALUES:
            _parse_dps(doc, slo, shi, tid, card, problems, dp_seen)
    return card


def _parse_dps(doc: Doc, slo: int, shi: int, tid: str, card: dict, problems, dp_seen: set) -> None:
    """`- DP-###: <text>` bullets, each with indented `- Default:` and `- Recommendation:` sub-bullets."""
    cur, field = None, None  # current DP (None after a rejected DP line) and the field being continued
    skipping = False         # inside a rejected DP: its indented lines are already covered by that error
    for i in range(slo, shi):
        line = doc.lines[i]
        if not line.strip():
            continue
        if not line[:1].isspace():
            cur, field, skipping = None, None, False
            m = DP_RE.match(line.strip())
            if not m:
                problems.append(_err("E-STRUCTURE", doc.name, i + 1,
                                     f"{tid}: '#### Decision points' line is not '- DP-###: <text>'"))
                skipping = True
                continue
            dpid, text = m.groups()
            if not ID_PATTERNS["dp"].fullmatch(dpid):
                problems.append(_err("E-STRUCTURE", doc.name, i + 1, f"{tid}: bad dp ID '{dpid}'"))
            elif dpid in dp_seen:
                problems.append(_err("E-STRUCTURE", doc.name, i + 1, f"duplicate dp ID '{dpid}'"))
            elif not text:
                problems.append(_err("E-STRUCTURE", doc.name, i + 1, f"{dpid} has no text"))
            else:
                dp_seen.add(dpid)
                cur = {"id": dpid, "text": text, "default": None, "rec": None, "line": i + 1}
                card["dps"].append(cur)
                field = "text"
                continue
            skipping = True
            continue
        if skipping:
            continue
        if cur is None:
            problems.append(_err("E-STRUCTURE", doc.name, i + 1,
                                 f"{tid}: indented '#### Decision points' line before any '- DP-###: <text>'"))
            skipping = True
            continue
        s = line.strip()
        if BULLET_RE.match(s):
            m = DP_SUB_RE.match(s)
            if not m:
                problems.append(_err("E-STRUCTURE", doc.name, i + 1,
                                     f"{cur['id']}: sub-bullet must be '- Default: ...' or '- Recommendation: ...'"))
                field = None
                continue
            key = "default" if m.group(1).lower() == "default" else "rec"
            if cur[key] is not None:
                problems.append(_err("E-STRUCTURE", doc.name, i + 1,
                                     f"{cur['id']}: duplicate '{m.group(1).capitalize()}:' sub-bullet"))
                field = None
                continue
            cur[key], cur[key + "_line"], field = m.group(2), i + 1, key
        elif field is not None:
            cur[field] = (cur[field] + " " + s).strip()
    for dp in card["dps"]:
        for key, what in (("default", "Default"), ("rec", "Recommendation")):
            if dp[key] is None:
                problems.append(_err("E-STRUCTURE", doc.name, dp["line"],
                                     f"{dp['id']}: missing '- {what}: ...' sub-bullet"))
            elif not dp[key]:
                problems.append(_err("E-STRUCTURE", doc.name, dp[key + "_line"],
                                     f"{dp['id']}: '{what}:' has no text"))
        if dp["rec"] and not REC_RE.match(dp["rec"]):
            problems.append(_err("E-STRUCTURE", doc.name, dp["rec_line"],
                                 f"{dp['id']}: Recommendation must be '<choice> — <one-line reason>'"))


def _parse_plan(doc: Doc, problems) -> dict:
    plan = {"name": _title(doc, "PLAN", problems), "status": None, "lock": "", "deadline": None,
            "lanes": [], "waves": [], "tasks": [], "cards": {}, "card_order": [],
            "lanes_ok": False, "waves_ok": False, "tasks_ok": False}
    hdr = doc.header()
    for key in ("status", "baseline lock", "deadline"):
        if key not in hdr:
            problems.append(_err("E-STRUCTURE", doc.name, None, f"header line '{key.capitalize()}:' missing"))
    if "status" in hdr:
        plan["status"] = hdr["status"][0]
    if "baseline lock" in hdr:
        plan["lock"] = hdr["baseline lock"][0]
    if "deadline" in hdr:
        val, line = hdr["deadline"]
        if val.lower() != "none":
            ok = bool(DATE_RE.match(val))
            if ok:
                try:
                    _dt.date.fromisoformat(val)
                except ValueError:
                    ok = False
            if ok:
                plan["deadline"] = val
            else:
                problems.append(_err("E-STRUCTURE", doc.name, line, f"Deadline must be YYYY-MM-DD or none, not '{val}'"))

    seen: set[str] = set()
    rows = _read_table(doc, "Lanes", ["Lane", "Display name", "Persona"], problems)
    plan["lanes_ok"] = rows is not None
    for r in rows or []:
        slug = r["lane"]
        if not slug or re.search(r"\s", slug):
            problems.append(_err("E-STRUCTURE", doc.name, r["_line"], f"bad lane slug '{slug}'"))
        elif slug in seen:
            problems.append(_err("E-STRUCTURE", doc.name, r["_line"], f"duplicate lane '{slug}'"))
        else:
            seen.add(slug)
            plan["lanes"].append({"slug": slug, "name": r["display name"], "persona": r["persona"], "line": r["_line"]})

    rows = _read_table(doc, "Parallel waves", ["Wave", "Target"], problems)
    plan["waves_ok"] = rows is not None
    for n, r in enumerate(rows or []):
        want = f"W{n + 1}"
        if r["wave"] != want:
            plan["waves_ok"] = False
            problems.append(_err("E-STRUCTURE", doc.name, r["_line"],
                                 f"waves must be contiguous from W1: expected {want}, found '{r['wave']}'"))
            break
        plan["waves"].append({"k": r["wave"], "d": r["target"], "line": r["_line"]})

    cols = ["Task", "Lane", "Waves", "Requires", "Soft", "Enables", "Resources", "Delivers"]
    seen = set()
    rows = _read_table(doc, "Task graph", cols, problems, optional=("Status",))
    plan["tasks_ok"] = rows is not None
    for r in rows or []:
        line = r["_line"]
        if not _check_id(r["task"], "task", "'## Task graph'", doc.name, line, seen, problems):
            continue
        m = WAVES_CELL_RE.match(r["waves"])
        if not m:
            problems.append(_err("E-STRUCTURE", doc.name, line, f"{r['task']}: Waves must be 'W<n>' or 'W<n>-W<m>', not '{r['waves']}'"))
        tid = r["task"]
        plan["tasks"].append({
            "id": tid, "line": line, "lane": r["lane"],
            "status": status_word(r["status"]) if "status" in r else None,
            "wave_from": m.group(1) if m else None, "wave_to": (m.group(2) or m.group(1)) if m else None,
            "requires": _checked_ids(r["requires"], "task", f"{tid} Requires", doc.name, line, problems),
            "soft": _checked_ids(r["soft"], "task", f"{tid} Soft", doc.name, line, problems),
            "enables": _checked_ids(r["enables"], "task", f"{tid} Enables", doc.name, line, problems),
            "resources": _checked_ids(r["resources"], "resource", f"{tid} Resources", doc.name, line, problems),
            "delivers": _checked_ids(r["delivers"], "deliverable", f"{tid} Delivers", doc.name, line, problems),
        })

    sec = doc.section("Task cards")
    if sec is None:
        problems.append(_err("E-STRUCTURE", doc.name, None, "missing section '## Task cards'"))
    else:
        dp_seen: set[str] = set()
        for h, text, lo, hi in doc.subsections(3, sec[1], sec[2]):
            m = CARD_RE.match(text)
            if not m:
                problems.append(_err("E-STRUCTURE", doc.name, h + 1, f"card heading must be '### T-### \u2014 <name>', not '{text}'"))
                continue
            tid, name = m.group(1), m.group(2).strip()
            if not ID_PATTERNS["task"].fullmatch(tid):
                problems.append(_err("E-STRUCTURE", doc.name, h + 1, f"bad task ID '{tid}' in card heading"))
                continue
            if tid in plan["cards"]:
                problems.append(_err("E-STRUCTURE", doc.name, h + 1, f"duplicate card for {tid}"))
                continue
            plan["cards"][tid] = _parse_card(doc, h, lo, hi, tid, name, problems, dp_seen)
            plan["card_order"].append(tid)
    return plan


def _load_json(path: Path):
    return json.loads(path.read_bytes().decode("utf-8-sig"))


def parse_planning(planning_dir) -> tuple[dict, list[Problem]]:
    """Parse a planning/ folder. Returns (model, problems); problems are errors only.

    Raises OSError when a file exists but cannot be read.
    """
    d = Path(planning_dir)
    problems: list[Problem] = []
    model = {
        "dir": str(d),
        "sha256": {},
        "spec": {"name": None, "status": None, "goals": [], "deliverables": [], "types": {},
                 "deliverables_ok": False},
        "resources": {"items": [], "ok": False},
        "plan": {"name": None, "status": None, "lock": "", "deadline": None, "lanes": [],
                 "waves": [], "tasks": [], "cards": {}, "card_order": [],
                 "lanes_ok": False, "waves_ok": False, "tasks_ok": False},
        "labels": None, "labels_state": "absent",
        "classes": None, "classes_state": "absent", "classes_error": None,
    }
    parsers = {SPEC: ("spec", _parse_spec), RES: ("resources", _parse_resources), PLAN: ("plan", _parse_plan)}
    for name in SOURCES:
        p = d / name
        if not p.is_file():
            problems.append(_err("E-STRUCTURE", name, None, "required file missing"))
            continue
        raw = p.read_bytes()
        model["sha256"][name] = hashlib.sha256(raw).hexdigest()
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError as e:
            problems.append(_err("E-STRUCTURE", name, None, f"not valid UTF-8 ({e.reason} at byte {e.start})"))
            continue
        key, fn = parsers[name]
        model[key] = fn(Doc(name, text), problems)

    p = d / LABELS
    if p.is_file():
        try:
            obj = _load_json(p)
        except (ValueError, UnicodeDecodeError) as e:
            problems.append(_err("E-STRUCTURE", LABELS, None, f"not valid JSON: {e}"))
            obj = None
        if obj is not None:
            if not isinstance(obj, dict) or obj.get("format") != "plan-labels-v1":
                problems.append(_err("E-STRUCTURE", LABELS, None, 'format must be "plan-labels-v1"'))
            elif not isinstance(obj.get("labels"), dict):
                problems.append(_err("E-STRUCTURE", LABELS, None, "'labels' must be an object"))
            else:
                model["labels"], model["labels_state"] = obj, "ok"
        if model["labels_state"] != "ok":
            model["labels_state"] = "invalid"

    p = d / CLASSES
    if p.is_file():
        try:
            model["classes"], model["classes_state"] = _load_json(p), "present"
        except (ValueError, UnicodeDecodeError) as e:
            model["classes_state"], model["classes_error"] = "invalid", f"not valid JSON: {e}"
    return model, problems


# --------------------------------------------------------------------------- validate

def _str_list(v):
    return isinstance(v, list) and len(v) > 0 and all(isinstance(x, str) and x for x in v)


def _nonempty_str(v):
    return isinstance(v, str) and v.strip() != ""


def _var_rows(v):
    return (isinstance(v, list) and len(v) > 0 and all(
        isinstance(r, list) and len(r) == 4 and all(isinstance(x, str) for x in r[:3]) for r in v))


def _section_rows(v):
    return (isinstance(v, list) and len(v) > 0 and all(
        isinstance(r, list) and len(r) == 2 and isinstance(r[0], str)
        and isinstance(r[1], (str, int, float)) and not isinstance(r[1], bool) for r in v))


def _pair_rows(v):
    return (isinstance(v, list) and len(v) > 0 and all(
        isinstance(r, list) and len(r) == 2 and all(isinstance(x, str) and x for x in r) for r in v))


# type -> (required {field: check}, optional {field: check})
CATALOG = {
    "coef-plot": ({"terms": _str_list, "models": _str_list}, {"facets": _str_list}),
    "regression-table": ({"terms": _str_list, "models": _str_list, "footer": _str_list}, {}),
    "dataset": ({"unit": _nonempty_str, "target": _nonempty_str, "variables": _var_rows}, {}),
    "chart": ({"kind": lambda v: v in ("bar", "line"), "x": _nonempty_str, "y": _nonempty_str},
              {"groups": _str_list}),
    "summary-table": ({"variables": _str_list}, {}),
    "report-outline": ({"sections": _section_rows}, {}),
    "deck-outline": ({"slides": _str_list}, {}),
    "replication-package": ({"inputs": _pair_rows, "tables": _str_list, "figures": _str_list,
                             "language": _nonempty_str}, {"datasets": _str_list}),
}


def type_problems(fields: dict) -> list[str]:
    """Reasons a deliverable block does not satisfy the mockup catalog (empty = valid)."""
    t = fields.get("type")
    if not isinstance(t, str) or not t:
        return ["no 'type' field"]
    if t not in CATALOG:
        return [f"unknown type '{t}' (known: {', '.join(CATALOG)})"]
    req, opt = CATALOG[t]
    out = []
    for k, check in req.items():
        if k not in fields:
            out.append(f"missing required field '{k}'")
        elif not check(fields[k]):
            out.append(f"field '{k}' has the wrong shape")
    for k, check in opt.items():
        if k in fields and not check(fields[k]):
            out.append(f"optional field '{k}' has the wrong shape")
    return out


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def wave_index(model) -> dict[str, int]:
    return {w["k"]: i for i, w in enumerate(model["plan"]["waves"])}


def task_span(task: dict, model) -> tuple[int, int] | None:
    """Half-open [s, e) over wave indices; researcher tasks are [s, s). None if unknown."""
    wi = wave_index(model)
    a, b = task.get("wave_from"), task.get("wave_to")
    if a not in wi or b not in wi or wi[b] < wi[a]:
        return None
    s = wi[a]
    return (s, s) if task["lane"] == RESEARCHER else (s, wi[b] + 1)


def validate(model) -> list[Problem]:
    """Cross-reference and graph rules (FORMAT.md section 8). Returns errors and warnings."""
    P: list[Problem] = []
    spec, plan = model["spec"], model["plan"]
    tasks = {t["id"]: t for t in plan["tasks"]}
    cards = plan["cards"]
    lanes = {ln["slug"] for ln in plan["lanes"]}
    wi = wave_index(model)
    rs_ids = {r["id"] for r in model["resources"]["items"]}
    d_ids = {d["id"] for d in spec["deliverables"]}
    dps = {dp["id"]: (tid, dp) for tid in plan["card_order"] for dp in cards[tid]["dps"]}
    # A collection whose table failed to parse is already an E-STRUCTURE; do not cascade
    # it into one unknown-reference error per reference.
    ok = {"lane": plan.get("lanes_ok", True), "wave": plan.get("waves_ok", True),
          "task": plan.get("tasks_ok", True), "resource": model["resources"].get("ok", True),
          "deliverable": spec.get("deliverables_ok", True)}

    # E-CARD
    for t in plan["tasks"]:
        if t["id"] not in cards:
            P.append(_err("E-CARD", PLAN, t["line"], f"{t['id']} is in '## Task graph' but has no card"))
    for tid in plan["card_order"]:
        if ok["task"] and tid not in tasks:
            P.append(_err("E-CARD", PLAN, cards[tid]["line"], f"card {tid} has no '## Task graph' row"))

    # E-NO-VERIFY
    for tid in plan["card_order"]:
        if not cards[tid]["ver"]:
            P.append(_err("E-NO-VERIFY", PLAN, cards[tid]["line"], f"{tid} has no '#### Verification and review' content"))

    # E-UNKNOWN-REF (+ reversed wave spans)
    for t in plan["tasks"]:
        tid, line = t["id"], t["line"]
        if ok["lane"] and t["lane"] not in lanes:
            P.append(_err("E-UNKNOWN-REF", PLAN, line, f"{tid}: unknown lane '{t['lane']}'"))
        for w in dict.fromkeys(x for x in (t["wave_from"], t["wave_to"]) if x):
            if ok["wave"] and w not in wi:
                P.append(_err("E-UNKNOWN-REF", PLAN, line, f"{tid}: unknown wave '{w}'"))
        if t["wave_from"] in wi and t["wave_to"] in wi and wi[t["wave_to"]] < wi[t["wave_from"]]:
            P.append(_err("E-STRUCTURE", PLAN, line, f"{tid}: wave span {t['wave_from']}-{t['wave_to']} runs backwards"))
        for col, key in (("Requires", "requires"), ("Soft", "soft"), ("Enables", "enables")):
            for r in t[key]:
                if ok["task"] and r not in tasks:
                    P.append(_err("E-UNKNOWN-REF", PLAN, line, f"{tid}: unknown task '{r}' in {col}"))
        for r in t["resources"]:
            if ok["resource"] and r not in rs_ids:
                P.append(_err("E-UNKNOWN-REF", PLAN, line, f"{tid}: unknown resource '{r}'"))
        for r in t["delivers"]:
            if ok["deliverable"] and r not in d_ids:
                P.append(_err("E-UNKNOWN-REF", PLAN, line, f"{tid}: unknown deliverable '{r}'"))
    for tid in plan["card_order"]:
        c = cards[tid]
        if c["from_dp"] and c["from_dp"] not in dps:
            P.append(_err("E-UNKNOWN-REF", PLAN, c["from_dp_line"], f"{tid}: Generated-from names unknown decision point '{c['from_dp']}'"))
        if c.get("gate_mode") and tid in tasks and tasks[tid]["lane"] != RESEARCHER:
            P.append(_err("E-STRUCTURE", PLAN, c["gate_mode_line"],
                          f"{tid}: Gate-mode is only allowed on researcher-lane (gate) tasks, not lane '{tasks[tid]['lane']}'"))
        if c["from_dp"] and not c.get("gate_mode"):
            P.append(_err("E-STRUCTURE", PLAN, c["from_dp_line"], f"{tid}: Generated-from requires a Gate-mode line"))
    for did, blk in spec["types"].items():
        if ok["deliverable"] and did not in d_ids:
            P.append(_err("E-UNKNOWN-REF", SPEC, blk["line"], f"deliverable block names unknown deliverable '{did}'"))

    # E-CYCLE (Requires only, known tasks only)
    state: dict[str, int] = {}
    cycles: list[list[str]] = []
    seen_cycles: set[tuple[str, ...]] = set()
    for root in tasks:
        if state.get(root):
            continue
        stack = [(root, iter([r for r in tasks[root]["requires"] if r in tasks]))]
        path = [root]
        state[root] = 1
        while stack:
            node, it = stack[-1]
            nxt = next(it, None)
            if nxt is None:
                stack.pop()
                path.pop()
                state[node] = 2
                continue
            if state.get(nxt) == 1:
                cyc = path[path.index(nxt):]
                k = cyc.index(min(cyc))
                norm = tuple(cyc[k:] + cyc[:k])
                if norm not in seen_cycles:
                    seen_cycles.add(norm)
                    cycles.append(list(norm))
            elif not state.get(nxt):
                state[nxt] = 1
                path.append(nxt)
                stack.append((nxt, iter([r for r in tasks[nxt]["requires"] if r in tasks])))
    for cyc in cycles:
        P.append(_err("E-CYCLE", PLAN, tasks[cyc[0]]["line"],
                      "cycle in Requires: " + " -> ".join(cyc + [cyc[0]])))

    # E-SCHEDULE
    for t in plan["tasks"]:
        sp = task_span(t, model)
        if sp is None:
            continue
        for r in t["requires"]:
            if r not in tasks:
                continue
            dsp = task_span(tasks[r], model)
            if dsp is not None and dsp[1] > sp[0]:
                P.append(_err("E-SCHEDULE", PLAN, t["line"],
                              f"{t['id']} [{sp[0]},{sp[1]}) requires {r} [{dsp[0]},{dsp[1]}), "
                              f"which ends after {t['id']} starts ({dsp[1]} > {sp[0]})"))

    # E-EDGE-SYNC
    for t in plan["tasks"]:
        for r in t["requires"]:
            if r in tasks and t["id"] not in tasks[r]["enables"]:
                P.append(_err("E-EDGE-SYNC", PLAN, tasks[r]["line"],
                              f"{t['id']} Requires {r}, but {r} Enables does not list {t['id']}"))
        for e in t["enables"]:
            if e in tasks and t["id"] not in tasks[e]["requires"]:
                P.append(_err("E-EDGE-SYNC", PLAN, t["line"],
                              f"{t['id']} Enables {e}, but {e} Requires does not list {t['id']}"))

    # W-STATUS, W-STATUS-SYNC (v1.1): status is information, never an error
    for t in plan["tasks"]:
        st = t.get("status")
        if st is not None and st not in STATUSES:
            P.append(_warn("W-STATUS", PLAN, t["line"], f"{t['id']} status '{st}' is not one of {', '.join(STATUSES)}"))
        cs = plan["cards"].get(t["id"], {}).get("status")
        if st is not None and cs is not None and cs != st:
            P.append(_warn("W-STATUS-SYNC", PLAN, plan["cards"][t["id"]]["status_line"],
                           f"{t['id']} card says '{cs}', Task graph says '{st}' (the Task graph wins)"))

    # Labels: E-LABEL-ID, W-STALE-LABELS, W-NO-LABEL
    labels = model["labels"]["labels"] if model["labels_state"] == "ok" else {}
    if model["labels_state"] == "ok":
        known = set(tasks) | d_ids | rs_ids
        for key, val in labels.items():
            kind = next((k for k in ("resource", "deliverable", "task")
                         if ID_PATTERNS[k].fullmatch(str(key))), None)
            if key not in known and (kind is None or ok[kind]):
                P.append(_err("E-LABEL-ID", LABELS, None, f"label key '{key}' is not a known task, deliverable or resource ID"))
            if not isinstance(val, dict) or not _nonempty_str(val.get("label")):
                P.append(_err("E-LABEL-ID", LABELS, None, f"label for '{key}' has an empty 'label'"))
            elif "plain" in val and not isinstance(val["plain"], str):
                P.append(_err("E-LABEL-ID", LABELS, None, f"label for '{key}' has a non-string 'plain'"))
        srcs = model["labels"].get("sources")
        srcs = srcs if isinstance(srcs, dict) else {}
        stale = [n for n in SOURCES if n in model["sha256"]
                 and str(srcs.get(n, "")).lower() != model["sha256"][n]]
        if stale:
            P.append(_warn("W-STALE-LABELS", LABELS, None,
                           f"source hashes differ for {', '.join(stale)}; re-run the writer pass"))
    if model["labels_state"] == "absent":
        P.append(_warn("W-NO-LABEL", LABELS, None, "file not found; every task and deliverable falls back to its source name"))
    elif model["labels_state"] == "ok":
        for t in plan["tasks"]:
            if t["id"] not in labels:
                P.append(_warn("W-NO-LABEL", PLAN, t["line"], f"{t['id']} has no label (falls back to its source name)"))
        for d in spec["deliverables"]:
            if d["id"] not in labels:
                P.append(_warn("W-NO-LABEL", SPEC, d["line"], f"{d['id']} has no label (falls back to its source name)"))

    # E-PHASE, W-PHASE-EMPTY (1.2.0; FORMAT.md section 6)
    if model["labels_state"] == "ok":
        P.extend(_phase_problems(model["labels"], plan["tasks"]))

    # E-CLASSES
    P.extend(_classes_problems(model, tasks, dps, cards))

    # W-UNTYPED, W-TYPE-FIELDS
    for d in spec["deliverables"]:
        blk = spec["types"].get(d["id"])
        if blk is None:
            P.append(_warn("W-UNTYPED", SPEC, d["line"], f"{d['id']} has no deliverable block (plain tile, no mockup)"))
            continue
        why = [f"line {n} is not 'key: value'" for n in blk["bad"]] + type_problems(blk["fields"])
        if why:
            P.append(_warn("W-TYPE-FIELDS", SPEC, blk["line"], f"{d['id']}: {'; '.join(why)} (plain tile)"))

    # W-NO-PRODUCER
    produced = {d for t in plan["tasks"] for d in t["delivers"]}
    for d in spec["deliverables"]:
        if d["id"] not in produced:
            P.append(_warn("W-NO-PRODUCER", SPEC, d["line"], f"{d['id']} is produced by no task"))
    return P


def phase_list(labels_obj) -> list[dict]:
    """Well-formed declared phases, in order (FORMAT.md section 6); [] when none or malformed."""
    ph = labels_obj.get("phases") if isinstance(labels_obj, dict) else None
    if not isinstance(ph, list):
        return []
    out, seen = [], set()
    for p in ph:
        if (isinstance(p, dict) and isinstance(p.get("id"), str) and ID_PATTERNS["phase"].fullmatch(p["id"])
                and p["id"] not in seen and _nonempty_str(p.get("name"))):
            seen.add(p["id"])
            out.append(p)
    return out


def _phase_problems(labels_obj, plan_tasks) -> list[Problem]:
    P = []

    def bad(msg):
        P.append(_err("E-PHASE", LABELS, None, msg))

    raw = labels_obj.get("phases")
    declared = []
    if raw is not None and not isinstance(raw, list):
        bad("'phases' must be a list")
    elif isinstance(raw, list):
        seen = set()
        for i, p in enumerate(raw):
            where = f"phases[{i}]"
            if not isinstance(p, dict):
                bad(f"{where} must be an object")
                continue
            pid = p.get("id")
            if not isinstance(pid, str) or not ID_PATTERNS["phase"].fullmatch(pid):
                bad(f"{where}.id must match PH-<digits>")
            elif pid in seen:
                bad(f"{where}.id '{pid}' is a duplicate")
            else:
                seen.add(pid)
                declared.append(pid)
            if not _nonempty_str(p.get("name")):
                bad(f"{where} has an empty 'name'")
            if "plain" in p and not isinstance(p["plain"], str):
                bad(f"{where} has a non-string 'plain'")
    known = set(declared)
    labels = labels_obj.get("labels") if isinstance(labels_obj.get("labels"), dict) else {}
    task_ids = {t["id"] for t in plan_tasks}
    used = set()
    for key, val in labels.items():
        if not isinstance(val, dict) or "phase" not in val:
            continue
        ph = val["phase"]
        if key not in task_ids:
            bad(f"label '{key}' has a 'phase', but phases are allowed on task labels only")
        elif not raw:
            bad(f"{key}: phase '{ph}', but no phases are declared")
        elif not isinstance(ph, str) or ph not in known:
            bad(f"{key}: unknown phase '{ph}'")
        else:
            used.add(ph)
    if raw:
        for t in plan_tasks:
            v = labels.get(t["id"])
            if not isinstance(v, dict) or "phase" not in v:
                bad(f"{t['id']}: no phase (phases are declared, so every task needs one)")
        for pid in declared:
            if pid not in used:
                P.append(_warn("W-PHASE-EMPTY", LABELS, None, f"{pid}: no task in this phase (shown as an empty card)"))
    return P


def gate_mode_for(sub, proc, threshold) -> str | None:
    """FORMAT.md section 5: approve iff S and P >= threshold; decide iff S >= threshold > P; else no gate."""
    if sub < threshold:
        return None
    return "approve" if proc >= threshold else "decide"


def _classes_problems(model, tasks, dps, cards=None) -> list[Problem]:
    cards = cards or {}
    st = model["classes_state"]
    if st == "absent":
        return []
    if st == "invalid":
        return [_err("E-CLASSES", CLASSES, None, model["classes_error"])]
    c = model["classes"]
    if not isinstance(c, dict):
        return [_err("E-CLASSES", CLASSES, None, "top level must be an object")]
    P = []

    def bad(msg):
        P.append(_err("E-CLASSES", CLASSES, None, msg))

    if c.get("format") != "decision-classes-v1":
        bad('format must be "decision-classes-v1"')
    cl = c.get("classifier")
    if not isinstance(cl, dict):
        bad("'classifier' must be an object")
    else:
        for k in ("name", "version", "run_at", "definition_sha256"):
            if not _nonempty_str(cl.get(k)):
                bad(f"classifier.{k} is required (non-empty string)")
    thr = c.get("threshold")
    if not _num(thr):
        bad("'threshold' must be a number")
        thr = None
    if not _nonempty_str(c.get("plan_sha256_before")):
        bad("'plan_sha256_before' is required (non-empty string)")
    items = c.get("items")
    if not isinstance(items, dict):
        bad("'items' must be an object")
        return P
    for dpid, it in items.items():
        if dpid not in dps:
            bad(f"items names unknown decision point '{dpid}'")
            continue
        if not isinstance(it, dict):
            bad(f"items.{dpid} must be an object")
            continue
        owner = dps[dpid][0]
        if it.get("task") != owner:
            bad(f"items.{dpid}.task is '{it.get('task')}', but {dpid} is in card {owner}")
        for k in ("substantive", "procedural"):
            if not _num(it.get(k)):
                bad(f"items.{dpid}.{k} must be a number")
        cls = it.get("class")
        if cls not in ("substantive", "procedural"):
            bad(f"items.{dpid}.class must be 'substantive' or 'procedural'")
        elif thr is not None and _num(it.get("substantive")):
            want = "substantive" if it["substantive"] >= thr else "procedural"
            if cls != want:
                bad(f"items.{dpid}.class is '{cls}' but substantive {it['substantive']} vs threshold {thr} gives '{want}'")
        g = it.get("gate_task")
        if g is not None and g not in tasks:
            bad(f"items.{dpid}.gate_task '{g}' is not a known task")
        elif g is not None and cards.get(g, {}).get("from_dp") != dpid:
            bad(f"items.{dpid}.gate_task '{g}' does not carry Generated-from: {dpid}")
        elif (g is not None and thr is not None and _num(it.get("substantive"))
              and _num(it.get("procedural")) and cards.get(g, {}).get("gate_mode")):
            have = cards[g]["gate_mode"]
            want = gate_mode_for(it["substantive"], it["procedural"], thr)
            if have != want:
                why = (f"gives '{want}'" if want else "is below threshold, so it gets no gate")
                bad(f"items.{dpid}: gate {g} has Gate-mode '{have}', but substantive {it['substantive']}, "
                    f"procedural {it['procedural']} vs threshold {thr} {why}")
    return P


# --------------------------------------------------------------------------- build

def build_page_data(model, built: str, warnings=None) -> dict:
    """Page data (FORMAT.md section 10). `warnings` defaults to the WARN lines of validate(model)."""
    if warnings is None:
        warnings = [p for p in validate(model) if not p.is_error]
    spec, plan = model["spec"], model["plan"]
    labels = model["labels"]["labels"] if model["labels_state"] == "ok" else {}

    def lab(i, fallback):
        v = labels.get(i)
        if isinstance(v, dict):
            label = v.get("label") if _nonempty_str(v.get("label")) else fallback
            plain = v.get("plain") if isinstance(v.get("plain"), str) else ""
            return label, plain
        return fallback, ""

    items = {}
    cls_ok = model["classes_state"] == "present" and isinstance(model["classes"], dict)
    if cls_ok and isinstance(model["classes"].get("items"), dict):
        items = model["classes"]["items"]

    phases = phase_list(model["labels"]) if model["labels_state"] == "ok" else []
    phase_ids = {p["id"] for p in phases}

    def phase_of(tid):
        v = labels.get(tid)
        ph = v.get("phase") if isinstance(v, dict) else None
        return ph if ph in phase_ids else None

    lanes, n = {}, 0
    for ln in plan["lanes"]:
        if ln["slug"] == RESEARCHER:
            lanes[ln["slug"]] = {"n": "You", "c": "accent", "you": True}
        else:
            lanes[ln["slug"]] = {"n": ln["name"], "c": OWNER_COLOURS[n % len(OWNER_COLOURS)], "you": False}
            n += 1

    # A Recommendation reaches the page only through an approve gate (FORMAT §5, §10).
    approve_dps = {c.get("from_dp") for c in plan["cards"].values() if c.get("gate_mode") == "approve"}
    tasks = []
    for t in plan["tasks"]:
        card = plan["cards"].get(t["id"], {})
        name = card.get("name", t["id"])
        label, plain = lab(t["id"], name)
        s, e = task_span(t, model) or (0, 0)
        dps = []
        for dp in card.get("dps", []):
            it = items.get(dp["id"]) if isinstance(items.get(dp["id"]), dict) else {}
            dps.append({"id": dp["id"], "text": dp["text"],
                        "default": dp.get("default") or "",
                        "rec": (dp.get("rec") or "") if dp["id"] in approve_dps else None,
                        "sub": it.get("substantive") if _num(it.get("substantive")) else None,
                        "proc": it.get("procedural") if _num(it.get("procedural")) else None,
                        "cls": it.get("class") if isinstance(it.get("class"), str) else None})
        tasks.append({
            "id": t["id"], "name": name, "lane": t["lane"], "s": s, "e": e,
            "ph": phase_of(t["id"]),
            "st": t["status"] if t.get("status") in STATUSES else None,
            "label": label, "plain": plain,
            "out": card.get("out", ""), "ver": list(card.get("ver", [])),
            "res": list(t["resources"]), "deliv": list(t["delivers"]),
            "deps": list(t["requires"]), "soft": list(t["soft"]),
            "cp": card.get("priority") == "critical-path",
            "gate": t["lane"] == RESEARCHER,
            "dps": dps,
            "from_dp": card.get("from_dp"),
            "gate_mode": card.get("gate_mode") if t["lane"] == RESEARCHER else None,
        })

    deliverables = []
    for d in spec["deliverables"]:
        label, plain = lab(d["id"], d["name"])
        blk = spec["types"].get(d["id"])
        typ, fields = None, {}
        if blk is not None and not blk["bad"] and not type_problems(blk["fields"]):
            typ = blk["fields"]["type"]
            fields = {k: v for k, v in blk["fields"].items() if k != "type"}
        deliverables.append({"id": d["id"], "name": d["name"], "label": label, "plain": plain,
                             "req": d["req"], "type": typ, "fields": fields})

    resources = {}
    for r in model["resources"]["items"]:
        label, _ = lab(r["id"], r["desc"])
        resources[r["id"]] = {"label": label, "desc": r["desc"]}

    lab_meta = {"by": None, "on": None, "stale": False}
    if model["labels_state"] == "ok":
        wb = model["labels"].get("written_by")
        if isinstance(wb, dict) and (_nonempty_str(wb.get("harness")) or _nonempty_str(wb.get("model"))):
            lab_meta["by"] = f"{wb.get('harness') or ''}/{wb.get('model') or ''}"
        if _nonempty_str(model["labels"].get("date")):
            lab_meta["on"] = model["labels"]["date"]
        lab_meta["stale"] = any(p.rule == "W-STALE-LABELS" for p in warnings)

    classes = None
    if cls_ok and isinstance(model["classes"].get("classifier"), dict):
        cl = model["classes"]["classifier"]
        classes = {"by": f"{cl.get('name', '')} {cl.get('version', '')}".strip(), "on": str(cl.get("run_at", ""))}

    lock = plan["lock"].strip()
    goals = spec["goals"]
    return {
        "title": plan["name"] or spec["name"] or "",
        "goal": goals[0]["text"] if goals else "",
        "status": f"LOCKED {lock}" if lock else "DRAFT",
        "built": built,
        "deadline": plan["deadline"],
        "waves": [{"k": w["k"], "d": w["d"]} for w in plan["waves"]],
        "phases": [{"k": p["id"], "n": p["name"],
                    "plain": p["plain"] if isinstance(p.get("plain"), str) else ""} for p in phases],
        "lanes": lanes,
        "resources": resources,
        "tasks": tasks,
        "deliverables": deliverables,
        "sources": {n: model["sha256"].get(n, "")[:12] for n in SOURCES},
        "labels": lab_meta,
        "classes": classes,
        "tool": f"{TOOL} {VERSION}",
        "warnings": [str(w) for w in warnings],
    }


def page_json(page_data: dict) -> str:
    blob = json.dumps(page_data, ensure_ascii=False, separators=(",", ":"))
    return (blob.replace("</", "<\\/").replace("<!--", "\\u003c!--")
            .replace("\u2028", "\\u2028").replace("\u2029", "\\u2029"))


def render(page_data: dict, template_path=TEMPLATE) -> str:
    """Return the page: template.html with the marker replaced by the page data."""
    tpl = Path(template_path).read_text(encoding="utf-8")
    count = tpl.count(MARKER)
    if count != 1:
        raise ValueError(f"template marker {MARKER} must appear exactly once in {template_path} (found {count})")
    return tpl.replace(MARKER, page_json(page_data))


# --------------------------------------------------------------------------- CLI

def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="backslashreplace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(prog="plan_viewer.py", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("planning_dir", type=Path)
    ap.add_argument("-o", "--out", type=Path, help=f"output .html (default: <planning-dir>/{OUT_NAME})")
    ap.add_argument("--built", help="build date YYYY-MM-DD shown on the page (default: today)")
    ap.add_argument("--check", action="store_true", help="lint only; write nothing")
    a = ap.parse_args(argv)

    if a.check and a.out is not None:
        print("error: --check writes nothing; do not combine it with -o", file=sys.stderr)
        return 2
    built = a.built or _dt.date.today().isoformat()
    try:
        if not DATE_RE.match(built):
            raise ValueError
        _dt.date.fromisoformat(built)
    except ValueError:
        print(f"error: --built must be YYYY-MM-DD, not {built!r}", file=sys.stderr)
        return 2
    if not a.planning_dir.is_dir():
        print(f"error: not a directory: {a.planning_dir}", file=sys.stderr)
        return 2

    try:
        model, problems = parse_planning(a.planning_dir)
    except OSError as e:
        print(f"error: cannot read planning files: {e}", file=sys.stderr)
        return 2
    problems = problems + validate(model)
    errors = [p for p in problems if p.is_error]
    warnings = [p for p in problems if not p.is_error]
    for p in errors + warnings:
        print(p, file=sys.stderr)
    if errors:
        print(f"{len(errors)} error(s), {len(warnings)} warning(s); nothing written", file=sys.stderr)
        return 1
    if a.check:
        print(f"ok ({len(warnings)} warning(s))")
        return 0

    out = (a.out or a.planning_dir / OUT_NAME).resolve()
    try:
        page = render(build_page_data(model, built, warnings), TEMPLATE)
        out.write_text(page, encoding="utf-8", newline="\n")
    except (OSError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    print(out.as_uri())
    return 0


if __name__ == "__main__":
    sys.exit(main())
