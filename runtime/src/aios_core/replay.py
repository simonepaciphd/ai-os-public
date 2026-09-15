"""Deterministic replay and projection (T-005).

Replay reads committed lines only (an incomplete final line is uncommitted, DEC-001
rule 5), verifies every line against the kernel record schema, the hash chain, the
per-aggregate version sequence, command uniqueness, and the content-addressed blob,
and folds them into a :class:`ReplayState`. Any violation raises :class:`CorruptLog`
naming the line: fail closed, nothing repaired here.

The projection is a pure function of the committed history: the same lines always
produce the same ``projection_sha256``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterator

from .events import (
    GENESIS_EVENT_ID,
    KernelError,
    canonical_bytes,
    record_errors,
    sha256_file,
    sha256_hex,
)

if TYPE_CHECKING:  # pragma: no cover
    from .store import EventStore


class CorruptLog(KernelError):
    """Committed history violates an invariant. Recovery is a human decision."""


@dataclass(frozen=True)
class AggregateState:
    version: int
    event_type: str
    payload_sha256: str
    last_event_id: str

    def as_dict(self) -> dict:
        return {
            "version": self.version,
            "event_type": self.event_type,
            "payload_sha256": self.payload_sha256,
            "last_event_id": self.last_event_id,
        }


@dataclass(frozen=True)
class CommittedCommand:
    aggregate_id: str
    aggregate_version: int
    event_type: str
    payload_sha256: str
    event_id: str
    sequence: int

    def as_dict(self) -> dict:
        return dict(self.__dict__)


@dataclass
class ReplayState:
    aggregates: dict[str, AggregateState] = field(default_factory=dict)
    commands: dict[str, CommittedCommand] = field(default_factory=dict)
    event_ids: set[str] = field(default_factory=set)
    event_count: int = 0
    last_sequence: int = 0
    head_event_id: str = GENESIS_EVENT_ID
    byte_offset: int = 0  # end of the last committed line
    trailing_bytes: int = 0  # uncommitted torn tail after byte_offset
    prefix_sha256: str = sha256_hex(b"")  # hash of bytes[0:byte_offset]

    def projection(self) -> dict:
        """Deterministic current-state projection (no timestamps, no paths)."""
        return {
            "schema_version": "aios-kernel-projection-v1",
            "aggregates": {k: v.as_dict() for k, v in sorted(self.aggregates.items())},
            "commands": {k: v.event_id for k, v in sorted(self.commands.items())},
            "event_count": self.event_count,
            "head_event_id": self.head_event_id,
        }

    @property
    def projection_sha256(self) -> str:
        return sha256_hex(canonical_bytes(self.projection()))

    def copy(self) -> "ReplayState":
        return ReplayState(
            aggregates=dict(self.aggregates),
            commands=dict(self.commands),
            event_ids=set(self.event_ids),
            event_count=self.event_count,
            last_sequence=self.last_sequence,
            head_event_id=self.head_event_id,
            byte_offset=self.byte_offset,
            trailing_bytes=self.trailing_bytes,
            prefix_sha256=self.prefix_sha256,
        )


# ------------------------------------------------------------------- line reading


def committed_split(raw: bytes) -> tuple[bytes, int]:
    """Split raw log bytes into (committed bytes, torn tail length)."""
    if not raw or raw.endswith(b"\n"):
        return raw, 0
    end = raw.rfind(b"\n") + 1
    return raw[:end], len(raw) - end


def iter_committed_lines(raw: bytes, start_offset: int = 0) -> Iterator[tuple[int, bytes]]:
    """Yield (absolute byte offset of line end, line bytes without newline)."""
    committed, _ = committed_split(raw)
    if len(committed) <= start_offset:
        return
    position = start_offset
    for line in committed[start_offset:].split(b"\n")[:-1]:
        position += len(line) + 1
        yield position, line


# --------------------------------------------------------------------- folding


def _fold_line(state: ReplayState, line: bytes, line_number: int, blobs_dir: Path) -> None:
    try:
        record = json.loads(line.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CorruptLog(f"line {line_number}: not-json") from exc
    if canonical_bytes(record) != line:
        raise CorruptLog(f"line {line_number}: non-canonical")
    errors = record_errors(record)
    if errors:
        raise CorruptLog(f"line {line_number}: schema {'; '.join(errors)}")
    if record["sequence"] != state.last_sequence + 1:
        raise CorruptLog(f"line {line_number}: sequence-gap")
    if record["previous_event_id"] != state.head_event_id:
        raise CorruptLog(f"line {line_number}: chain-broken")
    if record["event_id"] in state.event_ids:
        raise CorruptLog(f"line {line_number}: duplicate-event-id")
    if record["command_id"] in state.commands:
        raise CorruptLog(f"line {line_number}: duplicate-command-id")
    aggregate = state.aggregates.get(record["aggregate_id"])
    current_version = aggregate.version if aggregate else 0
    if record["aggregate_version"] != current_version + 1:
        raise CorruptLog(f"line {line_number}: aggregate-version-gap")
    blob = blobs_dir / record["payload_sha256"]
    if not blob.is_file() or sha256_file(blob) != record["payload_sha256"]:
        raise CorruptLog(f"line {line_number}: blob-missing-or-mismatched")

    state.aggregates[record["aggregate_id"]] = AggregateState(
        version=record["aggregate_version"],
        event_type=record["event_type"],
        payload_sha256=record["payload_sha256"],
        last_event_id=record["event_id"],
    )
    state.commands[record["command_id"]] = CommittedCommand(
        aggregate_id=record["aggregate_id"],
        aggregate_version=record["aggregate_version"],
        event_type=record["event_type"],
        payload_sha256=record["payload_sha256"],
        event_id=record["event_id"],
        sequence=record["sequence"],
    )
    state.event_ids.add(record["event_id"])
    state.event_count += 1
    state.last_sequence = record["sequence"]
    state.head_event_id = record["event_id"]


def replay_bytes(raw: bytes, blobs_dir: Path, start: ReplayState | None = None) -> ReplayState:
    """Fold committed lines into state, optionally continuing from a verified checkpoint."""
    state = start.copy() if start is not None else ReplayState()
    committed, torn = committed_split(raw)
    if start is not None:
        if state.byte_offset > len(committed):
            raise CorruptLog("checkpoint-ahead-of-log")
        if sha256_hex(committed[: state.byte_offset]) != state.prefix_sha256:
            raise CorruptLog("checkpoint-prefix-mismatch")
    line_number = state.last_sequence
    for end, line in iter_committed_lines(raw, state.byte_offset):
        line_number += 1
        _fold_line(state, line, line_number, blobs_dir)
        state.byte_offset = end
    state.prefix_sha256 = sha256_hex(committed)
    state.trailing_bytes = torn
    return state


def replay(store: "EventStore", start: ReplayState | None = None) -> ReplayState:
    raw = store.events_path.read_bytes() if store.events_path.exists() else b""
    return replay_bytes(raw, store.blobs_path, start)


def load_state(store: "EventStore") -> ReplayState:
    """State from the latest valid checkpoint plus the log tail, else a full replay.

    A checkpoint that disagrees with the log (ahead of it, or over a rewritten prefix)
    is corruption of append-only history and fails closed rather than being ignored.
    """
    from .checkpoints import load_latest_checkpoint

    checkpoint = load_latest_checkpoint(store)
    return replay(store, checkpoint.state if checkpoint is not None else None)


def iter_records(store: "EventStore") -> Iterator[dict[str, Any]]:
    """Committed records in order, without verification beyond JSON parsing."""
    if not store.events_path.exists():
        return
    raw = store.events_path.read_bytes()
    for _, line in iter_committed_lines(raw):
        yield json.loads(line.decode("utf-8"))


# ---------------------------------------------------------------------- verify


def verify(store: "EventStore") -> dict:
    """Integrity report for humans and tests. Never raises; never writes."""
    report: dict[str, Any] = {
        "events_path": store.events_path.name,
        "ok": True,
        "error": None,
        "event_count": 0,
        "head_event_id": GENESIS_EVENT_ID,
        "projection_sha256": None,
        "trailing_bytes": 0,
        "stray_blob_temporaries": sorted(
            p.name for p in store.blobs_path.glob(".*.tmp")
        ),
        "checkpoint": None,
    }
    try:
        from .checkpoints import load_latest_checkpoint

        checkpoint = load_latest_checkpoint(store)
        report["checkpoint"] = checkpoint.name if checkpoint is not None else None
        state = replay(store, checkpoint.state if checkpoint is not None else None)
    except KernelError as exc:
        report["ok"] = False
        report["error"] = str(exc)
        try:
            raw = store.events_path.read_bytes() if store.events_path.exists() else b""
            report["trailing_bytes"] = committed_split(raw)[1]
        except OSError:
            pass
        return report
    report.update(
        event_count=state.event_count,
        head_event_id=state.head_event_id,
        projection_sha256=state.projection_sha256,
        trailing_bytes=state.trailing_bytes,
    )
    return report
