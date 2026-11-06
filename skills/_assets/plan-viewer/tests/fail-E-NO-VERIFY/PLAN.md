# PLAN: Information exposure and institutional trust

Status: READY
Spec: SPEC.md v001; resources: RESOURCES.md v001
Baseline lock: 2025-12-15T10:00-08:00, project lead
Deadline: 2026-03-31
Source draft plan/review: Plan-Draft.md, Plan-Review.md
Mode: PLAN_AND_EXECUTE

## Fixed decisions and preserved strengths
- The pre-registered model specification is fixed; deviations need a spec delta.

## Finding disposition ledger
| Finding | Disposition | Evidence/reason | Plan change | User decision |
|---|---|---|---|---|
| F-001 | accepted | Attention-check rule was implicit | Added gate T-004 | Approved |

## Requirement traceability
| Spec ID | Producer task/output | Verifier/review evidence | Status |
|---|---|---|---|
| R-001 | T-005 / model outputs | A-001 model log | planned |
| R-002 | T-009 / replication package | A-002 run log | planned |

## Lanes
| Lane | Display name | Persona |
|---|---|---|
| researcher | Project lead | researcher (human) |
| data | Data engineering | engineer |
| analysis | Analysis | researcher |
| writing | Writing | writer |

## Task graph
| Task | Lane | Waves | Status | Requires | Soft | Enables | Resources | Delivers | Write claim | Researcher gates | Acceptance IDs |
|---|---|---|---|---|---|---|---|---|---|---|---|
| T-001 | data | W1 | ready | none | none | T-002, T-003, T-004, T-006 | RS-001, RS-002, RS-003 | D-001 | data/clean/ | none | none |
| T-002 | analysis | W2 | pending | T-001 | none | T-005 | RS-003 | D-002 | output/descriptives/ | none | none |
| T-003 | researcher | W2 | pending | T-001 | none | T-005 | RS-004 | none | none | — | none |
| T-004 | researcher | W2 | pending | T-001 | none | T-005 | none | none | none | — | none |
| T-005 | analysis | W3-W4 | pending | T-002, T-003, T-004 | none | T-007, T-008, T-009 | RS-004, RS-005 | D-003, D-004 | output/models/ | T-003, T-004 | A-001 |
| T-006 | analysis | W4 | pending | T-001 | T-005 | T-007, T-008 | RS-005 | D-005 | output/figures/ | none | none |
| T-007 | writing | W5 | pending | T-005, T-006 | none | none | none | D-006, D-009 | paper/ | none | none |
| T-008 | writing | W5 | pending | T-005, T-006 | T-007 | none | none | D-007 | slides/ | none | none |
| T-009 | data | W5 | pending | T-005 | none | none | RS-005 | D-008 | replication/ | none | A-002 |

## Parallel waves
| Wave | Target | Ready condition | Lanes/tasks | Collision result | Integration/review gate |
|---|---|---|---|---|---|
| W1 | 2026-01-16 | Spec locked | data: T-001 | none | Dataset review |
| W2 | 2026-01-30 | D-001 verified | analysis: T-002; researcher: T-003, T-004 | none | Gates approved |
| W3 | 2026-02-13 | Gates approved | analysis: T-005 | none | none |
| W4 | 2026-02-27 | — | analysis: T-005, T-006 | output/ split by subfolder | Model review |
| W5 | 2026-03-20 | Models verified | writing: T-007, T-008; data: T-009 | none | Final review |

## Task cards

### T-001 — Clean and merge the survey waves

Status: ready
Type: build
Priority: critical-path
Spec refs: D-001

#### Objective
One cleaned respondent-level dataset combining both waves.

#### Outputs
| Output | Exact path/interface/artifact | Consumer(s) | Contract / required properties |
|---|---|---|---|
| Analysis dataset | `data/clean/analysis.csv` | T-002, T-005, T-006 | One row per respondent; codebook variables |

#### Verification and review
- Self-check: row count equals the sum of both wave files minus documented duplicates.
- Independent review: a second agent compares five random rows against the raw files.

#### Decision points
none

### T-002 — Produce descriptive statistics

Status: pending
Type: build
Priority: required
Spec refs: D-002

#### Objective
A descriptive statistics table for every covariate.

#### Outputs
| Output | Exact path/interface/artifact | Consumer(s) | Contract / required properties |
|---|---|---|---|
| Descriptives table | `output/descriptives/table1.csv` | T-007 | Mean, SD, min, max per covariate |

#### Verification and review
- Self-check: every codebook covariate appears once.
- Independent review: totals match the dataset row count.

#### Decision points
- DP-001: Decide whether respondents who fail the attention check are excluded from the analysis sample.
  - Default: Keep every respondent and report attention-check failures in a footnote.
  - Recommendation: Exclude respondents who fail the check — the pre-registration lists it as an exclusion criterion.

### T-003 — Approve the model specification

Status: pending
Type: verify
Priority: critical-path
Spec refs: R-001
Generated-from: DP-005
Gate-mode: approve

#### Objective
The project lead confirms the model specification matches the pre-registration.

#### Outputs
Signed approval line in the decision log.

#### Verification and review
- The approval names the pre-registration section it checked.

#### Decision points
none

### T-004 — Decide the attention-check exclusion rule

Status: pending
Type: verify
Priority: required
Generated-from: DP-001
Gate-mode: decide

#### Objective
The project lead decides the exclusion rule raised by DP-001.

#### Outputs
The chosen rule, recorded in the decision log.

#### Verification and review
- The decision log entry cites DP-001 and the option chosen.

#### Decision points
none

### T-005 — Estimate the main models

Status: pending
Type: build
Priority: critical-path
Spec refs: D-003, D-004, R-001, A-001

#### Objective
Estimates for models M1-M3 as pre-registered.

#### Outputs
| Output | Exact path/interface/artifact | Consumer(s) | Contract / required properties |
|---|---|---|---|
| Regression table | `output/models/table2.csv` | T-007, T-008 | M1-M3, robust SEs, N and R² |
| Coefficient plot | `output/models/figure1.pdf` | T-007, T-008 | Treatment and moderator terms |

#### Verification and review
- Self-check: the model log shows the pre-registered formula for each model.
- Independent review: a second agent re-runs M1 from a clean session and compares coefficients.
- Acceptance tests: A-001.

#### Decision points
- DP-002: Choose the file naming scheme for the model output tables.
  - Default: Name the tables table2.csv onward, in paper order.
  - Recommendation: Keep the paper-order names — they match the table numbers in the paper.
- DP-005: Decide whether models M1-M3 are estimated exactly as pre-registered.
  - Default: Estimate M1-M3 exactly as pre-registered.
  - Recommendation: Estimate M1-M3 exactly as pre-registered — any deviation needs a spec delta.

### T-006 — Plot trust by treatment arm

Status: pending
Type: build
Priority: optional
Spec refs: D-005

#### Objective
A bar chart of mean trust by treatment arm and wave.

#### Outputs
| Output | Exact path/interface/artifact | Consumer(s) | Contract / required properties |
|---|---|---|---|
| Bar chart | `output/figures/figure2.pdf` | T-007, T-008 | Bars by arm, grouped by wave |

#### Verification and review
- Self-check: bar heights match group means in the dataset.

#### Decision points
- DP-003: Choose the colour palette and the order of the bars.
  - Default: Use the house palette and the arm order in the codebook.
  - Recommendation: Put the control arm first — readers compare each treatment with control.

### T-007 — Draft the working paper

Status: pending
Type: document
Priority: critical-path
Spec refs: D-006, D-009

#### Objective
A complete working paper draft.

#### Outputs
| Output | Exact path/interface/artifact | Consumer(s) | Contract / required properties |
|---|---|---|---|
| Working paper | `paper/paper.pdf` | Reviewers | Sections and page targets in SPEC |

#### Verification and review
- Self-check: every table and figure in the paper is regenerated from the model outputs.
- Independent review: a reader checks each claim against the tables.

#### Decision points
none

### T-008 — Draft the conference slides

Status: pending
Type: document
Priority: required
Spec refs: D-007

#### Objective
A slide deck for a 15-minute talk.

#### Outputs
| Output | Exact path/interface/artifact | Consumer(s) | Contract / required properties |
|---|---|---|---|
| Slides | `slides/talk.pdf` | Conference audience | Six slides as outlined |

#### Verification and review

#### Decision points
none

### T-009 — Assemble the replication package

Status: pending
Type: build
Priority: required
Spec refs: D-008, R-002, A-002

#### Objective
An archive that reproduces every table and figure.

#### Outputs
| Output | Exact path/interface/artifact | Consumer(s) | Contract / required properties |
|---|---|---|---|
| Replication archive | `replication/package.zip` | Journal editors | Runs end to end with one command |

#### Verification and review
- Self-check: a clean-folder run regenerates every output.
- Acceptance tests: A-002.

#### Decision points
- DP-004: Choose the archive format for the replication package.
  - Default: A zip archive.
  - Recommendation: A zip archive — journals accept it without extra tools.

## Launch manifest
| Lane | Task/chunk | Persona | CWD | Inputs | Claim | Output | Researcher gates | Review | Release |
|---|---|---|---|---|---|---|---|---|---|
| data | T-001 | engineer | project root | RS-001, RS-002, RS-003 | data/clean/ | D-001 | none | second agent | integrator |

## Task-engineering queue
One packet per ready task: T-001.

## Spec-change control
- Current locked spec/version: SPEC.md v001
- Delta log: CHANGELOG.md; integrator is sole writer
- Delta recipient: integrator
- Lane reporting contract: report and pause on any deviation from the pre-registration
- Post-execution reconciliation: `planning-spec-reconciliation-protocol.md`

## Risks, approvals, rollback
- Vendor file revision: re-run T-001 and downstream tasks.

## Blocked/deferred items
none

## Readiness-audit results
All checks passed.

## User authorization to execute
Approved by the project lead, 2025-12-15.
