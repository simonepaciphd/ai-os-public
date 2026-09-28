---
file: install-kit/install-state.md
version: 0.1.0
last_reviewed: 2026-09-27
---

# Install state (ledger)

Read this at the start of every session. Update it at every gate and at the end of every session. This is the only coordination file for the install.

## Current position

- install_started: 
- adapter: 
- selected_levels:    <!-- e.g. L0, L1, L2; the user's words go in "Level choice" below -->
- current_level: 
- current_step: 
- last_session: 
- status: not-started   <!-- not-started | in-progress | waiting-for-user | done -->

## Level choice (user's words, verbatim)

## Gates

| Level | Name | Selected | Gate status | Date | User's decision (verbatim) |
|---|---|---|---|---|---|
| L0 | Instructions file | | pending | | |
| L1 | Library | | pending | | |
| L2 | Project | | pending | | |
| L3 | Bookkeeping | | pending | | |
| L4 | Portfolio | | pending | | |

Gate status values: `pending` · `approved` · `approved-with-changes` · `sent-back` · `not-selected`.

## Values captured

<!-- one line each: name · value or OPEN · where it was used. L1 keeps its own substitution manifest; list only values L0 or later levels use. -->

## Open items

<!-- one line each: date · level · item · who must act -->

## Stop-and-ask events

<!-- one line each: date · rule number from PRINCIPLES §7 · what was asked · user's answer -->
