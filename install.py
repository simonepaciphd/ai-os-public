"""Install native bookkeeping for an explicitly selected local project.

No downloads, package manager, provider calls, global harness edits or elevation.
The executable Python used here is recorded in generated local hook commands.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import sys
import subprocess
import tempfile
import uuid

PACKAGE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
BEGIN = "<!-- AIOS NATIVE BEGIN -->"
END = "<!-- AIOS NATIVE END -->"
ASSET_FIELDS = ["asset_path", "asset_type", "creator", "created", "last_modified",
                "verification", "ai_output_hash", "model_metadata", "notes"]
LOG_FIELDS = ["date", "session_id", "harness", "model", "researcher_input_summary",
              "agent_output_summary", "assets_affected", "notes", "initiator", "task_difficulty", "decisions"]


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def read(path):
    return path.read_bytes() if path.exists() else None


def absolute(value):
    return Path(value).expanduser().resolve()


def command(parts):
    if os.name == "nt":
        # Windows command hooks use a shell. Refuse expandable/metacharacter paths.
        if any(any(c in p for c in '\r\n\0"%!?`$&|<>^') for p in parts):
            raise ValueError("Use installation/project/Python paths without shell metacharacters")
        return "& " + " ".join("'" + p.replace("'", "''") + "'" for p in parts)
    return shlex.join(parts)


def instructions(root):
    launcher = root / "runtime" / "aios.py"
    return (f"{BEGIN}\n## Native bookkeeping\n\n"
            f"Read `{root / 'coord' / 'SPEC.md'}` completely at startup, with BOARD.md, "
            "controls, your mailbox and project requirements. Use the fresh hook receipt "
            "for your activation. The native writer owns routine session/provenance "
            "fields; this replaces manual ledger-writing instructions for those fields. "
            "Supply claims before writes and substantive semantic metadata at checkpoints. "
            "Do not claim native-owned records. Check live claims before every write.\n\n"
            f"CLI: `{command([sys.executable, '-I', '-B', str(launcher)])}`. "
            "Use `--describe` for the request schema; `--request <private-json-file>` "
            "submits a semantic request. On exit submit close and verify closed plus "
            "publication complete. Honor shutdown controls; failed hooks permit only "
            "cleanup/recovery until revalidated. Never replay task effects.\n"
            f"{END}\n")


class Plan:
    def __init__(self):
        self.files = {}

    def put(self, path, body):
        path = path.absolute()
        # Reject symlinked files/parents so generated setup cannot escape its target.
        if any(p.is_symlink() or (hasattr(p, "is_junction") and p.is_junction())
               for p in [path, *path.parents]):
            raise ValueError("Installation target contains a symlink or junction")
        if path not in self.files:
            self.files[path] = (read(path), body)
        else:
            self.files[path] = (self.files[path][0], body)

    def existing(self, path):
        return self.files[path][1] if path in self.files else read(path)

    def apply(self, backup_dir):
        changed = {p: pair for p, pair in self.files.items() if pair[0] != pair[1]}
        for p, (before, _) in changed.items():
            if read(p) != before:
                raise ValueError("Installation input changed; inspect and retry")
        if not changed:
            return 0
        backup_dir.mkdir(parents=True, exist_ok=False)
        # Durable preimages and planned digests allow manual recovery after a crash.
        record = []
        for number, (p, (before, after)) in enumerate(changed.items()):
            if before is not None:
                (backup_dir / str(number)).write_bytes(before)
            record.append({"path": str(p), "backup": str(number) if before is not None else None,
                           "after_sha256": hashlib.sha256(after).hexdigest()})
        (backup_dir / "plan.json").write_bytes(encoded(record))
        completed = []
        try:
            for p, (before, after) in changed.items():
                p.parent.mkdir(parents=True, exist_ok=True)
                if read(p) != before:
                    raise ValueError("Installation input changed during publication")
                with tempfile.NamedTemporaryFile(dir=p.parent, delete=False) as f:
                    temporary = Path(f.name)
                    f.write(after)
                    f.flush()
                    os.fsync(f.fileno())
                try:
                    if read(p) != before:
                        raise ValueError("Installation input changed during publication")
                    os.replace(temporary, p)
                finally:
                    temporary.unlink(missing_ok=True)
                completed.append((p, before, after))
        except Exception:
            for p, before, after in reversed(completed):
                if read(p) == after:
                    if before is None:
                        p.unlink()
                    else:
                        p.write_bytes(before)
            raise
        (backup_dir / "complete").write_text("complete\n", encoding="utf-8")
        return len(changed)


def ledger(plan, path, fields):
    before = read(path)
    if before is not None:
        rows = list(csv.reader(io.StringIO(before.decode("utf-8-sig"))))
        if not rows or len(set(rows[0])) != len(rows[0]) or not set(fields) - {"notes", "asset_type"} <= set(rows[0]):
            raise ValueError(f"Existing ledger has incompatible columns: {path.name}")
        if any(len(row) != len(rows[0]) for row in rows[1:]):
            raise ValueError(f"Existing ledger has malformed rows: {path.name}")
    else:
        plan.put(path, (",".join(fields) + "\n").encode())


def hook_config(plan, project, root, harness):
    path = project / (".claude/settings.local.json" if harness == "claude-code" else ".codex/hooks.json")
    before = read(path)
    config = json.loads(before.decode("utf-8-sig")) if before else {}
    if not isinstance(config, dict) or not isinstance(config.get("hooks", {}), dict):
        raise ValueError("Unsupported existing hooks configuration")
    # Other AI OS installations must be removed deliberately, never doubled.
    hooks = config.setdefault("hooks", {})
    parts = [sys.executable, "-I", "-B", str(root / "runtime/aios.py"), "--harness", harness]
    if harness == "claude-code":
        handler_base = {"type": "command", "command": sys.executable, "args": parts[1:]}
    elif os.name == "nt":
        command(parts)  # Validate shell-sensitive path characters first.
        script = (root / "runtime/hook.ps1").as_posix()
        handler_base = {"type": "command", "command":
                        f'powershell.exe -NoProfile -NonInteractive -File "{script}" -Harness codex-cli'}
    else:
        handler_base = {"type": "command", "command": command(parts)}
    events = ["SessionStart", "UserPromptSubmit", "PreToolUse", "PostToolUse", "Stop", "SessionEnd"]
    events += ["PostToolUseFailure"] if harness == "claude-code" else ["Interrupt"]
    for entries in hooks.values():
        if not isinstance(entries, list):
            raise ValueError("Unsupported existing hook entries")
        for entry in entries:
            for handler in entry.get("hooks", []):
                previous = handler.get("command", "") + " " + " ".join(handler.get("args", []))
                managed = any(x in previous for x in ("aios.py", "native-bookkeeping", "runtime/hook.ps1"))
                same = all(handler.get(k) == v for k, v in handler_base.items())
                if managed and not same:
                    raise ValueError("Another AI OS hook is present; reconcile it before installing")
    for event in events:
        entries = hooks.setdefault(event, [])
        if any(all(h.get(k) == v for k, v in handler_base.items()) for e in entries for h in e.get("hooks", [])):
            continue
        entries.append({"hooks": [{**handler_base,
                                   "timeout": 3 if event in {"SessionEnd", "Interrupt"} else 30}]})
    plan.put(path, encoded(config))


def build_plan(args):
    root, project = absolute(args.root), absolute(args.project)
    if not project.is_dir() or root == project or root.is_relative_to(project):
        raise ValueError("Project must exist; install root must be separate from the project")
    if project.is_relative_to(root) and project.parts[len(root.parts)] in {"runtime", "config", "coord"}:
        raise ValueError("Project overlaps runtime-owned directories")
    if root == PACKAGE or root.is_relative_to(PACKAGE):
        raise ValueError("Install outside the public source checkout")
    slug = args.slug or project.name.lower().replace(" ", "-")
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,79}", slug):
        raise ValueError("Project slug must use lowercase letters, digits, hyphens or underscores")
    if slug == "ai-os-system":
        raise ValueError("ai-os-system is reserved for the installation root")
    config_path = root / "config/ownership.json"
    previous = json.loads(config_path.read_text(encoding="utf-8-sig")) if config_path.exists() else None
    default_state = Path.home() / ".local/state/ai-os" / hashlib.sha256(str(root).encode()).hexdigest()[:12]
    state = absolute(args.state_dir or (previous["state_root"] if previous else default_state))
    if state.is_relative_to(root) or root.is_relative_to(state) or state.is_relative_to(project) or project.is_relative_to(state):
        raise ValueError("Private state must be separate from the install root and projects")
    if not shutil.which("git"):
        raise ValueError("Git is required for workspace inspection")
    if previous and (previous.get("distribution") != "ai-os-public-native-1" or previous["state_root"] != str(state)
                     or previous["os_root"] != str(root)):
        raise ValueError("Existing root belongs to another installation or state path")
    if not previous and ((root / "coord").exists() or (state.exists() and any(state.iterdir()))):
        raise ValueError("Existing coordination/state without installation metadata; inspect before initializing")
    if any((parent / ".git").exists() for parent in [state, *state.parents]):
        raise ValueError("Private state cannot live in a Git checkout")
    config = previous or {"distribution": "ai-os-public-native-1", "owner": "v2", "enabled": True,
                          "mode": "live-sharded", "storage_format": "project-session-v1",
                          "storage_generation": "public-native-1", "epoch": uuid.uuid4().hex,
                          "os_root": str(root), "state_root": str(state),
                          "python_executable": sys.executable, "projects": {}}
    for other, value in config["projects"].items():
        if not value.get("provenance", True):
            continue
        other_root = Path(value["root"])
        if other != slug and (project.is_relative_to(other_root) or other_root.is_relative_to(project)):
            raise ValueError("Project overlaps an existing registered project")
    target = {"root": str(project), "worktrees": [], "provenance": True}
    if slug in config["projects"] and config["projects"][slug] != target:
        raise ValueError("Project slug is already bound to a different configuration")
    config["projects"][slug] = target
    system = {"root":str(root), "worktrees":[], "provenance":False}
    if "ai-os-system" in config["projects"] and config["projects"]["ai-os-system"] != system:
        raise ValueError("Conflicting installation-root mapping")
    config["projects"]["ai-os-system"] = system
    # Do not reconfigure an installation while its native sessions hold work.
    for p in (state / "activations").glob("*.json"):
        if json.loads(p.read_bytes()).get("status") == "active":
            raise ValueError("Close active AI OS sessions before running the installer")
    for relative in [".claude/settings.local.json", ".codex/hooks.json", ".aios/native.md"]:
        tracked = subprocess.run(["git", "-c", "safe.directory=" + str(project), "-C", str(project),
                                  "ls-files", "--error-unmatch", "--", relative],
                                 capture_output=True, timeout=10)
        if tracked.returncode == 0:
            raise ValueError("Generated local configuration is already tracked by Git: " + relative)
    plan = Plan()
    manifest = json.loads((PACKAGE / "runtime/MANIFEST.json").read_text(encoding="utf-8-sig"))
    for relative, sha in manifest["files"].items():
        source = (PACKAGE / "runtime" / relative).resolve()
        if not source.is_relative_to(PACKAGE / "runtime"):
            raise ValueError("Invalid runtime manifest path")
        body = source.read_bytes()
        if hashlib.sha256(body).hexdigest() != sha:
            raise ValueError("Public source integrity check failed")
        destination = root / "runtime" / relative
        if destination.exists() and destination.read_bytes() != body:
            raise ValueError("Existing runtime differs; upgrades require a separate migration")
        plan.put(destination, body)
    plan.put(root / "runtime/MANIFEST.json", (PACKAGE / "runtime/MANIFEST.json").read_bytes())
    plan.put(config_path, encoded(config))
    spec = root / "coord/SPEC.md"
    if not spec.exists():
        plan.put(spec, (PACKAGE / "runtime/templates/SPEC.md").read_bytes())
    if not (root / "coord/BOARD.md").exists():
        plan.put(root / "coord/BOARD.md", b"# Coordination notices\n")
    index = root / "memory/projects-ledger.md"
    if not index.exists():
        plan.put(index, b"# Projects ledger\n\n## Active projects\n\n| name | category | subtype | life_stage | priority | last_session | next_milestone |\n|---|---|---|---|---|---|---|\n")
    template = root / "memory/projects-ledger/_template.md"
    if not template.exists():
        plan.put(template, b"# Project registration\n\nUse the native register-project preflight/apply operation to create project stanzas.\n")
    ledger(plan, project / "asset-registry.csv", ASSET_FIELDS)
    ledger(plan, project / "interaction-log.csv", LOG_FIELDS)
    local_note = project / ".aios/native.md"
    local_body = instructions(root).encode()
    if local_note.exists() and local_note.read_bytes() != local_body:
        raise ValueError("Existing local AI OS instructions differ; reconcile before installing")
    plan.put(local_note, local_body)
    for name in ["AGENTS.md", "CLAUDE.md"]:
        path = project / name
        before = (read(path) or b"").decode("utf-8-sig")
        block = (BEGIN + "\n## Native bookkeeping\n\n"
                 "Read .aios/native.md for this project's installed native bookkeeping "
                 "entrypoint and required startup sources. Native hooks own routine "
                 "session/provenance fields; supply claims and semantic metadata through "
                 "the native writer. Check live claims before writes, honor controls, "
                 "and verify native close/publication on exit.\n" + END + "\n")
        if BEGIN in before or END in before:
            if before.count(BEGIN) != 1 or before.count(END) != 1 or before.index(BEGIN) > before.index(END):
                raise ValueError("Malformed AI OS instruction block")
            old = before[before.index(BEGIN):before.index(END) + len(END)]
            if old != block.rstrip():
                raise ValueError("AI OS instruction block was changed; review before reinstalling")
        else:
            plan.put(path, (before + ("\n\n" if before else "") + block).encode())
    harnesses = ["claude-code", "codex-cli"] if args.harness == "both" else [args.harness]
    for harness in harnesses:
        hook_config(plan, project, root, harness)
    for base, lines in [(project, [".cowork/", ".aios/", ".claude/settings.local.json", ".codex/hooks.json"]),
                        (root, ["config/", "memory/", "coord/sessions/", "coord/mailbox/", "coord/control/", "coord/inbox/"])]:
        path = base / ".gitignore"
        before = (read(path) or b"").decode("utf-8-sig")
        missing = [x for x in lines if x not in before.splitlines()]
        if missing:
            plan.put(path, (before + ("\n" if before and not before.endswith("\n") else "")
                            + "\n".join(missing) + "\n").encode())
    return plan, root, state


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(Path.home() / "AI-OS"))
    parser.add_argument("--project", required=True)
    parser.add_argument("--slug")
    parser.add_argument("--state-dir")
    parser.add_argument("--harness", choices=["both", "claude-code", "codex-cli"], default="both")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    if sys.version_info < (3, 11):
        parser.error("Python 3.11 or newer is required")
    try:
        plan, root, state = build_plan(args)
        changed = [str(p) for p, (a, b) in plan.files.items() if a != b]
        if args.dry_run:
            print(json.dumps({"status": "plan", "files": changed, "private_state": str(state)}, indent=2))
            return 0
        root.mkdir(parents=True, exist_ok=True)
        lock = root / ".install.lock"
        with lock.open("x") as stream:
            stream.write(str(os.getpid()))
        try:
            # Re-read under the installer lock to detect changes since preflight.
            plan, root, state = build_plan(args)
            state.mkdir(parents=True, exist_ok=True, mode=0o700)
            for directory in ["sessions/_closed", "mailbox/operator", "control", "inbox"]:
                (root / "coord" / directory).mkdir(parents=True, exist_ok=True)
            count = plan.apply(state / "installation-backups" / uuid.uuid4().hex)
        finally:
            lock.unlink()
        print(json.dumps({"status": "installed", "changed_files": count,
                          "runtime": str(root / "runtime/aios.py"), "private_state": str(state),
                          "next": "Restart the harness; review hook trust and verify a fresh SessionStart receipt."}, indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print("Install refused: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
