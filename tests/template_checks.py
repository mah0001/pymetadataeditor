import os
import warnings
from collections import defaultdict

import pandas as pd

from pymetadataeditor import MetadataEditor


def categorize_warnings(uid, template_info: pd.Series, folder):
    # List to store warnings
    caught_warnings = []

    # Function to catch warnings
    def custom_warning_handler(message, category, filename, lineno, file=None, line=None):
        caught_warnings.append(str(message))

    # Set the custom warning handler
    warnings.showwarning = custom_warning_handler

    me.get_metadata_class(uid)

    # Initialize containers for categorized warnings
    categorized_warnings = defaultdict(set)  # Using a dictionary with sets to handle unique values

    # Loop through caught_warnings and categorize them
    for warning in caught_warnings:
        if warning.startswith("UnknownFieldInfoKey"):
            categorized_warnings["unknown_field_info_keys"].add("".join(warning.split(":")[1:]).strip())
        elif warning.startswith("KeyError"):
            categorized_warnings["key_errors"].add("".join(warning.split(":")[1:]).strip())
        elif warning.startswith("UnknownEnum"):
            categorized_warnings["unknown_enum"].add("".join(warning.split(":")[1:]).strip())
        elif warning.startswith("UnknownRule"):
            categorized_warnings["unknown_rule"].add("".join(warning.split(":")[1:]).strip())
        elif warning.startswith("UnknownConstraint"):
            categorized_warnings["unknown_constraint"].add("".join(warning.split(":")[1:]).strip())
        elif warning.startswith("ArrayMissingType"):
            categorized_warnings["array_missing_types"].add("".join(warning.split(":")[1:]).strip())
        elif warning.startswith("SkippingCustomElement"):
            categorized_warnings["custom_element_skipped"].add("".join(warning.split(":")[1:]).strip())
        elif "Unverified HTTPS request is being made to host " in warning:
            categorized_warnings["insecure_request_warning"].add(warning)
        else:
            categorized_warnings["unknown_warnings"].add(warning)

    # Convert sets to sorted lists for final output
    unknown_field_info_keys = sorted(categorized_warnings["unknown_field_info_keys"])
    key_errors = sorted(categorized_warnings["key_errors"])
    unknown_enum = sorted(categorized_warnings["unknown_enum"])
    unknown_rule = sorted(categorized_warnings["unknown_rule"])
    unknown_constraint = sorted(categorized_warnings["unknown_constraint"])
    array_missing_types = sorted(categorized_warnings["array_missing_types"])
    custom_element_skipped = sorted(categorized_warnings["custom_element_skipped"])
    unknown_warnings = sorted(categorized_warnings["unknown_warnings"])

    # Create the directory if it does not exist
    data_type = template_info.data_type
    os.makedirs(f"{folder}/{data_type}", exist_ok=True)
    metadata_name = template_info["name"].replace(" ", "_").replace(".", "-").replace("/", "-")

    if (
        len(key_errors) != 0
        or len(unknown_field_info_keys) != 0
        or len(unknown_enum) != 0
        or len(array_missing_types) != 0
        or len(unknown_rule) != 0
        or len(unknown_constraint) != 0
        or len(custom_element_skipped) != 0
        or len(unknown_warnings) != 0
    ):
        with open(f"{folder}/{data_type}/{uid}_{metadata_name}.txt", "w") as f:
            f.write(
                f"Template '{template_info['name']}', UID: {template_info.uid}, DataType: {template_info.data_type}\n\n"
            )
            if len(key_errors) > 0:
                f.write("Key errors in the template:\n")
                for k in key_errors:
                    f.write("\t" + k + "\n")
                f.write("\n")

            if len(unknown_field_info_keys) > 0:
                f.write("Unknown field in the template:\n")
                for u in unknown_field_info_keys:
                    f.write("\t" + u + "\n")
                f.write("\n")

            if len(unknown_enum) > 0:
                f.write("Unknown enum in the template:\n")
                for u in unknown_enum:
                    f.write("\t" + u + "\n")
                f.write("\n")

            if len(array_missing_types) > 0:
                f.write("Array missing type in the template:\n")
                for u in array_missing_types:
                    f.write("\t" + u + "\n")
                f.write("\n")

            if len(unknown_rule) > 0:
                f.write("Unknown rule in the template:\n")
                for u in unknown_rule:
                    f.write("\t" + u + "\n")
                f.write("\n")

            if len(unknown_constraint) > 0:
                f.write("Unknown constraint in the template:\n")
                for u in unknown_constraint:
                    f.write("\t" + u + "\n")
                f.write("\n")

            if len(custom_element_skipped) > 0:
                f.write("Custom element skipped in the template:\n")
                for u in custom_element_skipped:
                    f.write("\t" + u + "\n")
                f.write("\n")

            if len(unknown_warnings) > 0:
                f.write("Unknown warnings in the template:\n")
                for u in unknown_warnings:
                    f.write("\t" + u + "\n")
                f.write("\n")
    return unknown_warnings


# def get_missing_types(d: dict) -> list[str]:

#     bad = []
#     for k, v in d.items():
#         if k == 'type':
#             if isinstance(v, dict):
#                 bad += [f"{k}.{x}" for x in get_missing_types(v)]
#             elif v is None:
#                 bad.append(k)
#             elif isinstance(v, str) and v.strip() == "":
#                 bad.append(k)
#             elif not isinstance(v, str):
#                 bad.append(k)
#         elif k == 'anyOf':
#             if not isinstance(v, list):
#                 bad.append(k)
#             elif len(v) == 0:
#                 bad.append(k)
#             elif len([x for x in v if x != {'type': 'null'}]) == 0:
#                 bad.append(k)
#             elif any([len(x)==0 for x in v if x != {'type': 'null'}]):
#                 bad.append(k)
#             elif any(['type' not in v2 and "$ref" not in v2 for v2 in v]):
#                 bad.append(k)
#             elif any([v2['type'].strip()=="" for v2 in v if 'type' in v2]):
#                 bad.append(k)
#             elif any([v2['$ref'].strip()=="" for v2 in v if '$ref' in v2]):
#                 bad.append(k)
#         elif isinstance(v, dict):
#             type_keys = ['type', 'anyOf']
#             if k not in ['$defs', 'properties']:
#                 if len(v) == 1 and "$ref" in v:
#                     if not v["$ref"].startswith("#/$defs/"):
#                         bad.append(k)
#                 elif not any([key in v.keys() for key in type_keys]):
#                     bad.append(k)
#             bad += [f"{k}.{x}" for x in get_missing_types(v)]
#         elif isinstance(v, list):
#             for item in v:
#                 if isinstance(item, dict):
#                     bad += [f"{k}.{x}" for x in get_missing_types(item)]

#     return bad


if __name__ == "__main__":
    folder = "template_warnings"
    os.makedirs(folder, exist_ok=False)
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    with open(env_path) as f:
        for line in f:
            if line.strip() and not line.startswith("#"):
                key, value = line.strip().split("=", 1)
                os.environ[key] = value
    your_api_key = os.getenv("API_KEY")
    your_api_key = os.getenv("API_KEY")
    api_url = os.getenv("API_URL")

    assert your_api_key is not None, "API_KEY is not set"
    assert api_url is not None, "API_URL is not set"
    me = MetadataEditor(api_url=api_url, api_key=your_api_key, verify_ssl=False)
    templates = me.list_templates().drop_duplicates("uid")

    unknown_warnings = set()
    for _, template in templates.iterrows():
        unknown_warnings = unknown_warnings.union(categorize_warnings(template.uid, template, folder))

    for uw in sorted(unknown_warnings):
        print(uw)
    print("done")
