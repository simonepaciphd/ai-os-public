---
name: planning-adversarial-review-protocol
description: Independently challenge a technical plan against its approved goal specification and resource map, finding omissions, contradictions, inefficiencies, missed dependencies, collisions, weak reviews, and unrealized synergies. Use automatically after implementation mapping, in a fresh read-only subagent context, to produce evidence-linked proposed plan patches without rewriting the plan. In `SPEC` mode, also challenge a spec draft before approval (feasibility, consistency, research design, completeness, whether outputs answer the research questions).
audience: public
version: 0.2
---

# Planning Adversarial-Review Protocol

Act as an independent red-team reviewer of a plan, not as its coauthor. Test whether the technical map can actually produce the approved goal efficiently and safely.

Composes with `planning-output-specification-protocol.md`, `planning-implementation-map-protocol.md`, `planning-protocol.md`, downstream `planning-adjudication-protocol.md`, and execution feedback through `planning-spec-reconciliation-protocol.md`.

Version: 0.2 (first public release; earlier versions are not shipped in this repo).

## Modes

- **`PLAN` mode (default)** — everything below except the `SPEC` mode section.
- **`SPEC` mode** — the section *SPEC mode* only, plus the universal rules that it names.

## Invocation contract

The orchestrator automatically spawns this skill in `PLAN` mode after `Plan-Draft.md` passes its structural completion gate.

Required inputs:

- approved, resource-linked `SPEC.md` and `RESOURCES.md`;
- `Plan-Draft.md` and all task cards;
- only the project interfaces or tree needed to verify factual feasibility.

Isolation rules:

- Work read-only.
- Return the review to the parent; do not edit the spec, plan, task cards, ledgers, or source files.
- Do not receive the mapper's hidden rationale, expected weaknesses, or preferred corrections.
- Treat `SPEC.md` as authoritative. If it is ambiguous or contradictory, file `SPEC-QUESTION`; do not decide the user's goal.

## Output

Produce `Plan-Review.md` with findings that can be adjudicated individually. Every finding must cite concrete spec IDs, task IDs, plan sections, interfaces, or file paths.

Severity:

- `CRITICAL`: the plan cannot satisfy a must-have goal, is unsafe, or would cause irrecoverable/shared-state harm.
- `HIGH`: a major requirement, dependency, integration, or verification gap is likely to fail.
- `MEDIUM`: material inefficiency, fragile coupling, missed reuse/synergy, or under-specified boundary.
- `LOW`: localized clarity or optimization issue with limited outcome risk.

Finding types:

`OMISSION | CONTRADICTION | INEFFICIENCY | DEPENDENCY | COLLISION | INTERFACE | REVIEW-GAP | RISK | GRANULARITY | SYNERGY | SPEC-QUESTION | CHANGE-CONTROL`.

## Universal rules

1. **Attack the mapping, preserve the goal.** Judge whether the plan realizes the spec; never substitute your preferred product or research judgment.
2. **Evidence before criticism.** Quote or point to the exact requirement/task/interface that creates the problem.
3. **Show consequence.** Explain what fails, duplicates, blocks, or becomes risky if the finding is ignored.
4. **Propose a minimal patch.** Name added/removed/merged/split tasks, changed edges, altered claims, or new review evidence. Do not rewrite the plan wholesale.
5. **Distinguish defects from preferences.** A viable alternative is not a finding unless the current choice violates the spec, project conventions, cost/risk constraints, or coherence.
6. **Search for positive synergies.** Identify reusable outputs, shared evidence collection, common schemas, combined reviews, and sequencing changes that reduce work without coupling agents unsafely.
7. **Audit parallelism both ways.** Flag unsafe fan-out and missed concurrency.
8. **No generic advice.** “Add more tests,” “improve documentation,” or “consider security” is invalid without a target, evidence, and proposed acceptance check.
9. **Audit execution feedback.** Flag plans that provide no durable way for task agents to report discovered spec conflicts, pause affected work, obtain user approval, version the spec, and propagate accepted changes.

## SPEC mode — review the spec draft

The orchestrator spawns this mode in Stage 1, once the spec draft passes its completeness checks and before the user approves it.

Inputs: the user's brief, the spec draft, and the authoritative inputs the spec cites. Same isolation as plan mode: read-only, return findings to the parent, no access to the author's private rationale. Universal rules 2, 3, 5 and 8 apply.

Challenge the draft on:

1. **Feasibility** — can each deliverable be produced with the stated inputs, time and constraints?
2. **Internal consistency** — do any requirements, constraints, non-goals or acceptance tests contradict one another?
3. **Research design** — do the samples, variables, methods and robustness checks support the claims the outputs are meant to make?
4. **Completeness** — are deliverables, edge cases, failure behavior or acceptance evidence missing?
5. **Question fit** — does the set of outputs actually answer the stated research questions or goals?

Finding types: `FEASIBILITY | CONSISTENCY | DESIGN | COMPLETENESS | QUESTION-FIT`. Severity as in plan mode. Each finding states the problem, its consequence, and alternative resolutions. **The reviewer proposes; the user resolves every substantive choice** — never rewrite the goal or pick among research-design alternatives.

Output `Spec-Review.md`: inputs reviewed, isolation, verdict (`Approve as drafted | Approve after fixes | Requires user decisions`), findings (`SF-###`: severity/type, evidence with spec IDs, problem, consequence, alternatives, user decision required, confidence), and what the review does not show. Complete when every `G/D/R/A/C` item has been examined, every finding cites spec IDs, and no file has been modified.

## Pass 1 — Spec coverage from the outside in

Start from every `D-*`, `R-*`, `A-*`, and `C-*` rather than from the plan's task order.

For each, ask:

- Which task produces the required result?
- Which artifact demonstrates it?
- Which independent check proves the relevant acceptance test?
- Does the task's output contract actually match the downstream consumer?
- Is the requirement only mentioned, or operationally enforced?
- Could all listed tasks finish while this requirement still fails?

Flag orphaned requirements, ornamental checks, and acceptance tests that can pass without the intended outcome.

## Pass 2 — Task graph and interface integrity

Audit:

- missing, reversed, circular, or unnecessary dependencies;
- inputs that are neither pre-existing nor produced by predecessors;
- outputs with no consumer;
- two tasks owning the same path, table, schema, API, section, or external state in the same wave;
- consumers starting before interface/schema decisions are locked;
- integration tasks with no explicit merge order or conflict owner;
- tasks so broad they cannot be independently reviewed;
- tasks so narrow their handoff cost exceeds their work;
- critical-path blockers mislabeled optional or deferred.

Try to construct a counterexample execution where agents follow every task card exactly and still deadlock, overwrite work, or produce incompatible outputs.

## Pass 3 — Efficiency and synergy

Look for:

- duplicated discovery, extraction, setup, conversion, or validation across tasks;
- one upstream artifact that could satisfy several downstream inputs;
- shared fixtures, schemas, templates, or test harnesses that should be built once;
- reviews that can be combined because they inspect the same evidence;
- serial tasks with independent inputs and write scopes that should share a wave;
- parallel tasks that will repeatedly synchronize and should be merged;
- needless tool or persona switching;
- costly work scheduled before a cheap feasibility probe or smoke test;
- work on optional features that delays the critical path.

Do not call every shared asset a synergy: centralization is useful only when it reduces duplication without creating a bottleneck or shared-writer conflict.

## Pass 4 — Operability, risk, and recovery

Audit whether the plan includes, where applicable:

- failure detection and actionable error reporting;
- rollback, containment, retry, resume, and idempotence;
- data provenance, migration reconciliation, and no-loss checks;
- sensitive-data and credential boundaries;
- cost/time estimates and small-sample smoke gates;
- external-communication/deployment approvals;
- observability and ownership after delivery;
- documentation and handoff sufficient for the named operator;
- a real end-to-end acceptance run using the same interfaces as production.
- task-level triggers for reporting a spec delta and a named integrator/sole delta-log writer;
- a narrow stop/continue rule so one delta does not freeze unrelated parallel work;
- post-execution reconciliation of delivered artifacts against the final locked spec and approval history.

## Pass 5 — Reviewer self-challenge

Before finalizing:

1. Identify the strongest reason each `CRITICAL` or `HIGH` finding might be wrong.
2. Downgrade or remove findings that depend on unstated preferences.
3. Confirm each proposed patch preserves approved spec decisions.
4. Check for pairs of findings whose patches conflict.
5. State the top three things the plan already does well so adjudication does not accidentally regress them.

## `Plan-Review.md` template

```markdown
# Adversarial Review: <plan>

Inputs reviewed: <paths/versions>
Reviewer isolation: fresh subagent | fallback fresh-context pass
Review scope: coverage, graph, interfaces, efficiency, parallelism, risk, verification

## Executive verdict
- Ready as written | Ready after fixes | Requires user decisions | Re-map required
- Critical: <n>; High: <n>; Medium: <n>; Low: <n>
- Strongest preserved features: <three>

## Findings

### F-001 — <short title>
- Severity/type: HIGH / DEPENDENCY
- Evidence: <spec IDs, task IDs, section/path>
- Problem: <precise defect>
- Consequence: <what fails or costs more>
- Counterexample: <how exact plan execution exposes it>
- Proposed minimal patch: <task/edge/claim/review change>
- Affected tasks/spec IDs: <IDs>
- User decision required: yes/no; <why>
- Confidence: high/medium/low

## Missed synergies
| Finding | Reusable connection | Proposed change | Coupling risk | Net benefit |

## Parallelism audit
| Wave/tasks | Issue | Collision/dependency evidence | Proposed topology |

## Coverage delta
| Spec ID | Current mapping | Gap | Proposed producer/verifier |

## Conflicting recommendations
<Any findings that cannot both be adopted.>

## What this review does not show
<Limits, unavailable context, and non-claims.>
```

## Completion gate

Return only after:

- every must-have spec item has been audited;
- every wave has been collision-checked;
- every task input/output boundary has been sampled, with critical-path boundaries checked exhaustively;
- every high/critical finding has a concrete patch or a clearly stated user decision;
- the plan's during/post-execution spec-change channel has been audited;
- speculative preferences have been removed or labeled low-confidence;
- no file has been modified.

## Common failure modes

- **Persona drift into planner:** reviewer rewrites the whole plan. Convert changes into atomic findings and patches.
- **Severity inflation:** every improvement is “high.” Re-anchor severity to failure consequence.
- **Checklist theater:** generic risks appear without plan evidence. Delete them.
- **Goal challenge disguised as review:** reviewer prefers a different output. File `SPEC-QUESTION` only if the approved spec is genuinely inconsistent or underspecified.
- **Parallelism maximalism:** reviewer recommends more agents without checking write scopes and coordination cost. Include a concrete wave topology.
- **Synergy maximalism:** shared components become bottlenecks. State coupling risk and net benefit.
- **Change-control blind spot:** the plan assumes execution cannot teach anything about the spec. Add a concrete reporting, adjudication, versioning, propagation, and final reconciliation path.

## Worked example

Given a plan for a multi-source briefing system, the reviewer finds that every source adapter produces a differently named date field (`INTERFACE`), two parallel agents both edit the central registry (`COLLISION`), source-quality checks repeat four times (`SYNERGY`), and no task verifies the user's maximum-reading-time acceptance test (`OMISSION`). It proposes one schema-lock predecessor, disjoint adapter outputs plus a single registry integrator, one reusable evidence-quality harness, and a final timed acceptance review.
