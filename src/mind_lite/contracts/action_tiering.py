from enum import Enum


class ActionMode(str, Enum):
    AUTO = "auto"
    SUGGEST = "suggest"
    MANUAL = "manual"


def decide_action_mode(risk_tier: str, confidence: float) -> ActionMode:
    if confidence < 0.0 or confidence > 1.0:
        raise ValueError("confidence must be between 0.0 and 1.0")

    if risk_tier == "high":
        return ActionMode.MANUAL

    if risk_tier == "medium":
        return ActionMode.SUGGEST if confidence >= 0.70 else ActionMode.MANUAL

    if risk_tier == "low":
        return ActionMode.AUTO if confidence >= 0.80 else ActionMode.MANUAL

    raise ValueError(f"unknown risk tier: {risk_tier}")
