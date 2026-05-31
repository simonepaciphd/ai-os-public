---
name: rr-response-memo-protocol
description: Turns a journal R&R — original editor letter + referee reports, the decision-annotated rr-revision-plan, and the revised manuscript — into a point-by-point response-to-reviewers memo, organized by reviewer. The agent drafts each entry from the user's annotated decision and verifies every manuscript locus against the revised paper; the user owns every stance. Second of two R&R-pipeline skills; consumes rr-revision-plan-protocol.
audience: public
version: 0.1
composed_with: [project-setup, rr-revision-plan-protocol]
---

# R&R Response-Memo Protocol

A four-phase skill that assembles the **response-to-reviewers memo** for a journal Revise & Resubmit. It ingests three inputs — the original editor decision letter and referee reports, the completed `rr-revision-plan` **annotated by the user with a decided response per point**, and the **revised** manuscript — and produces a single point-by-point memo organized **by reviewer**: each demand → the response the user takes, what was changed and **where in the revised manuscript** (page + named artifact, verified against the actual file), and the rationale; for demands declined or partially addressed, the reasoned justification.

The deliverable is the user's memo, drafted but never authored in substance. The agent's job is to (1) read the user's annotated decisions off the revision plan, (2) re-organize the plan's `Theory / Empirics / Minor` buckets back into reviewer order, (3) draft each entry in the user's voice from the decision the user annotated, (4) locate and **verify** every "I changed X on page Y" claim against the revised manuscript, and (5) check that every plan point maps to a memo entry. The agent **never originates or sharpens a stance** — especially on declined or pushed-back demands. Every response traces to an annotation the user wrote; where an annotation is missing or ambiguous, the agent surfaces it and waits.

Designed to compose with `rr-revision-plan-protocol` (its annotated output is this skill's primary input — the bridge artifact), `project-setup` (the memo is registered in `asset-registry.csv`; the session is logged in `interaction-log.csv`), and your own manuscript-drafting / voice workflow (which governs the memo's voice — match the manuscript's register and your prior memos; avoid AI-isms). It is the second and final skill of the two-skill R&R pipeline.

Governing principles: **user control** and **radical transparency** — see `{{LIBRARY_ROOT}}/skills/about-governing-principles.md`. Here that means: the agent drafts from the user's annotated decisions and verifies loci while the user owns every stance (every decline/partial framing is a sign-off point), and the memo records which model/version drafted it, is marked an agent draft pending review, and notes where the user overrode the draft.

---

## When to use

- The user invokes it directly once the revision is drafted and the `rr-revision-plan` has been annotated with a decided response per point, and they want the annotated plan + revised manuscript turned into a submission-ready response memo.
- As the downstream half of the R&R pipeline: to convert the demand-map produced by `rr-revision-plan-protocol` into the point-by-point memo, after the actual revisions exist.

Do not use when: the revision plan has **not** been annotated with the user's decisions (the agent cannot originate stances — stop and ask for the annotations); the revision has not yet been drafted (there is no revised manuscript to verify loci against — the loci would be fabricated); or the task is to *build the demand-map* in the first place (that is `rr-revision-plan-protocol`, upstream).

## Artifacts the skill produces

1. `<journalacronym>_response_memo_<YYYY-MM-DD>.md` — the response-to-reviewers memo, written inside the active project's submission folder tree (located and confirmed in Phase 0, not assumed). Markdown; the user ports it to the journal's submission format (.docx) separately.
2. A row in that project's `asset-registry.csv` (`asset_type = output`; creator `agent` or `mixed`; model metadata filled; `verification = not-verified` pending the user's review).
3. A row in that project's `interaction-log.csv` capturing the session.

## Universal rules

1. **Never originate a stance.** Every response traces to a decision the user annotated on the revision plan. Do not concede, push back, accommodate, or hedge on the agent's own judgment — no "the obvious response is", no invented justification for a decline. A plan point with no annotation, or an ambiguous one, goes to "Flagged for you"; the agent surfaces it and waits. There is no agent-decided response anywhere in this artifact.
2. **Organize by reviewer; invert the plan's buckets.** The revision plan is bucketed `Theory / Empirics / Minor` by paper flow; the memo runs by **reviewer** — `Reviewer #1`, `Reviewer #2`, `Reviewer #3`, in reviewer order, each reviewer's points in that reviewer's own ordering. The editor is addressed in the opening letter, not a separate section — *unless* the editor raised demands distinct from the referees', which then get their own entries.
3. **Paraphrase the demand into a thematic heading; do not quote the referee in the memo body.** Each entry opens with a short title in the user's words (e.g., "Donations as a signal to the state"), not the referee's verbatim text. The verbatim quotes live in the working material (the revision plan), not the memo. Open each response by conceding the legitimate part of the concern, then narrow to the response.
4. **Cite every change by a verified locus; never paste new text.** State what changed and where, in the past tense, by **page number + named artifact** ("I expanded Table 2 on page 24"; "amended my footnote on page 31"). Never paste new manuscript text into the memo; never write "see attached." **Verify every locus against the revised manuscript** — both error directions: do not assert a change that is not there, and do not miss a change the annotation claims. A claimed change that cannot be located goes to "Flagged for you"; do not invent a page or section.
5. **Decline / partial = substantive sign-off.** Draft the framing of every refusal or partial accommodation from the user's annotated decision and the evidence they point to, following the user's signature pattern: concede the concern → move the disagreement onto the evidence the referee can check → disclose any inconvenient prior result → keep it bounded, never adversarial, never "out of scope." Each decline/partial framing is a pause point — present it for sign-off before committing it.
6. **Coverage is exhaustive — no silent drops.** Every point in the revision plan maps to exactly one memo entry, or to an explicit "Flagged for you" item. Produce a coverage ledger (plan point → memo entry) at delivery. Flag any plan point with no corresponding response, and any memo entry with no plan precursor. Cross-reviewer demands (one plan point attributed to several referees): write the full response under the first reviewer who raised it, then cross-reference under the others ("As noted in my response to Reviewer #1…") — **expanding** the cross-reference whenever a later reviewer's framing needs separate justification, rather than a bare "see above."
7. **Match the voice; avoid AI-isms.** Draw the register from the revised manuscript and your prior response memos (the fixed scaffold; "I agree with the reviewer that…"; concede-then-evidence). Compose with your own voice/manuscript workflow for voice governance; hand the draft to `writer` for prose polish when it needs work beyond matching that register. No LLM tells (no "delve", "it is worth noting", "moreover"-stacking, hedge piles, empty summaries).
8. **Read-only on all inputs; record provenance.** Never edit, annotate, or move the editor letter, the referee reports, the revision plan, or the manuscript. The manuscript is an under-review artifact you must not edit. The memo's header records the drafting model/version and date, marks the file an agent draft pending the user's review, and notes where the user overrode the draft; `verification` stays `not-verified` until sign-off.

---

## Phase 0 — Intake

Goal: assemble and confirm the three inputs and the output target, and confirm the revision plan is annotated, before any drafting.

**Interview checklist:**

1. *"Point me to: the original editor letter + referee reports; the `rr-revision-plan` you have annotated with your decisions; and the revised manuscript (compiled PDF and source)."* If given a submission folder, Glob it and confirm the file set back to the user rather than assuming which file is which.
2. *"Confirm the plan is annotated with a decided response per point."* If it is not, **stop**: the agent cannot originate stances. Ask the user to annotate first, or to flag the points they want left open.
3. *"Which round is this — first R&R response, second, …?"*
4. *"Confirm where the memo should be written."* Propose the detected submission-folder path and the filename `<journalacronym>_response_memo_<YYYY-MM-DD>.md`; do not write outside a confirmed path.

**Action step:** lock the journal acronym, the round, today's date, the input paths, and the output path. Do not proceed until the inputs are located, the plan is confirmed annotated, and the output path is confirmed. All inputs are read-only from here on.

---

## Phase 1 — Ingest decisions and comprehend the revised manuscript

Goal: read the user's decisions off the annotated plan and build the manuscript map that makes locus verification accurate rather than asserted.

**Action step:**

1. Read the annotated revision plan. For each point, capture: its keyword title, its source attribution(s) (`R1`, `R2`, `Editor`), the verbatim referee/editor quote(s), the proposed locus, and **the user's annotated decision** (read holistically — the annotation format is flexible). Build the per-point demand → decision table that the memo is drafted from.
2. Flag, in a running list, any plan point whose decision annotation is missing or ambiguous. These are surfaced in "Flagged for you"; they are not filled in by the agent.
3. Record each point's reviewer attribution(s) — this is what lets Phase 2 invert the plan's buckets into reviewer order and handle cross-reviewer points.
4. Read the revised manuscript end to end (dispatch a read-only subagent if it is long). Verify loci against the **compiled PDF** for page numbers; consult the LaTeX/source for section and line detail. Build a compact map — section order, table/figure inventory, page anchors — so every "where" claim in Phase 2 can be checked against the real file.
5. If the manuscript map or any decision is uncertain enough to risk a mis-draft, surface it to the user before Phase 2; otherwise proceed.

---

## Phase 2 — Draft the memo entries, by reviewer

Goal: turn the demand → decision table into bucket-inverted, reviewer-ordered, locus-verified entries in the user's voice.

**Action step:**

1. **Invert** the plan's `Theory / Empirics / Minor` buckets into reviewer order: regroup every point under the reviewer(s) who raised it, and within each reviewer follow that reviewer's own point ordering (Rule 2).
2. For each demand, write a short **paraphrased thematic heading** (Rule 3), then draft the response **from the user's annotated decision** — open by conceding the legitimate concern, then state the response. Never originate or sharpen the stance (Rule 1).
3. For each change the decision claims, **verify the locus** against the revised manuscript map (Rule 4) and state it as a completed past-tense action with page + named artifact. A change that cannot be located → "Flagged for you"; do not invent a locus.
4. For **declined or partial** demands, draft the framing per the user's signature pattern — concede → move the disagreement onto the evidence → disclose inconvenient priors → keep it bounded (Rule 5). Mark each as a sign-off point.
5. Handle **cross-reviewer** points: full response under the first reviewer, cross-reference (expanded where separate justification is owed) under the others (Rule 6).
6. Draft the **opening letter**: salutation "Dear Editor and Reviewers,"; ¶1 thanks + manuscript title in quotes + that it was revised; ¶2 the overarching changes — flex the count and framing to the editor's **steering comments** in the decision letter (do not force a rigid "First / Second / Finally" if the editor emphasized a different number of headline changes); ¶3 a transition sentence into the point-by-point. Optional closing thanks.
7. Match the manuscript's register and your prior memos; avoid AI-isms (Rule 7). Hand to `writer` if prose polish is needed.

---

## Phase 3 — Coverage check, assemble, and deliver

Goal: prove no plan point was dropped, assemble the memo, and hand it back as a draft pending sign-off.

**Action step:**

1. **Coverage ledger.** Build the plan point → memo entry mapping. Confirm every plan point maps to exactly one entry or an explicit flag; flag any unmapped plan point and any memo entry with no plan precursor (Rule 6).
2. Assemble the memo per the *Output skeleton* below, with the provenance header.
3. Add the "Flagged for you" section: plan points with missing/ambiguous decisions, claimed changes that could not be located in the manuscript, and any decline/partial framing awaiting sign-off (Rules 1, 4, 5).
4. **Present the full assembled memo to the user for sign-off before writing the file** — pause specifically on missing decisions, unverifiable loci, and every decline/partial framing.
5. On sign-off, write to the path confirmed in Phase 0. Register per `project-setup`: add an `asset-registry.csv` row (creator `agent`/`mixed`, model metadata filled, `verification = not-verified`) and an `interaction-log.csv` row.
6. Deliver: tell the user it is an agent draft pending their review; point them to the "Flagged for you" section first; note that the memo paraphrases each demand (verbatim quotes remain in the revision plan) and that they should port the .md to the journal's submission format.

---

## Output skeleton

```
# Response to Reviewers — <paper short title>

**Journal:** <name>  ·  **R&R round:** <n>
**Inputs:** editor letter + referee reports (<files>); annotated revision plan (<file>); revised manuscript (<file>, <version / date>)
**Drafted by** <model id / version>, <YYYY-MM-DD>; read-only on all inputs.
**Status:** agent draft — pending review and correction by the user. User overrides logged inline as [USER: …].

---

Dear Editor and Reviewers,

<¶1 — thanks; "<manuscript title>"; that it was revised.>
<¶2 — the overarching changes; count and framing flexed to the editor's steering comments.>
<¶3 — transition: "Below, I provide detailed responses to each of the reviewers' comments…">

---

## Reviewer #1

### <Paraphrased thematic heading>
<Response in the user's voice, drafted from their annotated decision: concede the
concern, then state what was done and why. Change cited by verified locus.>
*Change: <what changed>, <page / §, verified against the revised manuscript>.*

### <Paraphrased thematic heading>  [decline / partial — signed off <date>]
<Concede → move disagreement onto the evidence → disclose any inconvenient prior result → bounded.>
*Change: <partial change + locus>, or — where no change — the reasoned justification.*

## Reviewer #2

### <Paraphrased thematic heading>
<As noted in my response to Reviewer #1's point on <X> — [expanded where separate justification is owed].>

...

## Editor   <only if the editor raised demands distinct from the referees'>

...

---

## Coverage ledger  <delivered with the draft; not part of the submitted memo>
| Plan point (bucket · title · sources) | Memo entry | Status |
|---|---|---|
| Empirics · Treatment scaled to population · R1, R2 | R1 §"…" | answered |
| ... | ... | flagged — no decision annotated |

## Flagged for you
- <plan point with missing/ambiguous decision — needs your stance before it can be drafted>
- <claimed change not locatable in the revised manuscript — verify or correct the locus>
- <decline/partial framing awaiting your sign-off>
```

---

## Handoff with other skills

- `rr-revision-plan-protocol` (upstream): its annotated output is this skill's primary input. The plan supplies the buckets, keyword handles, verbatim quotes, attributions, and loci; **the user's annotations on it supply the decided responses**; this skill inverts the buckets into reviewer order and drafts the memo. Coverage is checked against the plan so nothing the plan catalogued is dropped.
- `project-setup`: the memo is registered in the project's `asset-registry.csv` (Rule 4 of the setup protocol) and the session is logged in `interaction-log.csv` (Rule 5).
- Your own manuscript-drafting / voice workflow: governs the memo's voice — match the manuscript's register; consulted to keep the prose in the user's voice, never to edit the manuscript.
- `writer` (persona): take the handoff for prose polish when the memo's register needs work beyond matching the manuscript. The researcher persona drafts the memo's substance but does not author prose.

## Common failure modes

- **Agent originates a stance.** The cardinal failure. Symptom: an entry contains a concede/push-back the user never annotated, or an invented justification for a decline. Recovery: strip the entry back to the annotated decision; if there is no annotation, move the point to "Flagged for you" and ask.
- **Fabricated locus.** Symptom: "I revised Section 4.2 on page 19" where no such change exists in the revised manuscript, or a page number that does not match the compiled PDF. Recovery: re-verify against the manuscript map; if the change cannot be located, flag it rather than asserting it — both error directions (no phantom changes, no missed ones).
- **Pasted manuscript text / "see attached".** Symptom: the memo reproduces new paragraphs of the paper instead of citing where they live. Recovery: replace with a past-tense locus citation (Rule 4).
- **Silent drop.** Symptom: a plan point — often the referee's deepest conceptual objection — has no memo entry and no flag. Recovery: the coverage ledger must account for every plan point; re-map and either answer or flag.
- **Bucket leakage into the memo.** Symptom: the memo is organized Theory/Empirics/Minor (the plan's structure) instead of by reviewer. Recovery: invert per Rule 2 — regroup by reviewer in reviewer order.
- **Referee quoted in the memo body.** Symptom: verbatim referee text pasted into an entry. Recovery: paraphrase into a thematic heading; the quotes stay in the revision plan (Rule 3).
- **Collapsed cross-reference.** Symptom: a cross-reviewer point reduced to a bare "see above" when the later reviewer's framing needed its own justification. Recovery: expand the cross-reference (Rule 6).
- **AI-isms.** Symptom: the memo reads as genre-average LLM prose, not the user's voice. Recovery: re-draft against the manuscript's register and prior memos; compose with your own voice/manuscript workflow; hand to `writer`.

## Worked example

A second-round R&R response is due. **Phase 0:** the user points to the submission folder; the agent confirms it holds the editor letter + three referee reports, `bjps_revisions_plan_2026-07-10.md` **annotated** with a decision under each point, and `manuscript_v5.pdf` + the LaTeX source, and that the memo should be written there as `bjps_response_memo_2026-07-12.md`. The plan is confirmed annotated. **Phase 1:** the agent reads the annotated plan, building a demand → decision table, and notes that one Minor point (R2, a citation request) has no decision annotated — it goes to the running flag list. It reads `manuscript_v5.pdf` and maps section order, tables, and page anchors. It records that the plan's `Empirics` point "Treatment scaled to population" is attributed to both R1 and R2. **Phase 2:** the agent inverts the buckets into reviewer order; under Reviewer #1 it writes the heading **"Population scaling of the treatment"**, drafts the response from the user's annotation (which decided to re-operationalize and report the new positive result while disclosing the old null), opens by conceding R1's concern, and verifies the change — "I added the logged-treatment table to Appendix B (Table B3, page 41)" — against the PDF, where Table B3 does appear on page 41. Because R2 raised the same point, the full response sits under R1 and a cross-reference appears under R2, expanded with the one distinction R2 added. For a declined point — R3's request for an additional mechanism test the user decided not to run — the agent drafts the refusal per the user's annotated reasoning (concede the alternative is plausible → show two existing results it cannot explain → cite their loci), and marks it a sign-off point. **Phase 3:** the coverage ledger shows every plan point mapped except the un-annotated R2 citation request, which is flagged. The agent presents the full draft, pausing on the un-annotated citation point and on the R3 refusal framing; the user signs off (correcting one sentence of the R3 framing, logged inline as `[USER: …]`). The memo is written, registered `not-verified`, and delivered as an agent draft.
