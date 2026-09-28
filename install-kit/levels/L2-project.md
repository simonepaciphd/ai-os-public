---
file: install-kit/levels/L2-project.md
version: 0.1.0
last_reviewed: 2026-09-27
governed_by: skills/project-setup.md, skills/project-setup-existing.md
---

# L2 — Project

## Goal
One project folder that another session can pick up: a `README.md` entry point, an `implementation-roadmap.md`, a folder layout that separates sources, working files and outputs, and two plain records, `asset-registry.csv` and `interaction-log.csv`.

## Prerequisites
- L1 recommended. The project skills wire the library in as one of their steps. Without L1, skip that step and record it as `OPEN`.
- A project the user chooses: a new one, or a folder they already have.

## Interview
Ask which case applies:
- **New project:** follow `skills/project-setup.md` ("How to Use"). It interviews for title, type, category and project rules.
- **Existing folder:** follow `skills/project-setup-existing.md`. Phases 0–2 map the folder and offer three options (full restructure, selective additions, minimal adoption). The choice is the user's.

## Steps
Follow the chosen skill in order, with these two adjustments for a kit install:
1. **Library wiring** (project-setup step 6, existing-project Phase 6): run it only if L1 is installed.
2. **Registration** (project-setup step 7, existing-project Phase 7): registration uses the native runtime, which arrives with L3. If L3 is selected, leave registration for L3. If not, skip it and record that in `install-state.md`.

Until L3 is installed, the agent appends rows to the two CSV files by hand, as `project-setup.md` describes ("Asset Registry", "Interaction Log").

Existing-project rules apply in full. In particular, any move of an existing file is planned and signed off first (Phase 3).

## Validation
- The folder tree, `README.md`, the roadmap and both CSV files exist, and the headers match `project-setup.md`.
- Existing project: the skill's "what changed" summary lists every file moved or added.
- Show the user the tree and the summary. The library defines no automated check for this level.

## Gate
Ask: "Is this the project structure you want?" Record the answer verbatim.
