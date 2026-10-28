# Indicators: data structures, data, notes and publishing

How to load indicator data into the Metadata Editor and publish it to NADA from Python.

An indicator project has three parts:

- **Metadata:** title, definition, sources, and so on (`me.metadata`, see [metadata workflows](metadata-workflows.md)).
- **Data structure (DSD):** the columns of the data and their roles. It lives in the **registry** (`me.data_structures`) and is **bound** to projects; several indicator projects can share one DSD.
- **Data:** one long CSV, which can hold several indicators. Each project imports the rows whose `indicator_id` column matches its **indicator ID value**.

```python
import os
from pymetadataeditor import MetadataEditor

me = MetadataEditor(os.getenv("METADATA_API_URL"), os.getenv("METADATA_API_KEY"), timeout=600)
```

## 1. Create a data structure from a CSV

`create_from_csv` reads the header and builds the components:

- **Roles** for common names: `INDICATOR_ID`, `INDICATOR_NAME`, `TIME_PERIOD`, `OBS_VALUE`, `REF_AREA` (geography) and `FREQ` (periodicity). Override them with `roles`.
- `X` + `X_LABEL`: a **codelist** built from the code/label pair.
- `footnote_columns`: columns that hold **note IDs** (`display_role="footnote"`, no codelist).
- `label_columns="attribute"` also keeps the label columns as attributes after their code column (labels stored with the data).

```python
ds = me.data_structures.create_from_csv(
    name="EDUCATION", agency="MYORG", version="1.0.0", title="Education indicators",
    csv_path="data.csv", footnote_columns=["NOTE_ID"],
)
print(ds["structure_id"], ds["validation"]["validation"]["valid"])
```

Preview first with `dry_run=True`, or only build the payload with `pymetadataeditor.components_from_csv(...)` and pass it to
`me.data_structures.import_components_csv(structure_id, components, csv_path=..., dry_run=True)`.

Other calls: `list`, `get`, `get_by_identity`, `validate`, `add_component`, `update_component` (e.g. `display_role`, `sort_order`), `delete_component`, `import_json`, `export`, `import_sdmx`.

## 2. Load data (and notes)

```python
project = me.projects.create("indicator", {"idno": "EDU_NER", "series_description": {"idno": "EDU_NER", "name": "Net enrolment rate"}})

report = me.indicators.load_csv(
    project["id"], "data.csv",
    indicator_id_value="EDU_NER",          # rows of this indicator
    data_structure_id=ds["structure_id"],  # bind (once)
    notes_csv="notes.csv",                 # optional: note text
)
report["import"]["data_notes"]   # notes read from text columns, generated IDs, checks
report["notes_check"]            # {valid, errors, warnings, unknown, unused, ...}
```

`load_csv` binds the DSD, sets the indicator ID value, uploads and checks the CSV (large files use a resumable upload), imports the data, imports the notes and checks the note references. The single steps are `bind`, `update_binding`, `prepare_data` and `import_data`.

- One file, many indicators: `me.indicators.load_many("data.csv", {"EDU_NER": 101, "EDU_GER": 102})`.
- From pandas: `me.indicators.load_dataframe(project_id, df, indicator_id_value="EDU_NER")`.
- Background job (large files): `upload_id = me.uploads.upload("data.csv")`, then `me.jobs.import_indicator_data_and_wait(project_id, upload_id, "EDU_NER")`.

## 3. Notes

Cells reference notes by ID in a footnote column (several separated by `;`, e.g. `N03;N04`). The text is stored once per note in the project's **Data notes**. Notes with `scope = table` apply to the whole indicator.

Ways to provide the text:

| Source | How |
|---|---|
| Notes CSV (`note_id, note`; optional `indicator_id, scope, column`) | `me.indicators.notes.import_csv(project, csv_path="notes.csv", dry_run=True)` |
| Text columns in the data CSV | `NOTE_ID_LABEL` (and `NOTE_ID_LABEL2`… by position), or one `NOTE_ID_LABEL` with texts separated by `\|\|`. If the CSV has text but no `NOTE_ID`, the IDs (`N01`, `N02`…) are generated on import. |
| Python | `me.indicators.notes.add(project, "N01", "Text", column="NOTE_ID")`, `notes.remove`, `notes.set` |

Check references: `me.indicators.notes.check(project)`. An unknown ID is an error; a note used in another column, an unused note, or a table note used in cells is a warning.

## 4. Look at the data

```python
me.indicators.data_rows(project_id, limit=20, filters={"REF_AREA": ["XAL"]})
me.indicators.chart_data(project_id, geography=["XAL", "XBO"], dimensions={"SEX": ["_T"]})  # with notes
me.indicators.export_data(project_id, "export.csv")   # DSD columns, DSD order
```

## 5. Publish to NADA

```python
me.indicators.publish(
    "EDU_NER", catalog_connection_id=1,
    metadata_options={"published": 1, "access_policy": "open"},
)
```

This publishes the metadata, then the data structure, then the data. The data structure is re-imported only when it differs from NADA's copy (`dsd_force=True` re-imports anyway; re-importing flags every NADA study on that structure for re-sync). For the background job, use `me.jobs.publish_to_nada(..., publish_dsd=True, dsd_overwrite=True, publish_indicator_data=True)`.

## 6. Preparing data with pandas (`pymetadataeditor.tidy`)

```python
from pymetadataeditor import tidy

long = tidy.wide_to_long(wide, id_vars=["Country", "Sex"])            # one row per observation
long = tidy.split_value_flags(long)                                    # "12.3 e [1]" -> OBS_VALUE, OBS_STATUS, NOTE_MARKERS
long = tidy.markers_to_note_ids(long, {"[1]": "N01", "[2]": "N02"})    # markers -> NOTE_ID
long = tidy.add_labels(long, {"REF_AREA": {"XAL": "Aldoria"}})         # REF_AREA_LABEL next to REF_AREA
tidy.check_observation_key(long, ["REF_AREA", "Sex", "TIME_PERIOD"])  # duplicates
tidy.write_notes_csv({"N01": "Census year."}, "notes.csv", indicator_id="EDU_NER")
```

## Errors

API failures raise `pymetadataeditor.ApiError` (a `requests` `HTTPError`) with `status_code`, `message` and `errors` (e.g. the validation errors of a DSD or notes import).
