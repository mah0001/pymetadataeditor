from datetime import datetime
from typing import Any, get_args

from metadataschemas.utils.quick_start import make_skeleton
from metadataschemas.utils.utils import is_list_annotation, is_optional_annotation
from pydantic import BaseModel, ValidationError


def _prepend_draft_drop_non_str(d: Any, prefix: str) -> dict | list | str | None:
    """
    Recursively prepend a prefix to all strings in a dictionary or list and drop empty strings and non-strings.

    Args:

        d (Any): The dictionary or list to process.
    """

    if isinstance(d, dict):
        out = {}
        for k, v in d.items():
            new_v = _prepend_draft_drop_non_str(v, prefix)
            if new_v is not None:
                out[k] = new_v
        if len(out) > 0:
            return out
        else:
            return None
    elif isinstance(d, list):
        out = []
        for v in d:
            new_v = _prepend_draft_drop_non_str(v, prefix)
            if new_v is not None:
                out.append(new_v)
        if len(out) > 0:
            return out
        else:
            return None
    elif isinstance(d, str):
        if d.strip() == "":
            return None
        else:
            return prefix + d
    else:
        return None


def _iterated_validated_update_to_outline(model_def: type[BaseModel], updates: dict, verbose=False) -> BaseModel:
    original_model = make_skeleton(model_def).model_dump()
    # print(original_model)
    model_def.model_validate(original_model, strict=False)

    model_fields = model_def.model_fields
    for key, value in updates.items():
        if key not in original_model:
            continue

        # get annotation aka type of the field
        annotation = model_fields[key].annotation
        if is_optional_annotation(annotation):
            annotation = get_args(annotation)[0]
        is_list = False
        if is_list_annotation(annotation):
            annotation = get_args(annotation)[0]
            is_list = True
        # print(annotation)

        # get candidate value
        if isinstance(value, dict) and issubclass(annotation, BaseModel):
            candidate_value = _iterated_validated_update_to_outline(annotation, value, verbose=verbose).model_dump()
        elif is_list and isinstance(value, list) and issubclass(annotation, BaseModel):
            candidate_value = []
            for item in value:
                candidate_value.append(
                    _iterated_validated_update_to_outline(annotation, item, verbose=verbose).model_dump()
                )
        else:
            candidate_value = value

        # try the candidate value
        original_value = original_model[key]
        original_model[key] = candidate_value
        try:
            model_def.model_validate(original_model, strict=False)
        except ValidationError as e:
            # If validation fails, leave the original value
            if verbose:
                print(f"Skipping {key}({annotation})={candidate_value} because of {e}\n")
            original_model[key] = original_value
        # print(original_model)

    return model_def.model_validate(original_model, strict=False)


def get_date_as_text():
    """
    Returns the current date as a formatted string with an ordinal suffix for the day.

    The format of the returned date string is "Month DaySuffix, Year", where:
    - Month is the full name of the month (e.g., January, February).
    - DaySuffix is the day of the month with an appropriate ordinal suffix (e.g., 1st, 2nd, 3rd, 4th, etc.).
    - Year is the four-digit year.

    Example:
        If today's date is October 21, 2023, the function will return "October 21st, 2023".

    Returns:
        str: The formatted date string.
    """
    today = datetime.today()
    day = today.day
    # Determine ordinal suffix
    if 10 <= day % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")

    # Format the date
    return today.strftime(f"%B %-d{suffix}, %Y")


def json_to_markdown(data, level=1):
    """
    Converts a JSON object into Markdown.  Future versions of MarkItDown will support this natively.

    Args:
        data: The JSON object (dict, list, or primitive type).
        level: Current Markdown heading level for nested keys.

    Returns:
        A Markdown string.
    """
    markdown = ""

    if isinstance(data, dict):
        for key, value in data.items():
            markdown += f"{'#' * level} {key}\n\n"  # Add heading for the key
            markdown += json_to_markdown(value, level + 1)  # Recursively process value
    elif isinstance(data, list):
        for item in data:
            markdown += f"- {json_to_markdown(item, level + 1).strip()}\n"  # Format as a list
    else:
        # Format primitive types (string, number, boolean, null)
        markdown += f"{data}\n\n"

    return markdown
