def build_ask_prompt(query: str, citations: list[dict]) -> str:
    context_parts = []
    for i, citation in enumerate(citations[:5], 1):
        note_id = citation.get("note_id", "unknown")
        excerpt = citation.get("excerpt", "")
        context_parts.append(f"[{i}] {note_id}\n{excerpt}")
    
    context = "\n\n".join(context_parts) if context_parts else "No relevant notes found."
    
    return f"""You are a helpful assistant answering questions about the user's notes.

Use ONLY the provided context to answer. If the context doesn't contain relevant information, say so clearly.

CONTEXT FROM NOTES:
{context}

QUESTION: {query}

Instructions:
- Answer concisely based on the context
- If you use information from the notes, reference them like [1], [2], etc.
- If the context doesn't answer the question, say "Based on the available notes, I don't have information about that."
- Do not make up information not in the context

Answer:"""


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
