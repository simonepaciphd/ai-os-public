---
file: install-kit/levels/L3-bookkeeping.md
version: 0.1.0
last_reviewed: 2026-09-27
governed_by: docs/setup-guides/native-bookkeeping-install.md, install.py, skills/project-registration.md
---

# L3 — Bookkeeping

## Goal
For each selected project, the agent tool records sessions, claims, checkpoints and closeouts automatically through hooks, and one local writer maintains the project's records. The installer also creates the projects ledger that L4 uses.

## Prerequisites
From "Requirements" in `docs/setup-guides/native-bookkeeping-install.md`:
- Python 3.11 or newer, and Git, both on the path;
- Claude Code or Codex with the documented hook interface;
- an existing project folder the user owns (from L2, or any folder);
- all agent sessions closed. The installer refuses to run while one is active.

Tested on Windows and on Ubuntu under WSL. macOS is not verified (`docs/native-bookkeeping-validation.md`). Only one user on one machine is supported.

## Interview
1. Which project folder, and what short name (slug)? The slug is lower-case letters, digits, `-` and `_`. `ai-os-system` is reserved.
2. Which tool: Claude Code, Codex or both? (Default: both.)
3. Where the install root goes (default `~/AI-OS`) and, optionally, the private state folder. The installer refuses locations inside the project or inside a Git checkout.

## Steps
Follow "Install" and "Verify the installation" in the guide.
1. **Dry run first:** `python install.py --project "<folder>" --slug <slug> --dry-run`. Show the user the JSON plan, and every path it lists, before anything is written.
2. On approval, run the same command without `--dry-run`. Installing is PRINCIPLES §7.1; writing hook settings is §7.2.
3. Keep the printed runtime path, and record it in `install-state.md`.
4. Run `python "<install root>/runtime/aios.py" --doctor`. Expect `status=ok` and `runtime_integrity=verified`.
5. The user restarts the tool and reviews the new hooks in `/hooks`, trusting only the exact definitions shown ("Verify the installation"). You cannot do this for them.
6. **Register the project** by following `skills/project-registration.md`. For an existing folder, the user says "Register this existing project: <path>". Registration applies only with the exact preflight token. This is PRINCIPLES §7.6.

## Validation
From "Verify the installation", in a **fresh** session started by the user:
- SessionStart reports an active activation and clear controls;
- one checkpoint request succeeds;
- one close request returns `status=closed` and `close_verification.status=verified`.

A simulated event from the command line does not count. Repeat for each tool selected.

## Rollback
"Troubleshooting and removal" in the guide describes removing the runtime's own hook handlers and marker blocks while keeping the records. There is no uninstall command. Show the user that section before the install, not after.

## Gate
Show the dry-run plan, the doctor output, the registration result and the fresh-session results. Ask: "Do you want bookkeeping running on this project?" Record the answer verbatim.
