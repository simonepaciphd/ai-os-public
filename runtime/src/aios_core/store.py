"""The single-writer append-only event store (T-005), per DEC-001.

Layout under ``root``::

    events.ndjson     one canonical JSON kernel record per line; the authority
    blobs/<sha256>    content-addressed canonical JSON payloads
    checkpoints/      generated; see :mod:`aios_core.checkpoints`
    .writer.lock      persistent file; an OS byte-range lock fences writers

Admission path for every command (all under the writer lock):

1. Validate the payload (if a validator is configured) before anything is written.
2. Load state (from the latest valid checkpoint plus the tail, or a full replay).
3. If the log has a torn final line, truncate it: it was never committed.
4. Same ``command_id`` with the same aggregate, type, and payload hash: return the
   committed event (idempotent). Same id with different content: fail closed.
5. ``expected_version`` must equal the aggregate's current version, else conflict.
6. Publish the blob (temp file, fsync, ``os.replace``), then append one line + fsync.

Test hooks (``hooks``) fire at named transitions so a crash can be simulated at each.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO, Callable, Mapping

from . import replay as _replay
from .events import (
    KernelError,
    ValidationError,
    canonical_bytes,
    make_record,
    sha256_file,
    sha256_hex,
)

if os.name == "nt":
    import msvcrt
else:
    import fcntl


class VersionConflict(KernelError):
    """The caller's expected aggregate version is not the current one."""


class DuplicateConflict(KernelError):
    """A command id was reused with different content."""


class WriterBusy(KernelError):
    """The writer lock could not be acquired within the timeout."""


HOOK_POINTS = (
    "after-validate",
    "after-load-state",
    "after-recover",
    "after-blob-temp-write",
    "after-blob-publish",
    "before-append-write",
    "after-append-write",
    "after-append-fsync",
    "after-checkpoint-temp-write",
)

Validator = Callable[[str, Any], list[str]]


@dataclass(frozen=True)
class AppendResult:
    status: str  # "committed" | "duplicate"
    event_id: str
    sequence: int
    aggregate_version: int
    payload_sha256: str
    blob_created: bool
    lock_wait_ms: float
    torn_bytes_removed: int

    def as_dict(self) -> dict:
        return dict(self.__dict__)


class EventStore:
    def __init__(
        self,
        root: Path,
        *,
        validator: Validator | None = None,
        hooks: Mapping[str, Callable[[], None]] | None = None,
        lock_timeout_seconds: float = 15.0,
    ) -> None:
        self.root = Path(root)
        self.events_path = self.root / "events.ndjson"
        self.blobs_path = self.root / "blobs"
        self.checkpoints_path = self.root / "checkpoints"
        self.lock_path = self.root / ".writer.lock"
        self.validator = validator
        self.hooks = dict(hooks or {})
        self.lock_timeout_seconds = lock_timeout_seconds
        for name in self.hooks:
            if name not in HOOK_POINTS:
                raise KernelError(f"unknown hook point: {name}")
        self.root.mkdir(parents=True, exist_ok=True)
        self.blobs_path.mkdir(exist_ok=True)
        self.checkpoints_path.mkdir(exist_ok=True)
        self._ensure_lock_file()

    # ------------------------------------------------------------------ hooks

    def _hook(self, name: str) -> None:
        hook = self.hooks.get(name)
        if hook is not None:
            hook()

    # ------------------------------------------------------------------- lock

    def _ensure_lock_file(self) -> None:
        try:
            with self.lock_path.open("xb", buffering=0) as handle:
                handle.write(b"0")
                os.fsync(handle.fileno())
        except FileExistsError:
            pass
        except PermissionError:
            # Windows maps a simultaneous create-exclusive collision to EACCES. The file
            # is never deleted, so visible existence proves the race rather than a fault.
            if not self.lock_path.is_file():
                raise

    def acquire_lock(self, timeout_seconds: float | None = None) -> tuple[BinaryIO, str, float]:
        """Take the writer lock (OS advisory byte-range lock on the first byte)."""
        timeout = self.lock_timeout_seconds if timeout_seconds is None else timeout_seconds
        token = f"{os.getpid()}-{time.monotonic_ns()}"
        start = time.perf_counter()
        while True:
            handle = self.lock_path.open("r+b", buffering=0)
            handle.seek(0)
            try:
                if os.name == "nt":
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                handle.close()
                if time.perf_counter() - start >= timeout:
                    raise WriterBusy(f"writer lock timed out: {self.lock_path}")
                time.sleep(0.001)
                continue
            return handle, token, (time.perf_counter() - start) * 1000.0

    def release_lock(self, handle: BinaryIO, token: str) -> None:
        del token  # the byte-range lock itself is the fence; the token only labels the holder
        try:
            handle.seek(0)
            if os.name == "nt":
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()

    # ------------------------------------------------------------------ blobs

    def blob_path(self, digest: str) -> Path:
        return self.blobs_path / digest

    def publish_blob(self, payload: Any) -> tuple[str, bool]:
        """Content-addressed publish: temp file, fsync, same-directory ``os.replace``."""
        body = canonical_bytes(payload)
        digest = sha256_hex(body)
        target = self.blob_path(digest)
        if target.exists():
            if sha256_file(target) != digest:
                raise _replay.CorruptLog(f"blob content mismatch: {digest}")
            return digest, False
        temporary = self.blobs_path / f".{digest}.{os.getpid()}.{time.monotonic_ns()}.tmp"
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0), 0o600)
        try:
            os.write(descriptor, body)
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        self._hook("after-blob-temp-write")
        os.replace(temporary, target)
        if sha256_file(target) != digest:
            raise _replay.CorruptLog(f"published blob mismatch: {digest}")
        return digest, True

    def read_payload(self, digest: str) -> Any:
        """Load a payload by hash, verifying the bytes."""
        path = self.blob_path(digest)
        if not path.is_file():
            raise _replay.CorruptLog(f"missing blob: {digest}")
        raw = path.read_bytes()
        if sha256_hex(raw) != digest:
            raise _replay.CorruptLog(f"blob content mismatch: {digest}")
        return json.loads(raw.decode("utf-8"))

    # ---------------------------------------------------------------- recovery

    def _truncate_torn_tail(self, state: "_replay.ReplayState") -> int:
        """Drop an incomplete final line. Caller must hold the writer lock."""
        if state.trailing_bytes == 0:
            return 0
        with self.events_path.open("r+b") as handle:
            handle.truncate(state.byte_offset)
            handle.flush()
            os.fsync(handle.fileno())
        return state.trailing_bytes

    def recover(self) -> int:
        """Truncate a torn tail under the lock; returns bytes removed. Committed
        corruption is never repaired here: replay raises and nothing is touched."""
        handle, token, _ = self.acquire_lock()
        try:
            state = _replay.load_state(self)
            return self._truncate_torn_tail(state)
        finally:
            self.release_lock(handle, token)

    # ------------------------------------------------------------------ append

    def append(
        self,
        *,
        aggregate_id: str,
        command_id: str,
        expected_version: int,
        event_type: str,
        payload: Any,
    ) -> AppendResult:
        if self.validator is not None:
            errors = self.validator(event_type, payload)
            if errors:
                raise ValidationError(errors)
        self._hook("after-validate")
        payload_bytes = canonical_bytes(payload)
        payload_sha256 = sha256_hex(payload_bytes)

        handle, token, wait_ms = self.acquire_lock()
        try:
            state = _replay.load_state(self)
            self._hook("after-load-state")
            removed = self._truncate_torn_tail(state)
            self._hook("after-recover")

            existing = state.commands.get(command_id)
            if existing is not None:
                same = (
                    existing.aggregate_id == aggregate_id
                    and existing.event_type == event_type
                    and existing.payload_sha256 == payload_sha256
                )
                if not same:
                    raise DuplicateConflict(f"command id reused with different content: {command_id}")
                return AppendResult(
                    "duplicate", existing.event_id, existing.sequence, existing.aggregate_version,
                    payload_sha256, False, wait_ms, removed,
                )

            current = state.aggregates.get(aggregate_id)
            current_version = current.version if current else 0
            if current_version != expected_version:
                raise VersionConflict(
                    f"{aggregate_id}: expected version {expected_version}, current {current_version}"
                )

            digest, created = self.publish_blob(payload)
            self._hook("after-blob-publish")
            record = make_record(
                aggregate_id=aggregate_id,
                aggregate_version=current_version + 1,
                command_id=command_id,
                event_type=event_type,
                payload_sha256=digest,
                previous_event_id=state.head_event_id,
                sequence=state.last_sequence + 1,
            )
            line = canonical_bytes(record) + b"\n"
            self._hook("before-append-write")
            with self.events_path.open("ab", buffering=0) as log:
                log.write(line)
                self._hook("after-append-write")
                os.fsync(log.fileno())
            self._hook("after-append-fsync")
            return AppendResult(
                "committed", record["event_id"], record["sequence"], record["aggregate_version"],
                digest, created, wait_ms, removed,
            )
        finally:
            self.release_lock(handle, token)

    # ------------------------------------------------------------------ reads

    def state(self) -> "_replay.ReplayState":
        """Current committed state (read-only; does not take the lock)."""
        return _replay.load_state(self)

    def verify(self) -> dict:
        """Human-readable integrity report; never raises, never writes."""
        return _replay.verify(self)
