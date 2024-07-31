import json

# import pymetadataeditor.schemas.timeseries_schema as tss
import metadataschemas.timeseries_schema as tss
import pytest
from metadataschemas.schema_base_model import SchemaBaseModel

from pymetadataeditor.tools import update_metadata, validate_metadata


def test_validate_metadata():
    class Example(SchemaBaseModel):
        idno: str
        series_description: tss.SeriesDescription

    with pytest.raises(AssertionError):
        validate_metadata({}, "bad_schema")

    data_is_malformed_json_string = """{"idno": "GB123"""
    with pytest.raises(json.decoder.JSONDecodeError):
        validate_metadata(data_is_malformed_json_string, Example)

    data_is_incomplete_string = """{"idno": "GB123"}"""
    with pytest.raises(ValueError):
        validate_metadata(data_is_incomplete_string, Example)

    data_is_valid_string = """{"idno": "GB123", "series_description": {"idno": "GB123", "name": "GB123"}}"""
    validate_metadata(data_is_valid_string, Example)

    data_is_incomplete_dict = {"idno": "12"}
    with pytest.raises(ValueError):
        validate_metadata(data_is_incomplete_dict, Example)

    data_is_valid_dict = {"idno": "12", "series_description": {"idno": "12", "name": "n"}}
    validate_metadata(data_is_valid_dict, Example)

    data_is_mix_of_dict_and_obj = {"idno": "12", "series_description": tss.SeriesDescription(idno="12", name="n")}
    validate_metadata(data_is_mix_of_dict_and_obj, Example)

    data_is_obj = Example(idno="12", series_description=tss.SeriesDescription(idno="12", name="n"))
    validate_metadata(data_is_obj, Example)


def test_update_metadata():
    class Example(SchemaBaseModel):
        f1: int
        f2: str
        f3: float

    original = Example(f1=1, f2="two", f3=3.0)
    new = update_metadata(original, f1=None, f3=3.3, f2="new_value")

    assert original.f1 == 1
    assert original.f2 == "two"
    assert original.f3 == 3.0
    assert isinstance(new, Example)
    assert new.f1 == 1
    assert new.f2 == "new_value"
    assert new.f3 == 3.3
