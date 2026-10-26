"""Live integration test for indicator data, DSDs and notes against a Metadata Editor instance.

Environment:
    API_URL, API_KEY          Metadata Editor API (e.g. http://localhost/metadata-editor/index.php/api)
    NOTES_TEST_DIR            folder with the notes test data (data.csv, data_with_note_text.csv, notes.csv)
    NADA_CONNECTION_ID        optional: also publish to this catalog connection

Run: pytest tests/integration_indicators_test.py -s
"""

import csv
import os
import time

import pytest

from pymetadataeditor import ApiError, MetadataEditor

API_URL = os.getenv("API_URL")
API_KEY = os.getenv("API_KEY")
DATA_DIR = os.getenv("NOTES_TEST_DIR", "")
NADA_CONNECTION_ID = os.getenv("NADA_CONNECTION_ID")

pytestmark = pytest.mark.skipif(
    not (API_URL and API_KEY and os.path.isdir(DATA_DIR)), reason="API_URL, API_KEY and NOTES_TEST_DIR are required"
)


@pytest.fixture(scope="module")
def me():
    return MetadataEditor(API_URL, API_KEY, allow_http=API_URL.startswith("http:"), verify_ssl=False, timeout=600)


def test_indicator_workflow_with_notes(me, tmp_path):
    stamp = time.strftime("%Y%m%d%H%M%S")
    data_csv = os.path.join(DATA_DIR, "data.csv")

    # 1. DSD from the CSV header: codelists from code/label pairs, footnote columns flagged
    created = me.data_structures.create_from_csv(
        name=f"PY_TEST_{stamp}", agency="TRN", version="1.0.0", title="pymetadataeditor test DSD",
        csv_path=data_csv, footnote_columns=["NOTE_ID", "SOURCE_NOTE_ID"], roles={"COMMENT_OBS": "annotation"},
    )
    structure_id = created["structure_id"]
    assert created["validation"]["validation"]["valid"] is True
    components = {c["name"]: c for c in me.data_structures.components(structure_id)}
    assert components["NOTE_ID"].get("display_role") == "footnote"

    # 2. Project
    idno = f"PY_TEST_LIT_{stamp}"
    project = me.projects.create("indicator", {"idno": idno, "series_description": {"idno": idno,
                                                                                    "name": "pymetadataeditor test"}})
    project_id = int(project["id"])

    try:
        # 3. Data (with a note text column) + notes CSV in one call
        report = me.indicators.load_csv(
            project_id, os.path.join(DATA_DIR, "data_with_note_text.csv"), indicator_id_value="TRN_LIT_RATE",
            data_structure_id=structure_id, notes_csv=os.path.join(DATA_DIR, "notes.csv"),
        )
        assert report["import"]["status"] == "success"
        from_csv = report["import"]["data_notes"]["from_data_csv"]
        assert sorted(from_csv["added"]) == ["N01", "N03", "N04"]
        assert report["notes_import"]["summary"]["added"] == ["N02", "N05", "S01", "T01"]
        assert report["notes_check"]["valid"] is True
        assert report["notes_check"]["unused"] == ["N05"]

        # 4. Chart data: noted missing values kept, note text and table notes returned
        chart = me.indicators.chart_data(project_id, geography=["XAL", "XBO", "XCA"],
                                         dimensions={"SEX": ["F", "M", "_T"]})["data"]
        assert len(chart["records"]) == 44
        assert sorted(chart["notes"]) == ["N01", "N02", "N03", "N04", "S01"]
        assert [t["id"] for t in chart["table_notes"]] == ["T01"]

        # 5. Export: DSD columns in DSD order, no internal columns
        out = me.indicators.export_data(project_id, str(tmp_path / "export.csv"))
        with open(out, newline="", encoding="utf-8") as handle:
            header = next(csv.reader(handle))
        assert header[0] == "INDICATOR_ID" and not any(h.startswith("_ts_") for h in header)

        # 6. Notes editing through the project metadata
        me.indicators.notes.add(project_id, "N77", "Added from Python", column="NOTE_ID")
        assert "N77" in [n["id"] for n in me.indicators.notes.list(project_id)["notes"]]
        me.indicators.notes.remove(project_id, "N77")
        assert "N77" not in [n["id"] for n in me.indicators.notes.list(project_id)["notes"]]

        # 7. Structured errors
        with pytest.raises(ApiError):
            me.indicators.bind(project_id, data_structure_id=99999999)

        # 8. Optional publish
        if NADA_CONNECTION_ID:
            published = me.indicators.publish(
                idno, int(NADA_CONNECTION_ID), metadata_options={"published": 1, "access_policy": "open"}
            )
            assert published["metadata"]["status"] == "success"
            assert published["dsd"]["status"] in ("success", "skipped")
            assert published["data"]["status"] == "success"
    finally:
        me.projects.delete(project_id)
