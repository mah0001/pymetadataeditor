"""Helper functions for the LLM Metadata Editor when working with Pydantic models and LLM outputs."""

from datetime import datetime
from typing import Any, List, get_args

from metadataschemas.utils.quick_start import make_skeleton
from metadataschemas.utils.utils import (
    get_subtype_of_optional_or_list,
    is_list_annotation,
    is_optional_annotation,
    is_optional_list,
    subset_pydantic_model_type,
)
from openai import APITimeoutError
from pydantic import BaseModel, ValidationError

# from tqdm import tqdm
from tqdm import tqdm


def _prepend_draft_drop_non_str(d: Any, prefix: str) -> dict | list | str | None:
    """Recursively prepend a prefix to all strings in a dictionary or list and drop empty strings and non-strings.

    Args:
        d (Any): The dictionary or list to process.
        prefix (str): The prefix to prepend to all strings.

    Returns:
        dict | list | str | None: The processed dictionary or list, or the string with the prefix prepended.
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
    """Recursively updates a model definition with given updates and validates the result.

    This function takes a model definition and a dictionary of updates, makes a skeleton and applies the updates
    to that skeleton, and validates the updated model. If validation fails for any update value, the
    original skeleton value is retained.

    Args:
        model_def (type[BaseModel]): The model definition class to be updated.
        updates (dict): A dictionary containing the updates to be applied to the model.
        verbose (bool, optional): If True, prints detailed information about validation failures. Defaults to False.

    Returns:
        BaseModel: The validated model instance with the applied updates.

    Raises:
        ValidationError: If the final model validation fails.

    Steps:
        1. Create a skeleton of the model and dump its initial state.
        2. Validate the initial state of the model.
        3. Iterate over the updates dictionary.
        4. For each update, check if the key exists in the original model.
        5. Determine the type of the field (annotation) and handle optional and list types.
        6. Recursively update nested models if the value is a dictionary or a list of dictionaries.
        7. Apply the candidate value to the original model.
        8. Validate the updated model.
        9. If validation fails, revert to the original value and optionally print the error.
        10. Return the validated model instance.
    """
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
    """Returns the current date as a formatted string with an ordinal suffix for the day.

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
    """Converts a JSON object into Markdown.  Future versions of MarkItDown will support this natively.

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


def call_per_field(
    klass: type[BaseModel], client, model: str, messages: list[dict[str, str]], show_progress_bar: bool = False
) -> BaseModel:
    """Calls the LLM per field and returns a validated model.

    This function is typically used when the LLM model is less powerful such as when the model is running locally.

    Args:
        klass (type[BaseModel]): The Pydantic model class to be updated.
        client: The LLM client. such as OpenAI(api_key=..., base_url=...) or AzureOpenAI(api_key=..., base_url=...)
        model (str): The model name, for example "gpt-4o" or "llama3.1".
        messages (list[dict[str, str]]): The messages to be sent to the LLM.
        show_progress_bar (bool): If True, shows a progress bar. Defaults to False but is set to True nested calls.


    Returns:
        BaseModel: The validated model instance with the applied updates.

    Example:
    ```python
    klass = metadata_class_no_rules, metadata_type, _ = MetadataEditor._get_metadata_class_and_type_and_UID(
            metadata_type_or_template_uid, apply_template_rules=False
        )
    client = OpenAI(api_key=..., base_url=...)
    model = "gpt-4o"
    messages = [{"role": "system", "content": "You are a helpful assistant who writes metadata."},
                {"role": "user", "content": "A report on the state of the world"}]
    updated_model = call_per_field(klass, client, model, messages)
    ```
    1. The function iterates over each field in the Pydantic model.
    2. For each field, it sends a request to the LLM with the provided messages.
    3. If the LLM response is valid, it updates the field in the model.
    4. If the LLM response is invalid, it attempts to handle nested fields or lists.
    5. The function returns the updated and validated model.
    """
    final_dict = {}
    for field in tqdm(klass.model_fields.keys(), disable=not show_progress_bar):
        try:
            completion = client.beta.chat.completions.parse(
                model=model,
                messages=messages,
                response_format=subset_pydantic_model_type(klass, [field]),
                temperature=0.0,
                timeout=60 * 1,
            )
        except APITimeoutError:
            # print(f"{' '*(indent+2)}Timeout")
            continue
        except ValidationError:
            # print(f"{' '*indent}Validation Error for {field}, attempting to step through subfields")
            field_annotation = klass.model_fields[field].annotation
            # print(f"{' '*indent}field")
            if is_optional_list(field_annotation) or is_list_annotation(field_annotation):
                # print(get_subtype_of_optional_or_list(field_annotation))
                class subtype(BaseModel):
                    field: List[get_subtype_of_optional_or_list(field_annotation)]

                final_dict[field] = call_per_field(subtype, client, model, messages, show_progress_bar=True)
            elif is_optional_annotation(field_annotation):
                # print(get_subtype_of_optional_or_list(field_annotation))
                final_dict[field] = call_per_field(
                    get_subtype_of_optional_or_list(field_annotation), client, model, messages, show_progress_bar=True
                )
            else:
                continue
        else:
            message = completion.choices[0].message
            metadata_dict = message.parsed.model_dump(exclude_none=True, exclude_unset=True)
            final_dict = {**final_dict, **metadata_dict}
    return _iterated_validated_update_to_outline(klass, final_dict)
