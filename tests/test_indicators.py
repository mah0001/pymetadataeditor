"""Unit tests (mocked HTTP) for uploads, data structures, codelists, indicators, notes and tidy helpers."""

import json
from typing import Any, Dict, List

import pandas as pd
import pytest
import requests

from pymetadataeditor import ApiError, MetadataEditor, components_from_csv
from pymetadataeditor import requester as requester_module
from pymetadataeditor import tidy


class FakeResponse:
    def __init__(self, status: int = 200, body: Any = None, text: str = "", content: bytes = b""):
        self.status_code = status
        self._body = body
        self.text = text if text else (json.dumps(body) if body is not None else "")
        self._content = content

    def json(self):
        if self._body is None:
            raise ValueError("no json")
        return self._body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError(f"{self.status_code}", response=self)

    def iter_content(self, chunk_size=1):
        yield self._content


class Calls(list):
    """Recorded requests; ``queue`` holds the responses to return (default: a success body)."""

    queue: List[FakeResponse]


@pytest.fixture
def calls(monkeypatch):
    """Record requests; responses come from a queue or a default success body."""
    recorded = Calls()
    queue: List[FakeResponse] = []

    def fake_request(method, url, **kwargs):
        files = kwargs.get("files")
        if files:
            kwargs["files"] = {k: (v[0], v[1]) if isinstance(v, tuple) else getattr(v, "name", "file")
                               for k, v in files.items()}
        recorded.append({"method": method, "url": url, **kwargs})
        return queue.pop(0) if queue else FakeResponse(body={"status": "success"})

    monkeypatch.setattr(requester_module.requests, "request", fake_request)
    recorded.queue = queue
    return recorded


@pytest.fixture
def me():
    return MetadataEditor("http://editor.test/index.php/api", "key", allow_http=True)


def _path(call):
    return call["url"].split("/index.php/api/", 1)[1]


# ── request layer ────────────────────────────────────────────────────────────


def test_api_error_parses_message_and_validation_errors(me, calls):
    errors = [{"path": "components[0].name", "message": "Required."}]
    calls.queue.append(FakeResponse(400, {"status": "failed", "message": "VALIDATION_FAILED: " + json.dumps(errors)}))
    with pytest.raises(ApiError) as info:
        me.data_structures.validate(5)
    assert info.value.status_code == 400
    assert info.value.message == "VALIDATION_FAILED"
    assert info.value.errors == errors
    assert isinstance(info.value, requests.exceptions.HTTPError)


def test_api_error_keeps_errors_list(me, calls):
    calls.queue.append(FakeResponse(400, {"status": "failed", "message": "Notes CSV has errors", "errors": ["Line 3"]}))
    with pytest.raises(ApiError) as info:
        me.indicators.notes.import_csv(9, upload_id="u1")
    assert info.value.errors == ["Line 3"]


def test_timeout_default_and_override(me, calls):
    me._apinterface.timeout = 30
    me.indicators.binding(9)
    me.indicators.import_data(9, timeout=600)
    assert calls[0]["timeout"] == 30
    assert calls[1]["timeout"] == 600


# ── uploads ──────────────────────────────────────────────────────────────────


def test_upload_sends_chunks(me, calls, tmp_path):
    f = tmp_path / "data.csv"
    f.write_bytes(b"x" * 25)
    calls.queue.append(FakeResponse(body={"status": "success", "upload_id": "abc"}))
    upload_id = me.uploads.upload(str(f), chunk_size=10)
    assert upload_id == "abc"
    assert _path(calls[0]) == "uploads/init"
    assert calls[0]["json"] == {"filename": "data.csv", "total_size": 25, "total_chunks": 3, "chunk_size": 10}
    chunks = [c for c in calls if _path(c).startswith("uploads/chunk/")]
    assert [c["data"]["chunk_number"] for c in chunks] == ["0", "1", "2"]
    assert all(_path(c) == "uploads/chunk/abc" for c in chunks)


# ── data structures ──────────────────────────────────────────────────────────


def test_import_components_csv_multipart_payload(me, calls, tmp_path):
    f = tmp_path / "d.csv"
    f.write_text("A,B\n1,2\n")
    comps = [{"name": "A", "column_type": "dimension", "csv_column": "A"}]
    me.data_structures.import_components_csv(5, comps, csv_path=str(f), dry_run=True)
    call = calls[0]
    assert _path(call) == "data_structures/import_components_csv/5"
    payload = json.loads(call["data"]["payload"])
    assert payload["dry_run"] is True and payload["components"] == comps
    assert "file" in call["files"]


def test_import_components_csv_with_upload_id_uses_json(me, calls):
    me.data_structures.import_components_csv(5, [], upload_id="u9", dry_run=False)
    assert calls[0]["json"]["upload_id"] == "u9" and calls[0]["json"]["dry_run"] is False


def test_components_from_csv_roles_codelists_footnotes(tmp_path):
    f = tmp_path / "d.csv"
    f.write_text("INDICATOR_ID,REF_AREA,REF_AREA_LABEL,SEX,SEX_LABEL,TIME_PERIOD,OBS_VALUE,NOTE_ID,OBS_STATUS\n")
    comps = components_from_csv(str(f), footnote_columns=["NOTE_ID"])
    by = {c["name"]: c for c in comps}
    assert [c["name"] for c in comps] == ["INDICATOR_ID", "REF_AREA", "SEX", "TIME_PERIOD", "OBS_VALUE", "NOTE_ID",
                                          "OBS_STATUS"]
    assert by["REF_AREA"]["column_type"] == "geography"
    assert by["REF_AREA"]["codelist"] == {"mode": "from_csv", "code_column": "REF_AREA", "label_column": "REF_AREA_LABEL"}
    assert by["SEX"]["column_type"] == "dimension"
    assert by["NOTE_ID"] == {"name": "NOTE_ID", "column_type": "annotation", "csv_column": "NOTE_ID",
                             "display_role": "footnote"}
    assert by["OBS_STATUS"]["column_type"] == "attribute"
    with_labels = components_from_csv(str(f), label_columns="attribute")
    names = [c["name"] for c in with_labels]
    assert names.index("REF_AREA_LABEL") == names.index("REF_AREA") + 1


def test_components_from_csv_requires_roles(tmp_path):
    f = tmp_path / "d.csv"
    f.write_text("COUNTRY,YEAR,VALUE\n")
    with pytest.raises(ValueError, match="indicator_id"):
        components_from_csv(str(f))
    f.write_text("IND,COUNTRY,YEAR,VALUE\n")
    comps = components_from_csv(
        str(f), roles={"IND": "indicator_id", "COUNTRY": "geography", "YEAR": "time_period", "VALUE": "observation_value"}
    )
    assert [c["column_type"] for c in comps] == ["indicator_id", "geography", "time_period", "observation_value"]


# ── indicators and notes ─────────────────────────────────────────────────────


def test_bind_update_binding_and_idno_paths(me, calls):
    me.indicators.bind("MY IDNO/1", data_structure_id=5)
    me.indicators.update_binding("MY IDNO/1", indicator_id_value="TRN_LIT_RATE")
    assert _path(calls[0]) == "indicator_dsd/bind_global/MY%20IDNO%2F1"
    assert calls[0]["json"] == {"data_structure_id": 5}
    assert calls[1]["json"] == {"indicator_id_value": "TRN_LIT_RATE"}


def test_notes_import_form_fields(me, calls, tmp_path):
    f = tmp_path / "notes.csv"
    f.write_text("note_id,note\nN01,Text\n")
    me.indicators.notes.import_csv(9, csv_path=str(f), dry_run=True, replace=True)
    call = calls[0]
    assert _path(call) == "indicator_dsd/notes_import/9"
    assert call["data"] == {"dry_run": "1", "replace": "1", "delimiter": ","}


def test_notes_set_patches_data_notes(me, calls):
    me.indicators.notes.set(9, [{"id": "N01", "note": "Text", "scope": None}, {"id": "T01", "note": "All", "scope": "table"}])
    call = calls[0]
    assert _path(call) == "editor/patch/timeseries/9"  # project type normalised by ProjectsClient
    patch = call["json"]["patches"][0]
    assert patch["path"] == "/data_notes"
    assert patch["value"] == [{"id": "N01", "note": "Text"}, {"id": "T01", "note": "All", "scope": "table"}]
    with pytest.raises(ValueError):
        me.indicators.notes.set(9, [{"id": "N01;N02", "note": "x"}])


def test_export_data_streams_to_file(me, calls, tmp_path):
    calls.queue.append(FakeResponse(200, None, content=b"A,B\n1,2\n"))
    out = me.indicators.export_data(9, str(tmp_path / "out.csv"))
    assert open(out, "rb").read() == b"A,B\n1,2\n"
    assert calls[0]["stream"] is True


def test_publish_resolves_numeric_id_and_steps(me, calls):
    calls.queue.extend([
        FakeResponse(body={"status": "success", "project": {"id": "9"}}),
        FakeResponse(body={"status": "success"}),
        FakeResponse(body={"dsd": {"status": "skipped"}, "data": None}),
        FakeResponse(body={"dsd": None, "data": {"status": "success"}}),
    ])
    out = me.indicators.publish("TRN_NOTES_TEST_LIT", 2, metadata_options={"published": 1})
    paths = [_path(c) for c in calls]
    assert paths == ["editor/TRN_NOTES_TEST_LIT", "publish/9/2", "publish/indicator/9/2", "publish/indicator/9/2"]
    assert calls[1]["json"] == {"overwrite": "yes", "published": 1}
    assert calls[2]["json"]["publish_dsd"] is True and calls[2]["json"]["dsd_force"] is False
    assert calls[3]["json"]["publish_indicator_data"] is True
    assert out == {"metadata": {"status": "success"}, "dsd": {"status": "skipped"}, "data": {"status": "success"}}


def test_jobs_import_indicator_data_and_publish_dsd_force(me, calls):
    me.jobs.import_indicator_data(9, "u1", "TRN_LIT_RATE")
    me.jobs.publish_to_nada(9, 2, publish_dsd=True, dsd_force=True)
    assert _path(calls[0]) == "jobs/import_indicator_data"
    assert calls[0]["json"]["indicator_value"] == "TRN_LIT_RATE"
    assert calls[1]["json"]["dsd_force"] is True


def test_load_csv_checks_indicator_value(me, calls, tmp_path):
    f = tmp_path / "d.csv"
    f.write_text("INDICATOR_ID\nA\n")
    calls.queue.extend([
        FakeResponse(body={"status": "success"}),  # update_binding
        FakeResponse(body={"status": "success", "indicator_values": [{"value": "A"}]}),  # prepare
    ])
    with pytest.raises(ValueError, match="not found"):
        me.indicators.load_csv(9, str(f), indicator_id_value="B")


# ── tidy ─────────────────────────────────────────────────────────────────────


def test_split_value_flags_and_markers():
    df = pd.DataFrame({"OBS_VALUE": ["12.3 e [1]", "1,234.5", ".. [2]", "n/a", "45p", "7"]})
    out = tidy.split_value_flags(df)
    assert out["OBS_VALUE"].tolist()[:2] == [12.3, 1234.5]
    assert pd.isna(out["OBS_VALUE"][2]) and pd.isna(out["OBS_VALUE"][3])
    assert out["OBS_STATUS"].tolist() == ["E", "A", "O", "O", "P", "A"]
    assert out["NOTE_MARKERS"].tolist() == ["[1]", "", "[2]", "", "", ""]


def test_markers_to_note_ids_with_extra_and_unknown():
    df = pd.DataFrame({"REF_AREA": ["XCA", "XAL"], "NOTE_MARKERS": ["[1]", ""]})
    extra = (df["REF_AREA"] == "XCA").map({True: "N02", False: ""})
    out = tidy.markers_to_note_ids(df, {"[1]": "N01"}, extra=extra)
    assert out["NOTE_ID"].tolist() == ["N01;N02", ""]
    with pytest.raises(ValueError):
        tidy.markers_to_note_ids(pd.DataFrame({"NOTE_MARKERS": ["[9]"]}), {"[1]": "N01"})


def test_wide_to_long_labels_and_key_check(tmp_path):
    wide = pd.DataFrame({"REF_AREA": ["XAL", "XBO"], "2020 ": ["1", "2"], "2021": ["3", "4"]})
    long = tidy.wide_to_long(wide, ["REF_AREA"])
    assert sorted(long["TIME_PERIOD"].unique()) == ["2020", "2021"]
    labelled = tidy.add_labels(long, {"REF_AREA": {"XAL": "Aldoria", "XBO": "Borvania"}})
    assert list(labelled.columns)[:2] == ["REF_AREA", "REF_AREA_LABEL"]
    dup = tidy.check_observation_key(pd.concat([long, long.head(1)]), ["REF_AREA", "TIME_PERIOD"])
    assert len(dup) == 2
    table = tidy.write_notes_csv({"N01": "A note"}, str(tmp_path / "n.csv"), indicator_id="X")
    assert table.to_dict("records") == [{"note_id": "N01", "indicator_id": "X", "scope": "cell", "column": "NOTE_ID",
                                         "note": "A note"}]
