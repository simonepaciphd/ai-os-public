# AI Operating System

Product version: **v2.0.1** ([release notes](docs/releases/v2.0.1.md), [changelog](CHANGELOG.md)).
The canonical product version is stored in `VERSION`; runtime contract and storage identifiers are separate.

The AI OS is a library of plain-text instructions that tells an AI agent how to work on your research. It runs on [Claude Code](https://docs.claude.com/claude-code) and Codex: personas give each session a role, protocol skills write recurring work out as steps, and an optional local install keeps a record of sessions, outputs and handoffs.

It is a starter library, not a turnkey product: methodology and governance scaffolding to adapt to your own work. [`CLAUDE.md`](CLAUDE.md) sets out the audience contract and what is *not* shared.

**Guide:** [Working with AI Agents](https://simonepaciphd.github.io/ai-os-public/) · **Install:** [Build your AI OS, level by level](https://simonepaciphd.github.io/ai-os-public/install.html) · **Demo:** [a plan page](https://simonepaciphd.github.io/ai-os-public/plan-demo.html)

## Two principles

- **Researcher control.** You keep authority over every substantive decision. The agent may carry out the work; it does not take the judgment.
- **Radical transparency.** The AI-assisted process is recorded so that you, and others, can inspect its inputs, intermediate work, decisions and outputs.

The fuller argument is in [With Great Powers](https://simonepaciphd.github.io/with-great-powers/); the shared statement every protocol points to is [`skills/about-governing-principles.md`](skills/about-governing-principles.md).

## How the system works

Three layers, each a set of files the agent reads:

- **Across your work.** An identity file (who you are, how you work), personas, the skills library with its librarian, and a projects ledger.
- **The active task.** One session with one goal, one persona and the skills it needs. It stops at agreed gates for your decision and leaves its outputs and a handoff before the next task begins.
- **Inside each project.** A standard folder with an entry point, the plan and its decisions, and the artifacts the work produces, each with its provenance.

What a session records becomes the next session's context. The [guide](https://simonepaciphd.github.io/ai-os-public/) walks through the lifecycle of a task.

## Components

### Personas

Each session takes one role, with a set remit and limits. Five ship here, in [`personas/`](personas/):

| Persona          | Purpose                                                                      | Notes                                                              |
| ---------------- | ---------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| `chief-of-staff` | Portfolio oversight, project monitoring, routing.                            | Refuses substantive work.                                          |
| `researcher`     | Senior-scholar collaborator across theory, design, empirics, interpretation. | Refuses prose; refuses substantive decisions on the user's behalf. |
| `writer`         | Co-writer for prose deliverables.                                            | Ships as a stub: voice-bearing skills are user-defined.            |
| `engineer`       | Technical infrastructure and the agentic OS itself.                          | Refuses research substance and prose.                              |
| `teacher`        | Course design, assignment design, lecture prep, pedagogical reflection.      | Default skills are user-defined and not shipped.                   |

To write your own, use [`persona-writing-protocol.md`](skills/persona-writing-protocol.md).

### Skills and the librarian

A protocol skill is a recurring procedure written out as steps: required inputs, the points where the agent stops for your decision, and the expected outputs. The [`librarian`](agents/librarian.md) subagent finds the right skill in the library. The skills in [`skills/`](skills/) cover literature review and citation checks, R&R revision plans and response memos, project setup, session recovery, and writing new skills ([`skill-writing-protocol.md`](skills/skill-writing-protocol.md)) and handoff prompts ([`task-engineering-protocol.md`](skills/task-engineering-protocol.md)).

### Project setup

Every project gets the same folders, including a standard replication package in `appendix/` ([`project-setup.md`](skills/project-setup.md)). A project that already has its own structure is retrofitted with [`project-setup-existing.md`](skills/project-setup-existing.md).

### Planning

Before implementation, the agent helps you define the finished result, then plans the work that produces it. [`planning-protocol.md`](skills/planning-protocol.md) coordinates eight stage protocols (`planning-*-protocol.md`):

1. **Specify.** An interview produces `SPEC.md`, what the finished project must contain; an independent reviewer challenges it.
2. **Resources.** `RESOURCES.md` lists what you already have and links it to the spec.
3. **Map, challenge, adjudicate.** The agent writes a task plan in which every requirement maps to tasks with a check; an adversarial reviewer tests it; the findings are resolved into `PLAN.md`.
4. **Lock.** You approve `SPEC.md`, `RESOURCES.md` and `PLAN.md` together as the baseline.
5. **Launch and reconcile.** Tasks run in dependency-safe waves; any change to the spec found along the way is reported and decided, not absorbed.

You make every research choice. The [plan viewer](skills/_assets/plan-viewer/README.md) checks a project's `planning/` folder and builds a single-file plan page (Python 3, standard library only); the file templates are in [`skills/_assets/planning-templates/`](skills/_assets/planning-templates/).

**[See a demo plan page →](https://simonepaciphd.github.io/ai-os-public/plan-demo.html)** It is built from a fictional survey-experiment plan, one of the viewer's test fixtures.

A student edition of the workflow is published with the POLISCI 290 capstone course: [browse the folder](https://github.com/simonepaciphd/polisci290-capstone/tree/main/research-planning) or [download the zip](https://simonepaciphd.github.io/polisci290-capstone/research-planning.zip).

### Native bookkeeping (optional)

A local install that registers sessions, records claims, summaries and artifacts, and publishes a closeout at the end of each session. Hooks handle the routine records; the agent submits the substantive ones. Requires Python 3.11+ and Git and installs only for the projects you select: see the [technical installer guide](docs/setup-guides/native-bookkeeping-install.md).

Already have a project folder? After installing, say **“Register this existing project: [path].”** The [registration workflow](skills/project-registration.md) previews and completes registration without changing the folder structure.

## Quick start

Open your agent in this repository (or the unzipped [install kit](https://simonepaciphd.github.io/ai-os-public/install.html)) and say:

> Read `install-kit/START-HERE.md` and help me choose my levels.

There are five levels, from an instructions file to portfolio oversight. Each ends at a gate where the agent shows what it did and waits for your decision; you can stop after any level.

Step-by-step guides that do not assume terminal experience:

- **Claude Code (terminal).** [Setup guide →](docs/setup-guides/claude-code-setup.md)
- **Claude desktop app.** *Coming soon.* [Placeholder →](docs/setup-guides/claude-desktop-setup.md)
- **Codex app.** *Coming soon.* [Placeholder →](docs/setup-guides/codex-setup.md)

## What's in the repo

- `skills/` — protocol skills (`*.md`); `skills/_assets/` holds supporting files (the plan viewer and the planning templates).
- `personas/` — the five session personas.
- `agents/` — installable subagents (currently: `librarian`).
- `install-kit/`, `install.py`, `runtime/` — the level-by-level installer and native bookkeeping.
- `site/` — the guide, the install page and the demo plan page, published to GitHub Pages.
- `CLAUDE.md` — tier-level orientation, audience contract, placeholder vocabulary.

## License

MIT — see [`LICENSE`](LICENSE).

## Citation

If you use these protocols in published work:

> Paci, Simone (2026). *AI Operating System — public protocols.* GitHub repository. https://github.com/simonepaciphd/ai-os-public

The governing principles trace back to: Paci, Simone (April 2026 working draft), *With Great Powers*, https://simonepaciphd.github.io/with-great-powers/.
