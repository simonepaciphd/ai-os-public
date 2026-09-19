# Public native bookkeeping runtime

Product version **2.0.1** is defined by the repository `VERSION` file and included in the generated runtime manifest.

This is the portable dependency subset of the installed native bookkeeping system:
seven core modules and nine native modules, plus a portable CLI and Windows hook
launcher. Runtime dependencies are Python's standard library and the Git executable.

- aios.py: manifest verification, native CLI, doctor and status.
- src/aios_native/: semantic contract, lifecycle, per-session journals, hook ingress,
  safe diagnostics, optional model metadata helper and bounded intake.
- src/aios_core/: event integrity, replay, checkpoints, coordination and liveness.
- templates/SPEC.md: generic operating contract installed under coord/.
- UPSTREAM.json: source and distribution digests, release identity and adaptations.
- MANIFEST.json: exact distributed runtime bytes.

Install through [the technical guide](../docs/setup-guides/native-bookkeeping-install.md).
Run the installer from the repository root; do not copy private ownership files,
journals, installation archives, provider settings or session records.

The public contract is native-semantic-public-1. Generic operator mailbox and
operator-decides disposition replace deployment-specific identity vocabulary.
Only the dependency subset needed for native bookkeeping is included; unrelated
pilot execution, provider adapters and governance experiments are not shipped.

Source integrity is a local installation check, not a signature or a defense against
a user who can rewrite both the runtime and its manifest. Hooks do not grant task
permission. Claims, judgments and requested snapshot bodies remain agent/operator
inputs. The distribution provides no automatic privacy filter for those inputs.

For a reviewed source change, run python tools/build-runtime-manifest.py at the
repository root, inspect UPSTREAM.json and MANIFEST.json, and rerun tests. Never
run the manifest builder against an unexplained changed installation.
