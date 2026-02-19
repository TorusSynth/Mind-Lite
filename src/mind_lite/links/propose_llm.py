import json
from collections import Counter

ALLOWED_REASONS = {"shared_project_context", "structural_overlap", "semantic_similarity"}
LMSTUDIO_BASE_URL = "http://localhost:1234"
MAX_SUGGESTIONS = 10
MAX_TARGET_SATURATION = 3
MIN_CONFIDENCE = 0.50


def build_link_prompt(source: dict, candidates: list[dict]) -> str:
    def render_note(n: dict) -> str:
        tags = n.get("tags", [])
        tag_str = ", ".join(str(t) for t in tags) if isinstance(tags, list) else str(tags)
        return f"- id: {n.get('note_id')}\n  title: {n.get('title')}\n  tags: {tag_str}"

    candidates_block = "\n".join(render_note(c) for c in candidates)
    return (
        f"Score link suggestions from source note to candidates.\n\n"
        f"SOURCE:\n{render_note(source)}\n\n"
        f"CANDIDATES:\n{candidates_block}\n\n"
        f'{{"suggestions": [{{"target_note_id": "<id>", "confidence": 0.0-1.0, "reason": "<reason>"}}]}}\n'
        f"reason must be one of: shared_project_context, structural_overlap, semantic_similarity\n"
        f"Only include suggestions with confidence >= 0.50"
    )


def parse_link_response(raw: str) -> list[dict]:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return []

    if not isinstance(payload, dict):
        return []

    suggestions = payload.get("suggestions", [])
    if not isinstance(suggestions, list):
        return []

    parsed = []
    for s in suggestions:
        if not isinstance(s, dict):
            continue
        target = s.get("target_note_id")
        if not isinstance(target, str) or not target.strip():
            continue
        reason = s.get("reason")
        if reason not in ALLOWED_REASONS:
            raise ValueError(f"Invalid reason: {reason}. Must be one of: shared_project_context, structural_overlap, semantic_similarity")
        confidence = s.get("confidence", 0.5)
        if not isinstance(confidence, (int, float)):
            confidence = 0.5
        confidence = max(0.0, min(1.0, float(confidence)))
        parsed.append({
            "target_note_id": target.strip(),
            "confidence": confidence,
            "reason": reason,
        })
    return parsed


def apply_spam_controls(
    suggestions: list[dict],
    existing_links: set[str],
    batch_targets: Counter | dict,
) -> list[dict]:
    if not isinstance(batch_targets, dict):
        batch_targets = {}
    filtered = []
    for s in suggestions:
        if s["confidence"] < MIN_CONFIDENCE:
            continue
        target = s["target_note_id"]
        if target in existing_links:
            continue
        if batch_targets.get(target, 0) >= MAX_TARGET_SATURATION:
            continue
        batch_targets[target] = batch_targets.get(target, 0) + 1
        filtered.append(s)
    return sorted(filtered, key=lambda x: x["confidence"], reverse=True)[:MAX_SUGGESTIONS]


def _call_llm(prompt: str) -> str:
    import httpx

    try:
        response = httpx.post(
            f"{LMSTUDIO_BASE_URL}/v1/chat/completions",
            json={
                "model": "local-model",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "max_tokens": 500,
            },
            timeout=15.0,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception:
        return '{"suggestions": []}'


def score_links(source: dict, candidates: list[dict]) -> list[dict]:
    prompt = build_link_prompt(source, candidates)
    raw = _call_llm(prompt)
    return parse_link_response(raw)
