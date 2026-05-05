# ai-os-public

A public mirror of the sharable layer of an AI Operating System for use with [Claude Code](https://docs.claude.com/claude-code): protocol skills, agent personas, and a librarian subagent.

This repository ships a **starter library** — methodology and governance scaffolding intended to be customized to the redistributing user's context, not a turnkey product to be used as-is. Voice-bearing skills and project-internal material are deliberately excluded; see `CLAUDE.md` for the full audience contract and the list of what is *not* shared.

## Contents

- `skills/` — protocol skills (`*.md` files).
- `personas/` — five agent personas selectable per session: `chief-of-staff`, `researcher`, `writer`, `engineer`, `teacher`.
- `agents/` — installable subagents (currently: `librarian`).
- `CLAUDE.md` — tier-level orientation, audience contract, and placeholder vocabulary.

## Requirements

- [Claude Code](https://docs.claude.com/claude-code) installed.
- Familiarity with command-line use and Markdown editing.

## Setup

The library is parameterized with `{{PLACEHOLDER}}` tokens (`{{LIBRARY_ROOT}}`, `{{PROJECTS_DIR}}`, `{{REPO_NAME}}`, etc. — full list in `CLAUDE.md`). Setup substitutes those tokens for your environment and wires the result into the Claude Code harness.

1. Clone this repository to a folder you control:

   ```
   git clone https://github.com/simonepaciphd/ai-os-public.git
   ```

2. Read `skills/about-governing-principles.md`. The two principles (user control, radical transparency) frame everything else in the library.

3. Run `skills/ai-operating-system-setup-protocol.md` end-to-end. It runs an intake interview, captures values for every placeholder, applies substitution across the library, and dispatches to `skills/skills-library-setup.md` and `skills/skills-library-connection.md` to finish wiring.

Placeholders left unfilled remain live as `{{TOKEN}}` and are flagged in the substitution manifest — you can return to them later.

## Personas

| Persona          | Purpose                                                                                  | Notes                                                              |
| ---------------- | ---------------------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| `chief-of-staff` | Portfolio oversight, project monitoring, routing to specialized personas.                | Refuses substantive work.                                          |
| `researcher`     | Senior-scholar collaborator across theory, design, empirics, interpretation.             | Refuses prose; refuses substantive decisions on the user's behalf. |
| `writer`         | Co-writer for prose deliverables.                                                        | Ships as a stub: voice-bearing skills are user-defined.            |
| `engineer`       | Technical infrastructure and the agentic OS itself.                                      | Refuses research substance and prose.                              |
| `teacher`        | Course design, assignment design, lecture prep, pedagogical reflection.                  | Default skills are user-defined and not shipped.                   |

## License

MIT — see [`LICENSE`](LICENSE).

## Citation

If you use these protocols in published work:

> Paci, Simone (2026). *AI Operating System — public protocols.* GitHub repository. https://github.com/simonepaciphd/ai-os-public

The governing principles trace back to: Paci, Simone (April 2026 working draft), *With Great Powers*, https://simonepaciphd.github.io/with-great-powers/.
