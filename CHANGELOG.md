# Changelog

## v2.0.1 — release candidate

- Return bounded close-publication verification in the closing call and teach
  close-as-last-tool. Closed activations require fresh native SessionStart;
  late completion/stop/end events remain inert.
- Retry transient Windows EACCES bookkeeping reads within the existing 250 ms
  deadline, including errors without winerror. Persistent denials retain the
  original exception; task effects are never retried.
- Read admission aliases directly, distinguishing absence from unreadable or
  corrupt state. Missing admission cannot be fabricated by prompt/tool events.
- Let unregistered Claude conversations ask for an existing or new project and
  use an exact, identity-bound registration command. Existing-project attachment
  preserves its canonical root, ledger and project history.
- Validate registration argv independently of stdin, reject ambiguous arguments,
  preserve control/ownership checks, and report safe error stage/class metadata.
  Permit exact read-only Describe during registration; deny injected commands.
- Refuse malformed legacy CSV without rewriting records, including invalid
  quoting, and document separately authorized, backed-up repair.
- Restore Python 3.11 startup intake compatibility while retaining symlink/junction rejection.
- Define product version `2.0.1` in `VERSION`; propagate it into installer output,
  installed metadata and generated integrity/provenance manifests. Contract and
  storage identifiers are unchanged.

See [release, upgrade and rollback notes](docs/releases/v2.0.1.md) and
[validation evidence](docs/native-bookkeeping-validation.md).
