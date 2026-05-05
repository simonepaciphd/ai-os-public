---
name: literature-error-check-protocol
description: Two-pass pre-publication audit of every bibliography entry against how it is actually used in a paper. Pass 1 is broad-and-shallow (existence + abstract); Pass 2 is deep-and-scoped (full-text retrieval). Output is a calibrated table of inexistent / misused error probabilities.
audience: public
version: 0.1
---

# Literature Error-Check Protocol

A two-pass, pre-publication audit of every bibliography entry against how it is actually used in a paper. Pass 1 is broad and shallow (existence + abstract check across all entries); Pass 2 is deep and scoped (full-text retrieval for entries flagged in Pass 1). Each pass is a separate agent invocation, with user review in between. Output: a printed-and-saved Markdown table, one row per entry, with calibrated probabilities for `inexistent` and `misused` errors plus metadata mismatches, sorted by cumulative error probability.

Designed to compose with a paper-writing protocol the user maintains (consumed at the end of paper drafting) and `lit-review-protocol.md` (a sibling, but for *discovering* literature, not auditing it). Distinct from both — this skill never gathers new sources and never edits paper content.

Governing principles: **user control** and **radical transparency** — see {{LIBRARY_ROOT}}/skills/about-governing-principles.md. The skill produces a report and proposes a deep-audit set; it does not modify the paper, the bibliography, or the project ledger. Every probability the agent emits is anchored in an explicit calibration band (see Universal Rule 3) so that the report's claims are themselves auditable.

---

## When to use

- **Keyword triggers:** "check bibliography", "pre-submission citation audit", "literature error check", "audit my cites".
- **Project-ledger signal:** project `current_phase ∈ {pre-submission, pre-revise-and-resubmit}`.
- **Manual invocation:** before any external-facing release of a paper, op-ed, book chapter, or grant proposal that carries a bibliography.

Do not use when:

- The task is *gathering* new literature for an argument (use `lit-review-protocol.md` instead).
- The paper is at draft stage and the bibliography is still volatile (running this too early wastes lookups).
- The artifact has fewer than ~5 cites (audit by hand; the table-output overhead isn't worth it).
- The bibliography is in a non-standard format the skill cannot parse (e.g., footnoted citations in a humanities chapter without a `.bib`). Flag and refuse rather than guess.

## Artifacts the skill produces

1. **Printed Markdown table in chat**, one row per bibliography entry, sorted by `cum_err` descending. Columns: `key`, `found`, `URL`, `P(inexistent)`, `P(misused)`, `other_errors`, `cum_err`.
2. **Saved report file** at `<project_root>/appendix/literature-error-check-<YYYY-MM-DD>.md` if an `appendix/` directory exists. If it does not, the agent **stops and asks the user where to save** — it does not silently fall back to project root. The saved file mirrors the chat table and adds:
   - Pass identifier (`pass: 1` or `pass: 2`).
   - Per-entry evidence trail: which lookup hit, what abstract/full-text was retrieved, what claim sentence was matched against.
   - Proposed deep-audit set (Pass 1 only).
3. **Updated saved report** at the same path on Pass 2 (overwrites Pass 1 with `pass: 2` and richer evidence per audited row; preserves Pass 1 rows for entries not deep-audited).

The skill never writes to the `.tex`, `.bib`, project ledger, or any other paper-content file.

## Universal rules

1. **Two passes, two invocations.** Pass 1 and Pass 2 are run as separate agent invocations with user review between. Do not collapse them into one call, even when token budget would allow it — the human-in-the-loop is the calibration.
2. **No content edits.** This skill writes only its own report file. It never modifies the `.tex`, the `.bib`, or any other artifact.
3. **Anchor every probability to a band.** Pass 1 probabilities come from the calibration table in Phase 1, not from free-form judgment. Pass 2 probabilities come from explicit full-text evidence with a citation in the evidence trail. No free-floating numbers like `P = 0.73`.
4. **Cap `P(misused)` at 0.70 in Pass 1.** An abstract is not enough evidence to assert misuse with higher confidence. Going above 0.70 requires Pass 2 full-text evidence.
5. **Aggregate per-entry as max-across-uses.** If an entry is cited multiple times, the entry's `P(inexistent)` and `P(misused)` are the *maxima* across cite sites, not the means.
6. **Disconfirm before ratifying.** Once an entry is flagged suspicious, try harder to find it (more name variants, accent stripping, journal-acronym expansion, alternate years) before ratifying the flag. The skill's failure mode is over-confident false positives.
7. **Negotiate the Pass 2 batch size with the user after Pass 1.** There is no fixed cap. After printing the Pass 1 table and proposed deep-audit set, the agent asks the user how many of those entries to deep-audit in this invocation, and the user decides based on the Pass 1 output (severity distribution, time available, retrieval feasibility). Never proceed into Pass 2 without an explicit batch size.
8. **Pause only at start and end of each pass.** No mid-pass narration. The agent runs Pass 1 (or Pass 2) silently from confirmation to printed table.
9. **Never claim a source is non-existent on a single lookup.** Mark `not-found` only after Crossref *and* OpenAlex *and* Semantic Scholar *and* a normalized-variant retry have all missed.

---

## Phase 0 — Pre-flight

Goal: confirm inputs and which pass is being run.

**Interview checklist:**

1. *"Which pass — Pass 1 (broad) or Pass 2 (deep)?"*
2. *"Confirm the project root. Default: current working directory."*
3. *"Confirm the main `.tex` file. Default: `main.tex` at project root."*
4. *"Confirm the `.bib` file location. Default: scan `\bibliography{...}` and `\addbibresource{...}` in the main `.tex` to discover it."*
5. *(Pass 2 only)* *"Path to the Pass 1 report file. Default: most recent `literature-error-check-*.md` under `appendix/`."*
6. *(Pass 2 only)* *"Deep-audit set — accept the proposed set from Pass 1, or revise."* The agent prints Pass 1's proposed set, then waits.
7. *(Pass 2 only)* *"How many of those entries to deep-audit in this invocation?"* No default — the user picks the batch size based on the Pass 1 output. See Universal Rule 7. If the requested batch is larger than the agent judges feasible in one call, raise the concern but defer to the user.

**Action step:**
- Verify all paths exist. If anything is missing, stop and ask — do not guess.
- Verify the bib file parses (read it; confirm at least one entry); if parse fails, stop and ask.
- For Pass 2: load the Pass 1 report and reconstruct the per-entry state.

---

## Phase 1 — Pass 1: broad existence + abstract audit

Goal: for every bibliography entry, verify the source exists and check the cited abstract against the paper's claim.

**No interview** — this phase runs silently from Phase 0 confirmation to Phase 2 output.

**Action step:**

### 1.1 Extract the bibliography
Parse the `.bib` file. For each entry capture: `key`, `authors`, `year`, `title`, `venue` (journal / booktitle / publisher), `DOI` (if present), `URL` (if present), `pages` (if present), `edition` (if present).

### 1.2 Extract cite sites
Walk every `.tex` file under the project root, including those reached by `\input{...}` and `\include{...}` chains from the main file. For each `\cite{...}` family command (`\cite`, `\citep`, `\citet`, `\citeauthor`, `\citeyear`, `\textcite`, `\parencite`, `\autocite`, with or without `[...]` arguments), record:
- the cite key
- the file path and line
- the **claim sentence**: the full sentence containing the `\cite{...}`. If the sentence is shorter than ~10 words, also include the prior sentence for context.

A single `\cite{a,b,c}` produces three cite sites.

### 1.3 Run the lookup chain per entry
For each unique cite key with a matching `.bib` entry, run lookups in order, stopping at first hit:

1. **DOI resolution** (if `DOI` present in `.bib`): resolve via `doi.org` / Crossref. Pull metadata + abstract.
2. **Crossref title + first-author + year search.**
3. **OpenAlex title + first-author + year search.**
4. **Semantic Scholar title + first-author + year search.**
5. **Normalized-variant retry**: strip accents, expand common journal acronyms, swap Anglicized author surnames, try `±1` year. (Disconfirmation step per Universal Rule 6.)
6. If still nothing: mark `found = not-found`.

If any lookup hits, set `found = located` and capture: canonical URL (DOI preferred, else stable platform URL), retrieved metadata, retrieved abstract.

### 1.4 Score `P(inexistent)`
Apply the calibration table:

| Evidence | `P(inexistent)` |
|---|---|
| DOI resolves cleanly | 0.05 |
| Found via title+author+year, no DOI | 0.15 |
| Found, but title differs substantially from `.bib` title | 0.50 |
| Not found across all four lookups + variant retry | 0.85 |
| Not found, *and* author-name pattern is LLM-typical (common given+family, no other publications visible in OpenAlex) | 0.95 |

### 1.5 Score `P(misused)` per cite site, then aggregate
For each cite site of an entry that was located, compare the **claim sentence** against the **retrieved abstract**:

| Evidence | `P(misused)` per site |
|---|---|
| Abstract is clearly on-topic for the claim | 0.10 |
| Found via title+author match, abstract on-topic | 0.20 |
| Abstract is *topically mismatched* with the claim (different field, different question, different population) | 0.70 |
| Found by author+year only, title differs substantially | 0.40 |
| Entry is `not-found` | n/a (already captured by `P(inexistent)`) |

Cap at 0.70 per Universal Rule 4. **Aggregate per entry as max across cite sites** per Universal Rule 5.

### 1.6 Detect `other_errors`
Compare `.bib` metadata against retrieved metadata. Flag — do not auto-correct — any of:

- Year mismatch.
- Author name divergence beyond accents/transliteration.
- Title differs in substance (not in capitalization or punctuation).
- Venue mismatch (different journal, different publisher).
- Page-range mismatch.
- Edition mismatch (where retrievable).
- DOI mismatch (between `.bib` and Crossref).

Per Universal Rule 6: if `.bib` and the lookup disagree, flag *both* values; never auto-pick one as canonical.

### 1.7 Compute `cum_err`
`cum_err = min(1.0, P(inexistent) + P(misused))`. This is the table sort key.

---

## Phase 2 — Pass 1 output

Goal: print and save the Pass 1 report; propose a deep-audit set; end the invocation.

**Action step:**

### 2.1 Print the table to chat
Sort entries by `cum_err` descending. Print as a Markdown table. Column order: `key | found | URL | P(inexistent) | P(misused) | other_errors | cum_err`. Truncate long URLs with `…`; truncate long `other_errors` lists to top 3 with a count of remaining.

### 2.2 Save the report
Write to `<project_root>/appendix/literature-error-check-<YYYY-MM-DD>.md` if `appendix/` exists. If it does not, **pause and ask the user where to save** (Universal Rule + "Artifacts the skill produces" item 2). Do not silently fall back. File structure:

```markdown
---
pass: 1
date: YYYY-MM-DD
project_root: <path>
main_tex: <path>
bib_file: <path>
n_entries: <int>
n_cite_sites: <int>
---

# Literature Error-Check — Pass 1

## Table
<the same table printed to chat>

## Proposed deep-audit set
<list of keys with cum_err >= 0.50, formatted as a comma-separated cite-key list ready to paste into Pass 2 Phase 0>

## Evidence trail
### <key 1>
- found: <located | not-found>
- lookup hit: <crossref | openalex | semanticscholar | none>
- URL: <...>
- abstract retrieved: <yes/no, and the abstract text or "n/a">
- cite sites:
  - <file:line> — claim sentence: "<...>"
  - ...
- P(inexistent) reasoning: <which band, why>
- P(misused) reasoning: <per-site bands, max>
- other_errors: <list with the .bib value vs lookup value>

### <key 2>
...
```

### 2.3 Propose the deep-audit set
Print to chat, after the table:

> **Proposed deep-audit set (cum_err ≥ 0.50):** `key1, key2, …` (`N` entries).
> Confirm, revise, or sub-set this list. How many do you want deep-audited in the next invocation? (No fixed cap — set the batch size based on this output. See Universal Rule 7.) Paste the final list into Pass 2's Phase 0.

End of invocation. The agent does not run Pass 2 in the same call.

---

## Phase 3 — Pass 2: deep full-text audit

Goal: for the flagged subset, retrieve full text and verify each cite site directly. Replaces Pass 1 probabilities with full-text-grounded ones.

**Pre-condition:** Phase 0 confirmed the deep-audit set and the batch size for this invocation (Universal Rule 7: batch size is negotiated, not capped).

**No interview during execution** — runs silently from Phase 0 confirmation to Phase 4 output.

**Action step:**

### 3.1 Retrieve full text per audited entry
For each key in the deep-audit set, attempt full-text retrieval in order:

1. **Open-access copy via Crossref `link` / `unpaywall`** (if available).
2. **OpenAlex `open_access` URL.**
3. **Semantic Scholar `openAccessPdf`.**
4. **Publisher landing-page** (DOI resolution) — only metadata + abstract; do not paywall-bypass.
5. **arXiv / SSRN / institutional repository** if author preprint exists.

If full text is retrieved, set `found = full-text` for that row. If not, leave `found = located` and note in evidence trail that Pass 2 could not improve on Pass 1; Pass 2 probabilities for that row remain unchanged from Pass 1.

### 3.2 Verify each cite site against full text
For each cite site (claim sentence) of each audited entry:

- Search the full text for evidence supporting the claim. Use semantic search (paraphrase tolerance), not exact-string match.
- Classify the cite as: `supported`, `not-found-in-text`, `contradicted`, or `unverifiable-without-domain-context`.

### 3.3 Update probabilities
Re-score with full-text evidence:

| Evidence | `P(inexistent)` | `P(misused)` |
|---|---|---|
| Full text retrieved, claim **supported** | 0.05 | 0.05 |
| Full text retrieved, claim **not found** | 0.05 | 0.85 |
| Full text retrieved, claim **contradicted** | 0.05 | 0.95 |
| Full text retrieved, **unverifiable** (claim depends on external context) | 0.05 | flag, leave at Pass 1 value |
| Full text **not retrieved** | unchanged | unchanged |

Apply max-across-sites aggregation per Universal Rule 5. The 0.70 cap (Universal Rule 4) does **not** apply to Pass 2 — full text is the evidence the cap was guarding against.

### 3.4 Reflag `other_errors` if full-text reveals new mismatches (e.g., page numbers, edition).

---

## Phase 4 — Pass 2 output

Goal: print and save the updated report; end the invocation.

**Action step:**

### 4.1 Print the updated table to chat
Same column order. Audited rows show updated probabilities; non-audited rows keep their Pass 1 values. Sort by `cum_err` descending.

### 4.2 Save the updated report
Overwrite (or version with a `-pass2` suffix if the user prefers; default = overwrite) at the same path the Pass 1 report was saved to (read from Phase 0). If that path is no longer writable or has moved, pause and ask. File frontmatter `pass: 2`. Evidence trail for audited rows now includes:

- full-text retrieval source
- per-site verification verdict (`supported` / `not-found` / `contradicted` / `unverifiable`)
- the textual passage from the source that grounds (or fails to ground) the claim

### 4.3 Print a one-paragraph summary to chat
Format:

> **Pass 2 summary:** Audited `N` entries. `X` confirmed clean, `Y` confirmed misused, `Z` confirmed inexistent, `W` unverifiable. Updated table above; full evidence trail at `<path>`.

End of invocation. No further action — the user decides what to do with the findings (correct cites, swap sources, delete claims).

---

## Handoff with other skills

- **A paper-writing protocol the user maintains** — this skill is the late-stage QA pass *after* paper-writing has produced the bibliography and cite sites. Run after the paper is otherwise submission-ready.
- **`lit-review-protocol.md`** — sibling, not parent: run a lit review *before* writing to discover sources; run literature-error-check *after* writing to audit how those sources are used.
- **`project-setup.md`** — when invoked inside a project that uses `project-setup`'s registry, the saved report file should be added to `asset-registry.csv` with `asset_type = report` and `creator = mixed`. (Not required for invocations outside the project-setup convention.)
- **`security-officer-protocol.md`** — invoke if the agent finds itself drifting toward confident false positives (e.g., flagging an entire bibliography as "mostly hallucinated" without evidence). The officer is diagnostic; authorship of the report stays with this skill.

## Common failure modes

- **Confident "misused" from abstract alone.** Symptom: Pass 1 marks `P(misused) = 0.70` for many entries on weak abstract evidence. Recovery: Universal Rule 4 caps the band; if the agent feels strongly about a row, it must defer to Pass 2 full-text.
- **Treating Google Scholar snippets as authoritative.** Snippets are scrape-fragile and paragraph-truncated. Recovery: this skill does not use Google Scholar in the lookup chain. If you find yourself adding it in Pass 2, restrict to author preprint discovery, not claim verification.
- **False `not-found`s from metadata variants.** Common causes: missing accents, transliterated surnames, journal acronyms, edition vs printing, year off-by-one. Recovery: Universal Rule 6 — variant retry before declaring `not-found`. If still failing, mark `not-found` *and* note the variants tried in the evidence trail.
- **Stale Zotero records spawning spurious `other_errors`.** The `.bib` may lag behind the canonical Crossref record. Recovery: flag both values; never auto-pick one. The user decides which is right.
- **Pass 2 token-budget blowout.** Symptom: deep-auditing too many entries in one call, agent hits a context limit mid-pass or produces shallow per-entry evidence. Recovery: Universal Rule 7 — the batch size is negotiated with the user *after* Pass 1, based on what came out. If a single invocation feels too large, split into multiple Pass 2 calls.
- **Confirming the agent's prior.** Once the agent flags an entry, it tends to retrieve evidence that confirms the flag. Recovery: Universal Rule 6 — try harder to *disconfirm* before ratifying. In Pass 2, search the full text both for supporting and for contradicting passages, and report whichever is stronger.
- **Over-running the audit.** Symptom: skill applied to a draft-stage paper with a still-volatile bibliography, producing a report that's stale within a week. Recovery: the "do not use when" block — wait until pre-submission.

## Worked example

Toy paper with 4 cite keys: `smith2010`, `nguyen2018`, `gpt-fabrication2023` (a hallucinated entry), `kahneman2011`.

**Pass 1.**
- `smith2010`: DOI resolves; abstract is on-topic for the claim. `P(inexistent)=0.05`, `P(misused)=0.10`, `cum_err=0.15`.
- `nguyen2018`: found via Crossref title+author+year (no DOI in `.bib`); abstract topically mismatched (the paper claims a tax-policy result, the source is on tax accounting in private equity). `P(inexistent)=0.15`, `P(misused)=0.70` (capped), `cum_err=0.85`.
- `gpt-fabrication2023`: not found in Crossref, OpenAlex, or Semantic Scholar; author name pattern looks LLM-typical (no other publications). `P(inexistent)=0.95`, `P(misused)=n/a`, `cum_err=0.95`.
- `kahneman2011`: DOI resolves; abstract on-topic. `P(inexistent)=0.05`, `P(misused)=0.10`, `cum_err=0.15`.

Sorted table prints with `gpt-fabrication2023` and `nguyen2018` at the top. Proposed deep-audit set: `gpt-fabrication2023, nguyen2018`.

**Pass 2** (user confirms the set).
- `gpt-fabrication2023`: full text not retrievable (no copy exists anywhere). Pass 2 cannot improve on Pass 1; row stays at `cum_err=0.95` with `found=not-found`. The skill recommends the user delete the cite or replace it.
- `nguyen2018`: open-access PDF retrieved via Unpaywall. Searched full text for the tax-policy claim — not found; the paper is genuinely about a different topic. Updated `P(misused)=0.85`. Verdict in evidence trail: `not-found-in-text`. `cum_err` updated to 1.0 (capped).

User then makes the editorial decision: delete `gpt-fabrication2023`, swap `nguyen2018` for a correct source.

Total agent time: ~5 min Pass 1, ~3 min Pass 2. User review between passes: ~10 min.
