# plan-viewer format contract — `plan-viewer-format-v1`

The single contract between the enforced planning templates (`../planning-templates/`), the builder (`plan_viewer.py`), the classifier (`classify.py`), the page (`template.html`) and the test fixtures (`tests/`). Change this file first; then change the code.

Version: 1.0-draft (2026-10-28). Standard library Python only. No personal names or paths anywhere in this folder.

Amended 2026-11-06 (builder 1.2.0, §6, §8, §10, §11): optional **phases** in `Plan-Labels.json` group tasks into named high-level stages ("Survey design", "Paper writing") for a simplified Phases view. Phases are display-only and agent-written in the labels pass: they never enter `PLAN.md`, the baseline lock or scheduling, and waves stay the dispatch unit. A plan without phases builds exactly as before.

Amended 2026-10-28 (§3 `replication-package`): raw inputs move to `data/inputs/`, analysis-ready datasets are drawn in `data/`, and a new `ai-disclosure/` folder is always shown. The input fields are unchanged.

## 1. Files in a project's `planning/` folder

| File | Required | Written by | Read by |
|---|---|---|---|
| `SPEC.md` | yes | planning stages 1-2 | builder |
| `RESOURCES.md` | yes | planning stage 2 | builder |
| `PLAN.md` | yes | planning stages 3-5 (+ `classify.py` gate insertion) | builder, classifier |
| `Plan-Labels.json` | no | writer-pass subagent (stage 5) | builder |
| `Decision-Classes.json` | no | `classify.py` or the classifier subagent | builder |
| `Plan-Visual.html` | output | builder | people |

## 2. Markdown parsing rules (all three files)

- **Header block:** `Key: value` lines between the `# ` title and the first `## `. Keys are matched case-insensitively.
- **Sections:** a `## <Name>` heading, matched by exact name (case-insensitive, trimmed). A section ends at the next heading of the same or a higher level.
- **Tables:** the first pipe table in a section. The header row's cell names are matched case-insensitively after trimming, and the column order is free. Extra columns are ignored. The separator row is required. Cells are trimmed; inline Markdown is kept verbatim.
- **ID lists in a cell:** separated by commas and/or whitespace. The values `none`, `—`, `-` or an empty cell mean an empty list.
- **IDs:** goals `G-###`, deliverables `D-###`, requirements `R-###`, acceptance `A-###`, resources `RS-###`, tasks `T-###`, waves `W<n>`, decision points `DP-###`. Each pattern is digits only, with at least one digit (`D-01` and `D-001` both match). IDs are unique within their kind.

## 3. `SPEC.md`

- Title `# SPEC: <name>`. Header `Status:` (`OPEN | APPROVED | LOCKED`).
- `## Goal and success`: bullets `- G-###[ [TAG]]: <text>`. The page goal is the text of the first `G-*`.
- `## Deliverables` table, which needs the columns `ID`, `Deliverable` and `Required contents`.
- `## Deliverable types` (optional section): one fenced block per typed deliverable.

  ````
  ```deliverable D-001
  type: coef-plot
  terms: ["Exposure", "Trust"]
  models: ["M1", "M2"]
  ```
  ````

  Each line is `key: value`. A value is parsed as JSON when it is valid JSON; otherwise it is a bare string (trimmed). Blank lines and `#` comment lines are ignored.

**Mockup catalog v1: required fields** (`?` = optional):

| type | fields |
|---|---|
| `coef-plot` | `terms` [str], `models` [str], `facets`? [str] |
| `regression-table` | `terms` [str], `models` [str], `footer` [str] (e.g. `["N", "R²"]`) |
| `dataset` | `unit` str, `target` str (e.g. `"≈ 2,400 rows × 18 columns"`), `variables` [[name, label, type, values]] |
| `chart` | `kind` `bar`\|`line`, `x` str, `y` str, `groups`? [str] |
| `summary-table` | `variables` [str] |
| `report-outline` | `sections` [[title, pages]] |
| `deck-outline` | `slides` [str] |
| `replication-package` | `inputs` [[name, source]], `tables` [str], `figures` [str], `language` str (script extension, e.g. `"R"` → `.R`, `"py"`), `datasets`? [str] (analysis-ready files) |

`language` is the script file extension without the dot (`"R"`, `"py"`, `"do"`), used verbatim. The tree lists each raw input as a file in `data/inputs/`, with its source as a note; `datasets`, when given, are listed as files directly in `data/`.

`replication-package` renders the standard `appendix/` layout as a folder tree:
- `README.txt`
- `codebook.pdf`, for the final analysis dataset
- `data/`:
  - `inputs/`: flat, holding `README.txt` (the provenance of each raw input, listing `inputs`) and the raw files
  - the analysis-ready datasets (`datasets`), directly in `data/`
- `outputs/tables/` and `outputs/figures/`, listing `tables` and `figures`
- `scripts/`: exactly two, `data_builder.<ext>` (`data/inputs/` → analysis-ready datasets in `data/`) and `analysis.<ext>` (analysis datasets → final outputs)
- `ai-disclosure/`: AI-use disclosure material, always shown empty with the note "AI-use disclosure (system-dependent)"; its contents are deliberately not specified and there is no field for them

`appendix/archive/` is kept in the working tree but excluded from shipped packages, so it is not drawn. The tree uses no numbers, but the standard mockup caption still applies.

## 4. `RESOURCES.md`

`## Asset inventory` table, which needs the columns `Asset ID` (`RS-###`) and `Description`. Nothing else is read.

## 5. `PLAN.md`

- Title `# PLAN: <name>`. Header lines: `Status:`, `Baseline lock:` (an empty value means draft; otherwise it is shown as `LOCKED <value>`), and `Deadline:` (`YYYY-MM-DD` or `none`).
- `## Lanes` table: `Lane` (slug), `Display name`, `Persona`. The lane slug `researcher` is reserved for the human decision-maker and is shown as "You". Other lanes take the owner colours o1..o5 in table order, cycling.
- `## Parallel waves` table: `Wave` (`W1..Wn`, contiguous from W1), `Target` (free text: a date or "wk 1"). The table order is the time axis.
- `## Task graph` table, which needs the columns `Task`, `Lane`, `Waves`, `Requires`, `Soft`, `Enables`, `Resources`, `Delivers`. Other template columns (`Status`, `Write claim`, `Researcher gates`, `Acceptance IDs`) are kept in the template but not read.
  - `Waves`: `W2` or `W2-W3`. Internally the span is half-open, `[start, end)` over wave indices: `W2` = [1,2) and `W2-W3` = [1,3).
- `## Task cards`: one card per task-graph row, headed `### T-### — <name>` (em dash, en dash or `-` accepted). Inside a card:
  - metadata lines `Priority: critical-path | required | optional` (critical-path marks the main path) and `Generated-from: DP-###` (only on gate tasks written by the classifier);
  - `#### Outputs`, kept verbatim as "What it produces" (the table or text, rendered as the source Markdown);
  - `#### Verification and review`, kept verbatim as "How it's checked"; each bullet is one check;
  - `#### Decision points` (may be absent or say `none`): bullets `- DP-###: <the choice, phrased as a decision>`. DP IDs are unique plan-wide. Each DP bullet has two indented sub-bullets, both required (`E-STRUCTURE` if missing):
    - `- Default: <the choice the agent makes if nobody objects>`
    - `- Recommendation: <the choice the AI recommends> — <one-line reason>`
  - Gate cards written by the classifier also carry `Gate-mode: approve | decide`:
    - `approve` (S and P both >= threshold): the card quotes the Recommendation, and the researcher approves or changes it;
    - `decide` (S >= threshold, P below it): the card carries background only, and the Recommendation is dropped.
  - DPs with S below the threshold get no gate; the page shows their Default in the task pop-up.
  - A gate task is a hard dependency of the task its DP belongs to: the classifier adds the gate to that task's `Requires` (and the gate's `Enables`), in the same wave.

**HTML comments are not skipped.** Anything inside `<!-- -->` is parsed like other text, so template guidance must not contain parseable blocks or IDs. **Soft edges** (`Soft`) are display-only: they need no inverse in `Enables` and are exempt from `E-SCHEDULE`, `E-CYCLE` and `E-EDGE-SYNC`. The `Display name` of the `researcher` row is unused (always shown as "You").

**Researcher-lane tasks are decisions and take no wave time.** Their span is `[start, start)`: drawn at the start of their wave and allowed to precede a task in the same wave.

## 6. `Plan-Labels.json` (`plan-labels-v1`)

```json
{"format": "plan-labels-v1",
 "written_by": {"harness": "claude-code", "model": "<model id>"},
 "date": "YYYY-MM-DD",
 "sources": {"SPEC.md": "<sha256 hex>", "RESOURCES.md": "<sha256 hex>", "PLAN.md": "<sha256 hex>"},
 "labels": {"T-001": {"label": "≈ 4 words", "plain": "one or two plain sentences"},
            "D-001": {"label": "...", "plain": "..."},
            "RS-001": {"label": "...", "plain": "..."}}}
```

`sources` hashes are SHA-256 of the raw file bytes, so line endings matter; keep planning files LF (`* -text` in `.gitattributes`). Keys of `labels` are source IDs (task, deliverable or resource). This is the "every label carries its source ID" rule.

**Phases (optional, builder 1.2.0).** Two additions, both optional, so a v1 file without them stays valid:

```json
{"phases": [{"id": "PH-1", "name": "Survey design", "plain": "one plain sentence"},
            {"id": "PH-2", "name": "Paper writing", "plain": "..."}],
 "labels": {"T-001": {"label": "...", "plain": "...", "phase": "PH-1"}}}
```

- `phases` is an ordered list; its order is the reading order of the Phases view. `id` matches `PH-<digits>` and is unique; `name` is a non-empty string (≈ 1–3 words); `plain` is optional (string).
- `phase` is allowed on **task** labels only and names a declared phase ID.
- When `phases` is non-empty, **every task** in the Task graph needs a label with a `phase` (`E-PHASE`). An empty or absent `phases` list means the plan has no phases; then no label may carry `phase`.
- Phases are a reading aid. They do not affect waves, dependencies, the schedule check or the baseline lock, and a phase may span any waves and overlap other phases.
- The labels writer assigns them, not the researcher; re-running the writer pass refreshes them with the labels. `W-STALE-LABELS` covers them.

## 7. `Decision-Classes.json` (`decision-classes-v1`)

```json
{"format": "decision-classes-v1",
 "classifier": {"name": "jev | subagent", "version": "<pinned model/version>", "run_at": "<ISO-8601 with offset>",
                "definition_sha256": "<sha256 of the definition text sent>"},
 "threshold": 0.5,
 "items": {"DP-001": {"task": "T-004", "substantive": 0.81, "procedural": 0.22,
                      "class": "substantive", "gate_task": "T-031", "raw": {}}},
 "plan_sha256_before": "<sha256 of PLAN.md before gate insertion>"}
```

`class` is `substantive` iff `substantive >= threshold`. `raw` keeps the classifier's full response for that item (radical transparency). The exact JEV request/response contract and the gate-insertion procedure belong to `classify.py` and are documented in its README (`classify-README.md`). This file fixes only the output.

## 8. Build rules

Every message is printed as `ERROR <rule>: <file>[:<line>]: <text>` or `WARN <rule>: ...`. All problems are collected before exit.

| Rule | Kind | Condition |
|---|---|---|
| `E-STRUCTURE` | error | required file, section, table or column missing or malformed; bad ID pattern; duplicate ID; DP without a valid `Default:` / `Recommendation: <choice> — <reason>` pair; `Gate-mode` with a bad value, on a non-researcher task, or missing where `Generated-from` is set |
| `E-CARD` | error | task-graph row without a card, or a card without a row |
| `E-NO-VERIFY` | error | task card with no `Verification and review` content |
| `E-UNKNOWN-REF` | error | unknown lane, wave, task (in Requires/Soft/Enables), `RS-*`, `D-*` or `DP-*` reference |
| `E-CYCLE` | error | cycle in `Requires` (the cycle is listed) |
| `E-SCHEDULE` | error | hard edge with `dep.end > task.start` |
| `E-EDGE-SYNC` | error | `Enables` is not the exact inverse of `Requires` |
| `E-LABEL-ID` | error | `Plan-Labels.json` key is not a known task/deliverable/resource ID, or a label has an empty `label` |
| `E-PHASE` | error | `phases` malformed (not a list; entry without a `PH-<digits>` `id` or a non-empty `name`; duplicate `id`; non-string `plain`); a `phase` on a non-task label, naming an unknown phase, or present while no phases are declared; phases declared and a task without a `phase` |
| `E-CLASSES` | error | `Decision-Classes.json` malformed or naming an unknown DP; `gate_task` that does not carry `Generated-from` for that DP; `Gate-mode` contradicting the scores (incl. a gate for a DP below threshold) |
| `W-UNTYPED` | warning | deliverable with no `deliverable` block (shown as a plain tile, no mockup) |
| `W-TYPE-FIELDS` | warning | typed deliverable missing required fields or with an unknown type (plain tile) |
| `W-NO-LABEL` | warning | task or deliverable without a label (falls back to its source name) |
| `W-STALE-LABELS` | warning | `Plan-Labels.json` source hashes differ from current files ("re-run the writer pass") |
| `W-NO-PRODUCER` | warning | deliverable produced by no task |
| `W-PHASE-EMPTY` | warning | declared phase with no task (shown as an empty card) |

Exit codes: 0 = no errors (warnings allowed); 1 = one or more errors (no output written); 2 = usage or IO error.

## 9. Builder CLI

```
plan_viewer.py <planning-dir> [-o <out.html>] [--built YYYY-MM-DD]   # default out: <planning-dir>/Plan-Visual.html
plan_viewer.py --check <planning-dir>                                  # lint only, no file written
plan-viewer.cmd ...                                                    # = python "%~dp0plan_viewer.py" %*
```

On success the builder prints the warnings and then `file:///...` of the output. The page is deterministic: the same inputs plus the same `--built` produce byte-identical output. `--built` defaults to today.

## 10. Page data (injected into `template.html`)

The builder replaces the literal `/*__PLAN_DATA__*/null` in `template.html` with one JSON object. In that JSON, `</` is escaped as `<\/` and U+2028/2029 are escaped too. Shape:

```
{
 "title": str, "goal": str, "status": "LOCKED <ts>" | "DRAFT", "built": "YYYY-MM-DD",
 "deadline": "YYYY-MM-DD" | null,
 "waves": [{"k": "W1", "d": "<Target>"}],
 "phases": [{"k": "PH-1", "n": "<name>", "plain": str}],
 "lanes": {"<slug>": {"n": "<Display name>", "c": "o1".."o5" | "accent", "you": bool}},
 "resources": {"RS-001": {"label": str, "desc": str}},
 "tasks": [{"id", "name", "lane", "s": int, "e": int, "ph": "PH-1" | null, "label", "plain",
            "out": str, "ver": [str], "res": [str], "deliv": [str],
            "deps": [str], "soft": [str], "cp": bool, "gate": bool,
            "dps": [{"id", "text", "default": str, "rec": str|null, "sub": num|null, "proc": num|null, "cls": str|null}],
            "from_dp": str|null, "gate_mode": "approve"|"decide"|null}],
 "deliverables": [{"id", "name", "label", "plain", "req": str, "type": str|null, "fields": {}}],
 "sources": {"SPEC.md": "<sha256 first 12>", "RESOURCES.md": "...", "PLAN.md": "..."},
 "labels": {"by": "<harness/model>" | null, "on": "YYYY-MM-DD" | null, "stale": bool},
 "classes": {"by": "<name version>", "on": str} | null,
 "tool": "plan-viewer <version>",
 "warnings": [str]
}
```

Notes (amended 2026-10-28 after the template pass):
- `lanes` keys appear in `## Lanes` table order; the timeline groups lanes in that order. For the `researcher` lane the builder sets `n` to `"You"` (the table's display name is ignored).
- Gates: the builder sets `e == s` for every researcher-lane task.
- `ver[]`: one string per bullet of `#### Verification and review`, with the leading `- ` / `* ` / `1. ` marker stripped. Non-bullet content becomes a single item.
- `dps[].text` is plain text; the page escapes it.
- `resources[].label`: the `Plan-Labels.json` label if present, else the `Description` cell. `desc` is always the `Description` cell. There is no warning for a missing resource label.
- An unknown chart `kind`, or a field of the wrong JSON type, is `W-TYPE-FIELDS` and gives `type: null`. `report-outline` page targets may be numbers or strings.
- The build stamp is a date (`built`), not a time.
- `gate` is true iff the task's lane is `researcher`.
- `rec` is emitted only for a DP that produced an `approve` gate; otherwise it is `null` and never reaches the page (a `decide` gate gets background only).
- `label` falls back to `name`; `plain` falls back to `""`.
- `phases` is `[]` when the labels file declares none (or is absent or invalid); then every `ph` is `null`. `phases[].plain` falls back to `""`.
- `type` is null when the deliverable is untyped or invalid.
- Strings that come from Markdown (`out`, `ver[]`, `req`) are raw Markdown. The page renders a safe subset: escape everything, then `` `code` ``, `**bold**` and pipe tables.

## 11. Page behaviour (from the design brief, `BRIEF.md`, not shipped in this repo; `template.html` owns it)

**Staged amendment (2026-11-01; not installed): Current tasks / Full view.**
The task-graph status already emitted as `st` is authoritative. Current tasks
includes only `ready` or `in-progress` tasks whose every hard dependency has
`st: complete`. Missing, unknown, pending, blocked, verified, complete and
superseded task statuses are excluded. A verified or superseded dependency is
not complete. Soft links and dates never establish readiness. A researcher
gate can itself be current; it remains a human decision, never an approval
inferred by the viewer. Explicit ready/in-progress status is an integrator/lane
assertion, not independently validated scientific readiness or launch authority.

Full view is the default and retains every task and result. The independent
scope switch applies equally to Map and Timeline, retains the full wave axis
and deliverables, and leaves source data and all dialog relationships intact.
Only edges with two visible endpoints are drawn. Scope is not persisted;
the existing Map/Timeline preference is unchanged. Counts and an explicit empty
state explain filtering; missing statuses direct the reader to Full view.

- Map (default) and Timeline views, switched with a segmented control and remembered in `localStorage` (inside try/catch).
- Both views use the same wave axis.
- **Phases view (1.2.0)**, shown only when `phases` is non-empty; it is then the first button and the default view (key `planviewer.view.v2`, so a Map/Timeline choice remembered by an older page does not hide it). One card per phase, in `phases` order: name, `plain`, wave span (first start to last end of its tasks, as `W3–W9` with targets), a position bar over the whole wave axis with the same span in text for screen readers, steps done (when statuses exist), "decisions for you" (researcher-lane tasks), and the results its tasks deliver. A disclosure button (`aria-expanded`) lists the phase's tasks in start order; each opens the usual task dialog. The view is a vertical list with no horizontal scroll at any width. The Current tasks scope applies: counts and lists use visible tasks, spans stay those of all tasks, and phases with no visible task are hidden. Tasks whose `ph` names no phase fall into a final "Other" card.
- The task dialog shows the task's phase name when it has one.
- Researcher-lane tasks: accent-colour outline plus "You approve" (`Gate-mode: approve`) or "You decide" (`decide`).
- Critical-path edges are heavier ink; soft edges are dashed.
- "What you'll get" column and band.
- A `<dialog>` for every task and deliverable: focus trapped, Esc closes, focus returns to the opener.
- Every mockup carries a watermark and the caption "Mockup — placeholder values (b = 0, SE = 0.5). Not a result."
- At ≤ 640 px the map becomes a vertical list by wave.
- Light theme only, system fonts, no network requests.
- Footer: tool version, build date, source hashes, the labels writer and date, and the classifier name and version when present.

## 12. Coverage checklist (BRIEF → this contract)

- Header, goal and status: §3, §5, §10.
- View switch: §11.
- Map and Timeline on one axis: §5 `Waves`, §10 `s/e`.
- "What you'll get": §3 deliverables, §5 `Delivers`.
- Decision points: §5 researcher lane, §7.
- Footer transparency: §10 `sources`, `labels`, `classes`, `tool`.
- Task pop-up: `out`, `ver`, `res`, `deliv`, `deps`.
- Deliverable pop-up: `req`, `type`, `fields`.
- Mockup catalog: §3.
- Failure rules from BRIEF:
  - label without source ID → `E-LABEL-ID`
  - task without verification → `E-NO-VERIFY`
  - cycle → `E-CYCLE`
  - schedule/edge inconsistency → `E-SCHEDULE`, `E-EDGE-SYNC`
  - unknown resource/deliverable → `E-UNKNOWN-REF`
- Untyped deliverable warning → `W-UNTYPED`, `W-TYPE-FIELDS`.
- Phases view (2026-11-06): §6 phases, §8 `E-PHASE`, `W-PHASE-EMPTY`, §10 `phases`, `ph`, §11.
