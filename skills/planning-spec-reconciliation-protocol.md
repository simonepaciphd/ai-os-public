---
name: planning-spec-reconciliation-protocol
description: Detect, report, adjudicate, and reconcile changes to a locked goal specification during and after execution. Use as the execution-feedback stage of `/planning` whenever implementation evidence exposes a needed clarification, constraint, scope change, acceptance-test change, or actual deviation. Produces an append-only spec-delta log, pauses only affected work, requires user approval for substantive spec changes, versions the main spec, remaps impacted tasks, and performs a final delivered-result-versus-spec audit.
audience: public
version: 0.3
---

# Planning Spec-Reconciliation Protocol

Keep the locked goal specification authoritative while reality feeds back during execution. Report changes instead of silently editing the spec or retroactively redefining success.

Composes with `planning-output-specification-protocol.md`, `planning-implementation-map-protocol.md`, `planning-adversarial-review-protocol.md`, `planning-adjudication-protocol.md`, `planning-protocol.md`, and `task-engineering-protocol.md`.

Version: 0.3 (first public release; earlier versions are not shipped in this repo).

**Scope.** This protocol governs the spec from the baseline lock (Stage 6 of `planning-protocol.md`, where `SPEC.md`, `RESOURCES.md` and `PLAN.md` are locked together). Before that lock, spec edits need only the user's approval and a row in the spec's change history.

## Required inputs

- the current locked `SPEC.md`, including version and lock record;
- the canonical `PLAN.md` and task cards;
- task outputs, test/review evidence, agent handoffs, and execution status;
- all previously accepted or rejected spec-delta decisions.

## Outputs

1. `CHANGELOG.md` — append-only record of every proposed, rejected, accepted, superseded, or accidentally enacted change.
2. Versioned goal specs — preserve each locked version; never overwrite the only copy of the prior contract.
3. Updated affected task cards, traceability, DAG, and waves after an approved change.
4. `Spec-Reconciliation.md` — post-execution comparison of delivered reality against the final locked spec and all prior versions/deltas.

If the project has `asset-registry.csv` and `interaction-log.csv`, register the delta/reconciliation artifacts and log each adjudication session under the project's existing schemas. Do not create project ledgers here; project binding belongs to setup/retrofit.

## Delta types and states

Types:

- `CLARIFICATION` — wording or boundary needed to execute an existing intent.
- `DISCOVERED-CONSTRAINT` — reality adds a cost, policy, interface, or feasibility boundary.
- `SCOPE-ADD` — proposed new required output, behavior, audience, or case.
- `SCOPE-DROP` — proposed removal or weakening of a locked requirement.
- `ACCEPTANCE-CHANGE` — proposed change to how success is tested or approved.
- `IMPLEMENTATION-DEVIATION` — delivered or in-progress work differs from the spec without an approved spec change.
- `ASSUMPTION-RESOLUTION` — an `OPEN` or `INFERRED` item receives evidence or user resolution.

States:

`REPORTED | TRIAGED | CLARIFIED | RETURN-TO-MAPPING | USER-DECISION | ACCEPTED | REJECTED | SUPERSEDED | FIX-IMPLEMENTATION | ENACTED-UNAPPROVED | VERIFIED-CLOSED`.

## Universal rules

1. **The spec is normative.** Implementation convenience, sunk cost, or completed work does not change the goal.
2. **Report before adapting.** When execution encounters a conflict with the locked spec, stop the affected atomic step before committing the conflicting change and report a delta.
3. **Pause narrowly.** Block only tasks whose inputs, outputs, acceptance tests, or decisions depend on the delta. Independent work may continue.
4. **One reporter, one integrator.** Task agents send delta reports to the plan integrator; only the integrator appends to `CHANGELOG.md` and applies approved spec/plan updates.
5. **No silent spec edits.** Task agents, reviewers, and integrators may propose; a user-locked spec changes only through an explicit disposition.
6. **User owns substantive changes.** Any `SCOPE-ADD`, `SCOPE-DROP`, `ACCEPTANCE-CHANGE`, changed user-facing behavior, changed risk/privacy posture, or changed non-goal requires explicit user approval.
7. **Clarifications may be mechanical only when uniquely entailed.** If a clarification changes possible outputs or acceptance, treat it as substantive and ask.
8. **Version, do not erase.** Preserve the prior locked spec, create a new version, record exactly which IDs changed, and link the approving decision.
9. **Replan the affected subgraph.** An accepted delta does not authorize direct improvisation. Re-run coverage, dependency, collision, review, and task-engineering checks for impacted tasks.
10. **Never launder drift.** Post-execution reconciliation must label unapproved divergence as divergence; do not revise the spec merely to match what was built.

## Phase 0 — Install the execution feedback channel

Before launching any task, ensure every task-engineering handoff includes:

- current locked spec version and relevant stable IDs;
- a list of fixed decisions the task may not reopen;
- concrete triggers for a spec-delta report;
- the integrator/mailbox recipient;
- which work must stop and which may continue after reporting;
- a prohibition on editing `SPEC.md` or `CHANGELOG.md` directly.

Create `CHANGELOG.md` before Wave 1, even if initially empty. Assign it one writer: the planning integrator.

## Phase 1 — Report a delta during execution

A task agent must report when any of these occurs:

- a locked requirement appears impossible, unsafe, or materially costlier than planned;
- an unspecified case requires a user-facing or substantive choice;
- the task's correct output would differ from its spec-linked contract;
- acceptance evidence cannot be produced as specified;
- a new constraint, dependency, audience, input, or downstream consumer appears;
- requested implementation work would add scope not represented by a spec ID;
- work already performed has diverged from the spec;
- an `OPEN` or `INFERRED` spec item becomes resolvable with evidence.

Use this report packet:

```markdown
## Spec-delta report
- Reporter/session/task: <lane + T-ID>
- Current spec version: <version + lock timestamp>
- Proposed delta ID: <temporary lane-local ID; integrator assigns SD-###>
- Type: <delta type>
- Affected spec IDs: <G/D/R/A/C/N/Q IDs>
- Trigger/evidence: <observed fact, output, test, path, or source>
- Current contract: <what the locked spec requires>
- Observed or proposed change: <precise difference>
- Why execution cannot simply comply: <reason or "it can—this is an implementation defect">
- Consequence if unchanged: <outcome, risk, cost, delay>
- Affected tasks/waves/claims: <IDs>
- Work paused: <exact step/output>
- Work safe to continue: <IDs or none>
- Options: <fix implementation; change spec; bounded alternative>
- Recommendation: <option + reason, or no recommendation>
```

Send the packet to the integrator through the execution plan's handoff channel. Do not proceed through the conflicting boundary.

## Phase 2 — Triage against the locked spec

The integrator assigns `SD-###`, appends the packet, and selects one preliminary route:

1. **`FIX-IMPLEMENTATION`** — the spec is clear and feasible; return work to the task owner with no spec change.
2. **`CLARIFICATION`** — wording can be clarified without changing any valid output, priority, or acceptance condition. Record the clarification and obtain user confirmation at the next checkpoint unless urgent.
3. **`USER-DECISION`** — alternatives materially change the result, scope, acceptance, cost/risk, or ownership.
4. **`RETURN-TO-MAPPING`** — the spec stands but the task graph or implementation decision is wrong; remap the affected subgraph.
5. **`ENACTED-UNAPPROVED`** — work has already diverged. Contain the divergence, preserve evidence, and ask whether to revert/fix or consider a spec change.

Before asking the user, identify whether the reported issue is really a specification change or merely a plan/task defect. Do not burden the user with engineering mistakes that can be corrected while preserving the spec.

## Phase 3 — Adjudicate a substantive delta

Present one to three independent deltas per interview:

```markdown
### SD-### — <decision question>
Current locked requirement: <IDs + concise text>
Execution evidence: <what changed or was discovered>
Affected work: <tasks, outputs, timeline, cost/risk>

1. Keep the spec — <implementation fix and consequence>.
2. Change the spec — <exact replacement/addition/removal and consequence>.
3. <Only if genuinely distinct> — <bounded alternative>.

Recommendation: <evidence-based option or "none—value choice">
```

Record the user's answer verbatim enough to preserve the decision. `SCOPE-DROP` and weakened acceptance criteria require especially explicit approval; never infer them from schedule pressure.

## Phase 4 — Version and propagate an accepted change

For each accepted delta:

1. Preserve the prior locked file as `SPEC-v<old>.md` or the project's equivalent immutable snapshot, under `planning/archive/` (v0.7 layout; plans started earlier keep their snapshot folder), and add it to `planning/archive/README.md`.
2. Create the next version with the same stable IDs. Add IDs for new requirements; mark removed items `SUPERSEDED-BY:<SD-ID>` rather than deleting history.
3. Add a change-log row naming the delta, changed IDs, approver, timestamp, reason, and affected artifacts.
4. Re-lock `SPEC.md`, `RESOURCES.md` and `PLAN.md` together explicitly with the user, and refresh the project `CLAUDE.md` `Current plan` block if its phase or paths changed. If the project keeps a baseline lock record, write the new one at the top of `planning/` and move the superseded one to `planning/archive/records/`. Re-run the labels pass, then rebuild the page into `planning/page/Plan-Visual.html` (`planning-protocol.md` Phase 5, step 3).
5. Re-run requirement coverage for affected IDs.
6. Re-run technical mapping, adversarial review, and adjudication only for the affected subgraph unless the delta changes the whole architecture.
7. Supersede affected task cards and task-engineering packets; do not mutate in-progress prompts invisibly.
8. Recompute ready tasks, waves, claims, critical path, approvals, and review gates.
9. Update `SPEC.md`, `RESOURCES.md` and `PLAN.md` together where the delta touches them; commit them with `Plan-Labels.json` and the rebuilt page in one commit in the project repo naming the `SD-###`. In a repo with Pages, pushing that commit (the user's sign-off) republishes the page.
10. Notify every affected lane of the new spec and plan versions before resuming.

Rejected deltas remain in the log with their reason; return affected work to implementation correction or keep it blocked.

## Phase 5 — Reconcile after execution

After all planned work stops—whether completed, partially completed, or aborted—compare delivered artifacts and evidence to the final locked spec. Also inspect all delta reports to detect changes that were proposed, rejected, or enacted without approval.

For every `D/R/A/C/N` ID, assign:

- `MET` — delivered and supported by the required evidence;
- `MET-AS-CHANGED` — delivered under an explicitly approved later spec version;
- `NOT-MET` — delivered result violates or omits the requirement;
- `UNVERIFIED` — evidence is insufficient;
- `NOT-APPLICABLE` — only when the locked spec itself says so;
- `ENACTED-UNAPPROVED` — implementation changed the contract without approval.

Do not count a self-report as acceptance evidence when the spec requires an independent review or user test.

Then run the **final traceability review**: for each final deliverable, trace the generating tasks, the `RESOURCES.md` inputs they consumed, and the approved methodological decisions behind them; rerun the documented pipeline and confirm it reproduces the final outputs. A deliverable that cannot be traced or reproduced is `UNVERIFIED`.

## `CHANGELOG.md` template

```markdown
# Changelog (spec deltas): <goal>

Current locked spec: <path/version/timestamp>
Integrator/sole writer: <lane/session>

| Delta | Reported by/task | Type | Affected spec IDs | Evidence | State | User decision | Spec version | Plan/task impact |
|---|---|---|---|---|---|---|---|---|

## Delta records
<Full report, triage, decision, propagation, and closure evidence per SD-###.>
```

## `Spec-Reconciliation.md` template

```markdown
# Spec Reconciliation: <goal>

Execution state: complete | partial | aborted
Initial locked spec: <version/path>
Final locked spec: <version/path>
Execution plan/version: <path>
Delta log: <path>

## Executive report-back
- Approved spec changes: <count + IDs>
- Rejected/deferred changes: <count + IDs>
- Unapproved enacted changes: <count + IDs>
- Requirements met / changed / not met / unverified: <counts>
- User decisions still required: <IDs>

## Spec-version history
| Version | Locked at/by | Delta IDs | Changed spec IDs | Reason | Downstream plan versions |

## Delivered-result comparison
| Spec ID | Final requirement | Delivered evidence | Status | Delta/version | Required action |

## Execution-discovered changes
| Delta | Discovery | Disposition | What changed in spec | What changed in plan/tasks | Verification |

## Unapproved drift
| Task/output | Expected | Actual | Containment | Fix implementation or consider spec change? |

## Acceptance evidence
| A-ID | Evidence/reviewer | Result | Gaps |

## Traceability and reproduction
| Deliverable | Generating tasks | Resources (RS-IDs) | Approved decisions | Reproduced by pipeline rerun? |

## Final user report and decisions
<Concise list of what changed from the original spec, why, who approved it, and what remains unresolved.>
```

## Completion gate

Execution is not fully closed until:

- every delta is dispositioned or explicitly deferred with an owner;
- every researcher gate is resolved (PDF §7);
- every approved delta appears in a versioned locked spec and affected plan/task artifacts;
- every unapproved divergence is surfaced, not normalized away;
- every final spec ID has a reconciliation status and evidence;
- every final deliverable is traced to tasks, resources and decisions, and the pipeline rerun reproduces it;
- dependent tasks remain blocked when reconciliation exposes unmet requirements;
- the user receives a concise report of all changes from the original spec to the delivered result.

## Common failure modes

- **Retroactive spec laundering:** change the spec after a failed build so the build “passes.” Keep the delta unapproved and classify the output `NOT-MET` or `ENACTED-UNAPPROVED`.
- **Chat-only drift:** an agent mentions a change but no durable delta exists. Require the report packet and integrator log.
- **Global stop for local delta:** every lane pauses. Block only affected dependencies and claims.
- **Silent prompt mutation:** update an in-progress task card without notifying its agent. Supersede and reissue the packet.
- **Delta spam:** agents report ordinary implementation choices as spec changes. Triage plan/task defects away from goal changes.
- **Acceptance weakening under pressure:** a missed test becomes an easier test. Require explicit user approval and preserve the original acceptance record.
- **Reconciliation without evidence:** mark items met based on author assertion. Require the evidence named by each `A-*` contract.

## Worked example

During a local archive build, the importer discovers that encrypted PDFs cannot be processed under the locked no-external-services constraint. The task reports `SD-004` and pauses only encrypted-PDF ingestion. Other importers continue. The integrator determines this is a substantive scope/acceptance choice and asks whether to exclude encrypted PDFs with an explicit failure report or add a local decryption input requirement. The user approves the latter; the spec advances from v1 to v2, the importer and acceptance fixture tasks are remapped, and affected agents receive new packets. After execution, `Spec-Reconciliation.md` shows v1→v2, the approved change, evidence that the new case passes, and one unrelated unverified accessibility test still blocking full closure.
