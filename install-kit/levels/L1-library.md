---
file: install-kit/levels/L1-library.md
version: 0.1.0
last_reviewed: 2026-09-27
governed_by: skills/ai-operating-system-setup-protocol.md (Phases 0–3 and 5), skills/skills-library-setup.md, skills/skills-library-connection.md
---

# L1 — Library

## Goal
Your own copy of the personas (`personas/`), protocol skills (`skills/`) and the librarian subagent (`agents/librarian.md`), with the `{{PLACEHOLDER}}` tokens filled in and connected to your agent tool so a persona or skill can be invoked.

## Prerequisites
- Nothing below this level. L0 is optional.
- The checks in Phase 0 of `skills/ai-operating-system-setup-protocol.md`.
- For Claude Code, the requirements in `docs/setup-guides/claude-code-setup.md` ("Prerequisites"). Do not place the library inside `~/.claude/`.

## Interview
Phase 1 of the setup protocol (Sections A–E). It records every answer in an intake transcript and reads it back for sign-off. Do not begin substitution before that sign-off.

If L0 has already run, skip Section D and Phase 4 and say so in the transcript.

## Steps
1. **Setup protocol, Phase 1:** intake interview and signed-off transcript.
2. **Phase 2:** snapshot the library (PRINCIPLES §5), then substitute. It writes a substitution manifest and ends with a `{{` search.
   - Expected residue: placeholders the user marked `OPEN`, lines that describe the search itself, and `${{ … }}` in `.github/workflows/`, which is GitHub Actions syntax, not a placeholder.
3. **Phase 3:** wire the library to the tool through `skills/skills-library-setup.md` and, per project, `skills/skills-library-connection.md`.
   - The skills ship as flat `.md` files. For your tool's native skill invocation, `skills-library-setup.md` Phase 2.5 converts them. Otherwise use the pointer mechanism in `skills-library-connection.md`. Present both to the user; the choice is theirs.
   - Any edit to global configuration (`~/.claude/`, `~/.codex/config.toml`) is PRINCIPLES §7.2.
4. **Phase 5:** validation.

## Where the library is silent
Stop and ask the user; do not improvise:
- **Installing the librarian.** The library does not say where `agents/librarian.md` is installed. Your adapter lists what your tool expects; confirm with the user.
- **`/chief-of-staff` start-up.** Phase 5 mentions a session-start hook for persona activation. The library does not ship one. Test activation by invoking the persona directly and report what happens.
- **Skill-usage logging.** The librarian refers to logging hooks that are not shipped. Record it as `OPEN`.

## Validation
Phase 5 of the setup protocol: skill resolution through the librarian, persona activation on each chosen tool, and the placeholder residue check. Show each result.

## Gate
Show the transcript, the manifest, what was wired where, and the validation results. Ask: "Is the library installed the way you want it?" Record the answer verbatim.
