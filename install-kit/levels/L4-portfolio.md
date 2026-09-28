---
file: install-kit/levels/L4-portfolio.md
version: 0.1.0
last_reviewed: 2026-09-27
governed_by: personas/chief-of-staff.md, agents/librarian.md, skills/recover-session-protocol.md, skills/security-officer-protocol.md
---

# L4 — Portfolio

## Goal
Work across several projects: a projects ledger that shows what is active, a chief-of-staff persona that reads it at the start of a session, the librarian's periodic library review, and a way to recover a lost session. This level is a set of routines. It is not a program to install.

## Prerequisites
- **L3.** The installer creates `memory/projects-ledger.md` and `memory/projects-ledger/_template.md` under the install root, and registration adds each project's row. The library has no other procedure that creates the ledger.
- **L1.** Personas and the librarian must be installed and resolvable.

## Interview
Offer each piece separately; the user may take any subset:
1. **Chief of staff as the session default.** See `personas/chief-of-staff.md` ("Auto-detection signals", "Integration overrides"). It points at the ledger through `{{LEDGER_PATH}}`, so confirm that value matches the ledger L3 created.
2. **Librarian review.** Run on demand; a monthly cadence is suggested in the chief-of-staff persona. Its outputs are review files and update queues that only the user marks applied or dismissed.
3. **Session recovery.** `skills/recover-session-protocol.md` rebuilds a lost session from disk. It is written for Claude Code.
4. **Security officer.** `skills/security-officer-protocol.md`. Several of its automatic triggers are not shipped ("v0"), so it is invoked by hand.

## Steps
1. Confirm the ledger path and that each registered project has a row. Do not edit ledger rows by hand; registration and the writer own them (PRINCIPLES §7.6).
2. For each piece the user chose, show the governing file's activation section and set it up as that file says.
3. Record each piece and where it is set up in `install-state.md`.

## Where the library is silent
Stop and ask the user; do not improvise:
- **How chief-of-staff becomes the session default.** The persona expects a session-start hook that the library does not ship.
- **The skill-usage logging hooks** that the librarian's usage audit reads are not shipped. That duty will report no data until they exist.
- **Done-checks.** The library defines none for this level. Propose one per piece (for example: invoke the persona and see the ledger summary; run one librarian review), and let the user approve it at the gate.

## Validation
Run the checks the user approved. Show each result.

## Gate
Ask: "Are these the portfolio routines you want?" Record the answer verbatim. The install is complete when every selected level has passed its gate.
