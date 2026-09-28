---
file: install-kit/adapters/codex.md
version: 0.1.0
last_reviewed: 2026-09-27
---

# Adapter — Codex

Use this adapter when the agent is Codex (CLI, app or IDE extension). The library's beginner guide for Codex (`docs/setup-guides/codex-setup.md`) is marked "coming soon", so this adapter lists only what other library files state.

## Where things go (as the library states them)

| Level | Location | Source in the library |
|---|---|---|
| L1 skills | `$HOME/.agents/skills/<name>/SKILL.md` (after Phase 2.5), or a pointer in the project's `AGENTS.md` | `skills/skills-library-setup.md` Phase 4; `skills/skills-library-connection.md` Phase 2 |
| L1 connector | Codex's own file is `AGENTS.md`. To let it read the library's `CLAUDE.md` files, add `project_doc_fallback_filenames = ["CLAUDE.md"]` to `~/.codex/config.toml` (sign-off required) | `skills/skills-library-setup.md` Phase 4 |
| L1 personas | Personas activate by description match. Codex has no user-typed persona slash commands | `skills/ai-operating-system-setup-protocol.md` Phase 5 |
| L3 hooks | `<project>/.codex/hooks.json`. On Windows the hooks run through `runtime/hook.ps1` in PowerShell | `install.py`; `docs/setup-guides/native-bookkeeping-install.md` |

## Not stated in the library — confirm with the user

- **L0 location.** The library documents the instructions file for Claude Code only. It names `~/.codex/AGENTS.md` only as a place for a library pointer. Ask the user where their Codex setup should read the instructions file from, and record it as `OPEN` until they decide.
- **Librarian subagent.** The library gives no Codex install path.

## Notes

- After L3, the user reviews and trusts the new hooks in `/hooks`. Project-local hooks also need a trusted project configuration layer ("Verify the installation" in the bookkeeping guide).
- Do not change PowerShell execution policy. The guide leaves that to the user's own approved procedure.
