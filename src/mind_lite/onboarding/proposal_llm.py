import json

ALLOWED_CHANGE_TYPES = {
    "tag_enrichment",
    "link_add",
    "folder_standardization",
}
ALLOWED_RISK_TIERS = {"low", "medium", "high"}


def parse_llm_candidates(raw: str) -> list[dict]:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ValueError("raw must be valid JSON") from error

    if not isinstance(payload, dict):
        raise ValueError("raw must decode to a JSON object")

    proposals = payload.get("proposals")
    if not isinstance(proposals, list):
        raise ValueError('raw must include "proposals" as a list')

    parsed: list[dict] = []
    for index, candidate in enumerate(proposals):
        try:
            parsed.append(_validate_candidate(candidate))
        except ValueError as error:
            raise ValueError(f"proposal[{index}]: {error}") from error
    return parsed


def build_note_prompt(note: dict) -> str:
    tags = note.get("tags", [])
    if isinstance(tags, list):
        rendered_tags = ", ".join(str(tag) for tag in tags)
    elif isinstance(tags, str):
        rendered_tags = tags
    else:
        rendered_tags = "[invalid tags]"

    return (
        f"note_id: {note.get('note_id', '')}\n"
        f"title: {note.get('title', '')}\n"
        f"folder: {note.get('folder', '')}\n"
        f"tags: {rendered_tags}\n"
        f"content_preview: {note.get('content_preview', '')}"
    )


def _validate_candidate(candidate: object) -> dict:
    if not isinstance(candidate, dict):
        raise ValueError("each proposal must be an object")

    note_id = candidate.get("note_id")
    if not isinstance(note_id, str) or not note_id.strip():
        raise ValueError("note_id must be a non-empty string")

    change_type = candidate.get("change_type")
    if change_type not in ALLOWED_CHANGE_TYPES:
        allowed_values = ", ".join(sorted(ALLOWED_CHANGE_TYPES))
        raise ValueError(
            f'change_type is invalid: got {change_type!r}; '
            f"allowed values: {allowed_values}"
        )

    risk_tier = candidate.get("risk_tier")
    if risk_tier not in ALLOWED_RISK_TIERS:
        allowed_values = ", ".join(sorted(ALLOWED_RISK_TIERS))
        raise ValueError(
            f'risk_tier is invalid: got {risk_tier!r}; '
            f"allowed values: {allowed_values}"
        )

    confidence = candidate.get("confidence")
    if not isinstance(confidence, (int, float)) or isinstance(confidence, bool):
        raise ValueError("confidence must be a number")
    if confidence < 0 or confidence > 1:
        raise ValueError("confidence must be in [0, 1]")

    details = candidate.get("details")
    if not isinstance(details, dict):
        raise ValueError("details must be an object")

    return candidate
