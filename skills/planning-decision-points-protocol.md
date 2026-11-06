---
name: planning-decision-points-protocol
description: Inventory every choice a planned task involves as `DP-###` decision points with a Default and a Recommendation, then (optional, end of Stage 5, before the lock) classify each one as substantive and/or procedural with the approved two-question definition — JEV through `classify.py` by default, an independent subagent as fallback — and bake a `researcher`-lane gate task into `PLAN.md` for every substantive one. Use when writing task cards and before the planning baseline lock.
audience: public
version: 0.1
---

# Planning Decision-Points Protocol

Make every choice inside a plan visible, and route the substantive ones to the user as gate tasks before the plan locks.

Composes with `planning-protocol.md` (Stage 5), `planning-implementation-map-protocol.md` (task cards), `planning-adjudication-protocol.md` (`PLAN.md`), `planning-labels-protocol.md` (runs after this step) and `planning-spec-reconciliation-protocol.md` (gates after the lock). File contracts: `_assets/plan-viewer/FORMAT.md` §5 (cards, gates) and §7 (`Decision-Classes.json`).

Version: 0.1 (first public release; earlier versions are not shipped in this repo).

## 1. Inventory (every task card)

Each task card carries a `#### Decision points` section (`_assets/planning-templates/PLAN.md`). List every choice the task involves, phrased as a decision, or write `none`:

```markdown
#### Decision points
- DP-001: <the choice, phrased as a decision>
  - Default: <the choice the agent makes if nobody objects>
  - Recommendation: <the choice the AI recommends> — <one-line reason>
```

- IDs `DP-###` are unique plan-wide and never renumbered.
- Both sub-bullets are required (`E-STRUCTURE` otherwise), including for choices that look substantive; the classifier decides what the page shows.
- Write the decision text so it stands alone: the classifier sees only the text.

## 2. Classify (optional; end of Stage 5, before the lock)

Run once `PLAN.md` has settled after adjudication, before the writer labels pass and the plan-viewer build. Classify runs **before the lock only**. After the lock, a new gate enters only through a spec delta (`planning-spec-reconciliation-protocol.md`).

**Definition.** Two independent yes/no questions, each answered as a probability: *substantive* and *procedural*. Use the APPROVED question texts, criteria and anchors in `_assets/plan-viewer/definition.json`. Do not paraphrase the questions.

**Threshold.** 0.5 on each score. A DP is `substantive` iff its substantive score ≥ 0.5 (FORMAT §7).

**Quadrant mapping:**

| Substantive ≥ 0.5 | Procedural ≥ 0.5 | Result |
|---|---|---|
| yes | yes | gate task, `Gate-mode: approve` — "Approve the recommendation": the card quotes the Recommendation; the user approves or changes it |
| yes | no | gate task, `Gate-mode: decide` — "You decide": the card carries background only; the Recommendation is dropped |
| no | yes or no | no gate; the page shows the Default in the task pop-up (the neither quadrant is handled as procedural) |

**Gate tasks.** Each gate is its own task in the reserved `researcher` lane, with `Generated-from: DP-###` and `Gate-mode: approve | decide` on its card. A gate takes no wave time: it sits at the start of the wave of the task it gates and may precede that task in the same wave (FORMAT §5). The result is accepted automatically and baked into `PLAN.md` before the lock; the full response goes to `planning/Decision-Classes.json` (FORMAT §7: classifier name and pinned version, run time, definition hash, threshold, per-DP scores and class, the gate task, the raw response, and the hash of `PLAN.md` before insertion).

**Recommendation rule.** The Recommendation on an `approve` gate applies to **plan gates only**. Decision pages and chat keep the house rule: no recommendation on substantive decisions.

## 3. Default classifier: JEV through `classify.py`

`_assets/plan-viewer/classify.py` (its README, `classify-README.md`, documents the exact request/response and gate-insertion procedure). Its contract, from the JEV API notes (`jev-api.md`, not shipped in this repo):

- **Key lookup, in order:** environment variable `TYPESAFE_API_KEY`; then `jev-key.txt` in the launcher's working directory; then a masked pop-up (stdlib `tkinter`, console `getpass` fallback). A typed key is used for that run only and **never saved**. The script warns if `jev-key.txt` is tracked by Git or sits in a cloud-synced folder.
- **Model pin:** `jev-1.14.0`, sent explicitly on every call (never an alias such as `jev-latest`); the `model` field of each response is recorded.
- **Version check, every run:** `GET /v1/models` looks for a newer version. On a newer version, one small probe question tests whether input and output stay mechanically the same, and the coded test set is re-run; the new version is swapped in only if the probe passes and κ ≥ 0.6 still holds. Otherwise the user is notified that an update via an AI agent is warranted, and the run keeps the pin.
- **Scrubbing:** paths, emails and IDs are stripped from the decision text before sending.
- **Output:** `Decision-Classes.json` plus the gate tasks in `PLAN.md`; then `plan_viewer.py --check` must pass.

**Cost rule.** The agent never runs a call that reaches the paid API itself: it prints the cost estimate (JEV bills input tokens only; current price in `classifier.json` and `classify-README.md`) and a `!` command for the user to run in chat. Tests use a local mock server.

## 4. Fallback: independent subagent

When JEV is unavailable (no key, outage, failed version check without a passing pin), one subagent that **did not write the plan** classifies. Give it only this protocol, the approved definition and the DP texts (no plan rationale), and the same two questions and threshold. Record `classifier.name: "subagent"` with its harness and exact model ID as `version`. The parent writes its output into `Decision-Classes.json` and inserts the gates under the same mapping.

## 5. Reliability gate

Before a classifier's output is baked in automatically, it must agree with the user's blind coding of a test set (a `.jsonl` test set and the user's coding replies, named in `classifier.json` `test_set`/`coding`; not shipped in this repo): **Cohen's κ ≥ 0.6 on the substantive score**. On failure, the question text is revised, re-approved by the user, and re-tested; nothing auto-bakes until it passes. The same bar governs a JEV version swap (§3).

## Return report

DPs inventoried per task; classifier name and version; per-quadrant counts; gate tasks inserted (IDs, modes); the `--check` output; the cost line actually incurred (from the user's run); and any DP whose text had to be scrubbed so heavily that its classification is doubtful.
