---
name: rr-revision-plan-protocol
description: Turns a journal R&R (editor letter + referee reports + manuscript) into a reviewer-attributed, reasoned-summary revision plan — bucketed Theory / Empirics / Minor, ordered by paper flow. The agent summarizes and locates each demand; the user decides every response. First of two R&R-pipeline skills; feeds rr-response-memo-protocol.
audience: public
version: 0.1
composed_with: [project-setup]
---

# R&R Revision-Plan Protocol

A four-phase skill that ingests the three artifacts of a journal Revise & Resubmit — the editor's decision letter, the referee reports, and the submitted manuscript — and produces a single structured **revision plan**: every reviewer/editor demand decomposed into a discrete point, summarized in reasoned prose grounded in the actual paper, attributed to its source(s), and located in the manuscript. The plan is organized into `Theory / Empirics / Minor` buckets and ordered within each bucket by the paper's own flow.

The deliverable is a **reasoned summary, not a categorization and not a set of proposed responses.** The agent's job is to make each demand legible — what is being asked, what part of the paper's theory/design/findings/robustness it targets, what is at stake, how it relates to other demands — and to surface ambiguity. The user decides how to react to every request. This skill never drafts, proposes, or implies a response, stance, or revision.

Designed to compose with `project-setup` (the plan is registered in the project's `asset-registry.csv`; the session is logged in `interaction-log.csv`) and your own manuscript-drafting workflow (which governs the manuscript it reads). It is the first of a two-skill R&R pipeline: its output is the structured demand-map that `rr-response-memo-protocol` later builds the point-by-point response memo on top of.

Governing principles: **user control** and **radical transparency** — see `{{LIBRARY_ROOT}}/skills/about-governing-principles.md`. Here that means: the agent summarizes and locates each demand while the user decides every response (nothing is agent-resolved), and the plan records which model/version drafted it, marked an agent draft pending the user's review and correction.

---

## When to use

- The user invokes it directly when an R&R is in hand and they want the referee reports turned into a structured, scannable map of what is being asked before they decide how to revise.
- Before substantive revision work begins, to triage demands by where they sit in the paper and how much judgment each will need.
- As the upstream half of the R&R pipeline: to produce the demand-map that `rr-response-memo-protocol` will consume.

Do not use when: the task is to *draft the response memo* (that is `rr-response-memo-protocol`, downstream of the actual revisions); the task is a fresh submission with no referee reports; or the user wants the agent to decide how to respond to demands (the agent never does — it summarizes).

## Artifacts the skill produces

1. `<journalacronym>_revisions_plan_<YYYY-MM-DD>.md` — the revision plan, written inside the active project's submission folder tree (located and confirmed in Phase 0, not assumed).
2. A row in that project's `asset-registry.csv` (`asset_type = output` or `reference`; creator `agent` or `mixed`; model metadata filled; `verification = not-verified` pending the user's review).
3. A row in that project's `interaction-log.csv` capturing the session.

## Universal rules

1. **Summarize, never decide.** Produce a reasoned summary of each demand. Never propose, draft, or imply how the user should respond — no "concede / push back / accommodate", no suggested wording, no planned change. Every response decision is the user's, taken downstream. There is no decision field in this artifact.
2. **Quote verbatim, attribute exactly.** Every point carries the exact text of the demand, attributed to its source (`R1`, `R2`, `Editor`, …). Never substitute a paraphrase for the quote. Editor remarks bearing on a point are quoted within that point, alongside the referee quotes.
3. **Reason from the manuscript, not from genre priors.** The summary of what each demand targets and the "where in the paper" locus must be grounded in the manuscript actually read in Phase 1 — not a plausible guess about what a paper of this kind contains. If you cannot locate what a demand refers to, flag it; do not invent a locus.
4. **Bucket, then order by paper flow.** Three buckets — `Theory`, `Empirics`, `Minor`. `Minor` is purely procedural: citation fixes, typos, formatting, small content additions. Within each bucket, order points by the paper's own section flow (intro → theory → data/design → results → robustness → conclusion).
5. **Consolidate overlaps.** When more than one source raises the same demand, write one point and attribute all sources; cross-reference rather than duplicate. Do not over-consolidate — two genuinely distinct asks that happen to be topically near stay separate.
6. **Surface uncertainty at delivery, don't bury it.** Ambiguous demands and anything you could not locate in the manuscript go in a dedicated "Flagged for you" section delivered with the first draft. Do not resolve an ambiguity by guessing the reviewer's intent.
7. **Read-only on all three inputs.** Never edit, annotate, or move the editor letter, the referee reports, or the manuscript. The manuscript is an under-review artifact you must not edit; this skill only reads it.
8. **Record provenance.** The plan's header records the drafting model/version and the date, and marks the file an agent draft pending the user's review and correction. `verification` in the asset registry stays `not-verified` until the user signs off.

---

## Phase 0 — Intake

Goal: assemble and confirm the three inputs and the output target before any analysis.

**Interview checklist:**

1. *"Point me to the editor's decision letter, the referee reports, and the version of the manuscript under review."* (If given a submission folder, Glob it and confirm the file set back to the user rather than assuming which files are which.)
2. *"Which round is this — first R&R, second, …?"*
3. *"Confirm where the plan should be written."* Propose the detected submission-folder path and the filename `<journalacronym>_revisions_plan_<YYYY-MM-DD>.md`; do not write outside a confirmed path.

**Action step:** lock the journal acronym, the round, today's date, the three input paths, and the output path. Do not proceed until the inputs are located and the output path is confirmed. All three inputs are read-only from here on.

---

## Phase 1 — Comprehend the manuscript

Goal: build the internal map of the paper that makes the per-demand summaries and the locus-mapping accurate rather than genre-average.

**Action step:** read the manuscript end to end (dispatch a read-only subagent for this if the paper is long). Produce a compact internal map — not necessarily written into the plan file:

- the theory / central argument;
- the identification or empirical design;
- the main findings;
- the robustness structure;
- the **section order** and an inventory of sections, tables, and figures (this is what lets Phase 2 order within buckets by paper flow and assign each demand a real locus).

If the paper is unfamiliar enough that the map is uncertain, surface the map to the user for a quick check before Phase 2; otherwise proceed.

---

## Phase 2 — Decompose and summarize the demands

Goal: turn the editor letter and referee reports into bucketed, summarized, attributed points.

**Action step:**

1. Extract every discrete demand from each referee report and the editor letter at the granularity of distinct *asks* — a single paragraph often carries several; a single sentence sometimes carries none.
2. Consolidate demands raised by more than one source into one point, attributing all sources (Rule 5).
3. Give each point a short, scannable **keyword title**.
4. Bucket each point into `Theory`, `Empirics`, or `Minor` (Rule 4).
5. Order the points within each bucket by the paper's section flow (from the Phase-1 map).
6. For each point, write: a short **reasoned summary** grounded in the manuscript (what is asked, what it targets, what is at stake, how it links to sibling points); the **proposed locus** in the paper where it lands; and the **exact verbatim quote(s)** from each source, including any editor remark that bears on the point.
7. Do **not** write a response, stance, decision, or planned change anywhere (Rule 1).

---

## Phase 3 — Assemble and deliver

Goal: write the plan file, register it, and hand it back as a draft pending review.

**Action step:**

1. Assemble the plan per the *Output skeleton* below, with the provenance header.
2. Add the "Flagged for you" section: ambiguous demands, and anything you could not locate in the manuscript (Rule 6).
3. Write to the path confirmed in Phase 0.
4. Register per `project-setup`: add an `asset-registry.csv` row (creator `agent`/`mixed`, model metadata filled, `verification = not-verified`) and an `interaction-log.csv` row.
5. Deliver: tell the user it is an agent draft pending their review; point them to the "Flagged for you" section first; note that once they have decided their responses and revised the manuscript, this plan is the input to `rr-response-memo-protocol`.

---

## Output skeleton

```
# Revision Plan — <paper short title>

**Journal:** <name>  ·  **Decision:** <major / minor revision>  ·  **R&R round:** <n>
**Inputs:** editor letter (<file>); referee reports (<files>); manuscript (<file>, <version / date>)
**Analysis:** drafted by <model id / version>, <YYYY-MM-DD>; read-only on all inputs.
**Status:** agent draft — pending review and correction by the user.
**Editor's overall disposition (verbatim, if stated):** "<…>"

---

## Theory

### <Keyword title>  — R1, R2
<2–4 sentence reasoned summary: what is asked; what part of the theory/argument it
targets; what is at stake; how it links to other points. Grounded in the manuscript.>
*Where in paper:* <section / subsection>
> **R1:** "<exact quote>"
> **R2:** "<exact quote>"
> **Editor:** "<exact quote, if the editor commented on this point>"

### <Keyword title>  — R3
...

## Empirics

### <Keyword title>  — R1
<reasoned summary>
*Where in paper:* <§ / Table / Figure / page>
> **R1:** "<exact quote>"

...

## Minor

### <Keyword title>  — R2
<one-line summary — these are procedural: citations, typos, formatting, small additions>
*Where in paper:* <locus>
> **R2:** "<exact quote>"

...

---

## Flagged for you — ambiguities & uncertainties

- <demand / point>: <why it is ambiguous, or what could not be located in the manuscript, or what needs your read before it can be summarized cleanly>
```

---

## Handoff with other skills

- `rr-response-memo-protocol` (downstream): consumes this plan as its structured demand-map. The plan supplies the buckets, keyword handles, verbatim quotes, attributions, and loci; the memo protocol adds the user's decided responses and the actual revisions (read off the revised manuscript).
- `project-setup`: the plan file is registered in the project's `asset-registry.csv` (Rule 4 of the setup protocol) and the session is logged in `interaction-log.csv` (Rule 5).
- Your own manuscript-drafting workflow: governs the manuscript this skill reads; consulted only to understand paper structure, never to edit prose.
- `lit-review-protocol`: not normally invoked — external grounding is out of scope for this skill (its source of truth is the reports and the manuscript). Invoke only if a demand explicitly turns on whether a literature exists and the user asks for that check.

## Common failure modes

- **Agent drafts a response.** The cardinal failure. Symptom: a point contains "I will…", "we should…", "the obvious fix is…", or a concede/push-back stance. Recovery: strip every point back to summary + locus + quote; the decision is the user's.
- **Paraphrase in place of quote.** Symptom: no verbatim referee text, so the user cannot check the summary against what was actually written. Recovery: re-insert exact quotes for every point (Rule 2).
- **Genre-average locus mapping.** Symptom: "Where in paper" cites sections or tables that do not exist in this manuscript. Recovery: re-read the Phase-1 map; if a demand's target genuinely cannot be located, move it to "Flagged for you" rather than guessing.
- **Missed demands.** Symptom: a multi-ask referee paragraph collapsed to one point. Recovery: re-decompose at the sentence level (Phase 2, step 1).
- **Over-consolidation.** Symptom: two distinct asks merged because they were topically near, hiding one of them. Recovery: split; consolidate only true duplicates (Rule 5).
- **Minor-bucket inflation.** Symptom: a substantive theory/design ask parked in `Minor` to shorten the plan. Recovery: `Minor` is only citations, typos, formatting, and small content additions; anything requiring judgment belongs in `Theory` or `Empirics`.

## Worked example

A second-round R&R arrives. Phase 0: the user points to the submission folder; the agent confirms it holds `Editor.docx`, `Reviewer 1–3.docx`, and `manuscript_v4.pdf`, and that the plan should be written there as `ajps_revisions_plan_2026-06-02.md`. Phase 1: the agent reads the manuscript and maps it — argument, identification strategy, four results tables, an appendix of robustness checks, section order intro→theory→data→results→robustness→conclusion. Phase 2: from R1's third paragraph the agent extracts a demand —

> R1: "I'd like to see the treatment measure be defined relative to some indicator of municipality size... if the author disagrees, a defense is surely needed."

It gives the point the title **Treatment scaled to population**, files it under `Empirics`, places it after the measurement subsection in paper order, and writes a three-sentence summary: the demand targets the core identifying measure; it bears directly on the central results table; R2's "size confound" remark raises the same concern, so the two are consolidated with both attributed. The agent writes the summary and locus, quotes R1 and R2 verbatim, and stops — it does **not** suggest logging the variable, re-running the analysis, or conceding the point. Phase 3: the plan is written, registered in `asset-registry.csv` as `not-verified`, and delivered with a "Flagged for you" note that one of R3's comments ("the framing feels off") was too vague to locate in the manuscript and needs the user's read. The user then decides each response; later, this plan feeds `rr-response-memo-protocol`.
