# LLM-assisted metadata

Use a large language model to draft or augment metadata from documents, URLs, and other sources.

Setup (same as the [README](../README.md#quick-start)):

```python
from pymetadataeditor import MetadataEditor
import os

me = MetadataEditor(
    api_url=os.getenv("METADATA_API_URL"),
    api_key=os.getenv("METADATA_API_KEY"),
    verify_ssl=False,
)
openai_key = os.getenv("OPENAI_API_KEY")  # or Azure / other provider per your config
```

## Supported metadata types

Automatic drafting works for types such as:

- microdata (survey)
- geospatial
- indicator (timeseries)
- document
- script
- video

## Supported sources

- PDF, Word, Excel, PowerPoint
- Plain text, CSV, JSON, XML
- ZIP archives
- Images
- Web URLs

## Draft metadata from files

```python
docs = [
    "path/to/study_report.pdf",
    "path/to/questionnaire.pdf",
]

draft = me.draft_metadata_from_files(
    llm_api_key=openai_key,
    files=docs,
    metadata_type_or_template_uid="microdata",
    output_mode="pydantic",
    metadata_producer_organization="Your organization name",
)

draft.pretty_print()
```

## Draft from a URL

```python
draft = me.draft_metadata_from_files(
    llm_api_key=openai_key,
    files=["https://data.worldbank.org/indicator/NY.GDP.MKTP.CD"],
    metadata_type_or_template_uid="indicator",
    output_mode="pydantic",
    metadata_producer_organization="Your organization name",
)
```

## After drafting

Convert format or export:

```python
as_dict = me.change_mode_or_template(draft, output_mode="dict")
me.save_metadata_to_excel(draft, "draft_metadata.xlsx")
```

Log to the Metadata Editor:

```python
project_id = me.metadata.create(
    draft,
    metadata_type_or_template_uid="microdata",
)
```

## Augment existing metadata

Load a project, then enrich it from additional sources:

```python
existing = me.metadata.get_for_project(project_id, output_mode="pydantic")

augmented = me.augment_metadata_from_files(
    input_metadata=existing,
    llm_api_key=openai_key,
    files=["https://example.org/full-report.pdf"],
    output_mode="pydantic",
    metadata_producer_organization="Your organization name",
    prefix="<AI>",  # marks fields added by the LLM
)

me.metadata.update(project_id, augmented)
```

## Providers

The tool supports OpenAI-compatible APIs and can be configured for Azure OpenAI or local models (e.g. Ollama), depending on your environment. See method docstrings on `draft_metadata_from_files` and `augment_metadata_from_files` for parameters.

## Related guides

- [Metadata workflows (outlines, Pydantic, Excel)](metadata-workflows.md)
- [Migrating from v1 API](../legacy-migration.MD)
