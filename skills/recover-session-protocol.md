---
name: recover-session-protocol
description: Identify a lost prior Claude Code session for the current project, present recovery candidates with disk evidence, and produce both a `claude --resume` command and a self-contained fresh-session prompt that re-establishes context. Never resumes a session itself; never auto-appends to logs; surfaces the recovery as the user's call.
audience: public
version: 0.1
---

# Recover-Session Protocol

Identify the lost prior Claude Code session for the current project, present recovery options to the user, and produce **both** a `claude --resume` command and a self-contained fresh-session prompt that re-establishes context from disk evidence. The skill never resumes a session itself, never assumes a candidate transcript is correct without the user's confirmation, and never auto-appends to logs — recovery is the user's call.

Composes with `project-setup.md` (uses `interaction-log.csv` as primary evidence when present) and the persona system, if the user has one (the fresh-session prompt re-invokes the appropriate persona).

Governing principles: **user control** and **radical transparency** — see `{{LIBRARY_ROOT}}/skills/about-governing-principles.md`. The agent surfaces candidate transcripts with evidence; the user picks. Disk state is reported as observed, not as assumed.

---

## When to use

- User says: "I closed the terminal", "lost the previous session", "pick up where we left off", "reopen that context", "where were we", or any equivalent phrasing about a prior conversation that ended unexpectedly.
- Working tree shows uncommitted changes (untracked files, modifications) that don't match the most recently logged session in the project's `interaction-log.csv`.
- User explicitly invokes `/recover-session-protocol`.

Do not use when: the most recent logged session already matches working-tree state (no recovery needed); the user wants to start fresh and is not asking about prior context; the question is about general project state (use `git status` + `git log` directly).

## Artifacts the skill produces

1. A `claude --resume <session-id>` command pointing at one specific transcript.
2. A self-contained fresh-session prompt for paste into a new `claude` invocation, structured per the template in Phase 4 below.
3. A flagged to-do for the resumed / new session: append the missing `interaction-log.csv` row (and any missing `asset-registry.csv` rows) **in that session, not in this one**.

## Universal rules

1. **Never run `claude --resume` yourself.** It would close the current session.
2. **Never assume the candidate transcript is correct.** Surface 1–3 candidates with evidence; require the user to confirm before producing the dual output.
3. **Never silently append to `interaction-log.csv` or `asset-registry.csv`.** Surface those as to-dos for the new session.
4. **Always produce both outputs.** `--resume` command and fresh-session prompt, every invocation. The user chooses which to use.
5. **Default inspection depth is medium:** first user prompt of each candidate transcript + keyword counts + tool-use counts. Do not read full transcripts unless the user asks.
6. **The fresh-session prompt must require a "report back before editing" first turn.** The new agent verifies disk state before extending lost work — this catches half-finished lost-session output.
7. **Distinguish "lost session" from "lost transcript".** Transcripts persist on disk under `~/.claude/projects/<cwd-encoded>/`; the conversation thread is what was lost. State this if the user is unsure.

---

## Phase 0 — Confirm project root and resolve transcript directory

Goal: locate the transcript folder for the current project.

**Interview checklist:**
1. *"Confirm the project root is `<cwd>`?"* (Use the current working directory.)
2. *"Roughly when did the lost session end? (today, yesterday, this week.)"* — narrows the candidate list.

**Action step:**
- Resolve transcript dir as `~/.claude/projects/<cwd-encoded>/`, where `<cwd-encoded>` replaces drive separators and path separators with `-`. Example: a project at `~/Dropbox/website` encodes to `-home-<user>-Dropbox-website` (POSIX) or `C--Users-<user>-Dropbox-website` (Windows).
- List `*.jsonl` files. If none exist, stop and report: no transcripts, recovery not possible from this skill.

---

## Phase 1 — Inventory candidate transcripts

Goal: produce a candidate list with metadata.

**Action step:**
1. List all `*.jsonl` in the transcript dir with `Name`, `LastWriteTime`, `Length` (bytes). Sort by `LastWriteTime` desc.
2. Identify the current session's transcript and exclude it. Either match by `sessionId` if known, or read the first event of the most recently modified file and compare its `SessionStart` content to the current session's start banner.
3. For each remaining candidate (cap at 5 most recent unless the user asks for more):
   - Read the first ~6 lines to extract the first non-attachment user message (`"type":"user"` with a `"role":"user"` content field).
   - Count keyword hits relevant to the project (e.g. `src/content`, `package.json`, or project-specific paths surfaced by working-tree changes).
   - Count `"tool_use"` occurrences as a session-weight proxy.
   - Note start timestamp (first event) and end timestamp (last event or `LastWriteTime`).

---

## Phase 2 — Identify the lost session

Goal: present 1–3 candidates with evidence; user confirms.

**Action step:**
1. **Primary evidence (preferred): `interaction-log.csv`.**
   - If the project has `interaction-log.csv` (project-setup-protocol projects do), read it and list logged session IDs / dates.
   - Sessions whose transcript file exists but whose work is **not** in `interaction-log.csv` are the strongest candidates for "lost".
2. **Fallback evidence (when no `interaction-log.csv`):**
   - Run `git status` and `git diff --stat`. List untracked files and modifications.
   - Match those paths to candidate transcripts via keyword counts. The transcript with the most references to the modified paths is the most likely source.
   - Cross-check with file mtimes on the changed files — they should fall inside the candidate session's window.
3. Present a **short ranked candidate table** to the user:
   - Session ID (full UUID) and short ID (first 8 chars).
   - Start–end times.
   - Size + tool-use count.
   - First user prompt (one-line summary).
   - Evidence: which working-tree changes / which keywords match.
4. Wait for the user to pick a candidate. Do not proceed until confirmed. If the user rejects all candidates, ask them to expand the time window or describe the lost work more specifically, then re-run Phase 1 with a wider net.

---

## Phase 3 — Reconstruct context from disk

Goal: enumerate what the lost session produced, what's verified, and what's missing.

**Action step:**
1. `git status` + `git diff --stat` (already obtained in Phase 2 fallback path; rerun if Phase 2 used the log path instead).
2. List the new files / modifications grouped by subsystem (e.g. `src/`, `content/`, governance files, build configs).
3. Read project governance docs the lost session was operating against — start with `implementation-roadmap.md` (or equivalent), any `outputs/build-reports/*.md` referenced as schema or plan, and the most recent `interaction-log.csv` row that precedes the lost session.
4. Identify three sets:
   - **Done (visible on disk).** Files written, edits applied.
   - **Unverified.** Build not run, types not checked, tests not executed, logs not appended.
   - **Missing.** Roadmap items the lost session was supposed to reach but didn't, by comparing roadmap state vs disk state.
5. Note any **drift risks**: schema files written by the lost session that the new session must validate (Zod schemas, type definitions, content collection configs) before extending.

Do not read the full transcript at this phase unless the user asks. Disk state is authoritative; the transcript is supporting evidence.

---

## Phase 4 — Produce the dual output

Goal: hand the user one `--resume` command and one fresh-session prompt, both ready to paste.

**Action step — Output 1: `--resume` command.**

A single line, in shell-ready form:

```
claude --resume <full-session-uuid>
```

Annotate with: "Run from `<project root>` after exiting the current session."

**Action step — Output 2: Fresh-session prompt.**

A fenced markdown block following this template. Fill every angle-bracketed slot from Phase 3 evidence; do not invent.

````
/<persona-name-if-applicable>

# Resume <task or phase name> for <project name>

Project: <absolute project path>
<one-line project framing>.
Previous session (transcript `<short-uuid>`, <start>–<end> UTC) was lost when the terminal closed. It implemented <high-level summary of what disk evidence shows> but never logged the work or verified the build.

## First: orient on actual disk state

Run `git status` and `git diff --stat`. Expect untracked: <list>. Modified: <list>.

Do NOT assume those files are correct or complete — the previous session may have produced stubs, partial wiring, or schema/content drift. Spot-check before extending.

## Read first (in order)

1. <governance doc 1>
2. <governance doc 2>
3. <project-specific files the lost session was building against>
...

## <Locked decisions or scope> (do not re-litigate)

- <decision 1, sourced from a real doc>
- <decision 2>
...

## Your job in this session

1. Inventory state from disk and report it back honestly before changing anything.
2. <Verification step 1 — e.g. run build, run tests, run type-check>
3. <Identify gap between disk state and roadmap>
4. <Surface gap as numbered to-do before continuing>
5. Append the missing `interaction-log.csv` row for session `<short-uuid>` (label per project convention). Update `asset-registry.csv` with new files. Check off completed roadmap items only after build is green.
6. <Persona-specific handoff, if applicable>.

## Hard constraints (<persona-name-if-applicable> persona)

- <persona hard refusal 1>
- <persona hard refusal 2>
...

## What I (the user) need from you first turn

Before any edits: a short report (under 250 words) of (a) what the lost session actually produced on disk vs. roadmap intent, (b) what's missing, (c) your proposed first 3 fixes in order. I'll approve before you touch <key directory>.
````

**Action step — Hand off to user.**

Present both outputs in a single message. Recommend `--resume` as the cleaner path; offer the fresh-session prompt as the fallback. Optionally offer to save the fresh-session prompt to `outputs/build-reports/resume-prompt-<date>-<letter>.md` (or project-equivalent path) for durability.

Do not proceed past this point in the same conversation. The skill ends with the dual output.

---

## Handoff with other skills

- `project-setup.md`: this skill reads `interaction-log.csv` and `asset-registry.csv` as evidence. Surfaces missing rows as to-dos for the recovered/new session — does not write them itself.
- Persona skills (if the user has any): the fresh-session prompt template re-invokes the persona under which the lost session was running. Identify the persona from the lost transcript's first user message (`/<persona-name>` slash command) or from the project's most recent logged session.
- `skill-writing-protocol.md`: this skill was drafted under that protocol; future revisions should follow Phase 5 (test and iterate).

## Common failure modes

- **Wrong project root.** Agent resolves the transcript dir from a different cwd than the user meant. Recovery: always print the resolved path and confirm before listing transcripts.
- **Multiple candidates, no clear winner.** Keyword counts ambiguous (e.g. two recent sessions both touched `src/`). Recovery: present top 3 with full evidence; let the user pick. Do not guess.
- **Lost session was killed mid-tool-call.** Disk is left in inconsistent state (half-written file, broken schema). Recovery: the fresh-session prompt's "report back before editing" first turn catches this. Reinforce by including a `npm run build` (or equivalent verification) in the new session's job list.
- **No `interaction-log.csv` and no git repo.** Fallback evidence is filesystem mtimes + transcript keyword counts only. Confidence is low; flag that to the user and offer to widen the candidate window.
- **"Lost session" actually means "lost browser tab" or "lost terminal scrollback".** Transcripts persist regardless. Clarify the distinction if the user seems to think the data is gone.
- **User resumes via `--resume` while the original session is still alive.** Two concurrent sessions on the same transcript can happen. The skill cannot prevent this; mention it in the hand-off if there's any risk.

## Worked example

User: *"hey, I mistakenly closed the terminal in the last chat and am not sure where we were... let's pick back up working on it. Any way of re-opening that context?"*

1. **Phase 0:** Resolve transcript dir to `~/.claude/projects/<cwd-encoded>/` for the project root. User confirms project root.
2. **Phase 1:** Five `*.jsonl` files. Drop the current session's transcript (matched by start banner). Three candidates remain: today's three sessions.
3. **Phase 2:** Project has `interaction-log.csv`. Most recent logged session is `2026-05-04-a` (schema + roadmap, "no `src/` or `content/` edits yet"). Working tree shows untracked `src/content/`, `src/pages/practice/`, `src/pages/teaching/`. Keyword count: candidate `fe8c51bd` has 29 `src/content` references and 261 tool uses; candidate `f7ef1acf` has 0 `src/content` references (it's an older audit session). Present `fe8c51bd` as the strongest match. User confirms.
4. **Phase 3:** Disk shows: `src/content/config.ts` with 6 Zod collections; 16 project stubs; 16 publication YAMLs; 5 course YAMLs; 5 page files; 7 new `.astro` page scaffolds. Roadmap still has Phase 4.0/4.1/4.2 unchecked; `interaction-log.csv` missing a `2026-05-04-b` row. No `npm run build` evidence in the working tree.
5. **Phase 4:** Output 1 — `claude --resume fe8c51bd-17f2-4168-bbb0-80eb471a3c04`. Output 2 — fresh-session prompt with required-reading list (schema doc, Q&A doc, IA proposal, roadmap, ledger), locked decisions, job list (orient → build → triage → log → check off), hard constraints from the relevant persona, and a "report back under 250 words before editing" first-turn requirement.
6. User picks one path. Skill ends.

Total time: about 5 minutes of user attention.
