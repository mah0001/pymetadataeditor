from typing import Dict, Type, Union

from metadataschemas.schema_base_model import SchemaBaseModel
from pydantic import BaseModel


def validate_metadata(metadata: Union[Dict, SchemaBaseModel], schema_definition: Type[SchemaBaseModel]) -> None:
    """
    Checks that the metadata contains the key information that all metadata must have, namely idno

    Args:
        metadata (dict or SchemaBaseModel): The metadata to be validated
        schema (str): Type of metadata being passed, must be "TimeSeries"

    Raises:
        ValueError: If the metadata is deemed invalid for whatever reason.

    """
    assert isinstance(schema_definition, type) and issubclass(schema_definition, BaseModel)
    if not isinstance(metadata, (dict, SchemaBaseModel)):
        raise ValueError(
            "Metadata must be passed as a python dictionary or as a pydantic object or a json string, "
            f"but {type(metadata)} was passed instead"
        )

    if isinstance(metadata, SchemaBaseModel):
        metadata = metadata.model_dump()  # SchemaBaseModel validates on assignment so shouldn't need to be re-validated
    schema_definition.model_validate(metadata)


def update_metadata(old_object: SchemaBaseModel, **kwargs):
    """
    Updates the metadata of a given Pydantic model instance with new values provided as keyword arguments.

    Args:
        old_object (SchemaBaseModel): The original instance of a Pydantic model to be updated.
        **kwargs: Arbitrary keyword arguments representing the fields and their new values to update in the model.
                  Only the fields with non-None values will be updated.

    Returns:
        SchemaBaseModel: A new instance of the Pydantic model with updated metadata.

    Raises:
        AttributeError: If a provided field name does not exist in the model.

    Example:
        class Example(SchemaBaseModel):
            f1: int
            f2: str

        original = Example(f1=1, f2="old")
        updated = update_metadata(original, f2="new")
        print(updated)
        # Output: Example(f1=1, f2='new')
    """
    new_object = old_object.model_copy()
    for k, v in kwargs.items():
        if v is not None:
            new_object[k] = v
    return new_object
