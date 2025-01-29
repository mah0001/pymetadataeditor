# pyMetadataEditor

A tool connected to Metadata Editor for creating, editing and managing metadata for microdata, indicators, geospatial data, documents, scripts, images and videos.

# How to use pyMetadataEditor


```python
from pymetadataeditor import MetadataEditor
import os
```



```python
your_api_key = os.getenv("API_KEY")
api_url = os.getenv("API_URL")
me = MetadataEditor(api_url=api_url, api_key=your_api_key, verify_ssl=False)
```

## Listing your projects


```python
me.list_projects(limit=8)
```

<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>type</th>
      <th>idno</th>
      <th>study_idno</th>
      <th>title</th>
      <th>abbreviation</th>
      <th>nation</th>
      <th>year_start</th>
      <th>year_end</th>
    </tr>
    <tr>
      <th>id</th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>1003</th>
      <td>document</td>
      <td>12345</td>
      <td>DOC_001</td>
      <td>Sample Document 1</td>
      <td>SD1</td>
      <td>Example Nation</td>
      <td>2020</td>
      <td>2025</td>
    </tr>
    <tr>
      <th>1002</th>
      <td>survey</td>
      <td>67890</td>
      <td>SURVEY_002</td>
      <td>Sample Survey 2</td>
      <td>SS2</td>
      <td>Example Nation</td>
      <td>2019</td>
      <td>2024</td>
    </tr>
    <tr>
      <th>1001</th>
      <td>timeseries</td>
      <td>54321</td>
      <td>TS_003</td>
      <td>Time Series 3</td>
      <td>TS3</td>
      <td>Another Nation</td>
      <td>2021</td>
      <td>2026</td>
    </tr>
  </tbody>
</table>
</div>




## Creating a new indicator project


```python
demo_name = "GB20241030_demo"
```


```python
series_description = {
                        "idno": demo_name,
                        "doi": "V1",
                        "name": "Version 1",
                        "display_name": "Version 1"
                     }

indicator_id = me.create_project_log({"idno": demo_name, "series_description": series_description}, "indicator")
```


# Starting with outlines

The metadata can be both large and hierarchical. Starting with a skeleton outline makes things easier.

Outlines are available in three modes - dictionary, pydantic model and as an Excel file.

## Dictionaries
Dictionaries are created like so:


```python
indicator_dict = me.make_metadata_outline('indicator', output_mode='dict')
indicator_dict
```




    {'metadata_information': {'title': None,
      'idno': None,
      'producers': [{'name': '', 'abbr': None, 'affiliation': None, 'role': None}],
      'prod_date': None,
      ...
        'email': None,
        'telephone': None,
        'uri': None}]},
     'tags': [{'tag': None, 'tag_group': None}]}


## Pydantic

Pydantic is a nice python library for defining and validating data schemas. An outline for the indicator schema can be created like so:


```python
indicator_pydantic = me.make_metadata_outline('indicator', 'pydantic')
indicator_pydantic
```


giving

    IHSN_INDICATOR_1-0_Template_v01_EN(metadata_information=metadata_information(title=None, idno=None, producers=[Producer(name='', abbr=None, affiliation=None, role=None)], prod_date=None, ...



It can be updated using dot notation, for example:


```python
indicator_pydantic.metadata_information.producers[0].name = "example_producer"
indicator_pydantic
```


giving

    IHSN_INDICATOR_1-0_Template_v01_EN(metadata_information=metadata_information(title=None, idno=None, producers=[Producer(name='example_producer', abbr=None, affiliation=None, role=None)], prod_date=None, ...

## Excel

Finally, a nicely formatted Excel file can be created into which the metadata can be written, with the name of the metadata type or of the default template used as the filename if no filename is explicitly given.


```python
outline_filename = me.make_metadata_outline('indicator', 'excel')
```

And then read back in from Excel like so:

```python
indicator_excel = me.read_metadata_from_excel(outline_filename)
```

## Retreiving existing metadata

Likewise, existing projects can be downloaded as either dictionaries, pydantic models or as excel spreadsheets.

Asking for the metadata as a pydantic object

```python
demo_pydantic = me.get_project_metadata_by_id(indicator_id, 'pydantic')
demo_pydantic
```

which gives:

    IHSN_INDICATOR_1-0_Template_v01_EN(metadata_information=metadata_information(title=None, idno=None, producers=[Producer(name='', abbr=None, affiliation=None, role=None)], prod_date=None, ...

# Automatic Metadata Creation and Augmentation from Sources

We can use a Large Language Model to make a first draft of metadata from a source document or documents.

We can create metadata from source files such as:
- pdfs
- word
- excel
- powerpoint
- text files
- csv
- XML
- ZIP files
- Images




```python
docs = ["survey_records/cambodia/cambodia_lsms_basic_information_document.pdf", "survey_records/cambodia/cambodia_living_standards_measurement_study_plus_manual_english.pdf"]

example = me.draft_metadata_from_files(openai_api_key=openai_key, 
                                       files=docs, 
                                       metadata_type_or_template_uid='microdata',
                                       output_mode='pydantic',
                                       metadata_producer_organization="The World Bank Group, DEC - Development Data Group"
                                       )
```

The files are read in and sent to the LLM for processing. 

    Read in survey_records/cambodia/cambodia_lsms_basic_information_document.pdf, running token count is 6373
    Read in survey_records/cambodia/cambodia_living_standards_measurement_study_plus_manual_english.pdf, running token count is 24901
    Sending to OpenAI, this may take a few minutes...

We can then view the new metadata
```python
example.pretty_print()
```
which gives

<pre style="white-space:pre;overflow-x:auto;line-height:normal;font-family:Menlo,'DejaVu Sans Mono',consolas,'Courier New',monospace">IHSN_DDI_2-<span style="color: #800080; text-decoration-color: #800080; font-weight: bold">5_Template_v01_EN</span><span style="font-weight: bold">(</span>
    <span style="color: #808000; text-decoration-color: #808000">doc_desc</span>=<span style="color: #800080; text-decoration-color: #800080; font-weight: bold">doc_desc</span><span style="font-weight: bold">(</span>
        <span style="color: #808000; text-decoration-color: #808000">producers</span>=<span style="font-weight: bold">[</span>
            <span style="color: #800080; text-decoration-color: #800080; font-weight: bold">Producer</span><span style="font-weight: bold">(</span>
                <span style="color: #808000; text-decoration-color: #808000">name</span>=<span style="color: #008000; text-decoration-color: #008000">'The World Bank Group, DEC - Development Data Group'</span>,
                <span style="color: #808000; text-decoration-color: #808000">abbr</span>=<span style="color: #008000; text-decoration-color: #008000">'WBG'</span>,
                <span style="color: #808000; text-decoration-color: #808000">affiliation</span>=<span style="color: #008000; text-decoration-color: #008000">'World Bank'</span>,
                <span style="color: #808000; text-decoration-color: #808000">role</span>=<span style="color: #008000; text-decoration-color: #008000">'Metadata producer'</span>
            <span style="font-weight: bold">)</span>
        <span style="font-weight: bold">]</span>,
        <span style="color: #808000; text-decoration-color: #808000">prod_date</span>=<span style="color: #008000; text-decoration-color: #008000">'2025-01-28'</span>,
        <span style="color: #808000; text-decoration-color: #808000">idno</span>=<span style="color: #008000; text-decoration-color: #008000">'CAMBODIA_LSMS_PLUS_2019_2020_v01_EN'</span>,
        <span style="color: #808000; text-decoration-color: #808000">version_statement</span>=<span style="color: #800080; text-decoration-color: #800080; font-weight: bold">version_statement</span><span style="font-weight: bold">(</span>
            <span style="color: #808000; text-decoration-color: #808000">version</span>=<span style="color: #008000; text-decoration-color: #008000">'1.0'</span>,
            <span style="color: #808000; text-decoration-color: #808000">version_date</span>=<span style="color: #008000; text-decoration-color: #008000">'2025-01-28'</span>,
            <span style="color: #808000; text-decoration-color: #808000">version_resp</span>=<span style="color: #008000; text-decoration-color: #008000">''</span>,
            <span style="color: #808000; text-decoration-color: #808000">version_notes</span>=<span style="color: #008000; text-decoration-color: #008000">'First draft of the metadata for the Cambodia Living Standards Measurement Study - Plus </span>
<span style="color: #008000; text-decoration-color: #008000">(LSMS+) 2019-20.'</span>
        <span style="font-weight: bold">)</span>
    <span style="font-weight: bold">)</span>,
    ...

<span style="font-weight: bold">)</span>
</pre>




# Contributing
## Setting up the python environment

This library uses Poetry for dependency management (https://python-poetry.org/docs/basic-usage/).

In your python environment run `pip install poetry` then navigate to the pymetadataeditor folder and run `poetry install` or, if that doesn't work, try `python -m poetry install`.

### Development python environment

If you want to make changes to this repo then you also need to install the tools used for development but which aren't used otherwise, for example pytest.

Run:

`poetry install --with dev`
`poetry run pre-commit install`

### Poetry troubleshooting

If you are running on Windows and see errors about numpy installation errors then it could be an issue with Windows file paths. With default settings, file paths that exceed a few hundred characters can cause installation problems. To overcome this you can either

1) enable long path support in Windows (https://learn.microsoft.com/en-us/windows/win32/fileio/maximum-file-path-limitation?tabs=powershell#enable-long-paths-in-windows-10-version-1607-and-later)
2) install python libraries in a folder in the current directory by running `poetry config virtualenvs.in-project true` and then running `poetry install`

## Notes

In keeping with World Bank Group practice, it should be noted that parts of this code base were written with the assistance of ChatGPT.