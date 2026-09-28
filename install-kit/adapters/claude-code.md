---
file: install-kit/adapters/claude-code.md
version: 0.1.0
last_reviewed: 2026-09-27
---

# Adapter — Claude Code

Use this adapter when the agent is Claude Code (terminal, desktop app or IDE extension). Beginner walkthrough: `docs/setup-guides/claude-code-setup.md`. Desktop app notes: `docs/setup-guides/claude-desktop-setup.md`.

## Where things go (as the library states them)

| Level | Location | Source in the library |
|---|---|---|
| L0 | `~/.claude/CLAUDE.md` (every session), or a `CLAUDE.md` in the library or project folder | `skills/ai-operating-system-setup-protocol.md`, Phase 4 |
| L1 skills | `~/.claude/skills/<name>/SKILL.md` (after Phase 2.5), or a pointer in the project's `CLAUDE.md` | `skills/skills-library-setup.md` Phase 4; `skills/skills-library-connection.md` Phase 2 |
| L1 connector | Claude Code reads `~/.claude/CLAUDE.md` and the `CLAUDE.md` files from the project root upwards | `skills/skills-library-setup.md` Phase 4 |
| L3 hooks | `<project>/.claude/settings.local.json` (project-local; the installer does not touch `~/.claude/`) | `install.py`; `docs/setup-guides/native-bookkeeping-install.md` "What is created" |

## Not stated in the library — confirm with the user

- **Librarian subagent location.** Claude Code reads subagent definitions from `.claude/agents/<name>.md` in a project (code.claude.com/docs/en/sub-agents). Whether to install `agents/librarian.md` there, or at user level, is the user's choice; check the same page for the user-level location.
- **Persona slash commands.** `/chief-of-staff` and similar need a command or skill that loads the persona file. The library does not ship one. Offer to create one only if the user asks, and record it as a kit-made file.

## Notes

- Keep permission prompts on for writes outside the library and project folders. Do not widen permissions to save time.
- After L3, the user reviews hooks in `/hooks` and allows the local configuration when prompted.
- The recovery protocol (L4) is written for Claude Code.
