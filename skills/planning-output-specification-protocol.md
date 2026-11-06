---
name: planning-output-specification-protocol
description: Interview the user and inspect authoritative inputs to define exactly what a final deliverable, system, decision, or project result must look like and include—without planning implementation. Use as Stage 1 of planning or whenever a goal needs a detailed, testable output specification before technical choices or task decomposition.
audience: public
version: 0.3
---

# Planning Output-Specification Protocol

Define the destination before discussing the route. Produce a concrete, testable `SPEC.md` that a planner can later implement without guessing what “done” means.

Composes with `planning-protocol.md`; its draft is reviewed by `planning-adversarial-review-protocol.md` (`SPEC` mode); the approved spec is linked to resources by `planning-resource-map-protocol.md`, consumed by `planning-implementation-map-protocol.md` and versioned through `planning-spec-reconciliation-protocol.md` when execution evidence produces an approved change.

Version: 0.3 (first public release; earlier versions are not shipped in this repo).

## Boundary

This skill owns **what the final result is**. It does not own:

- implementation tasks or order;
- agent assignments or parallel waves;
- tools, frameworks, libraries, vendors, or code architecture;
- estimates based on an unchosen implementation;
- step-by-step execution instructions.

A user-mandated technology may appear only as a fixed constraint (for example, “must be an editable `.pptx`” or “must run on Cloudflare Workers”), never as an implementation recommendation.

## Output

Produce `SPEC.md` with stable IDs:

- `G-*` goal and outcome statements;
- `D-*` deliverables;
- `R-*` required content, behavior, or capability;
- `A-*` acceptance tests;
- `C-*` constraints;
- `N-*` non-goals;
- `Q-*` unresolved questions.

Use IDs from the first draft onward. Add new IDs; do not renumber existing ones.

## Universal rules

1. **Interrogate outcomes, not methods.** Ask what users see, receive, decide, or can do—not how it will be built.
2. **Inspect before asking.** Read supplied examples, source artifacts, templates, schemas, project instructions, and prior decisions. Never make the user restate discoverable facts.
3. **Evidence-tag the spec.** Mark each substantive line `USER`, `SOURCE:<path/link>`, `INFERRED`, or `OPEN`. An inference remains provisional until the user accepts the spec.
4. **Practical completeness.** Cover normal use, edge cases, failure behavior, quality thresholds, exclusions, maintenance/ownership expectations, and downstream use.
5. **Acceptance tests describe observable outcomes.** “High quality,” “robust,” and “user friendly” are not tests until translated into inspectable conditions.
6. **Do not invent preferences.** Offer alternatives when helpful, but record no choice without evidence.
7. **Ask in small decision batches.** Ask one to three high-leverage questions at a time. Combine independent, low-cost clarifications; isolate decisions with large downstream consequences.
8. **Approve explicitly; lock at the baseline.** Downstream planning begins only after the spec review is resolved and the user approves the spec draft or explicitly delegates remaining `INFERRED` items. The spec is `LOCKED` only at the planning baseline (Stage 6 of `planning-protocol.md`); until then it changes only with the user's approval, recorded in its change history.
9. **Version after the baseline lock.** Once the spec is locked, do not edit it in place. Report proposed changes through `planning-spec-reconciliation-protocol.md`, preserve the prior version, and link every approved change to its delta decision.

## Phase 0 — Intake and evidence inventory

1. Restate the initial goal as a provisional one-sentence outcome.
2. Identify the audience, operator, beneficiary, evaluator, and downstream consumer when distinct.
3. Inventory authoritative inputs and examples. For each, record location, authority, and what it constrains.
4. Extract already-fixed decisions, requirements, terminology, and exclusions.
5. Create an `Unknowns` list; separate missing facts from genuine user preferences.

Do not interview yet about facts available in the inventory.

## Phase 1 — Outcome interview

Cover the following domains, skipping only those clearly inapplicable. Ask targeted questions rather than reading the checklist verbatim.

1. **Purpose and use:** What decision, action, experience, or capability should the result enable? What happens immediately after delivery?
2. **Audience and environment:** Who uses it, with what expertise, access, device, context, frequency, and time pressure?
3. **Deliverable inventory:** What exact artifacts, surfaces, files, records, messages, or states must exist? Which are primary versus supporting?
4. **Required substance:** What must each deliverable contain, show, calculate, permit, prevent, preserve, or communicate?
5. **Behavior and lifecycle:** What are the main user journeys or operating scenarios from entry through completion? What persists, changes, expires, or repeats?
6. **Inputs and provenance:** What information enters the result, who supplies it, what is authoritative, what may be missing, and what must be traceable?
7. **Outputs and interfaces:** What leaves the result, in what format and granularity, and what other human or system consumes it?
8. **Edge cases and failure behavior:** What should happen on invalid, absent, duplicated, stale, conflicting, unauthorized, or partial input?
9. **Quality attributes:** What levels of correctness, usability, accessibility, privacy, security, performance, portability, maintainability, and editability matter?
10. **Constraints:** What deadlines, budgets, formats, policies, platforms, compatibility requirements, or immovable prior decisions constrain the result?
11. **Non-goals:** What plausible adjacent features, audiences, or outcomes are intentionally excluded?
12. **Acceptance and review:** Who approves the result, what evidence will they inspect, and what observable conditions distinguish pass from fail?

**Research projects.** When the goal is a research project or paper, also close gaps in: definitions of key concepts; samples and units; variables and their measurement; methodology and estimators; analyses; robustness checks; figures; tables; and paper outputs. Unanswered items stay `OPEN`; never substitute an assumption.

When the user cannot specify a numeric threshold, offer a bounded qualitative test tied to a real scenario—for example, “a first-time operator can complete the canonical workflow using only the delivered instructions”—and label it `INFERRED` until accepted.

## Phase 2 — Scenario and completeness pass

Write at least these scenarios when applicable:

| Scenario | Actor and starting state | Trigger/input | Expected final state | Failure behavior | Spec IDs |
|---|---|---|---|---|---|
| Canonical | Most common valid case | Normal input | Intended result | Explicit fallback | `R-*`, `A-*` |
| Boundary | Minimum/maximum/empty/duplicate | Edge input | Defined behavior | No silent corruption | `R-*`, `A-*` |
| Failure | Unavailable/invalid/unauthorized | Fault | Safe, legible failure | Recovery or stop | `R-*`, `A-*` |
| Handoff | Downstream consumer receives output | Completed result | Usable interface/artifact | Rejection criteria | `D-*`, `A-*` |

Then test the draft with these questions:

- Can two competent planners read the spec and agree on what must exist, even if they choose different implementations?
- Does every required deliverable have content/behavior requirements and acceptance evidence?
- Are vague adjectives replaced by examples, thresholds, or observable judgments?
- Does the spec cover how failure is experienced, not merely successful behavior?
- Are priorities explicit (`must | should | could`) rather than implied by order?
- Are non-goals strong enough to prevent scope creep?

## `SPEC.md` template

Use `_assets/planning-templates/SPEC.md` (format contract `_assets/plan-viewer/FORMAT.md` §3; `plan_viewer.py --check` enforces it). It keeps the earlier sections (header, goal, actors, deliverables with the Stage-2 `Resources` column, requirements, scenarios, inputs, interfaces, quality, acceptance, constraints, non-goals, open questions, change history, sign-off).

What it adds: an optional `## Deliverable types` section with one `deliverable D-###` block per deliverable (type plus fields from the mockup catalog), so the plan page can draw a placeholder mockup; an untyped deliverable is shown as a plain tile.

## Approval gate

Before presenting, the spec draft must have passed the adversarial spec review (`planning-adversarial-review-protocol.md`, `SPEC` mode) and every substantive finding must be resolved by the user. Present the final draft with:

1. a five-line synopsis of the intended result;
2. the most consequential fixed decisions;
3. all blocking `Q-*` items;
4. all remaining `INFERRED` items;
5. a direct request to `APPROVE`, edit, or defer.

Do not approve if a blocking question remains unanswered. A non-blocking open question must name its future owner and the tasks it may block. After the baseline lock, an edit request becomes a spec delta: preserve the current locked version and follow `planning-spec-reconciliation-protocol.md` before issuing a replacement.

## Common failure modes

- **Solution leakage:** framework choices appear as requirements. Rewrite them as outcome properties or move them to Stage 3.
- **Feature list without use:** requirements exist but no actor/scenario explains why. Add scenario and downstream-use coverage.
- **Happy-path spec:** invalid or missing inputs have no defined behavior. Add boundary and failure scenarios.
- **Acceptance theater:** tests say “review for quality.” Replace with named evidence and an approver.
- **False precision:** invented numeric thresholds imply user choices. Mark `OPEN` or propose options explicitly.
- **Invisible exclusion:** adjacent work is assumed out of scope but not recorded. Add an `N-*` item.
- **In-place revision during execution:** the main spec changes with no durable record of the earlier promise. Restore the prior locked version, create a delta, obtain the required approval, and issue a new version.

## Worked example

For “a recurring weekly research brief,” the output spec fixes the brief's audience, decisions it supports, sections, evidence/provenance expectations, maximum reading time, handling of conflicting sources, late-data behavior, archive/search expectations, and pass/fail review. It does not choose a database, scheduler, model, email provider, or agent topology.
