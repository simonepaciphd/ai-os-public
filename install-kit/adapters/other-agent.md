---
file: install-kit/adapters/other-agent.md
version: 0.1.0
last_reviewed: 2026-09-27
---

# Adapter — other agents

Use this adapter for any agent that can read and write files in a folder but is neither Claude Code nor Codex (for example Cursor or a chat assistant with file access).

| Level | Works? | How |
|---|---|---|
| L0 | yes | Ask the user which instructions file their tool loads every session. Write it there. |
| L1 | partly | Use the instruction-file pointer or the README Skills block in `skills/skills-library-connection.md` (Phase 2, mechanisms C and D; `.cursorrules` is named for Cursor). Native skill invocation is not covered. |
| L2 | yes | The project skills are plain files and work with any agent. |
| L3 | no | The installer writes hooks for Claude Code and Codex only. |
| L4 | partly | Routines that are plain reading and writing (reading the ledger, the librarian review done as a prompt) can work. None is tested outside Claude Code and Codex. L4 also needs L3. |

Tell the user at the start which levels their tool cannot reach, before they choose.
