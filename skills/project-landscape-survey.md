---
name: project-landscape-survey
description: Read-only, high-level survey of all visible projects in the user's project root (e.g., a Dropbox folder, `~/projects/`, a shared drive). Produces a project-landscape map with life-stage classification per project. One-shot skill, intended to be invoked from a fresh session and write its output to the user's identity-sources path.
audience: public
version: 0.1
---

# Project Landscape Survey

A read-only skill for surveying the user's project landscape (e.g., the contents of a Dropbox folder, a `~/projects/` tree, or another canonical project root) and producing a life-stage map. Designed for one-shot invocation from a fresh session — no interview, no multi-phase loop. The output is consumed downstream by identity-layer build steps and (optionally) by a portfolio-management persona, if the user has one.

Governing principles: **user control** and **radical transparency** — see `{{LIBRARY_ROOT}}/skills/about-governing-principles.md`. This skill describes the project landscape; it does not prescribe action on any project. Every classification is traceable to a concrete signal.

---

## When to use

- Initial identity-layer build (when standing up a portfolio-aware agent stack) needs a portfolio map.
- Periodic refresh of the project landscape (e.g., quarterly, or before annual reviews).
- A new persona or audience tier needs visibility into the existing portfolio.

Do not use when:
- A single-project audit is needed — use a project-specific protocol instead.
- Project quality assessment is the goal — this skill stays structural and refuses quality opinions.
- Mutating or reorganizing files is the goal — this skill is strictly read-only.

## Artifacts the skill produces

1. `{{LIBRARY_ROOT}}/identity/sources/project-landscape.md` — the survey output (overwrites prior version; previous version moved to `project-landscape.archive-YYYY-MM-DD.md` if present).
2. No other side effects. No registry updates. No log entries.

## Universal rules

1. **Read-only.** No `Edit`, no `Write` outside the single output file, no mutating `Bash` commands. Allowed Bash operations: `ls`, `stat`, `find` (read-only flags), `git log` / `git status` (no fetch/pull), `wc -l`. Forbidden: `mv`, `rm`, `cp`, `git add`, `git commit`, anything that changes filesystem state.
2. **High-level only.** Use folder structure, file names, modification times, and presence flags for canonical files (`README*`, `asset-registry.csv`, `interaction-log.csv`, `.git/`). Do **not** read paper drafts, code files, or notes to infer project content.
3. **Description over prescription.** Classify life-stage. Never opine on quality, importance, or what should happen next. Recommendations are out of scope.
4. **Surface, don't decide.** If life-stage is ambiguous, mark `unclear` and record the conflicting signals. Do not guess.
5. **Provenance for every classification.** Every life-stage label is followed by the specific signal(s) that produced it. A label without a signal is a bug.
6. **No cross-project synthesis.** Do not write a "summary of the user's research agenda" or thematic groupings. The output is a per-project list, not an editorial.

---

## Scope of the survey

**Root scan path:** `{{PROJECTS_DIR}}` — the directory containing the user's active projects (typically `~/Dropbox/`, `~/projects/`, or wherever the user keeps them; configured during library setup).

**Top-level folders to skip entirely:**
- App-managed sync folders (e.g., Overleaf project mirrors, cloud-storage app directories).
- The library root itself (`{{LIBRARY_ROOT}}`) — this is infrastructure, not a project.
- Any infrastructure-only folder the user has flagged (e.g., a research-lab control room, shared CI config, dotfiles).
- Any folder name starting with `.`, `_`, or `~` (hidden / archive / temp markers).

The user can extend or override the skip list in their library setup.

**Depth policy:**
- Enumerate top-level folders (depth 1).
- For each top-level folder, decide: is this itself a project, or a container of projects? Containers (e.g., a folder named `Research/` or `Papers/`) recurse one more level (depth 2).
- Beyond depth 2: only descend to confirm a specific signal (e.g., presence of `drafts/submitted/`, `data/raw/`, `.git/HEAD`). Do not exhaustively walk subtrees.

## What to extract per project

For each project candidate, record:

| Field | Source |
|---|---|
| `name` | Folder name |
| `path` | Absolute path |
| `life_stage` | One of the values from the taxonomy below |
| `last_modified` | Most recent file mtime in the folder, recursive (use `find -printf` or equivalent) |
| `signals` | Bullet list of the specific observations that produced the life-stage label |
| `canonical_files` | Presence flags for `README*`, `asset-registry.csv`, `interaction-log.csv`, `.git/`, `drafts/`, `data/`, `submissions/`, `archive/` |
| `notes` | Free-text only when classification is `unclear` or there is a salient anomaly |

## Life-stage taxonomy

Use exactly one of these labels per project:

- `seed` — recently created (<14 days), minimal content (≤5 files, no `drafts/` or `data/`)
- `active` — modifications in the past 30 days, multiple touched files, no archive markers
- `slow` — modifications in 30–180 days, intermittent activity
- `dormant` — last touched 180+ days ago, no archive markers, no submission markers
- `archived` — explicitly inside an `archive/` parent or with an `archive/` flag file; or dormant for 365+ days
- `under-review` — `drafts/submitted/` or `drafts/R&R/` subfolder present, or `interaction-log.csv` shows a recent submission entry
- `published` — explicit `published/` marker, accepted draft, or DOI/citation in a top-level metadata file
- `unclear` — signals are mixed or absent; reason recorded in `notes`

## Output format

Write to `{{LIBRARY_ROOT}}/identity/sources/project-landscape.md`. If a prior version exists, rename it first (`project-landscape.archive-<scan-date>.md`) before overwriting.

```markdown
# Project Landscape Survey

- **Scan date:** <YYYY-MM-DD>
- **Root path:** {{PROJECTS_DIR}}
- **Projects found:** <N>
- **Skipped (per scope rules):** <list>

## Distribution

- seed: <n>
- active: <n>
- slow: <n>
- dormant: <n>
- archived: <n>
- under-review: <n>
- published: <n>
- unclear: <n>

---

## Projects

### <project-name>

- **path:** <absolute path>
- **life_stage:** <label>
- **last_modified:** <YYYY-MM-DD>
- **canonical_files:** README ✓ | asset-registry.csv ✗ | interaction-log.csv ✗ | .git ✓ | drafts/ ✓ | data/ ✗ | submissions/ ✗ | archive/ ✗
- **signals:**
  - <observation 1>
  - <observation 2>
- **notes:** <only if unclear or anomalous>

---

[repeat per project, alphabetical by name]

---

## Ambiguity log

For every `unclear` classification, the conflicting signals.

## Skipped folders

For every top-level folder that was skipped, the reason (per scope rules).
```

## Workflow

1. List the root path's top-level folders. Identify which are projects vs. containers vs. skip-list.
2. For each candidate, gather the fields above using only read-only tools.
3. Classify life-stage. If signals conflict, mark `unclear` and record both.
4. Compose the output document. Sort projects alphabetically by name.
5. If a prior `project-landscape.md` exists, rename it with the archive suffix.
6. Write the new file.
7. Stop. Do not propose actions, recommendations, or follow-ups beyond the file.

## Handoff with other skills

- The output is consumed by an identity-writing protocol (when the user has one) at the source-reading step.
- A portfolio-management persona (e.g., a chief-of-staff persona, when the user has drafted one) may invoke this skill on demand for portfolio-level deliberation.
- This skill does **not** call other skills. It is a leaf node.

## Common failure modes

- **Reading inside files.** The agent opens a paper draft to "understand the project." Recovery: re-read Universal Rule 2; restrict to folder structure, names, mtimes, and presence flags.
- **Inflated last-modified signals.** A folder shows a recent mtime because a sync service touched metadata, not because the user touched it. Recovery: cross-check with file content mtimes (`find -type f -printf '%T@ %p\n' | sort -n | tail`) before classifying. Mark `unclear` if signals disagree.
- **Hidden archives.** The user's archive convention may be a sibling folder rather than a subfolder. Recovery: surface and ask in a follow-up; do not auto-classify based on guessed conventions.
- **Editorializing.** The output reads like a research-agenda summary. Recovery: cut every sentence that is not a per-project, signal-grounded fact. The skill describes; it does not narrate.
- **Recommendation drift.** The output starts proposing what to revive, retire, or prioritize. Recovery: per Universal Rule 3, classify only. Recommendations belong to a portfolio-management persona's deliberation downstream, not to this skill.
- **Skipping the ambiguity log.** Every `unclear` label needs an entry. A survey with `unclear` labels and an empty ambiguity log is incomplete.

## Worked example

(To be filled in after first invocation in the user's library.)
