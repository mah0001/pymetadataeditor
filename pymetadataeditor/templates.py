import copy
import logging
import warnings
from typing import Dict, List, Optional, Tuple, Type

from metadataschemas.utils.schema_base_model import SchemaBaseModel
from metadataschemas.utils.utils import (
    get_subtype_of_optional_or_list,
    is_list_annotation,
    is_optional_annotation,
    merge_dicts,
    standardize_keys_in_dict,
)
from pydantic import BaseModel, Field, create_model
from pydantic.fields import FieldInfo


# Configure logging
def setup_logging(enable_logging: bool = True):
    if enable_logging:
        logging.basicConfig(
            level=logging.DEBUG,  # Set log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            format="%(filename)s:%(lineno)d - %(levelname)s - %(message)s",
        )
    else:
        logging.disable(logging.CRITICAL)  # Disable all logging


# Enable or disable logging by setting this variable
ENABLE_LOGGING = False

# Call the setup function
setup_logging(ENABLE_LOGGING)

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
        example=field.example if hasattr(field, "example") else None,
        json_schema_extra=field.json_schema_extra if hasattr(field, "json_schema_extra") else None,
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


def define_simple_element(item, parent_schema, element_type=str) -> Dict[str : Tuple[Type[BaseModel]], Field]:
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
                        f"{item}"
                    ),
                    UserWarning,
                )
                child_field_info = Field(..., title=item["title"])
        else:
            warnings.warn(
                (
                    f"KeyError: {e}. Field likely doesn't exist in base schema. "
                    f"Proceeding since key='{item['key']}' is a {element_type} type. "
                    f"{item}"
                ),
                UserWarning,
            )
            child_field_info = Field(..., title=item["title"])
    if "title" in item:
        child_field_info.title = item["title"]
    if "description" in item:
        child_field_info.description = item["description"]
    if "help_text" in item:
        child_field_info.description = item["help_text"]
    if ("required" in item and item["required"]) or ("is_required" in item and item["is_required"]):
        logging.info("REQUIRED, item: %s", item)
        child_field_info = copy_field_set_required_status(child_field_info, True)
        field_type = element_type, child_field_info
    else:
        child_field_info.default = None
        child_field_info = copy_field_set_required_status(child_field_info, False)
        field_type = Optional[element_type], child_field_info
    return {item["key"]: field_type}


def fill_skipped_field_info(d_old, parent_schema, parent_name=""):
    new_vals = {}
    for k, v in d_old.items():
        if isinstance(v, dict):
            childname = ".".join([parent_name, k]).strip(".")
            # v_new = fill_skipped_field_info(v, parent_schema, parent_name=childname)
            try:
                field_info = get_child_field_info_from_dot_annotated_name(childname, parent_schema)
                field_info_found = True
            except KeyError:
                field_info = Field(..., title=k)
                field_info_found = False
            mdl = create_model_for_template(v, parent_schema, k, childname)
            if ("required" in v and v["required"]) or ("is_required" in v and v["is_required"]):
                field_info = copy_field_set_required_status(field_info, True)
                logging.info(
                    f"REQUIRED, k: {k}, field_info_found: {field_info_found}, field_info: {field_info}, d_old: {d_old}"
                )
            else:
                mdl = Optional[mdl]
                field_info = copy_field_set_required_status(field_info, False)
                logging.info(
                    f"OPTIONAL, k: {k}, field_info_found: {field_info_found}, field_info: {field_info}, d_old: {d_old}"
                )
                # field_info.is_required
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
    return create_model(
        model_name,
        __module__="template",
        __base__=SchemaBaseModel,
        __metadata_type__=parent_schema.__metadata_type__,
        __metadata_type_version__=parent_schema.__metadata_type_version__,
        __template_name__=name if uid is not None else None,
        __template_uid__=uid,
        **dict_of_elements,
    )


def get_children_of_props(
    props: List[Dict[str, str]], parent_schema: Type[BaseModel]
) -> Dict[str : Tuple[Type[BaseModel]], Field]:
    children = {}
    for prop in props:
        if "prop_key" not in prop:
            children.update(template_type_handler(prop, parent_schema))
        else:
            name = prop["prop_key"]
            try:
                child_field_info = get_child_field_info_from_dot_annotated_name(name, parent_schema)
                if "title" in prop:
                    child_field_info.title = prop["title"]
                if "help_text" in prop:
                    child_field_info.description = prop["help_text"]
                child_field = child_field_info.annotation, child_field_info
                children[prop["key"]] = child_field
            except KeyError:
                children.update(template_type_handler(prop, parent_schema))
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


def define_array_element(item, parent_schema) -> Dict[str : Tuple[Type[BaseModel]], Field]:
    assert "type" in item and (
        item["type"] == "array" or item["type"] == "nested_array"
    ), f"expected array item but got {item}"
    assert "key" in item, f"expected key in item but got {item.keys()}"
    field_info = Field(..., title=item["title"])
    if "help_text" in item:
        field_info.description = item["help_text"]
    if "props" not in item:
        warnings.warn(f"array without a type found, assuming array of str: {item}")
        element_type = List[str]
    else:
        children = get_children_of_props(item["props"], parent_schema)
        child_model = create_model_for_template(children, parent_schema, make_array_element_name(item["key"]))
        element_type = List[child_model]
    if ("required" in item and item["required"]) or ("is_required" in item and item["is_required"]):
        field_type = element_type, field_info
        field_info = copy_field_set_required_status(field_info, True)
        logging.info("REQUIRED, item: %s", item)
    else:
        field_info.default = None
        field_info = copy_field_set_required_status(field_info, False)
        field_type = Optional[element_type], field_info

    return {item["key"]: field_type}


def define_simple_array_element(
    item: dict, parent_schema: Type[BaseModel]
) -> Dict[str : Tuple[Type[BaseModel]], Field]:
    assert (
        isinstance(item, dict) and "type" in item and item["type"] == "simple_array"
    ), f"expected simple_array item, got {item}"
    try:
        child_field_info = get_child_field_info_from_dot_annotated_name(item["key"], parent_schema)
        if "title" in item:
            child_field_info.title = item["title"]
        if "description" in item:
            child_field_info.description = item["description"]
    except KeyError as e:
        warnings.warn(
            (
                f"KeyError: {e}. Field likely doesn't exist in base schema. "
                f"Proceeding since key={item['key']} is a simple_array type. "
                f"{item}"
            ),
            UserWarning,
        )
        child_field_info = Field(..., title=item["title"])
        if "help_test" in item:
            child_field_info.description = item["help_text"]
    if ("required" in item and item["required"]) or ("is_required" in item and item["is_required"]):
        field_type = List[str], child_field_info
        child_field_info = copy_field_set_required_status(child_field_info, True)
        logging.info("REQUIRED, item: %s", item)
    else:
        child_field_info.default = None
        child_field_info = copy_field_set_required_status(child_field_info, False)
        field_type = Optional[List[str]], child_field_info
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
    items: List[dict], parent_schema: Type[BaseModel]
) -> Dict[str : Tuple[Type[BaseModel]], Field]:
    elements = {}
    for item in items:
        if "is_custom" in item and item["is_custom"] is True:
            if "additional" not in elements:
                elements["additional"] = {}
            elif not isinstance(elements["additional"], dict):
                elements["additional"] = {
                    k: (v.annotation, v) for k, v in elements["additional"][0].model_fields.items()
                }
            d = template_type_handler(item, parent_schema)
            m = create_model_for_template(d, parent_schema, item["key"])
            field_info = Field(..., title=item["title"])
            if "description" in item:
                field_info.description = item["description"]
            if "help_test" in item:
                field_info.description = item["help_text"]
            if ("required" in item and item["required"]) or ("is_required" in item and item["is_required"]):
                field_type = m, field_info
                field_info = copy_field_set_required_status(field_info, True)
                logging.info("REQUIRED, item: %s", item)
            else:
                field_info.default = None
                field_type = Optional[m], field_info
                field_info = copy_field_set_required_status(field_info, False)
            elements["additional"][item["key"]] = field_type
        else:
            new_dict = template_type_handler(item, parent_schema)
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


def template_type_handler(item, parent_schema):
    if item["type"] in ["string", "text", "date", "textarea"]:
        return define_simple_element(item, parent_schema, str)
    elif item["type"] in ["integer", "number"]:
        return define_simple_element(item, parent_schema, int)
    elif item["type"] == "boolean":
        return define_simple_element(item, parent_schema, bool)
    elif item["type"] in ["array", "nested_array"]:
        return define_array_element(item, parent_schema)
    elif item["type"] == "simple_array":
        return define_simple_array_element(item, parent_schema)
    elif item["type"] in ["section", "section_container"]:
        if "items" in item:
            return define_group_of_elements(item["items"], parent_schema)
        elif "props" in item:
            return define_group_of_elements(item["props"], parent_schema)
        else:
            raise ValueError(f"{item['type']} does not contain items or props, found only {item}")
    else:
        raise NotImplementedError(f"type {item['type']}, {item}")


def pydantic_from_template(
    template: Dict, parent_schema: Type[SchemaBaseModel], uid: str, name: Optional[str] = None
) -> Type[BaseModel]:
    assert "items" in template, f"expected 'items' in template but got {list(template.keys())}"
    if name is None:
        if "title" in template:
            name = template["title"]
        else:
            name = "new_model"
    model_elements = define_group_of_elements(template["items"], parent_schema)
    return create_model_for_template(model_elements, parent_schema, name, uid=uid)
