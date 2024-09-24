from typing import Dict


def validate_json_patches(patches):
    """
    Validates a list of JSON patches according to the JSON Patch specification.

    Args:
        patches (list): A list of JSON patch dictionaries.

    Returns:
        list: The validated patches with corrected paths if necessary.

    Raises:
        ValueError: If a patch is invalid or contains an error.
    """
    valid_ops = {"add", "remove", "replace", "move", "copy", "test"}
    validated_patches = []

    for patch in patches:
        if not isinstance(patch, dict):
            raise ValueError(f"Invalid patch format: {patch}. Each patch must be a dictionary.")

        op = patch.get("op")
        path = patch.get("path")

        if op not in valid_ops:
            raise ValueError(f"Invalid operation '{op}'. Valid operations are {valid_ops}.")

        if not isinstance(path, str):
            raise ValueError(f"Invalid path: {path}. Path must be a string.")

        if not path.startswith("/"):
            path = "/" + path

        # Additional checks for specific operations
        if op in {"add", "replace", "test"} and "value" not in patch:
            raise ValueError(f"Operation '{op}' requires a 'value' field.")

        if op in {"move", "copy"} and "from" not in patch:
            raise ValueError(f"Operation '{op}' requires a 'from' field.")

        validated_patches.append({**patch, "path": path})

    return validated_patches


def remove_empty_from_dict(old_dict: Dict) -> Dict:
    """Helper function for removing entries from dictionaries that look like:
    [{'name': ''}]
    """
    new_dict = {}
    for k, v in old_dict.items():
        if v is None:
            continue
        if isinstance(v, str):
            if v != "":
                new_dict[k] = v
        elif isinstance(v, dict):
            new_sub_dict = remove_empty_from_dict(v)
            if len(new_sub_dict) > 0:
                new_dict[k] = new_sub_dict
        elif isinstance(v, list):
            new_list = []
            for elem in v:
                if elem is None:
                    continue
                if isinstance(elem, dict):
                    new_elem = remove_empty_from_dict(elem)
                    if len(new_elem) > 0:
                        new_list.append(new_elem)
                elif isinstance(elem, str):
                    if elem != "":
                        new_list.append(elem)
                else:
                    new_list.append(elem)
            if len(new_list) > 0:
                new_dict[k] = new_list
        else:
            new_dict[k] = v
    return new_dict
