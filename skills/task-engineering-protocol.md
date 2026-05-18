---
name: task-engineering-protocol
description: Interview-driven protocol that engineers a self-contained handoff prompt for a one-off task with no matching skill — silently scans the local library for personas, skills, and project context when available; otherwise asks the user directly. Output is a Markdown handoff prompt designed to be pasted into a fresh session.
audience: public
version: 0.1
---

# Task-Engineering Protocol

A skill for engineering a self-contained handoff prompt for a one-off task that no existing skill covers. The skill runs an interview, optionally scans the local environment for personas / skills / project assets, and produces a single Markdown handoff prompt designed to be pasted into a fresh session — encouraging context isolation and avoiding cross-task contamination.

Designed to be **harness-agnostic**: works in Claude Code, claude.ai chat, ChatGPT, Gemini, or any other LLM front-end where the user can paste a prompt. When run inside an environment with a structured library (personas, skills, project ledger) at a known root, it silently picks up that scaffolding and routes the handoff appropriately. When run in a chat / virtual environment with no filesystem access, the silent scan is skipped and the user is asked about scaffolding directly.

Composes with `skill-writing-protocol.md` (if the one-off task starts recurring, promote it to a real skill) and `persona-writing-protocol.md` (if a missing persona surfaces during the interview).

Anchor reference: a current synthesis of provider prompt-engineering docs (Anthropic, OpenAI, Google, Meta, Mistral, Cohere) and academic findings on chain-of-thought, self-consistency, and verification. Re-verify provider docs every six months — recommendations change with model generations.

Governing principles: **user control** and **radical transparency** — see `{{LIBRARY_ROOT}}/skills/about-governing-principles.md`. Add: **context isolation** — one-off tasks should run in a fresh session, not bleed into the engineering session.

---

## When to use

- A discrete one-off task that no existing skill covers and that is not worth turning into a durable skill.
- A task that will be executed in a *fresh* session — either because context isolation matters, because the current session is congested, or because the deliverable will be handed off to a different model / collaborator / future-you.
- A task whose acceptance criteria, format, and verification rules are clear enough to be written down, but specific enough that they do not justify a permanent skill.

Do not use when:

- An existing skill already covers the task — invoke that skill instead.
- The task is genuinely recurring — draft a real skill with `skill-writing-protocol.md`.
- The task can be completed in the current session without isolation benefits, and the user has not requested a handoff artifact.
- The user has not yet decided what the task is. This protocol structures clarity into a prompt; it cannot manufacture clarity that does not exist. Surface the unresolved question first.

## Artifacts the skill produces

1. **Handoff prompt** — a Markdown document, presented in chat at the end of the session. The user copy-pastes it into a fresh session. Optionally also written to disk.
2. **Optional log file** — if the user opts into logging:
   - **Default (no project-CSV infrastructure):** a single JSON file `<task-slug>-task-log.json` written alongside the deliverable's expected location, containing task metadata, interaction log, asset registry, the full handoff prompt, and any next handoffs.
   - **Fall-through (project-CSV infrastructure present — see `project-setup.md`):** a row in the project's `interaction-log.csv` + a row in `asset-registry.csv` for the handoff prompt itself (`asset_type = reference`, `creator = mixed`, `verification = not-verified`).

The JSON schema for the default branch (Phase 1 Q8):

```json
{
  "task": {
    "slug": "<short-slug>",
    "title": "<task title>",
    "engineered_at": "<ISO date>",
    "harness": "<Claude Code | claude.ai | ChatGPT | Gemini | other>",
    "model": "<model identifier if known>"
  },
  "interaction_log": [
    { "phase": "0", "summary": "<silent scan results, or 'skipped — no library detected'>" },
    { "phase": "1", "summary": "<task interview answers, condensed>" },
    { "phase": "2", "summary": "<scaffolding interview if fired, otherwise 'skipped'>" },
    { "phase": "3", "summary": "<handoff prompt delivered>" }
  ],
  "asset_registry": [
    {
      "asset_id": "handoff-prompt",
      "type": "reference",
      "creator": "mixed",
      "verification": "not-verified"
    }
  ],
  "handoff_prompt": "<full markdown handoff prompt as a string>",
  "next_handoffs": ["<follow-up task 1>", "..."]
}
```

The single-JSON branch is the recommended default for users without a structured project layout — one file is easier to inspect, share, or archive than a pair of CSVs requiring a project skeleton.

## Universal rules

1. **One handoff prompt, one task.** Do not engineer multi-task prompts. If the interview surfaces additional tasks, queue them in the `Next handoffs` section of the current prompt and engineer separate prompts later.
2. **No implicit state.** The handoff prompt must be readable by a fresh session with no knowledge of the engineering conversation. Quote, summarize, or paste any needed context. Label prior decisions as `FIXED`, `TENTATIVE`, or `OPEN` so the next session knows what is settled and what is open.
3. **Interview first, synthesize second.** Do not start drafting the handoff prompt until the task interview is complete. If a key field is empty after the interview, ask one targeted follow-up rather than guessing.
4. **Do not invent preferences.** If the user has not expressed a preference on a design question (format, verbosity, template, plan), ask. Do not fill gaps with plausible defaults.
5. **Outcome-first, acceptance-criteria driven.** The handoff prompt names the deliverable as a noun, specifies acceptance criteria, and includes a stop condition for missing information. Do not include ritualistic boilerplate that does not change the acceptance criteria.
6. **Persona routing is conditional on a successful silent scan.** Only inject `Operate as <persona>` when the silent scan confirms a persona file exists and matches the task. Otherwise leave the persona slot blank — do not invent or name personas.
7. **Encourage a fresh window.** End the skill output with an explicit recommendation to start a new session and paste the handoff prompt. The recommendation may be overridden by the user, but the default is isolation.

---

## Phase 0 — Silent context scan

Goal: detect whether the user has a structured library available and, if so, enumerate the relevant assets. No user interaction.

**Probe steps:**

1. Attempt to read a sentinel file at `{{LIBRARY_ROOT}}/CLAUDE.md` (or its harness equivalent — e.g., `~/.claude/CLAUDE.md` for a Claude Code setup). Success + content-signature match (a library-tier marker like "skills", "personas", a known library name) → library present (`LIB = present`). Failure or generic content → `LIB = absent`; skip remaining probe steps.
2. If `LIB = present`, run the asset scan:
   - Enumerate `{{LIBRARY_ROOT}}/personas/*.md` — names and one-line descriptions.
   - Enumerate `{{LIBRARY_ROOT}}/skills/*.md` — names and one-line descriptions. Match the user's initial prompt against skill descriptions (keyword / Grep) to identify similar skills.
   - Read `{{LIBRARY_ROOT}}/CLAUDE.md` — library-level connector context.
   - Read `{{LEDGER_PATH}}` if it exists — does the task plausibly belong to an active project? Capture the project slug if so.
3. Hold all scan results in working memory. Do not announce them to the user yet; they inform the interview but should not preempt it.

**Action step:** if the scan finds a strong match to an existing skill (description overlaps materially with the user's initial framing), pause and ask the user verbatim: "An existing skill — `<skill-name>` — looks close to this task. Should I delegate to that skill instead of engineering a one-off prompt?" Wait for explicit yes / no before proceeding to Phase 1.

---

## Phase 1 — Task interview

Goal: extract the operative content of the handoff prompt. Deliver as a single numbered block; aim to run end-to-end in one round. Ask targeted follow-ups only if specific answers are too thin to act on.

**Interview checklist (deliver all at once):**

1. *"In one sentence, what is the task and what is the deliverable?"* — confirm or rephrase the user's initial framing.
2. *"Who is the audience for the deliverable, and what will they do with it?"* — anchors level of detail and tone.
3. *"What format and verbosity should the deliverable have? Markdown / JSON / table / outline / code / prose? Approximate length or word count? Are there templates I should follow — paste a path, link, or example."*
4. *"What is the plan? If you have one, describe it. If not, here are two or three options based on what you've told me and what the silent scan found: [propose options]. Pick one or propose your own."*
5. *"What context, sources, or prior decisions need to be inlined in the handoff? Paste, link, or describe."*
6. *"What constraints and non-goals matter? Sources to exclude, claims to avoid, length limits, style restrictions."*
7. *"What verification or validation should the next session run before delivering? Citation checks, factual cross-references, format validation, evidence-mapping?"*
8. *"Do you want a log of the interaction together with the final output?"* — default is a single JSON file alongside the deliverable; if your library has `project-setup.md`-style CSV infrastructure active in this project folder, the log appends there instead.
9. *"Are there follow-up tasks for another AI session after this deliverable is produced? If yes, name them — they become a `Next handoffs` section in the prompt, not additional work in the current handoff."*

**Action step:** synthesize answers into a structured in-memory working draft:

- Task statement (one sentence).
- Deliverable noun + format + verbosity + template path / link / "none".
- Audience and use case.
- Plan (selected from options or user-supplied; sequence of short steps).
- Sources / context / prior decisions, each labeled `FIXED` / `TENTATIVE` / `OPEN`.
- Constraints and non-goals.
- Verification rules.
- Log preference: `json-single-file` / `project-csv` / `none`.
- Follow-up tasks if any.

If any field is empty, ask one targeted follow-up before proceeding.

---

## Phase 2 — Scaffolding interview (conditional)

Goal: if Phase 0 did not surface usable scaffolding, ask about it now — *after* the task-specific interview, when the user has the task fresh in mind. Phase 2 is skipped if Phase 0 already produced a clean match.

**Trigger conditions:** fire if **either** holds —

- `LIB = absent` (chat / virtual environment, no filesystem access during the scan), or
- `LIB = present` but no persona obviously matches the task and no template / style guide was supplied in Phase 1.

**Interview checklist (conditional):**

1. *"Do you have a system prompt, persona, role description, or stance you want the next session to adopt for this task? Paste or describe."*
2. *"Are there existing protocols, style guides, or prior outputs you want the next session to imitate? Paste paths, links, or content."*
3. *"Are there templates or schemas the deliverable should follow that you didn't already mention?"*

**Action step:** fold the answers into the working draft. If the user supplies a persona / stance and the library is present, store the path. If the library is absent, inline the stance text into the handoff prompt (no path resolution possible in the next session).

---

## Phase 3 — Synthesize and deliver the handoff prompt

Goal: produce the Markdown handoff prompt and present it to the user in chat.

**Action step:** assemble the prompt in the structure of the **Handoff prompt template** below. Present it in a fenced code block in chat. End the chat message with:

> Recommended: open a fresh session, paste the prompt above, and run it there. Context isolation reduces cross-task contamination. If you'd prefer to run it in this session, say so.

If the user opted into logging (Phase 1 Q8):

- **Default branch (`json-single-file`):** write `<task-slug>-task-log.json` alongside the deliverable's expected location, conforming to the schema in the "Artifacts the skill produces" section above.
- **Fall-through branch (`project-csv`):** append a row to the project's `interaction-log.csv` and register the handoff prompt as an asset in `asset-registry.csv`. Requires the project folder to have been set up via `project-setup.md`.

Do not write to `{{LIBRARY_ROOT}}/CLAUDE.md` or to `{{LEDGER_PATH}}` — this skill produces an artifact, not a project update. Library-level connector or ledger changes are out of scope and would route through a management persona (e.g., `chief-of-staff`) or an infrastructure persona (e.g., `engineer`) if needed.

---

## Handoff prompt template

```markdown
# <Task title — short, descriptive noun phrase>

<!-- Persona routing is optional. Include this line ONLY when the silent scan
     detected a library and a persona file matches the task. Otherwise omit. -->
Operate as `<persona-name>` (load `{{LIBRARY_ROOT}}/personas/<persona-name>.md`).

## Role
You are <specific role / evaluator / writer / analyst>, working with <user>.

## Task
<One-sentence task statement, in the imperative.>

## Deliverable
- Format: <Markdown / JSON / table / code / prose>
- Length or verbosity: <word count or section count or bullet count>
- Audience: <who will use it and for what>
- Template: <path, link, or inlined skeleton; "none" is acceptable>

## Context
<Paste, summarize, or link the relevant source material. Place long documents
at the top; the task itself lives in the section above.>

## Prior decisions (label each)
- FIXED: <decision the next session must preserve>
- TENTATIVE: <decision the next session may revise with reason>
- OPEN: <question to resolve during execution>

## Plan
<Sequence of short steps. Each step is one sentence. The plan is scaffolding,
not the deliverable — do not produce a long visible reasoning trace.>

## Constraints and non-goals
- Constraint: <e.g. length cap, tone, citation style>
- Do not: <non-goal>
- Sources to use: <hierarchy>
- Sources to avoid: <exclusions>

## Verification (run before delivering)
- <verification check tied to external evidence or an explicit criterion>
- <verification check 2>
- If a needed fact is unavailable, mark it as OPEN; do not invent it.

## Stop condition
Deliver the artifact when <acceptance criterion 1> AND <acceptance criterion 2>.
If acceptance criteria cannot be met, stop and report what is missing.

## Logging
<Default: write a single JSON file `<task-slug>-task-log.json` alongside the
deliverable, with task metadata, interaction log, and asset registry rows.
Fall-through: if `project-setup.md`-style CSV infrastructure exists in the
working folder, append to `interaction-log.csv` and `asset-registry.csv`
instead. Omit this section entirely if logging was declined.>

## Next handoffs (if any)
- <follow-up task 1, to be engineered as a separate handoff prompt later>
- <follow-up task 2>
```

---

## Handoff with other skills

- `skill-writing-protocol.md`: if a one-off task starts recurring (three or more invocations), the user may want to promote the engineered prompt to a real skill via this protocol.
- `persona-writing-protocol.md`: if the interview surfaces a needed persona that does not yet exist, the user may want to draft one. Out-of-scope for this skill itself.
- `project-setup.md`: when the handoff runs inside a project folder set up with that protocol, this skill writes to that project's `interaction-log.csv` and `asset-registry.csv` (fall-through branch of Phase 1 Q8).
- `lit-review-protocol.md`: not called from this skill, but if the user's task is itself a literature review, the handoff prompt should delegate to `lit-review-protocol.md` in the fresh session rather than re-specifying the literature work inline.

## Common failure modes

- **Smuggled state.** The handoff prompt references "as discussed" or "the file we were looking at" — the next session cannot reconstruct that state. Recovery: re-read the draft against Universal Rule 2 (no implicit state) before delivering; replace every implicit reference with quoted content or a path the next session can read.
- **Persona over-routing.** The skill picks a persona by weak keyword match when no clean fit exists, biasing the next session toward an inappropriate stance. Recovery: only route to a persona when the silent scan found a strong, semantically clean match; otherwise leave the persona slot blank.
- **Multi-task creep.** The interview surfaces three tasks; the skill folds them into one prompt; the next session does none of them well. Recovery: split into separate handoffs and queue them as `Next handoffs` in the first prompt (Universal Rule 1).
- **Cargo-cult reasoning instructions.** The skill adds "think step by step" or a long planning ritual to every prompt. Per the anchor reference, this can hurt simple tasks and worsen socially sensitive ones. Recovery: include explicit planning only when the task is multi-step or compositional; for simple stylistic or extraction tasks, omit it.
- **Acceptance-criteria absence.** The skill produces a prompt that names the deliverable but not the test for success. Recovery: every handoff must include a stop condition and at least one acceptance criterion. If the user did not supply one in the interview, ask before drafting.
- **Generic verification.** The skill writes "verify accuracy" instead of "cite the source sentence for each factual claim" or "validate the JSON output against the supplied schema." Generic self-critique is empirically weak. Recovery: tie every verification step to external evidence or an explicit criterion.
- **Over-prompting.** The handoff accumulates boilerplate (decorative personas, legacy process instructions, redundant warnings) that does not change acceptance criteria. Recovery: cut anything that does not affect the deliverable; favor a shorter, sharper prompt.

## Worked example

A one-off task: the user wants a 200-line README for a small data-analysis repo, structured as Installation / Usage / Troubleshooting, citing two README templates the user maintains at `~/templates/README-A.md` and `~/templates/README-B.md`.

1. **Phase 0 silent scan.** Library detected at `{{LIBRARY_ROOT}}`. Personas include `chief-of-staff`, `researcher`, `engineer`, `teacher`. Skills include `skills-library-setup.md`, `project-setup.md`, `lit-review-protocol.md` — no existing skill matches "README writing"; closest neighbor is `project-setup.md` but its framing is narrower. Persona match: `engineer`.
2. **Phase 1 interview.** Task: single-pass README. Deliverable: 200-line Markdown, sections Installation / Usage / Troubleshooting. Audience: future contributors to the repo. Plan: read both templates → identify common structure → draft → revise. Sources: `~/templates/README-A.md`, `~/templates/README-B.md`, plus the repo's `package.json`. Constraints: no marketing language; no future-feature claims. Verification: every section maps to one of the two templates; line-count check. Logging: yes — JSON single file alongside the README (no project-CSV infrastructure in this repo). Follow-up: a `CONTRIBUTING.md` after the README ships.
3. **Phase 2.** Skipped — `engineer` persona is a clean fit; templates supplied in Phase 1.
4. **Phase 3.** Skill produces a Markdown handoff prompt with `Operate as engineer` at the top, all the above inlined as `Role`, `Task`, `Deliverable`, `Context`, `Prior decisions`, `Plan`, `Constraints`, `Verification`, `Stop condition`, `Logging`, and a `Next handoffs` section noting the `CONTRIBUTING.md` follow-up. Recommends fresh window. Writes `readme-task-log.json` alongside the README with task metadata, interaction log, and asset registry entries.

Total time: ~10–15 minutes of user attention.

---

## Status

- Version: 0.1
- Last revised: 2026-05-10
- Sanitized from the source library's personal-tier sibling via that library's public-skill-sanitizing protocol.
