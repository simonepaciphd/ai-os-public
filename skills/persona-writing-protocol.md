---
name: persona-writing-protocol
description: Five-phase interview-driven procedure for writing a new agent persona — encodes the user's chosen posture, skill repertoire, auto-detection signals, tool defaults, and handoffs into a reusable persona file invocable per session.
audience: public
version: 0.1
---

# Persona-Writing Protocol

A five-phase skill for writing a new agent persona: an interview-driven procedure to specify the posture, skill repertoire, auto-detection signals, tool defaults, and handoffs of an agent persona that the user can invoke explicitly (or that auto-selects at session start) for a coherent stretch of work.

Designed to compose with `skill-writing-protocol.md` (a persona file is itself a skill artifact and is registered the same way), the per-audience librarian subagent (the persona declares which skills it reaches for; the librarian resolves bare names to files), `security-officer-protocol.md` (every persona has implicit security-officer access), and the OS hooks in `~/.claude/settings.json` (persona invocations are logged the same way skill invocations are).

Governing principles: **user control** and **radical transparency** — see {{LIBRARY_ROOT}}/skills/about-governing-principles.md. The persona never invents its own posture; it encodes a stance the user has chosen for a recurring task type. Every phase begins with an interview and waits for explicit sign-off before committing anything to disk.

---

## When to use

- A recurring task type benefits from a stable posture across sessions (research, writing, review, system engineering, mentoring, etc.).
- The user wants to encapsulate a particular stance (e.g., adversarial reviewer, Socratic tutor) so it can be invoked on demand without re-specification.
- A specific audience tier needs a persona delivered as part of their library.
- The proposed persona is genuinely additive — its scope does not collapse into an existing persona.

Do not use when: the difference from an existing persona is small enough that an explicit instruction at the start of a session would suffice; the task is one-off; the user has not yet formed a clear preference about the posture; or the proposed persona is really a skill in disguise (i.e., it carries method specifications rather than posture).

## Artifacts the protocol produces

Under the appropriate `personas/` folder for the audience tier this persona belongs to:

1. `<persona-name>.md` — the persona file, following the skeleton at the end of this protocol.
2. A row in `asset-registry.csv` with `asset_type = persona` (when invoked inside a project folder).
3. A row in `interaction-log.csv` capturing the session that produced the persona (when invoked inside a project folder).
4. Optional: revisions to the `default_skills` lists of related personas if handoff routes have been redefined.

A persona is loaded by the agent at session start (via auto-detection or explicit invocation) and remains active until the user switches personas or ends the session.

## Universal rules

1. **Interview first, draft second.** Each phase has an interview step. Do not move to drafting until the user has answered.
2. **Do not invent posture.** If the user has not expressed a preference on a stance question, mark it `OPEN` and return. Do not fill gaps with plausible-sounding defaults.
3. **Encode practice, not training-memory.** The persona should reflect this user's stance for this task — not the genre-average posture an LLM might construct.
4. **Bare names with audience.** The `default_skills` list uses bare skill names (e.g., `lit-review-protocol`). The `audience` field controls resolution. Never write paths in the list. Skills resolve through the audience librarian.
5. **Implicit integrations, explicit logging.** Every persona has implicit access to the audience librarian, the security-officer, the LT-memory layers (global / project), and the skill-usage log. Personas declare integrations in the file ONLY when overriding a default. Personas DO declare `update_connectors` in frontmatter — a list of paths/globs pointing at user writings relevant to the persona's scope; the librarian scans these on demand and queues proposed updates in `{{LIBRARY_ROOT}}/memory/connector-update-queue.md` for the user to process in a live session. The OS-level hooks log every persona invocation, every skill invocation through the persona, and every integration use, regardless of whether the persona file mentions them.
6. **Per-tool defaults, not categorical shortcuts.** Tool defaults are listed per tool, with explicit posture (`liberal`, `ask-first`, `consent-then`, `refuse`). Categorical postures (`reader`, `writer`, `executor`) are forbidden — they collapse important distinctions.
7. **Auto-detection rules are structured.** Path patterns, file types, project metadata flags, prompt-shape signals — concrete and machine-checkable. No free-form prose detection (e.g., "when the user is doing research"). The librarian and the SessionStart hook can only act on structured signals.
8. **Personas reach, they don't author.** A persona reaches for skills; it does not contain skill content. If a persona starts inlining method specifications, refactor that into a skill the persona references.
9. **Mid-session handoff requires a clean break.** When the agent or user proposes switching personas mid-session, prompt: "clear current context, or end session and start fresh?" Do not silently switch.
10. **Invoke the security officer when nervous.** Same rule as `skill-writing-protocol.md`. If a phase you are about to execute could mislead the user or commit them to a position they have not framed, invoke `security-officer` (sentinel `[security-officer: <reason>]` or `Agent({subagent_type: "security-officer", ...})`) before acting.

---

## Phase 0 — Identify the need

Goal: confirm a new persona is the right response.

**Interview checklist:**

1. *"What recurring task type are you trying to support with a persona?"*
2. *"Which existing persona is the closest neighbor? Could you extend it instead of writing a new one?"*
3. *"Which audience tier does this persona belong to?"*
4. *"Could this be served by an explicit instruction at session start, or does it need a persistent stance across sessions?"*
5. *"Is what you are describing actually a posture (persona) or a procedure (skill)?"*

**Action step:** write a one-paragraph scope statement. Get sign-off before continuing.

---

## Phase 1 — Stance & posture interview

Goal: surface the posture, voice, priorities, and refusals that define this persona.

**Interview checklist:**

1. *"Describe in one sentence what this persona is FOR."*
2. *"What does it prioritize over everything else?"*
3. *"What does it explicitly refuse to do?"*
4. *"Whose existing work or behavior should it model? Three or four concrete examples."*
5. *"What posture or voice differentiates it from your other personas?"*

**Action step:** draft a short stance paragraph (3–6 sentences), grounded in the answers above. Get sign-off before continuing.

---

## Phase 2 — Skill repertoire & auto-detection signals

Goal: enumerate the skills the persona reaches for, and the structured signals that indicate this persona should auto-select at session start.

**Interview checklist:**

1. *"List the 3–8 skills this persona uses most. Bare names, please."*
2. *"Which one or two skills does it reach for FIRST when activated?"*
3. *"What folder paths or file types reliably indicate this persona should activate?"*
4. *"What user-prompt signals (verb shapes, named tasks, project keywords) indicate this persona?"*
5. *"What asset-registry tags or project-metadata flags should auto-trigger this persona?"*
6. *"If multiple personas match the same context, who wins, or do we always ask?"*

**Action step:** draft the `default_skills` list and the structured `auto_detection` rules block. Get sign-off before continuing.

---

## Phase 3 — Tool defaults & integration overrides

Goal: specify per-tool posture, plus any non-default integrations beyond the implicit defaults from Universal Rule 5.

**Interview checklist:**

1. *"Per tool — `Read`, `Edit`, `Write`, `Bash`, `Glob`, `Grep`, `WebFetch`, `WebSearch`, `Agent`, `NotebookEdit` — what is the default posture (`liberal`, `ask-first`, `consent-then`, `refuse`)?"*
2. *"Are there tools this persona should never call?"*
3. *"Does this persona need any integration beyond librarian / security-officer / memory / skill-usage log?"*
4. *"Does this persona log any artifacts beyond what the OS-level skill-usage log captures?"*
5. *"Are there default permissions or hook behaviors this persona overrides?"*

**Action step:** draft the `tool_defaults` block and the (usually empty) `integration_overrides` block. Get sign-off before continuing.

---

## Phase 4 — Draft the persona file

Goal: assemble the persona file from prior phases, following the skeleton below.

**Action step:** assemble in this order:

1. Frontmatter (`name`, `description`, `audience`, `version`, `default_skills`, `librarian_scope`, `update_connectors`).
2. Stance (the 3–6 sentences from Phase 1).
3. Default skills (bullet list of bare names, each with a one-phrase reach-condition).
4. Auto-detection signals (structured rules block from Phase 2).
5. Handoff (when to suggest switching to another persona).
6. Tool defaults (per-tool list from Phase 3).
7. Integration overrides (only if Phase 3 produced any; otherwise omit).

Voice: second-person imperative for the stance and tool defaults ("you...", "do not..."); declarative-structured for the rules blocks. Disciplined, controlled, no inflated language.

---

## Phase 5 — Test and iterate

Goal: the first real invocation is the final phase of drafting.

**Prerequisite:** the OS harness must be wired before Phase 5 can validly observe activation. Specifically: SessionStart and UserPromptSubmit hooks for default activation and alias detection, plus per-persona slash commands at `~/.claude/commands/`. Without these, "did auto-detection fire?" is unanswerable — the persona file exists but nothing loads it at runtime. Persona drafts written before the harness is wired should be marked Phase 5 *deferred*, not pending.

**Action step:**

1. Invoke the persona on one real task end to end (auto-detect or explicit `/persona <name>`).
2. Log: did auto-detection fire when expected? did the right skills surface? did tool defaults bite where they should? did handoff trigger on the right cue?
3. Revise the persona file. First-draft personas that are never tested tend to encode false-confidence postures.

**Review cadence:** re-read after the first three sessions; re-read every six months even without new sessions.

---

## Persona file skeleton

```
---
name: <persona-name>
description: <one line: what this persona is FOR>
audience: <audience-tier>
version: 0.1
default_skills:
  - <skill-name-1>
  - <skill-name-2>
librarian_scope: <audience-tier>
update_connectors:
  - <path-or-glob-1>
  - <path-or-glob-2>
---

# <Persona Name>

## Stance

<3–6 sentences. Posture, voice, priorities, refusals.>

## Default skills

- `<skill-name>` — <one phrase: when this persona reaches for it>
- ...

## Auto-detection signals

Activate this persona when ANY of the following hold:

- **Path patterns:** <glob>, <glob>
- **File types:** <list>
- **Prompt-shape signals:** <verb-list, keyword-list>
- **Project metadata:** <asset-registry tag>, <state.md flag>

If multiple personas match: <ask | priority order | named winner>.

## Handoff

- → `<other persona>` when <condition>
- → `<other persona>` when <condition>

Mid-session handoff requires the clean-break prompt per Universal Rule 9 of `persona-writing-protocol.md`.

## Tool defaults

- `Read`: <liberal | ask-first | consent-then | refuse>
- `Edit`: ...
- `Write`: ...
- `Bash`: ...
- `Glob`: ...
- `Grep`: ...
- `WebFetch`: ...
- `WebSearch`: ...
- `Agent`: ...
- `NotebookEdit`: ...

## Integration overrides

<Only present if this persona deviates from the implicit default integrations
(librarian / security-officer / memory / skill-usage log). Otherwise omit this section.>
```

---

## Handoff with other skills

- `skill-writing-protocol.md` — a persona file is registered in `asset-registry.csv` per Rule 4 of the setup protocol; the session that produced it is logged in `interaction-log.csv` per Rule 5.
- `project-setup.md` — when the persona is invoked inside a project folder, the invocation is recorded in `interaction-log.csv` (the OS-level hook).
- The audience librarian (`<audience>/agents/librarian.md`) — resolves the bare skill names listed in `default_skills` to files, using keyword match against skill description frontmatter.
- `security-officer-protocol.md` — implicit access for every persona; invoke when nervous about a posture decision.
- `lit-review-protocol.md` — invoked as a subagent if Phase 1 needs external posture models (e.g., what does an "adversarial reviewer" look like in the relevant literature).

## Common failure modes

- **Posture drift.** The persona's stance reads as a generic LLM "helpful assistant" voice. Recovery: re-run Phase 1 with concrete artifacts of the user's actual past behavior; cut every sentence in the stance that could appear in any persona.
- **Skill bloat.** `default_skills` lists more than ~8 skills. Recovery: split the persona, or trim to the skills the persona reaches for FIRST; the librarian can find others on demand.
- **Vague auto-detection.** Auto-detection rules use prose like "when the user is doing research." Recovery: per Universal Rule 7, convert to structured rules — paths, file types, prompt-shapes, metadata flags.
- **Inlined skill content.** The persona contains method specifications. Recovery: per Universal Rule 8, extract into a skill and reference by name.
- **Categorical tool defaults.** Tool defaults written as `reader`, `writer`, `executor`. Recovery: per Universal Rule 6, expand to per-tool list with the four allowed postures.
- **Handoff loops.** Persona A hands off to B which hands off back to A. Recovery: define handoff conditions explicitly with exit criteria; require clean-break between switches.
- **Missing audience consideration.** A persona drafted in one audience tier that should also exist in another. Recovery: at Phase 0, explicitly ask whether the same posture is needed in another tier; if yes, draft a parallel persona (do not symlink — audiences are separate repos).
- **Skill leakage across audiences.** A persona's `default_skills` list references a skill that lives outside its audience tier. Recovery: the librarian scope is single-tier; a persona can only resolve skills inside its audience. If a skill is needed in two tiers, it lives in both (separate copies, kept in sync via the user's editorial pass).
