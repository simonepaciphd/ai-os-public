---
name: project-setup
description: Template + setup protocol for scaffolding a new social-science research project (or other research / writing / methodological project) under agentic workflow. Produces canonical folder structure, README, implementation roadmap, asset registry, interaction log, ledger row + per-project stanza, and skill-library wiring.
audience: public
version: 0.4
---

# Project Setup Protocol

## Registration-only route

For “Register this existing project: [path]”, use `project-registration.md`. The receiving task completes mechanical registration without restructuring or repeated persona handoffs. The interviews below apply to requested scaffolding or retrofit work.


This file is both a **template** and a **setup instruction** for agentic AI tools working in a research project. Copy it into a new project folder and either (a) fill in the bracketed placeholders manually and rename to `README.md`, or (b) invoke an agent with "run the project-setup protocol" to scaffold the folder semi-automatically.

Governing principles: **user control** and **radical transparency** — see `{{LIBRARY_ROOT}}/skills/about-governing-principles.md`. Humans retain all key decisions; provenance and verification are tracked for every asset.

---

## How to Use (Agent Instructions)

When asked to run this protocol, an agent should:

1. Ask the user for the **project title**, **project type** (empirical-research | position-paper | literature-review | data-exploration | methodological | other), **ledger category** (research-project | public-writing | teaching-project | business | personal — adapt to the user's own ledger schema), and any **project-specific rules**.
2. Create the folder structure under the "Folder Structure" section below, pruning branches that do not apply (e.g., a pure writing project can omit `inputs/`, `outputs/`, `scripts/`).
3. Generate a filled-in `README.md` from the template section below.
4. Generate `implementation-roadmap.md` by translating the user's outline / plan into a checkable to-do list.
5. Generate `asset-registry.csv` and `interaction-log.csv` with the schemas specified below. Pre-populate the registry with any files already present in the folder.
5a. **Create the project repo** (see *Project Repo* below): one Git repo per project, in a local directory outside any cloud-synced folder (e.g. `~/repos/<slug>/`), holding the project's code and other Git-relevant assets plus a `planning/` folder. If the project already has a local Git repo outside cloud sync, that repo is the project repo; do not create a second one. Add a remote only with the user's sign-off. Record the repo path in the project `README.md` (`Project repo: <path>`).
6. **Wire the project to the skills library.** If the user has an existing library, dispatch to `skills-library-connection.md` to pick the lowest-friction wiring (harness-native copy/symlink, instruction-file pointer, or README-only) for the (harness × library-format) pair. If no library exists, dispatch to `skills-library-setup.md` first, then to `skills-library-connection.md`.
7. **Register the created project.** Use `project-registration.md` with the title/category/subtype already established. If native bookkeeping is installed, use its `register-project` preflight/apply operation and preserve the actual conversation/cwd binding; do not manually duplicate native-owned ledger writes.
8. Report the final structure back to the user and confirm before proceeding to substantive work. Surface the new ledger row and stanza path.

---

# [Project Title] — Project Folder

## Project Overview

[1–3 sentences: research question / purpose, approach, and expected output (paper, replication package, dataset, memo).]

## Project Type

[empirical-research | position-paper | literature-review | data-exploration | methodological | other]

## Rules for Agents

Core rules (apply to every project):

1. **User retains control.** No substantive decision (design, interpretation, final phrasing, model/method choice) is made by an agent without explicit user sign-off.
2. **One instance, one task.** Start each non-trivial task in a fresh agent instance with a focused plan. Do not accumulate unrelated threads in a single context.
3. **Never modify files in `inputs/`** (empirical projects) or `background/` source material. These are read-only; derived artifacts go elsewhere.
4. **Register every new asset** (draft, figure, table, script, dataset, note) in `asset-registry.csv` with a creator flag (`human` / `agent` / `mixed`) and verification status (`not-verified` / `partially-verified` / `human-verified`). Without native bookkeeping, when the agent authors or substantively edits a text asset, also snapshot its output to `.cowork/snapshots/` and record the `ai_output_hash` (see Asset Registry below).
5. **Log every non-trivial session** in `interaction-log.csv` with date, input/output summary, and model metadata, plus `initiator`, coarse `task_difficulty`, and any substantive `decisions` surfaced (see Interaction Log below).
6. **Archive, don't delete.** Move obsolete files to the nearest `archive/` subfolder.
7. **Consult `implementation-roadmap.md`** before starting work and update it as steps complete.
8. **Skill orchestration.** For any complex task, first check the skill library at `{{LIBRARY_ROOT}}`. If no skill fits, ask the user whether to create one before improvising.
9. **Validation by default.** Prefer deterministic validation checks (tests, reproducibility runs, cross-source comparisons) over self-assessment.

Project-specific rules:

[Add constraints specific to this project — e.g., "all figures reproducible from scripts in figures/", "never cite sources outside background/literature/", "freeze section X after advisor review."]

## Folder Structure

Full template (prune branches that do not apply):

```
Project Folder/
├── README.md                      # This file, filled in
├── implementation-roadmap.md      # Living to-do list / plan
├── asset-registry.csv             # Provenance + verification tracking
├── interaction-log.csv            # Session-level user-agent log
├── .cowork/snapshots/             # Content-addressed AI-output snapshots (<sha256>.snap); low-salience provenance store
│
├── background/                    # Project knowledge (read-only source material)
│   ├── literature/                # Papers, references
│   ├── concepts/                  # Definitions, frameworks, notes
│   ├── feedback/                  # Advisor / reviewer / colleague notes
│   └── archive/
│
├── drafts/                        # Paper / memo drafts (writing projects)
│   └── archive/
│
├── figures/                       # Final figures (+ source if reproducible)
│   └── archive/
│
├── tables/                        # Final tables
│   └── archive/
│
├── scripts/                       # All code (empirical or demo)
│   ├── data-collection/
│   ├── data-cleaning/
│   ├── data-management/
│   ├── data-analysis/
│   └── archive/
│
├── inputs/                        # Raw & cleaned data — READ-ONLY at raw level
│   ├── raw/
│   ├── clean/
│   └── archive/
│
├── outputs/                       # Generated analysis results
│   ├── results/
│   └── archive/
│
└── appendix/                      # Replication package shipped with final output (see Replication Package)
    ├── README.txt
    ├── codebook.pdf
    ├── data/
    │   └── inputs/
    ├── outputs/
    │   ├── tables/
    │   └── figures/
    ├── scripts/
    ├── ai-disclosure/
    └── archive/                   # working tree only; never shipped
```

Guidance:
- **Writing-only projects** (position papers, literature reviews): keep `background/`, `drafts/`, `figures/`, `tables/`, optionally `scripts/` (for demos) and `appendix/`. Omit `inputs/` and `outputs/`.
- **Empirical projects**: keep the full tree. The data pipeline (raw → clean → merged → results) runs through `scripts/` and `inputs/` → `outputs/`.
- **Every subfolder** has a sibling `archive/` for routine cleanup.
- **Code lives in the project repo** (`<repo>/scripts/`, same subfolders) rather than the project folder, together with `planning/` (*Project Repo* below).

## Replication Package

`appendix/` is the replication package shipped with the final output. Its layout is fixed:

```
appendix/
├── README.txt                     # contents, run order, table/figure → script map, software + versions, runtime, seed locations, data-availability statement
├── codebook.pdf                   # for the final analysis dataset
├── data/
│   ├── inputs/                    # flat: the raw input datasets + one README.txt giving the provenance of each
│   └── <analysis-ready datasets>  # written by data_builder, documented by codebook.pdf
├── outputs/
│   ├── tables/
│   └── figures/
├── scripts/                       # exactly two scripts
│   ├── data_builder.<ext>         # data/inputs/ → analysis-ready datasets in data/
│   └── analysis.<ext>             # analysis-ready datasets → outputs/tables/, outputs/figures/
└── ai-disclosure/                 # AI-use disclosure material; contents depend on the user's AI system
```

- **Exactly two scripts**, whatever the number of stages: stages become sections or functions inside `data_builder` and `analysis`. A two-language pipeline keeps one script per step, each with its own extension.
- **`ai-disclosure/`** holds the disclosure material the user's AI system produces. What it contains is set per system.
- **Nothing else ships.** Working reports (code reviews, literature checks) and `appendix/archive/` stay out of the deposited package.
- **Scope.** New projects scaffold this layout. An existing project's `appendix/` is brought into it when the project next assembles a package (submission, conditional acceptance, deposit), not before (`project-setup-existing.md`).

## Project Repo

- Project repo: `[path]` — one local Git repo per project, never inside a cloud-synced folder (Google Drive, Dropbox, OneDrive sync can corrupt `.git`).
- Holds the project's code (`scripts/`) and other Git-relevant assets (configuration, small text assets worth versioning). Large data, binaries and material shared through cloud drives or Overleaf stay in the project folder.
- `planning/` holds the planning governance files directly, if you use a spec-first planning workflow: a specification of every deliverable, a resource map, an implementation plan and a changelog. One live plan per project; closed plans move to `planning/archive/<YYYY-MM-DD>-<name>/`.
- Commit each approved baseline and each approved change to the specification.

## Implementation Roadmap

See `implementation-roadmap.md` — the living plan for this project. Agents read it before starting work and check off items as they complete. Material changes to scope or sequencing must be confirmed with the user.

## Asset Registry

Every major asset is tracked in `asset-registry.csv`. Schema:

| Column | Values |
|--------|--------|
| `asset_path` | Relative path from project root |
| `asset_type` | draft \| figure \| table \| script \| dataset \| note \| reference \| other |
| `creator` | human \| agent \| mixed |
| `model_metadata` | Model ID + harness (e.g., `claude-opus-4-7 / claude-code`); blank if `human` |
| `created` | YYYY-MM-DD |
| `last_modified` | YYYY-MM-DD |
| `verification` | not-verified \| partially-verified \| human-verified |
| `notes` | Free text (purpose, known issues, review status) |
| `ai_output_hash` | sha256 of the AI-produced bytes at generation time; pointer into `.cowork/snapshots/`. Blank if `human`-created or not snapshotted (e.g. binaries). |

Where native bookkeeping is installed, submit asset metadata to its writer for
registry publication and snapshots; do not manually edit native-owned rows.
Otherwise append a row when creating an asset and update `last_modified` +
`verification` on substantive edits.

**Resource inventory.** The registry is also the project's resource inventory: starting resources a plan depends on (datasets, existing code, documentation) get rows too, human-created ones included, so every deliverable can be traced to its inputs. A planning workflow's resource-mapping step starts from this file.

Without native bookkeeping, when an agent **creates or substantively edits a text-class asset** (draft / script / note / table-as-text), it also snapshots the exact bytes it produced: compute the sha256, write the bytes to `.cowork/snapshots/<sha256>.snap` (skip if that hash already exists — the store is content-addressed and keeps the full AI-edit chain for free), and record the sha256 in `ai_output_hash`. Binaries (figures, datasets) are not snapshotted — leave `ai_output_hash` blank. The snapshot is what lets a later audit diff AI-output → final artifact; it needs no human action. Keep `.cowork/` low-salience — it is a provenance store, never a live score surface.

Verification *acts* (opening a cited source, an independent search, running a test, recomputing a result) are read from the session transcript at audit time, not logged here; the `verification` status column remains a coarse after-the-fact claim.

## Interaction Log

Every non-trivial user-agent session is logged in `interaction-log.csv`. Schema:

| Column | Values |
|--------|--------|
| `date` | YYYY-MM-DD |
| `session_id` | Short identifier (e.g., `2026-04-21-a`) |
| `harness` | claude-code \| chatgpt \| codex \| antigravity \| other |
| `model` | Model ID (e.g., `claude-opus-4-7`) |
| `researcher_input_summary` | 1–2 sentences |
| `agent_output_summary` | 1–2 sentences |
| `assets_affected` | Comma-separated paths (match `asset-registry.csv`) |
| `notes` | Free text |
| `initiator` | human \| agent \| mixed — who set this session's agenda |
| `task_difficulty` | low \| medium \| high — coarse difficulty, for normalizing editing/verification intensity |
| `decisions` | Substantive decisions surfaced this session, comma-free. Per decision `<ratification>/<alt>` — ratification ∈ approved \| modified \| deferred \| rejected, alt ∈ alt \| noalt (were alternatives shown); multiple `;`-separated. Blank = none surfaced. Example: `modified/alt;approved/noalt` |

These columns form the native-compatible schema. Native installations publish
session rows through checkpoint/close requests; do not append duplicate rows.
The native writer fills `initiator` and `task_difficulty` with `human` and
`medium` when a request omits them, and leaves `decisions` blank: decisions go
to the session's closeout note instead.

Optional: for reproducibility-critical projects, consider cryptographic attestation of log entries (see Gordon, Samii, Su — Data-NoMad, arxiv).

## Data Sources *(empirical projects only)*

| Source | File(s) | Coverage |
|--------|---------|----------|
| [Dataset name] | `inputs/raw/[filename]` | [Years / waves / scope] |

## Cleaned Data *(empirical projects only)*

All cleaned data lives in `inputs/clean/` as [format] files, following the naming convention `[convention]`.

## Analysis Pipeline *(empirical projects only)*

1. **Raw data** → `scripts/data-cleaning/` → **Cleaned data** (`inputs/clean/`)
2. **Cleaned data** → `scripts/data-management/` → **Merged analysis-ready data**
3. **Merged data** → `scripts/data-analysis/` → **Results** (`outputs/results/`)

## Key Methodological Notes *(empirical projects only)*

- **Dependent variable(s):** [...]
- **Independent variable(s):** [...]
- **Method:** [...]

## Language & Tools

- **Primary language(s):** [e.g., R, Python, Stata, LaTeX]
- **Raw data formats:** [.csv, .sav, .dta, .rds, ...]
- **Output formats:** [.parquet, .rds, .pdf, ...]

## Skills

- Skill library: `{{LIBRARY_ROOT}}`
- Wiring: set during setup by `skills-library-connection.md` (lowest-friction option for the project's harness and library format).
- For any complex task, check for an appropriate skill first. If none fits, ask the user whether to create one before improvising.

## External Integrations

- LaTeX / Overleaf root: `{{OVERLEAF_ROOT}}` (if applicable; e.g., `~/Dropbox/Apps/Overleaf`).
- Ask whether an Overleaf or other external typesetting project already exists for this work and whether to set one up / link it.
- For other integrations (Zotero library, GitHub remote, Linear/Jira, shared drives), record paths or identifiers here.
