# PLAN: <goal>

Status: READY | READY-WITH-BLOCKS | NOT-READY (readiness; lock state is `Baseline lock` below)
Spec: <path + approved version>; resources: <RESOURCES.md path + version>
Baseline lock: <timestamp, by> (Stage 6; leave the value empty until locked)
Deadline: <YYYY-MM-DD | none>
Source draft plan/review: <Plan-Draft.md, Plan-Review.md paths>
Mode: PLAN_ONLY | PLAN_AND_EXECUTE

## Fixed decisions and preserved strengths
- <decision or strength>

## Finding disposition ledger
| Finding | Disposition | Evidence/reason | Plan change | User decision |
|---|---|---|---|---|
| <finding ID> | <disposition> | <evidence/reason> | <plan change> | <user decision> |

## Requirement traceability
| Spec ID | Producer task/output | Verifier/review evidence | Status |
|---|---|---|---|
| <D/R/A ID> | <T-### / output> | <verifier/review evidence> | <status> |

## Lanes
<!-- `researcher` is reserved for the human decision-maker (shown as "You"); keep its row. Other lanes take the owner colours in table order. -->
| Lane | Display name | Persona |
|---|---|---|
| researcher | You | researcher (human) |
| <lane-slug> | <display name> | <persona> |

## Task graph
<!-- Waves: `W2` or `W2-W3`. Requires = hard edges (must finish first); Soft = soft edges (drawn dashed, not scheduled). Enables must be the exact inverse of Requires. Researcher-lane tasks are decisions: they take no wave time. Lists use commas; write `none` for an empty list. -->
| Task | Lane | Waves | Status | Requires | Soft | Enables | Resources | Delivers | Write claim | Researcher gates | Acceptance IDs |
|---|---|---|---|---|---|---|---|---|---|---|---|
| T-001 | <lane-slug> | W1 | pending | none | none | <T-### IDs> | <RS-### IDs> | <D-### IDs or none> | <paths/sections> | <T-### gate IDs or none> | <A-### IDs> |

## Parallel waves
<!-- Waves run W1..Wn with no gaps; table order is the time axis. Target is free text: a date or "wk 1". -->
| Wave | Target | Ready condition | Lanes/tasks | Collision result | Integration/review gate |
|---|---|---|---|---|---|
| W1 | <date or "wk 1"> | <ready condition> | <lanes/tasks> | <collision result> | <integration/review gate> |

## Task cards
<!-- One card per Task graph row, headed `### T-### — <name>`. Card sub-headings are level 4 (`####`). `Generated-from` and `Gate-mode` appear only on gate tasks inserted by the classifier (researcher lane). Gate-mode approve means the gate quotes the recommendation for you to approve or change; decide means the gate gives background only. `#### Decision points` holds one bullet per decision point, phrased as a decision (IDs unique plan-wide), or the word `none`. Each bullet needs two indented sub-bullets: Default (what the agent does if nobody objects) and Recommendation (the recommended choice, a dash, and a one-line reason). -->

### T-001 — <imperative task name>

Status: pending | ready | blocked | in-progress | verified | complete | superseded
Type: spike | build | migrate | integrate | verify | document | operate
Priority: critical-path | required | optional
Spec refs: <G/D/R/A/C/N IDs>
Decision refs: <DEC IDs>
Generated-from: <DP-### — classifier-inserted gate tasks only; delete this line otherwise>
Gate-mode: <approve | decide — classifier-inserted gate tasks only; delete this line otherwise>

#### Objective
<One observable result this task produces.>

#### Inputs
| Input | Location/producer | Required state/version | Missing-input behavior |
|---|---|---|---|
| <input> | <location/producer> | <required state/version> | <missing-input behavior> |

#### Outputs
| Output | Exact path/interface/artifact | Consumer(s) | Contract / required properties |
|---|---|---|---|
| <output> | <exact path/interface/artifact> | <consumer(s)> | <contract / required properties> |

#### Execution resources
- Persona/role: <existing persona or bounded role>
- Tools/connectors: <specific available tools>
- Skills/protocols: <exact existing paths/names>
- Working directory/environment: <path/surface>

#### Dependencies
- Requires: <T-IDs or none>
- Enables: <T-IDs>
- Can run with: <T-IDs>
- Researcher gates: <decisions the researcher must approve before this task starts or completes, or none>

#### Ownership and collision control
- Read scope: <paths/interfaces>
- Write claim: <exact paths or logical sections>
- Shared surfaces: <none or integrator owner + merge order>

#### Procedure boundary
- Included: <work this agent owns>
- Excluded: <nearby work owned elsewhere>
- Fixed decisions: <items not to reopen>

#### Spec-change reporting
- Spec version: <version/path; locked at the Stage 6 baseline>
- Report to: <integrator/mailbox recipient>
- Report when: <task-specific impossibility, ambiguity, new constraint, scope/acceptance change, or observed deviation triggers>
- Stop boundary: <exact work/output that must pause>
- Safe continuation: <independent work allowed after reporting>
- Forbidden: editing `SPEC.md` or `CHANGELOG.md` directly

#### Verification and review
- Self-checks: <commands/inspection>
- Independent review: <reviewer/task and evidence>
- Acceptance tests: <A-IDs>
- Failure/rollback: <containment and reversible path>

#### Decision points
- DP-001: <the choice, phrased as a decision>
  - Default: <the choice the agent makes if nobody objects>
  - Recommendation: <the choice the AI recommends> — <one-line reason>

#### Return report
Changed files; verification results (each check above, with evidence); failures; blockers; unresolved decisions; proposed status (`verified` or `blocked`). Sent to the plan integrator, who alone marks `complete`.

#### Done condition
<Exact output + checks + handoff state required before the task may be marked `verified`.>

#### Chunking trigger
<When task engineering must split this task into sequential handoffs.>

## Launch manifest
| Lane | Task/chunk | Persona | CWD | Inputs | Claim | Output | Researcher gates | Review | Release |
|---|---|---|---|---|---|---|---|---|---|
| <lane-slug> | <T-### / chunk> | <persona> | <cwd> | <inputs> | <claim> | <output> | <gates> | <review> | <release> |

## Task-engineering queue
<One fixed-input packet per ready task.>

## Spec-change control
- Current locked spec/version: <path/version>
- Delta log: <path; integrator is sole writer>
- Delta recipient: <integrator/mailbox>
- Lane reporting contract: <trigger + stop/continue rule>
- Post-execution reconciliation: `planning-spec-reconciliation-protocol.md`

## Risks, approvals, rollback
## Blocked/deferred items
## Readiness-audit results
## User authorization to execute
