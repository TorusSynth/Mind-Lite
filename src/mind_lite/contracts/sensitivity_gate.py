import re
from dataclasses import dataclass

PROTECTED_TAGS = {"private", "sensitive", "secret"}
PROTECTED_PATH_PREFIXES = ("private/", "secrets/", "finance/")
SECRET_PATTERNS = (
    re.compile(r"\bOPENAI_API_KEY\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{8,}\b"),
)


@dataclass(frozen=True)
class SensitivityInput:
    frontmatter: dict
    tags: list[str]
    path: str
    content: str


@dataclass(frozen=True)
class SensitivityResult:
    allowed: bool
    reasons: list[str]


def cloud_eligibility(payload: SensitivityInput) -> SensitivityResult:
    reasons: list[str] = []

    if bool(payload.frontmatter.get("sensitive")) or bool(payload.frontmatter.get("private")):
        reasons.append("blocked_by_frontmatter_flag")

    lowered_tags = {tag.lower() for tag in payload.tags}
    if lowered_tags.intersection(PROTECTED_TAGS):
        reasons.append("blocked_by_tag_rule")

    normalized_path = payload.path.strip().lower().replace("\\", "/")
    if normalized_path.startswith(PROTECTED_PATH_PREFIXES):
        reasons.append("blocked_by_path_rule")

    for pattern in SECRET_PATTERNS:
        if pattern.search(payload.content):
            reasons.append("blocked_by_regex_pattern")
            break

    return SensitivityResult(allowed=(len(reasons) == 0), reasons=reasons)
