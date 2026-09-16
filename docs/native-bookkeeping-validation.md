# Native package validation

Date: 2026-09-15.

## Existing-project registration update

Windows / Python 3.14: **49 isolated tests passed in 39.398 seconds**, comprising
28 registration fixtures and 21 installer/lifecycle tests. Tests ran against the
working public source with the regenerated runtime manifest. They include the
installed CLI from both the AI OS root and a previously unregistered project root.

Registration cases cover missing and repeated registration, slug/path conflicts,
incomplete files, actual cwd binding, concurrent changes, interrupted publication,
stable delayed artifacts and source attribution, Windows permission preservation,
claims, controls and accurate not-yet-admitted intake. Successful retries produce
no duplicate project changes. No real project was registered as a test.

Runtime and new workflow files were checked for private filesystem roots, task
identities and project names; none are distributed. Actual host receipt injection
and non-Windows platforms remain unverified. The public code is distributed through
a reviewed source branch; it is not an in-place runtime migration.

The section below records the earlier installer baseline.

## Earlier installer baseline

- Windows, Python 3.14; standard library plus Git.
- Tests executed from an extracted Git archive of tree
  6864545cce401582841a7621846921d965563e46.
- All 19 tests passed (87.861 seconds).
- All 20 runtime files matched MANIFEST.json in the exported archive.
- Python syntax checks passed.
- New runtime, installer, technical guide, tests and manifest tool scanned for
  author-specific names, account/email strings and personal filesystem roots:
  zero matches. Existing public attribution was retained.
- Staged whitespace check passed.

Coverage includes no-write preview, repeat installation, preservation of existing
settings/instructions, tracked-local-config refusal, both native lifecycle adapters,
generated Windows hook execution from space-containing paths, claim conflict and
release, concurrent closeout, exact snapshots, idempotent provenance, raw-payload
non-persistence, invalid artifact/human-verification refusal, shutdown closure,
idle prompt routing, status/intake and interrupted-publication recovery.

Only this validation note is added after the tested source tree; runtime and
installer bytes remain those tested. Runtime source ancestry and adaptations are
recorded in runtime/UPSTREAM.json.

## Earlier baseline limits

- These are disposable fixture tests, not real Claude/Codex UI acceptance.
- macOS, Linux and other supported Python versions have not been exercised here.
- No change was installed into the author's live harness or private runtime.
- No native state, project records, private settings or installation backups are
  included in the distribution.
- This package has not been pushed or deployed by this validation session.
- Full-system acceptance, compact startup, cross-machine operation and automated
  portfolio launch are not established by these results.

After installation, verify a real SessionStart receipt and a completed closeout
in each harness you intend to use, as described in the technical guide.
