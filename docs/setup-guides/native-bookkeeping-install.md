# Native bookkeeping: technical installation

Product release: **v2.0.1**. See the [upgrade and rollback plan](../releases/v2.0.1.md).

This installs the public native runtime for one existing local project. It provides
registration, heartbeat, claims, shutdown checks, semantic provenance, exact text
snapshots, closeout and bookkeeping recovery through Claude Code or Codex hooks.
It makes no provider calls and requires no Python packages.

## Requirements

- Python 3.11 or newer and Git, both available in your terminal.
- A current Claude Code or Codex installation with the documented hook interface.
- An existing project folder you own.
- Close active installation sessions before running the installer or changing hooks.

## Install

Download or clone this repository, open a terminal in it, then run:

~~~text
python install.py --project "PATH_TO_EXISTING_PROJECT" --slug example
~~~

Replace the project path with your own existing directory. By default, the installer
uses an AI-OS folder in your home directory and connects both harnesses.
Use --harness claude-code or --harness codex-cli to select one.

Optional arguments:

| Argument | Purpose |
| --- | --- |
| --root "PATH" | Choose the installation directory. Keep it outside the public source checkout and outside the project. Projects may live under its projects/ subdirectory. |
| --state-dir "PATH" | Choose private local state storage, separate from source, installation and project trees. Default: .local/state/ai-os/<installation-id> under your home directory. |
| --dry-run | Print the proposed file changes without writing anything. |

No administrator privileges, package installation, global harness edits or API keys
are needed. Existing unrelated hook handlers, permission settings and instructions
are preserved. The installer refuses incompatible ledgers, an existing conflicting
project-level AI OS installation, changed managed files, and active native sessions. Repeating
the same install after sessions close is a no-op. To register another folder, use
the registration workflow below. To add its project-local lifecycle hooks, run
the installer with its --project and --slug after closing active sessions.

The installer prints the installed runtime path. Keep that location stable.
It records the Python executable used for installation; changing or removing that
Python installation requires a reviewed reconfiguration.

## What is created

| Location | Contents |
| --- | --- |
| Installation runtime/ | Manifest-verified standard-library runtime. |
| Installation config/ownership.json | Generated paths, project selection, runtime ownership and state format. |
| Installation coord/ | Coordination specification, board, controls, sessions and operator mailbox. |
| Installation memory/projects-ledger.md and memory/projects-ledger/ | Private portfolio index and project records, ignored by Git. |
| Project .claude/settings.local.json | Claude lifecycle handlers, using executable/argument form. |
| Project .codex/hooks.json | Codex lifecycle handlers. Windows uses the supplied PowerShell launcher. |
| Project .aios/native.md | Machine-specific agent instructions, ignored by Git. |
| Project AGENTS.md and CLAUDE.md | Small portable blocks pointing to .aios/native.md. Existing content is retained. |
| Project asset-registry.csv and interaction-log.csv | Native provenance ledgers; existing compatible ledgers are retained. |
| Project .cowork/snapshots/ | Created when an agent explicitly submits a text artifact. |
| Private state directory | Per-session journals, integrity records, closeout outboxes and installation backups. |

Paths are generated from the recipient's choices. The distributed runtime has no
author-specific paths, projects, account IDs, state or credentials. License
attribution in the existing repository remains intact. Generated configuration,
local hook files, instructions and snapshots are ignored by Git; do not publish
private journals or installation backups.

## Verify the installation

Run the printed runtime path with Python and --doctor:

~~~text
python "PATH_TO_AI_OS/runtime/aios.py" --doctor
~~~

Expect status=ok and runtime_integrity=verified. This checks the installation;
it does not prove that your harness actually delivers hooks.

1. Open a fresh session in the configured project. Inspect /hooks for duplicate
   AI OS handlers inherited from user or system configuration; this installer
   manages project configuration only.
2. In Codex, review the new hooks using /hooks and trust their exact definitions.
   Project-local hooks also require a trusted project configuration layer.
   In Claude Code, inspect /hooks and allow the local configuration as prompted.
3. Inspect the SessionStart result. It should report an active activation and
   clear controls. Verify a corresponding record in coord/sessions/.
4. Submit a checkpoint and close request using the examples below.
5. Read `status=closed` and `close_verification.status=verified` from that same
   close result. The result checks released claims, archive and closeout publication.
   Send the final response without another tool; any independent inspection belongs
   to the operator outside the closed activation.

A CLI-simulated event is not evidence of host delivery. Interrupted, unsupported,
disabled or untrusted hooks must remain explicit gaps. A stopped response does
not necessarily end the native session.

## Register an existing folder

Say **“Register this existing project: [path].”** Follow
[project-registration](../../skills/project-registration.md) for the supported
`register-project` preflight/apply operation, retry rules and delayed artifact logging.
The receiving task completes the authorized bookkeeping; restructuring remains a
separate setup request. Unknown planning metadata stays `PENDING`.

Invoke the installed runtime by absolute path from the actual task cwd. A task
at the AI OS root retains its `ai-os-system` binding; a task in the new project
can be admitted to that project. Never substitute the target path for the actual
cwd or conversation identity. The installer reserves `ai-os-system` for the
coordination-only root.

Preflight reports mappings, ledger state, missing project files, conflicts and
proposed writes. Apply requires that exact preflight token. Configuration,
admission, local publication and actual host receipt delivery are reported
separately. `native-not-yet-admitted` means the conversation has no admission
alias; it does not establish a deployment failure. Registration does not install
project-local hooks or prove that the host delivers them.

## Unknown directories in Claude

When the installed hook is actually delivered from an unknown directory, SessionStart
and UserPromptSubmit ask which existing project it belongs to or whether to create
a new project. Explicit registration instructions already supplied by the user count
as the answer. Ordinary tools remain gated until registration succeeds.

Use the exact `registration_command` in that context with the chosen slug and
`existing` or `new`. The portable CLI uses `--register-cwd --harness claude-code
--native-id ACTUAL_ID --workspace ACTUAL_CWD --project SLUG --registration-kind KIND`.
On Windows the generated command invokes PowerShell and works from Git Bash too;
on POSIX it invokes the selected Python directly. Space-containing paths are supported.
Paths requiring unsupported shell quoting require operator registration; do not edit
the generated command. AskUserQuestion and the exact read-only Describe command remain
available, subject to ordinary host permissions. Extra arguments, alternate configuration,
command chaining and background execution are denied.

Existing-project attachment adds a workspace alias while preserving the canonical
root and ledgers. New-project registration uses the actual cwd as its root. The
writer checks ownership, controls, claims, overlaps and terminal identity, then uses
the existing preflight/apply journal. Retry the identical command after an interrupted
publication. Registration takes identity from argv and ignores stdin.

This does not install global hooks or make an undelivered hook run in arbitrary
directories. Other harnesses retain explicit registration/restart guidance.
A missing admission in an already mapped directory requires a native SessionStart
and fresh receipt; prompt/tool events and semantic resume cannot invent admission.

## Malformed ledger repair

Inspect the selected installation's `config/ownership.json`: the project's configured
`root` contains `asset-registry.csv` and `interaction-log.csv`. The portfolio index
is under installation `memory/projects-ledger.md`, with stanzas in
`memory/projects-ledger/`. Do not infer a different OS root from a CSV failure.
`--describe` is state-free contract discovery and never validates these files.

Registration refuses missing columns, duplicate headers, short/overflow rows and
invalid CSV quoting. It does not infer hashes, discard cells or merge records.
Repair requires a separately authorized operator action:

1. Stop new admissions and close active writers; inspect claims and pending journals.
2. Back up exact bytes and record each preimage SHA-256. Build and review an explicit
   proposed correction using verified source records; keep uncertain values unresolved.
3. Use the existing registration mutex and shared resource locks for every affected
   ledger. Recheck the original hashes under those locks immediately before replacement;
   if anything changed, stop and reconcile the new record instead of overwriting it.
4. Preserve permissions, verify exact postimages, validate with the native parser and
   account for all records and fields. Retain private backups. Then retry registration.

No general ledger auto-repair API or installation migration is supplied. Do not run a
one-off repair from another installation or restore old ledgers over newer records.

## Semantic checkpoints

Agents read the installed coord/SPEC.md and the project instructions. Routine hooks
refresh heartbeat; agents still supply claims, substantive summaries, decisions
and artifact metadata. Claims use absolute paths or paths relative to the installed
AI OS root, not implicitly relative to the project.

To inspect the exact request schema:

~~~text
python "PATH_TO_AI_OS/runtime/aios.py" --describe
~~~

Create a UTF-8 JSON request outside publicly shared source. Fill ACTIVATION from
the fresh receipt and choose a new key for each new request:

~~~json
{
  "operation": "checkpoint",
  "key": "example-checkpoint-001",
  "activation": "ACTIVATION",
  "claims": ["ABSOLUTE_PATH_TO_PROJECT/output.txt"],
  "task": "Produce the specified output",
  "input_summary": "Requested a checked output artifact",
  "summary": "Output created and checked",
  "artifacts": [
    {
      "path": "output.txt",
      "creator": "agent",
      "verification": "partially-verified",
      "text": true
    }
  ]
}
~~~

The artifact must already exist. Claim it before writing by first submitting a
checkpoint containing the claim, then submit the artifact metadata after the write.
Never send raw prompts, transcripts, secrets or sensitive artifact bodies as
summaries. text=true intentionally snapshots the file's exact bytes.

~~~text
python "PATH_TO_AI_OS/runtime/aios.py" --validate --request "PATH_TO_REQUEST.json"
python "PATH_TO_AI_OS/runtime/aios.py" --request "PATH_TO_REQUEST.json"
~~~

Validation checks request shape only. Submission rechecks ownership, controls,
workspace, claims and artifact containment. Agents cannot assign human-verified.

Use a fresh key for changed content. Reuse the identical request/key only when
retrying an uncertain bookkeeping delivery; never reuse it for different content.

## Close and recover

~~~json
{
  "operation": "close",
  "key": "example-close-001",
  "activation": "ACTIVATION",
  "claims": [],
  "summary": "Completed and checked the specified output",
  "input_summary": "Requested the output",
  "decisions": [],
  "relaunch": "no"
}
~~~

Finish edits, logging and checks first. Submit it with --request as the final tool
call and verify status=closed plus close_verification.status=verified in that
same result. Then send the final response without more tools.
Public relaunch values are yes, no and operator-decides. This public contract
uses native-semantic-public-1; it is not an in-place migration of an existing
private deployment.

For pending or unconfirmed publication, an operator outside the closed activation
inspects the state and may submit this bookkeeping-only request:

~~~json
{"operation": "reconcile", "key": "example-reconcile-001"}
~~~

Reconcile repairs bookkeeping only. Do not rerun task effects. --status reports
sessions and bounded pending-publication observations. --intake with --harness,
--native-id and --workspace provides bounded mailbox/status intake; consult
--help for pagination. It does not replace required startup reading.

To request shutdown, the operator creates coord/control/SHUTDOWN-REQUESTED.md.
Agents finish only their current atomic step, close and stop. Removing that flag
is an operator action after shutdown/recovery is resolved.

## Troubleshooting and removal

- Missing receipt: check project trust, hook trust, selected project path and /hooks.
- Python/Git missing: install them using their official distributions and reopen
  the terminal. Windows paths used in shell commands must avoid shell expansion
  characters. Spaces and ordinary apostrophes are supported.
- PowerShell refuses the downloaded launcher: inspect its source and your local
  script policy. Follow your organization's approved script-trust procedure;
  this installer does not bypass or change execution policy.
- Integrity mismatch: inspect the changed runtime file against the distribution.
  Do not regenerate the installed manifest just to make the check pass.
- Claim collision: contact the holder. A stale heartbeat does not release its
  private active claim.
- Interrupted installer: inspect .install.lock and private installation-backups/.
  A plan records original files and intended postimage hashes. Restore only a
  file still matching the recorded postimage; preserve newer edits. After checking
  that no installer is running, resolve the lock deliberately before retrying.
- Malformed ledger: follow the explicit repair procedure below; registration refuses
  without rewriting rows. Describe reports the source contract, not ledger contents.

To disconnect, close all active sessions and verify publication, remove only this
runtime's handlers from the project's two hook files, remove the managed AIOS NATIVE
blocks from AGENTS.md/CLAUDE.md, and remove .aios/native.md. Keep project ledgers,
snapshots and private journals until you decide their retention. Existing unrelated
handlers and permission settings must remain. Runtime updates and state migrations
require a separate tested procedure; this first installer refuses changed binaries.

## Coverage

The package includes automated fixture tests for installation, both hook adapters,
generated command execution, claims, privacy, snapshots, shutdown and interrupted
publication. Run:

~~~text
python -B -m unittest discover -s tests -v
~~~

Validation performed for this package is recorded in docs/native-bookkeeping-validation.md.
Same-user local-machine coordination is the supported scope. This package does
not claim compact-startup delivery, automatic portfolio launch, remote/multi-user
coordination, token accounting or universal hook enforcement.

Hook contracts checked against the official
[Codex hook reference](https://learn.chatgpt.com/docs/hooks) and
[Claude Code hook reference](https://code.claude.com/docs/en/hooks) on 2026-09-15.
