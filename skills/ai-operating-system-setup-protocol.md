---
name: ai-operating-system-setup-protocol
description: One-time bootstrap walkthrough for installing a public AI Operating System mirror — runs an intake interview to capture user-specific values, applies placeholder substitution across the library, and dispatches to the library-setup and library-connection skills to wire the result into Claude Code.
audience: public
version: 0.1
---

# AI Operating System Setup Protocol

A consumer-facing bootstrap procedure for an external user who has just received a copy of the public AI Operating System mirror (skills, agents, personas, audience-tier `CLAUDE.md`) and wants to turn it into their own working library. The protocol is interview-driven where it must capture values from the user (paths, identity, repo intent) and mechanical everywhere else (the actual placeholder substitution and the harness wiring, both of which are handed off to companion skills).

Composes with:

- `skills-library-setup.md` — scaffolds the library structure (folders, registries, ledgers).
- `skills-library-connection.md` — wires the library into the Claude Code harness (`~/.claude/`).
- `about-governing-principles.md` — every shipped skill in the library references this; the user should read it before customizing.

Governing principles: **user control** and **radical transparency** — see {{LIBRARY_ROOT}}/skills/about-governing-principles.md. The protocol never picks a path, name, or affiliation on the user's behalf; if the user does not have an answer for a given placeholder, it is marked `OPEN` and surfaced rather than filled in. Every value captured in Phase 1 and substituted in Phase 2 is recorded in a manifest the user keeps with the library.

---

## When to use

- The user has cloned, downloaded, or otherwise received the public mirror folder and wants to make it their own working library.
- The user is migrating from a personal-only library to a multi-tier setup and needs the public tier instantiated alongside.
- The library has been re-pulled (refreshed from upstream public) and the user wants to re-run substitution against new placeholder occurrences without losing prior values.

Do not use when:

- The user already has a working AI OS and just wants to install a single new skill — copy the skill file directly and substitute by hand.
- The user is asking how to *use* the library (how to invoke a skill, how to pick a persona) — that is harness usage, not setup.
- The library was never sanitized to placeholder form (it is a personal copy with absolute paths baked in) — no substitution is needed; treat it as the user's own private library.

## Artifacts the skill produces

1. An **intake-interview transcript** at `<chosen-library-root>/setup/intake-<YYYY-MM-DD>.md` — captured Phase 1 answers, one row per placeholder, plus the values that were marked `OPEN`.
2. A **substitution manifest** at `<chosen-library-root>/setup/substitution-manifest-<YYYY-MM-DD>.md` — for every placeholder, the value substituted in and the count of files touched. Co-located with the intake transcript.
3. A **populated library** at the user's chosen root: every `{{PLACEHOLDER}}` token replaced (or left in place and flagged in the manifest if marked `OPEN`).
4. Optional: a starter `CLAUDE.md` identity file (Phase 4) if the user wants a personalized identity layer.
5. A wired harness — produced by the dispatched companion skills, not by this protocol directly.

## Universal rules

1. **Capture before substitute.** Every value the substitution will write must first be recorded in the intake transcript and confirmed by the user. No silent fills.
2. **No invented values.** If the user does not have an answer, mark the placeholder `OPEN` in the manifest and leave the token in place. Plausible defaults are never substituted in.
3. **Snapshot before substitution.** Before Phase 2 runs, the library folder is duplicated (or version-controlled). Substitution is destructive in-place; the snapshot is the rollback path.
4. **Manifest is canonical.** The substitution manifest, not the agent's memory, is the record of what was filled in with what. Future re-runs of this protocol diff against the manifest.
5. **One root per run.** A single Phase 1 captures values for one library root. If the user wants to install multiple tiers (e.g., a `public/` mirror beside a `personal/` tier they will draft themselves), run the protocol once per tier, with a separate manifest each time.
6. **Do not edit `~/.claude/` from this protocol.** Harness wiring is delegated to `skills-library-connection.md` (Phase 3). This protocol stops at the library boundary.
7. **Identity layer is opt-in.** Phase 4 only runs if the user explicitly requests a personalized `CLAUDE.md`. The library is fully usable without it.

---

## Phase 0 — Prerequisites

Goal: confirm the user has what they need before any interview begins.

**Check before proceeding:**

1. The user has a copy of the public mirror somewhere on disk (cloned, downloaded, or copied). Confirm the path.
2. Claude Code is installed and the user can locate `~/.claude/` (the harness root).
3. The user has read access to the mirror's `CLAUDE.md` and `about-governing-principles.md`. If not, ask them to read at least the governing principles before continuing — those frame everything that follows.
4. The user has not already run substitution against this mirror copy. If they have, ask whether this is a refresh (re-pull) and read the prior `substitution-manifest-*.md` if one exists; otherwise stop and ask whether the user means to overwrite an existing setup.

**Action step:** if all four checks pass, proceed to Phase 1. Otherwise, stop and surface what is missing.

---

## Phase 1 — Intake interview

Goal: capture a value for every placeholder the public mirror uses, asking only what is needed and marking what is not yet known as `OPEN`.

**The protocol uses these placeholders.** Ask the user about each in turn; their values will be substituted across the library in Phase 2.

### Section A — Path layout (required)

1. *"Where will your library live? Provide a path; e.g., `~/AI-OS/`, `~/Documents/AI-OS/`, or some folder under your projects directory. This will become `{{LIBRARY_ROOT}}`."*

2. *"Will you have multiple audience tiers (e.g., a `public/` tier the way the source mirror does, plus your own `personal/`, `students/`, or `RAs/` tiers)? If yes, what is the parent path that contains all tiers? This becomes `{{OS_ROOT}}`. If no — and the library root will hold a single tier — `{{OS_ROOT}}` is the same as `{{LIBRARY_ROOT}}`."*

3. *"Where do your active projects live on disk? E.g., `~/projects/`, `~/Dropbox/`, `~/work/`. This becomes `{{PROJECTS_DIR}}`."*

4. *"Do you use Overleaf, Dropbox-synced LaTeX, or another sync target for writing projects? If yes, what is the sync root? This becomes `{{OVERLEAF_ROOT}}`. If no, mark `OPEN` and skip."*

5. *"Is there a path that depends on your home directory and that the substitution can't handle with the placeholders above? If yes, name `{{USER_HOME}}` (rare). Otherwise mark `OPEN` and move on."*

### Section B — Ledger (required)

6. *"Where will your active-projects ledger live? Default: `{{LIBRARY_ROOT}}/memory/projects-ledger.md`. Confirm or override. This becomes `{{LEDGER_PATH}}`."*

### Section C — Project root (deferred)

`{{PROJECT_ROOT}}` is per-project, not per-library. It is set the first time a skill writes to a specific project folder. **Do not capture a value here.** Note in the manifest: *"Set per-project; not bootstrap."*

### Section D — Identity (optional, gated by Phase 4)

7. *"Do you want a personalized identity layer (your name, affiliation, field) in the library's `CLAUDE.md`? If yes, we will run Phase 4 after substitution; if no, the library uses generic 'the user' framing throughout. You can add identity later."*

If yes, capture:

- 8. *"Your display name. This becomes `{{USER_NAME}}`."*
- 9. *"Your institutional or organizational affiliation. This becomes `{{USER_AFFILIATION}}`. Mark `OPEN` if you don't want to record one."*
- 10. *"Your discipline or primary field. This becomes `{{USER_FIELD}}`. Mark `OPEN` if you don't want to record one."*

If no, mark all three identity placeholders `OPEN` and proceed.

### Section E — Repository (optional)

11. *"Will you sync this library to a git repository? If yes, what is the repo name? This becomes `{{REPO_NAME}}`. If no, mark `OPEN` — the placeholder will remain in the library but harmlessly; you can fill it later."*

**Action step:** record every answer in `<chosen-library-root>/setup/intake-<YYYY-MM-DD>.md` with one row per placeholder (name, value or `OPEN`, source-of-truth note). Read the full transcript back to the user verbatim and ask: *"Is this correct? Anything to revise before substitution?"* Iterate until the user signs off. **Do not begin Phase 2 until the intake transcript is signed off.**

---

## Phase 2 — Apply substitutions

Goal: replace every `{{PLACEHOLDER}}` token across the library with the value captured in Phase 1, leaving `OPEN` placeholders untouched and recorded in the manifest.

**Action step:**

1. **Snapshot the library.** Per Universal Rule 3, duplicate the library folder (or commit it under version control) before any substitution. Record the snapshot location in the manifest.

2. **For each placeholder with a captured value**, walk the library files (skills, personas, agents, `CLAUDE.md`, any other `*.md` and `*.json` under the library root) and replace every literal `{{PLACEHOLDER}}` occurrence with the captured value. The user runs the actual substitution in whatever tool they prefer — a text editor's project-wide find-and-replace, a sed/awk/PowerShell one-liner, an IDE's refactor command, or by hand for a small library. The protocol does not prescribe a tool.

3. **For each placeholder marked `OPEN`**, leave the literal `{{PLACEHOLDER}}` token in place. Note in the manifest that this placeholder remains live; the user can substitute it later via the same Phase 2 process when they have a value.

4. **Generate the substitution manifest** at `<library-root>/setup/substitution-manifest-<YYYY-MM-DD>.md`. For every placeholder, record:
   - Placeholder name.
   - Substituted value, OR `OPEN` (still live).
   - Count of files touched (or `0` for `OPEN`).
   - A short note if a placeholder did not appear anywhere in the library (this is informational, not an error).

5. **Verify by grep.** Run a search for `{{` across the library. Every remaining hit should be a placeholder marked `OPEN` in the manifest. Anything else is a substitution miss; fix in place and update the manifest.

6. **Surface the manifest to the user** before continuing. *"Substitution complete. Manifest at `<path>`. Confirm the file count per placeholder looks right; flag any unexpected `0`-count rows. Ready to wire to the harness?"*

---

## Phase 3 — Wire to the harness

Goal: register the library with the Claude Code harness so skills, personas, and agents become invocable.

**Do not implement the wiring in this protocol.** Two companion skills already specify the wiring contract:

- **`skills-library-setup.md`** — scaffolds any missing structural pieces (folders, the active-projects ledger, the asset registry, the librarian subagent install).
- **`skills-library-connection.md`** — wires the library into `~/.claude/` (slash commands, hooks, persona session-start, librarian agent install path).

**Action step:**

1. Confirm the user has read the two companion skills (or is willing to dispatch them now without re-reading). Ask: *"Run `skills-library-setup` first, or skip if your library is already scaffolded?"*

2. If the user opts in: invoke `skills-library-setup.md` end-to-end. It writes its own artifacts; this protocol does not duplicate them.

3. Then invoke `skills-library-connection.md` end-to-end. It edits `~/.claude/settings.json`, installs slash commands, and registers the librarian.

4. Both companion skills surface their own sign-off prompts. This protocol's role is dispatch + wait; it does not edit `~/.claude/` itself (Universal Rule 6).

**Interrupt back to user** after both companion skills return. Phase 3 is complete when the user confirms that at least one slash-command invocation works end-to-end (e.g., `/chief-of-staff` activates the persona).

---

## Phase 4 — (Optional) Identity layer

Goal: if the user opted in during Phase 1 Section D, write a personalized `CLAUDE.md` identity file using the captured identity values.

**Pre-condition:** the user answered "yes" to Phase 1 question 7 and supplied at least `{{USER_NAME}}`.

**Interview checklist:**

1. *"Where should the personalized identity file live? Default: `~/.claude/CLAUDE.md` (the global identity layer Claude Code reads on every session). Alternatives: a per-tier identity file inside the library (`{{LIBRARY_ROOT}}/CLAUDE.md`), or a per-project identity file."*
2. *"What broad work areas should the identity file declare? E.g., research / writing / consulting / teaching / engineering / artistic practice. List the ones that apply to you in priority order."*
3. *"What operating principles do you want to highlight beyond the two governing ones? Examples from the library: 'ask before guessing,' 'terse by default,' 'verify citations.' Choose any subset; add your own; or leave it at the two governing principles only."*
4. *"What red lines should the identity file declare — things you never want any persona to do without explicit sign-off? The library's defaults include: no edits to under-review or published artifacts, no fabricated citations, no substantive decisions on the user's behalf."*

**Action step:** draft a short `CLAUDE.md` (≤ 80 lines) using the captured values. Show the draft to the user verbatim and ask for revisions. Iterate until signed off; then write to the user-specified path. Record in the substitution manifest.

The identity file is not a skill or persona — it is a connector layer that every Claude Code session reads before any user prompt. Keep it terse and load-bearing.

---

## Phase 5 — Validate

Goal: confirm the library is functional end to end before declaring setup complete.

**Action step:**

1. **Skill resolution.** Ask the user to invoke a known shipped skill via the librarian (e.g., name `lit-review-protocol` to the librarian and confirm it resolves to a file). If the librarian fails to resolve, return to Phase 3 — `skills-library-connection.md` did not register correctly.

2. **Persona activation.** Ask the user to invoke a persona via slash command. Confirm the session-start hook reads the persona file and the persona's stance is loaded. If the slash command does not activate, return to Phase 3.

3. **Placeholder residue check.** Re-run the `{{` grep over the library root. The only allowed hits are placeholders marked `OPEN` in the substitution manifest. Anything else is a Phase 2 miss; fix and update.

4. **Identity file (if Phase 4 ran).** Confirm the identity file is read on a fresh session by checking that the principles or work areas it declared appear in the agent's first reply.

If all four checks pass, the setup is complete. The substitution manifest is the canonical record of what was filled in; future refreshes diff against it.

---

## Handoff with other skills

- `skills-library-setup.md`: dispatched in Phase 3 to scaffold the library structure.
- `skills-library-connection.md`: dispatched in Phase 3 to wire the library into `~/.claude/`.
- `about-governing-principles.md`: read by the user in Phase 0; referenced by every Tier B/C skill in the library.
- `skill-writing-protocol.md`: governs the skill files the user is installing; read it if they want to write their own skills after setup.
- `persona-writing-protocol.md`: governs the persona files; read it if they want to draft additional personas (e.g., a `librarian` for a tier the public mirror doesn't ship, or a custom voice persona).

## Common failure modes

- **Substitution before sign-off.** The agent runs the substitution before the user has confirmed the intake transcript. Symptom: a value the user would have changed gets baked in; the snapshot is the only path back. Recovery: Universal Rule 1 is non-negotiable — no substitution before sign-off.
- **Plausible-default fill-ins.** The agent guesses at `{{LIBRARY_ROOT}}` (e.g., picks `~/AI-OS/` because that was the example) instead of asking. Symptom: the user discovers their library installed somewhere unexpected. Recovery: Universal Rule 2 — no invented values; ask or mark `OPEN`.
- **No snapshot.** The agent skips Phase 2 step 1 because the library "looks small enough". Symptom: a substitution miss leaves the library in a half-baked state with no rollback. Recovery: Universal Rule 3 — always snapshot first.
- **Missing manifest.** The substitution is run but no manifest is written. Symptom: future refreshes can't diff; the user can't tell which placeholders were filled vs. left `OPEN`. Recovery: Universal Rule 4 — the manifest is the canonical record; regenerate it from the intake transcript and the snapshot if it was lost.
- **Skipping Phase 5.** The agent declares setup done after Phase 3 without validating skill resolution and persona activation. Symptom: the user discovers a wiring failure at the first real session, not at setup. Recovery: Phase 5 is mandatory; rerun.
- **Editing `~/.claude/` from this protocol.** The agent edits `settings.json` directly instead of dispatching to `skills-library-connection.md`. Symptom: the harness wiring is duplicated or inconsistent across libraries. Recovery: Universal Rule 6 — this protocol stops at the library boundary; harness edits go through the connection skill.
- **Identity-layer creep.** The agent drafts a long, opinionated personal `CLAUDE.md` in Phase 4 instead of a short connector layer. Symptom: the identity file restates skill content, contains the agent's prose voice rather than the user's, or balloons past 80 lines. Recovery: rewrite tight; the identity file is a connector, not a manifesto.
- **Re-running without reading the prior manifest.** A refresh run substitutes against the new public-mirror placeholders without loading the prior manifest, so prior `OPEN` values get re-asked from scratch. Symptom: the user is asked the same questions twice; values may drift. Recovery: Phase 0 step 4 — read any prior `substitution-manifest-*.md` first; the interview only asks about placeholders the prior manifest left `OPEN` or that the new mirror introduced.
