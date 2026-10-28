# Metadata workflows

How to work with metadata outlines, Pydantic models, Excel, and reading existing projects.

These methods live on `MetadataEditor` (`me`). For creating and loading projects in the database, use `me.metadata` (see [Quick start](../README.md#quick-start) in the README).

## Contents

- [Metadata outlines](#metadata-outlines)
- [Dictionaries](#dictionaries)
- [Pydantic](#pydantic)
- [Excel](#excel)
- [Retrieving existing metadata](#retrieving-existing-metadata)

---

## Metadata outlines

Metadata is often large and hierarchical. Starting from a skeleton outline makes editing easier.

Outlines are available in three modes: **dictionary**, **Pydantic model**, and **Excel file**.

```python
from pymetadataeditor import MetadataEditor
import os

me = MetadataEditor(
    api_url=os.getenv("METADATA_API_URL"),
    api_key=os.getenv("METADATA_API_KEY"),
    verify_ssl=False,
)
```

---

## Dictionaries

```python
indicator_dict = me.make_metadata_outline("indicator", output_mode="dict")
```

You get a nested `dict` with `None` placeholders for empty fields, ready to fill in before calling `me.metadata.create(...)`.

---

## Pydantic

[Pydantic](https://docs.pydantic.dev/) models provide validation and IDE-friendly attribute access.

```python
indicator_pydantic = me.make_metadata_outline("indicator", output_mode="pydantic")
```

Update fields with dot notation:

```python
indicator_pydantic.metadata_information.producers[0].name = "example_producer"
```

When satisfied, log to the Metadata Editor:

```python
project_id = me.metadata.create(
    indicator_pydantic,
    metadata_type_or_template_uid="indicator",
)
```

---

## Excel

Create a formatted Excel template (filename defaults to the metadata type or template name):

```python
outline_filename = me.make_metadata_outline("indicator", output_mode="excel")
```

Edit the file, then read it back:

```python
indicator_from_excel = me.read_metadata_from_excel(outline_filename, output_mode="pydantic")
```

Save an in-memory model to Excel:

```python
me.save_metadata_to_excel(indicator_pydantic, "my_metadata.xlsx")
```

Convert between representations:

```python
as_dict = me.change_mode_or_template(indicator_pydantic, output_mode="dict")
```

---

## Retrieving existing metadata

Download metadata for a project you already created:

```python
# Pydantic model (template-aware validation)
demo_pydantic = me.metadata.get_for_project(project_id, output_mode="pydantic")

# Plain dictionary
demo_dict = me.metadata.get_for_project(project_id, output_mode="dict")

# Excel file on disk
me.metadata.get_for_project(
    project_id,
    output_mode="excel",
    filename="exported_metadata.xlsx",
    title="My export",
)
```

Update after editing:

```python
me.metadata.update(project_id, updated_pydantic_model)
```

For raw project JSON from the API (no template workflow), use `me.projects.get_json(project_id)`.
