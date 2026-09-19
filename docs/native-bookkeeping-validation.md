# Native package validation

## v2.0.1 release candidate â€” 2026-09-18

Prepared from refreshed `main` at `5ca494d340dd09dae69eb0ac84c6fa76441cd014`.
Implementation commit: `b8a2b94ca754e0630524280dd4be51cff53cde8b`.
Tested Git tree: `c13a6994aa5a6431e523c6f8788b4777327def8f`.

All runs below used the same extracted Git ZIP, including the installer and
regenerated runtime manifest, rather than importing working-tree modules.

| Platform | Python | Result | Suite time |
| --- | --- | --- | --- |
| Windows | 3.11.9 | 112 run: 111 passed, 1 skipped | 227.119 s |
| Windows | 3.14.0 | 112 run: 111 passed, 1 skipped | 231.263 s |
| Ubuntu under WSL | 3.12.3 | 112 run: 104 passed, 8 skipped | 90.133 s |

Command: `python -I -B -m unittest discover -s tests -v`.
The Windows skip is the sharded-outbox-only case in the legacy fixture. Linux
additionally skips two alias-sharing tests, three other Windows-sharing tests,
Windows DACL preservation and PowerShell/Git Bash transport. Linux fixtures use
the Linux temporary filesystem; source ZIP extraction is on the Windows mount.

Artifact SHA-256:
`ac9206643b3b1b3db37fd645d27cbb717d144f10c528283e1d9dbdaf3deb482c`.
Runtime manifest SHA-256:
`8787c083fd71f11ea500384ef59a6eb76a736cb8f115952eaadbee506de9ed05`.
All 21 distributed runtime files match the manifest, with no missing or extra
runtime files; all 16 source provenance digests match their distributed files.
Python 3.11 syntax validation and staged whitespace checks also passed.

The final review archive adds only this validation record after the tested tree;
runtime, installer, tests, version and release-note bytes remain identical.

Coverage includes close readback/duplicate close, inert late events and terminal
refusal, bounded transient/persistent Windows reads, missing/corrupt/locked aliases,
unknown-cwd questions, exact registration/Describe gating and injected-command
refusal, new/existing projects, canonical-root-preserving attachment, interrupted
retry, claims/overlaps/shutdown/recovery controls, closed identities, hostile/empty
stdin, malformed argv and strict malformed-ledger refusal with unchanged files.
Public installer repeatability, settings preservation and paths with spaces pass.
PowerShell and Git Bash both execute the generated registration with closed stdin.

Testing the supported minimum version exposed and fixed the existing use of
`Path.is_junction()` in startup intake, an API absent in Python 3.11. Actual
Windows junction and Linux symlink fixtures verify that link rejection remains.

New runtime, tests and release files were scanned for private roots, identities,
project names and private wrapper/evidence references; none were included.
Existing intentional public attribution remains. No private ledgers, settings,
activation records, repair scripts, transcripts or handoff are distributed.

Limits: fixture results do not establish actual Claude/Codex UI delivery, macOS,
other Python minor versions, universal enforcement or full-system acceptance.
No live runtime was upgraded. Remote push, tag and release publication remain
pending explicit approval. See [release/upgrade/rollback notes](releases/v2.0.1.md).

The following entries are historical validation of earlier source trees.

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
