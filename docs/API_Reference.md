<!-- markdownlint-disable -->


# <kbd>class</kbd> `MetadataEditor`
pyMetadataEditor helps create and manage metadata in a Metadata Editor database. 

pyMetadataEditor allows you to list, create, update and delete projects, manage collections and list templates in  a metadata database. 

You can save metadata to an Excel file. Or use OpenAI to draft metadata from files or web pages. 

First obtain an API key and pase it into a file called '.env' in the root of your project. The contents of the  file should look like this: 

 `METADATA_API_URL=https://<name_of_your_metadata_database>.org/index.php/api` 

 `METADATA_API_KEY=your_api_key` 



Then in python run 

```python
from pymetadataeditor import MetadataEditor
import os

api_url = os.getenv("METADATA_API_URL")
api_key = os.getenv("METADATA_API_KEY")
me = MetadataEditor(api_url = api_url, api_key = api_key)
``` 

Then you can list and create new projects like so: 

```python
me.list_projects(limit=100)
indicator_metadata = me.make_metadata_outline("indicator", "pydantic")
# update the indicator metadata as needed.

# View nicely formatted metadata
indicator_metadata.pretty_print()

# Then log the metadata to the database
me.create_project_log(dict_of_indicator, "indicator")
``` 


### <kbd>method</kbd> `__init__`

```python
__init__(
    api_url: str,
    api_key: str,
    allow_http: bool = False,
    verify_ssl: bool = True
)
```

Create a new MetadataEditor object connected to an instance of a Metadata Editor database. 



**Args:**
 
 - <b>`api_url`</b> (str):  the URL typically looks like 'https://<name_of_your_metadata_database>.org/index.php/api' 
 - <b>`api_key`</b> (str):  typically this is created through the web interface of the metadata system. 
 - <b>`allow_http`</b> (bool):  whether to allow calls to the metadata system when the URL begins "http" instead of the  more secure "https". Defaults to False. 
 - <b>`verify_ssl`</b> (bool):  Although it is good practice for API requests to verify SSL, some systems do not allow  this so setting verify_ssl=False may be required. Defaults to True. 



**Example:**
 ```python
from pymetadataeditor import MetadataEditor
import os

api_url = os.getenv("METADATA_API_URL")
api_key = os.getenv("METADATA_API_KEY")
me = MetadataEditor(api_url = api_url, api_key = api_key)
``` 




---


## <kbd>method</kbd> `add_projects_to_collection`

```python
add_projects_to_collection(
    collection: Union[int, List[int]],
    id_format: str,
    projects: Union[int, List[int], str, List[str]]
)
```

Adds project or projects to specified collection or collections. 

This method associates one or more projects with one or more collections. The `collection` parameter can be a single collection ID or a list of collection IDs. The `projects` parameter can be a single project ID, a single project ID number (idno), a list of project IDs, or a list of project idnos. The `id_format` parameter specifies whether the project identifiers are in the form of IDs (integer) or idno (string). 



**Args:**
 
 - <b>`collection `</b>:  Union[int, List[int]]  A single collection ID or a list of collection IDs to which projects should be added. 
 - <b>`id_format `</b>:  str  Specifies the format of the project identifiers. Must be either 'id' or 'idno'. 
 - <b>`projects `</b>:  Union[int, List[int], str, List[str]]  A single project ID, a single project idno, a list of project IDs, or a list of  project idnos to be added to the specified collection(s). 



**Example:**
 ```python
me = MetadataEditor(api_url = api_url, api_key = api_key)
me.add_projects_to_collection(collection=1, id_format='id', projects=[101, 102])
me.add_projects_to_collection(collection=[1, 2], id_format='idno', projects=['A101', 'A102'])
``` 

---


## <kbd>method</kbd> `augment_metadata_from_files`

```python
augment_metadata_from_files(
    input_metadata: Union[BaseModel, Dict, str],
    llm_api_key: str,
    files: Union[List[str], str],
    output_mode: str,
    metadata_type_or_template_uid: Optional[str] = None,
    metadata_producer_organization: Optional[str] = None,
    prefix: Optional[str] = None,
    filename: Optional[str] = None,
    title: Optional[str] = None,
    llm_model_name='gpt-4o',
    tokenizer_model='o200k_base',
    max_tokens=128000,
    llm_base_url: Optional[str] = None,
    azure_deployment_name: Optional[str] = None
) → Union[BaseModel, Dict, str]
```

Augment existing metadata with information from files or web pages. 

Since the metadata is being augmented, the new metadata can be given a prefix to indicate it is new. 



**Args:**
 
 - <b>`input_metadata`</b> (Union[BaseModel, Dict, str]):  The existing metadata to augment. Can be a dictionary, a  pydantic model or a path to an Excel file. 
 - <b>`llm_api_key`</b> (str):  The API key for the LLM API. 
 - <b>`files`</b> (List[str] | str):  The path to the file or a list of paths to the files from which to base metadata. 
 - <b>`output_mode`</b> (str):  The type of output. Must be 'dict', 'pydantic' or 'excel'. 
 - <b>`metadata_type_or_template_uid`</b> (Optional[str]):  The type of metadata to create or the UID of a template to  use. If None then the type will be inferred from the input_metadata. 
 - <b>`metadata_producer_organization`</b> (Optional[str]):  The name of the organisation producing the metadata. 
 - <b>`prefix`</b> (Optional[str]):  A prefix to add to the new metadata. If None, no prefix is added. 
 - <b>`filename`</b> (Optional[str]):  If output_mode=='excel', the path to the Excel file.  If None and output_mode=='excel', defaults to {name of metadata type}_metadata.xlsx 
 - <b>`title`</b> (Optional[str]):  If output_mode=='excel', the title for the Excel sheet.  If None and mode=='excel', defaults to '{name of metadata type} Metadata' 
 - <b>`llm_model_name`</b> (str):  The OpenAI model to use. Defaults to "gpt-4o". Note any model must accept a response  format (also called structured output). Usually you should leave this to the default value.  The option is provided in case OpenAI deprecated the 4o model. 
 - <b>`tokenizer_model`</b> (str):  The tokenizer model to use. Defaults to "o200k_base". Note this should be the  tokenizer corresponding to the OpenAI model used. Usually you should leave this to the default value.  The option is provided in case OpenAI deprecated the 4o model. 
 - <b>`max_tokens`</b> (int):  The maximum number of tokens to use when sending the content to OpenAI.  Defaults to 128_000, which has been the typical maximum for the 4o model. 
 - <b>`llm_base_url`</b> (Optional[str]):  The base URL for the LLM API. If None, the default URL is used which  sends the request to OpenAI. Alternatively, this can be the base URL for a local LLM instance such as  Ollama or a private deployment of an LLM model. If using Azure OpenAI, this should be the Azure 
 - <b>`endpoint URL (eg "https`</b>: //my-azure-openai-resource.openai.azure.com/") and the azure_deployment_name  parameter should also be set. 
 - <b>`azure_deployment_name`</b> (Optional[str]):  Used when an organization has its own deployment of an LLM model in   Azure, possibly for privacy reasons. Be sure to provide the llm_base_url parameter as well which should  be the Azure endpoint URL. 



**Returns:**
 
 - <b>`Union[BaseModel, Dict, str]`</b>:  The augmented metadata. 



**Example:**
 ```python
me = MetadataEditor(api_url=..., api_key=...)

# augment existing metadata with information from files
me.augment_metadata_from_files(
    input_metadata=my_indicator_metadata,
    llm_api_key="...",
    files=["/path/to/word_file1.docx", "http://www.example.com/report.pdf"],
    output_mode="pydantic",
    metadata_producer_organization="My Organization",
    prefix="<AI>"
)

# Example with an Azure instance of a Large Language Model:
me.augment_metadata_from_files(
    input_metadata=my_indicator_metadata,
    llm_api_key="...",
    files=["/path/to/word_file1.docx", "http://www.example.com/report.pdf"],
    output_mode="pydantic",
    metadata_producer_organization="My Organization",
    prefix="<AI>",
    llm_base_url="https://my-azure-openai-resource.openai.azure.com/",
    azure_deployment_name="my-llm-deployment"
)
``` 

---


## <kbd>method</kbd> `change_mode_or_template`

```python
change_mode_or_template(
    metadata: Union[BaseModel, Dict, str],
    output_mode: str,
    output_template_uid: Optional[str] = None,
    input_template_uid: Optional[str] = None,
    filename: Optional[str] = None,
    title: Optional[str] = None,
    simplify: Optional[bool] = None
) → Union[BaseModel, Dict, str]
```

Change the mode or template of a metadata object. 

In terms of modes, you can convert 
    - a dict to a pydantic model, or vice versa, 
    - a dict to an Excel file, or vice versa, 
    - a pydantic model to an Excel file, or vice versa 

And in terms of templates, you can convert a metadata object from one template to another. 



**Args:**
 
 - <b>`metadata`</b> (Union[BaseModel, Dict, str]):  The metadata to process. 
 - <b>`output_mode`</b> (str):  The output mode. Must be 'dict', 'pydantic' or 'excel'. 
 - <b>`output_template_uid`</b> (Optional[str]):  The UID of the new template. If None then the existing template is  used. 
 - <b>`input_template_uid`</b> (Optional[str]):  The UID of the input template. Required if the metadata is a dictionary.  Ignored if metadata is a pydantic model or a path to an Excel file. 
 - <b>`filename`</b> (Optional[str]):  If output_mode=='excel', the path to the Excel file.  If None, defaults to {name of metadata type}_metadata.xlsx 
 - <b>`title`</b> (Optional[str]):  If output_mode=='excel', the title for the Excel sheet.  If None, defaults to '{name of metadata type} Metadata' 
 - <b>`simplify`</b> (Optional[bool]):  If output_mode=='dict', then if simplify=True, only elements that were explicitly  set with non-null, non-empty values are returned in the dictionary. Default behaviour is False 



**Returns:**
 
 - <b>`Union[BaseModel, Dict, str]`</b>:  The updated metadata object. 

---


## <kbd>method</kbd> `copy_collection`

```python
copy_collection(source_id: int, target_id: int)
```

Copy projects and users from one collection to another. 



**Args:**
 
 - <b>`source_id`</b> (int):  The ID of the source collection. 
 - <b>`target_id`</b> (int):  The ID of the target collection. 

---


## <kbd>method</kbd> `count_projects`

```python
count_projects() → int
```

Count the number of projects you have access to. 



**Returns:**
 
 - <b>`int`</b>:  The number of projects 

---


## <kbd>method</kbd> `count_projects_in_collection`

```python
count_projects_in_collection(collection: int) → int
```

Count the number of projects you have access to. 



**Args:**
  collection (int):  The id of the collection. 



**Returns:**
 
 - <b>`int`</b>:  The number of projects 

---


## <kbd>method</kbd> `create_collection`

```python
create_collection(title: str, description: str)
```

Creates a new collection with the specified title and description. 



**Args:**
 
 - <b>`title`</b> (str):  The title of the collection. 
 - <b>`description`</b> (str):  The description of the collection. 



**Returns:**
 
 - <b>`(int)`</b>:  The id of the newly created collection 

---


## <kbd>method</kbd> `create_project_log`

```python
create_project_log(
    metadata: Union[BaseModel, Dict, str],
    metadata_type_or_template_uid: Optional[str] = None
) → int
```

Validates and logs metadata which can be a dictionary, a pydantic model or a path to an Excel spreadsheet. 



**Args:**
 
 - <b>`metadata`</b> (dictionary or BaseModel or str):  If str, it's assumed this is a path to an appropriately  formatted Excel file. 
 - <b>`metadata_type_or_template_uid`</b> (str):  If passing in a simple type then the supported types are:  document, geospatial, image, indicator, indicators_db, microdata, resource, script, table, video  In this case we will use the default template for that metadata type.  Alternatively you can pass in the UID of a template. This is required if the metadata is a dictionary  otherwise the UID associated with the pydantic model or the Excel file will be used. 



**Returns:**
 
 - <b>`int`</b>:  The ID of the newly created document metadata 

---


## <kbd>method</kbd> `delete_collection_by_id`

```python
delete_collection_by_id(id: int)
```

If the collection exists then deletes it and check it was deleted. 



**Args:**
 
 - <b>`id`</b> (int):  the id of the colection. 



**Raises:**
 
 - <b>`DeleteNotAppliedError`</b>:  This can be the result of system admins blocking data deletion 

---


## <kbd>method</kbd> `delete_project_by_id`

```python
delete_project_by_id(id: int)
```

If the project exists then delete it and check it was deleted. 



**Args:**
 
 - <b>`id`</b> (int):  the id of the project, not to be confused with the idno. 



**Raises:**
 
 - <b>`DeleteNotAppliedError`</b>:  This can be the result of system admins blocking data deletion 

---


## <kbd>method</kbd> `delete_resource_by_id`

```python
delete_resource_by_id(project_id, resource_id)
```

If the resource exists then deletes it and check it was deleted. 



**Args:**
 
 - <b>`project_id`</b> (int):  The project id the resource is associated with. 
 - <b>`resource_id`</b> (int):  The id of the resource. 



**Raises:**
 
 - <b>`DeleteNotAppliedError`</b>:  This can be the result of system admins blocking data deletion 

---


## <kbd>method</kbd> `delete_template`

```python
delete_template(uid: str)
```

Deletes the given template. 



**Args:**
 
 - <b>`uid`</b> (str):  The Unique Identifier of the template to delete. 

---


## <kbd>method</kbd> `draft_metadata_from_files`

```python
draft_metadata_from_files(
    llm_api_key: str,
    files: Union[List[str], str],
    output_mode: str,
    metadata_type_or_template_uid: str,
    metadata_producer_organization: Optional[str] = None,
    filename: Optional[str] = None,
    title: Optional[str] = None,
    llm_model_name='gpt-4o',
    tokenizer_model='o200k_base',
    max_tokens=128000,
    llm_base_url: Optional[str] = None,
    azure_deployment_name: Optional[str] = None
) → Union[BaseModel, Dict, str]
```

Automatically generate *draft* metadata for a project based on local files or web pages. 

The files can be: 


- PDF 
- PowerPoint 
- Word 
- Excel 
- Images 
- Audio 
- HTML 
- Text-based formats (CSV, XML) 
- ZIP files 

In the case of images and audio the files will first be passed to OpenAI for describing or transcribing. 



**Args:**
 
 - <b>`llm_api_key`</b> (str):  The API key for the LLM API. 
 - <b>`files`</b> (List[str] | str):  The path to the file or a list of paths to the files from which to base metadata. 
 - <b>`output_mode`</b> (str):  The type of output. Must be 'dict', 'pydantic' or 'excel'. 
 - <b>`metadata_type_or_template_uid`</b> (str):  The type of metadata to create or the UID of a template to use. 
 - <b>`metadata_producer_organization`</b> (Optional[str]):  The name of the organisation producing the metadata. 
 - <b>`filename`</b> (Optional[str]):  If output_mode=='excel', the path to the Excel file.  If None and output_mode=='excel', defaults to {name of metadata type}_metadata.xlsx 
 - <b>`title`</b> (Optional[str]):  If output_mode=='excel', the title for the Excel sheet.  If None and mode=='excel', defaults to '{name of metadata type} Metadata' 
 - <b>`llm_model_name`</b> (str):  The model to use. Defaults to "gpt-4o". Note any model must accept a response  format (also called structured output). Usually you should leave this to the default value.  The option is provided in case OpenAI deprecated the 4o model. 
 - <b>`tokenizer_model`</b> (str):  The tokenizer model to use. Defaults to "o200k_base". Note this should be the  tokenizer corresponding to the OpenAI model used. Usually you should leave this to the default value.  The option is provided in case OpenAI deprecated the 4o model. 
 - <b>`max_tokens`</b> (int):  The maximum number of tokens to use when sending the content to OpenAI.  Defaults to 128_000, which has been the typical maximum for the 4o model. 
 - <b>`llm_base_url`</b> (Optional[str]):  The base URL for the LLM API. If None, the default URL is used which  sends the request to OpenAI. Alternatively, this can be the base URL for a local LLM instance such as  Ollama or a private deployment of an LLM model. If using Azure OpenAI, this should be the Azure 
 - <b>`endpoint URL (eg "https`</b>: //my-azure-openai-resource.openai.azure.com/") and the azure_deployment_name  parameter should also be set. 
 - <b>`azure_deployment_name`</b> (Optional[str]):  Used when an organization has its own deployment of an LLM model in   Azure, possibly for privacy reasons. Be sure to provide the llm_base_url parameter as well which should  be the Azure endpoint URL. 



**Returns:**
 
 - <b>`(Union[BaseModel, Dict, str])`</b>:  If mode == 'dict', a dictionary is returned. If mode == 'pydantic', a  pydantic model object is returned. If mode == 'excel' then the metadata was saved to a file and the  filename is returned. 



**Example:**
 ```python
me = MetadataEditor(api_url = api_url, api_key = api_key)
me.draft_metadata_from_files(
    llm_api_key="...",
    files=["/path/to/word_file1.docx", "http://www.example.com/report.pdf"],
    output_mode="pydantic",
    metadata_type_or_template_uid="indicator",
    metadata_producer_organization="My Organization",
    filename="output.xlsx",
    title="My Metadata",
)

# Example with a local model running on Ollama:
me.draft_metadata_from_files(
    llm_api_key="ollama",  # pragma: allowlist secret
    files=["/path/to/word_file1.docx", "http://www.example.com/report.pdf"],
    output_mode="pydantic",
    metadata_type_or_template_uid="indicator",
    metadata_producer_organization="My Organization",
    filename="output.xlsx",
    title="My Metadata",
    llm_base_url="http://localhost:11434/v1/",
    llm_model_name="llama3.1"
)

# Example with an Azure instance of a Large Language Model:
me.draft_metadata_from_files(
    llm_api_key="...",
    files=["/path/to/word_file1.docx", "http://www.example.com/report.pdf"],
    output_mode="pydantic",
    metadata_type_or_template_uid="indicator",
    metadata_producer_organization="My Organization",
    filename="output.xlsx",
    title="My Metadata",
    llm_base_url="https://my-azure-openai-resource.openai.azure.com/",
    azure_deployment_name="my-llm-deployment"
)
``` 

---


## <kbd>method</kbd> `generic_api_request`

```python
generic_api_request(
    method: str,
    endpoint: str,
    params: Optional[Dict] = None,
    data: Optional[Dict] = None,
    json: Optional[Dict] = None,
    files: Optional[Dict[str, BufferedReader]] = None
) → Dict
```

Make a generic API request to the Metadata Editor API. 

It's generally better to use the specific functions such as list_projects, create_project_log etc. but this function is provided for flexibility and to allow for future changes in the API. 



**Args:**
 
 - <b>`method`</b> (str):  Either 'POST' or 'GET' 
 - <b>`endpoint`</b> (str):  The path appended to the API_URL to which a GET or POST request is sent. 
 - <b>`params`</b> (optional dict):  additional parameters to send with a GET request. 
 - <b>`data`</b> (optional dict):  The data to send with a POST request. 
 - <b>`json`</b> (optional dict):  The JSON data to send with a POST request. 
 - <b>`files`</b> (optional dict[str, BufferedReader]):  The files to send with a POST request in the form ```{"filename": open(filename, "rb")}```.



**Returns:**


 - <b>`    Dict`</b>:  The response from the API as a dictionary.


---


## <kbd>method</kbd> `get_collection_by_id`

```python
get_collection_by_id(id: int) → Series
```

Get information about a collection like title, description, created date. 



**Args:**
 
 - <b>`id`</b> (int):  the id of the collection. 



**Returns:**
 
 - <b>`(pd.Series)`</b>:  a pandas series of the collection information 



**Raises:**
 
 - <b>`Exception`</b>:  You don't have permission to access this project - often this means the id is incorrect 

---


## <kbd>method</kbd> `get_metadata_class`

```python
get_metadata_class(metadata_type_or_template_uid: str) → Type[BaseModel]
```

Create a pydantic class of a given metadata type or template UID. 

If a metadata type is passed then the class will be created from the default template of that type. 



**Args:**
 
 - <b>`metadata_type_or_template_uid`</b> (str):  The metadata type or template UID. 



**Returns:**
 
 - <b>`Type[BaseModel]`</b>:  The pydantic class of the metadata. 



**Examples:**
 ```python
me = MetadataEditor(api_url=..., api_key=...)
indicator_metadata_class = me.get_metadata_class("indicator")
specific_metadata_class = me.get_metadata_class("timeseries-system-en")
``` 

---


## <kbd>method</kbd> `get_project_by_id`

```python
get_project_by_id(id: int) → Series
```

Retrieve information about a project such as the title, creator, creation date and last updated date. 



**Args:**
 
 - <b>`id`</b> (int):  the id of the project, not to be confused with the idno. 



**Returns:**
 
 - <b>`(pd.Series)`</b>:  project information 



**Raises:**
 
 - <b>`Exception`</b>:  You don't have permission to access this project - often this means the id is incorrect 

---


## <kbd>method</kbd> `get_project_metadata_by_id`

```python
get_project_metadata_by_id(
    id: int,
    output_mode: str,
    template_uid: Optional[str] = None,
    simplify: bool = True,
    filename: Optional[str] = None,
    title: Optional[str] = None,
    debug: bool = False
) → Union[BaseModel, Dict, str]
```

Return the metadata as a dictionary, pydantic object or saved to an Excel file. 



**Args:**
 
 - <b>`id`</b> (int):  the id of the project, not to be confused with the idno. 
 - <b>`output_mode`</b> (str):  The type of output. Must be 'dict', 'pydantic' or 'excel'. 
 - <b>`template_uid`</b> (Optional[str]):  The UID of the template to be applied to the logged metadata if different from  the template already associated with the project.  If None then the template listed in the logs will be used. And if the logs don't list a template then  the default template for that metadata type will be used.  The special value 'default' can be used to apply the default template for the metadata type.  When the output mode is 'dict' the special value 'none' can be used to remove the template from the  metadata and return whatever metadata was logged. 
 - <b>`simplify`</b> (bool):  If output_mode=='dict', then if simplify=True, only elements that were explicitly set with  non-null, non-empty values are returned in the dictionary. Default behaviour is True 
 - <b>`filename`</b> (Optional[str]):  If output_mode=='excel' then this is the path to the Excel file.  If None and output_mode=='excel', defaults to {name of metadata type}_metadata.xlsx 
 - <b>`title`</b> (Optional[str]):  If output_mode=='excel' then the title for the Excel sheet.  If None and mode=='excel', defaults to '{name of metadata type} Metadata' 
 - <b>`debug`</b> (bool):  If True, then the function will print out some internal, intermediate output. Default False. 



**Returns:**
 
 - <b>`(Union[BaseModel, Dict, str])`</b>:  If mode == 'dict', a dictionary is returned. If mode == 'pydantic', a  pydantic model object is returned. If mode == 'excel' then the metadata was saved to a file and the  filename is returned. 

---


## <kbd>method</kbd> `get_resources_by_id`

```python
get_resources_by_id(id: int) → DataFrame
```

List documentation (Reports, Questionnaires, Tables, etc.) for a project. 



**Args:**
 
 - <b>`id`</b> (int):  project id 



**Returns:**
 
 - <b>`(pd.DataFrame)`</b>:  resource information including titles, subtitles, authors and file formats 

---


## <kbd>method</kbd> `get_template_by_uid`

```python
get_template_by_uid(uid: str) → Series
```

Retrieves given template by *UID*, not id. 



**Args:**
 
 - <b>`uid`</b> (str):  The Unique Identifier of the template to retrieve. 



**Returns:**
 
 - <b>`pd.Series`</b>:  A pandas Series containing the template details. 

---


## <kbd>method</kbd> `list_collections`

```python
list_collections() → DataFrame
```

Lists all the collections associated with your API key. 



**Returns:**
 
 - <b>`pd.DataFrame`</b>:  Collection information 

---


## <kbd>method</kbd> `list_projects`

```python
list_projects(
    limit: Union[int, str],
    keywords: Optional[str, List[str]] = None,
    metadata_type: Optional[str] = None,
    offset: int = 0,
    sort_by: Optional[str] = None
) → DataFrame
```

Lists all the projects associated with your API key. 



**Args:**
 
 - <b>`limit`</b> (int or str):  Page size e.g. 10 to show 10 records. If limit='All' then all records are retrieved. 
 - <b>`keywords`</b> (optional str or list of str):  Keywords for filtering projects by title and/or idno. 
 - <b>`metadata_type`</b> (optional str):  If given, only projects of this type are returned. 
 - <b>`offset`</b> (int):  Offset for pagination e.g. 10 to skip first 10 records. Default is 0. 
 - <b>`sort_by`</b> (optional str):  valid values: "title_asc", "title_desc", "updated_asc", "updated_desc". 



**Returns:**
 
 - <b>`pd.DataFrame`</b>:  Information about the projects 

---


## <kbd>method</kbd> `list_projects_in_collection`

```python
list_projects_in_collection(
    collection: int,
    limit: Union[int, str],
    keywords: Optional[str, List[str]] = None,
    offset: int = 0,
    sort_by: Optional[str] = None
) → DataFrame
```

Retrieve projects that have been added to the given collection. 



**Args:**
 
 - <b>`collection`</b> (int):  The id of the collection. 
 - <b>`limit`</b> (int):  The maximum number of projects to return. If limit='All' then all records are retrieved. 
 - <b>`keywords`</b> (optional str or list of str):   filter projects based on whether the project title or idno contains  this keyword 
 - <b>`offset`</b> (int):  Offset for pagination e.g. 10 to skip first 10 records. Default is 0. 
 - <b>`sort_by`</b> (optional str):  valid values: "title_asc", "title_desc", "updated_asc", "updated_desc". 



**Returns:**
 
 - <b>`pd.DataFrame`</b>:  Information on the projects in the collection, such as id, idno, title and type. 

---


## <kbd>method</kbd> `list_templates`

```python
list_templates() → DataFrame
```

Retrieves templates, both standard and any custom templates. 



**Returns:**
 
 - <b>`pd.DataFrame`</b>:  A DataFrame containing the templates. If none are found, an empty DataFrame is returned. 

---


## <kbd>method</kbd> `log_resource`

```python
log_resource(
    project_id: int,
    dctype: str,
    title: str,
    author: Optional[str] = None,
    dcdate: Optional[str] = None,
    country: Optional[str] = None,
    language: Optional[str] = None,
    contributor: Optional[str] = None,
    publisher: Optional[str] = None,
    rights: Optional[str] = None,
    description: Optional[str] = None,
    abstract: Optional[str] = None,
    toc: Optional[str] = None,
    filename: Optional[str] = None
) → int
```

Log a new resource associated with a project (Reports, Questionnaires, Tables, etc). 

If filename is provided then the file is uploaded and logged. 



**Args:**
 
 - <b>`project_id`</b> (int):  The project id the resource is associated with. 
 - <b>`dctype`</b> (str):  The type of the resource (e.g., 'txt', 'pdf'). 
 - <b>`title`</b> (str):  The title of the resource. 
 - <b>`author`</b> (Optional[str]):  The author of the resource. Defaults to None. 
 - <b>`dcdate`</b> (Optional[str]):  The date of the resource. Defaults to None. 
 - <b>`country`</b> (Optional[str]):  The country associated with the resource. Defaults to None. 
 - <b>`language`</b> (Optional[str]):  The language of the resource. Defaults to None. 
 - <b>`contributor`</b> (Optional[str]):  The contributor to the resource. Defaults to None. 
 - <b>`publisher`</b> (Optional[str]):  The publisher of the resource. Defaults to None. 
 - <b>`rights`</b> (Optional[str]):  The rights associated with the resource. Defaults to None. 
 - <b>`description`</b> (Optional[str]):  A brief description of the resource. Defaults to None. 
 - <b>`abstract`</b> (Optional[str]):  An abstract summarizing the resource. Defaults to None. 
 - <b>`toc`</b> (Optional[str]):  The table of contents of the resource. Defaults to None. 
 - <b>`filename`</b> (Optional[str]):  The filename of the resource which will be uploaded. Defaults to None. 



**Returns:**
 
 - <b>`int`</b>:  The unique identifier of the logged resource. 

---


## <kbd>method</kbd> `make_metadata_outline`

```python
make_metadata_outline(
    metadata_type_or_template_uid: str,
    output_mode: str,
    filename: Optional[str] = None,
    title: Optional[str] = None
) → Union[Dict, BaseModel, Path]
```

Creates a skeleton outline of a given metadata type. 

Since the metadata can be quite complex, it's useful to start with all the possible fields and their subfields. 



**Args:**
 
 - <b>`metadata_type_or_template_uid`</b> (str): The type of a supported metadata type, currently:  document, geospatial, image, indicator, indicators_db, microdata, resource, script, table, video  If passed as a template UID then this template is retreived and an outline created. 
 - <b>`output_mode`</b> (str):  The type of output. Must be 'dict', 'pydantic' or 'excel'. 
 - <b>`filename`</b> (Optional[str]):  If output_mode=='excel', the path to the Excel file.  If None, defaults to {name of metadata type}_metadata.xlsx 
 - <b>`title`</b> (Optional[str]):  If output_mode=='excel', the title for the Excel sheet.  If None, defaults to '{name of metadata type} Metadata' 



**Returns:**
 
 - <b>``BaseModel` | `Dict` | `str``</b>:  If `output_mode == 'dict'`, a dictionary is returned.  If `output_mode == 'pydantic'`, a pydantic model object is returned.  If `output_mode == 'excel'`, the metadata was saved to a file and the filename is returned. 



**Examples:**
 ```python
me = MetadataEditor(api_url=..., api_key=...)

# using a metadata type will create an outline using the default template
indicator_dict = me.make_metadata_outline("indicator", "dict")
indicator_dict['metadata_information']['idno'] = "my_idno"

# using a template uid
indicator_pydantic = me.outline_metadata("timeseries-system-en", "pydantic")
indicator_pydantic.metadata_information.idno = "my_idno"

# an outline can also be written to an Excel file
path_to_indicator_excel_file = me.outline_metadata("indicator", "excel", "indicator_outline_metadata.xlsx")
``` 

---


## <kbd>method</kbd> `move_collection`

```python
move_collection(source_id, target_id)
```

Move source collection to be a sub-collection of the target collection. 



**Args:**
 
 - <b>`source_id`</b> (int):  The ID of the source collection. 
 - <b>`target_id`</b> (int):  The ID of the target collection. 

---


## <kbd>method</kbd> `patch_update_project_log_by_id`

```python
patch_update_project_log_by_id(
    id: int,
    op: str,
    path: str,
    value: Optional[str] = None
)
```

Add, update, or remove parts of a project's metadata using a single JSON Patch operation. 

"JSON Patch is a format for describing changes to a JSON document. It can be used to avoid sending a whole document when only a part has changed." - https://jsonpatch.com/ accessed 2024-08-20 

This method applies a single JSON Patch operation to update the metadata of a project specified by its ID. 

JSON Patch Operations: 


- "add": Adds a value to the specified path. If the path already exists, the value is replaced. 
- "remove": Removes the value at the specified path. 
- "replace": Replaces the value at the specified path with a new value. 
- "test": Tests that the specified path contains the given value. 

The `path` is a string that uses a slash (`/`) notation to specify the location within the JSON document. For example, `/author` refers to the "author" field, and `/metadata/title` refers to the "title" field inside the "metadata" object. If the path does not start with a `/`, the method will automatically prepend it. 



**Args:**
 
 - <b>`id`</b> (int):  The unique identifier of the project whose metadata is to be updated. 
 - <b>`op`</b> (str):  The JSON Patch operation to be applied. Valid operations are "add", "remove",  "replace", and "test". 
 - <b>`path`</b> (str):  The path in the project's metadata where the operation will be applied, using JSON  Pointer notation. 
 - <b>`value`</b> (Optional[str]):  The value to be added, replaced, or tested. Not required for "remove" operations. 



**Raises:**
 
 - <b>`ValueError`</b>:  If the provided operation, path, or value is invalid. 



**Example:**
 ```python
me = MetadataEditor(api_url = api_url, api_key = api_key)

# set the author of the project with ID 123 to "John Doe"
me.patch_update_project_log_by_id(id=123, op="add", path="/author", value="John Doe")

# test that the author is "John Doe"
me.patch_update_project_log_by_id(id=123, op="test", path="/author", value="John Doe")

# change the author to "Jane Doe"
me.patch_update_project_log_by_id(id=123, op="replace", path="/author", value="Jane Doe")

# remove the value of author
me.patch_update_project_log_by_id(id=123, op="remove", path="/author")
``` 

---


## <kbd>method</kbd> `read_metadata_from_excel`

```python
read_metadata_from_excel(
    filename: str,
    output_mode: str = 'pydantic',
    exclude_unset=True
) → Union[BaseModel, Dict]
```

Read metadata from an Excel file. 



**Args:**
 
 - <b>`filename`</b> (str):  The path to the Excel file. 
 - <b>`output_mode`</b> (str):  The output mode. Must be 'pydantic' or 'dict'. 
 - <b>`exclude_unset`</b> (bool):  If mode=='dict', then if exclude_unset=True, only elements that were explicitly set  with non-null, non-empty values are returned in the dictionary. 



**Returns:**
 
 - <b>`Union[BaseModel, Dict]`</b>:  The metadata object or dictionary. 

---


## <kbd>method</kbd> `remove_projects_from_collection`

```python
remove_projects_from_collection(
    collection: Union[int, List[int]],
    id_format: str,
    projects: Union[int, List[int], str, List[str]]
)
```

Removes project or projects from specified collection or collections. 

This method dissociates one or more projects from one or more collections. The `collection` parameter can be a single collection ID or a list of collection IDs. The `projects` parameter can be a single project ID, a single project ID number (idno), a list of project IDs, or a list of project idnos. The `id_format` parameter specifies whether the project identifiers are in the form of IDs or idnos. 

Note that if the project(s) are not in the collection there is no error raised since either way the project  will not be in the collection after this function executes 



**Args:**
 
 - <b>`collection `</b>:  Union[int, List[int]]  A single collection ID or a list of collection IDs to which projects should be removed. 


 - <b>`id_format `</b>:  str  Specifies the format of the project identifiers. Must be either 'id' or 'idno'. 


 - <b>`projects `</b>:  Union[int, List[int], str, List[str]]  A single project ID, a single project idno, a list of project IDs, or a list of  project idnos to be removed from the specified collection(s). 



**Raises:**
 
 - <b>`AssertionError`</b>:  If `id_format` is not 'id' or 'idno'.  If a project ID is not an integer when `id_format` is 'id'.  If a project ID number is not a string when `id_format` is 'idno'. 





**Example:**
 ```python
me = MetadataEditor(api_url = api_url, api_key = api_key)
me.remove_projects_from_collection(collection=1, id_format='id', projects=[101, 102])

me.remove_projects_from_collection(collection=[1, 2], id_format='idno', projects=['A101', 'A102'])
``` 

---


## <kbd>method</kbd> `save_metadata_to_excel`

```python
save_metadata_to_excel(
    metadata_model: BaseModel | dict | str,
    metadata_type_or_template_uid: Optional[str] = None,
    filename: Optional[str] = None,
    title: Optional[str] = None
) → str
```

Save a metadata object to an Excel file. 



**Args:**
 
 - <b>`metadata_model`</b> (BaseModel|dict|str):  The pydantic object, python dictionary or path to an Excel file. 
 - <b>`metadata_type_or_template_uid`</b> (Optional[str]):  If the metadata is a dictionary, this is the UID of the  template to use. Ignored if metadata is a pydantic model or a path to an Excel file. 
 - <b>`filename`</b> (Optional[str]):  The path to the output Excel file. Defaults to {name}_metadata.xlsx 
 - <b>`title`</b> (Optional[str]):  The title for the output Excel sheet. Defaults to '{name} Metadata' 



**Returns:**
 
 - <b>`str`</b>:  The path to the saved Excel file. 

---


## <kbd>method</kbd> `set_template_for_collection`

```python
set_template_for_collection(collection_id: int, template_uid: str)
```

Set the specified template to be used for all metadata of its type to a collection. 



**Args:**
 
 - <b>`collection_id`</b> (int):  the id of the collection. 
 - <b>`template_uid`</b> (str):  The Unique Identifier of the template to apply to the collection. 

---


## <kbd>method</kbd> `update_collection`

```python
update_collection(
    id: int,
    title: Optional[str] = None,
    description: Optional[str] = None
)
```

Updates the specified collection with a new title and/or description. 



**Args:**
 
 - <b>`id`</b> (int):  The unique identifier of the collection to update. 
 - <b>`title`</b> (Optional[str]):  The new title of the collection. Defaults to None. 
 - <b>`description`</b> (Optional[str]):  The new description of the collection. Defaults to None. 



**Raises:**
 
 - <b>`Assertion Error`</b>:  if both title and description are None, since we must update one or the other. 

---


## <kbd>method</kbd> `update_project_log_by_id`

```python
update_project_log_by_id(id: int, new_metadata: Union[BaseModel, Dict, str])
```

Updates the record of the metadata. 

If a dictionary is passed that only contains a subset of the possible keys then the remaining values not mentioned are left as is. 



**Args:**
 
 - <b>`id`</b> (int):  The ID of the metadata to update. 
 - <b>`new_metadata`</b> (dictionary, BaseModel or str):  If str, it's assumed this is a path to an appropriately  formatted Excel file 

---


## <kbd>method</kbd> `update_resource`

```python
update_resource(
    project_id: int,
    resource_id: int,
    dctype: str,
    title: str,
    author: Optional[str] = None,
    dcdate: Optional[str] = None,
    country: Optional[str] = None,
    language: Optional[str] = None,
    contributor: Optional[str] = None,
    publisher: Optional[str] = None,
    rights: Optional[str] = None,
    description: Optional[str] = None,
    abstract: Optional[str] = None,
    toc: Optional[str] = None,
    filename: Optional[str] = None
) → int
```

Update the log of resource associated with a project (Reports, Questionnaires, Tables, etc). 

If filename is provided then the file is uploaded and logged. 



**Args:**
 
 - <b>`project_id`</b> (int):  The project id the resource is associated with. 
 - <b>`resource_id`</b> (int):  The id of the resource. 
 - <b>`dctype`</b> (str):  The type of the resource (e.g., 'txt', 'pdf'). 
 - <b>`title`</b> (str):  The title of the resource. 
 - <b>`author`</b> (Optional[str]):  The author of the resource. Defaults to None. 
 - <b>`dcdate`</b> (Optional[str]):  The date of the resource. Defaults to None. 
 - <b>`country`</b> (Optional[str]):  The country associated with the resource. Defaults to None. 
 - <b>`language`</b> (Optional[str]):  The language of the resource. Defaults to None. 
 - <b>`contributor`</b> (Optional[str]):  The contributor to the resource. Defaults to None. 
 - <b>`publisher`</b> (Optional[str]):  The publisher of the resource. Defaults to None. 
 - <b>`rights`</b> (Optional[str]):  The rights associated with the resource. Defaults to None. 
 - <b>`description`</b> (Optional[str]):  A brief description of the resource. Defaults to None. 
 - <b>`abstract`</b> (Optional[str]):  An abstract summarizing the resource. Defaults to None. 
 - <b>`toc`</b> (Optional[str]):  The table of contents of the resource. Defaults to None. 
 - <b>`filename`</b> (Optional[str]):  The filename of the resource which will be uploaded. Defaults to None. 

