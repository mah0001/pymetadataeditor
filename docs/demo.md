# How to use pyMetadataEditor


```python
from pymetadataeditor import MetadataEditor
import os

# show all columns in pandas
import pandas as pd
pd.set_option('display.max_columns', None)
```

## Examples of the interface


```python
your_api_key = os.getenv("API_KEY")
api_url = os.getenv("API_URL")
me = MetadataEditor(api_url=api_url, api_key=your_api_key, verify_ssl=False)
```

### Listing your projects


```python
me.list_projects(limit=2)
```




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
<th>published</th>
<th>created</th>
<th>changed</th>
<th>varcount</th>
<th>created_by</th>
<th>changed_by</th>
<th>is_shared</th>
<th>thumbnail</th>
<th>template_uid</th>
<th>attributes</th>
<th>username</th>
<th>username_cr</th>
<th>collections</th>
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
<th></th>
<th></th>
<th></th>
<th></th>
<th></th>
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
<th>5095</th>
<td>survey</td>
<td>6b609e22-e86f-43f8-92c2-d2fd4920b4aa</td>
<td>zwxL</td>
<td>sial</td>
<td>None</td>
<td>pXmU, PzaQ, iWik...and 2 more</td>
<td>0</td>
<td>0</td>
<td>None</td>
<td>2025-05-23T19:31:51+00:00</td>
<td>2025-05-23T19:31:51+00:00</td>
<td>None</td>
<td>24</td>
<td>24</td>
<td>None</td>
<td>None</td>
<td>954e023b790d8b15433544d85eb6431e</td>
<td>None</td>
<td>Gordon Blackadder</td>
<td>Gordon Blackadder</td>
<td>[]</td>
</tr>
<tr>
<th>5069</th>
<td>survey</td>
<td>96d15eb0-520f-4a8f-90a3-34f391b9ab00</td>
<td>aykI</td>
<td>WVmB</td>
<td>None</td>
<td>pYhT</td>
<td>0</td>
<td>0</td>
<td>None</td>
<td>2025-05-23T19:27:43+00:00</td>
<td>2025-05-23T19:27:43+00:00</td>
<td>None</td>
<td>24</td>
<td>24</td>
<td>None</td>
<td>None</td>
<td>954e023b790d8b15433544d85eb6431e</td>
<td>None</td>
<td>Gordon Blackadder</td>
<td>Gordon Blackadder</td>
<td>[]</td>
</tr>
</tbody>
</table>




```python
me.count_projects()
```




    1789



### Creating a new indicator project


```python
demo_name = "GB20250225_demo"
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


```python
me.list_projects(limit=3, sort_by="updated_desc")
```




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
<th>published</th>
<th>created</th>
<th>changed</th>
<th>varcount</th>
<th>created_by</th>
<th>changed_by</th>
<th>is_shared</th>
<th>thumbnail</th>
<th>template_uid</th>
<th>attributes</th>
<th>username</th>
<th>username_cr</th>
<th>collections</th>
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
<th></th>
<th></th>
<th></th>
<th></th>
<th></th>
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
<th>5096</th>
<td>timeseries</td>
<td>9960d5df-f2f4-477b-98ce-a58e20b829b4</td>
<td>GB20250225_demo</td>
<td>Version 1</td>
<td>None</td>
<td>None</td>
<td>0</td>
<td>0</td>
<td>None</td>
<td>2025-05-23T19:35:14+00:00</td>
<td>2025-05-23T19:35:14+00:00</td>
<td>None</td>
<td>24</td>
<td>24</td>
<td>None</td>
<td>None</td>
<td>timeseries-system-en</td>
<td>{'database_id': None}</td>
<td>Gordon Blackadder</td>
<td>Gordon Blackadder</td>
<td>[]</td>
</tr>
<tr>
<th>5095</th>
<td>survey</td>
<td>6b609e22-e86f-43f8-92c2-d2fd4920b4aa</td>
<td>zwxL</td>
<td>sial</td>
<td>None</td>
<td>pXmU, PzaQ, iWik...and 2 more</td>
<td>0</td>
<td>0</td>
<td>None</td>
<td>2025-05-23T19:31:51+00:00</td>
<td>2025-05-23T19:31:51+00:00</td>
<td>None</td>
<td>24</td>
<td>24</td>
<td>None</td>
<td>None</td>
<td>954e023b790d8b15433544d85eb6431e</td>
<td>None</td>
<td>Gordon Blackadder</td>
<td>Gordon Blackadder</td>
<td>[]</td>
</tr>
<tr>
<th>5069</th>
<td>survey</td>
<td>96d15eb0-520f-4a8f-90a3-34f391b9ab00</td>
<td>aykI</td>
<td>WVmB</td>
<td>None</td>
<td>pYhT</td>
<td>0</td>
<td>0</td>
<td>None</td>
<td>2025-05-23T19:27:43+00:00</td>
<td>2025-05-23T19:27:43+00:00</td>
<td>None</td>
<td>24</td>
<td>24</td>
<td>None</td>
<td>None</td>
<td>954e023b790d8b15433544d85eb6431e</td>
<td>None</td>
<td>Gordon Blackadder</td>
<td>Gordon Blackadder</td>
<td>[]</td>
</tr>
</tbody>
</table>




```python
me.get_project_by_id(indicator_id)
```




    id                                                               5096
    idno                             9960d5df-f2f4-477b-98ce-a58e20b829b4
    type                                                       timeseries
    title                                                       Version 1
    abbreviation...




```python
me.get_project_metadata_by_id(indicator_id, output_mode='dict')
```




    {'series_description': {'idno': 'GB20250225_demo',
      'name': 'Version 1',
      'display_name': 'Version 1'}}



So we've gotten back less than expected. That's because the default template for indicators doesn't include the top level idno or a series_description.display_name. Better to start then with an outline of the actual data we want.

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
      'version_statement': {'version': None,
       'version_date': None,
       'version_notes': None,
       'version_resp': None}},
     'series_description':...



and updated in the usual way:


```python
indicator_dict['metadata_information']['producers'][0]['name'] = "example_producer"
indicator_dict
```




    {'metadata_information': {'title': None,
      'idno': None,
      'producers': [{'name': 'example_producer',
        'abbr': None,
        'affiliation': None,
        'role': None}],
      'prod_date': None,
      'version_statement': {'version': None,
       'version_date': None,
       'version_notes': None,
       'version_resp': Non...



## Pydantic

Pydantic is a nice python library for defining and validating data schemas. An outline for the indicator schema can be created like so:


```python
indicator_pydantic = me.make_metadata_outline('indicator', 'pydantic')
indicator_pydantic
```




    Indicator_Schema_1-0_EN(metadata_information=metadata_information(title=None, idno=None, producers=[Producer(name='', abbr=None, affiliation=None, role=None)], prod_date=None, version_statement=version_statement(version=None, version_date=None, version_notes=None, version_resp=None)), series_descrip...



It can be updated using dot notation, for example:


```python
indicator_pydantic.metadata_information.producers[0].name = "example_producer"
indicator_pydantic
```




    Indicator_Schema_1-0_EN(metadata_information=metadata_information(title=None, idno=None, producers=[Producer(name='example_producer', abbr=None, affiliation=None, role=None)], prod_date=None, version_statement=version_statement(version=None, version_date=None, version_notes=None, version_resp=None))...



### Printing

The pydantic metadata object also contains a helper function for printing metadata:


```python
indicator_pydantic.pretty_print()
```


Indicator_Schema_1-<span style="color: #800080; text-decoration-color: #800080; font-weight: bold">0_EN</span><span style="font-weight: bold">(</span><span style="color: #808000; text-decoration-color: #808000">metadata_information</span>=<span style="color: #800080; text-decoration-color: #800080; font-weight: bold">metadata_information</span><span style="font-weight: bold">(</span><span style="color: #808000; text-decoration-color: #808000">title</span>=<span style="color: #800080; text-decoration-color: #800080; font-style: italic">None</span>,
        <span style="color: #808000; text-decoration-color: #808000">idno</span>=<span style="color: #800080; text-decoration-color: #800080; font-style: italic">None</span>,
        <span style="color: #808000; text-decoration-color: #808000">producers</span>=<span style="font-weight: bold">[</span><span style="color: #800080; text-decoration-color: #800080; font-weight: bold">Producer</span><span style="font-weight: bold">(</span><span style="color: #808000; text-decoration-color: #808000">name</span>=<span style="color: #008000; text-decoration-color: #008000">'example_producer'</span>, <span style="color: #808000; text-decoration-color: #808000">abbr</span>=<span style="color: #800080; text-decoration-color: #800080; font-style: italic">None</span>, <span style="color: #808000; text-decoration-color: #808000">affiliation</span>=<span style="color: #800080; text-decoration-color: #800080; font-style: italic">None</span>, <span style="color: #808000; text-decoration-color: #808000">role</span>=<span style="color: #800080; text-decoration-color: #800080; font-style: italic">None</span><span style="font-weight: bold">)]</span>,
        <span style="color: #808000; text-decoration-color: #808000">prod_date</span>=<span style="color: #800080; text-decoration-color: #800080; font-style: italic">None</span>,
        <span style="color: #808000; text-decoration-color: #808000">version_statement</span>=<span style="color: #800080; text-decoration-color: #800080; font-weight: bold">version_statement</span><span style="font-weight: bold">(</span><span style="color: #808000; text-decoration-color: #808000">version</span>=<span style="color: #800080; text-decoration-color: #800080; font-style: italic">None</span>,
            <span style="color: #808000; text-decoration-color: #808000">version_date</span>=<span style="color: #800080; text-decoration-color: #800080; font-style: italic">None</span>,
            <span style="color: #808000; text-decoration-color: #808000">version_notes</span>=<span style="color: #800080; text-decoration-color: #800080; font-style: italic">None</span>,
            <span style="color: #808000; text-decoration-color: #808000">version_resp</span>=<span style="color: #800080; text-decoration-color: #800080; font-style: italic">None</span><span style="font-weight: bold">)</span><span style="font-weight: bold">)</span>,
    <span style="color: #808000; text-decoration-color: #808000">series_description</span>=<span style="color: #800080; text-decoration-color: #800080; font-weight: bold">series_description</span><span style="font-weight: bold">(</span><span style="color: #808000; text-decoration-color: #808000">idno</span>=<span style="color: #008000; text-decoration-color: #008000">''</span>,
        <span style="color: #808000; text-decoration-color: #808000">alternate_identifiers</span>=<span style="font-weight: bold">[</span><span style="color: #800080; text-decoration-color: #800080; font-weight: bold">Alternate_identifier</span><span style="font-weight: bold">(</span><span style="color: #808000; text-decoration-color: #808000">type</span>=<span style="color: #800080; text-decoration-color: #800080; font-style: italic">None</span>, <span style="color: #808000; text-decoration-color: #808000">identifier</span>=<span style="color: #800080; text-decoration-color: #800080; font-style: italic">None</span>, <span style="color: #808000; text-decoration-color: #808000">database</span>=<span style="color: #800080; text-decoration-color: #800080; font-style: italic">None</span>, <span style="color: #808000; text-decoration-color: #808000">uri</span>=<span style="color: #800080; text-decoration-color: #800080; font-style: italic">None</span>, <span style="color: #808000; text-decoration-color: #808000">notes</span>=<span style="color: #800080; text-decoration-color: #800080; font-style: italic">None</span><span style="font-weight: bold">)</span><span style="font-weight: bold">]</span>,
        <span style="color: #808000; text-decoration-color: #808000">name</span>=...


We can also convert back to a dictionary and we can choose to simplfy which excludes Nones, empty strings, empty lists and empty dictionaries


```python
me.change_mode_or_template(indicator_pydantic, output_mode='dict', simplify=True)
```




    {'metadata_information': {'producers': [{'name': 'example_producer'}]}}



## Excel

Finally, a nicely formatted Excel file can be created into which the metadata can be written, with the name of the metadata type or of the default template used as the filename if no filename is explicitly given.


```python
outline_filename = me.make_metadata_outline('indicator', 'excel')
outline_filename
```




    'Indicator_Schema_1-0_EN_metadata.xlsx'




```python
indicator_excel = me.read_metadata_from_excel(outline_filename)
```


```python
# Tidy up the file
os.remove(outline_filename)
```

## Retreiving existing metadata

Likewise, existing projects can be downloaded as either dictionaries, pydantic models or as excel spreadsheets.


```python
demo_dict = me.get_project_metadata_by_id(indicator_id, output_mode='dict')
demo_dict
```




    {'series_description': {'idno': 'GB20250225_demo',
      'name': 'Version 1',
      'display_name': 'Version 1'}}




```python
demo_pydantic = me.get_project_metadata_by_id(indicator_id, 'pydantic')
demo_pydantic
```




    Indicator_Schema_1-0_EN(metadata_information=metadata_information(title=None, idno=None, producers=[Producer(name='', abbr=None, affiliation=None, role=None)], prod_date=None, version_statement=version_statement(version=None, version_date=None, version_notes=None, version_resp=None)), series_descrip...




```python
excel_filename = demo_name+'.xlsx'
me.get_project_metadata_by_id(indicator_id, output_mode='excel', filename=excel_filename)
```




    'GB20250225_demo.xlsx'



### Updating an existing project

You can create and update projects with metadata as either dictionaries, pydantic models or in Excel files. 


```python
indicator_id
```




    5096




```python
demo_dict
```




    {'series_description': {'idno': 'GB20250225_demo',
      'name': 'Version 1',
      'display_name': 'Version 1'}}




```python
me.update_project_log_by_id(indicator_id, demo_dict)
```


```python
me.update_project_log_by_id(indicator_id, demo_pydantic)
```


```python
me.update_project_log_by_id(indicator_id, excel_filename)
# tidy up the file
os.remove(excel_filename)
```

### Updating with patch updates

You can also update metadata with patch updates. With this method you can add, update, or remove parts of a project's metadata using a single JSON Patch operation.

"JSON Patch is a format for describing changes to a JSON document. It can be used to avoid sending a whole
document when only a part has changed." (https://jsonpatch.com/ accessed 2024-08-20)

JSON Patch Operations:

- `add`: Adds a value to the specified path. If the path already exists, the value is replaced.
- `remove`: Removes the value at the specified path.
- `replace`: Replaces the value at the specified path with a new value.
- `test`: Tests that the specified path contains the given value.

The `path` is a string that uses a slash (`/`) notation to specify the location within the metadata.



```python
# add a value that was previously empty
me.patch_update_project_log_by_id(indicator_id, 'add', '/series_description/definition_short', 'This is a test description')
# test that a specified value is set
me.patch_update_project_log_by_id(indicator_id, 'test', '/series_description/definition_short', 'This is a test description')
# change a value
me.patch_update_project_log_by_id(indicator_id, 'replace', '/series_description/definition_short', 'This is a new test description')
# remove a value
me.patch_update_project_log_by_id(indicator_id, 'remove', '/series_description/definition_short')

```

# Collections

We can list and create collections, we can add and remove projects from collections and we can apply templates to collections.


```python
me.list_collections().head()
```




<table border="1" class="dataframe">
<thead>
<tr style="text-align: right;">
<th></th>
<th>title</th>
<th>description</th>
<th>created</th>
<th>changed</th>
<th>created_by</th>
<th>changed_by</th>
<th>pid</th>
<th>wgt</th>
<th>username</th>
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
<th></th>
</tr>
</thead>
<tbody>
<tr>
<th>183</th>
<td>aa</td>
<td>aa</td>
<td>2025-03-31T06:59:18+00:00</td>
<td>2025-03-31T06:59:18+00:00</td>
<td>39</td>
<td>39</td>
<td>3</td>
<td>None</td>
<td>outsourcify</td>
</tr>
<tr>
<th>8</th>
<td>aL-moved</td>
<td>Collection description Text</td>
<td>1970-01-01T00:33:43+00:00</td>
<td>2024-02-06T04:04:35+00:00</td>
<td>13</td>
<td>20</td>
<td>None</td>
<td>None</td>
<td>chriskrestel</td>
</tr>
<tr>
<th>18</th>
<td>CCKP</td>
<td>World Bank Climate Change Knowledge Platform</td>
<td>2024-06-05T02:04:21+00:00</td>
<td>2024-06-05T02:04:21+00:00</td>
<td>2</td>
<td>2</td>
<td>None</td>
<td>None</td>
<td>Olivier Dupriez</td>
</tr>


</tbody>
</table>




```python
collection_id = me.create_collection(demo_name+"_collection", description = "An example collection for demonstration")
```


```python
me.get_collection_by_id(collection_id)
```




    id                                                 213
    title                       GB20250225_demo_collection
    description    An example collection for demonstration
    created                                     1748028923
    changed                                     1748028923
    created_by...



### Populating collections


```python
me.add_projects_to_collection(collection=collection_id, id_format='id', projects=[indicator_id])
```


```python
me.list_projects_in_collection(collection=collection_id, limit=5)
```




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
<th>published</th>
<th>created</th>
<th>changed</th>
<th>varcount</th>
<th>created_by</th>
<th>changed_by</th>
<th>is_shared</th>
<th>thumbnail</th>
<th>template_uid</th>
<th>attributes</th>
<th>username</th>
<th>username_cr</th>
<th>collections</th>
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
<th></th>
<th></th>
<th></th>
<th></th>
<th></th>
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
<th>5096</th>
<td>timeseries</td>
<td>9960d5df-f2f4-477b-98ce-a58e20b829b4</td>
<td>GB20250225_demo</td>
<td>Version 1</td>
<td>None</td>
<td>None</td>
<td>0</td>
<td>0</td>
<td>None</td>
<td>2025-05-23T19:35:14+00:00</td>
<td>2025-05-23T19:35:23+00:00</td>
<td>None</td>
<td>24</td>
<td>24</td>
<td>None</td>
<td>None</td>
<td>timeseries-system-en</td>
<td>{'database_id': None}</td>
<td>Gordon Blackadder</td>
<td>Gordon Blackadder</td>
<td>[{'id': '213', 'title': 'GB20250225_demo_colle...</td>
</tr>
</tbody>
</table>




```python
me.remove_projects_from_collection(collection=collection_id, id_format='id', projects=[indicator_id])
```

### Deleting Collections


```python
me.delete_collection_by_id(collection_id)
```

# Templates

Different organizations often want to specify the use of different subsets of metadata. We can list templates and see which templates are the default for our organization.


```python
me.list_templates().head()
```




<table border="1" class="dataframe">
<thead>
<tr style="text-align: right;">
<th></th>
<th>uid</th>
<th>template_type</th>
<th>name</th>
<th>data_type</th>
<th>lang</th>
<th>template</th>
<th>default</th>
<th>id</th>
<th>version</th>
<th>organization</th>
<th>author</th>
<th>description</th>
<th>instructions</th>
<th>created</th>
<th>created_by</th>
<th>changed</th>
<th>changed_by</th>
<th>owner_id</th>
<th>deleted_at</th>
<th>deleted_by</th>
<th>is_deleted</th>
<th>owner_username</th>
<th>owner_email</th>
<th>changed_by_username</th>
<th>changed_by_email</th>
<th>created_by_username</th>
<th>created_by_email</th>
</tr>
</thead>
<tbody>
<tr>
<th>0</th>
<td>microdata-system-en</td>
<td>core</td>
<td>Microdata DDI 2.5 EN</td>
<td>survey</td>
<td>en</td>
<td>metadata_editor/metadata_editor_templates/surv...</td>
<td>False</td>
<td>NaN</td>
<td>NaN</td>
<td>NaN</td>
<td>NaN</td>
<td>NaN</td>
<td>NaN</td>
<td>NaN</td>
<td>NaN</td>
<td>NaN</td>
<td>NaN</td>
<td>NaN</td>
<td>NaN</td>
<td>NaN</td>
<td>NaN</td>
<td>NaN</td>
<td>NaN</td>
<td>NaN</td>
<td>NaN</td>
<td>NaN</td>
<td>NaN</td>
</tr>
<tr>
<th>1</th>
<td>232ea3aaece0cdf1db157f797f6b92e5fr</td>
<td>core</td>
<td>IHSN DDI 2.5 Modèle v01 FR</td>
<td>survey</td>
<td>fr</td>
<td>metadata_editor/metadata_editor_templates/surv...</td>
<td>False</td>
<td>NaN</td>
<td>NaN</td>
<td>NaN</td>
<td>NaN</td>
<td>NaN</td>
<td>NaN</td>
<td>NaN</td>
<td>NaN</td>
<td>NaN</td>
<td>NaN</td>
<td>NaN</td>
<td>NaN</td>
<td>NaN</td>
<td>NaN</td>
<td>NaN</td>
<td>NaN</td>
<td>NaN</td>
<td>NaN</td>
<td>NaN</td>
<td>NaN</td>
</tr>
<tr>
<th>2</th>
<td>6740f5f920502baf3f6cbcaa5c113deeen</td>
<td>core</td>
<td>IHSN DDI 2.5 Template v01 EN</td>
<td>survey</td>
<td>en</td>
<td>metadata_editor/metadata_editor_templates/surv...</td>
<td>False</td>
<td>NaN</td>
<td>NaN</td>
<td>NaN</td>
<td>NaN</td>
<td>NaN</td>
<td>NaN</td>
<td>NaN</td>
<td>NaN</td>
<td>NaN</td>
<td>NaN</td>
<td>NaN</td>
<td>NaN</td>
<td>NaN</td>
<td>NaN</td>
<td>NaN</td>
<td>NaN</td>
<td>NaN</td>
<td>NaN</td>
<td>NaN</td>
<td>NaN</td>
</tr>
<tr>
<th>3</th>
<td>timeseries-system-en</td>
<td>core</td>
<td>Indicator Schema 1.0 EN</td>
<td>timeseries</td>
<td>en</td>
<td>metadata_editor/metadata_editor_templates/time...</td>
<td>True</td>
<td>NaN</td>
<td>NaN</td>
<td>NaN</td>
<td>NaN</td>
<td>NaN</td>
<td>NaN</td>
<td>NaN</td>
<td>NaN</td>
<td>NaN</td>
<td>NaN</td>
<td>NaN</td>
<td>NaN</td>
<td>NaN</td>
<td>NaN</td>
<td>NaN</td>
<td>NaN</td>
<td>NaN</td>
<td>NaN</td>
<td>NaN</td>
<td>NaN</td>
</tr>

</tbody>
</table>




```python
me.get_template_by_uid("microdata-system-en")
```




    uid                                            microdata-system-en
    template_type                                                 core
    name                                          Microdata DDI 2.5 EN
    data_type                                                   survey
    lang...



### Template Classes

We can create a pydantic model for a given class


```python
c = me.get_metadata_class("6740f5f920502baf3f6cbcaa5c113deeen")
```


```python
c
```




    template.IHSN_DDI_2-5_Template_v01_EN




```python
c.model_fields
```




    {'doc_desc': FieldInfo(annotation=Union[doc_desc, NoneType], required=False, default=None),
     'study_desc': FieldInfo(annotation=Union[study_desc, NoneType], required=False, default=None),
     'tags': FieldInfo(annotation=Union[List[Tag], NoneType], required=False, default=None, title='Tags', descriptio...



But it's usually easier to start with an outline of the class. Again, this can be in either a dictionary, a pydantic model or as an Excel file.


```python
me.make_metadata_outline("6740f5f920502baf3f6cbcaa5c113deeen", "pydantic").pretty_print()
```


IHSN_DDI_2-<span style="color: #800080; text-decoration-color: #800080; font-weight: bold">5_Template_v01_EN</span><span style="font-weight: bold">(</span><span style="color: #808000; text-decoration-color: #808000">doc_desc</span>=<span style="color: #800080; text-decoration-color: #800080; font-weight: bold">doc_desc</span><span style="font-weight: bold">(</span><span style="color: #808000; text-decoration-color: #808000">producers</span>=<span style="font-weight: bold">[</span><span style="color: #800080; text-decoration-color: #800080; font-weight: bold">Producer</span><span style="font-weight: bold">(</span><span style="color: #808000; text-decoration-color: #808000">name</span>=<span style="color: #800080; text-decoration-color: #800080; font-style: italic">None</span>, <span style="color: #808000; text-decoration-color: #808000">abbr</span>=<span style="color: #800080; text-decoration-color: #800080; font-style: italic">None</span>, <span style="color: #808000; text-decoration-color: #808000">affiliation</span>=<span style="color: #800080; text-decoration-color: #800080; font-style: italic">None</span>, <span style="color: #808000; text-decoration-color: #808000">role</span>=<span style="color: #800080; text-decoration-color: #800080; font-style: italic">None</span><span style="font-weight: bold">)]</span>,
        <span style="color: #808000; text-decoration-color: #808000">prod_date</span>=<span style="color: #800080; text-decoration-color: #800080; font-style: italic">None</span>,
        <span style="color: #808000; text-decoration-color: #808000">idno</span>=<span style="color: #800080; text-decoration-color: #800080; font-style: italic">None</span>,
        <span style="color: #808000; text-decoration-color: #808000">version_statement</span>=<span style="color: #800080; text-decoration-color: #800080; font-weight: bold">version_statement</span><span style="font-weight: bold">(</span><span style="color: #808000; text-decoration-color: #808000">version</span>=<span style="color: #800080; text-decoration-color: #800080; font-style: italic">None</span>,
            <span style="color: #808000; text-decoration-color: #808000">version_date</span>=<span style="color: #800080; text-decoration-color: #800080; font-style: italic">None</span>,
            <span style="color: #808000; text-decoration-color: #808000">version_resp</span>=<span style="color: #800080; text-decoration-color: #800080; font-style: italic">None</span>,
            <span style="color: #808000; text-decoration-color: #808000">version_notes</span>=<span style="color: #800080; text-decoration-color: #800080; font-style: italic">None</span><span style="font-weight: bold">)</span><span style="font-weight: bold">)</span>,
    <span style="color: #808000; text-decoration-color: #808000">study_desc</span>=<span style="color: #800080; text-decoration-color: #800080; font-weight: bold">study_desc</span><span style="font-weight: bold">(</span><span style="color: #808000; text-decoration-color: #808000">title_statement</span>=<span style="color: #800080; text-decoration-color: #800080; font-weight: bold">title_statement</span><span style="font-weight: bold">(</span><span style="color: #808000; text-decoration-color: #808000">title</span>=<span style="color: #008000; text-decoration-color: #008000">''</span>,
            <span style="color: #808000; text-decoration-color: #808000">sub_title</span>=<span style="color: #800080; text-decoration-color: #800080; font-style: italic">None</span>,
            <span style="color: #808000; text-decoration-color: #808000">alternate_title</span>=<span style="color: #800080; text-decoration-color: #800080; font-style: italic">None</span>,
            <span style="color: #808000; text-decoration-color: #808000">translated_title</span>=<span style="color: #800080; text-decoration-color: #800080; font-style: italic">None</span>,
            <span style="color: #808000; text-decoration-color: #808000">idno</span>=<span style="color: #008000; text-decoration-color: #008000">''</span>,
            <span style="color: #808000; text-decoration-color: #808000">identifiers</span>=<span style="font-weight: bold">[</span><span style="color: #800080; text-decoration-color: #800080; font-weight: bold">Identifier</span><span style="font-weight: bold">(</span><span style="color: #808000; text-decoration-color: #808000">type</span>=<span style="color: #800080; text-decoration-color: #800080; font-style: italic">None</span>, <span style="color: #808000; text-decoration-color: #808000">identifier</span>=<span style="color: #800080; text-decoration-color: #800080; font-style: italic">None</span><span style="font-weight: bold">)]</span>...



```python
me.make_metadata_outline("6740f5f920502baf3f6cbcaa5c113deeen", "dict")
```




    {'doc_desc': {'producers': [{'name': None,
        'abbr': None,
        'affiliation': None,
        'role': None}],
      'prod_date': None,
      'idno': None,
      'version_statement': {'version': None,
       'version_date': None,
       'version_resp': None,
       'version_notes': None}},
     'study_desc': {'title_statement': {'t...



## Deleting Projects


```python
me.delete_project_by_id(indicator_id)
```
