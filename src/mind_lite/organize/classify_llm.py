import json

ALLOWED_PARA = {"project", "area", "resource", "archive"}


def build_classify_prompt(note: dict) -> str:
    tags = note.get("tags", [])
    if isinstance(tags, list):
        rendered_tags = ", ".join(str(t) for t in tags)
    elif isinstance(tags, str):
        rendered_tags = tags
    else:
        rendered_tags = ""

    return (
        f"Classify this note into PARA (Projects, Areas, Resources, Archive).\n\n"
        f"title: {note.get('title', '')}\n"
        f"folder: {note.get('folder', '')}\n"
        f"tags: {rendered_tags}\n"
        f"content_preview: {note.get('content_preview', '')[:500]}\n\n"
        f'Respond with JSON: {{"primary": "<category>", "secondary": ["<category>"], "confidence": 0.0-1.0}}\n'
        f"primary must be exactly one of: project, area, resource, archive\n"
        f"secondary can have up to 2 additional categories (not including primary)"
    )


def parse_classify_response(raw: str) -> dict:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ValueError("response must be valid JSON") from error

    if not isinstance(payload, dict):
        raise ValueError("response must be a JSON object")

    primary = payload.get("primary")
    if primary not in ALLOWED_PARA:
        allowed = ", ".join(sorted(ALLOWED_PARA))
        raise ValueError(f"primary must be one of: {allowed}")

    secondary = payload.get("secondary", [])
    if not isinstance(secondary, list):
        raise ValueError("secondary must be a list")
    if primary in secondary:
        raise ValueError("secondary cannot repeat primary")
    if len(secondary) > 2:
        raise ValueError("secondary can have at most 2 entries")

    confidence = payload.get("confidence", 0.5)
    if not isinstance(confidence, (int, float)):
        confidence = 0.5
    confidence = max(0.0, min(1.0, float(confidence)))

    return {
        "primary": primary,
        "secondary": [s for s in secondary if s in ALLOWED_PARA and s != primary],
        "confidence": confidence,
    }


LMSTUDIO_BASE_URL = "http://localhost:1234"


def _call_llm(prompt: str) -> str:
    import httpx

    try:
        response = httpx.post(
            f"{LMSTUDIO_BASE_URL}/v1/chat/completions",
            json={
                "model": "local-model",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "max_tokens": 200,
            },
            timeout=10.0,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception:
        return '{"primary": "resource", "secondary": [], "confidence": 0.5}'


def classify_note(note: dict) -> dict:
    prompt = build_classify_prompt(note)
    raw = _call_llm(prompt)
    parsed = parse_classify_response(raw)
    parsed["note_id"] = note.get("note_id", "")
    return parsed
