from enum import Enum


class RunState(str, Enum):
    QUEUED = "queued"
    ANALYZING = "analyzing"
    READY_SAFE_AUTO = "ready_safe_auto"
    AWAITING_REVIEW = "awaiting_review"
    APPROVED = "approved"
    APPLIED = "applied"
    VERIFIED = "verified"
    AUTO_SAFE_MODE = "auto_safe_mode"
    ROLLED_BACK = "rolled_back"
    FAILED_NEEDS_ATTENTION = "failed_needs_attention"


_ALLOWED_FORWARD_TRANSITIONS: dict[RunState, set[RunState]] = {
    RunState.QUEUED: {RunState.ANALYZING},
    RunState.ANALYZING: {RunState.READY_SAFE_AUTO},
    RunState.READY_SAFE_AUTO: {RunState.AWAITING_REVIEW},
    RunState.AWAITING_REVIEW: {RunState.APPROVED},
    RunState.APPROVED: {RunState.APPLIED},
    RunState.APPLIED: {RunState.VERIFIED},
    RunState.VERIFIED: set(),
}

_GLOBAL_FAILURE_STATES = {
    RunState.AUTO_SAFE_MODE,
    RunState.ROLLED_BACK,
    RunState.FAILED_NEEDS_ATTENTION,
}


def can_transition(current: RunState, target: RunState) -> bool:
    if target in _GLOBAL_FAILURE_STATES:
        return True

    if current in _GLOBAL_FAILURE_STATES:
        return False

    return target in _ALLOWED_FORWARD_TRANSITIONS.get(current, set())


def validate_transition(current: RunState, target: RunState) -> bool:
    return can_transition(current, target)
