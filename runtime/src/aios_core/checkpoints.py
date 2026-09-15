"""Checkpoints: a verified replay state pinned to a byte offset and prefix hash (T-005).

A checkpoint is a generated artifact (DEC-001 rule 6). It never becomes authority: on
load it is checked against the log prefix it claims to summarize, and replay continues
from its byte offset. Files are ``checkpoints/<sequence:012d>-<head16>.json``, written
atomically; the newest by sequence wins. A half-written temp file is ignored.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from .events import GENESIS_EVENT_ID, KernelError, canonical_bytes
from .replay import AggregateState, CommittedCommand, CorruptLog, ReplayState

if TYPE_CHECKING:  # pragma: no cover
    from .store import EventStore

CHECKPOINT_SCHEMA_VERSION = "aios-kernel-checkpoint-v1"
_NAME_WIDTH = 12


@dataclass(frozen=True)
class Checkpoint:
    name: str
    state: ReplayState


def _state_to_document(state: ReplayState) -> dict:
    return {
        "schema_version": CHECKPOINT_SCHEMA_VERSION,
        "sequence": state.last_sequence,
        "event_count": state.event_count,
        "head_event_id": state.head_event_id,
        "byte_offset": state.byte_offset,
        "prefix_sha256": state.prefix_sha256,
        "projection_sha256": state.projection_sha256,
        "aggregates": {k: v.as_dict() for k, v in sorted(state.aggregates.items())},
        "commands": {k: v.as_dict() for k, v in sorted(state.commands.items())},
    }


def _document_to_state(document: dict) -> ReplayState:
    required = {
        "schema_version", "sequence", "event_count", "head_event_id", "byte_offset",
        "prefix_sha256", "projection_sha256", "aggregates", "commands",
    }
    if not isinstance(document, dict) or set(document) != required:
        raise CorruptLog("checkpoint-schema")
    if document["schema_version"] != CHECKPOINT_SCHEMA_VERSION:
        raise CorruptLog("checkpoint-schema-version")
    commands = {
        key: CommittedCommand(**value) for key, value in document["commands"].items()
    }
    state = ReplayState(
        aggregates={key: AggregateState(**value) for key, value in document["aggregates"].items()},
        commands=commands,
        event_ids={command.event_id for command in commands.values()},
        event_count=document["event_count"],
        last_sequence=document["sequence"],
        head_event_id=document["head_event_id"],
        byte_offset=document["byte_offset"],
        trailing_bytes=0,
        prefix_sha256=document["prefix_sha256"],
    )
    if state.event_count != len(commands) or state.last_sequence != state.event_count:
        raise CorruptLog("checkpoint-inconsistent")
    if state.event_count == 0 and state.head_event_id != GENESIS_EVENT_ID:
        raise CorruptLog("checkpoint-inconsistent")
    if state.projection_sha256 != document["projection_sha256"]:
        raise CorruptLog("checkpoint-projection-mismatch")
    return state


def checkpoint_name(state: ReplayState) -> str:
    return f"{state.last_sequence:0{_NAME_WIDTH}d}-{state.head_event_id[:16]}.json"


def write_checkpoint(store: "EventStore", state: ReplayState | None = None) -> Checkpoint:
    """Persist the current verified state. Takes the writer lock so the offset is exact."""
    handle, token, _ = store.acquire_lock()
    try:
        from .replay import load_state

        current = state if state is not None else load_state(store)
        if current.trailing_bytes:
            # Never checkpoint over a torn tail: recover first (the store does this on append).
            store._truncate_torn_tail(current)
            current = current.copy()
            current.trailing_bytes = 0
        name = checkpoint_name(current)
        target = store.checkpoints_path / name
        body = canonical_bytes(_state_to_document(current)) + b"\n"
        if target.exists():
            if target.read_bytes() != body:
                raise CorruptLog(f"checkpoint-collision {name}")
            return Checkpoint(name, current)
        temporary = store.checkpoints_path / f".{name}.{os.getpid()}.{time.monotonic_ns()}.tmp"
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0), 0o600)
        try:
            os.write(descriptor, body)
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        store._hook("after-checkpoint-temp-write")
        os.replace(temporary, target)
        return Checkpoint(name, current)
    finally:
        store.release_lock(handle, token)


def list_checkpoints(store: "EventStore") -> list[Path]:
    if not store.checkpoints_path.is_dir():
        return []
    return sorted(
        p for p in store.checkpoints_path.iterdir()
        if p.is_file() and p.suffix == ".json" and not p.name.startswith(".")
    )


def load_checkpoint(path: Path) -> Checkpoint:
    raw = path.read_bytes()
    try:
        document = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CorruptLog(f"checkpoint-not-json {path.name}") from exc
    if canonical_bytes(document) + b"\n" != raw:
        raise CorruptLog(f"checkpoint-non-canonical {path.name}")
    state = _document_to_state(document)
    if path.name != checkpoint_name(state):
        raise CorruptLog(f"checkpoint-name-mismatch {path.name}")
    return Checkpoint(path.name, state)


def load_latest_checkpoint(store: "EventStore") -> Checkpoint | None:
    """The newest checkpoint, or ``None``. A malformed newest checkpoint fails closed."""
    paths = list_checkpoints(store)
    if not paths:
        return None
    return load_checkpoint(paths[-1])


def prune_checkpoints(store: "EventStore", keep: int = 2) -> list[str]:
    """Remove all but the newest ``keep`` checkpoints (generated artifacts only)."""
    if keep < 1:
        raise KernelError("keep at least one checkpoint")
    removed: list[str] = []
    handle, token, _ = store.acquire_lock()
    try:
        for path in list_checkpoints(store)[:-keep]:
            path.unlink()
            removed.append(path.name)
    finally:
        store.release_lock(handle, token)
    return removed
