# Basic usage: pyMetadataEditor

Minimal examples for connecting to a Metadata Editor instance, listing projects, inspecting templates and collections, building a metadata outline, and optionally logging a new project.

For deeper workflows, see `examples.ipynb`, `demo.ipynb`, and the [API reference](https://github.com/mah0001/pymetadataeditor/blob/main/docs/API_Reference.md).

## Prerequisites

Set your API URL and key in the environment. The library docstring uses `METADATA_API_URL` and `METADATA_API_KEY`; some demos use `API_URL` and `API_KEY`. The connection cell below checks both.

### Jupyter kernel (fixes `ModuleNotFoundError: pymetadataeditor`)

The notebook must use a Python that has this package and its dependencies installed.

1. In Cursor: **Python: Select Interpreter** (Command Palette) and pick `.venv` under this repo, **or** install into your current interpreter (same path the next cell prints).
2. The base install (indicators, projects, metadata, publishing) has no heavy dependencies. The LLM-assisted metadata features (OpenAI, `tiktoken`, `markitdown`) are an optional extra: `pip install "pymetadataeditor[llm]"`.

One-time setup with Homebrew Python 3.12 (example):

```bash
cd /Volumes/webdev/pymetadataeditor
brew install python@3.12
/opt/homebrew/opt/python@3.12/bin/python3.12 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
python -m ipykernel install --user --name=pymetadataeditor --display-name="Python (pymetadataeditor)"
```

Then choose the **Python (pymetadataeditor)** kernel (or `.venv/bin/python`) for this notebook.

The first code cell below also puts the repo root on `sys.path` so imports work when the working directory is the project root or `demo/`, as long as dependencies are installed in that kernel.


```python
import os
import sys
from pathlib import Path


def _repo_root() -> Path:
    cwd = Path.cwd().resolve()
    for candidate in (cwd, cwd.parent):
        if (candidate / "pymetadataeditor" / "__init__.py").is_file():
            return candidate
    return cwd


ROOT = _repo_root()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

print("Using Python:", sys.executable)
print("Repo root on sys.path:", ROOT)

from pymetadataeditor import MetadataEditor
```

    Using Python: /Volumes/webdev/pymetadataeditor/.venv/bin/python
    Repo root on sys.path: /Volumes/webdev/pymetadataeditor



    ModuleNotFoundError: No module named 'pandas'



```python
api_url = os.getenv("METADATA_API_URL") or os.getenv("API_URL")
api_key = os.getenv("METADATA_API_KEY") or os.getenv("API_KEY")

if not api_url or not api_key:
    raise RuntimeError(
        "Set METADATA_API_URL and METADATA_API_KEY (or API_URL and API_KEY) before running this notebook."
    )

me = MetadataEditor(api_url=api_url, api_key=api_key)
```

## List and count projects

`list_projects` returns a pandas `DataFrame` indexed by internal project `id`.


```python
total = me.count_projects()
print("Total projects:", total)

projects_df = me.list_projects(limit=10, sort_by="updated_desc")
projects_df
```


```python
if len(projects_df) > 0:
    first_id = int(projects_df.index[0])
    summary = me.get_project_by_id(first_id)
    print("Project", first_id, "—", summary.get("title", ""))

    meta = me.get_project_metadata_by_id(first_id, "dict")
    print("Top-level metadata keys:", list(meta.keys())[:12], "..." if len(meta) > 12 else "")
else:
    print("No projects returned for this page; try a larger limit or different filters.")
```

## Templates and collections


```python
templates_df = me.list_templates()
templates_df.head()
```


```python
collections_df = me.list_collections()
collections_df.head()
```

## Metadata outline

Start from a skeleton for a supported type (e.g. `indicator`, `survey`, `document`) or a template UID, in `dict`, `pydantic`, or `excel` form.


```python
outline = me.make_metadata_outline("indicator", "pydantic")
outline.pretty_print()
```

## Thin project API (`ProjectsClient`)

`MetadataEditor` exposes `me.projects` for API-shaped list/get/create responses (dictionaries) alongside the higher-level helpers above.


```python
page = me.projects.list(limit=5)
print("Keys in list response:", sorted(page.keys()))
print("Total from API:", page.get("total"))
```

## Create a project (optional)

Set `CREATE_DEMO_PROJECT` to `True` and change `demo_idno` to a **new, unique** idno before running. This calls `create_project_log` and inserts a real indicator in your catalog.


```python
CREATE_DEMO_PROJECT = False
demo_idno = "REPLACE_WITH_UNIQUE_IDNO"

if CREATE_DEMO_PROJECT:
    series_description = {
        "idno": demo_idno,
        "name": "Usage notebook demo",
        "display_name": "Usage notebook demo",
    }
    new_id = me.create_project_log(
        {"idno": demo_idno, "series_description": series_description},
        "indicator",
    )
    print("Created project internal id:", new_id)
else:
    print("Skipped create (set CREATE_DEMO_PROJECT = True to run).")
```
