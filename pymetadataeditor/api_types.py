"""Project type normalization for Metadata Editor API paths."""

from typing import Dict

# Legacy / display names -> OpenAPI path segment (hyphenated).
_PROJECT_TYPE_ALIASES: Dict[str, str] = {
    "indicator": "timeseries",
    "indicators_db": "timeseries-db",
    "microdata": "survey",
}


def normalize_project_type(project_type: str) -> str:
    """Map legacy or display type names to OpenAPI project-type path segments."""
    key = project_type.strip().lower().replace("-", "_")
    mapped = _PROJECT_TYPE_ALIASES.get(key, key)
    return mapped.replace("_", "-")
