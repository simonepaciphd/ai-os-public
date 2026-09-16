---
name: project-registration
description: Register an existing project folder without scaffolding or restructuring; preflight, repeatable native publication, actual conversation admission, and explicitly delayed provenance logging.
audience: public
version: 1.0
---

# Register an existing project

Invocation: **“Register this existing project: [path].”**

Keep the existing folder structure. The receiving task completes the mechanical
workflow; no repeated chief/engineer handoffs are needed. Use `project-setup.md`
for new scaffolding and `project-setup-existing.md` for a requested retrofit.

## Prerequisites and authority

The user must authorize registration of the folder. Infer its title, canonical
path and existing slug from the folder, configured mappings and ledger. Ask only
about unresolved identity conflicts or substantive decisions the user wants filled.
Unknown descriptive fields can remain `PENDING`; never infer priority or activity
from file timestamps. Do not change research content, settings or permissions.

Use the installed public native runtime described in
`docs/setup-guides/native-bookkeeping-install.md`. If it is absent or its
`--describe` response lacks `register-project`, report that prerequisite and
follow the supported installation procedure; do not improvise a second writer.
This feature ships with the updated distribution. The installer still refuses an
in-place update of changed runtime binaries; existing installations need a
separately reviewed update procedure.

Read the installed coordination specification, controls, board, mailbox, persona
and project requirements. Check every live claim before writes. An overlapping
holder must be contacted; a stale heartbeat is not permission to seize a claim.

## One native entrypoint

Run from the **actual conversation cwd**, using the current native conversation
id and harness. Never change cwd or substitute a project path to fabricate admission.

```text
python "PATH_TO_AI_OS/runtime/aios.py" --request "PRIVATE_REQUEST.json"
```

Preflight request:

```json
{
  "operation": "register-project",
  "key": "registration-UNIQUE-ID",
  "phase": "preflight",
  "root": "ABSOLUTE_EXISTING_PROJECT_PATH",
  "workspace": "ACTUAL_CONVERSATION_CWD",
  "native_id": "CURRENT_CONVERSATION_ID",
  "harness": "codex-cli"
}
```

1. **Preflight.** Inspect the read-only result: existing mapping and ledger,
   missing bookkeeping and project docs, pending metadata, conflicts, proposed
   files, actual caller admission, and preflight token. Show a compact summary.
   Optional `project` (slug), `name`, `category` and `subtype` must be supported by
   observed facts. No extra permission question is needed for an authorized,
   unambiguous registration.
2. **Apply.** Keep the fields/key, set `phase` to `apply`, and add the returned
   `preflight` token. The native writer rechecks identity, ownership, controls,
   claims, file preimages and shared locks. It preserves unrelated configuration,
   index rows, stanza prose, and existing compatible provenance CSVs.
3. **Verify.** Inspect configuration, ledger and public publication results
   separately from caller admission. Missing README/roadmap files are reported,
   not generated. Only absent provenance CSVs are initialized. Malformed files
   are conflicts, never silently replaced.
4. **Close.** Supply the substantive session summary through the normal writer;
   verify close and publication. Keep decisions and unresolved issues explicit.

The public installation stores its index at `memory/projects-ledger.md` and
stanzas under `memory/projects-ledger/`; these are private generated data and
ignored by Git. Registration is forward bookkeeping, not a retrospective file
inventory or a portfolio reprioritization.

## Admission and host delivery

At the target project root, the writer can admit an unadmitted caller through
the existing native lifecycle. At the AI OS installation root, it retains the
coordination-only root binding and reports `target_project_admitted: false`.
Existing active callers retain their actual workspace/project. Closed activations
stay closed until explicitly activated through the native lifecycle.

Configuration, admission, public files, and **actual host receipt delivery** are
different facts. `--intake` without an alias reports `native-not-yet-admitted`;
that is not evidence of deployment failure. CLI success does not prove hooks ran.
Registration does not install project-local hooks. If those are needed for a
new project, the same responsible task follows the installer guide after closing
active installation sessions, preserves unrelated handlers/settings, and checks
the real host receipt. Do not report unwired hooks as working.

## Recovery and delayed logging

Repeat the **identical apply request/key** after interrupted publication. The
private redo journal skips exact postimages and refuses conflicting newer files.
Another key for that project is blocked while publication is incomplete. After a
successful registration, a fresh preflight produces no duplicate ledger changes.
If successful publication has subsequently changed, inspect the reported drift
and use a fresh preflight; never restore old bytes over newer work.

Delayed artifact logging requires explicit user/handoff authorization. Add both:

```json
{
  "source": {"task": "ORIGINAL_TASK", "date": "2026-01-15", "harness": "codex-cli", "model": "unavailable"},
  "delayed_artifacts": [{"path": "drafts/example.md", "sha256": "EXPECTED_64_HEX_DIGEST", "text": true}]
}
```

The expected digest identifies the completed handoff version. Changing files
remain pending; do not refresh their digests merely to pass the check. The writer
checks stable bytes, publishes exact snapshots, attributes source task/date/model
separately from the logging task/date, and avoids duplicate delayed log rows.
This does not prove original-task admission, original generation time, close, or
human verification. Unknown original models remain `unavailable`.

Complete with one concise result: project and canonical root; registration/ledger
outcome; actual admission/publication; precise unresolved issues. Shared locks
coordinate native writers; observed hash checks do not exclude every external
editor race or an indistinguishable edit-and-revert.
