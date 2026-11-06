# SPEC: <name>

Status: OPEN | APPROVED | LOCKED
Version: v001
Supersedes: none | <prior version/path>
Owner: <user/approver>
Mode: new | revision
Authoritative inputs: <paths/links>

## Goal and success
- G-001 [USER]: <outcome>
- G-002 [SOURCE:<source>]: <why it matters / downstream use>

## Actors, audience, and operating context
| Actor | Needs / permissions | Context of use | Successful experience |
|---|---|---|---|
| <actor> | <needs / permissions> | <context of use> | <successful experience> |

## Deliverables
| ID | Deliverable | Format/surface | Required contents | Consumer | Priority | Resources (Stage 2) |
|---|---|---|---|---|---|---|
| D-001 | <deliverable> | <format/surface> | <required contents> | <consumer> | <priority> | <RS-### IDs, filled at Stage 2> |

## Deliverable types
<!--
Optional. One fenced block per typed deliverable; a deliverable without one is
drawn as a plain tile (warning W-UNTYPED). Open the fence with the word
`deliverable` and the deliverable's ID, for example ```deliverable D-001```.
Each line is `key: value`; a value is read as JSON when it is valid JSON,
otherwise as a bare string. Blank lines and `#` lines are ignored.
The example blocks below are inert (their fence is `text`): copy the key lines
of the matching type into a `deliverable D-###` fence and replace the
placeholders. Delete the examples you do not use.
-->

```text
# coef-plot: one row per term, optional facets per model.
type: coef-plot
terms: ["<term>", "<term>"]
models: ["<model>", "<model>"]
facets: ["<facet>"]
```

```text
# regression-table: columns = models; footer rows such as N and R².
type: regression-table
terms: ["<term>", "<term>"]
models: ["<model>", "<model>"]
footer: ["N", "R²"]
```

```text
# dataset: codebook rows are [name, label, type, values].
type: dataset
unit: <unit of observation>
target: <≈ rows × columns>
variables: [["<name>", "<label>", "<type>", "<values>"]]
```

```text
# chart: kind is bar or line; groups is optional.
type: chart
kind: bar
x: <x-axis variable>
y: <y-axis variable>
groups: ["<group>", "<group>"]
```

```text
# summary-table: one row per variable.
type: summary-table
variables: ["<variable>", "<variable>"]
```

```text
# report-outline: sections are [title, page target]; the target may be a number or a string.
type: report-outline
sections: [["<section title>", 2], ["<section title>", "<pages>"]]
```

```text
# deck-outline: one title per slide.
type: deck-outline
slides: ["<slide title>", "<slide title>"]
```

```text
# replication-package: inputs are [file, source]; language is the script extension (R, py, do).
# Drawn as README.txt, codebook.pdf, inputs/, outputs/tables/, outputs/figures/ and
# scripts/data_builder.<ext> + scripts/analysis.<ext>. datasets is optional.
type: replication-package
inputs: [["<raw file>", "<source>"], ["<raw file>", "<source>"]]
tables: ["<table>", "<table>"]
figures: ["<figure>"]
language: <script extension>
datasets: ["<analysis-ready file>"]
```

## Requirements
| ID | Requirement | Applies to | Source | Priority | Notes/example |
|---|---|---|---|---|---|
| R-001 | <requirement> | <D-### IDs> | <source> | <priority> | <notes/example> |

## Scenarios
| ID | Actor/start | Trigger/input | Expected final state | Failure behavior | Requirement IDs |
|---|---|---|---|---|---|
| S-001 | <actor/start> | <trigger/input> | <expected final state> | <failure behavior> | <R-### IDs> |

## Inputs and provenance
| Input | Owner/source | Required? | Validity/freshness | Missing/conflict behavior |
|---|---|---|---|---|
| <input> | <owner/source> | <yes/no> | <validity/freshness> | <missing/conflict behavior> |

## Output/interface contracts
| Producer/result | Consumer | Format/granularity | Required fields/properties | Rejection condition |
|---|---|---|---|---|
| <producer/result> | <consumer> | <format/granularity> | <required fields/properties> | <rejection condition> |

## Quality attributes
| Attribute | Required outcome | Observable threshold/evidence | Priority |
|---|---|---|---|
| <attribute> | <required outcome> | <observable threshold/evidence> | <priority> |

## Acceptance tests
| ID | Given | When | Then | Evidence | Approver | Requirement IDs |
|---|---|---|---|---|---|---|
| A-001 | <given> | <when> | <then> | <evidence> | <approver> | <R-### IDs> |

## Constraints
- C-001 [USER]: <fixed boundary>

## Non-goals
- N-001 [USER]: <explicit exclusion>

## Open questions and provisional assumptions
| ID | Question/assumption | Why it matters | Owner | Blocking? | Resolution |
|---|---|---|---|---|---|
| Q-001 | <question/assumption> | <why it matters> | <owner> | <yes/no> | <resolution> |

## Change history
| Version | Delta ID | Changed spec IDs | Change | Approved by/at | Reason | Downstream artifacts superseded |
|---|---|---|---|---|---|---|
| v001 | <delta ID or none> | <spec IDs> | <change> | <name, timestamp> | <reason> | <artifacts or none> |

## Sign-off
- Spec review: <Spec-Review.md path; findings resolved>
- Approved by/at: <name, timestamp>
- Locked by/at (Stage 6 baseline): <name, timestamp>
- Delegated inferences accepted: <IDs or none>
