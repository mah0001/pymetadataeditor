# pyMetadataEditor

A Python client for [Metadata Editor](https://github.com/worldbank/metadata-editor): create, edit, and manage metadata for microdata, indicators, geospatial data, documents, scripts, images, and videos.

## Installation

This project uses [Poetry](https://python-poetry.org/docs/basic-usage/):

```bash
pip install poetry
cd pymetadataeditor
poetry install
```

For development (pytest, pre-commit):

```bash
poetry install --with dev
poetry run pre-commit install
```

## Quick start

```python
from pymetadataeditor import MetadataEditor
import os

me = MetadataEditor(
    api_url=os.getenv("METADATA_API_URL"),   # e.g. https://host/index.php/api
    api_key=os.getenv("METADATA_API_KEY"),
    verify_ssl=False,  # set True when SSL is verified on your server
)
```

### List projects

```python
response = me.projects.list(limit=10)
for project in response["projects"]:
    print(project["id"], project["type"], project["title"])
```

### Create a project (template-aware)

```python
demo_name = "my_indicator_demo"
metadata = {
    "idno": demo_name,
    "series_description": {
        "idno": demo_name,
        "name": "Version 1",
    },
}

project_id = me.metadata.create(
    metadata,
    metadata_type_or_template_uid="indicator",
)
```

### Read metadata back

```python
model = me.metadata.get_for_project(project_id, output_mode="pydantic")
model.pretty_print()
```

## API overview (v2)

Thin clients return **raw API JSON** (`dict`). Workflow helpers on `me.metadata` handle validation and Pydantic/Excel conversion.

| Client | Role |
|--------|------|
| `me.projects` | List, get, create, update, patch, delete projects |
| `me.metadata` | Template-aware create, update, get (dict / pydantic / excel) |
| `me.collections` | Collections and membership |
| `me.templates` | Template CRUD |
| `me.resources` | External resources (reports, questionnaires, files) |
| `me.api` | Generic `get` / `post` / `put` / `delete` for any path |

Methods still on `me` directly include `make_metadata_outline`, `read_metadata_from_excel`, `draft_metadata_from_files`, and related helpers.

**Breaking change:** v1 flat methods (`list_projects`, `create_project_log`, …) were removed. See [legacy-migration.MD](legacy-migration.MD).

### Direct HTTP (`me.api`)

For endpoints without a typed wrapper yet:

```python
me.api.get("/editor", params={"limit": 5})
me.api.post("/collections/add_projects", json={"collections": [1], "id_format": "id", "projects": [101]})
```

POST body styles:

- `json={...}` — JSON API payloads
- `data={...}` — form fields
- `data={...}` + `files={...}` — multipart uploads

Many deletes use **POST** in restricted networks (e.g. `me.projects.delete`, `me.collections.delete`), not HTTP DELETE.

## Guides

- [Metadata workflows](docs/metadata-workflows.md) — outlines, [Pydantic](docs/metadata-workflows.md#pydantic), [Excel](docs/metadata-workflows.md#excel), [retrieving metadata](docs/metadata-workflows.md#retrieving-existing-metadata)
- [LLM-assisted metadata](docs/llm-assisted-metadata.md) — draft and augment from documents and URLs
- [API examples](docs/examples.md) — collections, copying projects, and common tasks
- [Migrating from v1](legacy-migration.MD) — old → new method mapping
- [API reference](docs/API_Reference.md) — regenerate with `python make_docs.py`

## Contributing

### Poetry troubleshooting (Windows)

If NumPy or path-length errors occur:

1. Enable [long paths in Windows](https://learn.microsoft.com/en-us/windows/win32/fileio/maximum-file-path-limitation?tabs=powershell#enable-long-paths-in-windows-10-version-1607-and-later), or
2. Run `poetry config virtualenvs.in-project true` then `poetry install`

### Tests

```bash
poetry run pytest tests/test_interface.py -q
```

### API documentation

```bash
python make_docs.py
```

## Notes

Parts of this codebase were written with the assistance of ChatGPT, in keeping with World Bank Group practice.
