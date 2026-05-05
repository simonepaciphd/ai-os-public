# public/ — Sharable skills library

This audience tier contains skills, agents, and personas intended for public sharing — methodology and governance protocols the user has elected to publish or distribute beyond their personal library.

## Contents

- `skills/` — sharable protocol skills + per-skill asset folders in `_assets/`
- `agents/` — sharable subagents (librarian; others as needed)
- `personas/` — sharable agent personas selectable per session

## Personas

Five personas ship in this tier. Each encodes a stable posture for a recurring task type and is invocable via slash command (`/chief-of-staff`, `/researcher`, etc.) or explicit alias.

- `chief-of-staff` — session-default management persona; portfolio oversight, project monitoring, routing to specialized personas. Refuses substantive work.
- `researcher` — senior-scholar collaborator; supports theory, design, empirics, interpretation. Refuses prose; refuses substantive decisions on the user's behalf.
- `writer` — prose co-writer; preserves the user's voice, refuses substantive content changes. **Ships as a stub** — its voice-bearing skills (paper, op-ed, slide, lecture, grant, cover letter, reviewer response, voice-coherence) are deliberately excluded from the public mirror. The user must draft those protocols and wire them into their librarian to make this persona effective.
- `engineer` — technical infrastructure persona; codebases, build systems, the agentic OS itself. Refuses research substance and prose.
- `teacher` — instructor-practice persona; course design, assignment design, lecture prep, pedagogical reflection. Refuses end-to-end completion of teaching tasks without user input. All six default skills are user-defined and not shipped in the public mirror.

## Audience contract

This tier is a starter library. It is methodology and governance scaffolding to be customized to the redistributing user's context — not a turnkey product to be used as-is.

### Intended consumer

- Researchers, students, instructors, or operators who want a structured agentic-OS starter rather than a blank slate.
- Anyone composing a Claude Code workflow around skills, personas, and a librarian agent.
- Comfort with command-line use, Markdown editing, and basic placeholder substitution is assumed.

### Licensing and attribution

- The contents of this tier are shared for derivative use. The originating principles statement (see `skills/about-governing-principles.md`) carries an attribution to the source author; that single attribution may be retained, replaced with the redistributing user's own framing, or stripped per that file's Sources block.
- All other shipped files are sanitized: identity strings, project state, and personal voice have been removed. License terms accompany the source distribution (see the `LICENSE` file at the distribution root); cite the library if useful, and preserve the radical-transparency provenance for any further redistribution.

### What is *not* shared

The public mirror deliberately omits:

- **Voice-bearing skills.** Paper-writing, op-ed, slide, lecture, grant, cover-letter, reviewer-response, and recommendation-letter protocols all encode the source author's specific prose voice. The `writer` persona ships as a stub for this reason — it can resist generic LLM cadences but cannot reach for protocol-grade writing skills until the user drafts their own.
- **Project state.** The active-projects ledger, per-project stanzas, and decision logs are personal to the source library and not redistributed.
- **User-specific identity.** Names, affiliations, fields, contact information, and the source author's personal connector layer at `~/.claude/CLAUDE.md` are not shipped. Use `skills/ai-operating-system-setup-protocol.md` Phase 4 to draft your own.
- **In-progress or under-review artifacts.** Anything the source author considered live or unfinished at sanitization time is excluded.

### Setup pointer

To install this tier as your own working library:

1. Read `skills/about-governing-principles.md`.
2. Run `skills/ai-operating-system-setup-protocol.md` end to end. It walks an intake interview that captures your values for every placeholder, applies substitution across the library, and dispatches to `skills/skills-library-setup.md` and `skills/skills-library-connection.md` to wire the result into the Claude Code harness.

### Placeholder vocabulary

The library uses the following placeholder tokens. The setup protocol asks you for each. Some are optional and may remain live as `{{TOKEN}}` if you don't have a value yet — they will simply not resolve until filled.

| Placeholder | Meaning |
|---|---|
| `{{LIBRARY_ROOT}}` | Root of your library tier (e.g., `~/AI-OS/`). |
| `{{OS_ROOT}}` | Root of a multi-tier OS, when relevant. |
| `{{PROJECTS_DIR}}` | Directory containing your active projects (e.g., `~/projects/`, `~/Dropbox/`). |
| `{{PROJECT_ROOT}}` | A specific project working directory (set per-project, not at bootstrap). |
| `{{LEDGER_PATH}}` | Active-projects ledger (default: `{{LIBRARY_ROOT}}/memory/projects-ledger.md`). |
| `{{USER_HOME}}` | Your home directory (only when paths can't avoid it; rare). |
| `{{USER_NAME}}` | Your display name (identity layer; optional). |
| `{{USER_AFFILIATION}}` | Your institution or organization (identity layer; optional). |
| `{{USER_FIELD}}` | Your discipline or primary field (identity layer; optional). |
| `{{OVERLEAF_ROOT}}` | LaTeX / Overleaf sync root (only if you use Overleaf or a similar sync target). |
| `{{REPO_NAME}}` | GitHub repo name for syncing the library (optional). |

`~/.claude/...` paths are **not** placeholders — they are harness-native, and `~` already abstracts your username.

## GitHub

Synced as private repo `{{REPO_NAME}}`. Despite the folder name "public," repo access is gated by default — the redistributing user controls who receives read tokens; the repo is not openly published unless the user chooses otherwise.
