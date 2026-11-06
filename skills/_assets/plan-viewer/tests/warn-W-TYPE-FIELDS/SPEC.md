# SPEC: Information exposure and institutional trust

Status: APPROVED
Version: v001
Supersedes: none
Owner: Project lead
Mode: new
Authoritative inputs: pre-registration document (RS-004); survey codebook (RS-003)

## Goal and success
- G-001 [USER]: Estimate whether exposure to a short factual briefing changes respondents' trust in public institutions.
- G-002 [SOURCE:pre-registration]: Produce a working paper and a conference talk that report the pre-registered estimates.

## Actors, audience, and operating context
| Actor | Needs / permissions | Context of use | Successful experience |
|---|---|---|---|
| Project lead | Approves specification and exclusions | Reviews outputs before release | Every estimate traces to a pre-registered choice |
| Conference audience | Reads slides only | 15-minute talk | Main result is clear in under a minute |

## Deliverables
| ID | Deliverable | Format/surface | Required contents | Consumer | Priority | Resources (Stage 2) |
|---|---|---|---|---|---|---|
| D-001 | Analysis dataset | CSV + codebook | One row per respondent; **all** pre-registered variables; `wave` identifier | Analysis lane | required | RS-001, RS-002, RS-003 |
| D-002 | Descriptive statistics table | Table in paper | Mean, SD, min and max for every covariate | Paper readers | required | RS-003 |
| D-003 | Main regression table | Table in paper | Models M1-M3 with robust SEs; N and R² | Paper readers | required | RS-004, RS-005 |
| D-004 | Coefficient plot | Figure in paper | Treatment and moderator terms for M1-M3 | Paper readers | required | RS-005 |
| D-005 | Trust by treatment arm | Figure in paper | Mean trust by arm and survey wave | Paper readers | optional | RS-005 |
| D-006 | Working paper | PDF | Sections and page targets as outlined | Reviewers | required | none |
| D-007 | Conference slides | Slide deck | Title, design, main result, robustness, next steps | Conference audience | required | none |
| D-008 | Replication package | Archive | Code, cleaned data and a README that runs end to end | Journal editors | required | RS-005 |
| D-009 | Online appendix | PDF | Robustness tables and full question wording | Reviewers | optional | none |

## Deliverable types

```deliverable D-001
type: dataset
unit: respondent
target: "≈ 2,400 rows × 18 columns"
variables: [["resp_id", "Respondent identifier", "int", "1-2400"], ["wave", "Survey wave", "int", "1, 2"], ["treat", "Briefing arm", "cat", "control, briefing"], ["trust", "Institutional trust index", "float", "0-10"]]
```

```deliverable D-002
type: summary-table
variables: ["age", "education", "income", "trust", "news_use"]
```

```deliverable D-003
type: regression-table
terms: ["Briefing", "Briefing × News use", "News use"]
models: ["M1", "M2", "M3"]
footer: ["N", "R²"]
```

```deliverable D-004
# Faceted by survey wave.
type: coef-plot
terms: ["Briefing", "Briefing × News use"]
models: ["M1", "M2", "M3"]
facets: ["Wave 1", "Wave 2"]
```

```deliverable D-005
type: chart
kind: pie
x: Treatment arm
y: Mean trust (0-10)
groups: ["Wave 1", "Wave 2"]
```

```deliverable D-006
type: report-outline
sections: [["Introduction", 3], ["Design and data", 5], ["Results", 8], ["Robustness", "4-6"], ["Conclusion", 2]]
```

```deliverable D-007
type: deck-outline
slides: ["Title", "Research question", "Design", "Main result", "Robustness", "Next steps"]
```

```deliverable D-008
type: replication-package
inputs: [["wave1.csv", "Survey vendor, wave 1 delivery"], ["wave2.csv"]]
tables: ["Descriptive statistics", "Main regression table"]
figures: ["Coefficient plot", "Trust by treatment arm"]
language: R
datasets: ["analysis.csv"]
```

## Requirements
| ID | Requirement | Applies to | Source | Priority | Notes/example |
|---|---|---|---|---|---|
| R-001 | Estimates follow the pre-registered specification | D-003, D-004 | pre-registration | required | Deviations listed in the paper |
| R-002 | The replication package reproduces every table and figure | D-008 | journal policy | required | One command |

## Scenarios
| ID | Actor/start | Trigger/input | Expected final state | Failure behavior | Requirement IDs |
|---|---|---|---|---|---|
| S-001 | Journal editor | Runs the replication package | All tables and figures regenerate | Script stops with a named missing input | R-002 |

## Inputs and provenance
| Input | Owner/source | Required? | Validity/freshness | Missing/conflict behavior |
|---|---|---|---|---|
| Survey waves 1 and 2 | Survey vendor | yes | Final delivery files | Stop and report |

## Output/interface contracts
| Producer/result | Consumer | Format/granularity | Required fields/properties | Rejection condition |
|---|---|---|---|---|
| Cleaning script | Analysis lane | CSV, one row per respondent | Codebook variables | Missing `resp_id` |

## Quality attributes
| Attribute | Required outcome | Observable threshold/evidence | Priority |
|---|---|---|---|
| Reproducibility | Same outputs from a clean run | Byte-identical tables | required |

## Acceptance tests
| ID | Given | When | Then | Evidence | Approver | Requirement IDs |
|---|---|---|---|---|---|---|
| A-001 | Cleaned dataset | Models are run | Estimates match the pre-registered specification | Model log | Project lead | R-001 |
| A-002 | Replication package | Run from a clean folder | All outputs regenerate | Run log | Project lead | R-002 |

## Constraints
- C-001 [USER]: No new data collection.

## Non-goals
- N-001 [USER]: No causal mediation analysis.

## Open questions and provisional assumptions
| ID | Question/assumption | Why it matters | Owner | Blocking? | Resolution |
|---|---|---|---|---|---|
| Q-001 | none | — | — | no | — |

## Change history
| Version | Delta ID | Changed spec IDs | Change | Approved by/at | Reason | Downstream artifacts superseded |
|---|---|---|---|---|---|---|
| v001 | none | all | Initial version | Project lead, 2025-12-01 | — | none |

## Sign-off
- Spec review: Spec-Review.md; findings resolved
- Approved by/at: Project lead, 2025-12-01
- Locked by/at (Stage 6 baseline): Project lead, 2025-12-15
- Delegated inferences accepted: none
