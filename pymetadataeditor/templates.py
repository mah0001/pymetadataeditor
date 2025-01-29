import copy

# import logging
import warnings
from enum import Enum
from typing import Dict, List, Optional, Tuple, Type, get_args

from annotated_types import Ge, Le, MaxLen, MinLen
from metadataschemas.utils.schema_base_model import SchemaBaseModel
from metadataschemas.utils.utils import (
    get_subtype_of_optional_or_list,
    is_list_annotation,
    is_optional_annotation,
    is_optional_list,
    merge_dicts,
    standardize_keys_in_dict,
)
from pydantic import BaseModel, Field, create_model
from pydantic._internal._fields import pydantic_general_metadata
from pydantic.fields import FieldInfo

from pymetadataeditor.utils import strip_model_rules

# # Configure logging
# def setup_logging(enable_logging: bool = True):
#     if enable_logging:
#         logging.basicConfig(
#             level=logging.DEBUG,  # Set log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
#             format="%(filename)s:%(lineno)d - %(levelname)s - %(message)s",
#         )
#         logging.captureWarnings(True)  # Redirect warnings to the logging system
#     else:
#         logging.disable(logging.CRITICAL)  # Disable all logging


# # Enable or disable logging by setting this variable
# ENABLE_LOGGING = False

# # Call the setup function
# setup_logging(ENABLE_LOGGING)


__all__ = ["pydantic_from_template"]


def copy_field_set_required_status(field: FieldInfo, required: bool) -> FieldInfo:
    """
    Create a copy of an existing field with the 'required' status adjusted.

    We want to take most of the field info from the original field, but the reqruied status from the template.

    Args:
        field (FieldInfo): The original field to copy.
        required (bool): Whether the new field should be required.

    Returns:
        FieldInfo: A new field instance with the updated 'required' status.
    """
    return FieldInfo(
        default=(... if required else None),  # Adjust required status
        alias=field.alias if hasattr(field, "alias") else None,
        title=field.title if hasattr(field, "title") else None,
        description=field.description if hasattr(field, "description") else None,
        examples=field.examples if hasattr(field, "examples") else None,
        json_schema_extra=field.json_schema_extra if hasattr(field, "json_schema_extra") else None,
        metadata=field.metadata if hasattr(field, "metadata") else None,
    )


def get_child_field_info_from_dot_annotated_name(name, parent_schema):
    name_split = name.split(".")
    sub_schema = parent_schema
    for key in name_split[:-1]:
        sub_schema = sub_schema.model_fields[key].annotation
        if is_optional_annotation(sub_schema) or is_list_annotation(sub_schema):
            sub_schema = get_subtype_of_optional_or_list(sub_schema)
        if not isinstance(sub_schema, type(BaseModel)):
            raise KeyError(name)
    try:
        child_field_info = standardize_keys_in_dict(sub_schema.model_fields)[name_split[-1]]
    except KeyError as e:
        raise KeyError(name_split[-1]) from e
    # except:
    #     raise ValueError(f"name={name}, parent_schema={sub_schema}")
    return copy.copy(child_field_info)


def define_simple_element(
    item, parent_schema, element_type=str, apply_rules: bool = True
) -> Dict[str : Tuple[Type[BaseModel]], Field]:
    assert (
        isinstance(item, dict)
        and "type" in item
        and item["type"] in ["string", "text", "integer", "number", "boolean", "date", "textarea"]
    ), f"expected string, integer or boolean item, got {item}"
    try:
        child_field_info = get_child_field_info_from_dot_annotated_name(item["key"], parent_schema)
    except KeyError as e:
        if "prop_key" in item:
            prop_key = item["prop_key"]
            prop_key_split = prop_key.split(".")
            # drop elements from prop_key_split if they begin "section-"
            prop_key_split = [x for x in prop_key_split if not x.startswith("section-")]
            prop_key = ".".join(prop_key_split)
            try:
                child_field_info = get_child_field_info_from_dot_annotated_name(prop_key, parent_schema)
            except KeyError as e2:
                warnings.warn(
                    (
                        f"KeyError: {e2}. Field likely doesn't exist in base schema. "
                        f"Proceeding since prop_key = '{prop_key}' is a {element_type} type. "
                        f"Full item defition = {item}"
                    ),
                    UserWarning,
                )
                child_field_info = Field(..., title=item["title"])
        else:
            warnings.warn(
                (
                    f"KeyError: {e}. Field likely doesn't exist in base schema. "
                    f"Proceeding since key='{item['key']}' is a {element_type} type. "
                    f"Full item defition = {item}"
                ),
                UserWarning,
            )
            child_field_info = Field(..., title=item["title"])
    field_type = update_field_info(item, child_field_info, element_type, apply_rules=apply_rules)
    return {item["key"]: field_type}


def get_constraints_from_string(s: str) -> List:
    """
    Parses a string of constraints separated by '|' and returns a list of corresponding constraint objects.

    Supported constraints:
    - "required": This constraint is ignored in the current implementation as it is applied elsewhere
    - "alpha_dash": Adds a pattern constraint that allows only alphabetic characters and dashes.
    - "min:<value>": Adds a minimum length constraint.
    - "max:<value>": Adds a maximum length constraint.

    Args:
        s (str): A string containing constraints separated by '|'.

    Returns:
        List: A list of constraint objects based on the input string.

    Example:
        >>> get_constraints_from_string("required|alpha_dash|min:5|max:80")
        [pydantic_general_metadata(pattern='^[a-zA-Z\\-]+$'), MinLen(5), MaxLen(80)]
    """
    annotations = []
    for annotation in s.split("|"):
        annotation = annotation.strip()
        if annotation == "":
            continue
        elif annotation in ["required", "idno", "numeric"]:
            continue
        elif annotation == "alpha_dash":
            annotations.append(pydantic_general_metadata(pattern="^[a-zA-Z\\-]+$"))
        elif annotation.startswith("min:"):
            annotations.append(MinLen(int(annotation.split(":")[1])))
        elif annotation.startswith("max:"):
            annotations.append(MaxLen(int(annotation.split(":")[1])))
        elif annotation.startswith("min_value"):
            annotations.append(Ge(int(annotation.strip("min_value").strip(":"))))
        elif annotation.startswith("max_value"):
            annotations.append(Le(int(annotation.strip("max_value").strip(":"))))
        else:
            # logging.warning(f"Unknown constraint: '{annotation}' from string: '{s}'")
            warnings.warn(f"UnknownConstraint: '{annotation}' from the list of constraints: '{s}'")
    return annotations


def create_enum(enum_name, values: list | dict) -> Enum:
    """
    Create an enum from a list of values.

    Args:
        enum_name (str): The name of the enum.
        values (list|dict): Can be a list of strings or a list of dicts with 'label' and 'code' keys.

    Returns:
        Enum: The created enum.
    """
    # Create the enum
    e = {}
    for value in values:
        if isinstance(value, str):
            e[value.strip().replace(" ", "_")] = value.strip()
        elif isinstance(value, dict) and "label" in value and "code" in value:
            e[value["label"].strip().replace(" ", "_")] = value["code"].strip()
        else:
            raise ValueError(
                f"Invalid value for enum: {value} from {values},"
                " must be a list of strings or dicts with 'label' and 'code' keys."
            )
    return Enum(enum_name, e)


def update_field_info(
    template_info, child_field_info, overriding_element_type: Optional[str] = None, apply_rules: bool = True
) -> Tuple[Type, FieldInfo]:
    """
    Updates the attributes of `child_field_info` based on the `template_info` dictionary.

    Args:
        template_info (dict): A dictionary containing template information with keys and values to update.
        child_field_info (object): The object whose attributes are to be updated.
        overriding_element_type (Optional[str], optional): An optional string to override the element type.

    Returns:
        tuple: A tuple containing the field type and the updated `child_field_info`.

    Raises:
        AttributeError: If an attribute in `template_info` cannot be set on `child_field_info`.

    Logs:
        Logs warnings if an attribute cannot be set on `child_field_info`.
        Logs information if the field is required or if the key contains "abbreviation".
    """
    child_field_info.title = template_info.get("title") or template_info.get("name") or child_field_info.title
    child_field_info.description = (
        template_info.get("description") or template_info.get("help_text") or child_field_info.description
    )
    # child_field_info.metadata = get_constraints_from_string(template_info.get('constraints', ''))
    rules = (
        template_info.get("constraints")
        or template_info.get("rules_")
        or template_info.get("_rules")
        or template_info.get("__rules", "")
    )
    if apply_rules and rules:
        child_field_info.metadata = get_constraints_from_string(rules)
    # if 'min' in rules and apply_rules:
    #     logging.info(f"MIN: template_info = {template_info}; child_field_info = {child_field_info}")

    for k, v in template_info.items():
        if k in [
            "required",
            "is_required",
            "key",
            "prop_key",
            "description",
            "help_text",
            "type",
            "display_type",
            "title",
            "name",
            "rules",
            "rules_",
            "_rules",
            "__rules",
            "is_recommended",
            "class",
            "enum",
            "props",
            "_ddi_xpath",
            "is_custom",
            "items",
            "type_options",
        ]:
            continue
        try:
            setattr(child_field_info, k, v)
        except AttributeError:
            # logging.warning(f"UnknownFieldInfoKey: {k}={v} not set on {child_field_info}")
            warnings.warn(f"UnknownFieldInfoKey: {k}='{v}' in template info {template_info}")
            continue

    if overriding_element_type is None:
        type_to_type = {
            "string": str,
            "text": str,
            "integer": int,
            "number": int,
            "boolean": bool,
            "date": str,
            "textarea": str,
        }

        element_type = template_info.get("type") or template_info.get("display_type")
        element_type = type_to_type.get(element_type, str)
        if apply_rules and "rules" in template_info:
            if isinstance(template_info["rules"], dict) and "is_uri" in template_info["rules"]:
                element_type = str  # AnyUrl - for required fields the default is example.com which is confusing
            elif isinstance(template_info["rules"], list) and len(template_info["rules"]) == 0:
                pass
            else:
                # logging.warning(f"Unknown rule: {template_info['rules']}")
                warnings.warn(f"UnknownRule: {template_info['rules']} - expected dict")
        if "enum" in template_info:
            if isinstance(template_info["enum"], list) and len(template_info["enum"]) > 0:
                enum_info = template_info["enum"]
                name = child_field_info.title
                try:
                    element_type = create_enum(name, enum_info)
                except ValueError:
                    warnings.warn(f"UnknownEnum: '{template_info['enum']}' found in template_info: {template_info}")
                    element_type = str
            else:
                # logging.warning(f"Unknown enum: '{template_info['enum']}' found in template_info: {template_info}")
                warnings.warn(f"UnknownEnum: '{template_info['enum']}' found in template_info: {template_info}")
    else:
        element_type = overriding_element_type

    required = (
        template_info.get("required")
        or template_info.get("is_required")
        or template_info.get("class", "") == "required"
        or "required" in template_info.get("rules_", "")
        or "required" in template_info.get("_rules", "")
        or "required" in template_info.get("__rules", "")
    )
    if required:
        # logging.info("REQUIRED, item: %s", template_info)
        child_field_info = copy_field_set_required_status(child_field_info, True)
        field_type = element_type, child_field_info
    else:
        child_field_info.default = None
        child_field_info = copy_field_set_required_status(child_field_info, False)
        field_type = Optional[element_type], child_field_info
    return field_type


def fill_skipped_field_info(d_old, parent_schema, parent_name=""):
    new_vals = {}
    for k, v in d_old.items():
        if isinstance(v, dict):
            childname = ".".join([parent_name, k]).strip(".")
            # v_new = fill_skipped_field_info(v, parent_schema, parent_name=childname)
            try:
                field_info = get_child_field_info_from_dot_annotated_name(childname, parent_schema)
            except KeyError:
                field_info = Field(..., title=k)
            mdl = create_model_for_template(v, parent_schema, k, childname)
            if ("required" in v and v["required"]) or ("is_required" in v and v["is_required"]):
                field_info = copy_field_set_required_status(field_info, True)
            else:
                mdl = Optional[mdl]
                field_info = copy_field_set_required_status(field_info, False)
            new_vals[k] = (mdl, field_info)
    d_new = d_old
    for k, v in new_vals.items():
        d_new[k] = v
    return d_new


def create_model_for_template(
    dict_of_elements: dict,
    parent_schema: Type[SchemaBaseModel],
    name: str,
    parent_name: Optional[str] = None,
    uid: Optional[str] = None,
) -> Type[BaseModel]:
    dict_of_elements = fill_skipped_field_info(
        dict_of_elements, parent_schema, parent_name if parent_name is not None else ""
    )
    dict_of_elements = standardize_keys_in_dict(dict_of_elements, pascal_to_snake=True)

    model_name = name.replace(" ", "_").rstrip("_").replace(".", "-")
    model = create_model(
        model_name,
        __module__="template",
        __base__=SchemaBaseModel,
        **dict_of_elements,
    )
    model._metadata_type__ = (
        parent_schema._metadata_type__
        if isinstance(parent_schema._metadata_type__, str)
        else parent_schema._metadata_type__.default
    )
    model._metadata_type_version__ = (
        parent_schema._metadata_type_version__
        if isinstance(parent_schema._metadata_type_version__, str)
        else parent_schema._metadata_type_version__.default
    )
    model._template_name__ = name if uid is not None else None
    model._template_uid__ = uid
    return model


def get_children_of_props(
    props: List[Dict[str, str]], parent_schema: Type[BaseModel], apply_rules: bool = True
) -> Dict[str : Tuple[Type[BaseModel]], Field]:
    children = {}
    for prop in props:
        if "prop_key" not in prop:
            children.update(template_type_handler(prop, parent_schema, apply_rules=apply_rules))
        else:
            name = prop["prop_key"]
            try:
                child_field_info = get_child_field_info_from_dot_annotated_name(name, parent_schema)
                # if "title" in prop:
                #     child_field_info.title = prop["title"]
                # if "help_text" in prop:
                #     child_field_info.description = prop["help_text"]
                # child_field = child_field_info.annotation, child_field_info
                child_field = update_field_info(prop, child_field_info, apply_rules=apply_rules)
                children[prop["key"]] = child_field
            except KeyError:
                children.update(template_type_handler(prop, parent_schema, apply_rules=apply_rules))
    return children


def make_array_element_name(key: str) -> str:
    """
    If name ends in s then replace the s and capitalize, else append Item to the string and capitalize

    >>>make_array_element_name("elements")
    "Element"

    >>>make_array_element_name("license")
    "LicenseItem"
    """
    assert isinstance(key, str), f"make_array_element_name expected str, got type {type(key)} for input {key}"
    key = key.split(".")[-1]
    if key[-1] == "s":
        return key[:-1].capitalize()
    else:
        return f"{key.capitalize()}Item"


def define_array_element(item, parent_schema, apply_rules: bool = True) -> Dict[str : Tuple[Type[BaseModel]], Field]:
    assert "type" in item and (
        item["type"] == "array" or item["type"] == "nested_array"
    ), f"expected array item but got {item}"
    assert "key" in item, f"expected key in item but got {item.keys()}"
    field_info = Field(..., title=item["title"])
    # if "help_text" in item:
    #     field_info.description = item["help_text"]
    if "props" not in item:
        warnings.warn(f"ArrayMissingType: '{item}' - assuming it's an array of str")
        element_type = List[str]
    else:
        children = get_children_of_props(item["props"], parent_schema, apply_rules=apply_rules)
        child_model = create_model_for_template(children, parent_schema, make_array_element_name(item["key"]))
        element_type = List[child_model]

    field_type = update_field_info(item, field_info, overriding_element_type=element_type, apply_rules=apply_rules)

    return {item["key"]: field_type}


def define_simple_array_element(
    item: dict, parent_schema: Type[BaseModel], apply_rules: bool = True
) -> Dict[str : Tuple[Type[BaseModel]], Field]:
    assert (
        isinstance(item, dict) and "type" in item and item["type"] == "simple_array"
    ), f"expected simple_array item, got {item}"
    try:
        child_field_info = get_child_field_info_from_dot_annotated_name(item["key"], parent_schema)
    except KeyError as e:
        warnings.warn(
            (
                f"KeyError: {e}. Field likely doesn't exist in base schema. "
                f"Proceeding since key={item['key']} is a simple_array type. "
                f"Full item defition = {item}"
            ),
            UserWarning,
        )
        child_field_info = Field(..., title=item["title"])
    field_type = update_field_info(item, child_field_info, overriding_element_type=List[str], apply_rules=apply_rules)
    return {item["key"]: field_type}


def dot_to_hierarchy(d):
    """
    Where dictionary keys have '.', separate the strings either side of the dot into a hierarchy of dictionaries.

    Example:

    >>> dot_to_hierarchy({"firstkey.secondkey.thirdkey": 1,
                          "firstkey.secondkey.fourthkey": 2,
                          "fifthkey": 3,
                          "firstkey.sixthkey": 4})
    {'firstkey': {'secondkey': {'thirdkey': 1, 'fourthkey': 2}, 'sixthkey': 4}, 'fifthkey': 3}
    """

    def merge_dicts(target, source):
        """Recursively merge source dictionary into target dictionary."""
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                merge_dicts(target[key], value)
            else:
                target[key] = value

    result = {}

    for key, value in d.items():
        if isinstance(value, dict):
            value = dot_to_hierarchy(value)  # Recursively handle nested dictionaries

        parts = key.split(".")
        current = result
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]

        # Merge if necessary
        if isinstance(current.get(parts[-1]), dict) and isinstance(value, dict):
            merge_dicts(current[parts[-1]], value)
        else:
            current[parts[-1]] = value

    return result


def define_group_of_elements(
    items: List[dict], parent_schema: Type[BaseModel], apply_rules: bool = True
) -> Dict[str : Tuple[Type[BaseModel]], Field]:
    elements = {}
    for item in items:
        if "is_custom" in item and item["is_custom"] is True:
            warnings.warn(f"SkippingCustomElement: '{item}' - Future work required to support these.")
            continue
            # if "additional" not in elements:
            #     elements["additional"] = {}
            # elif not isinstance(elements["additional"], dict):
            #     elements["additional"] = {
            #         k: (v.annotation, v) for k, v in elements["additional"][0].model_fields.items()
            #     }
            # d = template_type_handler(item, parent_schema, apply_rules=apply_rules)
            # m = create_model_for_template(d, parent_schema, item["key"])
            # field_info = Field(..., title=item["title"])
            # field_type = update_field_info(item, field_info, overriding_element_type = m, apply_rules=apply_rules)
            # elements["additional"][item["key"]] = field_type
        else:
            new_dict = template_type_handler(item, parent_schema, apply_rules=apply_rules)
            elements = merge_dicts(elements, new_dict)
    elements = dot_to_hierarchy(elements)
    elements = standardize_keys_in_dict(elements, pascal_to_snake=True)
    if "additional" in elements and isinstance(elements["additional"], dict):
        additional = elements.pop("additional")
        additional = create_model_for_template(additional, parent_schema, "additional")
        sub_field = Field(...)
        sub_field.title = "additional"
        elements["additional"] = additional, sub_field
    return elements


def template_type_handler(item, parent_schema, apply_rules: bool = True):
    if item["type"] in ["string", "text", "date", "textarea"]:
        return define_simple_element(item, parent_schema, str, apply_rules=apply_rules)
    elif item["type"] in ["integer", "number"]:
        return define_simple_element(item, parent_schema, int, apply_rules=apply_rules)
    elif item["type"] == "boolean":
        return define_simple_element(item, parent_schema, bool, apply_rules=apply_rules)
    elif item["type"] in ["array", "nested_array"]:
        return define_array_element(item, parent_schema, apply_rules=apply_rules)
    elif item["type"] == "simple_array":
        return define_simple_array_element(item, parent_schema, apply_rules=apply_rules)
    elif item["type"] in ["section", "section_container"]:
        if "items" in item:
            return define_group_of_elements(item["items"], parent_schema, apply_rules=apply_rules)
        elif "props" in item:
            return define_group_of_elements(item["props"], parent_schema, apply_rules=apply_rules)
        else:
            raise ValueError(f"{item['type']} does not contain items or props, found only {item}")
    else:
        raise NotImplementedError(f"type {item['type']}, {item}")


def append_variables_and_data_files(model_elements, parent_schema, apply_rules: bool = True):
    # as a hack, when we need no rules for LLM inference, don't include the "data_files", "variables", "variable_groups"
    # I found that the LLM is bad at these anyway and struggled with default *numerical* values.
    # I will have to come back to dealing with default numerical values.
    if not apply_rules:
        return model_elements

    if not (
        parent_schema._metadata_type__ == "microdata"
        or (
            hasattr(parent_schema._metadata_type__, "default") and parent_schema._metadata_type__.default == "microdata"
        )
    ):
        return model_elements

    for v in ["data_files", "variables", "variable_groups"]:
        if v in model_elements:
            continue
        field_info = get_child_field_info_from_dot_annotated_name(v, parent_schema)
        annotation = field_info.annotation
        if is_optional_annotation(annotation):
            field_info = copy_field_set_required_status(field_info, False)
        else:
            field_info = copy_field_set_required_status(field_info, True)

        if not apply_rules:
            if is_optional_list(annotation):
                print("is optional list")
                annotation = Optional[List[strip_model_rules(get_args(get_args(annotation)[0])[0])]]
            elif is_list_annotation(annotation):
                print("is list")
                annotation = List[strip_model_rules(get_args(annotation)[0])]
            elif is_optional_annotation(annotation):
                print("is optional")
                annotation = Optional[strip_model_rules(get_args(annotation)[0])]
        model_elements[v] = (annotation, field_info)
    return model_elements


def pydantic_from_template(
    template: Dict, parent_schema: Type[SchemaBaseModel], uid: str, name: Optional[str] = None, apply_rules: bool = True
) -> Type[BaseModel]:
    assert "items" in template, f"expected 'items' in template but got {list(template.keys())}"
    if name is None:
        if "title" in template:
            name = template["title"]
        else:
            name = "new_model"
    model_elements = define_group_of_elements(template["items"], parent_schema, apply_rules=apply_rules)
    if parent_schema._metadata_type__ == "microdata" or (
        hasattr(parent_schema._metadata_type__, "default") and parent_schema._metadata_type__.default == "microdata"
    ):
        model_elements = append_variables_and_data_files(model_elements, parent_schema, apply_rules=apply_rules)
    return create_model_for_template(model_elements, parent_schema, name, uid=uid)
