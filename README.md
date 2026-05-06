# ai-os-public

A starter library for building an AI Operating System on top of [Claude Code](https://docs.claude.com/claude-code): protocol skills, agent personas, and a `librarian` subagent. Methodology and governance scaffolding to customize, not a turnkey product. See [`CLAUDE.md`](CLAUDE.md) for the full audience contract and what is *not* shared.

## Quick start

Pick the tool you use. Each guide is a step-by-step walkthrough that does not assume terminal experience.

- **Claude Code (terminal).** [Setup guide →](docs/setup-guides/claude-code-setup.md)
- **Claude desktop app.** *Coming soon.* [Placeholder →](docs/setup-guides/claude-desktop-setup.md)
- **Codex app.** *Coming soon.* [Placeholder →](docs/setup-guides/codex-setup.md)

## What's in the repo

- `skills/` — protocol skills (`*.md`), the building blocks the personas reach for.
- `personas/` — five session-level agent personas (table below).
- `agents/` — installable subagents (currently: `librarian`).
- `CLAUDE.md` — tier-level orientation, audience contract, placeholder vocabulary.

## Personas

| Persona          | Purpose                                                                      | Notes                                                              |
| ---------------- | ---------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| `chief-of-staff` | Portfolio oversight, project monitoring, routing.                            | Refuses substantive work.                                          |
| `researcher`     | Senior-scholar collaborator across theory, design, empirics, interpretation. | Refuses prose; refuses substantive decisions on the user's behalf. |
| `writer`         | Co-writer for prose deliverables.                                            | Ships as a stub: voice-bearing skills are user-defined.            |
| `engineer`       | Technical infrastructure and the agentic OS itself.                          | Refuses research substance and prose.                              |
| `teacher`        | Course design, assignment design, lecture prep, pedagogical reflection.      | Default skills are user-defined and not shipped.                   |

## License

MIT — see [`LICENSE`](LICENSE).

## Citation

If you use these protocols in published work:

> Paci, Simone (2026). *AI Operating System — public protocols.* GitHub repository. https://github.com/simonepaciphd/ai-os-public

The governing principles trace back to: Paci, Simone (April 2026 working draft), *With Great Powers*, https://simonepaciphd.github.io/with-great-powers/.
