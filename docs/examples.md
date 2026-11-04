# Examples of Common Tasks for the pyMetadataEditor

Coded examples of common tasks for managing metadata with the `pyMetadataEditor`.

Code can be written by a Large Language Model such as ChatGPT. For this we recommend uploading the API Reference markdown file which described every function and its parameters, it can be found [here](https://github.com/mah0001/pymetadataeditor/blob/main/docs/API_Reference.md)

An example of using an LLM to write pyMetadataEditor code is here:

![Upload the API_reference and then ask ChatGPT to write python code, in this case the create a new collection and copy all the indicators from another collection into it.](<../docs/images/LLM_example.png>)

## Examples

All examples require the MetadataEditor object to be created first.


```python
from pymetadataeditor import MetadataEditor
import os
```


```python
your_api_key = os.getenv("API_KEY")
api_url = os.getenv("API_URL")
me = MetadataEditor(api_url=api_url, api_key=your_api_key)
```

### Moving a subset of projects from one collection to another


```python
new_collection_title = "My new collection"
new_collection_description = "This is a new collection"

source_collection_id = 17
```


```python
# Step 1: Create a new collection
new_collection_id = me.create_collection(title=new_collection_title, description=new_collection_description)

# Step 2: List projects in the source collection
projects_df = me.list_projects_in_collection(collection=source_collection_id, limit="All")

# Step 3: Filter for indicators (assuming type column exists)
indicator_projects = projects_df[projects_df["type"] == "indicator"]

# Step 4: Copy indicators to the new collection
project_ids = indicator_projects["id"].tolist()
me.add_projects_to_collection(collection=new_collection_id, id_format="id", projects=project_ids)

# Step 5: Remove the indicators from the source collection
me.remove_projects_from_collection(collection=source_collection_id, id_format="id", projects=project_ids)

```

### Upload a batch of projects from a custom Excel file

In this example, we assume that there are many indicators listed in an excel file, one indicator per row. The file looks something like

| name | idno | doi | definition_long | 
|------|------|-----|-----------------|
| Indicator 1 | 1 | 10.1234/5678 | This is a long definition of Indicator 1 |
| Indicator 2 | 2 | 10.1234/5679 | This is a long definition of Indicator 2 |
| Indicator 3 | 3 | 10.1234/5680 | This is a long definition of Indicator 3 |


```python
# Step 1: Read in the file
import pandas as pd
df = pd.read_excel("path/to/file.xlsx")

# track the uploaded metadata
uploaded_metadata_ids = []

# Step 2: Iterate over the rows
for i, row in df.iterrows():
    # Step 3: Create the metadata outline
    metadata = me.make_metadata_outline('indicator', 'pydantic')

    # Step 4: Fill in the metadata - adapt to the column names in your file
    metadata.series_description.name = row["name"]
    metadata.series_description.definition_long = row["definition_long"]
    metadata.series_description.display_name = row["display_name"]
    metadata.series_description.idno = row["idno"]
    metadata.series_description.doi = row["doi"]

    # Step 5: Upload the metadata to the MetadataEditor
    metadata_id = me.create_metadata(metadata)
    uploaded_metadata_ids.append(metadata_id)
```

### Moving data from one instance of MetadataEditor to another

Perhaps you have two instances of MetadataEditor, one for the development environment and one for the production environment. You want to move some projects from the development environment to the production environment.

For this you will need to instantiate two MetadataEditor objects, one for each environment. **This method assumes that the templates are the same in both environments.**


```python
dev_collection_id = 1

# Step 1: Connect to the dev instance of the MetadataEditor
dev_api_key = os.getenv("API_KEY")
dev_url = os.getenv("API_URL")
me_dev = MetadataEditor(api_url=dev_url, api_key=dev_api_key)

# Step 2: List the projects in a collection in the dev instance which will be copied to the prod instance
dev_projects_df = me_dev.list_projects_in_collection(collection=dev_collection_id, limit="All")

# track the uploaded metadata
uploaded_metadata_ids = []

# Step 3: Iterate through the list
for i, row in dev_projects_df.iterrows():
    # Step 4: Download the metadata from the dev instance
    metadata = me_dev.get_metadata(row["id"])

    # Step 5: Upload the metadata to the prod instance
    metadata_id = me.create_metadata(metadata)
    uploaded_metadata_ids.append(metadata_id)
```
