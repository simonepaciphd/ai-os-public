---
name: planning-labels-protocol
description: Stage-5 writer pass of planning. A writer subagent reads the settled SPEC.md, RESOURCES.md and PLAN.md and writes `planning/Plan-Labels.json` (`plan-labels-v1`) with a short label and a plain one-to-two-sentence description for every task, deliverable and resource, keyed by source ID, for the plan-viewer page. No sign-off; re-run after every approved spec delta.
audience: public
version: 0.2
---

# Planning Labels Protocol

Write the plain-language layer of the plan page. The labels are a visual layer only: the source files stay authoritative, and the page shows their details verbatim in its pop-ups.

Composes with `planning-protocol.md` (Stage 5), `planning-decision-points-protocol.md` (runs before this pass when used), and the plan-viewer asset `_assets/plan-viewer/` (`FORMAT.md` §6 is the file contract).

Version: 0.2 (first public release; earlier versions are not shipped in this repo).

## When it runs

- At Stage 5 of `planning-protocol.md`, after `PLAN.md` settles and after the optional decision-points classify step, and before the plan-viewer build and the Stage 6 lock.
- Again after every approved spec delta (and any other change to `SPEC.md`, `RESOURCES.md` or `PLAN.md`). The builder warns `W-STALE-LABELS` when the recorded hashes no longer match.
- **No sign-off is needed.** The labels change no plan content. Writing `Plan-Labels.json` after the lock is allowed for this reason; it is not a spec delta.

## Who runs it

One writer subagent, given only this file, the three source files and the writer persona (`{{LIBRARY_ROOT}}/personas/writer.md`). It may write `planning/Plan-Labels.json` and nothing else. Never stop, kill or restart a process you did not start; if a job hangs, report it and stop.

## What to write

`planning/Plan-Labels.json`, format `plan-labels-v1` (`_assets/plan-viewer/FORMAT.md` §6; example in `_assets/planning-templates/Plan-Labels.json`):

```json
{"format": "plan-labels-v1",
 "written_by": {"harness": "<harness>", "model": "<exact model id>"},
 "date": "YYYY-MM-DD",
 "sources": {"SPEC.md": "<sha256>", "RESOURCES.md": "<sha256>", "PLAN.md": "<sha256>"},
 "phases": [{"id": "PH-1", "name": "...", "plain": "..."}],
 "labels": {"T-001": {"label": "...", "plain": "...", "phase": "PH-1"}}}
```

1. **One entry per ID.** Every task (`T-###` in the `## Task graph`, including researcher-lane gate tasks), every deliverable (`D-###` in the SPEC `## Deliverables` table) and every resource (`RS-###` in the RESOURCES `## Asset inventory`). Key each entry by its source ID; never invent an ID (`E-LABEL-ID` fails the build).
2. **`label`:** about four words, a short name a reader recognises at a glance. Never empty.
3. **`plain`:** one or two plain sentences on what the item is or does and why it matters. No IDs, jargon or file paths unless the reader needs them.
4. **`sources`:** the SHA-256 of the **raw bytes** of each file as it is on disk (no newline normalisation, no re-encoding), e.g. `sha256sum` or Python `hashlib.sha256(path.read_bytes())`. Hash the files you actually read.
5. **`written_by`:** the harness and the exact model ID that wrote the labels. **`date`:** today.
6. **`phases` (optional, v0.2).** Write them when the plan has more than about 15 tasks, or when the parent asks; otherwise omit both `phases` and every `phase` key. Group the tasks into a few high-level stages a reader would name (for example "Survey design", "Pre-analysis plan", "Data collection", "Paper writing"), usually 3–7. List them in reading order as `{"id": "PH-1", "name": "<1-3 words>", "plain": "<one plain sentence>"}`, then give **every** task label, including researcher-lane gate tasks, a `"phase"` naming one of them (`E-PHASE` fails the build otherwise). Base the grouping on what the tasks do and the deliverables they feed, read from the source text; do not reorder, merge or reinterpret tasks. Phases may overlap in time. Deliverable and resource labels carry no `phase`.

## Register

Plain language in the user's register, not generic LLM cadence: short declarative sentences, concrete nouns, no hype, no filler, no "seamlessly", "robust", "leverage" or rhetorical triads. Follow the writer persona (`{{LIBRARY_ROOT}}/personas/writer.md`) and the voice rules it points to. Say what the item is, not how impressive it is. Do not restate or reinterpret substance: a label summarises the source text, it never adds a claim the source does not make.

## Check before returning

1. Run `python <skills>/_assets/plan-viewer/plan_viewer.py --check <planning-dir>`. It must exit 0 with no `E-LABEL-ID`, `E-PHASE`, `W-NO-LABEL`, `W-PHASE-EMPTY` or `W-STALE-LABELS` line.
2. Return to the parent: the file path, the count of labels per kind, the phases with their task counts (or "no phases"), the `--check` output, and any item whose source text was too unclear to label (labelled from its source name, listed for the parent).
