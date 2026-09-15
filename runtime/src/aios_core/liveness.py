"""One liveness and coordination interpretation (T-004).

Pure functions over the current ``coord/sessions/*.md`` shape. Every consumer verdict
about a session (scanner, spawn pre-flight, startup intake, shutdown orchestrator,
welfare hook) must come from :func:`interpret`; slot counts from :func:`slot_report`;
claim overlaps from :func:`claim_conflicts`; shutdown blocking from
:func:`shutdown_state`. Nothing here reads a clock or touches the filesystem: callers
pass ``now`` and the file text.

Canonical rules (policy ``liveness-policy-v1``, from coord/SPEC.md v0.5 and audit
F-02/F-08/F-09/F-10):

* ``status:`` is declared intent, never liveness evidence. ``status: done`` is the only
  terminal claim. A turn-level stop is never termination (F-02).
* Heartbeat age decides liveness. Missing, malformed, or incomparable heartbeats are not
  evidence of life and read as ``stale``.
* A heartbeat more than ``future_skew_minutes`` ahead of the clock is a fault; policy v1
  fails closed and reads it as ``stale`` (``future_verdict``). A heartbeat ahead of the
  clock but inside the tolerance is live with a warning.
* Only frontmatter counts. Body text can never shadow a key.
* Budgets come from one source, the ``budgets:`` line of SPEC.md. When it is absent the
  budget is unknown, never a hard-coded fallback.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, Mapping, Sequence

POLICY_VERSION = "liveness-policy-v1"

VERDICT_LIVE = "live"
VERDICT_STALE = "stale"
VERDICT_DONE = "done"

INTENT_VOCABULARY = frozenset({"active", "paused", "done"})
INTENT_MISSING = "missing"

_FRONTMATTER_DELIM = re.compile(r"^---\s*$")
_KEY_VALUE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.*?)\s*$")
_LIST_ITEM = re.compile(r"^\s+-\s*(.*?)\s*$")
_INLINE_COMMENT = re.compile(r"\s+#.*$")
_BUDGET_LINE = re.compile(r"^\s*budgets\s*:\s*(.*?)\s*$", re.MULTILINE)
_BUDGET_ITEM = re.compile(r"([A-Za-z0-9-]+)\s*=\s*(\d+)")


class LivenessError(ValueError):
    """Raised for caller errors (never for malformed session files, which get verdicts)."""


@dataclass(frozen=True)
class LivenessPolicy:
    version: str = POLICY_VERSION
    stale_minutes: int = 60
    future_skew_minutes: int = 5
    future_verdict: str = VERDICT_STALE

    def __post_init__(self) -> None:
        if self.stale_minutes <= 0 or self.future_skew_minutes < 0:
            raise LivenessError("policy thresholds must be positive")
        if self.future_verdict not in (VERDICT_STALE, VERDICT_LIVE):
            raise LivenessError("future_verdict must be 'stale' or 'live'")


DEFAULT_POLICY = LivenessPolicy()


@dataclass(frozen=True)
class SessionFacts:
    """What the file says, before any judgment."""

    source: str
    frontmatter_present: bool
    fields: Mapping[str, str]
    claims: tuple[str, ...]
    claims_declared: bool

    def get(self, key: str) -> str | None:
        return self.fields.get(key)


@dataclass(frozen=True)
class Verdict:
    source: str
    id: str
    harness: str | None
    verdict: str
    terminal: bool
    intent: str
    heartbeat_age_seconds: int | None
    reasons: tuple[str, ...]
    warnings: tuple[str, ...]
    claims: tuple[str, ...]
    policy_version: str = POLICY_VERSION

    @property
    def live(self) -> bool:
        return self.verdict == VERDICT_LIVE

    def as_dict(self) -> dict:
        return {
            "source": self.source,
            "id": self.id,
            "harness": self.harness,
            "verdict": self.verdict,
            "terminal": self.terminal,
            "intent": self.intent,
            "heartbeat_age_seconds": self.heartbeat_age_seconds,
            "reasons": list(self.reasons),
            "warnings": list(self.warnings),
            "claims": list(self.claims),
            "policy_version": self.policy_version,
        }


# --------------------------------------------------------------------------- parsing


def _strip_comment(value: str) -> str:
    return _INLINE_COMMENT.sub("", value).strip()


def parse_session_frontmatter(text: str, source: str = "<memory>") -> SessionFacts:
    """Parse the leading ``---`` block of a session file.

    Scalar keys keep the last occurrence inside the block; ``claims:`` accepts the
    indented ``- item`` list form or an inline ``[]``. Anything after the closing
    delimiter is body and is ignored.
    """
    lines = text.splitlines()
    if not lines or not _FRONTMATTER_DELIM.match(lines[0]):
        return SessionFacts(source, False, {}, (), False)

    fields: dict[str, str] = {}
    claims: list[str] = []
    claims_declared = False
    in_claims = False
    closed = False
    for line in lines[1:]:
        if _FRONTMATTER_DELIM.match(line):
            closed = True
            break
        if in_claims:
            item = _LIST_ITEM.match(line)
            if item:
                value = _strip_comment(item.group(1))
                if value:
                    claims.append(value)
                continue
            in_claims = False
        match = _KEY_VALUE.match(line)
        if not match or line[:1].isspace():
            continue
        key, raw = match.group(1), _strip_comment(match.group(2))
        if key == "claims":
            claims_declared = True
            in_claims = True
            inline = raw.strip()
            if inline.startswith("[") and inline.endswith("]"):
                claims.extend(
                    part.strip().strip("'\"")
                    for part in inline[1:-1].split(",")
                    if part.strip()
                )
                in_claims = False
            continue
        fields[key] = raw
    if not closed:
        # An unterminated block is not frontmatter: nothing in it can be trusted.
        return SessionFacts(source, False, {}, (), False)
    return SessionFacts(source, True, fields, tuple(claims), claims_declared)


def parse_timestamp(raw: str | None) -> datetime | None:
    """ISO 8601 via ``datetime.fromisoformat``; ``None`` for anything else."""
    if raw is None:
        return None
    value = raw.strip()
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _age_seconds(now: datetime, then: datetime) -> int | None:
    """Signed age in whole seconds, or ``None`` when the two are not comparable."""
    if (now.tzinfo is None) != (then.tzinfo is None):
        return None
    if now.tzinfo is not None:
        now = now.astimezone(timezone.utc)
        then = then.astimezone(timezone.utc)
    return int((now - then).total_seconds())


# ----------------------------------------------------------------------- interpret


def interpret(
    facts: SessionFacts, now: datetime, policy: LivenessPolicy = DEFAULT_POLICY
) -> Verdict:
    """The single heartbeat-to-liveness rule. Deterministic in ``(facts, now, policy)``."""
    if not isinstance(now, datetime):
        raise LivenessError("now must be a datetime")

    warnings: list[str] = []
    reasons: list[str] = []

    raw_id = facts.get("id")
    if not raw_id:
        warnings.append("id-missing")
        fallback = facts.source.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
        raw_id = fallback[:-3] if fallback.endswith(".md") else fallback
    harness = facts.get("harness") or None
    if harness is None:
        warnings.append("harness-missing")

    raw_status = facts.get("status")
    if raw_status is None or raw_status == "":
        intent = INTENT_MISSING
        warnings.append("status-missing")
    else:
        intent = raw_status
        if raw_status not in INTENT_VOCABULARY:
            warnings.append("status-outside-vocabulary")

    heartbeat_raw = facts.get("heartbeat")
    heartbeat = parse_timestamp(heartbeat_raw)
    age: int | None = None
    heartbeat_reason: str
    if not facts.frontmatter_present:
        heartbeat_reason = "frontmatter-missing"
    elif heartbeat_raw is None or heartbeat_raw == "":
        heartbeat_reason = "heartbeat-missing"
    elif heartbeat is None:
        heartbeat_reason = "heartbeat-malformed"
    else:
        age = _age_seconds(now, heartbeat)
        if age is None:
            heartbeat_reason = "heartbeat-timezone-mismatch"
        elif age < -policy.future_skew_minutes * 60:
            heartbeat_reason = "heartbeat-future"
        elif age > policy.stale_minutes * 60:
            heartbeat_reason = "heartbeat-stale"
        else:
            heartbeat_reason = "heartbeat-fresh"
            if age < 0:
                warnings.append("heartbeat-ahead-of-clock")

    started = parse_timestamp(facts.get("started"))
    if facts.get("started") and started is None:
        warnings.append("started-malformed")
    if started is not None and heartbeat is not None:
        gap = _age_seconds(started, heartbeat)
        if gap is not None and gap > 0:
            warnings.append("started-after-heartbeat")

    if intent == "done":
        verdict = VERDICT_DONE
        reasons.append("status-done")
        if heartbeat_reason not in ("heartbeat-fresh",):
            warnings.append(heartbeat_reason)
    else:
        reasons.append(heartbeat_reason)
        if heartbeat_reason == "heartbeat-fresh":
            verdict = VERDICT_LIVE
        elif heartbeat_reason == "heartbeat-future":
            verdict = policy.future_verdict
        else:
            verdict = VERDICT_STALE

    return Verdict(
        source=facts.source,
        id=raw_id,
        harness=harness,
        verdict=verdict,
        terminal=verdict == VERDICT_DONE,
        intent=intent,
        heartbeat_age_seconds=age,
        reasons=tuple(reasons),
        warnings=tuple(warnings),
        claims=facts.claims,
        policy_version=policy.version,
    )


def interpret_text(
    text: str, now: datetime, source: str = "<memory>", policy: LivenessPolicy = DEFAULT_POLICY
) -> Verdict:
    return interpret(parse_session_frontmatter(text, source), now, policy)


# --------------------------------------------------------------------------- budgets


@dataclass(frozen=True)
class BudgetSource:
    budgets: Mapping[str, int]
    source: str  # "spec" | "missing"


def parse_budgets(spec_text: str) -> BudgetSource:
    """The one budget source: the first ``budgets:`` line of SPEC.md.

    No fallback numbers. A missing line yields an empty mapping and ``source="missing"``
    so that consumers report the budget as unknown instead of inventing one (F-10).
    """
    match = _BUDGET_LINE.search(spec_text)
    if not match:
        return BudgetSource({}, "missing")
    budgets = {name: int(count) for name, count in _BUDGET_ITEM.findall(match.group(1))}
    if not budgets:
        return BudgetSource({}, "missing")
    return BudgetSource(budgets, "spec")


@dataclass(frozen=True)
class SlotRow:
    harness: str
    live: int
    budget: int | None
    free: int | None
    over_budget: bool | None
    naive_active: int

    def as_dict(self) -> dict:
        return {
            "harness": self.harness,
            "live": self.live,
            "budget": self.budget,
            "free": self.free,
            "over_budget": self.over_budget,
            "naive_active": self.naive_active,
        }


UNKNOWN_HARNESS = "unknown"


def slot_report(verdicts: Iterable[Verdict], budgets: BudgetSource) -> dict[str, SlotRow]:
    """Live rows per harness against the declared budgets.

    ``naive_active`` is what a status-only count would say; it is reported so the gap
    is visible and must never drive a decision (F-09).
    """
    rows = list(verdicts)
    harnesses = sorted(set(budgets.budgets) | {v.harness or UNKNOWN_HARNESS for v in rows})
    report: dict[str, SlotRow] = {}
    for harness in harnesses:
        mine = [v for v in rows if (v.harness or UNKNOWN_HARNESS) == harness]
        live = sum(1 for v in mine if v.live)
        naive = sum(1 for v in mine if v.intent == "active")
        budget = budgets.budgets.get(harness)
        if budget is None:
            report[harness] = SlotRow(harness, live, None, None, None, naive)
        else:
            report[harness] = SlotRow(
                harness, live, budget, max(0, budget - live), live > budget, naive
            )
    return report


# ---------------------------------------------------------------------------- claims


@dataclass(frozen=True)
class ClaimConflict:
    kind: str  # "equal" | "prefix" | "section"
    left_id: str
    left_claim: str
    right_id: str
    right_claim: str

    def as_dict(self) -> dict:
        return {
            "kind": self.kind,
            "left": [self.left_id, self.left_claim],
            "right": [self.right_id, self.right_claim],
        }


def normalize_claim(claim: str) -> tuple[str, str | None]:
    """Split ``path §section`` into a normalized path and optional section.

    Paths are compared with forward slashes and without a trailing slash. The section
    vocabulary belongs to the project; it is compared as an exact string.
    """
    path, section = claim, None
    if "§" in claim:
        path, section = claim.split("§", 1)
        section = section.strip() or None
    path = path.strip().replace("\\", "/").rstrip("/")
    return path, section


def _claims_overlap(a: str, b: str) -> str | None:
    pa, sa = normalize_claim(a)
    pb, sb = normalize_claim(b)
    if pa == pb:
        if sa == sb:
            return "equal"
        if sa is None or sb is None:
            return "section"
        return None
    if pa and pb.startswith(pa + "/"):
        return "prefix"
    if pb and pa.startswith(pb + "/"):
        return "prefix"
    return None


def claim_conflicts(verdicts: Iterable[Verdict]) -> list[ClaimConflict]:
    """Mechanical overlaps between the claims of *live* sessions only.

    Stale and done sessions hold nothing. A session never conflicts with itself.
    """
    live = [v for v in verdicts if v.live]
    found: list[ClaimConflict] = []
    for i, left in enumerate(live):
        for right in live[i + 1 :]:
            for lc in left.claims:
                for rc in right.claims:
                    kind = _claims_overlap(lc, rc)
                    if kind:
                        found.append(ClaimConflict(kind, left.id, lc, right.id, rc))
    return found


# -------------------------------------------------------------------------- shutdown


@dataclass(frozen=True)
class ShutdownState:
    requested: bool
    blocking: tuple[str, ...]

    def as_dict(self) -> dict:
        return {"requested": self.requested, "blocking": list(self.blocking)}


def shutdown_state(flag_present: bool, verdicts: Iterable[Verdict]) -> ShutdownState:
    """Shutdown blocks on live sessions only; stale and done never block."""
    if not flag_present:
        return ShutdownState(False, ())
    blocking = tuple(sorted(v.id for v in verdicts if v.live))
    return ShutdownState(True, blocking)


# --------------------------------------------------------------------------- helpers


def interpret_many(
    sessions: Sequence[SessionFacts], now: datetime, policy: LivenessPolicy = DEFAULT_POLICY
) -> list[Verdict]:
    return [interpret(facts, now, policy) for facts in sessions]
