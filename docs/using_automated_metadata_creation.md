# Automatic Metadata Creation and Augmentation from Sources

The pyMetadaEditor tool can be used to automatically create and augment metadata. The tool is designed to write metadata based on the content of files, such as PDFs, word documents, powerpoint presentations, and web URLs. 

The tool can also be used to augment existing metadata by adding additional information from the content of the files.

The tool can be use models from OpenAI, but can also run locally using ollama or with a private LLM running in Azure.

We start by instantiating the metadata editor object:


```python
from pymetadataeditor import MetadataEditor
import os

your_api_key = os.getenv("API_KEY")
api_url = os.getenv("API_URL")
openai_key = os.getenv("OPENAI_KEY")
me = MetadataEditor(api_url=api_url, api_key=your_api_key, verify_ssl=False)

```


```python
me.list_projects(limit=1)
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
</tr>
<tr>
<th>id</th>
<th></th>
<th></th>
<th></th>
<th></th>
<th></th>
</tr>
</thead>
<tbody>
<tr>
<th>2202</th>
<td>document</td>
<td>644e84d5-9a0c-4dd2-8a66-ec27808a26e4</td>
<td>DEMO_DOC_001</td>
<td>The Analysis of Household Surveys: A Microecon...</td>
<td>None</td>
</tr>
</tbody>
</table>



Automatic metadata creations works for metadata types:
- microdata
- geospatial
- indicator
- document
- script
- video


We can create metadata from source files such as: 
- pdfs
- word
- excel
- powerpoint
- text files
- csv
- JSON
- XML
- ZIP files
- Images
- URLs

To run on an OpenAI model you will need an OpenAI API key.

Here is how to automatically create metadata, here we use two local PDFs:


```python
docs = ["../survey_records/cambodia/cambodia_lsms_basic_information_document.pdf", "../survey_records/cambodia/cambodia_living_standards_measurement_study_plus_manual_english.pdf"]

example = me.draft_metadata_from_files(llm_api_key=openai_key, 
                                       files=docs, 
                                       metadata_type_or_template_uid='microdata',
                                       output_mode='pydantic',
                                       metadata_producer_organization="The World Bank Group, DEC - Development Data Group"
                                       )
example.pretty_print()
```

    Read in ../survey_records/cambodia/cambodia_lsms_basic_information_document.pdf, running token count is 6381
    Read in ../survey_records/cambodia/cambodia_living_standards_measurement_study_plus_manual_english.pdf, running token count is 24910
    Sending to OpenAI, this may take a few minutes...



IHSN_DDI_2-<span style="color: #800080; text-decoration-color: #800080; font-weight: bold">5_Template_v01_EN</span><span style="font-weight: bold">(</span><span style="color: #808000; text-decoration-color: #808000">doc_desc</span>=<span style="color: #800080; text-decoration-color: #800080; font-weight: bold">doc_desc</span><span style="font-weight: bold">(</span><span style="color: #808000; text-decoration-color: #808000">producers</span>=<span style="font-weight: bold">[</span><span style="color: #800080; text-decoration-color: #800080; font-weight: bold">Producer</span><span style="font-weight: bold">(</span><span style="color: #808000; text-decoration-color: #808000">name</span>=<span style="color: #008000; text-decoration-color: #008000">'The World Bank Group, DEC - Development Data Group'</span>,
                <span style="color: #808000; text-decoration-color: #808000">abbr</span>=<span style="color: #008000; text-decoration-color: #008000">'WBG'</span>,
                <span style="color: #808000; text-decoration-color: #808000">affiliation</span>=<span style="color: #008000; text-decoration-color: #008000">'The World Bank Group'</span>,
                <span style="color: #808000; text-decoration-color: #808000">role</span>=<span style="color: #008000; text-decoration-color: #008000">'Metadata Producer'</span><span style="font-weight: bold">)</span><span style="font-weight: bold">]</span>,
        <span style="color: #808000; text-decoration-color: #808000">prod_date</span>=<span style="color: #008000; text-decoration-color: #008000">'2025-02-26'</span>,
        <span style="color: #808000; text-decoration-color: #808000">idno</span>=<span style="color: #008000; text-decoration-color: #008000">'IHSN_DDI_v01_WBG_LSMS+_KHM_2025'</span>,
        <span style="color: #808000; text-decoration-color: #808000">version_statement</span>=<span style="color: #800080; text-decoration-color: #800080; font-weight: bold">version_statement</span><span style="font-weight: bold">(</span><span style="color: #808000; text-decoration-color: #808000">version</span>=<span style="color: #008000; text-decoration-color: #008000">'v01'</span>,
            <span style="color: #808000; text-decoration-color: #808000">version_date</span>=<span style="color: #008000; text-decoration-color: #008000">'2025-02-26'</span>,
            <span style="color: #808000; text-decoration-color: #808000">version_resp</span>=<span style="color: #008000; text-decoration-color: #008000">'The World Bank Group, DEC - Development Data Group'</span>,
            <span style="color: #808000; text-decoration-color: #808000">version_notes</span>=<span style="color: #008000; text-decoration-color: #008000">'Initial version.'</span><span style="font-weight: bold">)</span><span style="font-weight: bold">)</span>,
    <span style="color: #808000; text-decoration-color: #808000">study_desc</span>=<span style="color: #800080; text-decoration-color: #800080; font-weight: bold">study_desc</span><span style="font-weight: bold">(</span><span style="color: #808000; text-decoration-color: #808000">title_statement</span>=<span style="color: #800080; text-decoration-color: #800080; font-weight: bold">title_statement</span><span style="font-weight: bold">(</span><span style="color: #808000; text-decoration-color: #808000">title</span>=<span style="color: #008000; text-decoration-color: #008000">'Cambodia Living Standards Measurement Study - Plus 2019-2020'</span>,
            <span style="color: #808000; text-decoration-color: #808000">sub_title</span>=<span style="color: #800080; text-decoration-color: #800080; font-style: italic">None</span>,
            <span style="color: #808000; text-decoration-color: #808000">alternate_title</span>=<span style="color: #008000; text-decoration-color: #008000">'Cambodia LSMS+ 2019-20'</span>,
            <span style="color: #808000; text-decoration-color: #808000">translated_title</span>=<span style="color: #008000; text-decoration-color: #008000">'\x0b\x00b\x000b\x000b\x0b\x0b\x0b\x0b\x0b'</span>,
            <span style="color: #808000; text-decoration-color: #808000">idno</span>=<span style="color: #008000; text-decoration-color: #008000">'LSMS+_KHM_2019-2020'</span>,
            <span style="color: #808000; text-decoration-color: #808000">identifiers</span>=<span style="font-weight: bold">[]</span><span style="font-weight: bold">)</span>,
        <span style="color: #808000; text-decoration-color: #808000">series_statement</span>=<span style="color: #800080; text-decoration-color: #800080; font-weight: bold">series_statement</span><span style="font-weight: bold">(</span><span style="color: #808000; text-decoration-color: #808000">series_name</span>=<span style="color: #008000; text-decoration-color: #008000">'Living Standards Measurement Study - Plus'</span>...


The output can be converted to a dictionary or saved to an Excel file.


```python
metadata_dictionary = me.change_mode_or_template(example, output_mode='dict')
```


```python
me.save_metadata_to_excel(example, "cambodia_metadata.xlsx")
```

If we like the draft of the metadata, we can log it in the Metadata Editor in the usual way:


```python
me.create_project_log(example)
```

# Web URL

Similarly, if the source is a web URL, we can create metadata from the content of the web page by passing the URL to the `draft_metadata_from_files` method:


```python
docs = ['https://data.worldbank.org/indicator/NY.GDP.MKTP.CD']

example_gdp = me.draft_metadata_from_files(llm_api_key=openai_key, 
                                       files=docs, 
                                       metadata_type_or_template_uid='indicator',
                                       output_mode='pydantic',
                                       metadata_producer_organization="The World Bank Group, DEC - Development Data Group"
                                       )
example_gdp.pretty_print()
```

    Read in https://data.worldbank.org/indicator/NY.GDP.MKTP.CD, running token count is 1839
    Sending to OpenAI, this may take a few minutes...



IHSN_INDICATOR_1-<span style="color: #800080; text-decoration-color: #800080; font-weight: bold">0_Template_v01_EN</span><span style="font-weight: bold">(</span><span style="color: #808000; text-decoration-color: #808000">metadata_information</span>=<span style="color: #800080; text-decoration-color: #800080; font-weight: bold">metadata_information</span><span style="font-weight: bold">(</span><span style="color: #808000; text-decoration-color: #808000">title</span>=<span style="color: #008000; text-decoration-color: #008000">'GDP (current US$) Metadata'</span>,
        <span style="color: #808000; text-decoration-color: #808000">idno</span>=<span style="color: #008000; text-decoration-color: #008000">'WB_NY.GDP.MKTP.CD_v2025-02-26'</span>,
        <span style="color: #808000; text-decoration-color: #808000">producers</span>=<span style="font-weight: bold">[</span><span style="color: #800080; text-decoration-color: #800080; font-weight: bold">Producer</span><span style="font-weight: bold">(</span><span style="color: #808000; text-decoration-color: #808000">name</span>=<span style="color: #008000; text-decoration-color: #008000">'The World Bank Group'</span>,
                <span style="color: #808000; text-decoration-color: #808000">abbr</span>=<span style="color: #800080; text-decoration-color: #800080; font-style: italic">None</span>,
                <span style="color: #808000; text-decoration-color: #808000">affiliation</span>=<span style="color: #008000; text-decoration-color: #008000">'DEC - Development Data Group'</span>,
                <span style="color: #808000; text-decoration-color: #808000">role</span>=<span style="color: #008000; text-decoration-color: #008000">'Metadata producer'</span><span style="font-weight: bold">)</span><span style="font-weight: bold">]</span>,
        <span style="color: #808000; text-decoration-color: #808000">prod_date</span>=<span style="color: #008000; text-decoration-color: #008000">'2025-02-26'</span>,
        <span style="color: #808000; text-decoration-color: #808000">version_statement</span>=<span style="color: #800080; text-decoration-color: #800080; font-weight: bold">version_statement</span><span style="font-weight: bold">(</span><span style="color: #808000; text-decoration-color: #808000">version</span>=<span style="color: #800080; text-decoration-color: #800080; font-style: italic">None</span>,
            <span style="color: #808000; text-decoration-color: #808000">version_date</span>=<span style="color: #800080; text-decoration-color: #800080; font-style: italic">None</span>,
            <span style="color: #808000; text-decoration-color: #808000">version_notes</span>=<span style="color: #800080; text-decoration-color: #800080; font-style: italic">None</span>,
            <span style="color: #808000; text-decoration-color: #808000">version_resp</span>=<span style="color: #800080; text-decoration-color: #800080; font-style: italic">None</span><span style="font-weight: bold">)</span><span style="font-weight: bold">)</span>,
    <span style="color: #808000; text-decoration-color: #808000">series_description</span>=<span style="color: #800080; text-decoration-color: #800080; font-weight: bold">series_description</span><span style="font-weight: bold">(</span><span style="color: #808000; text-decoration-color: #808000">idno</span>=<span style="color: #008000; text-decoration-color: #008000">'NY.GDP.MKTP.CD'</span>,
        <span style="color: #808000; text-decoration-color: #808000">alternate_identifiers</span>=<span style="font-weight: bold">[</span><span style="color: #800080; text-decoration-color: #800080; font-weight: bold">Alternate_identifier</span><span style="font-weight: bold">(</span><span style="color: #808000; text-decoration-color: #808000">name</span>=<span style="color: #800080; text-decoration-color: #800080; font-style: italic">None</span>, <span style="color: #808000; text-decoration-color: #808000">identifier</span>=<span style="color: #800080; text-decoration-color: #800080; font-style: italic">None</span>, <span style="color: #808000; text-decoration-color: #808000">database</span>=<span style="color: #800080; text-decoration-color: #800080; font-style: italic">None</span>, <span style="color: #808000; text-decoration-color: #808000">uri</span>=<span style="color: #800080; text-decoration-color: #800080; font-style: italic">None</span>, <span style="color: #808000; text-decoration-color: #808000">notes</span>=<span style="color: #800080; text-decoration-color: #800080; font-style: italic">None</span><span style="font-weight: bold">)</span><span style="font-weight: bold">]</span>,
        <span style="color: #808000; text-decoration-color: #808000">name</span>...


# Augmenting existing metadata

If we already have some metadata, we can retrieve it from the Metadata Editor and augment it with additional information from the content of some files:

First retrieve the existing metadata:


```python
existing_metadata = me.get_project_metadata_by_id(2202, output_mode='pydantic')

existing_metadata.pprint()
```


IHSN_DOCUMENT_1-<span style="color: #800080; text-decoration-color: #800080; font-weight: bold">0_Template_v01_EN</span><span style="font-weight: bold">(</span><span style="color: #808000; text-decoration-color: #808000">metadata_information</span>=<span style="color: #800080; text-decoration-color: #800080; font-weight: bold">metadata_information</span><span style="font-weight: bold">(</span><span style="color: #808000; text-decoration-color: #808000">title</span>=<span style="color: #008000; text-decoration-color: #008000">'Metadata for: The Analysis of Household Surveys'</span>,
        <span style="color: #808000; text-decoration-color: #808000">idno</span>=<span style="color: #008000; text-decoration-color: #008000">'IHSN_978-1-4648-1331-3_v1.0'</span>,
        <span style="color: #808000; text-decoration-color: #808000">producers</span>=<span style="font-weight: bold">[</span><span style="color: #800080; text-decoration-color: #800080; font-weight: bold">Producer</span><span style="font-weight: bold">(</span><span style="color: #808000; text-decoration-color: #808000">name</span>=<span style="color: #008000; text-decoration-color: #008000">'John Doe'</span>, <span style="color: #808000; text-decoration-color: #808000">abbr</span>=<span style="color: #800080; text-decoration-color: #800080; font-style: italic">None</span>, <span style="color: #808000; text-decoration-color: #808000">affiliation</span>=<span style="color: #008000; text-decoration-color: #008000">'IHSN'</span>, <span style="color: #808000; text-decoration-color: #808000">role</span>=<span style="color: #008000; text-decoration-color: #008000">'Data Curator'</span><span style="font-weight: bold">)]</span>,
        <span style="color: #808000; text-decoration-color: #808000">production_date</span>=<span style="color: #008000; text-decoration-color: #008000">'2024-09-30'</span>,
        <span style="color: #808000; text-decoration-color: #808000">version</span>=<span style="color: #008000; text-decoration-color: #008000">''</span><span style="font-weight: bold">)</span>,
    <span style="color: #808000; text-decoration-color: #808000">document_description</span>=<span style="color: #800080; text-decoration-color: #800080; font-weight: bold">document_description</span><span style="font-weight: bold">(</span><span style="color: #808000; text-decoration-color: #808000">title_statement</span>=<span style="color: #800080; text-decoration-color: #800080; font-weight: bold">title_statement</span><span style="font-weight: bold">(</span><span style="color: #808000; text-decoration-color: #808000">idno</span>=<span style="color: #008000; text-decoration-color: #008000">'DEMO_DOC_001'</span>,
            <span style="color: #808000; text-decoration-color: #808000">title</span>=<span style="color: #008000; text-decoration-color: #008000">'The Analysis of Household Surveys: A Microeconometric Approach to Development Policy'</span>,
            <span style="color: #808000; text-decoration-color: #808000">sub_title</span>=<span style="color: #800080; text-decoration-color: #800080; font-style: italic">None</span>,
            <span style="color: #808000; text-decoration-color: #808000">alternate_title</span>=<span style="color: #800080; text-decoration-color: #800080; font-style: italic">None</span>,
            <span style="color: #808000; text-decoration-color: #808000">translated_title</span>=<span style="color: #800080; text-decoration-color: #800080; font-style: italic">None</span><span style="font-weight: bold">)</span>,
        <span style="color: #808000; text-decoration-color: #808000">identifiers</span>=<span style="font-weight: bold">[</span><span style="color: #800080; text-decoration-color: #800080; font-weight: bold">Identifier</span><span style="font-weight: bold">(</span><span style="color: #808000; text-decoration-color: #808000">type</span>=<span style="color: #008000; text-decoration-color: #008000">'ISBN'</span>, <span style="color: #808000; text-decoration-color: #808000">identifier</span>=<span style="color: #008000; text-decoration-color: #008000">'978-1-4648-1331-3'</span><span style="font-weight: bold">)]</span>,
        <span style="color: #808000; text-decoration-color: #808000">date_created</span>=<span style="color: #008000; text-decoration-color: #008000">'2019-01-16'</span>,
        <span style="color: #808000; text-decoration-color: #808000">date_published</span>=<span style="color: #800080; text-decoration-color: #800080; font-style: italic">None</span>,
        <span style="color: #808000; text-decoration-color: #808000">date_modified</span>=<span style="color: #800080; text-decoration-color: #800080; font-style: italic">None</span>...


Then augment the metadata with additional information from the content of the files. In this example, the original metadata was an incomplete record about a document. One way to augment this is to find the original document, in this case a PDF on the web, and use the `augment_metadata_from_files` method.

To make it obvious which fields were in the original metadata and which were added, we can set the prefix to `<AI>` which will be added to the fields that were added by the Large Language Model.


```python
docs = ["https://documents1.worldbank.org/curated/en/593871468777303124/pdf/17140-PUB-revised-PUBLIC-9781464813313-Updated.pdf"]
augmented = me.augment_metadata_from_files(input_metadata=existing_metadata,
                                           llm_api_key=openai_key,
                                           files=docs,
                                           output_mode='pydantic',
                                           metadata_producer_organization="The World Bank Group, DEC - Development Data Group",
                                           prefix="<AI>"
                                           )

augmented.pprint()
```

    Read in /var/folders/jv/htm9fs717y350bv788702w000000gp/T/tmpajh5p86n.txt, running token count is 633
    Read in https://documents1.worldbank.org/curated/en/593871468777303124/pdf/17140-PUB-revised-PUBLIC-9781464813313-Updated.pdf, running token count is 8378
    Sending to OpenAI, this may take a few minutes...



IHSN_DOCUMENT_1-<span style="color: #800080; text-decoration-color: #800080; font-weight: bold">0_Template_v01_EN</span><span style="font-weight: bold">(</span><span style="color: #808000; text-decoration-color: #808000">metadata_information</span>=<span style="color: #800080; text-decoration-color: #800080; font-weight: bold">metadata_information</span><span style="font-weight: bold">(</span><span style="color: #808000; text-decoration-color: #808000">title</span>=<span style="color: #008000; text-decoration-color: #008000">'Metadata for: The Analysis of Household Surveys'</span>,
        <span style="color: #808000; text-decoration-color: #808000">idno</span>=<span style="color: #008000; text-decoration-color: #008000">'IHSN_978-1-4648-1331-3_v1.0'</span>,
        <span style="color: #808000; text-decoration-color: #808000">producers</span>=<span style="font-weight: bold">[</span><span style="color: #800080; text-decoration-color: #800080; font-weight: bold">Producer</span><span style="font-weight: bold">(</span><span style="color: #808000; text-decoration-color: #808000">name</span>=<span style="color: #008000; text-decoration-color: #008000">'John Doe'</span>, <span style="color: #808000; text-decoration-color: #808000">abbr</span>=<span style="color: #800080; text-decoration-color: #800080; font-style: italic">None</span>, <span style="color: #808000; text-decoration-color: #808000">affiliation</span>=<span style="color: #008000; text-decoration-color: #008000">'IHSN'</span>, <span style="color: #808000; text-decoration-color: #808000">role</span>=<span style="color: #008000; text-decoration-color: #008000">'Data Curator'</span><span style="font-weight: bold">)]</span>,
        <span style="color: #808000; text-decoration-color: #808000">production_date</span>=<span style="color: #008000; text-decoration-color: #008000">'2024-09-30'</span>,
        <span style="color: #808000; text-decoration-color: #808000">version</span>=<span style="color: #008000; text-decoration-color: #008000">''</span><span style="font-weight: bold">)</span>,
    <span style="color: #808000; text-decoration-color: #808000">document_description</span>=<span style="color: #800080; text-decoration-color: #800080; font-weight: bold">document_description</span><span style="font-weight: bold">(</span><span style="color: #808000; text-decoration-color: #808000">title_statement</span>=<span style="color: #800080; text-decoration-color: #800080; font-weight: bold">title_statement</span><span style="font-weight: bold">(</span><span style="color: #808000; text-decoration-color: #808000">idno</span>=<span style="color: #008000; text-decoration-color: #008000">'DEMO_DOC_001'</span>,
            <span style="color: #808000; text-decoration-color: #808000">title</span>=<span style="color: #008000; text-decoration-color: #008000">'The Analysis of Household Surveys: A Microeconometric Approach to Development Policy'</span>,
            <span style="color: #808000; text-decoration-color: #808000">sub_title</span>=<span style="color: #800080; text-decoration-color: #800080; font-style: italic">None</span>,
            <span style="color: #808000; text-decoration-color: #808000">alternate_title</span>=<span style="color: #800080; text-decoration-color: #800080; font-style: italic">None</span>,
            <span style="color: #808000; text-decoration-color: #808000">translated_title</span>=<span style="color: #800080; text-decoration-color: #800080; font-style: italic">None</span><span style="font-weight: bold">)</span>,
        <span style="color: #808000; text-decoration-color: #808000">identifiers</span>=<span style="font-weight: bold">[</span><span style="color: #800080; text-decoration-color: #800080; font-weight: bold">Identifier</span><span style="font-weight: bold">(</span><span style="color: #808000; text-decoration-color: #808000">type</span>=<span style="color: #008000; text-decoration-color: #008000">'ISBN'</span>, <span style="color: #808000; text-decoration-color: #808000">identifier</span>=<span style="color: #008000; text-decoration-color: #008000">'978-1-4648-1331-3'</span><span style="font-weight: bold">)]</span>,
        <span style="color: #808000; text-decoration-color: #808000">date_created</span>=<span style="color: #008000; text-decoration-color: #008000">'2019-01-16'</span>,
        <span style="color: #808000; text-decoration-color: #808000">date_published</span>=<span style="color: #800080; text-decoration-color: #800080; font-style: italic">None</span>,
        <span style="color: #808000; text-decoration-color: #808000">date_modified</span>=<span style="color: #800080; text-decoration-color: #800080; font-style: italic">None</span>...


# Privacy

There are options for running privately without sharing the data with OpenAI.

## Running Locally

One option is to run the LLM on your personal computer. To do this you first need to download and install [Ollama](https://ollama.com/).

Ollama is a framework for running, managing, and serving large language models (LLMs) locally on a user's machine. It provides an easy-to-use interface for downloading, running, and interacting with models like Llama, Mistral, and others without requiring cloud-based services.

Once you have Ollama installed, you can download the LLMs you want to use. For example, to download the llama3.1 model, you would run:

```bash
ollama pull llama3.1
```
Then you must serve the model locally using:

```bash
ollama serve llama3.1
```

To check if the model is running, you can use:

```bash
ollama ps
```

To stop the model from running, you can use:

```bash
ollama stop llama3.1
```

And you can delete the model if you no longer need it:

```bash
ollama rm llama3.1
```

When the model is being served, you can use it in the pyMetadataEditor code by setting the llm_api_key to `ollama`, the llm_model_name to `llama3.1`, and the llm_base_url to `http://localhost:11434/v1/`.

It's important to remember that usually models that are small enough to run locally won't produce metadata as good as the larger models that are available remotely such as through OpenAI.


```python
docs = ['https://data.worldbank.org/indicator/NY.GDP.MKTP.CD']

example_gdp = me.draft_metadata_from_files(llm_api_key="ollama",  # pragma: allowlist secret
                                       files=docs, 
                                       metadata_type_or_template_uid='indicator',
                                       output_mode='pydantic',
                                       metadata_producer_organization="The World Bank Group, DEC - Development Data Group",
                                       llm_base_url='http://localhost:11434/v1',
                                       llm_model_name='llama3.1'
                                       )
example_gdp.pretty_print()
```

    Read in https://data.worldbank.org/indicator/NY.GDP.MKTP.CD, running token count is 1839
    Sending to http://localhost:11434/v1, this may take a few minutes...



IHSN_INDICATOR_1-<span style="color: #800080; text-decoration-color: #800080; font-weight: bold">0_Template_v01_EN</span><span style="font-weight: bold">(</span><span style="color: #808000; text-decoration-color: #808000">metadata_information</span>=<span style="color: #800080; text-decoration-color: #800080; font-weight: bold">metadata_information</span><span style="font-weight: bold">(</span><span style="color: #808000; text-decoration-color: #808000">title</span>=<span style="color: #008000; text-decoration-color: #008000">''</span>,
        <span style="color: #808000; text-decoration-color: #808000">idno</span>=<span style="color: #008000; text-decoration-color: #008000">''</span>,
        <span style="color: #808000; text-decoration-color: #808000">producers</span>=<span style="font-weight: bold">[</span><span style="color: #800080; text-decoration-color: #800080; font-weight: bold">Producer</span><span style="font-weight: bold">(</span><span style="color: #808000; text-decoration-color: #808000">name</span>=<span style="color: #008000; text-decoration-color: #008000">'The World Bank Group'</span>,
                <span style="color: #808000; text-decoration-color: #808000">abbr</span>=<span style="color: #008000; text-decoration-color: #008000">'WBG'</span>,
                <span style="color: #808000; text-decoration-color: #808000">affiliation</span>=<span style="color: #008000; text-decoration-color: #008000">'DEC - Development Data Group'</span>,
                <span style="color: #808000; text-decoration-color: #808000">role</span>=<span style="color: #008000; text-decoration-color: #008000">'Producer'</span><span style="font-weight: bold">)</span><span style="font-weight: bold">]</span>,
        <span style="color: #808000; text-decoration-color: #808000">prod_date</span>=<span style="color: #008000; text-decoration-color: #008000">'2025-02-26'</span>,
        <span style="color: #808000; text-decoration-color: #808000">version_statement</span>=<span style="color: #800080; text-decoration-color: #800080; font-weight: bold">version_statement</span><span style="font-weight: bold">(</span><span style="color: #808000; text-decoration-color: #808000">version</span>=<span style="color: #008000; text-decoration-color: #008000">''</span>, <span style="color: #808000; text-decoration-color: #808000">version_date</span>=<span style="color: #008000; text-decoration-color: #008000">''</span>, <span style="color: #808000; text-decoration-color: #808000">version_notes</span>=<span style="color: #008000; text-decoration-color: #008000">''</span>, <span style="color: #808000; text-decoration-color: #808000">version_resp</span>=<span style="color: #008000; text-decoration-color: #008000">''</span><span style="font-weight: bold">)</span><span style="font-weight: bold">)</span>,
    <span style="color: #808000; text-decoration-color: #808000">series_description</span>=<span style="color: #800080; text-decoration-color: #800080; font-weight: bold">series_description</span><span style="font-weight: bold">(</span><span style="color: #808000; text-decoration-color: #808000">idno</span>=<span style="color: #008000; text-decoration-color: #008000">'NY.GDP.MKTP.CD'</span>,
        <span style="color: #808000; text-decoration-color: #808000">alternate_identifiers</span>=<span style="font-weight: bold">[</span><span style="color: #800080; text-decoration-color: #800080; font-weight: bold">Alternate_identifier</span><span style="font-weight: bold">(</span><span style="color: #808000; text-decoration-color: #808000">name</span>=<span style="color: #008000; text-decoration-color: #008000">'NY.GDP.MKTP.CD'</span>,
                <span style="color: #808000; text-decoration-color: #808000">identifier</span>=<span style="color: #008000; text-decoration-color: #008000">'GDP (current US$)'</span>,
                <span style="color: #808000; text-decoration-color: #808000">database</span>=<span style="color: #008000; text-decoration-color: #008000">'World Bank national accounts data, and OECD National Accounts data files.'</span>,
                <span style="color: #808000; text-decoration-color: #808000">uri</span>=<span style="color: #008000; text-decoration-color: #008000">'/indicator/NY.GDP.MKTP.CD'</span>,
                <span style="color: #808000; text-decoration-color: #808000">notes</span>=<span style="color: #008000; text-decoration-color: #008000">'The World Bank Group is not responsible for the accuracy of the data. The World Bank Group </span><span style="color: #008000; text-decoration-color: #008000">does not guarantee its use, completeness, timeliness, security, or exportability.'</span><span style="font-weight: bold">)</span><span style="font-weight: bold">]</span>,
        ...


## Azure AI Services

Another option for running LLMs privately is to use a service like Azure AI Services.

Often organizations will have their own instance of an LLM within a service like Azure by Microsoft. Often they do to have more control over their data. 

You can use these services to augment your metadata by providing an endpoint (such as https://{your-resource-name}.openai.azure.com) and an API key.


**(The below error is expected as only a dummy url has been provided.)**


```python
me.augment_metadata_from_files(input_metadata=existing_metadata,
                               llm_api_key=os.getenv("API_KEY_FOR_AZURE_INSTANCE_OF_LLM"),
                               files=docs,
                               output_mode='pydantic',
                               metadata_producer_organization="The World Bank Group, DEC - Development Data Group",
                               prefix="<AI>",
                               azure_llm_base_url="https://{your-resource-name}.openai.azure.com"
                               ).pprint()
```

    Read in /var/folders/jv/htm9fs717y350bv788702w000000gp/T/tmpahk3tt2q.txt, running token count is 626
    Read in https://documents1.worldbank.org/curated/en/593871468777303124/pdf/17140-PUB-revised-PUBLIC-9781464813313-Updated.pdf, running token count is 8371
    Sending to https://{your-resource-name}.openai.azure.com, this may take a few minutes...



    APIConnectionError: Connection error.

