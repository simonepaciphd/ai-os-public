"""One deterministic native bookkeeping writer. No provider calls or tool authorization.

Private journal bodies are local, not telemetry. EventStore records only hashes and
enumerated operation/status metadata. A single OS lock serializes native deliveries;
each file replacement compares both preimage and intended postimage. Interrupted
publication is visible and reconciled before another operation can be admitted.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from aios_core.store import EventStore, WriterBusy
from aios_core.coord import snapshot
from aios_core.liveness import parse_session_frontmatter, interpret
from .request_contract import Refused, RequestInvalid, validate_request

def digest(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()

def encoded(value) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=True, indent=2) + "\n").encode()

def read(path: Path) -> bytes | None:
    try:
        return path.read_bytes()
    except FileNotFoundError:
        return None

def hash_at(path: Path) -> str | None:
    body = read(path)
    return digest(body) if body is not None else None

_UNSET = object()

PUBLICATION_ROLES = frozenset({"session-heartbeat", "session-close", "private-state",
    "transaction", "projection", "closeout", "project-provenance", "snapshot", "cache", "other"})


def publication_retry(action: Callable[[], None], *, check: Callable[[], None],
                      deadline: float, role: str) -> None:
    """Retry one prepared filesystem effect; an absolute deadline is shared by its writer."""
    started = time.monotonic()
    attempts = 0
    while True:
        check()  # Recheck ownership, claims and preimage even after a delayed reader.
        attempts += 1
        try:
            action()
            return
        except OSError as exc:
            now = time.monotonic()
            exc.native_publication_role = role
            exc.native_publication_attempts = attempts
            exc.native_publication_elapsed_ms = (now - started) * 1000
            remaining = deadline - now
            if os.name != "nt" or getattr(exc, "winerror", None) not in {5, 32, 33} or remaining <= 0:
                raise
            time.sleep(min(0.025, remaining))


def atomic(path: Path, body: bytes, *, expected=_UNSET,
           check: Callable[[], None] | None = None,
           deadline: float | None = None, role: str = "other") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    before = hash_at(path) if expected is _UNSET else expected
    tmp = path.with_name(path.name + ".native-tmp")
    with tmp.open("wb") as f:
        f.write(body)
        f.flush()
        os.fsync(f.fileno())
    def verify():
        if check is not None:
            check()
        if hash_at(path) != before:
            raise Refused("publication-conflict:" + str(path))
    publication_retry(lambda: os.replace(tmp, path), check=verify,
                      deadline=time.monotonic() + 0.5 if deadline is None else deadline,
                      role=role)


def line(value: str) -> str:
    if not isinstance(value, str) or any(c in value for c in "\r\n\0"):
        raise Refused("invalid-scalar")
    return value

def normalized_physical_path(path: Path) -> Path:
    value = str(path.resolve())
    if value.startswith(chr(92)*2 + "?" + chr(92)):
        value = value[4:]
        if value.startswith("UNC" + chr(92)):
            value = chr(92)*2 + value[4:]
    return Path(value)


def beneath(path: Path, root: Path) -> bool:
    return normalized_physical_path(path).is_relative_to(normalized_physical_path(root))


def workspace_matches(project: dict, workspace: Path, root: Path) -> bool:
    # A coordination-only OS root must not silently own unselected child projects.
    # Project roots and their explicit worktree aliases retain descendant support.
    workspace, root = workspace.resolve(), root.resolve()
    return workspace == root or (project.get("provenance", True) and workspace.is_relative_to(root))


def claim_base(value: str, os_root: Path) -> str:
    # Existing claims include section suffixes and annotations. Compare conservatively.
    value = value.split(" §", 1)[0].split(" (", 1)[0].replace("\\", "/").rstrip("/")
    value = value.split("*", 1)[0].rstrip("/")
    p = Path(value)
    if not p.is_absolute():
        p = os_root / p
    return str(normalized_physical_path(p)).replace("\\", "/").casefold().rstrip("/")

def overlap(a: str, b: str, os_root: Path) -> bool:
    x, y = claim_base(a, os_root), claim_base(b, os_root)
    return x == y or x.startswith(y + "/") or y.startswith(x + "/")

def csv_rows(path: Path, required: set[str]):
    body = path.read_text(encoding="utf-8-sig")
    reader = csv.DictReader(io.StringIO(body, newline=""))
    fields = reader.fieldnames
    if fields is None or not required <= set(fields) or len(set(fields)) != len(fields) or "" in fields:
        raise Refused("unsupported-ledger-schema")
    rows = list(reader)
    if any(None in row or None in row.values() for row in rows):
        raise Refused("malformed-ledger-row")
    return fields, rows

def csv_bytes(fields, rows) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")

class Bookkeeper:
    def __new__(cls, config, **kwargs):
        if cls is Bookkeeper:
            selected = json.loads(Path(config).read_text(encoding="utf-8-sig"))
            if selected.get("storage_format") == "project-session-v1":
                from .sharded import ProjectBookkeeper
                return object.__new__(ProjectBookkeeper)
        return object.__new__(cls)

    def __init__(self, config: Path, *, fault: Callable[[str], None] | None = None,
                 clock: Callable[[], datetime] | None = None):
        self.config_path = config.resolve()
        self.config = json.loads(config.read_text(encoding="utf-8-sig"))
        self.os_root = Path(self.config["os_root"]).resolve()
        self.coord = self.os_root / "coord"
        self.root = Path(self.config["state_root"]).resolve()
        self.journal_root = self.root
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.fault = fault or (lambda _: None)
        self._publication_deadline: float | None = None

    def _publication_role(self, path: Path) -> str:
        if path.parent == self.coord / "sessions": return "session-heartbeat"
        if path.parent == self.coord / "sessions" / "_closed": return "session-close"
        if path.parent == self.root / "activations" or path.parent == self.root / "aliases": return "private-state"
        if path.parent == self.root / "transactions": return "transaction"
        if path.parent == self.root / "views": return "projection"
        if path.parent == self.coord / "mailbox" / "operator": return "closeout"
        if path.name == "completed-transactions-cache.json": return "cache"
        if path.name in {"asset-registry.csv", "interaction-log.csv"}: return "project-provenance"
        if path.suffix == ".snap": return "snapshot"
        return "other"

    def _atomic(self, path: Path, body: bytes, **kwargs) -> None:
        check = kwargs.pop("check", None)
        def verify():
            self.ownership()
            if check is not None:
                check()
        atomic(path, body, check=verify, deadline=self._publication_deadline,
               role=self._publication_role(path), **kwargs)

    def control(self) -> str:
        try:
            control = self.coord / "control"
            entries = list(control.iterdir())  # Missing/unreadable is not clear.
            if any(p.name == "SHUTDOWN-REQUESTED.md" for p in entries):
                return "shutdown"
            return "clear"
        except OSError:
            return "unreadable-controls"

    def ownership(self):
        current = json.loads(self.config_path.read_text(encoding="utf-8-sig"))
        if current != self.config or current.get("owner") != "v2":
            raise Refused("ownership-changed")
        if not current.get("enabled", False):
            raise Refused("integration-disabled")
        if current.get("mode") == "rehearsal":
            sandbox = Path(current["rehearsal_root"]).resolve()
            for p in [self.os_root, self.root] + [Path(x["root"]) for x in current["projects"].values()]:
                if not beneath(p, sandbox):
                    raise Refused("rehearsal-path-outside-root")
        elif current.get("mode") != "live":
            raise Refused("invalid-mode")

    def check_claims(self, paths: list[str], session_id: str = ""):
        now = self.clock()
        # Fail closed on unreadable registry. Stale records never prove quiescence
        # at cutover; this check is only routine coordination, per SPEC.
        for p in (self.coord / "sessions").iterdir():
            if p.suffix != ".md" or not p.is_file():
                continue
            facts = parse_session_frontmatter(p.read_text(encoding="utf-8-sig"), p.name)
            verdict = interpret(facts, now)
            if verdict.id == session_id:
                continue
            if not facts.frontmatter_present:
                raise Refused("unreadable-session:" + p.name)
            if verdict.live:
                for claim in verdict.claims:
                    if any(overlap(claim, target, self.os_root) for target in paths):
                        raise Refused("claim-overlap:" + verdict.id)

    def work_state(self, project: dict) -> dict:
        root = Path(project["root"]).resolve()
        if not root.is_dir():
            raise Refused("project-unavailable")
        # Paths/statuses are returned privately to the responsible agent. No diff bodies.
        args = ["git", "-c", "safe.directory=" + str(root), "-C", str(root),
                "status", "--porcelain=v1", "--untracked-files=normal"]
        result = subprocess.run(args, capture_output=True, text=True, timeout=20,
                                env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"})
        if result.returncode:
            if not (root / ".git").exists():
                return {"kind": "non-git", "inspection": "agent-must-inspect-selected-paths"}
            raise Refused("working-tree-unreadable")
        return {"kind": "git", "status": result.stdout.splitlines(),
                "inspection": "inspect-uncertain-edits-before-retry"}

    def _mut(self, path: Path, body: bytes | None):
        return {"path": str(path.resolve()), "before": hash_at(path),
                "after": digest(body) if body is not None else None,
                "body": body.hex() if body is not None else None}

    def _event(self, tx, phase):
        events = EventStore(self.journal_root / "events")
        state = events.state()
        key = tx["key"] + ":" + phase
        current = state.aggregates.get(tx["activation"])
        payload = {"operation": tx["operation"], "phase": phase,
                   "request_sha256": tx["request_sha256"], "plan_sha256": tx["plan_sha256"],
                   "files": len(tx["writes"])}
        result = events.append(aggregate_id=tx["activation"], command_id=key,
                               expected_version=current.version if current else 0,
                               event_type="native.bookkeeping." + phase, payload=payload)
        if phase == "committed":
            # Keep subsequent short native closes independent of accumulated history.
            # These are verified derived indexes; the event log and blobs stay intact.
            from aios_core.checkpoints import write_checkpoint, prune_checkpoints
            write_checkpoint(events)
            prune_checkpoints(events, keep=2)
        return result

    def _publish(self, tx, tx_path, *, cleanup=False):
        if digest(encoded(tx["writes"])) != tx["plan_sha256"]:
            raise Refused("journal-integrity-failed")
        self._event(tx, "prepared")
        for i, change in enumerate(tx["writes"]):
            path = Path(change["path"])
            self.check_claims([str(path)], tx["activation"])
            actual = hash_at(path)
            if actual == change["after"]:
                continue
            if actual != change["before"]:
                raise Refused("publication-conflict:" + str(path))
            self.fault("before-write:" + str(i))
            def verify():
                self.ownership()
                self.check_claims([str(path)], tx["activation"])
                if not cleanup and tx["operation"] != "close" and self.control() != "clear":
                    raise Refused("cleanup-only:" + self.control())
            if change["body"] is None:
                def verify_delete():
                    verify()
                    if hash_at(path) != change["before"]:
                        raise Refused("publication-conflict:" + str(path))
                publication_retry(path.unlink, check=verify_delete,
                    deadline=self._publication_deadline if self._publication_deadline is not None else time.monotonic() + 0.5,
                    role=self._publication_role(path))
            else:
                body = bytes.fromhex(change["body"])
                if digest(body) != change["after"]:
                    raise Refused("journal-body-integrity-failed")
                self._atomic(path, body, expected=change["before"], check=verify)
            self.fault("after-write:" + str(i))
        self._event(tx, "committed")
        self.fault("after-event-commit")
        tx["complete"] = True
        self._atomic(tx_path, encoded(tx))
        self.fault("after-journal-complete")

    def _reconcile(self):
        directory = self.journal_root / "transactions"
        directory.mkdir(exist_ok=True)
        # Completed journals are immutable under this writer. Keep their file
        # identities in a disposable private cache, rather than decoding every
        # historical publication body on every heartbeat. Always enumerate the
        # directory: older in-flight writers need not know about this cache.
        # This is same-user trusted-state acceleration, not a content-integrity
        # attestation. Duplicate requests still read their original journal.
        cache_path = self.journal_root / "completed-transactions-cache.json"
        cached = {}
        try:
            document = json.loads(cache_path.read_bytes())
            entries = document["entries"]
            if (document["version"] == 1 and document["root"] == str(self.root)
                    and isinstance(entries, dict)
                    and document["sha256"] == digest(encoded(entries))
                    and all(isinstance(k, str) and isinstance(v, list)
                            and len(v) == 5 and all(type(n) is int for n in v)
                            for k, v in entries.items())):
                cached = entries
        except (OSError, ValueError, KeyError, TypeError):
            pass  # Missing/torn/obsolete derived cache falls back to full reads.

        def identity(stat):
            return [stat.st_dev, stat.st_ino, stat.st_size,
                    stat.st_mtime_ns, stat.st_ctime_ns]

        completed = {}
        with os.scandir(directory) as scan:
            paths = sorted((entry.name, identity(Path(entry.path).stat())) for entry in scan
                           if entry.name.endswith(".json") and entry.is_file())
        for name, before in paths:
            path = directory / name
            if cached.get(name) == before:
                completed[name] = before
                continue
            tx = json.loads(path.read_bytes())
            if not tx["complete"]:
                self._publish(tx, path, cleanup=True)
            # Never attach a completion fact to a different file replaced
            # between observation and decoding. Reconciled files are learned
            # on the next pass because publication changes their identity.
            after = identity(path.stat())
            if tx["complete"] is True and before == after:
                completed[name] = after
        if completed != cached:
            try:
                self._atomic(cache_path, encoded({"version": 1, "root": str(self.root),
                                           "entries": completed,
                                           "sha256": digest(encoded(completed))}))
            except (OSError, Refused):
                # Derived acceleration must not turn successful recovery into
                # failed bookkeeping. A later miss simply takes the full path.
                pass

    def execute(self, request: dict, *, lock_timeout_seconds: float = 20) -> dict:
        self.ownership()
        # Pure shape/admission validation precedes mkdir, lock creation, journal
        # reconciliation and events. Never infer a missing activation.
        validate_request(request)
        self.validate_claim_admission(request.get("claims", []))
        self.validate_artifact_paths(request.get("artifacts", []))
        op = request["operation"]
        self.root.mkdir(parents=True, exist_ok=True)
        mutex = EventStore(self.journal_root / "mutex")
        wait_started = time.monotonic()
        try:
            handle, token, wait_ms = mutex.acquire_lock(timeout_seconds=lock_timeout_seconds)
        except WriterBusy as exc:
            # Only failure to acquire the outer mutex proves this delivery has
            # not entered reconciliation or attempted publication.
            exc.native_writer_phase = "lock-wait"
            exc.native_lock_wait_ms = (time.monotonic() - wait_started) * 1000
            exc.native_lock_held_ms = 0.0
            raise
        acquired = time.monotonic()
        # One recovery window across reconciliation, planning and all writes.
        # Ordinary deliveries get up to five seconds after acquisition, bounded
        # by lock budget + 0.5s overall (20.5s ordinary, 2.5s short close).
        # Healthy first attempts remain allowed; expiry forbids further waiting.
        self._publication_deadline = min(acquired + 5.0, wait_started + lock_timeout_seconds + 0.5)
        phase = "reconciliation"
        try:
            self.ownership()
            self._reconcile()  # Bookkeeping cleanup only; never retries task effects.
            phase = "planning"
            controls = self.control()
            if op not in {"close", "reconcile"} and controls != "clear":
                raise Refused("cleanup-only:" + controls)
            if op == "reconcile":
                return {"status": "reconciled", "controls": controls}
            key = line(request["key"])
            tx_path = self.journal_root / "transactions" / (digest(key.encode()) + ".json")
            request_hash = digest(encoded(request))
            if tx_path.exists():
                tx = json.loads(tx_path.read_bytes())
                if tx["request_sha256"] != request_hash:
                    raise Refused("conflicting-duplicate")
                # Replayed admission cannot grant authority after terminal close.
                if op != "close":
                    state = self._session(tx["activation"])
                    if state["status"] != "active":
                        raise Refused("activation-closed")
                    self.check_claims(state["claims"], state["id"])
                result = dict(tx["result"])
                if op in {"start", "activate", "resume"}:
                    result["working_tree"] = self.work_state({"root": state["workspace"]})
                return {**result, "duplicate": True, "controls": controls}
            result, writes, activation = self._plan(request)
            self.check_claims([x["path"] for x in writes], activation)
            tx = {"key": key, "operation": op, "activation": activation,
                  "request_sha256": request_hash, "writes": writes,
                  "plan_sha256": digest(encoded(writes)), "complete": False,
                  "result": result}
            self._atomic(tx_path, encoded(tx))
            self.fault("after-journal")
            phase = "publication"
            self._publish(tx, tx_path)
            return {**result, "duplicate": False, "controls": controls}
        except WriterBusy as exc:
            # Nested event-store locks can time out after public writes. Keep
            # that uncertainty explicit; never classify by exception class alone.
            exc.native_writer_phase = phase
            exc.native_lock_wait_ms = wait_ms
            exc.native_lock_held_ms = (time.monotonic() - acquired) * 1000
            raise
        finally:
            self._publication_deadline = None
            mutex.release_lock(handle, token)

    def validate_claim_admission(self, claims):
        # Use precisely the same conservative normalization as publication.
        # Existing live records are NOT filtered or rewritten by this check.
        shared = [claim_base(str(self.coord / p), self.os_root)
                  for p in ("mailbox/operator", "sessions", "sessions/_closed")]
        for claim in claims:
            base = claim_base(claim, self.os_root)
            if any(target == base or target.startswith(base + "/") for target in shared):
                raise RequestInvalid("broad-shared-closeout-claim-use-exact-file", "claims[]")

    def validate_artifact_paths(self, artifacts):
        # Syntax/duplicate checks do not need activation lookup; actual project
        # containment and file reads remain in _assets under the writer lock.
        seen = set()
        for artifact in artifacts:
            relative = artifact["path"]
            path = Path(relative)
            # Only lexical normalization here: resolving the original spelling
            # against the selected project (including symlinks) stays in _assets.
            normalized = Path(os.path.normcase(os.path.normpath(relative)))
            if path.is_absolute() or path.drive or path.root or ".." in normalized.parts:
                raise Refused("artifact-outside-project")
            if set(normalized.parts) & {"inputs", "background", ".cowork", ".git"} or normalized in {
                    Path("asset-registry.csv"), Path("interaction-log.csv")}:
                raise Refused("artifact-readonly-or-bookkeeping")
            if relative in seen:
                raise Refused("duplicate-artifact")
            seen.add(relative)

    def _session(self, activation):
        if not re.fullmatch(r"[a-zA-Z0-9-]{1,120}", activation):
            raise Refused("invalid-activation")
        path = self.root / "activations" / (activation + ".json")
        if not path.is_file():
            raise Refused("activation-missing")
        return json.loads(path.read_bytes())

    def _session_bytes(self, state):
        fields = {k: state[k] for k in ("id", "tab", "harness", "model", "project",
                                        "status", "started", "heartbeat")}
        lines = ["---"] + [k + ": " + line(str(v)) for k, v in fields.items()]
        lines += ["writer: aios-native", "claims:"] + ["  - " + line(c) for c in state["claims"]]
        lines += ["---", "Current task: " + line(state["task"]), ""]
        return "\n".join(lines).encode()

    def _plan(self, req):
        op = req["operation"]
        stamp = self.clock().isoformat(timespec="seconds")
        date = stamp[:10]
        writes = []
        if op in {"start", "activate"}:
            project_id = line(req["project"])
            project = self.config["projects"].get(project_id)
            if not project:
                raise Refused("project-not-selected")
            native = line(req["native_id"])
            harness = req["harness"]
            if harness not in {"codex-cli", "claude-code"}:
                raise Refused("unsupported-harness")
            alias = self.root / "aliases" / (digest((harness + ":" + native).encode()) + ".json")
            if alias.exists():
                old = self._session(json.loads(alias.read_bytes())["activation"])
                if old["status"] == "active":
                    raise Refused("native-session-already-active:" + old["id"])
                if op != "activate":
                    raise Refused("explicit-activation-required")
            workspace = Path(req.get("worktree", project["root"])).resolve()
            allowed_roots = [Path(project["root"]).resolve()] + [Path(x).resolve() for x in project.get("worktrees", [])]
            if not any(workspace_matches(project, workspace, r) for r in allowed_roots):
                raise Refused("workspace-not-selected")
            work = self.work_state({"root": str(workspace)})
            sid = date.replace("-", "") + "-" + harness.split("-")[0] + "-v2-" + digest(
                (self.config["epoch"] + ":" + req["key"]).encode())[:16]
            # Existing terminal ids and v1 files can never be replaced.
            if any(p.exists() for p in [self.root / "activations" / (sid + ".json"),
                       self.coord / "sessions" / (sid + ".md"),
                       self.coord / "sessions" / "_closed" / (sid + ".md")]):
                raise Refused("activation-id-collision")
            claims = [line(x) for x in req.get("claims", [])]
            self.check_claims(claims, sid)
            view = snapshot(self.coord, self.clock())
            slots = view.slots.get(harness)
            if slots is None or slots.budget is None or slots.live >= slots.budget:
                raise Refused("harness-budget-unavailable-or-full")
            tab = line(req.get("tab", "AIOS WORK"))
            if not re.fullmatch(r"[A-Z0-9]+ [A-Z0-9]+", tab) or len(tab) > 10:
                raise Refused("invalid-tab")
            state = {"id": sid, "tab": tab, "harness": harness, "model": line(req.get("model", "unavailable")),
                     "project": project_id, "status": "active", "started": stamp, "heartbeat": stamp,
                     "claims": claims, "task": line(req.get("task", "Awaiting agent scope")),
                     "native_id": native, "epoch": self.config["epoch"], "workspace": str(workspace)}
            writes.append(self._mut(alias, encoded({"activation": sid})))
        else:
            sid = req["activation"]
            state = self._session(sid)
            # stale-sweep-freshness-under-lock: reconciliation may refresh it.
            if op == "close" and getattr(self, "_compat_close_reason", None) == "stale-sweep":
                if (self.clock() - datetime.fromisoformat(state["heartbeat"])).total_seconds() <= 3600:
                    raise Refused("activation-still-live")
            if state["epoch"] != self.config["epoch"]:
                raise Refused("activation-epoch-mismatch")
            if state["status"] != "active":
                raise Refused("activation-closed")
            project = self.config["projects"].get(state["project"])
            if not project:
                raise Refused("project-not-selected")
            workspace = Path(req.get("worktree", state["workspace"])).resolve()
            allowed_roots = [Path(project["root"]).resolve()] + [Path(x).resolve() for x in project.get("worktrees", [])]
            if not any(workspace_matches(project, workspace, r) for r in allowed_roots):
                raise Refused("workspace-not-selected")
            work = self.work_state({"root": str(workspace)}) if op == "resume" else None
            state["workspace"] = str(workspace)
            state["heartbeat"] = stamp
            if "model_source" in req:
                if req["model_source"] != "claude-statusline" or state["harness"] != "claude-code" or op != "checkpoint":
                    raise Refused("invalid-model-source")
                state["model"] = line(req["model"])
                state["model_source"] = "claude-statusline"
            if "claims" in req:
                state["claims"] = [line(x) for x in req["claims"]]
            if op != "close":
                self.check_claims(state["claims"], sid)
            if "task" in req:
                state["task"] = line(req["task"])
        root = Path(project["root"]).resolve()
        if req.get("artifacts"):
            state["assets"] = sorted(set(state.get("assets", [])) | {a["path"] for a in req["artifacts"]})
            if not project.get("provenance", True):
                raise Refused("project-provenance-not-selected")
            writes += self._assets(root, state, req["artifacts"], date)
        semantic = state.setdefault("semantic", {})
        for field in ("summary", "input_summary", "decisions", "priority", "relaunch",
                      "resume", "worktree", "branch", "initiator", "task_difficulty"):
            if field in req:
                semantic[field] = req[field]
        if op == "close":
            req = {**semantic, **req}
            state["status"] = "done"
            state["claims"] = []
            state["closed"] = stamp
            writes += self._closeout(root, state, req, date)
        active = self.coord / "sessions" / (sid + ".md")
        closed = self.coord / "sessions" / "_closed" / (sid + ".md")
        writes.append(self._mut(self.root / "activations" / (sid + ".json"), encoded(state)))
        if op == "close":
            writes.append(self._mut(closed, self._session_bytes(state)))
            if active.exists():
                writes.append(self._mut(active, None))
        else:
            writes.append(self._mut(active, self._session_bytes(state)))
        if not getattr(self, "sharded", False):
            # Small generated lifecycle projection, no independent state or provider payloads.
            rows = []
            for path in sorted((self.root / "activations").glob("*.json")):
                item = json.loads(path.read_bytes())
                if item["id"] != sid:
                    rows.append({k: item[k] for k in ("id", "project", "status", "heartbeat")})
            rows.append({k: state[k] for k in ("id", "project", "status", "heartbeat")})
            rows.sort(key=lambda x: x["id"])
            projection = {"sessions": rows, "tokens": "unavailable", "cost": "unavailable",
                          "coverage": "native-delivery-unverified", "writer": "aios-native"}
            writes.append(self._mut(self.root / "views" / "sessions.json", encoded(projection)))
        return ({"status": "closed" if op == "close" else "active", "activation": sid,
                 "working_tree": work, "claims": state["claims"],
                 "human_input": "claims, substantive summaries and verification remain agent/human decisions"},
                writes, sid)

    def _artifact_body(self, path):
        return path.read_bytes()

    def _assets(self, root, state, artifacts, date):
        registry = root / "asset-registry.csv"
        fields, rows = csv_rows(registry, {"asset_path", "creator", "created", "last_modified",
                                           "verification", "ai_output_hash", "model_metadata"})
        writes = []
        seen = set()
        for artifact in artifacts:
            if set(artifact) - {"path", "asset_type", "creator", "verification", "notes", "text"}:
                raise Refused("unknown-artifact-field")
            relative = line(artifact["path"])
            path = (root / relative).resolve()
            if not beneath(path, root) or Path(relative).is_absolute():
                raise Refused("artifact-outside-project")
            parts = {os.path.normcase(part) for part in path.relative_to(root).parts}
            if parts & {"inputs", "background", ".cowork", ".git"} or path in {
                registry, root / "interaction-log.csv"}:
                raise Refused("artifact-readonly-or-bookkeeping")
            if relative in seen:
                raise Refused("duplicate-artifact")
            seen.add(relative)
            body = self._artifact_body(path)
            sha = digest(body)
            creator = artifact.get("creator", "agent")
            verification = artifact.get("verification", "not-verified")
            if creator not in {"agent", "mixed"} or verification not in {
                "not-verified", "partially-verified"}:
                raise Refused("human-verification-required")
            matches = [r for r in rows if r["asset_path"] == relative]
            if len(matches) > 1:
                raise Refused("duplicate-registry-row")
            row = matches[0] if matches else {k: "" for k in fields}
            row.update(asset_path=relative, creator=creator, created=row.get("created") or date,
                       last_modified=date, verification=verification,
                       model_metadata=state["model"] + " / " + state["harness"],
                       ai_output_hash=sha if artifact.get("text", True) else "")
            for field in ("asset_type", "notes"):
                if field in fields:
                    row[field] = line(artifact.get(field, "other" if field == "asset_type" else ""))
            if not matches:
                rows.append(row)
            if artifact.get("text", True):
                snap = root / ".cowork" / "snapshots" / (sha + ".snap")
                if snap.exists() and hash_at(snap) != sha:
                    raise Refused("snapshot-integrity-failed")
                writes.append(self._mut(snap, body))
        writes.append(self._mut(registry, csv_bytes(fields, rows)))
        return writes

    def _closeout(self, root, state, req, date):
        decisions = req.get("decisions", [])
        if not isinstance(decisions, list):
            raise Refused("invalid-decisions")
        decisions = [line(x) for x in decisions]
        summary = line(req.get("summary", "PENDING: substantive closeout was not supplied"))
        sid = state["id"]
        fm = {"from": sid, "to": "operator", "sent": state["heartbeat"],
              "re": "closeout - " + state["project"], "type": "closeout",
              "project": state["project"], "priority": req.get("priority", "medium"),
              "relaunch": req.get("relaunch", "operator-decides"),
              "resume": req.get("resume", "native conversation; establish fresh activation"),
              "worktree": req.get("worktree", "none"), "branch": req.get("branch", "none"),
              "decision_points": str(len(decisions))}
        if fm["priority"] not in {"low", "medium", "high"} or fm["relaunch"] not in {
            "yes", "no", "operator-decides"}:
            raise Refused("invalid-closeout-disposition")
        lines = ["---"] + [k + ": " + line(v) for k, v in fm.items()]
        lines += ["---", summary] + [str(i + 1) + ". " + d for i, d in enumerate(decisions)]
        lines += ["", "Native writer closed bookkeeping; judgments above are agent-supplied.", ""]
        note = self.coord / "mailbox" / "operator" / (sid + "-closeout.md")
        if note.exists():
            raise Refused("closeout-name-collision")
        writes = [self._mut(note, "\n".join(lines).encode())]
        if not self.config["projects"][state["project"]].get("provenance", True):
            return writes
        log = root / "interaction-log.csv"
        body = log.read_bytes()
        parsed = list(csv.reader(io.StringIO(body.decode("utf-8-sig"), newline="")))
        if not parsed:
            raise Refused("unsupported-ledger-schema")
        fields = parsed[0]
        required = {"date", "session_id", "harness", "model", "researcher_input_summary",
                    "agent_output_summary", "assets_affected"}
        if not required <= set(fields) or any(fields.count(k) != 1 for k in required):
            raise Refused("unsupported-ledger-schema")
        position = fields.index("session_id")
        if any(len(r) > position and r[position] == sid for r in parsed[1:]):
            raise Refused("interaction-row-collision")
        row = {k: "" for k in fields}
        row.update(date=date, session_id=sid, harness=state["harness"], model=state["model"],
                   researcher_input_summary=line(req.get("input_summary", "PENDING: agent input summary")),
                   agent_output_summary=summary,
                   assets_affected="; ".join(state.get("assets", [])))
        for k, default in [("notes", "Deterministic lifecycle fields; agent-supplied summary"),
                           ("initiator", "human"), ("task_difficulty", "medium")]:
            if k in fields:
                row[k] = line(req.get(k, default))
        stream = io.StringIO(newline="")
        csv.writer(stream, lineterminator="\n").writerow([row[k] for k in fields])
        prefix = body + (b"" if body.endswith((b"\n", b"\r")) else b"\n")
        writes.append(self._mut(log, prefix + stream.getvalue().encode()))
        return writes
