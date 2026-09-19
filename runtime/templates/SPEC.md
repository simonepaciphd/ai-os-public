# AI OS native coordination

The native writer owns session registration, heartbeat, closeout, project ledger
publication and requested snapshots. Agents supply claims, summaries, decisions,
and verification. Hooks never authorize task effects or replace host permissions.

    budgets: claude-code=4, codex-cli=4

## Session workflow

1. At startup, inspect the fresh native receipt, this file, BOARD.md, control/,
   your session mailbox and project instructions. Missing controls or ownership
   means cleanup only. A receipt establishes bookkeeping, not task authorization.
2. Submit claims before editing, and check every live claim before each write.
   Use absolute paths or paths relative to the installed AI OS root. On overlap,
   contact the holder and wait; a stale public heartbeat never releases a private
   active claim. Native-owned session/state/closeout paths cannot be claimed.
3. At substantive checkpoints, submit a JSON request with a unique key and the
   activation from a fresh receipt. Include changed claims, task, summary,
   input_summary, decisions and artifacts as needed. Do not add heartbeats merely
   because a routine hook succeeded. Recheck controls and your mailbox.
4. The writer creates project registry rows and exact text snapshots on request.
   Agents cannot grant human-verified status. Keep summaries content-minimal:
   never submit secrets, raw prompts, transcripts or sensitive artifact bodies.
5. Finish edits, logs and checks, then submit close as the final tool call with
   claims=[], summary and disposition. Verify status=closed and
   close_verification.status=verified in that same result; send the final response
   without more tools. Pending/unconfirmed publication requires operator inspection
   or reconciliation outside the closed activation. Turn Stop and Interrupt are heartbeats;
   SessionEnd attempts close. Abrupt process death may deliver neither.
6. On SHUTDOWN-REQUESTED.md, finish the current atomic step only, close and stop.
   A deadline never authorizes removing the flag or aborting shutdown.
7. Resume checks controls, workspace and capacity. Closed activations stay closed;
   only explicit native SessionStart or semantic activate creates a new one.
   Reconcile repairs bookkeeping only; never replay a task effect after failure.

## Files

- sessions/*.md: generated live-session records; _closed/ contains closed records.
- mailbox/operator/: generated closeout notes. Other mailbox messages are separate
  sender-owned Markdown files with from, to, sent and re frontmatter.
- BOARD.md: operator notices. control/: shutdown/control flags.
- Project asset-registry.csv and interaction-log.csv: native provenance.
- Project .cowork/snapshots/: exact requested artifact bytes; private by default.
- Private journals and generated configuration live outside the public source.

Read startup sources completely; compact capsule delivery is not provided.
This is same-user, local-machine coordination. Host coverage, cross-machine
coordination, remote analytics and automatic portfolio launch are not supplied.
