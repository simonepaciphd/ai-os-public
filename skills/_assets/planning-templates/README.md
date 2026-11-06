# Planning templates (enforced)

These files are the starting point for a project's `planning/` folder. The format they follow is fixed in `../plan-viewer/FORMAT.md` (`plan-viewer-format-v1`); where this README and FORMAT.md differ, FORMAT.md wins.

| File | What it is | Filled at |
|---|---|---|
| `SPEC.md` | The output specification: goals, deliverables, requirements, acceptance tests. `## Deliverable types` holds one optional `deliverable D-###` block per deliverable so the viewer can draw a mockup; the inert `text` blocks show one example per catalog type. | Stages 1-2 (`planning-output-specification-protocol.md`; the `Resources` column at Stage 2) |
| `RESOURCES.md` | The starting state: every data, code, software and upstream asset (`RS-###`) and how it maps to deliverables. | Stage 2 (`planning-resource-map-protocol.md`) |
| `PLAN.md` | The adjudicated plan: lanes (the `researcher` row is reserved for the human decision-maker), the task graph, waves with targets, and one `### T-###` card per task with `#### Outputs`, `#### Verification and review` and `#### Decision points`. | Stages 3-5 (`planning-implementation-map-protocol.md` for the cards, `planning-adjudication-protocol.md` for the plan); gate tasks with `Generated-from: DP-###` are inserted by the decision classifier |
| `pages.yml` | GitHub Actions workflow that publishes `planning/page/Plan-Visual.html` to the repo's GitHub Pages on a push to the default branch. Copy to `.github/workflows/pages.yml`. The site is public even when the repo is private. | Stage 6, first lock in a repo under the user's own GitHub account (`planning-protocol.md` *Publishing the page*) |
| `Plan-Labels.json` | Example `plan-labels-v1` file: a short label and a plain description per task, deliverable and resource, plus the SHA-256 of each source file it was written from. Optional `phases` (an ordered list of `PH-#` names) with a `phase` on every task label give the page its Phases view; delete both to build without phases. Phases are a reading aid only (FORMAT.md §6). | Stage 5 writer pass, re-run after every approved spec delta |

Copy the three Markdown files into `<project>/planning/` and replace every `<angle-bracket>` placeholder. Folder layout (`planning/`, `planning/page/`, `planning/archive/records/`): `planning-protocol.md` *Folder layout*. Keep the section names and the table columns the viewer reads; extra columns and sections are allowed.

## Checking a project

```
python plan_viewer.py --check <planning-dir>
```

`plan_viewer.py` lives in `../plan-viewer/`. `--check` lints the folder against the format (missing sections or columns, cards, verification, references, cycles, schedule and edge consistency, labels and decision classes) and writes nothing. Exit code 0 means no errors (warnings may still print); 1 means errors; 2 means a usage or IO error. Without `--check` the same command builds `Plan-Visual.html`.

The templates themselves do not pass `--check`: their placeholders are not valid IDs.
