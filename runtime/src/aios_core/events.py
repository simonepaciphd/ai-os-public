"""Event records and validation (T-005).

Two layers, deliberately separate:

* The **kernel record** (``aios-kernel-record-v1``) is the NDJSON line the store owns:
  DEC-001's fields plus ``sequence`` and ``previous_event_id`` so every line is
  self-describing and hash-chained. Its identity is a SHA-256 over canonical JSON of the
  identity fields; the payload itself lives in a content-addressed blob.
* The **normalized envelope** (``pilot/contracts/event-envelope.schema.json``) is the
  T-002 contract a payload may claim to satisfy. It is validated against the exact
  schema bytes with the stdlib-only validator below, which implements precisely the
  JSON Schema keywords those contracts use and refuses anything else.

Unknown event types, unsupported versions, and forbidden fields are rejected before a
byte is written. Errors are content-free: a JSON-pointer-like path plus a keyword.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Mapping

RECORD_SCHEMA_VERSION = "aios-kernel-record-v1"
GENESIS_EVENT_ID = "0" * 64

ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._~:/@+-]{0,255}$")
SHA256_RE = re.compile(r"^[a-f0-9]{64}$")

RECORD_KEYS = (
    "aggregate_id",
    "aggregate_version",
    "command_id",
    "event_id",
    "event_type",
    "payload_sha256",
    "previous_event_id",
    "schema_version",
    "sequence",
)
_IDENTITY_KEYS = tuple(key for key in RECORD_KEYS if key != "event_id")


class KernelError(RuntimeError):
    """Base class for every fail-closed kernel error."""


class ValidationError(KernelError):
    """A record or payload does not satisfy its declared schema. Carries content-free paths."""

    def __init__(self, errors: list[str]) -> None:
        super().__init__("; ".join(errors))
        self.errors = errors


def canonical_bytes(value: Any) -> bytes:
    """Canonical JSON: sorted keys, no whitespace, UTF-8, no trailing newline."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


# ------------------------------------------------------------------ kernel record


def event_identity(record: Mapping[str, Any]) -> str:
    """The event id: SHA-256 over the canonical JSON of every field except ``event_id``."""
    return sha256_hex(canonical_bytes({key: record[key] for key in _IDENTITY_KEYS}))


def make_record(
    *,
    aggregate_id: str,
    aggregate_version: int,
    command_id: str,
    event_type: str,
    payload_sha256: str,
    previous_event_id: str,
    sequence: int,
) -> dict[str, Any]:
    record = {
        "aggregate_id": aggregate_id,
        "aggregate_version": aggregate_version,
        "command_id": command_id,
        "event_type": event_type,
        "payload_sha256": payload_sha256,
        "previous_event_id": previous_event_id,
        "schema_version": RECORD_SCHEMA_VERSION,
        "sequence": sequence,
    }
    record["event_id"] = event_identity(record)
    errors = record_errors(record)
    if errors:
        raise ValidationError(errors)
    return record


def record_errors(record: Any) -> list[str]:
    """Structural validation of one kernel record. Empty list means valid."""
    errors: list[str] = []
    if not isinstance(record, dict):
        return ["/: type"]
    keys = tuple(sorted(record))
    if keys != RECORD_KEYS:
        missing = sorted(set(RECORD_KEYS) - set(keys))
        extra = sorted(set(keys) - set(RECORD_KEYS))
        if missing:
            errors.append(f"/: required {','.join(missing)}")
        if extra:
            errors.append(f"/: additionalProperties {','.join(extra)}")
        return errors
    if record["schema_version"] != RECORD_SCHEMA_VERSION:
        errors.append("/schema_version: const")
    for key in ("aggregate_id", "command_id", "event_type"):
        value = record[key]
        if not isinstance(value, str) or not ID_RE.match(value):
            errors.append(f"/{key}: pattern")
    for key in ("payload_sha256", "previous_event_id", "event_id"):
        value = record[key]
        if not isinstance(value, str) or not SHA256_RE.match(value):
            errors.append(f"/{key}: pattern")
    for key in ("aggregate_version", "sequence"):
        value = record[key]
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            errors.append(f"/{key}: minimum")
    if not errors and record["event_id"] != event_identity(record):
        errors.append("/event_id: identity")
    return errors


# --------------------------------------------------------- stdlib schema validator


class SchemaRegistry:
    """Schemas by file name, with the byte hash of each so validation is pinned."""

    def __init__(self, documents: Mapping[str, bytes]) -> None:
        self.schemas: dict[str, Any] = {}
        self.hashes: dict[str, str] = {}
        for name, raw in documents.items():
            self.schemas[name] = json.loads(raw.decode("utf-8"))
            self.hashes[name] = sha256_hex(raw)

    @classmethod
    def from_directory(cls, contracts_dir: Path, names: tuple[str, ...] = (
        "event-envelope.schema.json", "event-envelope-1.1.0.schema.json", "identity.schema.json"
    )) -> "SchemaRegistry":
        return cls({name: (contracts_dir / name).read_bytes() for name in names})

    def resolve(self, ref: str, current: str) -> tuple[Any, str]:
        """Resolve ``#/$defs/x`` (same document) or ``<file>#/$defs/x``."""
        document_name, _, pointer = ref.partition("#")
        document_name = document_name or current
        if document_name not in self.schemas:
            raise ValidationError([f"$ref: unknown document {document_name}"])
        node = self.schemas[document_name]
        for part in pointer.strip("/").split("/") if pointer.strip("/") else []:
            if not isinstance(node, dict) or part not in node:
                raise ValidationError([f"$ref: unresolvable {ref}"])
            node = node[part]
        return node, document_name


_SUPPORTED_KEYWORDS = {
    "$schema", "$id", "title", "description", "examples", "$defs", "$ref",
    "type", "const", "enum", "pattern", "format", "minimum", "required", "properties",
    "additionalProperties", "propertyNames", "maxProperties", "items", "maxItems",
    "uniqueItems", "oneOf", "allOf", "not",
}

_TYPE_CHECKS: dict[str, Callable[[Any], bool]] = {
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "null": lambda v: v is None,
}


def _is_datetime(value: str) -> bool:
    try:
        datetime.fromisoformat(value)
    except ValueError:
        return False
    return "T" in value or " " in value


def _validate(instance: Any, schema: Any, registry: SchemaRegistry, document: str, path: str,
              errors: list[str]) -> None:
    if schema is True:
        return
    if schema is False:
        errors.append(f"{path}: false")
        return
    if not isinstance(schema, dict):
        raise ValidationError([f"{path}: schema-not-object"])
    unknown = set(schema) - _SUPPORTED_KEYWORDS - {k for k in schema if k.startswith("x-")}
    if unknown:
        raise ValidationError([f"{path}: unsupported-keyword {','.join(sorted(unknown))}"])

    if "$ref" in schema:
        target, target_doc = registry.resolve(schema["$ref"], document)
        _validate(instance, target, registry, target_doc, path, errors)

    if "type" in schema:
        types = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(_TYPE_CHECKS[t](instance) for t in types):
            errors.append(f"{path}: type")
            return
    if "const" in schema and instance != schema["const"]:
        errors.append(f"{path}: const")
    if "enum" in schema and instance not in schema["enum"]:
        errors.append(f"{path}: enum")
    if "pattern" in schema and isinstance(instance, str):
        if not re.search(schema["pattern"], instance):
            errors.append(f"{path}: pattern")
    if "format" in schema and isinstance(instance, str):
        if schema["format"] == "date-time" and not _is_datetime(instance):
            errors.append(f"{path}: format")
    if "minimum" in schema and isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if instance < schema["minimum"]:
            errors.append(f"{path}: minimum")

    if isinstance(instance, dict):
        for key in schema.get("required", []):
            if key not in instance:
                errors.append(f"{path}/{key}: required")
        properties = schema.get("properties", {})
        for key, value in instance.items():
            if key in properties:
                _validate(value, properties[key], registry, document, f"{path}/{key}", errors)
            elif "additionalProperties" in schema:
                extra = schema["additionalProperties"]
                if extra is False:
                    errors.append(f"{path}/{key}: additionalProperties")
                else:
                    _validate(value, extra, registry, document, f"{path}/{key}", errors)
            if "propertyNames" in schema:
                _validate(key, schema["propertyNames"], registry, document, f"{path}/{key}", errors)
        if "maxProperties" in schema and len(instance) > schema["maxProperties"]:
            errors.append(f"{path}: maxProperties")

    if isinstance(instance, list):
        if "items" in schema:
            for index, item in enumerate(instance):
                _validate(item, schema["items"], registry, document, f"{path}/{index}", errors)
        if "maxItems" in schema and len(instance) > schema["maxItems"]:
            errors.append(f"{path}: maxItems")
        if schema.get("uniqueItems"):
            seen = [canonical_bytes(item) for item in instance]
            if len(set(seen)) != len(seen):
                errors.append(f"{path}: uniqueItems")

    for sub in schema.get("allOf", []):
        _validate(instance, sub, registry, document, path, errors)
    if "not" in schema:
        inner: list[str] = []
        _validate(instance, schema["not"], registry, document, path, inner)
        if not inner:
            errors.append(f"{path}: not")
    if "oneOf" in schema:
        matches = 0
        for sub in schema["oneOf"]:
            inner = []
            _validate(instance, sub, registry, document, path, inner)
            if not inner:
                matches += 1
        if matches != 1:
            errors.append(f"{path}: oneOf")


def schema_errors(instance: Any, registry: SchemaRegistry, document: str) -> list[str]:
    """Validate ``instance`` against the named schema document. Empty list means valid."""
    errors: list[str] = []
    _validate(instance, registry.schemas[document], registry, document, "", errors)
    return sorted(set(errors))


# ------------------------------------------------------------- envelope validator


ENVELOPE_DOCUMENT = "event-envelope.schema.json"  # 1.0.0-pilot, frozen
# Envelope contract versions and the exact document each is validated against
# (compatibility.md, version negotiation: the payload declares its version, the consumer
# selects the document, validation is against pinned bytes). 1.1.0-pilot is the governed
# successor ruled by DEC-005 item 1 (2026-09-05): it adds the ``startup.*`` family and
# nothing else. A version not listed here is rejected, never guessed.
ENVELOPE_DOCUMENTS: Mapping[str, str] = {
    "1.0.0-pilot": ENVELOPE_DOCUMENT,
    "1.1.0-pilot": "event-envelope-1.1.0.schema.json",
}


@dataclass(frozen=True)
class EnvelopeValidator:
    """Payload validator for the store: the payload must be a T-002 envelope whose
    ``event_type`` matches the kernel record's, validated against the pinned schema bytes
    of the contract version the payload declares."""

    registry: SchemaRegistry

    @property
    def schema_sha256(self) -> str:
        """Digest of the 1.0.0-pilot document (kept for consumers that pin one hash)."""
        return self.registry.hashes[ENVELOPE_DOCUMENT]

    @property
    def schema_sha256_by_version(self) -> dict[str, str]:
        return {version: self.registry.hashes[document] for version, document in ENVELOPE_DOCUMENTS.items()}

    def __call__(self, event_type: str, payload: Any) -> list[str]:
        if not isinstance(payload, dict):
            return schema_errors(payload, self.registry, ENVELOPE_DOCUMENT)
        document = ENVELOPE_DOCUMENTS.get(payload.get("schema_version"))
        if document is None:
            return ["/schema_version: unsupported"]
        errors = schema_errors(payload, self.registry, document)
        if payload.get("event_type") != event_type:
            errors.append("/event_type: record-mismatch")
        return errors


def load_envelope_validator(contracts_dir: Path) -> EnvelopeValidator:
    return EnvelopeValidator(SchemaRegistry.from_directory(contracts_dir))
