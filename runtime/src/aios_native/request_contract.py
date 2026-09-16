"""Pure semantic request contract: no filesystem, identity lookup or cleanup."""
from __future__ import annotations

import re


class Refused(RuntimeError):
    pass


class RequestInvalid(Refused):
    """Only code-owned field names and classifications may reach diagnostics."""
    def __init__(self, classification, field=None):
        self.classification = classification
        self.field = field
        super().__init__(classification + (":" + field if field else ""))


VERSION = "native-semantic-public-1"
# JSON Schema uses regex search, where `$` may match before a final newline.
# The negative lookahead below requires the actual end in both regex engines.
# JSON can decode an escaped unpaired surrogate into a Python string, but it
# cannot be published as UTF-8. Exclude that range in the shared schema/runtime
# constraint; actual supplementary code points remain valid.
SCALAR = {"type": "string", "pattern": r"^[^\r\n\u0000\ud800-\udfff]*(?![\s\S])"}
NONEMPTY = {**SCALAR, "minLength": 1}
# Bookkeeping emits key + ':prepared' (9) and key + ':committed' (10).
# The unchanged kernel ID_RE permits 256 ASCII characters, starting with an
# alphanumeric. Reserve the longer suffix; tests compare BOTH event identities.
JOURNAL_KEY = {"type": "string", "minLength": 1, "maxLength": 256 - 10,
    "pattern": r"^[A-Za-z0-9][A-Za-z0-9._~:/@+-]*(?![\s\S])"}
ARTIFACT = {"type": "object", "additionalProperties": False, "required": ["path"],
    "properties": {"path": NONEMPTY, "asset_type": SCALAR, "notes": SCALAR,
        "creator": {"enum": ["agent", "mixed"]},
        "verification": {"enum": ["not-verified", "partially-verified"]},
        "text": {"type": "boolean"}}}
PROPERTIES = {name: SCALAR for name in (
    "model", "task", "summary", "input_summary", "resume", "branch", "initiator", "task_difficulty")}
PROPERTIES.update({
    "operation": NONEMPTY, "key": NONEMPTY, "project": NONEMPTY, "native_id": NONEMPTY,
    "activation": {"type": "string", "pattern": r"^[a-zA-Z0-9-]{1,120}(?![\s\S])"},
    "worktree": NONEMPTY,
    "tab": {"type": "string", "pattern": r"^[A-Z0-9]+ [A-Z0-9]+(?![\s\S])", "maxLength": 10},
    "harness": {"enum": ["codex-cli", "claude-code"]},
    "model_source": {"enum": ["claude-statusline"]},
    "priority": {"enum": ["low", "medium", "high"]},
    "relaunch": {"enum": ["yes", "no", "operator-decides"]},
    "claims": {"type": "array", "items": NONEMPTY},
    "decisions": {"type": "array", "items": SCALAR},
    "artifacts": {"type": "array", "items": ARTIFACT},
})
SEMANTIC = {"claims", "task", "summary", "input_summary", "decisions", "artifacts",
            "priority", "relaunch", "resume", "worktree", "branch", "initiator", "task_difficulty"}
REQUIRED = {
    "start": {"operation", "key", "project", "native_id", "harness"},
    "activate": {"operation", "key", "project", "native_id", "harness"},
    "checkpoint": {"operation", "key", "activation"},
    "resume": {"operation", "key", "activation"},
    "close": {"operation", "key", "activation"},
    "reconcile": {"operation", "key"},
}
ALLOWED = {op: required | SEMANTIC for op, required in REQUIRED.items()}
for op in ("start", "activate"):
    ALLOWED[op] |= {"tab", "model"}
ALLOWED["checkpoint"] |= {"model", "model_source"}
ALLOWED["reconcile"] = REQUIRED["reconcile"]

# Existing-project registration shares the approved native entrypoint but has
# its own preflight/apply lifecycle. It never changes an activation's workspace.
PROPERTIES.update({
    "root": NONEMPTY, "workspace": NONEMPTY, "name": NONEMPTY,
    "category": NONEMPTY, "subtype": NONEMPTY,
    "phase": {"enum": ["preflight", "apply"]},
    "preflight": {"type":"string", "pattern":r"^[0-9a-f]{64}(?![\s\S])"},
    "source": {"type":"object", "required":["task","date","harness","model"],
        "additionalProperties":False, "properties":{k:NONEMPTY for k in ("task","date","harness","model")}},
    "delayed_artifacts": {"type":"array", "items":{**ARTIFACT,
        "required":["path","sha256"], "properties":{**ARTIFACT["properties"],
        "sha256":{"type":"string", "pattern":r"^[0-9a-f]{64}(?![\s\S])"}}}},
})
REQUIRED["register-project"] = {"operation","key","phase","root","workspace","native_id","harness"}
ALLOWED["register-project"] = REQUIRED["register-project"] | {
    "project","name","category","subtype","preflight","delayed_artifacts","source","tab","model"}


def field_spec(operation, name):
    # Reconcile requires a scalar key but never journals or replay-caches it.
    return JOURNAL_KEY if name == "key" and operation != "reconcile" else PROPERTIES[name]


def schema():
    branches = []
    for op in REQUIRED:
        branch = {"type": "object", "additionalProperties": False,
            "required": sorted(REQUIRED[op]),
            "properties": {k: field_spec(op, k) for k in sorted(ALLOWED[op])}}
        branch["properties"]["operation"] = {"const": op}
        if op == "checkpoint":
            branch["dependentRequired"] = {"model_source": ["model"], "model": ["model_source"]}
        if op == "register-project":
            branch["dependentRequired"] = {"delayed_artifacts":["source"], "source":["delayed_artifacts"]}
            branch["allOf"] = [{"if":{"properties":{"phase":{"const":"apply"}}}, "then":{"required":["preflight"]}}]
            branch["properties"]["delayed_artifacts"] = {**PROPERTIES["delayed_artifacts"], "minItems":1}
        branches.append(branch)
    return {"$schema": "https://json-schema.org/draft/2020-12/schema", "title": VERSION, "oneOf": branches}


def _value(value, spec, field):
    kind = spec.get("type")
    if "enum" in spec and (not isinstance(value, str) or value not in spec["enum"]):
        raise RequestInvalid("invalid-field", field)
    if kind == "string":
        if not isinstance(value, str) or len(value) < spec.get("minLength", 0) or (
                "maxLength" in spec and len(value) > spec["maxLength"]) or (
                "pattern" in spec and re.fullmatch(spec["pattern"], value) is None):
            raise RequestInvalid("invalid-field", field)
    elif kind == "boolean" and type(value) is not bool:
        raise RequestInvalid("invalid-field", field)
    elif kind == "array":
        if not isinstance(value, list):
            raise RequestInvalid("invalid-field", field)
        for item in value:
            _value(item, spec["items"], field + "[]")
    elif kind == "object":
        if not isinstance(value, dict):
            raise RequestInvalid("invalid-field", field)
        if set(value) - set(spec["properties"]):
            raise RequestInvalid("unknown-artifact-field")
        for name in spec.get("required", []):
            if name not in value:
                raise RequestInvalid("missing-field", field + "." + name)
        for name, item in value.items():
            _value(item, spec["properties"][name], field + "." + name)


def validate_request(request):
    if not isinstance(request, dict):
        raise RequestInvalid("invalid-request-object")
    if "operation" not in request:
        raise RequestInvalid("missing-field", "operation")
    op = request["operation"]
    if not isinstance(op, str):
        raise RequestInvalid("invalid-field", "operation")
    if op not in REQUIRED:
        raise RequestInvalid("unknown-operation")
    if set(request) - ALLOWED[op]:
        raise RequestInvalid("unknown-request-field")
    for name in sorted(REQUIRED[op]):
        if name not in request:
            raise RequestInvalid("missing-field", name)
    for name, value in request.items():
        _value(value, field_spec(op, name), name)
    if op == "checkpoint":
        for left, right in (("model_source", "model"), ("model", "model_source")):
            if left in request and right not in request:
                raise RequestInvalid("missing-field", right)
    if op == "register-project":
        if request["phase"] == "apply" and "preflight" not in request:
            raise RequestInvalid("missing-field", "preflight")
        if bool(request.get("delayed_artifacts")) != ("source" in request):
            raise RequestInvalid("invalid-field", "source")
    return request


def examples():
    admission = {"project": "sample", "native_id": "YOUR_CURRENT_NATIVE_ID", "harness": "codex-cli",
                 "model": "fixture", "tab": "TEST WORK", "claims": [], "task": "Inspect selected work"}
    result = {op: {"operation": op, "key": "UNIQUE_" + op.upper() + "_KEY",
                  **(admission if op in {"start", "activate"} else
                     {} if op == "reconcile" else {"activation": "CURRENT-ACTIVATION-FROM-FRESH-RECEIPT"}),
                  **({"summary": "Verified local work", "input_summary": "Requested fixture work",
                      "decisions": [], "relaunch": "no"} if op == "close" else {})}
            for op in REQUIRED if op != "register-project"}
    result["register-project"] = {"operation":"register-project", "key":"YOUR_UNIQUE_REGISTRATION_KEY",
        "phase":"preflight", "root":"ABSOLUTE_EXISTING_PROJECT_PATH", "workspace":"ACTUAL_CONVERSATION_CWD",
        "native_id":"YOUR_CURRENT_NATIVE_ID", "harness":"codex-cli"}
    return result
