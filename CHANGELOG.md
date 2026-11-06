# Changelog

## Unreleased

- Skills: `project-setup` 0.5 Rule 3: an agent may add files under `inputs/`
  for a named batch the user approved in words, with the approval quoted and
  dated in the batch's provenance `README.txt`; add only, never overwrite,
  replace, move or delete. `background/` stays read-only.
- Planning fixes: `planning-protocol` drops the rules for plans started under
  unshipped earlier versions and records `planning-protocol v0.8` in new plan
  manifests; `FORMAT.md` names the gate outline the accent colour;
  `classify-README.md` says where the `WGP-*` source tags are credited.
- Rebuild `site/ai-os-install-kit.zip` from the updated files.

- Skills: first public release of the planning family. `planning-protocol` 0.8
  coordinates `planning-output-specification` 0.3, `planning-resource-map` 0.3,
  `planning-implementation-map` 0.4, `planning-adversarial-review` 0.2,
  `planning-adjudication` 0.3, `planning-decision-points` 0.1,
  `planning-labels` 0.2 and `planning-spec-reconciliation` 0.3.
- Skill assets: `skills/_assets/plan-viewer/` (plan-viewer 1.2.0: `plan_viewer.py`
  builder and `--check` linter, `FORMAT.md` contract, page template,
  `plan_status.py`, the optional `classify.py` decision-point classifier for a
  paid API, and offline tests with fixtures) and
  `skills/_assets/planning-templates/` (`SPEC.md`, `RESOURCES.md`, `PLAN.md`,
  `Plan-Labels.json`, a GitHub Pages workflow).
- Rebuild `site/ai-os-install-kit.zip` from the updated files.
- Skills: `project-setup` 0.4 and `project-setup-existing` 0.4 add one local
  project repo per project (code plus `planning/`), the standard `appendix/`
  replication package layout, the asset registry as resource inventory, and
  AI-output snapshots for installs without native bookkeeping. The
  registration route and native-writer wording are kept.
- Skills: `literature-error-check` 0.2 always asks where to save its report and
  never defaults to `appendix/`.
- README: link to the student edition of the planning workflow.
- Site: "In brief" overview after the hero on the guide page, linking the
  Research Guide PDF and the student planning workflow.
- Runtime unchanged; product version stays 2.0.1.

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
