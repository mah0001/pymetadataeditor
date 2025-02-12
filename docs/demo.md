# How to use pyMetadataEditor


```python
from pymetadataeditor import MetadataEditor
import os
```

## Examples of the interface


```python
your_api_key = os.getenv("API_KEY")
api_url = os.getenv("API_URL")
me = MetadataEditor(api_url=api_url, api_key=your_api_key, verify_ssl=False)
```

### Listing your projects


```python
me.list_projects(limit=8)
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
    </tr>
    <tr>
      <th>id</th>
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
    </tr>
    <tr>
      <th>1002</th>
      <td>survey</td>
      <td>67890</td>
      <td>SURVEY_002</td>
      <td>Sample Survey 2</td>
      <td>SS2</td>
      <td>Example Nation</td>
    </tr>
    <tr>
      <th>1001</th>
      <td>timeseries</td>
      <td>54321</td>
      <td>TS_003</td>
      <td>Time Series 3</td>
      <td>TS3</td>
      <td>Another Nation</td>
    </tr>
  </tbody>
</table>
</div>




```python
me.count_projects()
```




    1501



### Creating a new indicator project


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
<th>4662</th>
<td>timeseries</td>
<td>f6720e01-e634-461a-bf88-5f6e762a1e4b</td>
<td>GB20241030_demo</td>
<td>Version 1</td>
<td>None</td>
<td></td>
</tr>
<tr>
      <th>1003</th>
      <td>document</td>
      <td>12345</td>
      <td>DOC_001</td>
      <td>Sample Document 1</td>
      <td>SD1</td>
      <td>Example Nation</td>
    </tr>
    <tr>
      <th>1002</th>
      <td>survey</td>
      <td>67890</td>
      <td>SURVEY_002</td>
      <td>Sample Survey 2</td>
      <td>SS2</td>
      <td>Example Nation</td>
    </tr>
    <tr>
      <th>1001</th>
      <td>timeseries</td>
      <td>54321</td>
      <td>TS_003</td>
      <td>Time Series 3</td>
      <td>TS3</td>
      <td>Another Nation</td>
    </tr>
</tbody>
</table>




```python
me.get_project_by_id(indicator_id)
```




    id                                                               4662
    idno                             f6720e01-e634-461a-bf88-5f6e762a1e4b
    type                                                       timeseries
    title                                                       Version 1
    abbreviation...




```python
me.get_project_metadata_by_id(indicator_id, output_mode='dict')
```




    {'series_description': {'idno': 'GB20241030_demo', 'name': 'Version 1'}}



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




    IHSN_INDICATOR_1-0_Template_v01_EN(metadata_information=metadata_information(title=None, idno=None, producers=[Producer(name='', abbr=None, affiliation=None, role=None)], prod_date=None, version_statement=version_statement(version=None, version_date=None, version_notes=None, version_resp=None)), ser...



It can be updated using dot notation, for example:


```python
indicator_pydantic.metadata_information.producers[0].name = "example_producer"
indicator_pydantic
```




    IHSN_INDICATOR_1-0_Template_v01_EN(metadata_information=metadata_information(title=None, idno=None, producers=[Producer(name='example_producer', abbr=None, affiliation=None, role=None)], prod_date=None, version_statement=version_statement(version=None, version_date=None, version_notes=None, version_...



## Printing

The pydantic metadata object also contains a helper function for printing metadata:


```python
indicator_pydantic.pretty_print()
```


IHSN_INDICATOR_1-<span style="color: #800080; text-decoration-color: #800080; font-weight: bold">0_Template_v01_EN</span><span style="font-weight: bold">(</span><span style="color: #808000; text-decoration-color: #808000">metadata_information</span>=<span style="color: #800080; text-decoration-color: #800080; font-weight: bold">metadata_information</span><span style="font-weight: bold">(</span><span style="color: #808000; text-decoration-color: #808000">title</span>=<span style="color: #800080; text-decoration-color: #800080; font-style: italic">None</span>,
        <span style="color: #808000; text-decoration-color: #808000">idno</span>=<span style="color: #800080; text-decoration-color: #800080; font-style: italic">None</span>,
        <span style="color: #808000; text-decoration-color: #808000">producers</span>=<span style="font-weight: bold">[</span><span style="color: #800080; text-decoration-color: #800080; font-weight: bold">Producer</span><span style="font-weight: bold">(</span><span style="color: #808000; text-decoration-color: #808000">name</span>=<span style="color: #008000; text-decoration-color: #008000">'example_producer'</span>, <span style="color: #808000; text-decoration-color: #808000">abbr</span>=<span style="color: #800080; text-decoration-color: #800080; font-style: italic">None</span>, <span style="color: #808000; text-decoration-color: #808000">affiliation</span>=<span style="color: #800080; text-decoration-color: #800080; font-style: italic">None</span>, <span style="color: #808000; text-decoration-color: #808000">role</span>=<span style="color: #800080; text-decoration-color: #800080; font-style: italic">None</span><span style="font-weight: bold">)]</span>,
        <span style="color: #808000; text-decoration-color: #808000">prod_date</span>=<span style="color: #800080; text-decoration-color: #800080; font-style: italic">None</span>,
        <span style="color: #808000; text-decoration-color: #808000">version_statement</span>=<span style="color: #800080; text-decoration-color: #800080; font-weight: bold">version_statement</span><span style="font-weight: bold">(</span><span style="color: #808000; text-decoration-color: #808000">version</span>=<span style="color: #800080; text-decoration-color: #800080; font-style: italic">None</span>,
            <span style="color: #808000; text-decoration-color: #808000">version_date</span>=<span style="color: #800080; text-decoration-color: #800080; font-style: italic">None</span>,
            <span style="color: #808000; text-decoration-color: #808000">version_notes</span>=<span style="color: #800080; text-decoration-color: #800080; font-style: italic">None</span>,
            <span style="color: #808000; text-decoration-color: #808000">version_resp</span>=<span style="color: #800080; text-decoration-color: #800080; font-style: italic">None</span><span style="font-weight: bold">)</span><span style="font-weight: bold">)</span>,
    <span style="color: #808000; text-decoration-color: #808000">series_description</span>=<span style="color: #800080; text-decoration-color: #800080; font-weight: bold">series_description</span><span style="font-weight: bold">(</span><span style="color: #808000; text-decoration-color: #808000">idno</span>=<span style="color: #008000; text-decoration-color: #008000">''</span>,
        <span style="color: #808000; text-decoration-color: #808000">alternate_identifiers</span>=<span style="font-weight: bold">[</span><span style="color: #800080; text-decoration-color: #800080; font-weight: bold">Alternate_identifier</span><span style="font-weight: bold">(</span><span style="color: #808000; text-decoration-color: #808000">name</span>=<span style="color: #800080; text-decoration-color: #800080; font-style: italic">None</span>, <span style="color: #808000; text-decoration-color: #808000">identifier</span>=<span style="color: #800080; text-decoration-color: #800080; font-style: italic">None</span>, <span style="color: #808000; text-decoration-color: #808000">database</span>=<span style="color: #800080; text-decoration-color: #800080; font-style: italic">None</span>, <span style="color: #808000; text-decoration-color: #808000">uri</span>=<span style="color: #800080; text-decoration-color: #800080; font-style: italic">None</span>, <span style="color: #808000; text-decoration-color: #808000">notes</span>=<span style="color: #800080; text-decoration-color: #800080; font-style: italic">None</span><span style="font-weight: bold">)</span><span style="font-weight: bold">]</span>,
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




    'IHSN_INDICATOR_1-0_Template_v01_EN_metadata.xlsx'




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




    {'series_description': {'idno': 'GB20241030_demo', 'name': 'Version 1'}}




```python
demo_pydantic = me.get_project_metadata_by_id(indicator_id, 'pydantic')
demo_pydantic
```




    IHSN_INDICATOR_1-0_Template_v01_EN(metadata_information=metadata_information(title=None, idno=None, producers=[Producer(name='', abbr=None, affiliation=None, role=None)], prod_date=None, version_statement=version_statement(version=None, version_date=None, version_notes=None, version_resp=None)), ser...




```python
excel_filename = demo_name+'.xlsx'
me.get_project_metadata_by_id(indicator_id, output_mode='excel', filename=excel_filename)
```




    'GB20241030_demo.xlsx'



### Updating an existing project

You can create and update projects with metadata as either dictionaries, pydantic models or in Excel files. 


```python
me.update_project_log_by_id(indicator_id, demo_dict)
```


```python
me.update_project_log_by_id(indicator_id, demo_pydantic)
```


```python
me.update_project_log_by_id(indicator_id, excel_filename)
```

### Updating with patch updates


```python
# tidy up the file called f"{demo_name}.xlsx"
os.remove(f"{demo_name}.xlsx")
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
<th>1</th>
<td>Sample Title 1</td>
<td>Sample Description 1</td>
<td>2025-01-01T00:00:00+00:00</td>
<td>2025-01-02T00:00:00+00:00</td>
<td>1</td>
<td>2</td>
<td>None</td>
<td>None</td>
<td>user1</td>
</tr>
<tr>
<th>2</th>
<td>Sample Title 2</td>
<td>Sample Description 2</td>
<td>2025-02-01T00:00:00+00:00</td>
<td>2025-02-02T00:00:00+00:00</td>
<td>3</td>
<td>4</td>
<td>None</td>
<td>None</td>
<td>user2</td>
</tr>
<tr>
<th>3</th>
<td>Sample Title 3</td>
<td>Sample Description 3</td>
<td>2025-03-01T00:00:00+00:00</td>
<td>2025-03-02T00:00:00+00:00</td>
<td>5</td>
<td>6</td>
<td>None</td>
<td>None</td>
<td>user3</td>
</tr>
</tbody>
</table>




```python
collection_id = me.create_collection(demo_name+"_collection", description = "An example collection for demonstration")
```


```python
me.get_collection_by_id(collection_id)
```




    id                                                 179
    title                       GB20241030_demo_collection
    description    An example collection for demonstration
    created                                     1738874405
    changed                                     1738874405
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
</tr>
</thead>
<tbody>
<tr>
<th>4662</th>
<td>timeseries</td>
<td>f6720e01-e634-461a-bf88-5f6e762a1e4b</td>
<td>GB20241030_demo</td>
<td>Version 1</td>
<td>None</td>
<td></td>
<td>0</td>
<td>0</td>
<td>None</td>
<td>2025-02-06T20:39:58+00:00</td>
<td>2025-02-06T20:40:04+00:00</td>
<td>None</td>
<td>24</td>
<td>24</td>
<td>None</td>
<td>None</td>
<td>8603d94e27bccc2bdad1e00dbbf0fe32en</td>
<td>Dummy User</td>
<td>Dummy User</td>
<td>[{'id': '179', 'title': 'GB20241030_demo_colle...</td>
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
<th>...</th>
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
<td>dummy-uid-1</td>
<td>core</td>
<td>Dummy Template 1</td>
<td>survey</td>
<td>en</td>
<td>dummy_template_path_1</td>
<td>False</td>
<td>NaN</td>
<td>NaN</td>
<td>Dummy Org 1</td>
<td>...</td>
<td>NaN</td>
<td>NaN</td>
<td>NaN</td>
<td>NaN</td>
<td>dummy_user_1</td>
<td>dummy_email_1@example.com</td>
<td>dummy_changed_user_1</td>
<td>dummy_changed_email_1@example.com</td>
<td>dummy_created_user_1</td>
<td>dummy_created_email_1@example.com</td>
</tr>
<tr>
<th>1</th>
<td>dummy-uid-2</td>
<td>core</td>
<td>Dummy Template 2</td>
<td>survey</td>
<td>fr</td>
<td>dummy_template_path_2</td>
<td>False</td>
<td>NaN</td>
<td>NaN</td>
<td>Dummy Org 2</td>
<td>...</td>
<td>NaN</td>
<td>NaN</td>
<td>NaN</td>
<td>NaN</td>
<td>dummy_user_2</td>
<td>dummy_email_2@example.com</td>
<td>dummy_changed_user_2</td>
<td>dummy_changed_email_2@example.com</td>
<td>dummy_created_user_2</td>
<td>dummy_created_email_2@example.com</td>
</tr>
<tr>
<th>2</th>
<td>dummy-uid-3</td>
<td>core</td>
<td>Dummy Template 3</td>
<td>survey</td>
<td>es</td>
<td>dummy_template_path_3</td>
<td>False</td>
<td>NaN</td>
<td>NaN</td>
<td>Dummy Org 3</td>
<td>...</td>
<td>NaN</td>
<td>NaN</td>
<td>NaN</td>
<td>NaN</td>
<td>dummy_user_3</td>
<td>dummy_email_3@example.com</td>
<td>dummy_changed_user_3</td>
<td>dummy_changed_email_3@example.com</td>
<td>dummy_created_user_3</td>
<td>dummy_created_email_3@example.com</td>
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
