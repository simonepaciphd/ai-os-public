---
name: planning-implementation-map-protocol
description: Convert an approved, resource-linked output specification into a traceable technical and implementation task graph. Use after `SPEC.md` and `RESOURCES.md` are approved to define task cards with exact inputs, outputs, tools, skills, owners, dependencies, write scopes, tests, reviews, rollback, and safe parallel-agent waves—without beginning implementation.
audience: public
version: 0.4
---

# Planning Implementation-Map Protocol

Map an approved definition of “done” into an executable, reviewable DAG. Produce `Plan-Draft.md` and task cards; do not perform the tasks.

Composes with `planning-output-specification-protocol.md`, upstream `planning-resource-map-protocol.md`, `planning-protocol.md`, downstream `planning-adversarial-review-protocol.md`, and execution feedback through `planning-spec-reconciliation-protocol.md`.

Version: 0.4 (first public release; earlier versions are not shipped in this repo).

## Required inputs

- An `APPROVED` resource-linked `SPEC.md` and its `RESOURCES.md`.
- The project root or declared working environment.
- Authoritative architecture, policy, interface, ledger, and coordination files that constrain implementation.
- Known resource limits: harness slots, time/cost ceilings, required platforms, and approval boundaries.

Stop if the spec or resource map is unapproved. Return missing outcome decisions to Stage 1 and missing resources to Stage 2 rather than burying them as technical assumptions.

## Outputs

1. `Plan-Draft.md`—context inventory, decisions, traceability matrix, DAG, waves, integration strategy, risks, and validation plan.
2. Task cards embedded in the plan or stored as `Task-Cards/T-###.md`.
3. A proposed multi-agent topology, explicitly provisional until adversarial review and adjudication.

## Universal rules

1. **Trace every task to the goal.** A task without at least one `G/D/R/A/C/N` reference is unjustified; a requirement without a producer and verifier is uncovered.
2. **Inspect reality.** Read the relevant repository/project structure, existing interfaces, tests, skills, personas, and deployment conventions before selecting an approach.
3. **Separate decisions from tasks.** Record architecture or process choices with alternatives and reasons; tasks implement chosen decisions.
4. **Concrete contracts.** Each task names exact inputs, outputs, write scope, tools, skills, review method, and done condition.
5. **DAG, not prose sequence.** Dependencies must mean that a task cannot start correctly without a predecessor's output. Do not add dependencies merely to impose a preferred order.
6. **Parallelize by independence.** Default to aggressive fan-out across disjoint write scopes and available inputs. Collapse tasks that require constant coordination or edit the same surface.
7. **Review is work.** Verification, integration, documentation, migration, rollback rehearsal, and user acceptance are explicit tasks or gates—not final bullets appended to build tasks.
8. **No implementation.** Reads and non-mutating diagnostics are allowed; edits, deployments, external messages, and irreversible actions wait for the execution phase.
9. **Expose uncertainty.** Mark tasks `blocked` with reason `BLOCKED-SPEC` or `BLOCKED-INPUT`, or label them `SPIKE` or `OPTIONAL` (type/priority, not status); never present unknown feasibility as settled.
10. **Design the feedback path.** Every task card must say when execution evidence becomes a spec-delta report, where to send it, what work pauses, and what can safely continue.

## Phase 0 — Context and interface inventory

Start from `RESOURCES.md`; do not re-run asset discovery. Inspect further only the implementation surfaces it does not cover. Record:

- existing deliverables and reusable assets;
- repository/project structure and ownership boundaries;
- current data/file/API/interface contracts;
- test, build, deploy, logging, and rollback mechanisms;
- available personas, skills, tools, connectors, and credentials by name (never copy secret values);
- live coordination claims and resource capacity when AI OS is present;
- technical debt or constraints likely to affect the goal.

Classify every needed input as `EXISTS`, `TO-BUILD`, `EXTERNAL`, `USER-SUPPLIED`, or `UNKNOWN`, citing its `RS-*` ID where `RESOURCES.md` lists it. An input `RESOURCES.md` marks `UNRESOLVED` makes its tasks `blocked`.

## Phase 1 — Choose implementation posture

For each non-trivial decision, record:

| Decision ID | Question | Chosen option | Alternatives rejected | Reason | Spec IDs | Confidence | Reversible? |
|---|---|---|---|---|---|---|---|

Make mechanical choices when existing project conventions clearly govern. Interview the user only when options materially change cost, risk, ongoing ownership, user-facing behavior, or a locked preference. If feasibility is genuinely unknown, create a bounded `SPIKE` task whose output is evidence and a decision recommendation.

## Phase 2 — Build requirement traceability

Create a coverage table before task decomposition:

| Spec ID | Required result/test | Producer task(s) | Verifier/reviewer task(s) | Status |
|---|---|---|---|---|

Coverage rules:

- Every `D-*` and `R-*` has at least one producer.
- Every `A-*` has a named verification action and evidence artifact.
- Every `C-*` is enforced by a task, test, gate, or documented operating boundary.
- Every `N-*` has a guard against accidental scope creep when it is plausibly adjacent.
- Cross-cutting requirements (security, accessibility, provenance, observability, compatibility) map across all affected tasks, not to a single decorative “check” task.

## Phase 3 — Decompose task cards

Use the smallest task that can be independently owned, reviewed, and handed off without repeated synchronization. Do not split merely by file count; split by contract and write ownership.

Each task card must use the card schema in `_assets/planning-templates/PLAN.md` (`## Task cards`; format contract `_assets/plan-viewer/FORMAT.md` §5). It carries the fields of the earlier inline schema (status, type, priority, spec and decision refs; objective; inputs; outputs; execution resources; dependencies with researcher gates; ownership and collision control; procedure boundary; spec-change reporting; verification and review; return report; done condition; chunking trigger), headed `### T-### — <name>` with `####` sub-sections so the cards can sit inside `PLAN.md`.

What the template adds: a `#### Decision points` section listing each choice the task involves as `DP-###` with required `Default:` and `Recommendation:` lines (`planning-decision-points-protocol.md`), and a `Generated-from: DP-###` line used only on classifier-inserted gate cards.

### Procedural verification design

After the cards are drafted, write operational checks for every task, not generic requests to "check correctness": schema and unique-key assertions, row-count and merge-coverage checks, sample-consistency tests, exact output-path checks, numerical comparisons, model-to-figure reconciliation, full pipeline reruns. Any methodological judgment that cannot be automated becomes a named entry under the card's `Researcher gates`.

`verified` means the task's checks passed with evidence; `complete` means its outputs were also integrated. A task never reaches `complete` without its verification evidence.

## Phase 4 — Construct the DAG and parallel waves

1. Draw edges only from real input/output dependencies.
2. Topologically sort the graph; reject cycles.
3. Mark the critical path and tasks with slack.
4. Group ready tasks into waves, then run a collision check within each wave.
5. Assign a single integration owner for every shared interface or combined artifact.
6. Place independent verification after the outputs it reviews; do not let authors self-certify high-risk outputs.

For each wave, record:

| Wave | Task | Agent lane | Dependencies satisfied by | Write claim | Output handoff | Review gate |
|---|---|---|---|---|---|---|

### Parallelism decision rules

- **Split** when tasks have stable input contracts, disjoint write claims, and independently reviewable outputs.
- **Sequence** when a consumer needs a predecessor's output, an architecture decision is still open, or two tasks modify the same interface definition.
- **Use an integrator** when several agents produce components that meet at one shared surface.
- **Do not spawn** a lane whose coordination cost exceeds its independent work, whose only output is duplicative commentary, or whose inputs are not ready.
- **Reserve capacity** for at least one reviewer/integrator when the harness has a hard slot budget; production fan-out that consumes every slot defeats review.

### Plan page (rendered at Stage 5, not here)

After adjudication, the plan page `Plan-Visual.html` is built by `_assets/plan-viewer/plan_viewer.py` from the planning files; see the Stage 5 close in `planning-protocol.md` Phase 5 (decision points, labels pass, build with `--check`).

## Phase 5 — Risk, approvals, and execution packaging

Create a risk register:

| Risk | Trigger | Likelihood/impact | Prevention | Detection | Containment/rollback | Owner/task |

Explicitly gate:

- destructive or hard-to-recover actions;
- external communications, purchases, deployments, and publication;
- costly/cloud/long-running work (including required small-sample smoke runs);
- sensitive-data or credential use;
- changes to shared infrastructure or global configuration;
- substantive choices outside the active persona's authority.

Define which task cards are ready for `task-engineering-protocol.md`, which are blocked, and what evidence unblocks them.

## Structural completion gate

`Plan-Draft.md` is reviewable only if:

- coverage has no unexplained missing `D/R/A/C` IDs;
- the DAG is acyclic;
- each task has inputs, outputs, tools, skills, review, and done condition;
- each task has operational verification checks, and every non-automatable judgment is a researcher gate;
- every task input traces to an `RS-*` resource, a predecessor output, or is classed `USER-SUPPLIED`/`EXTERNAL`;
- every final `D-*` has a pipeline/reproduction task whose output is the documented pipeline the final traceability review reruns;
- each wave has collision-free write claims;
- every shared surface has one integrator;
- every task has a spec-delta reporting contract and the execution plan assigns one delta-log writer;
- unknowns are represented as blockers or spikes;
- no task has begun implementation.

## Common failure modes

- **Requirements dumped into one omnibus task:** split by output contract and review boundary.
- **Tool-first planning:** architecture follows a favorite framework rather than the spec and project conventions. Re-run context inventory and decision table.
- **Fake dependencies:** tasks are serialized because of narrative order. Remove edges that do not carry a required input.
- **Hidden shared write:** “separate” agents both touch a manifest, schema, index, or generated output. Assign one owner or an integrator.
- **Review as vibes:** “review quality” names neither evidence nor acceptance test. Create a verifier task with exact artifacts and checks.
- **Unbounded spike:** feasibility exploration has no question, timebox, or output. Rewrite it as an evidence-producing decision task.
- **No execution feedback path:** a lane must improvise when reality conflicts with the spec. Add task-specific report triggers, an integrator route, and a narrow stop/continue boundary.

## Worked example

An approved “searchable archive” spec maps to separate tasks for source inventory, canonical metadata schema, ingestion, search interface, access controls, migration, documentation, and acceptance testing. Schema locks before ingestion and interface work. Ingestion and interface can then run in parallel on disjoint paths; a migration agent consumes the schema; an integrator owns the shared manifest; a reviewer tests requirement coverage and end-to-end retrieval. The plan does not start any of that work.
