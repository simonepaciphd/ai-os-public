---
name: planning-resource-map-protocol
description: Inventory a project's starting resources and connect them to an approved output specification — asset discovery, resource-to-deliverable mapping, two-way gap and coverage review, and resource links for the spec. Use as Stage 2 of planning, run in one dedicated read-only subagent because discovery is search-heavy; also usable alone as a resource audit against an existing spec.
audience: public
version: 0.3
---

# Planning Resource-Map Protocol

Document the starting state before planning the build. Produce `RESOURCES.md` and proposed resource links so every specified deliverable is traceable to the data, code, software and upstream artifacts that will produce it, and every existing asset is either used or classified.

Composes with `planning-protocol.md` (Stage 2), upstream `planning-output-specification-protocol.md`, and downstream `planning-implementation-map-protocol.md`, which consumes `RESOURCES.md` instead of re-running discovery.

Version: 0.3 (first public release; earlier versions are not shipped in this repo).

## Invocation contract

The coordinator spawns this skill in **one dedicated subagent** after the spec draft is approved. Discovery can take many searches; keeping it in a subagent keeps the coordinator's context small.

Required inputs:

- the approved `SPEC.md` draft (deliverable IDs `D-*` and requirements `R-*`);
- the project root and any other locations the spec or user names (drives, repositories, data stores);
- the project's write boundaries (`background/` read-only; `inputs/` add-only with the user's approval per `project-setup.md` Rule 3; anything the project instructions protect).

Rules for the subagent:

- Work **read-only**. No moves, renames, installs, credential use, or external messages. Never stop, kill or restart a process you did not start; if a job hangs, report it and stop.
- Return `RESOURCES.md` content, proposed spec resource links and the gap review to the parent; do not edit the spec, plan, ledgers or project files.
- Record facts with their evidence (path, listing, schema read). Mark anything not checked `UNVERIFIED`; never infer a dataset's contents from its name alone.
- Questions only the user can answer (access, ownership, which version is authoritative) go in the return as `RQ-*` items (not `Q-*`, which belongs to the spec); do not guess.

## Pass A — Asset discovery

**Start from the project's `asset-registry.csv`**: it is the resource inventory, so every registered asset is a candidate resource and keeps its registry path. Then inventory folders, data sources and schemas, scripts, notebooks, environments, software, configuration, documentation, and external services relevant to the spec. For each asset record:

| Asset ID | Location | Type | Description | Purpose / producer | Access constraints | Verification status | Registry |
|---|---|---|---|---|---|---|---|

Verification status: `VERIFIED` (opened and checked), `LISTED` (seen, not opened), `UNVERIFIED` (named by a source, not found or not checked). Use stable `RS-*` IDs; never renumber. `Registry` is `registered` (row exists; cite `asset_path`) or `unregistered`. After the user approves `RESOURCES.md`, the coordinator registers unregistered `agent`/`mixed` resources through the native writer (at most 25 per request; a manifest for large sets). Human-created resources stay `unregistered` until the native writer supports registering them; never hand-edit the registry.

Bound the search: start from the paths the spec and project instructions name, then the project tree; stop widening once each deliverable has candidate inputs or a clear gap. Report the search scope so the coordinator knows what was not looked at.

## Pass B — Map resources to deliverables

Link every `D-*` (and `R-*` where the input differs) to the resources it needs. Only `D-*` links go into the spec's `Resources` column; `R-*` links stay in `RESOURCES.md`:

| Spec ID | Needed input | Resource(s) | Relationship | Confidence | Evidence |
|---|---|---|---|---|---|

Relationship: `input-data | existing-code | software | upstream-artifact | documentation | external-service`. These rows become the spec's resource links.

## Pass C — Two-way gap and coverage review

- **Unresourced deliverables:** outputs with missing inputs, tools, permissions or prerequisites. For each, list the options for the user — acquire/create the resource, revise the deliverable, or mark the dependency `UNRESOLVED`. Make no choice.
- **Unmapped resources:** assets that serve no current deliverable. Classify each as `useful | redundant | out-of-scope | investigate`, with a one-line reason.

## Pass D — Resource-linked specification (proposal)

Return:

1. `RESOURCES.md` (template below);
2. a proposed `Resources` column (resource IDs) for each deliverable row of `SPEC.md`;
3. the gap review for the user.

The coordinator writes both files after the user decides the gaps. Unresolved gaps stay `UNRESOLVED` in both files; they are never treated as solved.

## `RESOURCES.md` template

Use `_assets/planning-templates/RESOURCES.md` (format contract `_assets/plan-viewer/FORMAT.md` §4). Its sections and columns are unchanged from the earlier inline template.

What it adds: a filled example row per table and the lint rule that the plan viewer reads `Asset ID` (`RS-###`) and `Description` from `## Asset inventory`, so keep those two columns and that section name.

## Completion gate

Return only when:

- every `D-*` has at least one mapped resource or an unresourced-deliverable row;
- every inventoried asset is mapped or classified;
- every asset has a verification status, evidence and a registry status;
- the search scope is stated;
- no file has been modified.

## Common failure modes

- **Name-based inventory:** a file is described from its name. Open it or mark it `LISTED`.
- **Silent gap closing:** a missing input is "covered" by an asset that only resembles it. Record the gap and the near-match as an option.
- **Unbounded search:** discovery crawls whole drives. Start from named paths and state the stopping point.
- **Choosing for the user:** the subagent picks acquire vs revise. Return options only.

## Worked example

For an event-study spec with deliverable D-003 (FIG-03, event-study figure), discovery finds `panel.csv` (VERIFIED: unit-year keys, 1990-2020) and `cohort.do` (VERIFIED: estimates the model, writes no CSV). Mapping links D-003 to both. The gap review finds treatment dates are absent from `panel.csv`, an unresourced input with options "add a treatment-date source", "revise D-003's sample" or "unresolved". It also classifies an old `robustness_v1/` folder as `investigate`. The user chooses a source; the coordinator writes `RESOURCES.md` and the spec links before mapping starts.
