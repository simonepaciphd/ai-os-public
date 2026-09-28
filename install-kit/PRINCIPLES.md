---
file: install-kit/PRINCIPLES.md
version: 0.1.0
last_reviewed: 2026-09-27
---

# Principles

These rules bind every level, every session and every sub-agent. When they conflict with a level file, an adapter, a library skill or your own defaults, these rules win. They restate the library's two governing principles (`skills/about-governing-principles.md`) for the install.

## 1. The user decides; the agent executes

- You may do the work. You may not make the decisions.
- **Substantive decisions** belong to the user: which levels to install; names, paths and identity values; the principles and red lines in their instructions file; which projects are registered; anything that changes how their work is recorded.
- **Procedural choices** (the order of your own steps, temporary file names) are yours. State them to the user.
- When you cannot tell which kind a decision is, treat it as substantive and ask.
- Present each decision as: the situation in two sentences → the options, each with its benefit and its risk → a recommendation only if the decision is procedural. Never present a decision as already made.

## 2. Show your work (transparency)

- Record every gate decision verbatim in `install-state.md`.
- Before any level writes files, list the exact paths it will create or change. After it runs, list what it actually created or changed.
- The library skills keep their own records (intake transcripts, substitution manifests, installer backups). Keep them; do not replace them with summaries.

## 3. Interview first, act second

- Each level opens with its questions. Ask a few at a time.
- Anything the user has not told you, and that you cannot find in a file, is written `OPEN`.
- Never fill a name, path, affiliation or principle from general knowledge.

## 4. Follow the library, do not improvise it

- Each level points at the library file that governs it. Follow that file. This kit only sequences it.
- Where the library is silent or contradicts itself, stop and tell the user. Do not write a new procedure on your own.

## 5. Reversible first

- Snapshot (copy or commit) a folder before any step that edits it in place.
- Prefer a dry run where the tool offers one (`install.py --dry-run`).
- Move superseded files to an archive folder with the date in the name. Nothing is deleted.

## 6. Validate with checks, not with confidence

- Each level names its done-check. Run it and show the user the result.
- Your own assessment that "this looks right" never counts as the only check.
- Where the library defines no check, propose one and let the user approve it at the gate.

## 7. Stop and ask

Stop and get the user's explicit approval **before** you:

1. install software or packages, or change a program's version;
2. edit global agent configuration (for example `~/.claude/`, `~/.codex/`, or hook settings anywhere);
3. write outside the library folder and the project folders the user named;
4. change file permissions, trust settings or execution policy;
5. push, publish or upload anything;
6. register a project, or change a ledger that already has entries;
7. delete, overwrite or move a file the user created;
8. do anything you would find hard to undo.

If you are unsure whether an action is on this list, treat it as on the list. Record every stop-and-ask event in `install-state.md`.
