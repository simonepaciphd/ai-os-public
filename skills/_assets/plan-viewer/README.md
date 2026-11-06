# plan-viewer

Turns a project's `planning/` folder (`SPEC.md`, `RESOURCES.md`, `PLAN.md`, plus the optional `Plan-Labels.json` and `Decision-Classes.json`) into one self-contained `Plan-Visual.html`. Run it again after any change; nobody edits the HTML by hand.

Python 3, standard library only. The format contract is [`FORMAT.md`](FORMAT.md) (`plan-viewer-format-v1`); this README does not repeat it.

## Usage

```
python plan_viewer.py <planning-dir> [-o <out.html>] [--built YYYY-MM-DD]
python plan_viewer.py --check <planning-dir>
plan-viewer.cmd ...            (Windows wrapper, same arguments)
```

- Default output: `<planning-dir>/Plan-Visual.html`.
- `--built` is the date shown on the page (default: today). The same inputs plus the same `--built` give byte-identical output.
- `--check` lints only and writes nothing; it cannot be combined with `-o`.
- `ERROR` and `WARN` lines go to stderr. On success, stdout carries only the `file:///` link of the page (or `ok (N warning(s))` with `--check`).

## Rules

Every rule ID (`E-STRUCTURE`, `E-CARD`, `E-NO-VERIFY`, `E-UNKNOWN-REF`, `E-CYCLE`, `E-SCHEDULE`, `E-EDGE-SYNC`, `E-LABEL-ID`, `E-PHASE`, `E-CLASSES`, `W-UNTYPED`, `W-TYPE-FIELDS`, `W-NO-LABEL`, `W-STALE-LABELS`, `W-NO-PRODUCER`, `W-PHASE-EMPTY`) and its condition is defined in FORMAT.md §8. Messages read:

```
ERROR <rule>: <file>[:<line>]: <text>
WARN <rule>: <file>[:<line>]: <text>
```

All problems are collected before exit. When a whole table fails to parse (`E-STRUCTURE`), references into it are not also reported as `E-UNKNOWN-REF`.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | no errors (warnings allowed); page written, or `--check` passed |
| 1 | one or more errors; nothing written |
| 2 | usage or IO error (bad arguments, missing directory, unreadable file, template missing or without exactly one `/*__PLAN_DATA__*/null` marker) |

## Files

| File | Role |
|---|---|
| `FORMAT.md` | the contract |
| `plan_viewer.py` | builder and linter |
| `plan-viewer.cmd` | Windows wrapper |
| `template.html` | the page; the builder replaces `/*__PLAN_DATA__*/null` with the page data (FORMAT.md §10) |
| `tests/` | fixtures |

## Use as a library

```python
import plan_viewer as pv
model, problems = pv.parse_planning("path/to/planning")   # parse errors only
problems += pv.validate(model)                             # cross-reference rules, errors and warnings
page = pv.build_page_data(model, "2026-10-28")             # dict in the FORMAT.md §10 shape
html = pv.render(page, pv.TEMPLATE)
```

Each problem is a `Problem(kind, rule, file, line, text)`; `str(problem)` gives the message line and `problem.is_error` tells errors from warnings.
