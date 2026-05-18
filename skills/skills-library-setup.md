---
name: skills-library-setup
description: Stand up a personal (or lab-level) skills library from scratch. Picks a location, picks a librarian pattern (how agents find and load skills), seeds the library with a small starter set, wires it into the active harness and projects, and tests on one invocation.
audience: public
version: 0.1
---

# Skills-Library Setup Protocol

A five-phase skill for standing up a personal (or lab-level) skills library from scratch: pick a location, pick a *librarian* pattern (how agents find and load skills), seed the library with a small starter set, wire it into the active harness and projects, and test on one invocation.

Designed to compose with `project-setup.md` and `project-setup-existing.md` — both dispatch to this protocol when they detect no existing library — and with `skill-writing-protocol.md`, which adds every newly authored skill back into the library via Phase 3.

Governing principles: **user control** and **radical transparency** — see `{{LIBRARY_ROOT}}/skills/about-governing-principles.md` (or, before this library exists, the equivalent file in whichever distribution you are working from). The protocol never decides on its own where the library should live or how it should be organized. The user picks, the protocol surfaces trade-offs, and every commit waits for explicit sign-off.

---

## When to use

- The user has no existing skills library and wants to start one.
- An existing ad-hoc collection of skills, prompts, or templates (`prompts/`, `templates/`, a single `CLAUDE.md`, a Notion page) should be consolidated into a proper library.
- A lab or team wants to stand up a shared library all members can reach.

Do **not** use this skill when a library already exists and the user only wants to add one more skill (use `skill-writing-protocol.md`), when the real need is a single project-local playbook that does not justify cross-project reuse, or when the user has not yet drafted even one skill — write the first skill first, then come back.

## Artifacts the skill produces

1. `<library-root>/` — the library folder at the chosen path.
2. `<library-root>/README.md` — the index: one row per skill with name, one-sentence purpose, trigger keywords, and relative path.
3. `<library-root>/<starter-skill>.md` files — starter skills copied in, typically `skill-writing-protocol.md`, `project-setup.md`, plus any skills the user has already drafted.
4. Library install into each chosen harness skills path: `~/.claude/skills/` for Claude Code, `$HOME/.agents/skills/` for Codex.
5. Codex connector wiring: `project_doc_fallback_filenames = ["CLAUDE.md"]` added to `~/.codex/config.toml` if Codex was a chosen harness.
6. Optionally (if interview Q2 was yes), a library pointer in the harness-global config file (`~/.claude/CLAUDE.md` or `~/.codex/AGENTS.md`).

## Universal rules

1. **Interview first, commit second.** Every phase has an interview step. Do not create folders, copy files, or edit harness config until the user has answered the questions in the current phase.
2. **Surface trade-offs, don't pick for the user.** Location, librarian pattern, and starter seed are all choices the user owns. Present options as numbered lists with a clear trade-off line each.
3. **Small seed beats big dump.** A library that starts with three well-tested skills is more useful than one that starts with twenty speculative ones. Copy in only skills the user has actually used or is committed to using this month.
4. **The library is a first-class asset.** It should be version-controlled or otherwise backed up from day one. Propose a backup strategy even if the user defers the mechanics.
5. **Librarian over library.** The orchestration pattern — how agents find and load the right skill — matters more than any individual skill file. A well-indexed library of ten skills beats an unindexed heap of a hundred.

---

## Phase 0 — Confirm the need

Goal: verify that a new library is actually the right response, and discover any existing material that should be consolidated rather than bypassed.

**Interview checklist:**

1. *"Do you already have a folder of skills, prompts, or templates anywhere? Including under informal names: `prompts/`, `templates/`, `.cursorrules`, a `CLAUDE.md`, a Notion page, a Dropbox note. If yes, we should consolidate rather than start fresh."*
2. *"How many skills do you expect to have within six months — three, ten, fifty?"* This calibrates the librarian choice in Phase 2.
3. *"Is this library for you alone, or for a lab or team?"* Changes the location and the versioning defaults.
4. *"Which harness(es) do you work in — Claude Code, Codex, Cursor, Antigravity, multiple? Different harnesses have different preferred paths and different native skill mechanisms."*

**Action step:** write a one-paragraph scope statement covering single-user vs. team, expected size, and primary harness. Get sign-off before continuing.

---

## Phase 1 — Choose the library location

Goal: pick an absolute path for the library root, with a backup strategy named.

**Interview checklist:**

1. *"Should the library be available on every machine you use? If yes, we want a synced location (Dropbox, iCloud, OneDrive, or a git repo you clone everywhere)."*
2. *"Do you want version history? A git repo gives you diffs and rollback; a cloud-synced folder gives you multi-device sync but only shallow history."*
3. *"Does your harness expect skills in a specific path? Claude Code looks under `~/.claude/skills/`; Codex (CLI + IDE extensions) looks under `$HOME/.agents/skills/`. If yes, either use that path directly or symlink from it to your chosen canonical location."*
4. *"For teams: is the library going in a shared git repo, a shared cloud folder, or an institutional drive? Who has write access? Is there a review requirement before skills are added?"*

**Candidate locations — present as a numbered list with trade-offs:**

1. **Cloud-synced folder** (e.g., `~/Dropbox/skills-library/` or `~/OneDrive/skills/`). Easy multi-device; informal history; no diffs.
2. **Git repo** (e.g., `~/repos/skills/`, optionally mirrored to GitHub). Full history; diffable; requires commit discipline.
3. **Harness-native path** (e.g., `~/.claude/skills/`). Lowest-friction invocation; harness lock-in; often unsynced across machines unless combined with option 1 or 2.
4. **Hybrid** — canonical copy in a synced folder or git, symlinked into the harness-native path. Best of both worlds at the cost of one extra step at setup.

**Action step:** record the chosen path as `<library-root>` in the scope statement. Create the folder. Do not copy skills in yet.

---

## Phase 2 — Choose the librarian pattern

Goal: pick how agents will find and load skills when invoked. This is the *librarian* of the library — the mechanism through which content becomes discoverable.

**Interview checklist:**

1. *"When an agent needs a skill, how should it find the right one? Three common patterns: (a) read a top-level index file and pick by keyword; (b) scan the folder and read each file's frontmatter to match on triggers; (c) rely on the harness's built-in skills registration."*
2. *"Do you want a flat layout (all skills at the library root) or a nested one grouped by category (e.g., `orchestration/`, `research-methods/`, `writing/`, `meta/`)?"* Flat is almost always the right answer for the first ten skills.
3. *"Naming convention: `<skill-name>.md`, `<skill-name>-protocol.md`, or something else? Consistency matters more than the specific convention."*

**Librarian patterns — present as a numbered list with trade-offs:**

1. **Index-first.** A `README.md` at the library root lists every skill in a table (name, one-sentence purpose, trigger keywords, path). The agent reads the README, picks a skill, then loads only that file. Harness-agnostic. Requires manual index maintenance when skills are added.
2. **Frontmatter-discovery.** Each skill file begins with a YAML frontmatter block listing `name`, `description`, `triggers`, and `tags`. The agent scans the library, reads frontmatter only, and loads the full body only after selection. No central index to maintain; requires harness support for a scan-then-load step.
3. **Harness-native.** The harness (e.g., Claude Code's skills mechanism) knows about the library and invokes skills by name or trigger directly. Lowest-friction invocation; strongest lock-in if you ever switch harness.
4. **Hybrid.** Harness-native primary, with an index `README.md` as a human-readable fallback and as a source of truth if the harness's registration format changes. Recommended default for a user who expects to work across multiple harnesses over time.

**Action step:** write the chosen pattern into the scope statement, then scaffold:

- If index-first or hybrid: draft a `README.md` with a table header and no rows yet.
- If frontmatter-discovery: write a `CONVENTIONS.md` (or a short header comment) specifying the required frontmatter schema.
- If harness-native: document in `README.md` which harness and which registration path is expected, so a reader landing in the folder years later knows how it was meant to be used.

Present the scaffold to the user. Do not copy skills in until sign-off. If the chosen librarian pattern requires a library format the current library does not match — most common case: harness-native or hybrid on a library of flat `.md` files — run Phase 2.5 next. Otherwise skip to Phase 3.

---

## Phase 2.5 — Align library format with librarian pattern *(conditional)*

**Run this phase only if** the librarian pattern chosen in Phase 2 requires a structure the current library does not provide. The common trigger: primary harness is Claude Code, chosen pattern is harness-native or hybrid, and the library is currently flat `.md` files. Claude Code's native skill discovery requires each skill to be a **directory** containing a `SKILL.md` with YAML frontmatter (minimum: a `description:` field). Flat `.md` files sitting in `.claude/skills/` will not auto-invoke.

Other cases that trigger this phase: migrating from one harness-native format to another; adopting frontmatter-discovery on a library that has no frontmatter today.

Goal: transform the canonical library from its current format into the one the chosen librarian pattern requires, with explicit per-skill sign-off on any metadata the agent has to infer.

**Interview checklist:**

1. *"Confirming: the transformation will edit the canonical library at `<library-root>`, not just produce a transformed copy elsewhere. Canonical library writes are effectively irreversible. Do you have a backup — git history, cloud versioning, a recent snapshot — for rollback?"* If no, pause and stand one up before continuing.
2. *"For each skill, the target format needs at minimum a `description:` field (one sentence, agent-facing, used by the harness to decide when to invoke). Should I propose one per skill from the opening paragraph of each current file, or do you want to write descriptions yourself first?"*
3. *"Do you want to keep a flat-`.md` mirror alongside the transformed structure — e.g., a `_flat/` subdirectory or a top-level index that still lists original filenames — for human browsing? Transformed directories can be noisier to browse than flat files."*
4. *"Are there skills you want to leave in the old format because they are experimental, external, or about to be deprecated?"*

**Action step:**

1. Inventory the library: list every current skill file, its current path, and its target path (for Claude-Code-native: `<library-root>/<skill-name>/SKILL.md`; `<skill-name>` is the flat filename without the `.md` extension).
2. For each skill, draft a minimum frontmatter block:

   ```yaml
   ---
   name: <skill-name>
   description: <one-sentence proposal from the skill's opening paragraph>
   ---
   ```

   Add other fields (`allowed-tools`, `user-invocable`, `context`, `paths`) only when the user asks for them. Most skills do not need anything beyond `name` and `description`.
3. Present the full transformation plan as a single document — before × after paths, plus proposed frontmatter per file — and wait for explicit sign-off on each `description:`. Auto-proposals that look weak should be flagged, not hidden.
4. Execute the approved transformation:
   - Create `<library-root>/<skill-name>/` directory.
   - Move the flat file into `<library-root>/<skill-name>/SKILL.md`.
   - Prepend the approved frontmatter block.
   - Leave no duplicate flat `.md` at the old path unless the user requested the mirror.
5. If the librarian pattern (Phase 2) is index-first or hybrid, update `<library-root>/README.md` with the new relative paths.
6. Report the transformation: files moved, frontmatter added, mirrors created if any, and any skills still needing a user-written `description:` because the auto-proposal was too weak.

**Rule of thumb:** the wrap is a one-time cost measured in minutes per skill, mostly spent reviewing `description:` proposals. Budget ~15 minutes for a 10-skill library.

**After this phase:** `skills-library-connection.md` can use mechanism A (copy into `<project>/.claude/skills/`) or B (symlink) against the transformed library, unlocking Claude Code auto-invocation at the harness level. If Phase 2.5 is skipped, mechanism C (instruction-file pointer) remains the recommended wiring for flat libraries.

---

## Phase 3 — Seed with starter skills

Goal: copy a small, deliberate set of skills into the library, with each row in the index or each frontmatter block filled in.

**Interview checklist:**

1. *"Which skills do you already have drafted that should go in? Names or paths."*
2. *"For the starter set, do you want the meta-skills (`skill-writing-protocol`, `project-setup`) from this library's starter set? They compose directly with this one."*
3. *"Anything half-drafted you want me to leave out until it has been tested at least once?"* Enforces the "small seed beats big dump" rule.
4. *"For each skill going in, what are the 2–5 trigger keywords that should reliably surface it?"*

**Action step:** for each approved skill:

1. Copy the file into `<library-root>/` (flat) or the chosen category folder (nested).
2. If using index-first or hybrid: append a row to `README.md` with name, one-sentence purpose, trigger keywords, and relative path.
3. If using frontmatter-discovery: verify the file has a valid frontmatter block; write one if missing, confirming each field with the user.
4. Report a compact summary diff to the user (files copied, rows added) before moving to Phase 4.

---

## Phase 4 — Wire the library into the harness(es)

Goal: install the library into each chosen harness so agents can find skills, personas, and (where supported) hooks without further prompting. Active-project wiring is the separate concern of `skills-library-connection.md`.

**Interview checklist:**

1. *"Which harness or harnesses should know about this library right now? Claude Code, Codex (CLI + IDE extensions: VS Code, Cursor, Windsurf, JetBrains), or both?"*
2. *"Should we also add the library pointer to a harness-global config file (e.g., `~/.claude/CLAUDE.md` for Claude Code, `~/.codex/AGENTS.md` for Codex) so future projects inherit it automatically?"*

**Action step:**

1. **Install skills into each chosen harness's skills path.** For each harness named in the interview:

   - **Claude Code.** Symlink (preferred, if Phase 1 chose hybrid) or copy the canonical library into `~/.claude/skills/`. Each skill must be a directory containing `SKILL.md` with YAML frontmatter (`name`, `description` minimum) — the format produced by Phase 2.5 if it ran.
   - **Codex (CLI + IDE extensions).** Symlink (preferred — copying creates drift, requiring manual re-run of Phase 4 after any canonical edit) or copy the canonical library into `$HOME/.agents/skills/`. The cross-tool `.agents/` path is Codex's convention (not `.codex/skills/`). Same `SKILL.md` + frontmatter format as Claude Code; no format conversion needed.
   - **Personas on Codex (P1 personas-as-skills).** Persona files that ship as `SKILL.md`-format directories under `personas/` ride the same install loop — the persona's frontmatter `description` doubles as the skill's invocation trigger, and Codex activates the persona's stance by description match.

2. **Register the connector layer with each chosen harness.** The library's `CLAUDE.md` files (root + per-tier) are the connector layer.

   - **Claude Code.** Automatic — Claude Code reads `~/.claude/CLAUDE.md` and walks `CLAUDE.md` files up from the project root.
   - **Codex.** Codex's native connector filename is `AGENTS.md`. To make Codex read the existing `CLAUDE.md` files without duplication, add `project_doc_fallback_filenames = ["CLAUDE.md"]` to `~/.codex/config.toml`. **Ask for explicit sign-off before editing `~/.codex/config.toml`** — this skill stops short of writing harness config until the user approves.

3. If interview Q2 was yes, add the library pointer to the chosen harness-global config file (`~/.claude/CLAUDE.md` for Claude Code; `~/.codex/AGENTS.md` for Codex), so future sessions inherit it automatically.

---

## Phase 5 — Test and iterate

Goal: the first real invocation is the final phase of setup.

**Action step:**

1. Start a fresh agent instance in any project and give it a task that should trigger one of the seeded skills. Watch whether it finds and loads the right skill without further prompting.
2. If it does not, diagnose at the level of the failure: was it the index (skill not listed), the trigger keywords (too narrow or too broad), the location (harness cannot reach it), or the prompt (did not cue the skill)? Fix at that level; do not escalate to a library-wide refactor.
3. Log the session in `interaction-log.csv` if this protocol was invoked from inside a project.

**Review cadence:**

- After the first three skill invocations, revisit the index and trigger keywords and adjust.
- Every six months, audit the library: prune stale skills, consolidate duplicates, and promote project-local skills that have proven reusable.

---

## Librarian patterns — reference

| Pattern | Discovery mechanism | Strengths | Weaknesses |
|---|---|---|---|
| Index-first | Agent reads `README.md` table | Harness-agnostic; transparent; debuggable by a human | Manual index maintenance |
| Frontmatter-discovery | Agent scans files and reads frontmatter only | No central index to rot; self-describing files | Needs harness support for scan-then-load |
| Harness-native | Harness registration API | Lowest-friction invocation | Harness lock-in; opaque to other tools |
| Hybrid | Harness-native + index fallback | Robust to harness changes; debuggable | Slightly more to maintain |

## Handoff with other skills

- `project-setup.md` and `project-setup-existing.md`: dispatch to this protocol when they detect no existing library. Return the chosen `<library-root>`; they then dispatch to `skills-library-connection.md` to wire the library into the active project.
- `skills-library-connection.md`: runs immediately after this protocol to apply the chosen wiring between `<library-root>` and the active project, based on the harness and the library format set up here.
- `skill-writing-protocol.md`: every new skill produced by that protocol is added to this library via Phase 3 (append a row or write frontmatter, copy the file in).
- `lit-review-protocol.md` and any other composed skill: no direct handoff, but this protocol is their upstream dependency — without a library, none of them have a canonical home.

## Common failure modes

- **Premature library.** The user sets up a library before having any skills to put in it. Symptom: an empty `README.md` that rots. Recovery: write at least one skill via `skill-writing-protocol.md` before running this protocol, or wait until three drafts accumulate.
- **Over-categorization.** The user picks a nested layout with eight folders when they have four skills. Symptom: skills scattered across near-empty directories, each nearly impossible to search. Recovery: start flat, refactor into categories only when a category has three or more skills.
- **Orphaned global path.** Library sits in the harness-native path with no cross-machine sync, so it disappears when the user switches machines. Recovery: move the canonical copy to a synced location (Dropbox or git) and symlink into the harness path.
- **Unmaintained index.** New skills added to the folder but not to the index. Symptom: agents cannot find them even though the files exist. Recovery: either switch to frontmatter-discovery, or add an index-update line to the universal rules of `skill-writing-protocol.md` so new skills cannot land without an index entry.
- **Trigger-keyword collisions.** Two skills match the same keyword; the agent picks the wrong one. Recovery: add disambiguating keywords and a "see also" pointer on the losing skill; in extreme cases, narrow the broader skill's name.
- **Silent harness lock-in.** The user picks harness-native registration without realizing how hard the skills will be to use if they switch harness. Recovery: retrofit an index `README.md` after the fact; this is usually cheap and worth doing prophylactically.

## Worked example

A first-time user of agentic AI, with one drafted skill for running qualitative interviews, runs this protocol:

1. *Phase 0:* scope statement reads "single-user library, expected 5–10 skills within six months, primary harness Claude Code."
2. *Phase 1:* picks a hybrid location — canonical copy at `~/Dropbox/skills-library/`, symlinked to `~/.claude/skills/`.
3. *Phase 2:* picks index-first because the library will stay small; scaffolds a flat `README.md` with a three-column table (skill, purpose, triggers).
4. *Phase 3:* copies the interview skill in and appends a row. Declines to add the library's meta-skills for now because they want to read them first.
5. *Phase 4:* installs skills into `~/.claude/skills/` via symlink (Claude Code only — Codex not on this user's stack); declines a harness-global config entry for now.
6. *Phase 5:* first invocation in that project does not surface the interview skill because the prompt used the word "qualitative" but the triggers only listed "interview"; adds "qualitative" and "semi-structured" to the triggers and re-runs. Works.

Total time: about 45 minutes of user attention, mostly in Phases 1–2.
