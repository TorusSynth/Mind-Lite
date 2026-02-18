from dataclasses import dataclass


@dataclass(frozen=True)
class RoutingInput:
    local_confidence: float
    local_timed_out: bool
    grounding_failed: bool
    cloud_allowed: bool = True


@dataclass(frozen=True)
class RoutingDecision:
    provider: str
    fallback_used: bool
    reason: str


def select_provider(payload: RoutingInput) -> RoutingDecision:
    if payload.local_timed_out:
        if payload.cloud_allowed:
            return RoutingDecision(provider="openai", fallback_used=True, reason="timeout")
        return RoutingDecision(provider="local", fallback_used=False, reason="cloud_blocked")

    if payload.grounding_failed:
        if payload.cloud_allowed:
            return RoutingDecision(provider="openai", fallback_used=True, reason="grounding_failure")
        return RoutingDecision(provider="local", fallback_used=False, reason="cloud_blocked")

    if payload.local_confidence < 0.70:
        if payload.cloud_allowed:
            return RoutingDecision(provider="openai", fallback_used=True, reason="low_confidence")
        return RoutingDecision(provider="local", fallback_used=False, reason="cloud_blocked")

    return RoutingDecision(provider="local", fallback_used=False, reason="local_success")
