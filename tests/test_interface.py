import itertools
import os
from json import JSONDecodeError
from typing import Dict, List, Optional, Union

# import pymetadataeditor.schemas.indicator_schema as tss
import metadataschemas.indicator_schema as tss
import pandas as pd
import pytest
import requests
from pydantic import BaseModel, ValidationError
from requests.exceptions import SSLError

from pymetadataeditor import MetadataEditor
from pymetadataeditor.exceptions import DeleteNotAppliedError, TemplateError
from pymetadataeditor.requester import RequestsWithSpecificErrors


class MockResponse:
    def __init__(
        self,
        http_status_code: int = None,
        error_message: Optional[str] = None,
        json_data: Optional[Dict] = None,
        raise_json_decode_error: bool = False,
        raise_ssl: bool = False,
    ):
        """
        Used to create mock responses from the API so that we don't actually call the API everytime we run tests
        """
        self.status_code = http_status_code
        self.json_data = json_data if json_data is not None else {}
        self.text = error_message if error_message is not None else {}
        self.raise_json_decode_error = raise_json_decode_error
        self.raise_ssl = raise_ssl

        self.response = requests.Response()
        self.response.status_code = self.status_code
        # self.response._content = self.text.encode("utf-8")
        self.response.headers["Content-Type"] = "application/json"
        self.response.url = "https://example.com/api/resource"

    def raise_for_status(self):
        if self.raise_ssl:
            raise SSLError(self.text)
        elif self.status_code == 404:
            raise requests.exceptions.HTTPError("404")
        elif self.status_code == 403:
            raise requests.exceptions.HTTPError("403")  # Client Error: Forbidden for url", response=self)
        elif self.status_code == 400:
            raise requests.exceptions.HTTPError(
                "400 Client Error: Bad Request for url: example.com", response=self.response
            )

        elif self.status_code != 200:
            raise requests.exceptions.HTTPError(f"{self.status_code} Error")

    def json(self) -> Dict:
        if self.raise_json_decode_error:
            raise JSONDecodeError(msg="could not decode", doc="...", pos=2)
        elif self.json_data is not None:
            return self.json_data
        else:
            return {}


@pytest.fixture
def metadata_editor(monkeypatch):
    def mock_response(*args, **kwargs):
        return MockResponse(http_status_code=200)

    monkeypatch.setattr(requests, "request", mock_response)
    return MetadataEditor(api_url="https://example.com", api_key="test")  # pragma: allowlist secret


def test_MetadataEditor_instantiation(monkeypatch):
    test_api_key = "test"  # pragma: allowlist secret

    # url is not https and user defaults to requiring use of https
    with pytest.raises(ValidationError) as e:
        MetadataEditor(api_url="http://example.com", api_key=test_api_key)
    assert len(e.value.errors()) == 1

    # url is not https but user allows use of http
    def mock_response(*args, **kwargs):
        return MockResponse(http_status_code=200)

    monkeypatch.setattr(requests, "request", mock_response)
    MetadataEditor(api_url="http://example.com", api_key=test_api_key, allow_http=True)

    # bad URL
    def mock_response(*args, **kwargs):
        return MockResponse(http_status_code=404)

    monkeypatch.setattr(requests, "request", mock_response)
    with pytest.raises(requests.HTTPError) as e:
        me = MetadataEditor(api_url="https://example.com", api_key=test_api_key)
        me.projects.list(limit=100)
    assert str(e.value).split(".")[0] == "Page not found"

    # bad SSL
    def mock_response(*args, **kwargs):
        return MockResponse(raise_ssl=True, error_message="SSL Error GB")

    monkeypatch.setattr(requests, "request", mock_response)
    with pytest.raises(SSLError) as e:
        me = MetadataEditor(api_url="https://example.com", api_key=test_api_key)
        me.projects.list(limit=100)
    assert str(e.value)[:12] == "Usually this"

    # bad key
    def mock_response(*args, **kwargs):
        return MockResponse(http_status_code=403)

    monkeypatch.setattr(requests, "request", mock_response)
    with pytest.raises(PermissionError) as e:
        me = MetadataEditor(api_url="https://example.com", api_key=test_api_key)
        me.projects.list(limit=100)
    # assert str(e.value).split(".")[0] == "Access to that URL is denied for https://example.com"
    assert (
        str(e.value) == "Access to that URL is denied for https://example.com/editor Check that the API key is correct"
    )

    # good instantiation
    def mock_response(*args, **kwargs):
        return MockResponse(http_status_code=200)

    monkeypatch.setattr(requests, "request", mock_response)
    me = MetadataEditor(api_url="https://example.com", api_key=test_api_key)
    me.projects.list(limit=100)
    assert me._apinterface.api_key != test_api_key
    assert me._apinterface.api_key.get_secret_value() == test_api_key


@pytest.mark.parametrize("method", ["get", "post"])
def test_given_request(monkeypatch, metadata_editor, method: str):
    if method == "get":

        def func(*args, **kwargs):
            return metadata_editor._apinterface.get_request(*args, **kwargs)

    elif method == "post":

        def func(*args, **kwargs):
            return metadata_editor._apinterface.post_request(*args, **kwargs, json={})

    # api raises some http error
    def mock_response(*args, **kwargs):
        return MockResponse(http_status_code=502)

    monkeypatch.setattr(requests, "request", mock_response)

    with pytest.raises(Exception):
        func("/editor")

    # response is good
    def mock_response(*args, **kwargs):
        return MockResponse(http_status_code=200, json_data={})

    monkeypatch.setattr(requests, "request", mock_response)
    func("/editor")


def test_projects_subclient_list_and_get(monkeypatch, metadata_editor):
    captured = []

    def mock_response(*args, **kwargs):
        captured.append((args, kwargs))
        if kwargs.get("params") is not None:
            return MockResponse(http_status_code=200, json_data={"projects": [{"id": "p1"}], "total": 1})
        return MockResponse(http_status_code=200, json_data={"project": {"id": "my-idno", "title": "Example"}})

    monkeypatch.setattr(requests, "request", mock_response)
    listed = metadata_editor.projects.list(
        limit=10,
        keywords=["a", "b"],
        metadata_type="document",
        sort_by="title_asc",
        date_start="2026-01-01",
        date_end="2026-12-31",
        collection="1,2",
        exclude_collections="true",
        ownership="self",
        users="4,5",
    )
    assert listed["total"] == 1

    got = metadata_editor.projects.get("my-idno", version="1.0.0")
    assert got["project"]["id"] == "my-idno"
    assert captured[0][0][0] == "get"
    assert captured[0][0][1].endswith("/editor")
    assert captured[0][1]["params"]["date_start"] == "2026-01-01"
    assert captured[0][1]["params"]["users"] == "4,5"
    assert captured[1][1]["params"]["version"] == "1.0.0"


def test_projects_subclient_create_update_patch_delete(monkeypatch, metadata_editor):
    captured = []

    def mock_response(*args, **kwargs):
        captured.append((args, kwargs))
        return MockResponse(http_status_code=200, json_data={"ok": True, "id": 123})

    monkeypatch.setattr(requests, "request", mock_response)
    created = metadata_editor.projects.create("timeseries-db", {"idno": "abc"})
    assert created["ok"] is True

    updated = metadata_editor.projects.update("abc-idno", "timeseries-db", {"title": "new"})
    assert updated["ok"] is True

    patched = metadata_editor.projects.patch("abc-idno", "timeseries-db", [{"op": "replace", "path": "/title", "value": "X"}])
    assert patched["ok"] is True

    deleted = metadata_editor.projects.delete("abc-idno")
    assert deleted["ok"] is True
    assert captured[0][0][1].endswith("/editor/create/timeseries-db")
    assert captured[1][0][1].endswith("/editor/update/timeseries-db/abc-idno")
    assert captured[2][0][1].endswith("/editor/patch/timeseries-db/abc-idno")
    assert captured[3][0][0] == "post"
    assert captured[3][0][1].endswith("/editor/delete/abc-idno")


def test_projects_subclient_json_pdf_import_and_versions(monkeypatch, metadata_editor, tmp_path):
    captured = []

    def mock_response(*args, **kwargs):
        captured.append((args, kwargs))
        return MockResponse(http_status_code=200, json_data={"ok": True, "found": True, "value": "x"})

    monkeypatch.setattr(requests, "request", mock_response)
    metadata_editor.projects.get_json(
        "idno-1", version="1.0.0", exclude_variables=1, exclude_private_fields=1, external_resources=1, admin_metadata=1
    )
    metadata_editor.projects.get_json_field("idno-1", path="/idno", exclude_variables=1)
    metadata_editor.projects.generate_pdf("idno-1", include_private_fields=1, template_uid="uid123")

    import_file = tmp_path / "demo.json"
    import_file.write_text("{}")
    metadata_editor.projects.import_project("document", str(import_file))

    metadata_editor.projects.list_versions("idno-1", version="1.2.0")
    metadata_editor.projects.create_version("idno-1", "minor", "added section")
    metadata_editor.projects.delete_version("idno-1", "1.2.0")
    metadata_editor.projects.delete_version_by_id("idno-1", "1.2.0")

    assert captured[0][0][1].endswith("/editor/jsonidno-1")
    assert captured[0][1]["params"]["exclude_variables"] == 1
    assert captured[1][0][1].endswith("/editor/json-field/idno-1")
    assert captured[1][1]["params"]["path"] == "/idno"
    assert captured[2][0][1].endswith("/editor/generate_pdf/idno-1")
    assert captured[2][1]["params"]["template_uid"] == "uid123"
    assert captured[3][0][1].endswith("/importproject")
    assert "file" in captured[3][1]["files"]
    assert captured[4][0][1].endswith("/versions/idno-1")
    assert captured[5][1]["json"]["version_type"] == "minor"
    assert captured[5][1]["json"]["version_notes"] == "added section"
    assert captured[6][1]["json"]["version"] == "1.2.0"
    assert captured[7][1]["json"]["version"] == "1.2.0"


def test_projects_list(monkeypatch, metadata_editor):
    projects_payload = {
        "status": "success",
        "projects": [
            {"id": "1", "created": "2024-06-11T09:58:14-04:00"},
            {"id": "2", "created": "2024-06-11T09:58:14-04:00"},
        ],
        "total": 2,
    }

    def mock_response(*args, **kwargs):
        return MockResponse(http_status_code=200, json_data=projects_payload)

    monkeypatch.setattr(requests, "request", mock_response)

    actual = metadata_editor.projects.list(limit=100)
    assert len(actual["projects"]) == 2

    metadata_editor.projects.list(metadata_type="geospatial", limit=100)
    metadata_editor.projects.list(sort_by="title_asc", limit=100)

    all_projects = metadata_editor.projects.list_all(page_size=2)
    assert len(all_projects["projects"]) == 2


def test_projects_get(monkeypatch, metadata_editor):
    def mock_response(*args, **kwargs):
        return MockResponse(
            http_status_code=400,
            json_data={},
            error_message={"message": "You don't have permission to access this project"},
        )

    monkeypatch.setattr(requests, "request", mock_response)
    with pytest.raises(Exception, match="You don't have permission to access this project"):
        metadata_editor.projects.get(1)

    project = {"status": "success", "project": {"id": "2", "created": "2024-06-11T09:58:14-04:00"}}

    def mock_response(*args, **kwargs):
        return MockResponse(http_status_code=200, json_data=project)

    monkeypatch.setattr(requests, "request", mock_response)
    actual_project = metadata_editor.projects.get(2)["project"]
    assert actual_project["id"] == "2"


@pytest.mark.parametrize(
    "metadata_type, bad_metadata, good_metadata",
    [
        (
            "document",
            {},
            {"document_description": {"title_statement": {"idno": "example_idno", "title": "example_title"}}},
        ),
        ("geospatial", {}, {"description": {"idno": "example_idno"}}),
        ("script", None, {"doc_desc": {"idno": "example_idno"}}),
        ("table", None, {"table_description": {"title_statement": {"idno": "example idno", "title": "example title"}}}),
        (
            "indicator",
            {
                "idno": "GB123",
                "series_description": {"doi": "string", "name": "Gordons Test", "display_name": "string"},
            },
            {
                "idno": "GB123",
                "series_description": {
                    "idno": "string",
                    "doi": "string",
                    "name": "Gordons Test",
                    "display_name": "string",
                },
            },
        ),
        (
            "indicators_db",
            {},
            {"database_description": {"title_statement": {"idno": "example_idno", "title": "example_title"}}},
        ),
        (
            "microdata",
            {"study_desc": {}},
            {
                "study_desc": {
                    "title_statement": {"idno": "1", "title": "microdata1"},
                    "study_info": {"nation": [{"name": "nation_name"}]},
                }
            },
        ),
        ("video", {}, {"video_description": {"idno": "example_idno", "title": "example_title"}}),
    ],
)
def test_metadata_create(monkeypatch, metadata_editor, metadata_type, bad_metadata, good_metadata):
    def mock_response(*args, **kwargs):
        return MockResponse(http_status_code=200, json_data={"id": 1})

    monkeypatch.setattr(requests, "request", mock_response)

    def mock_get_metadata_class(*args, **kwargs):
        return metadata_editor._mm._TYPE_TO_SCHEMA[metadata_type]

    monkeypatch.setattr(metadata_editor, "get_metadata_class", mock_get_metadata_class)

    if bad_metadata is not None:
        with pytest.raises(ValidationError):
            metadata_editor.metadata.create(metadata=bad_metadata, metadata_type_or_template_uid=metadata_type)

    metadata_id = metadata_editor.metadata.create(
        metadata=good_metadata, metadata_type_or_template_uid=metadata_type
    )
    assert metadata_id == 1

    cls = metadata_editor.get_metadata_class(metadata_type)
    metadata_object = cls.model_validate(good_metadata)
    metadata_id = metadata_editor.metadata.create(
        metadata=metadata_object, metadata_type_or_template_uid=metadata_type
    )


def test_metadata_update(tmpdir, monkeypatch, metadata_editor):
    series_description = tss.SeriesDescription(idno="17", name="1")
    metadata_information = {"title": "check we can pass in a dict as well as a pydantic object"}

    # id is bad
    def mock_response(*args, **kwargs):
        return MockResponse(
            http_status_code=400,
            json_data={},
            error_message={"message": "You don't have permission to access this project"},
        )

    monkeypatch.setattr(requests, "request", mock_response)

    def mock_get_metadata_class(*args, **kwargs):
        return tss.TimeseriesSchema

    monkeypatch.setattr(metadata_editor, "get_metadata_class", mock_get_metadata_class)

    with pytest.raises(Exception, match="You don't have permission to access this project"):
        metadata_editor.metadata.update(
            id=1, new_metadata={"series_description": series_description, "metadata_information": metadata_information}
        )

    # id is good
    def mock_response(*args, **kwargs):
        return MockResponse(
            http_status_code=200,
            json_data={
                "project": {
                    "type": "indicator",
                    "metadata": {"idno": "12", "series_description": {"idno": "12", "name": "oldname"}},
                }
            },
        )

    monkeypatch.setattr(requests, "request", mock_response)
    metadata_editor.metadata.update(
        id=1, new_metadata={"series_description": series_description, "metadata_information": metadata_information}
    )

    # use pydantic
    model = metadata_editor.make_metadata_outline("indicator", "pydantic")
    metadata_editor.metadata.update(id=1, new_metadata=model)

    # use excel
    metadata_editor.make_metadata_outline(
        "indicator", "excel", filename=os.path.join(tmpdir, "test_update_project_log_by_id.xlsx")
    )


def test_projects_patch_one(monkeypatch, metadata_editor):
    def mock_response(*args, **kwargs):
        return MockResponse(http_status_code=200, json_data={})

    monkeypatch.setattr(requests, "request", mock_response)

    metadata_editor.projects.patch_one(1, "timeseries", op="remove", path="/toc")

    for p in [
        {"op": "replace", "path": "/title", "value": "New Title"},
        {"op": "add", "path": "/description", "value": "Updated description."},
    ]:
        metadata_editor.projects.patch_one(1, "timeseries", **p)

    with pytest.raises(ValueError, match="Invalid operation"):
        metadata_editor.projects.patch_one(1, "timeseries", op="bad_op", path="/title", value="Should raise error")

    for p in [
        {"op": "replace", "path": "title", "value": "Title without leading slash"},
        {"op": "add", "path": "description", "value": "Description without leading slash"},
    ]:
        metadata_editor.projects.patch_one(1, "timeseries", **p)

    with pytest.raises(ValueError, match="Operation 'replace' requires a 'value' field."):
        metadata_editor.projects.patch_one(1, "timeseries", op="replace", path="/title")


metadata_types = [
    "document",
    "image",
    "geospatial",
    "microdata",
    "script",
    "table",
    "indicator",
    "indicators_db",
    "video",
]
modes = ["excel", "dict", "pydantic"]


@pytest.mark.parametrize("metadata_type, mode", list(itertools.product(metadata_types, modes)))
def test_make_metadata_outline(tmpdir, monkeypatch, metadata_editor, metadata_type, mode):
    def mock_get_metadata_class(*args, **kwargs):
        return metadata_editor._mm._TYPE_TO_SCHEMA[metadata_type]

    monkeypatch.setattr(metadata_editor, "get_metadata_class", mock_get_metadata_class)

    metadata_editor.make_metadata_outline(
        metadata_type_or_template_uid=metadata_type,
        output_mode=mode,
        filename=os.path.join(tmpdir, f"outline_{metadata_type}.xlsx"),
    )


@pytest.mark.parametrize(
    "metadata_type, metadata",
    [
        ("document", {"document_description": {"title_statement": {"idno": "example_idno", "title": "example_title"}}}),
        ("geospatial", {"description": {"idno": "example_idno"}}),
        ("image", {"image_description": {"idno": "example_idno", "title": "example_title"}}),
        ("script", {"doc_desc": {"idno": "example_idno"}}),
        ("table", {"table_description": {"title_statement": {"idno": "example idno", "title": "example title"}}}),
        (
            "indicator",
            {
                "idno": "GB123",
                "series_description": {
                    "idno": "string",
                    "doi": "string",
                    "name": "Gordons Test",
                    "display_name": "string",
                },
            },
        ),
        (
            "indicators_db",
            {"database_description": {"title_statement": {"idno": "example_idno", "title": "example_title"}}},
        ),
        (
            "microdata",
            {
                "study_desc": {
                    "title_statement": {"idno": "1", "title": "microdata1"},
                    "study_info": {"nation": [{"name": "nation_name"}]},
                }
            },
        ),
        ("video", {"video_description": {"idno": "example_idno", "title": "example_title"}}),
    ],
)
def test_metadata_get_for_project(tmpdir, monkeypatch, metadata_editor, metadata_type, metadata):
    # bad project type
    def mock_response(*args, **kwargs):
        return MockResponse(
            http_status_code=200,
            json_data={
                "project": {
                    "type": "unknown",
                    "metadata": metadata,
                }
            },
        )

    # unknown metadata type can't be returned as an object, only as a dict
    monkeypatch.setattr(requests, "request", mock_response)

    def mock_get_metadata_class(*args, **kwargs):
        return metadata_editor._mm._TYPE_TO_SCHEMA[metadata_type]

    monkeypatch.setattr(metadata_editor, "get_metadata_class", mock_get_metadata_class)

    with pytest.raises(TemplateError):
        metadata_editor.metadata.get_for_project(1, output_mode="pydantic")
    with pytest.raises(TemplateError):
        metadata_editor.metadata.get_for_project(1, output_mode="dict")
    with pytest.raises(TemplateError):
        metadata_editor.metadata.get_for_project(1, output_mode="excel")
    ts = metadata_editor.metadata.get_for_project(1, output_mode="dict", template_uid="none")

    def mock_response(*args, **kwargs):
        return MockResponse(
            http_status_code=200,
            json_data={
                "project": {
                    "type": metadata_type,
                    "metadata": metadata,
                }
            },
        )

    monkeypatch.setattr(requests, "request", mock_response)

    # as object
    ts = metadata_editor.metadata.get_for_project(1, output_mode="pydantic")
    assert isinstance(ts, BaseModel), type(ts)

    ts = metadata_editor.metadata.get_for_project(1, output_mode="dict")
    assert isinstance(ts, dict)

    filename = os.path.join(tmpdir, f"metadata_get_for_project_test_{metadata_type}.xlsx")
    metadata_editor.metadata.get_for_project(1, output_mode="excel", filename=filename, title="metadata_get_for_project")


def test_api_client_verbs(monkeypatch, metadata_editor):
    captured = []

    def mock_response(*args, **kwargs):
        captured.append((args, kwargs))
        return MockResponse(http_status_code=200, json_data={"ok": True})

    monkeypatch.setattr(requests, "request", mock_response)

    metadata_editor.api.get("/editor", params={"limit": 1})
    assert captured[-1][0][0] == "get"
    assert captured[-1][0][1].endswith("/editor")
    assert captured[-1][1]["params"]["limit"] == 1

    metadata_editor.api.post("/editor/delete/{}", id="abc-idno")
    assert captured[-1][0][0] == "post"
    assert captured[-1][0][1].endswith("/editor/delete/abc-idno")

    metadata_editor.api.put("/example/{}", id=7, json={"title": "x"})
    assert captured[-1][0][0] == "put"
    assert captured[-1][0][1].endswith("/example/7")
    assert captured[-1][1]["json"]["title"] == "x"

    metadata_editor.api.delete("/collections/{}", id=3)
    assert captured[-1][0][0] == "delete"
    assert captured[-1][0][1].endswith("/collections/3")


def test_generic_api_request_delegates_to_api(monkeypatch, metadata_editor):
    captured = []

    def mock_response(*args, **kwargs):
        captured.append((args, kwargs))
        return MockResponse(http_status_code=200, json_data={"projects": []})

    monkeypatch.setattr(requests, "request", mock_response)
    response = metadata_editor.generic_api_request("get", "/editor", params={"limit": 2})
    assert response == {"projects": []}
    assert captured[0][0][0] == "get"


def test_projects_delete(monkeypatch, metadata_editor):
    captured = []

    def mock_response(*args, **kwargs):
        captured.append((args, kwargs))
        return MockResponse(http_status_code=200, json_data={"status": "success"})

    monkeypatch.setattr(requests, "request", mock_response)
    result = metadata_editor.projects.delete(42)
    assert result["status"] == "success"
    assert captured[0][0][0] == "post"
    assert captured[0][0][1].endswith("/editor/delete/42")


def test_list_collections(monkeypatch, metadata_editor):
    def mock_response(*args, **kwargs):
        return MockResponse(
            http_status_code=200, json_data={"collections": [{"id": 1, "title": "1", "created": "2024-01-01"}]}
        )

    monkeypatch.setattr(requests, "request", mock_response)
    response = metadata_editor.collections.list()
    assert len(response["collections"]) == 1
    assert response["collections"][0]["title"] == "1"

    def mock_response(*args, **kwargs):
        return MockResponse(http_status_code=200, json_data={"collections": []})

    monkeypatch.setattr(requests, "request", mock_response)
    assert metadata_editor.collections.list()["collections"] == []

    def mock_response(*args, **kwargs):
        return MockResponse(http_status_code=200, json_data={})

    monkeypatch.setattr(requests, "request", mock_response)
    assert "collections" not in metadata_editor.collections.list()


def test_get_collection(monkeypatch, metadata_editor):
    def mock_response(*args, **kwargs):
        return MockResponse(
            http_status_code=200, json_data={"collection": {"id": 1, "title": "1", "created": "2024-01-01"}}
        )

    monkeypatch.setattr(requests, "request", mock_response)
    response = metadata_editor.collections.get(id=1)
    assert response["collection"]["title"] == "1"

    def mock_response(*args, **kwargs):
        return MockResponse(http_status_code=200, json_data={})

    monkeypatch.setattr(requests, "request", mock_response)
    assert "collection" not in metadata_editor.collections.get(1)


def test_update_collection(monkeypatch, metadata_editor):
    def mock_response(*args, **kwargs):
        return MockResponse(http_status_code=200)

    monkeypatch.setattr(requests, "request", mock_response)
    metadata_editor.collections.update(id=1, title="New_title", description="new_description")

    with pytest.raises(AssertionError):
        metadata_editor.collections.update(id=1)


def test_collections_delete(monkeypatch, metadata_editor):
    captured = []

    def mock_response(*args, **kwargs):
        captured.append((args, kwargs))
        return MockResponse(http_status_code=200, json_data={"status": "success"})

    monkeypatch.setattr(requests, "request", mock_response)
    result = metadata_editor.collections.delete(42)
    assert result["status"] == "success"
    assert captured[0][0][0] == "post"
    assert captured[0][0][1].endswith("/collections/delete/42")


def test_add_projects_to_collection(monkeypatch, metadata_editor):
    def mock_response(*args, **kwargs):
        return MockResponse(http_status_code=200)

    monkeypatch.setattr(requests, "request", mock_response)

    # id format is invalid
    with pytest.raises(AssertionError):
        metadata_editor.collections.add_projects(1, "invalid", 1)

    with pytest.raises(AssertionError):
        metadata_editor.collections.add_projects(1, "id", "should be int")

    with pytest.raises(AssertionError):
        metadata_editor.collections.add_projects(1, "idno", 1)

    metadata_editor.collections.add_projects(1, "id", 1)
    metadata_editor.collections.add_projects(1, "id", [1])
    metadata_editor.collections.add_projects([1], "id", 1)
    metadata_editor.collections.add_projects([1], "idno", "idno1")
    metadata_editor.collections.add_projects([1], "id", [1, 2])


def test_remove_projects_from_collection(monkeypatch, metadata_editor):
    def mock_response(*args, **kwargs):
        return MockResponse(http_status_code=200)

    monkeypatch.setattr(requests, "request", mock_response)

    metadata_editor.collections.remove_projects(1, "id", 1)


def test_list_projects_in_collection(monkeypatch, metadata_editor):
    def mock_response(*args, **kwargs):
        return MockResponse(
            http_status_code=200,
            json_data={
                "total": 2,
                "limit": 100,
                "projects": [{"id": 1, "title": "title1"}, {"id": 2, "title": "title2"}],
            },
        )

    monkeypatch.setattr(requests, "request", mock_response)

    response = metadata_editor.collections.list_projects_via_editor(1, limit=100)
    assert len(response["projects"]) == 2

    # # call is good, but the number of projects is limited
    # def mock_response(*args, **kwargs):
    #     return MockResponse(
    #         http_status_code=200, json_data={"total": 2, "limit": 1, "projects": [{"id": 1, "title": "title1"}]}
    #     )

    # monkeypatch.setattr(requests, "request", mock_response)
    # with pytest.warns(UserWarning):
    #     metadata_editor.list_projects_in_collection(1, limit=100)


def test_list_templates(monkeypatch, metadata_editor):
    # there are no templates
    def mock_response(*args, **kwargs):
        return MockResponse(http_status_code=200, json_data={})

    monkeypatch.setattr(requests, "request", mock_response)
    assert metadata_editor.templates.list() == {}

    def mock_response(*args, **kwargs):
        return MockResponse(http_status_code=200, json_data={"templates": {}})

    monkeypatch.setattr(requests, "request", mock_response)
    assert metadata_editor.templates.list()["templates"] == {}

    def mock_response(*args, **kwargs):
        return MockResponse(http_status_code=200, json_data={"templates": {"core": []}})

    monkeypatch.setattr(requests, "request", mock_response)
    assert metadata_editor.templates.list()["templates"]["core"] == []

    # has templates
    def mock_response(*args, **kwargs):
        return MockResponse(
            http_status_code=200,
            json_data={
                "templates": {
                    "core": [
                        {
                            "uid": "example",
                            "template_type": "core",
                            "name": "example",
                            "template": "example_template",
                            "default": True,
                        }
                    ]
                }
            },
        )

    monkeypatch.setattr(requests, "request", mock_response)
    actual = metadata_editor._refresh_default_templates_cache()
    assert len(actual) == 1
    assert actual.iloc[0].uid == "example"


def test_ensure_template_cached(monkeypatch, metadata_editor):
    def mock_response(*args, **kwargs):
        return MockResponse(http_status_code=200, json_data={})

    monkeypatch.setattr(requests, "request", mock_response)
    with pytest.raises(KeyError):
        metadata_editor._ensure_template_cached("example")

    def mock_response(*args, **kwargs):
        return MockResponse(
            http_status_code=200,
            json_data={
                "result": {
                    "uid": "example",
                    "name": "example name",
                    "data_type": "microdata",
                    "template": {},
                }
            },
        )

    monkeypatch.setattr(requests, "request", mock_response)
    actual = metadata_editor._ensure_template_cached("example")
    assert actual.name == "example name"


def test_set_template_for_collection(monkeypatch, metadata_editor):
    def mock_response(*args, **kwargs):
        return MockResponse(
            http_status_code=200,
            json_data={
                "status": "success",
                "result": {"updated": [{"id": "1607", "type": "survey"}, {"id": "1502", "type": "survey"}]},
            },
        )

    monkeypatch.setattr(requests, "request", mock_response)
    metadata_editor.collections.set_template(1, "example_uid", "survey")


def test_get_resources_by_id(monkeypatch, metadata_editor):
    def mock_response(*args, **kwargs):
        return MockResponse(
            http_status_code=200,
            json_data={
                "resources": [
                    {
                        "id": 1,
                        "sid": "sid1",
                        "dctype": "Report",
                        "title": "Report Title",
                        "subtitle": "Subtitle",
                        "author": "Author Name",
                        "filename": "report.pdf",
                        "dcformat": "pdf",
                    }
                ]
            },
        )

    monkeypatch.setattr(requests, "request", mock_response)
    resources = metadata_editor.resources.list(1)
    assert len(resources["resources"]) == 1
    assert resources["resources"][0]["title"] == "Report Title"

    def mock_response(*args, **kwargs):
        return MockResponse(http_status_code=200, json_data={"resources": []})

    monkeypatch.setattr(requests, "request", mock_response)
    assert metadata_editor.resources.list(1)["resources"] == []

    def mock_response(*args, **kwargs):
        return MockResponse(http_status_code=200, json_data={})

    monkeypatch.setattr(requests, "request", mock_response)
    assert "resources" not in metadata_editor.resources.list(1)


@pytest.mark.parametrize(
    "dctype, title, author, filename, should_raise",
    [
        ("txt", "file1.txt", "Author1", None, False),  # No file upload
        ("pdf", "file2.pdf", "Author2", None, False),  # No file upload
        ("txt", "file3.txt", "Author3", None, False),  # No file upload
        ("pdf", "file4.pdf", "Author4", "tempfile.pdf", False),  # Valid file upload
    ],
)
def test_create_update_delete_resource(
    monkeypatch, metadata_editor, tmpdir, dctype, title, author, filename, should_raise
):
    def mock_response(*args, **kwargs):
        return MockResponse(http_status_code=200, json_data={"resource": {"id": 1}})

    monkeypatch.setattr(requests, "request", mock_response)

    if filename:
        temp_file = tmpdir.join(filename)
        temp_file.write("dummy content")
        filename = str(temp_file)

    if should_raise:
        with pytest.raises(ValidationError):
            metadata_editor.resources.create(
                project_id=1, dctype=dctype, title=title, author=author, file_path=filename
            )
    else:
        response = metadata_editor.resources.create(
            project_id=1, dctype=dctype, title=title, author=author, file_path=filename
        )
        assert int(response["resource"]["id"]) == 1

    if should_raise:
        with pytest.raises(ValidationError):
            metadata_editor.resources.update(
                project_id=1, resource_id=1, dctype=dctype, title=title, author=author, file_path=filename
            )
    else:
        metadata_editor.resources.update(
            project_id=1, resource_id=1, dctype=dctype, title=title, author=author, file_path=filename
        )

    def mock_delete_response(*args, **kwargs):
        return MockResponse(http_status_code=200)

    monkeypatch.setattr(RequestsWithSpecificErrors, "post_request", mock_delete_response)
    metadata_editor.resources.delete(project_id=1, resource_id=1)
