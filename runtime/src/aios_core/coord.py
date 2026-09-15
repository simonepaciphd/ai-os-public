"""Read-only reader for a ``coord/`` tree (T-004).

Turns the files into :class:`~aios_core.liveness.SessionFacts`, the SPEC budget line,
the control flag, and closeout-note frontmatter. It never writes. Every judgment is
delegated to :mod:`aios_core.liveness`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Sequence

from .liveness import (
    DEFAULT_POLICY,
    BudgetSource,
    ClaimConflict,
    LivenessPolicy,
    SessionFacts,
    ShutdownState,
    SlotRow,
    Verdict,
    claim_conflicts,
    interpret,
    parse_budgets,
    parse_session_frontmatter,
    shutdown_state,
    slot_report,
)

SHUTDOWN_FLAG = "SHUTDOWN-REQUESTED.md"

CLOSEOUT_REQUIRED = (
    "from",
    "to",
    "sent",
    "re",
    "type",
    "project",
    "priority",
    "relaunch",
    "resume",
    "worktree",
    "branch",
    "decision_points",
)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def read_sessions(coord_root: Path) -> list[SessionFacts]:
    """Open-registry session files (``sessions/*.md``), sorted by name. ``_closed`` is skipped."""
    sessions_dir = coord_root / "sessions"
    if not sessions_dir.is_dir():
        return []
    return [
        parse_session_frontmatter(read_text(path), source=path.name)
        for path in sorted(sessions_dir.glob("*.md"))
        if path.is_file()
    ]


def read_budgets(coord_root: Path) -> BudgetSource:
    spec = coord_root / "SPEC.md"
    if not spec.is_file():
        return BudgetSource({}, "missing")
    return parse_budgets(read_text(spec))


def control_flag_present(coord_root: Path) -> bool:
    return (coord_root / "control" / SHUTDOWN_FLAG).is_file()


# ------------------------------------------------------------------- closeout notes


@dataclass(frozen=True)
class CloseoutFacts:
    source: str
    is_closeout: bool
    valid: bool
    missing: tuple[str, ...]
    fields: dict
    decision_points: int | None
    actionable: bool
    relaunch: str | None

    def as_dict(self) -> dict:
        return {
            "source": self.source,
            "is_closeout": self.is_closeout,
            "valid": self.valid,
            "missing": list(self.missing),
            "decision_points": self.decision_points,
            "actionable": self.actionable,
            "relaunch": self.relaunch,
        }


def parse_closeout_note(text: str, source: str = "<memory>") -> CloseoutFacts:
    """Interpret mailbox frontmatter against the SPEC v0.5 closeout schema.

    ``actionable`` is true when the note carries decisions for Operator, or when the
    decision count cannot be read (fail toward visibility, A-008). Body text is ignored.
    """
    facts = parse_session_frontmatter(text, source)
    fields = dict(facts.fields)
    is_closeout = fields.get("type") == "closeout"
    missing = tuple(key for key in CLOSEOUT_REQUIRED if not fields.get(key))
    raw_points = fields.get("decision_points")
    decision_points: int | None
    try:
        decision_points = int(raw_points) if raw_points is not None else None
    except ValueError:
        decision_points = None
    if decision_points is not None and decision_points < 0:
        decision_points = None
    valid = is_closeout and not missing and decision_points is not None
    actionable = is_closeout and (decision_points is None or decision_points > 0)
    return CloseoutFacts(
        source=source,
        is_closeout=is_closeout,
        valid=valid,
        missing=missing,
        fields=fields,
        decision_points=decision_points,
        actionable=actionable,
        relaunch=fields.get("relaunch") if is_closeout else None,
    )


def read_closeout_notes(coord_root: Path, recipient: str = "operator") -> list[CloseoutFacts]:
    """Unread notes in ``mailbox/<recipient>/`` (the ``_read`` folder is skipped)."""
    box = coord_root / "mailbox" / recipient
    if not box.is_dir():
        return []
    return [
        parse_closeout_note(read_text(path), source=path.name)
        for path in sorted(box.glob("*.md"))
        if path.is_file()
    ]


# -------------------------------------------------------------------------- snapshot


@dataclass(frozen=True)
class CoordSnapshot:
    scanned_at: datetime
    policy: LivenessPolicy
    budgets: BudgetSource
    verdicts: tuple[Verdict, ...]
    slots: dict[str, SlotRow]
    conflicts: tuple[ClaimConflict, ...]
    shutdown: ShutdownState
    closeouts: tuple[CloseoutFacts, ...]

    def as_dict(self) -> dict:
        return {
            "scanned_at": self.scanned_at.isoformat(timespec="minutes"),
            "policy_version": self.policy.version,
            "stale_minutes": self.policy.stale_minutes,
            "future_skew_minutes": self.policy.future_skew_minutes,
            "future_verdict": self.policy.future_verdict,
            "budget_source": self.budgets.source,
            "budgets": dict(self.budgets.budgets),
            "sessions": [v.as_dict() for v in self.verdicts],
            "slots": {k: v.as_dict() for k, v in self.slots.items()},
            "claim_conflicts": [c.as_dict() for c in self.conflicts],
            "shutdown": self.shutdown.as_dict(),
            "closeouts": [c.as_dict() for c in self.closeouts],
        }


def snapshot(
    coord_root: Path,
    now: datetime,
    policy: LivenessPolicy = DEFAULT_POLICY,
    sessions: Sequence[SessionFacts] | None = None,
) -> CoordSnapshot:
    """Everything a control consumer needs, computed once from one interpretation."""
    facts = list(sessions) if sessions is not None else read_sessions(coord_root)
    verdicts = tuple(interpret(f, now, policy) for f in facts)
    budgets = read_budgets(coord_root)
    return CoordSnapshot(
        scanned_at=now,
        policy=policy,
        budgets=budgets,
        verdicts=verdicts,
        slots=slot_report(verdicts, budgets),
        conflicts=tuple(claim_conflicts(verdicts)),
        shutdown=shutdown_state(control_flag_present(coord_root), verdicts),
        closeouts=tuple(read_closeout_notes(coord_root)),
    )
