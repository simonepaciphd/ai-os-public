# Resources: Information exposure and institutional trust

Status: APPROVED
Version: v001
Spec: SPEC.md v001
Search scope: project data and code folders; vendor delivery portal not searched
Prepared by: resource-map subagent, 2025-12-05

## Asset inventory
| Asset ID | Location | Type | Description | Purpose / producer | Access constraints | Verification status | Registry |
|---|---|---|---|---|---|---|---|
| RS-001 | data/raw/wave1.csv | data | Survey wave 1 raw responses | Survey vendor | Restricted: no redistribution | VERIFIED | unregistered |
| RS-002 | data/raw/wave2.csv | data | Survey wave 2 raw responses | Survey vendor | Restricted: no redistribution | VERIFIED | unregistered |
| RS-003 | docs/codebook.pdf | document | Survey codebook with variable definitions | Survey vendor | none | VERIFIED | unregistered |
| RS-004 | docs/preregistration.pdf | document | Pre-registration document with model specification | Project lead | none | VERIFIED | unregistered |
| RS-005 | env/analysis-environment.txt | software | Pinned statistical software environment | Analysis lane | none | LISTED | unregistered |

## Resource-to-deliverable map
| Spec ID | Needed input | Resource(s) | Relationship | Confidence | Evidence |
|---|---|---|---|---|---|
| D-001 | Raw responses and definitions | RS-001, RS-002, RS-003 | source | high | Files opened |
| D-003 | Model specification | RS-004, RS-005 | specification | high | Pre-registration section 4 |

## Unresourced deliverables
| Spec ID | Missing | Options | User decision | Status |
|---|---|---|---|---|
| none | — | — | — | — |

## Unmapped resources
| Asset ID | Classification | Reason | User decision |
|---|---|---|---|
| none | — | — | — |

## Open questions
| ID | Question | Why it matters | Blocking? |
|---|---|---|---|
| none | — | — | no |

## Change history
| Version | Change | Approved by/at |
|---|---|---|
| v001 | Initial inventory | Project lead, 2025-12-06 |
