---
name: planning-adjudication-protocol
description: Reconcile an approved goal spec, resource map, technical plan, and adversarial review into a final execution plan (`PLAN.md`). Use after plan review to accept, reject, or modify findings; interview the user only on substantive or non-obvious tradeoffs; validate a collision-free dependency DAG; and produce launch-ready multi-agent waves and task-engineering handoffs.
audience: public
version: 0.3
---

# Planning Adjudication Protocol

Turn review findings into decisions and a corrected, executable plan. Resolve what follows clearly from the approved spec; bring the user only the decisions that require their authority or preference.

Composes with `planning-output-specification-protocol.md`, `planning-implementation-map-protocol.md`, `planning-adversarial-review-protocol.md`, `planning-protocol.md`, `planning-spec-reconciliation-protocol.md`, and `task-engineering-protocol.md`.

Version: 0.3 (first public release; earlier versions are not shipped in this repo).

## Required inputs

- approved, resource-linked `SPEC.md` and `RESOURCES.md`;
- `Plan-Draft.md` and all task cards;
- `Plan-Review.md` from an independent reviewer;
- relevant project/coordination state needed to validate claims and capacity.

Do not adjudicate from summaries when the source artifacts are available. Read all four artifacts and preserve their IDs. `PLAN.md` is not executable until the user locks it together with `SPEC.md` and `RESOURCES.md` (Stage 6 of `planning-protocol.md`).

## Output

Produce `PLAN.md` as the canonical post-review plan. It contains:

- goal/spec version and fixed decisions;
- disposition of every review finding;
- updated requirement traceability;
- corrected tasks and DAG;
- dependency-safe parallel waves;
- exact ownership and write claims;
- integration and independent-review gates;
- launch manifest and task-engineering queue;
- execution-time spec-delta reporting routes, stop/continue boundaries, and the sole delta-log owner;
- blocked decisions, approval gates, risks, and rollback paths.

Keep the original `Plan-Draft.md` and `Plan-Review.md` unchanged for provenance.

## Disposition states

- `ACCEPT`: adopt the reviewer's patch as written.
- `ACCEPT-MODIFIED`: adopt the finding with a different minimal patch.
- `REJECT`: evidence shows no defect or the patch conflicts with the approved spec.
- `USER-DECISION`: two or more materially different valid choices remain.
- `RETURN-TO-SPEC`: the issue exposes a genuine Stage-1 ambiguity or contradiction.
- `RETURN-TO-RESOURCES`: the issue exposes a missing or wrong resource link; return to Stage 2 (`planning-resource-map-protocol.md`).
- `DEFER`: non-critical optional improvement is recorded with a blocked/deferred task.

Every disposition records evidence and affected IDs. Silence is not a disposition.

## Universal rules

1. **Adjudicate mechanically when the answer is entailed.** Fix missing coverage, impossible inputs, cycles, duplicate writers, broken references, and unambiguous project-convention violations without burdening the user.
2. **Interview on authority, preference, or material tradeoff.** Ask when choices change the promised result, cost, timeline, risk tolerance, ownership burden, privacy posture, or irreversible external state.
3. **Do not average incompatible options.** When two designs reflect different priorities, present the fork and consequence; do not invent a hybrid merely to avoid asking.
4. **Preserve accepted strengths.** Carry forward the review's named strengths and ensure fixes do not regress them.
5. **One canonical plan.** Apply accepted changes to `PLAN.md`; do not force executors to reconcile plan plus review themselves.
6. **Revalidate after every structural change.** A patch can create new cycles, collisions, orphaned requirements, or integration bottlenecks.
7. **Plan for many agents safely.** Maximize useful concurrency subject to ready inputs, disjoint claims, integration capacity, and harness slot limits. Reserve reviewer/integrator capacity.
8. **Blocked means not launchable.** A task depending on an unresolved decision or missing input cannot appear in a ready wave.
9. **Prepare for execution feedback.** The final plan must route every spec conflict or discovered change through `planning-spec-reconciliation-protocol.md`; no lane may adapt the locked goal silently.

## Phase 0 — Normalize findings

Build a disposition table:

| Finding | Severity/type | Spec/task evidence | Proposed patch | Conflicts with | Initial disposition | User needed? |
|---|---|---|---|---|---|---|

Merge duplicate findings while retaining all original IDs. Separate compound findings when parts require different dispositions. Identify conflicts among proposed patches before applying any.

## Phase 1 — Clear adjudications

Resolve a finding without user input only when all are true:

- the defect is evidenced in the artifacts or project state;
- the approved spec implies the desired correction;
- only one practical minimal correction preserves existing fixed decisions; and
- the correction does not introduce a new material cost, risk, or user-facing choice.

Examples suitable for direct adjudication:

- add a missing verifier for an existing `A-*` test;
- correct a task dependency on the task that actually produces its input;
- assign a shared manifest to one integrator instead of two parallel writers;
- merge duplicate discovery tasks using the same sources and outputs;
- add a smoke check already required by existing project policy.

Record why each direct decision was clear.

## Phase 2 — User decision interview

For every remaining `USER-DECISION`, `RETURN-TO-SPEC` or `RETURN-TO-RESOURCES`, ask in batches of one to three independent decisions. Use this format:

```markdown
### Decision U-### — <question>
Why this surfaced: <finding/spec IDs>
What changes: <affected deliverables/tasks/waves>

1. <Option A> — outcome, cost/time, risk, ownership consequence.
2. <Option B> — outcome, cost/time, risk, ownership consequence.
3. <Option C, only if genuinely distinct> — consequence.

Recommendation: <option and evidence-based reason, or "none—value choice">
Default if deferred: <blocked tasks or reversible conservative posture>
```

Do not ask the user to choose implementation trivia governed by repository convention. Do not conceal a substantive outcome choice behind technical jargon.

If a decision reopens the final output itself, return to `planning-output-specification-protocol.md`, update and re-approve the spec (and its resource links if affected), then regenerate affected planning and review sections. Do not adjudicate around a changed goal.

## Phase 3 — Build the canonical execution DAG

Apply accepted findings and user decisions to a clean plan:

1. Update decisions and stable task cards without renumbering surviving tasks.
2. Add new task IDs for new work; mark removed tasks `superseded` with `Superseded-by: <ID>` rather than erasing provenance.
3. Rebuild requirement-to-producer-to-verifier coverage.
4. Recompute dependencies and topological order.
5. Recompute the critical path.
6. Assign waves from currently ready tasks.
7. Run write-collision and shared-interface checks inside each wave.
8. Add an integration task wherever multiple outputs converge.
9. Add an independent review task for high-risk or acceptance-critical outputs.

### Collision rules

- A filesystem path, database object, document section, design frame, remote resource, or external conversation has one writer per wave.
- Parent/child paths conflict unless ownership is explicitly sectioned and the storage mechanism safely supports concurrent writes.
- Generated files conflict with their generators' source/config ownership if one task may regenerate while another edits output.
- Shared indexes, manifests, schemas, dependency locks, and ledgers default to a single integrator.
- Reviewers are read-only; the parent/integrator applies accepted fixes.

### Dependency rules

- Every input names a pre-existing source or predecessor output.
- A wave begins only after all required predecessor reviews pass, not merely after files appear.
- Tasks with unresolved approval gates remain blocked even if technical inputs exist.
- Optional tasks do not block the critical path unless the user promotes them.

## Phase 4 — Create the multi-agent launch manifest

For every lane, record:

| Lane | Wave | Task/chunk | Persona/role | Working directory | Inputs | Exact write claim | Output handoff | Researcher gates | Review owner | Slot/release condition |
|---|---|---|---|---|---|---|---|---|---|---|

When AI OS is present, each lane must also include:

- a two-word ALL-CAPS tab label of at most 10 characters;
- session ID convention and project slug;
- `coord/SPEC.md` startup/heartbeat/mailbox/control/closeout instructions;
- recipient for questions and integration handoffs;
- current locked spec version and recipient for spec-delta reports;
- a task-specific spec-change trigger plus exact stop/continue boundary;
- a claim narrow enough to avoid overlap;
- a no-write-until-dependencies-ready instruction.

Choose the largest **safe useful** fan-out, not the largest imaginable count. Use these priorities:

1. Fill independent critical-path work first.
2. Fill required off-critical work whose outputs will soon be consumed.
3. Reserve one lane/slot for integration or adversarial review when needed.
4. Queue optional work rather than displacing critical review capacity.
5. If slot capacity is lower than a wave's lanes, schedule deterministic batches without changing dependencies.

As a tie-breaker, group related ready tasks that share inputs into one lane when that cuts duplicated context loading or file conflicts and the combined work still fits one context window; keep tasks with disjoint inputs in separate lanes.

## Phase 5 — Task-engineering queue

For each ready task, create a queue entry for `task-engineering-protocol.md` containing:

- task ID and fixed spec/decision references;
- exact input artifacts and required state;
- exact output contract and write claim;
- assigned persona/role, tools, and skills;
- dependencies already satisfied and evidence;
- required self-check, independent review, and acceptance IDs;
- rollback/containment, approval gates, and researcher gates;
- the fixed return report (changed files, verification results, failures, blockers, unresolved decisions);
- current locked spec version, spec-delta triggers, integrator recipient, and affected-work stop/continue rule;
- chunking trigger.

Task engineering may split a card into sequential chunks when:

- it spans more than one meaningful checkpoint or likely context window;
- later work depends on validating earlier outputs;
- it crosses write scopes that should be claimed separately;
- it contains an irreversible/costly action after a reversible build or smoke phase.

Each chunk must remain one task with one output contract. Chunks execute sequentially; independent sibling tasks remain parallel.

## `PLAN.md` template

Use `_assets/planning-templates/PLAN.md` (format contract `_assets/plan-viewer/FORMAT.md` §5; `plan_viewer.py --check` enforces it). It keeps the earlier sections (header, fixed decisions, finding disposition ledger, requirement traceability, task graph, parallel waves, launch manifest, task-engineering queue, spec-change control, risks, blocked items, readiness audit, user authorization).

What it adds: a `Deadline:` header line, a `## Lanes` table (lane `researcher` reserved for the human decision-maker), a `Target` column on waves, task-graph columns `Lane`, `Waves`, `Soft`, `Resources` and `Delivers`, and a `## Task cards` section holding every card (`### T-###`, with `#### Decision points`).

## Final readiness audit

Mark `READY` only if:

- all critical/high findings are resolved;
- every substantive user decision is answered or its tasks are blocked;
- every must-have spec ID has a producer and verifier;
- the DAG is acyclic and inputs resolve;
- concurrent write claims are disjoint;
- shared surfaces have one integrator;
- review and integration capacity is reserved;
- tools/skills/personas exist or prerequisites are explicit;
- approval, cost, sensitivity, and rollback gates are assigned;
- task-engineering packets preserve all fixed decisions;
- every researcher gate on a card is carried into its queue entry, task graph row and launch manifest row;
- every lane can report a spec delta without editing the spec, and the plan names the sole delta-log writer;
- post-execution `Spec-Reconciliation.md` is a required closure artifact;
- execution authorization matches the user's request.

## Common failure modes

- **Rubber-stamp adjudication:** every reviewer finding is accepted. Re-evaluate evidence and goal preservation.
- **User-question dumping:** mechanical defects become a long interview. Apply the clear-decision rule.
- **Invisible rejection:** findings disappear without a reason. Record every disposition.
- **Plan/review dual authority:** agents must read both and choose. Consolidate into `PLAN.md`.
- **Overfilled slots:** all agents build and nobody can integrate or review. Reserve capacity.
- **Shared integrator bottleneck:** every minor output routes through one agent. Centralize only shared surfaces; keep component ownership disjoint.
- **Chunk explosion:** simple tasks become many handoffs. Split only on the stated chunking triggers.
- **Unrouted execution learning:** agents discover the spec must change but have only a generic question channel. Add structured delta reporting, a named integrator, version propagation, and required final reconciliation.

## Worked example

The reviewer of a data portal plan raises eight findings. Four are direct fixes: a missing acceptance verifier, a reversed dependency, duplicate schema discovery, and two writers on one registry. Two low-value optimizations are deferred. One storage-retention choice changes user policy and is interviewed. One reviewer proposal is rejected because it violates the locked offline-use constraint. The final plan has three build lanes after a schema gate, one registry integrator, a separate end-to-end reviewer, and sequential deploy chunks separated by a smoke-test approval gate.
