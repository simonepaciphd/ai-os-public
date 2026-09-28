---
file: install-kit/START-HERE.md
version: 0.1.0
library_version: 2.0.1
last_reviewed: 2026-09-27
---

# Start here

## For the user

Open your agent in the folder that contains this `install-kit/` folder (the `ai-os-public` repository, or the unzipped download) and say:

> Read `install-kit/START-HERE.md` and help me choose my levels.

The agent explains the five levels, you pick the ones you want, and it installs them one at a time. Each level ends at a **gate**: the agent shows you what it did and waits for your decision. Nothing outside the library and the project folders you name is changed without your approval. You can stop after any level.

For a visual overview, see `site/install.html` or the online guide.

## For the agent

You are installing the AI Operating System library for **the user**, the person who gave you this instruction. The library is the folder that contains `install-kit/` (the **library root**).

**Paths.** Kit files (`PRINCIPLES.md`, `install-state.md`, `levels/…`, `adapters/…`) are inside `install-kit/`. Every other path in this kit (`skills/…`, `personas/…`, `agents/…`, `docs/…`, `install.py`, `runtime/…`) is relative to the library root.

Follow these steps in order.

1. Read `PRINCIPLES.md` in full. It overrides anything else in this kit and any default behavior of yours.
2. Read `install-state.md`.
   - If `selected_levels` is empty, this is a fresh install. Go to step 3.
   - Otherwise, resume at the level and step recorded there. Tell the user in one or two sentences where things stand and what happens next, then continue.
3. **Choose the adapter.** From what you can observe about your own runtime, propose one of `adapters/claude-code.md`, `adapters/codex.md` or `adapters/other-agent.md`. The user confirms it. Record it in `install-state.md`.
4. **Choose the levels.** Show the user the table below. They may pick any levels whose prerequisites are met or also selected. Record their choice verbatim in `install-state.md`. Install the selected levels in ascending order.
5. For each selected level, open its file in `levels/` and do exactly what it says, in section order: Goal → Prerequisites → Interview → Steps → Validation → Gate.
6. At each **Gate**:
   - show the user what you produced or changed, with paths;
   - ask for an explicit decision (approve / change / send back);
   - record the decision verbatim in `install-state.md`;
   - move to the next selected level.
   Never pass a gate on your own judgment.
7. End every session by updating `install-state.md` (level, step, open items, stop-and-ask events).

Where a level file says the library is **silent** on a step, do not invent a procedure. Tell the user what is missing and ask how they want to proceed. Write any unknown as `OPEN`, never as a plausible default.

## The levels

| Level | What you get | Needs first | Technical demand |
|---|---|---|---|
| L0 Instructions file | One file of your identity, principles and red lines, loaded every session | nothing | low: one text file |
| L1 Library | Personas and protocol skills, customized and connected to your agent tool | nothing (L0 optional) | low to medium: copying folders, find-and-replace |
| L2 Project | A project folder with a plan, an asset registry and an interaction log | L1 recommended | low: folders and two CSV files |
| L3 Bookkeeping | Automatic session records, claims, checkpoints and closeout for selected projects | a project folder you own (L2 or existing) | medium to high: Python 3.11+, Git, hook review |
| L4 Portfolio | A projects ledger, a chief-of-staff routine, the librarian, session recovery | L3 (it creates the ledger) and L1 (personas, librarian) | medium |

## Folder map

| Path | What it is |
|---|---|
| `PRINCIPLES.md` | The rules. Read first, every session. |
| `install-state.md` | The single ledger: where the install stands. |
| `levels/L0…L4` | One instruction file per level. |
| `adapters/` | Notes for specific agent tools. Step 3 picks one. |
| `skills/`, `personas/`, `agents/`, `docs/`, `install.py`, `runtime/` | The library this kit installs. The level files point into it; they do not copy it. |
