---
name: planning-protocol
description: Orchestrate a complex goal from an interview-built output specification with its own adversarial spec review, through a subagent-run resource map, technical task mapping, an automatically spawned adversarial plan review, user-aware adjudication and a single baseline lock, dependency-safe multi-agent execution, and during/post-execution reconciliation of any changes to the main spec. Use for `/planning`, "plan this project", "spec and plan this", or any substantial goal that should be defined before implementation, decomposed for parallel AI-OS execution, and checked for spec drift as work proceeds.
audience: public
version: 0.8
---

# Planning Protocol

Turn an initially broad goal into a reviewed description of the final result, a map of the resources that will produce it, a traceable technical plan, an independent adversarial review, an adjudicated execution plan locked together with the spec as one baseline, and a durable report of every spec change discovered during or after execution. This coordinator keeps each stage and artifact distinct. It implements the *Agentic Research Workflow* research guide (2026; "the PDF" below) and extends it with the plan review, adjudication and spec-delta channel.

Composes with `planning-output-specification-protocol.md`, `planning-resource-map-protocol.md`, `planning-implementation-map-protocol.md`, `planning-adversarial-review-protocol.md`, `planning-adjudication-protocol.md`, `planning-decision-points-protocol.md`, `planning-labels-protocol.md`, `planning-spec-reconciliation-protocol.md`, and `task-engineering-protocol.md`; tool asset `_assets/plan-viewer/` (builder `plan_viewer.py`, contract `FORMAT.md`) and enforced templates `_assets/planning-templates/`.

Version: 0.8 (first public release; earlier versions are not shipped in this repo).

## Artifacts and stage gates

| Stage | Artifact | Gate |
|---|---|---|
| 1. Specify | `SPEC.md` (draft) + `Spec-Review.md` | Spec reviewed adversarially by an isolated reviewer; user resolves findings and `APPROVE`s the endpoint draft; no implementation content |
| 2. Resources | `RESOURCES.md` + resource links in `SPEC.md` | Subagent inventory; two-way gap review resolved or explicitly unresolved; user approves the resource-linked spec |
| 3. Map | `Plan-Draft.md` | Every requirement maps to one or more executable task cards with procedural verification |
| 4. Challenge | `Plan-Review.md` | Independent reviewer tests the map against the approved spec and resource map |
| 5. Adjudicate | `PLAN.md` + `Decision-Classes.json` (optional) + `Plan-Labels.json` + `page/Plan-Visual.html` | Findings resolved; DAG, waves, claims, researcher gates, and review gates are executable; decision points classified (optional); labels written; `plan_viewer.py --check` passes and the page is built |
| 6. Baseline lock | `SPEC.md` + `RESOURCES.md` + `PLAN.md` `LOCKED` | User approves the three files together as the implementation baseline; project `CLAUDE.md` pointer block proposed |
| 7. Launch | Per-task handoff prompts | `task-engineering-protocol` packages each ready task or sequential chunk |
| 8. Reconcile | `CHANGELOG.md` + `Spec-Reconciliation.md` | Execution-discovered changes are reported, adjudicated, versioned, propagated, and compared with the delivered result; final traceability review |

Keep the stage artifacts separate even if presenting them in one chat. Location: the plan lives in `planning/` of the project's **project repo** (`project-setup.md` *Project Repo*: one repo per project, e.g. `~/repos/<ledger-slug>/`, holding its code and `planning/`, or the project's existing local Git repo). One live plan per project (not per-goal folders): a new goal enters the locked `SPEC.md` as a spec delta (`SCOPE-ADD`); a closed plan moves to `planning/archive/<YYYY-MM-DD>-<name>/` before a fresh plan starts. Outside a registered project, present them in chat unless the user chooses a path.

**Folder layout (v0.7).**

- `planning/` top level holds only `SPEC.md`, `RESOURCES.md`, `PLAN.md`, `CHANGELOG.md`, `Plan-Labels.json`, the current baseline lock record if the project keeps one (e.g. `Baseline-Lock-<YYYY-MM-DD>.json`), and `Decision-Classes.json` when the plan uses one. `plan_viewer.py` reads labels and decision classes only from the folder holding the three governance files, so those two stay here.
- `planning/page/` holds the built `Plan-Visual.html` and any check files written beside it. Nothing else.
- `planning/archive/records/` holds every process record, written there from the start: `Plan-Manifest.md`, `Spec-Review.md`, `Plan-Draft.md` and its task cards, `Plan-Review.md`, `Spec-Reconciliation.md`, interview and rulings notes, superseded lock records. Prior locked versions of the governance files go to `planning/archive/` (dated subfolders). `planning/archive/README.md` indexes every file there by path.
- The project `README.md` links the published plan page and describes this layout in one short paragraph.

**Publishing the page.** When the project repo is owned by the user's own GitHub account, the plan page is always published through that repo's GitHub Pages. Repos owned by organisations or by co-authors get no Pages site; their page stays a local file (plus an Artifact where the harness supports it). On GitHub Pro a Pages site from a private repo is **public**: anyone with the URL can read the page, though not the repo. There is no content check before publishing. Deployment uses the workflow in `_assets/planning-templates/pages.yml`, copied to `.github/workflows/pages.yml`; a push of `planning/page/Plan-Visual.html` to the default branch publishes it. Enabling Pages is a public-surface action: the agent never runs it but hands the user one line, `! gh api -X POST repos/<owner>/<repo>/pages -f build_type=workflow` (`-X PUT` when Pages already exists on the repo, e.g. a legacy `gh-pages` source), and then checks with the read-only `gh api repos/<owner>/<repo>/pages`.

**PDF correspondence.** PDF stage 1 (SPEC) = Stage 1; PDF stage 2 (RESOURCES) = Stage 2; PDF stage 3 (PLAN) = Stages 3-5; PDF stage 4 (researcher approval) = Stage 6; PDF stage 5 (waves) = Stage 7; PDF §5 change control = Stage 8 plus `planning-spec-reconciliation-protocol.md`. The PDF's four repository files are `SPEC.md`, `RESOURCES.md`, `PLAN.md` and the project `CLAUDE.md` (Phase 6), plus `CHANGELOG.md`. **Deliberate differences from the PDF:** the folder is named `planning/` rather than `governance/`, and the project repo sits outside the cloud-synced project folder. Process artifacts the PDF does not name: `Plan-Manifest.md`, `Spec-Review.md`, `Plan-Draft.md`, `Plan-Review.md`, `Decision-Classes.json`, `Plan-Labels.json`, `Plan-Visual.html`, `Spec-Reconciliation.md`.

**Templates.** The governance file templates (`SPEC.md`, `RESOURCES.md`, `PLAN.md` with its task cards, `Plan-Labels.json`) live in `_assets/planning-templates/` and follow `_assets/plan-viewer/FORMAT.md`; `plan_viewer.py --check` enforces them. The sub-protocols point to these files instead of carrying inline copies.

## Universal rules

1. **What before how.** Do not name tools, implementation tasks, code structure, staffing, or sequence while Stage 1 is open. Feasibility constraints may be recorded only as constraints on the result. From Stage 2, the spec may carry resource links (which existing assets each deliverable depends on); tool and task choices stay out of it.
2. **No silent gap filling.** Inspect available context first. Infer only what the user or an authoritative artifact establishes; label the rest `OPEN` and interview the user.
3. **Stable traceability.** Assign durable IDs to goals, deliverables, requirements, constraints, non-goals, acceptance tests, and tasks. Never renumber an ID after another artifact references it.
4. **Stage gates.** Never start Stage 2 from an unapproved spec draft, Stage 3 from an unapproved resource-linked spec, Stage 4 from an incomplete technical plan, Stage 6 from an unadjudicated review, or execution from an unlocked baseline. Before the Stage 6 lock the spec changes only with the user's approval, recorded in its change history; after the lock, only through a spec delta.
5. **Separate authorship.** The spec author must not impersonate the spec reviewer, and the mapping agent must not impersonate the plan reviewer. Each reviewer receives the raw artifacts and produces findings independently.
6. **Automatic adversarial review.** Spawn the spec reviewer once the spec draft passes its completeness checks, and the plan reviewer once `Plan-Draft.md` passes its structural gate, without waiting for an additional user request. If the harness cannot spawn, run the same prompt in the freshest isolated context available and disclose the limitation.
7. **Aggressive safe parallelism.** Prefer many focused agents when write sets and inputs are independent. Never manufacture parallelism across real dependencies or shared write scopes.
8. **Single writer for shared surfaces.** Within a wave, every writable path or logical section has one owner. Route shared-file changes through an integration task or explicit section claims.
9. **Execution authorization is explicit.** `PLAN_ONLY` stops after the Stage 6 baseline lock. `PLAN_AND_EXECUTE` may launch only after Stage 6 and only when the original request authorized implementation.
10. **AI-OS coordination is load-bearing.** When the AI OS is present, read `coord/SPEC.md`, register a session, inspect live claims before writes, count slots before spawns, maintain heartbeats/claims, honor control flags, and close the session.
11. **Security boundary.** If a proposed step could mislead the user, harm the project, expose sensitive material, or commit the user to an unframed position, stop and put it to the user as a decision before proceeding.
12. **No silent spec drift.** Execution agents report any conflict, clarification, added constraint, scope change, acceptance change, or delivered deviation through `planning-spec-reconciliation-protocol.md`; they never edit the locked goal spec directly.
13. **Git records approved changes.** Commit the governance files together in the project repo at the baseline lock and at each approved spec delta, naming the delta ID; versioned snapshots and `CHANGELOG.md` are kept as well, together with the rebuilt `planning/page/Plan-Visual.html`. Never add a remote or push without the user's sign-off; in a repo with Pages, that push also publishes the page.

## Phase 0 — Initialize

1. Determine mode from the request: `PLAN_ONLY` unless implementation is explicitly requested; otherwise `PLAN_AND_EXECUTE`.
2. Identify the project root, its project repo (create it per `project-setup.md` Step 5a if the project has none; the first v0.4 plan in an already-registered project creates it), artifact location, authoritative inputs, relevant persona, and requested deadline or resource limits.
3. When the AI OS exists, run its coordination startup before any write or spawn.
4. Silently inventory nearby plans, specs, templates, skills, source files, and project ledgers. Summarize only what materially changes the interview.
5. Create `planning/archive/records/Plan-Manifest.md` (and `planning/archive/README.md`, the path index) with the protocol version (`planning-protocol v0.8`), artifact paths, stage status (`not-started | open | approved | locked | superseded`), plan name, and mode.

Do not ask the user to repeat facts that can be read safely from local artifacts.

## Phase 1 — Specify the result

Load and execute `planning-output-specification-protocol.md` completely.

- Produce the `SPEC.md` draft (PDF Passes A-B: brief, clarification).
- Run its completeness checks.
- **Spec review (PDF Pass C).** Check AI-OS control state, slots and claims, then spawn one context-isolated reviewer with `planning-adversarial-review-protocol.md` in `SPEC` mode. Give it only the user's brief, the spec draft, the authoritative inputs the spec cites, and a read-only instruction. The parent writes the returned findings into `Spec-Review.md`. The user resolves every substantive finding; the parent applies resolved, mechanical fixes.
- **First complete spec (PDF Pass D).** Consolidate brief and review decisions; present the spec in a scannable form and obtain an explicit `APPROVE`, or record the user's precise edits and repeat.
- Mark Stage 1 `approved` in `Plan-Manifest.md` only after sign-off. The spec is not `LOCKED` until Stage 6.

If the user changes the goal later, reopen Stage 1, mark downstream artifacts `superseded`, and regenerate them. Do not patch a changed goal invisibly into an old technical plan.

## Phase 2 — Map resources

Load `planning-resource-map-protocol.md` and run it in **one dedicated subagent** (discovery is search-heavy; keep it out of the coordinator's context). Check control state, slots and claims before spawning. Give it the approved spec, the project root and the protocol; it works read-only and returns `RESOURCES.md` and the proposed resource links to the parent.

- The parent writes `RESOURCES.md` and adds the resource links to `SPEC.md` (recorded in its change history).
- Put the two-way gap review to the user: each unresourced deliverable (acquire/create, revise the deliverable, or mark unresolved) and each unmapped resource class that needs a choice. Unresolved gaps stay `UNRESOLVED`; never treat them as solved.
- Mark Stage 2 `approved` after the user approves the resource-linked spec.

## Phase 3 — Map implementation

Load and execute `planning-implementation-map-protocol.md` completely with the approved `SPEC.md`, `RESOURCES.md` and the approved project context.

- Produce `Plan-Draft.md` plus task cards (embedded or under `Task-Cards/`).
- Require complete requirement coverage, an acyclic dependency graph, explicit inputs/outputs/tools/skills/review for every task, and a proposed agent-wave topology.
- Do not treat the proposed topology as final until adversarial review and adjudication finish.

## Phase 4 — Spawn the adversarial plan reviewer

Before spawning, check AI-OS control state, live slot count, and current claims. Then launch exactly one context-isolated reviewer by default; use a second only for unusually high-stakes or multi-domain plans and only when capacity permits.

Give the reviewer only:

- the approved, resource-linked `SPEC.md` and `RESOURCES.md`;
- `Plan-Draft.md` and its task cards;
- the relevant project tree or interface inventory when needed to verify feasibility;
- `planning-adversarial-review-protocol.md`;
- a read-only instruction and a requirement to return findings to the parent rather than edit shared artifacts.

Do not give the reviewer the mapper's private rationale, expected findings, or a summary that reveals the intended answer. The parent writes the returned review into `Plan-Review.md` after checking live claims.

If the reviewer identifies a Stage-1 ambiguity rather than a planning defect, label it `SPEC-QUESTION`; do not let the reviewer silently rewrite the goal.

## Phase 5 — Adjudicate the plan

Load and execute `planning-adjudication-protocol.md` completely using the spec, resource map, draft plan and review.

- Resolve mechanical coverage, consistency, dependency, and collision defects directly when the fix follows uniquely from the approved spec.
- Batch genuine user decisions into small interviews, showing the consequence of each option.
- Produce `PLAN.md`, including the finding disposition ledger, revised task graph, parallel waves, ownership/claims, integration points, and launch manifest.
- Re-run all readiness checks after edits; a resolved review is not enough if the edited DAG is invalid.

Stage 5 is complete only when no unresolved critical/high finding remains and each `USER-DECISION` is answered or explicitly deferred with its dependent tasks blocked.

**Close Stage 5 (v0.5).** Once `PLAN.md` is settled, in this order:

1. **Decision points (optional).** Classify the task cards' `DP-###` items and bake a `researcher`-lane gate task into `PLAN.md` for each substantive one, per `planning-decision-points-protocol.md`. Before the lock only; the paid JEV call is run by the user from a `!` command; agents never run paid calls (`planning-decision-points-protocol.md` §3).
2. **Writer labels pass.** A writer subagent writes `planning/Plan-Labels.json` per `planning-labels-protocol.md`. No sign-off; re-run after every approved spec delta. For a plan with more than about 15 tasks, the same pass also groups the tasks into a few named phases (v0.8; FORMAT.md §6), which the page shows as its default Phases view.
3. **Build the plan page.** Run `python <skills>/_assets/plan-viewer/plan_viewer.py --check <planning-dir>`; it must exit 0. Then create `<planning-dir>/page/` if it is missing (the builder does not create folders) and run `python <skills>/_assets/plan-viewer/plan_viewer.py <planning-dir> -o <planning-dir>/page/Plan-Visual.html` and give the user the `file:///` link it prints. Nobody edits the page by hand; rebuild after any change. In a repo with Pages (see *Publishing the page*), the page goes public when it is pushed; otherwise publish it as an Artifact when the harness supports that. Keep the file in `planning/page/` either way.

**Phases view (v0.8).** When `Plan-Labels.json` declares phases, the page opens on a simplified view with one card per phase (name, plain description, wave span, progress, decisions for you, results), expandable to its tasks; Map and Timeline stay one click away. Phases are agent-written and display-only: they are not in `PLAN.md`, not part of the baseline lock and not a dispatch unit. Execution still launches by wave (Phase 7), and a phase may span and overlap any waves. Re-run the labels pass, not a spec delta, to change them.

What still holds from the old dashboard rules: all views (Phases, Map and Timeline) render from one schedule source (`PLAN.md` waves) on the **same time axis**, never topological depth; wave dates are targets, not commitments, and the page says so. The schedule and edge checks now run at build time (`E-SCHEDULE`, `E-EDGE-SYNC`, `E-CYCLE`; `_assets/plan-viewer/FORMAT.md` §8) instead of as a runtime badge. **Theme change:** the page is light only; v0.4 required light + dark.

## Phase 6 — Lock the baseline

Present `SPEC.md`, `RESOURCES.md` and `PLAN.md` together for one explicit `LOCK` (PDF stage 4): a short synopsis of what will exist, the unresolved resource gaps, the researcher gates, and the first ready wave. On sign-off mark all three `LOCKED` with the timestamp, set Stage 6 `locked` in `Plan-Manifest.md`, rebuild the page, and commit them together in the project repo. From here every spec change is a spec delta.

At the first lock in a repo under the user's own GitHub account, also: add `.github/workflows/pages.yml` from `_assets/planning-templates/pages.yml`; add the README paragraph that links the page (`https://<owner>.github.io/<repo>/`) and describes the `planning/` layout; give the user the one-line Pages enable command; and, after the user's push, confirm the page URL loads.

Then draft a short **`Current plan` block for the project `CLAUDE.md`**: current phase, authoritative governance paths, role of execution sessions, context to load, permissible edit scope, required tests, reporting format, and escalation route. Show it to the user and write it only on approval; replace, never stack, an earlier block, and remove it when the plan closes.

## Phase 7 — Package and optionally execute tasks

For each task whose dependencies are satisfied:

1. Invoke `task-engineering-protocol.md` with the locked task card, its spec references, upstream artifacts, assigned persona, inputs, output contract, claims, tools, skills, review gate, and acceptance tests.
2. Tell task engineering that the parent goal and adjudicated decisions are `FIXED`. It may clarify execution detail but may not redesign the goal or task graph.
3. If a task exceeds one context window, has multiple irreversible checkpoints, or mixes logically sequential write sets, split it into numbered sequential chunks. Each chunk becomes its own one-task handoff with explicit predecessor output and stop condition.
4. Launch only the current ready wave. Each agent registers its own session and exact claims. Review/integration tasks remain distinct from production tasks.
5. Require every handoff to carry the current locked spec version, a spec-delta reporting trigger, the plan integrator recipient, and a stop/continue boundary. Create `CHANGELOG.md` before Wave 1 with the integrator as sole writer.
6. When a lane reports a delta, load `planning-spec-reconciliation-protocol.md`; pause only affected work, triage whether the defect is in implementation/plan or the spec, and obtain user approval before any substantive spec change.
7. After a wave, collect outputs, run its declared reviews, process all reported deltas, update task states/spec and plan versions where approved, and release the next wave. Never launch all waves at once.
8. Every handoff fixes the **return report** each agent sends back: changed files, verification results, failures, blockers, and unresolved decisions. Never mark a task `complete` without its required verification evidence.

If mode is `PLAN_ONLY`, output the task-engineering queue and stop before generating launch actions.

## Phase 8 — Reconcile the main spec after execution

Load and execute `planning-spec-reconciliation-protocol.md` after execution completes, stops partially, or aborts.

- Compare every final `D/R/A/C/N` item with delivered artifacts and the evidence required by its acceptance contract.
- Produce `Spec-Reconciliation.md` plus the complete `CHANGELOG.md`.
- Report every approved change from the original spec, rejected/deferred proposal, unmet or unverified requirement, and change enacted without approval.
- Never revise the spec retroactively merely to make the implementation pass.
- If reconciliation exposes unmet locked requirements, route them back to implementation correction or a new user-approved spec delta; do not mark execution fully closed.
- Run the final traceability review (PDF §7): each final deliverable traced back through its generating tasks, `RESOURCES.md` inputs and approved decisions, and the documented pipeline rerun to reproduce the final outputs.

## Readiness audit

Before reporting the plan ready, verify all of the following:

- Every required Stage-1 field is approved and its spec review resolved; every open item is explicit.
- Every deliverable is linked to resources in `RESOURCES.md` or carries an explicit `UNRESOLVED` gap.
- Every judgment that cannot be checked automatically is a named researcher gate.
- Every requirement and acceptance test has at least one producing task and one verifying task or review.
- Every task input is pre-existing or produced by a predecessor.
- No output has two writers in the same wave.
- The dependency graph is acyclic and each wave contains only ready tasks.
- Shared surfaces have one integrator and a stated merge order.
- Skills and tools named by task cards actually exist or are marked as prerequisites.
- Destructive, costly, external, or sensitive actions carry approval gates and rollback/containment instructions.
- The critical path and optional tasks are distinguishable.
- Every task has a spec-delta reporting path and the integrator is the sole writer of the delta log.
- Post-execution closure requires a delivered-result-versus-spec reconciliation, not only task completion.
- The user can tell what will exist at the end without reading the implementation sequence.

## Common failure modes

- **Premature implementation:** tool or architecture choices appear in `SPEC.md`. Remove them unless they are user-mandated properties of the final result.
- **Decorative multi-agentism:** several agents touch the same files or wait on each other. Collapse them or create disjoint sections and an integrator.
- **Coverage by assertion:** the plan says a requirement is covered but no task output or test proves it. Add explicit producer and verifier links.
- **Reviewer contamination:** the reviewer is told what the mapper worries about. Re-run with raw artifacts and a neutral prompt.
- **Infinite adjudication:** minor preferences keep reopening locked goals. Ask only when alternatives materially change outcome, cost, risk, or user-facing behavior.
- **Task-engineering drift:** downstream prompts re-litigate the goal. Mark locked decisions `FIXED` and route real contradictions back to Stage 5.
- **Chat-only spec drift:** a lane adapts after mentioning a change informally. Require a structured delta report and integrator disposition before affected work resumes.
- **Retroactive spec laundering:** the final spec is rewritten to match what happened. Preserve version history and classify unapproved divergence explicitly.

## Worked example

For “build a lab intake portal,” Stage 1 specifies the users, submitted records, confirmation behavior, privacy limits, accessibility, error handling, administrative outputs, and acceptance tests—without choosing a framework; the spec reviewer flags that no deliverable answers who may delete records. Stage 2 finds an existing user directory and an old intake spreadsheet, links the directory to the access requirements, and classifies the spreadsheet as a migration source. Stage 3 maps the requirements into schema, interface, backend, validation, deployment, documentation, and end-to-end test tasks. Stage 4 catches that two agents are assigned to the same schema file. Stage 5 fixes the collision mechanically and emits waves with one schema owner, parallel UI/API workers after the schema locks, and a final integration reviewer. Stage 6 locks spec, resources and plan together. Task engineering then packages each ready task into isolated handoffs.
