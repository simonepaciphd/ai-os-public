---
file: install-kit/levels/L0-instructions-file.md
version: 0.1.0
last_reviewed: 2026-09-27
governed_by: skills/ai-operating-system-setup-protocol.md (Phase 4), skills/about-governing-principles.md
---

# L0 — Instructions file

## Goal
One short file that your agent reads at the start of every session: who you are, the two governing principles, any further working rules, and your red lines. Everything else in the library builds on this, but this level works on its own.

## Prerequisites
- None. L1 is not required.
- The user has read, or you have summarized for them, `skills/about-governing-principles.md`.

## Adaptation note
The library documents this file as Phase 4 of `skills/ai-operating-system-setup-protocol.md`, run after the library is installed. This kit runs the same interview on its own. The only difference: when L1 has not run, there is no substitution manifest, so record the file's path and the values used in `install-state.md` instead.

## Interview
Ask the four questions of Phase 4 in `skills/ai-operating-system-setup-protocol.md`, a few at a time:
1. Where should the file live? (See your adapter for the location your tool reads.)
2. Which broad work areas should it declare, in priority order?
3. Which working rules beyond the two governing principles? (For example "ask before guessing", "terse by default", "verify citations".) Any subset, their own, or none.
4. Which red lines? Offer the library's defaults as listed in Phase 4, and let the user edit them.

Also ask for the name (and, optionally, affiliation and field) to put in the file. Any value not given is written `OPEN` or left out, never guessed.

## Steps
1. Draft the file, 80 lines or fewer, from the answers only.
2. Show the draft verbatim. Revise until the user signs it off.
3. If a file already exists at the chosen path, show it and ask whether to merge, replace (after an archive copy) or choose another path. This is PRINCIPLES §7.7.
4. Writing to a global location such as `~/.claude/` is PRINCIPLES §7.2: ask before writing.
5. Record the path and values in `install-state.md`.

## Validation
In a fresh session of the agent tool, the first reply reflects the declared principles or work areas (the check in Phase 5 of the setup protocol). Ask the user to start that session and report what they see; you cannot open a fresh session yourself.

## Gate
Show the file path and the final text. Ask: "Is this the instructions file you want every session to start from?" Record the answer verbatim.
