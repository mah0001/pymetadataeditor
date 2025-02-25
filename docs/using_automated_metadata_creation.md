# Automatic Metadata Creation and Augmentation from Sources


```python
from pymetadataeditor import MetadataEditor
import os

your_api_key = os.getenv("API_KEY")
api_url = os.getenv("API_URL")
openai_key = os.getenv("OPENAI_KEY")
me = MetadataEditor(api_url=api_url, api_key=your_api_key, verify_ssl=False)

```


```python
me.list_projects(limit=5)
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
<th>2202</th>
<td>document</td>
<td>644e84d5-9a0c-4dd2-8a66-ec27808a26e4</td>
<td>DEMO_DOC_001</td>
<td>The Analysis of Household Surveys: A Microecon...</td>
<td>None</td>
<td></td>
<td>0</td>
<td>0</td>
<td>None</td>
<td>2024-10-01T16:09:09+00:00</td>
<td>2025-01-04T01:17:32+00:00</td>
<td>None</td>
<td>25</td>
<td>25</td>
<td>None</td>
<td>thumbnail-2202.png</td>
<td>2f62a6b2716ab55b4426005abdbe1600</td>
<td>vmascarinas</td>
<td>vmascarinas</td>
<td>[{'id': '85', 'title': 'Demo Collection', 'sid...</td>
</tr>
<tr>
<th>3489</th>
<td>survey</td>
<td>ec99e41a-e8fb-4fea-a89f-1c4cc69dd641</td>
<td>NULL</td>
<td>Example</td>
<td>None</td>
<td></td>
<td>0</td>
<td>0</td>
<td>None</td>
<td>2024-12-17T16:14:38+00:00</td>
<td>2024-12-17T16:14:38+00:00</td>
<td>None</td>
<td>24</td>
<td>24</td>
<td>None</td>
<td>None</td>
<td>6740f5f920502baf3f6cbcaa5c113deeen</td>
<td>Gordon Blackadder</td>
<td>Gordon Blackadder</td>
<td>[]</td>
</tr>


</tbody>
</table>



Works for metadata types:
- microdata
- geospatial
- indicator
- document
- script
- video


Can create metadata from source files of type: 
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
                <span style="color: #808000; text-decoration-color: #808000">abbr</span>=<span style="color: #800080; text-decoration-color: #800080; font-style: italic">None</span>,
                <span style="color: #808000; text-decoration-color: #808000">affiliation</span>=<span style="color: #800080; text-decoration-color: #800080; font-style: italic">None</span>,
                <span style="color: #808000; text-decoration-color: #808000">role</span>=<span style="color: #800080; text-decoration-color: #800080; font-style: italic">None</span><span style="font-weight: bold">)</span><span style="font-weight: bold">]</span>,
        <span style="color: #808000; text-decoration-color: #808000">prod_date</span>=<span style="color: #008000; text-decoration-color: #008000">'2025-02-06'</span>,
        <span style="color: #808000; text-decoration-color: #808000">idno</span>=<span style="color: #800080; text-decoration-color: #800080; font-style: italic">None</span>,
        <span style="color: #808000; text-decoration-color: #808000">version_statement</span>=<span style="color: #800080; text-decoration-color: #800080; font-weight: bold">version_statement</span><span style="font-weight: bold">(</span><span style="color: #808000; text-decoration-color: #808000">version</span>=<span style="color: #800080; text-decoration-color: #800080; font-style: italic">None</span>,
            <span style="color: #808000; text-decoration-color: #808000">version_date</span>=<span style="color: #800080; text-decoration-color: #800080; font-style: italic">None</span>,
            <span style="color: #808000; text-decoration-color: #808000">version_resp</span>=<span style="color: #800080; text-decoration-color: #800080; font-style: italic">None</span>,
            <span style="color: #808000; text-decoration-color: #808000">version_notes</span>=<span style="color: #800080; text-decoration-color: #800080; font-style: italic">None</span><span style="font-weight: bold">)</span><span style="font-weight: bold">)</span>,
    <span style="color: #808000; text-decoration-color: #808000">study_desc</span>=<span style="color: #800080; text-decoration-color: #800080; font-weight: bold">study_desc</span><span style="font-weight: bold">(</span><span style="color: #808000; text-decoration-color: #808000">title_statement</span>=<span style="color: #800080; text-decoration-color: #800080; font-weight: bold">title_statement</span><span style="font-weight: bold">(</span><span style="color: #808000; text-decoration-color: #808000">title</span>=<span style="color: #008000; text-decoration-color: #008000">'Cambodia Living Standards Measurement Study - Plus (Cambodia LSMS+) 2019-20'</span>,
            <span style="color: #808000; text-decoration-color: #808000">sub_title</span>=<span style="color: #800080; text-decoration-color: #800080; font-style: italic">None</span>,
            <span style="color: #808000; text-decoration-color: #808000">alternate_title</span>=<span style="color: #008000; text-decoration-color: #008000">'Cambodia LSMS+'</span>,
            <span style="color: #808000; text-decoration-color: #808000">translated_title</span>=<span style="color: #800080; text-decoration-color: #800080; font-style: italic">None</span>,
            <span style="color: #808000; text-decoration-color: #808000">idno</span>=<span style="color: #008000; text-decoration-color: #008000">''</span>,
            <span style="color: #808000; text-decoration-color: #808000">identifiers</span>=<span style="font-weight: bold">[]</span><span style="font-weight: bold">)</span>,
        <span style="color: #808000; text-decoration-color: #808000">series_statement</span>=<span style="color: #800080; text-decoration-color: #800080; font-weight: bold">series_statement</span><span style="font-weight: bold">(</span><span style="color: #808000; text-decoration-color: #808000">series_name</span>=<span style="color: #008000; text-decoration-color: #008000">'Living Standards Measurement Study - Plus'</span>...


## Saving Output 

Output can be saved as json or as an Excel file.


```python
example.model_dump_json(exclude_none=True, exclude_unset=True)
```




    '{"doc_desc":{"producers":[{"name":"World Bank Group, DEC - Development Data Group","abbr":"WBG","affiliation":"World Bank","role":"Metadata production"}],"prod_date":"2025-02-06","idno":"IHSN_DDI_2-5_WBG_KHM_LSMS_2019_V01","version_statement":{"version":"v01","version_date":"2025-02-06","version_re...




```python
me.save_metadata_to_excel(example, "cambodia_metadata.xlsx")
```

## Upload to the metadata editor


```python
me.create_project_log(example)
```

# Web URL


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

    Read in https://data.worldbank.org/indicator/NY.GDP.MKTP.CD, running token count is 1832
    Sending to OpenAI, this may take a few minutes...



IHSN_INDICATOR_1-<span style="color: #800080; text-decoration-color: #800080; font-weight: bold">0_Template_v01_EN</span><span style="font-weight: bold">(</span><span style="color: #808000; text-decoration-color: #808000">metadata_information</span>=<span style="color: #800080; text-decoration-color: #800080; font-weight: bold">metadata_information</span><span style="font-weight: bold">(</span><span style="color: #808000; text-decoration-color: #808000">title</span>=<span style="color: #008000; text-decoration-color: #008000">'GDP (current US$) - Metadata'</span>,
        <span style="color: #808000; text-decoration-color: #808000">idno</span>=<span style="color: #008000; text-decoration-color: #008000">'WB_NY.GDP.MKTP.CD_v1.0'</span>,
        <span style="color: #808000; text-decoration-color: #808000">producers</span>=<span style="font-weight: bold">[</span><span style="color: #800080; text-decoration-color: #800080; font-weight: bold">Producer</span><span style="font-weight: bold">(</span><span style="color: #808000; text-decoration-color: #808000">name</span>=<span style="color: #008000; text-decoration-color: #008000">'The World Bank Group'</span>,
                <span style="color: #808000; text-decoration-color: #808000">abbr</span>=<span style="color: #008000; text-decoration-color: #008000">'WBG'</span>,
                <span style="color: #808000; text-decoration-color: #808000">affiliation</span>=<span style="color: #008000; text-decoration-color: #008000">'DEC - Development Data Group'</span>,
                <span style="color: #808000; text-decoration-color: #808000">role</span>=<span style="color: #008000; text-decoration-color: #008000">'Metadata production'</span><span style="font-weight: bold">)</span><span style="font-weight: bold">]</span>,
        <span style="color: #808000; text-decoration-color: #808000">prod_date</span>=<span style="color: #008000; text-decoration-color: #008000">'2025-02-06'</span>,
        <span style="color: #808000; text-decoration-color: #808000">version_statement</span>=<span style="color: #800080; text-decoration-color: #800080; font-weight: bold">version_statement</span><span style="font-weight: bold">(</span><span style="color: #808000; text-decoration-color: #808000">version</span>=<span style="color: #008000; text-decoration-color: #008000">'1.0'</span>,
            <span style="color: #808000; text-decoration-color: #808000">version_date</span>=<span style="color: #008000; text-decoration-color: #008000">'2025-02-06'</span>,
            <span style="color: #808000; text-decoration-color: #808000">version_notes</span>=<span style="color: #008000; text-decoration-color: #008000">'Initial version of metadata for GDP (current US$) indicator.'</span>,
            <span style="color: #808000; text-decoration-color: #808000">version_resp</span>=<span style="color: #008000; text-decoration-color: #008000">'DEC - Development Data Group'</span><span style="font-weight: bold">)</span><span style="font-weight: bold">)</span>,
    <span style="color: #808000; text-decoration-color: #808000">series_description</span>=<span style="color: #800080; text-decoration-color: #800080; font-weight: bold">series_description</span><span style="font-weight: bold">(</span><span style="color: #808000; text-decoration-color: #808000">idno</span>=<span style="color: #008000; text-decoration-color: #008000">'NY.GDP.MKTP.CD'</span>,
        <span style="color: #808000; text-decoration-color: #808000">alternate_identifiers</span>=<span style="font-weight: bold">[</span><span style="color: #800080; text-decoration-color: #800080; font-weight: bold">Alternate_identifier</span><span style="font-weight: bold">(</span><span style="color: #808000; text-decoration-color: #808000">name</span>=<span style="color: #008000; text-decoration-color: #008000">'WDI Indicator Code'</span>,
                <span style="color: #808000; text-decoration-color: #808000">identifier</span>=<span style="color: #008000; text-decoration-color: #008000">'NY.GDP.MKTP.CD'</span>,
                <span style="color: #808000; text-decoration-color: #808000">database</span>=<span style="color: #008000; text-decoration-color: #008000">'World Development Indicators'</span>,
                <span style="color: #808000; text-decoration-color: #808000">uri</span>=<span style="color: #008000; text-decoration-color: #008000">'http://datatopics.worldbank.org/world-development-indicators/'</span>,
                <span style="color: #808000; text-decoration-color: #808000">notes</span>=<span style="color: #008000; text-decoration-color: #008000">'World Development Indicators'</span><span style="font-weight: bold">)</span><span style="font-weight: bold">]</span>,
        <span style="color: #808000; text-decoration-color: #808000">name</span>...



```python
me.save_metadata_to_excel(example_gdp, "gdp_metadata.xlsx")
```


```python
me.create_project_log(example_gdp)
```

# Augmenting existing metadata


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

    Read in /var/folders/jv/htm9fs717y350bv788702w000000gp/T/tmpsr19mxm9.txt, running token count is 634
    Read in https://documents1.worldbank.org/curated/en/593871468777303124/pdf/17140-PUB-revised-PUBLIC-9781464813313-Updated.pdf, running token count is 8379
    Sending to OpenAI, this may take a few minutes...



IHSN_DOCUMENT_1-<span style="color: #800080; text-decoration-color: #800080; font-weight: bold">0_Template_v01_EN</span><span style="font-weight: bold">(</span><span style="color: #808000; text-decoration-color: #808000">metadata_information</span>=<span style="color: #800080; text-decoration-color: #800080; font-weight: bold">metadata_information</span><span style="font-weight: bold">(</span><span style="color: #808000; text-decoration-color: #808000">title</span>=<span style="color: #008000; text-decoration-color: #008000">'Metadata for: The Analysis of Household Surveys'</span>,
        <span style="color: #808000; text-decoration-color: #808000">idno</span>=<span style="color: #008000; text-decoration-color: #008000">'IHSN_978-1-4648-1331-3_v1.0'</span>,
        <span style="color: #808000; text-decoration-color: #808000">producers</span>=<span style="font-weight: bold">[</span><span style="color: #800080; text-decoration-color: #800080; font-weight: bold">Producer</span><span style="font-weight: bold">(</span><span style="color: #808000; text-decoration-color: #808000">name</span>=<span style="color: #008000; text-decoration-color: #008000">'John Doe'</span>, <span style="color: #808000; text-decoration-color: #808000">abbr</span>=<span style="color: #800080; text-decoration-color: #800080; font-style: italic">None</span>, <span style="color: #808000; text-decoration-color: #808000">affiliation</span>=<span style="color: #008000; text-decoration-color: #008000">'IHSN'</span>, <span style="color: #808000; text-decoration-color: #808000">role</span>=<span style="color: #008000; text-decoration-color: #008000">'Data Curator'</span><span style="font-weight: bold">)]</span>,
        <span style="color: #808000; text-decoration-color: #808000">production_date</span>=<span style="color: #008000; text-decoration-color: #008000">'2024-09-30'</span>,
        <span style="color: #808000; text-decoration-color: #808000">version</span>=<span style="color: #008000; text-decoration-color: #008000">'&lt;AI&gt;1.0'</span><span style="color: #000000; text-decoration-color: #000000">    </span><span style="color: #000000; text-decoration-color: #000000; font-weight: bold">)</span><span style="color: #000000; text-decoration-color: #000000">,</span><span style="color: #000000; text-decoration-color: #000000">    </span><span style="color: #808000; text-decoration-color: #808000">document_description</span><span style="color: #000000; text-decoration-color: #000000">=</span><span style="color: #800080; text-decoration-color: #800080; font-weight: bold">document_description</span><span style="color: #000000; text-decoration-color: #000000; font-weight: bold">(</span><span style="color: #000000; text-decoration-color: #000000">        </span><span style="color: #808000; text-decoration-color: #808000">title_statement</span><span style="color: #000000; text-decoration-color: #000000">=</span><span style="color: #800080; text-decoration-color: #800080; font-weight: bold">title_statement</span><span style="color: #000000; text-decoration-color: #000000; font-weight: bold">(</span><span style="color: #000000; text-decoration-color: #000000">            </span><span style="color: #808000; text-decoration-color: #808000">idno</span><span style="color: #000000; text-decoration-color: #000000">=</span><span style="color: #008000; text-decoration-color: #008000">'DEMO_DOC_001'</span><span style="color: #000000; text-decoration-color: #000000">,</span><span style="color: #000000; text-decoration-color: #000000">            </span><span style="color: #808000; text-decoration-color: #808000">title</span><span style="color: #000000; text-decoration-color: #000000">=</span><span style="color: #008000; text-decoration-color: #008000">'The Analysis of Household Surveys: A Microeconometric Approach to Development Policy'</span><span style="color: #000000; text-decoration-color: #000000">,</span><span style="color: #000000; text-decoration-color: #000000">            </span><span style="color: #808000; text-decoration-color: #808000">sub_title</span><span style="color: #000000; text-decoration-color: #000000">=</span><span style="color: #800080; text-decoration-color: #800080; font-style: italic">None</span><span style="color: #000000; text-decoration-color: #000000">,</span><span style="color: #000000; text-decoration-color: #000000">            </span><span style="color: #808000; text-decoration-color: #808000">alternate_title</span><span style="color: #000000; text-decoration-color: #000000">=</span><span style="color: #800080; text-decoration-color: #800080; font-style: italic">None</span><span style="color: #000000; text-decoration-color: #000000">,</span><span style="color: #000000; text-decoration-color: #000000">            </span><span style="color: #808000; text-decoration-color: #808000">translated_title</span><span style="color: #000000; text-decoration-color: #000000">=</span><span style="color: #800080; text-decoration-color: #800080; font-style: italic">None</span><span style="color: #000000; text-decoration-color: #000000">        </span><span style="color: #000000; text-decoration-color: #000000; font-weight: bold">)</span><span style="color: #000000; text-decoration-color: #000000">,</span><span style="color: #000000; text-decoration-color: #000000">        </span><span style="color: #808000; text-decoration-color: #808000">identifiers</span><span style="color: #000000; text-decoration-color: #000000">=</span><span style="color: #000000; text-decoration-color: #000000; font-weight: bold">[</span><span style="color: #800080; text-decoration-color: #800080; font-weight: bold">Identifier</span><span style="color: #000000; text-decoration-color: #000000; font-weight: bold">(</span><span style="color: #808000; text-decoration-color: #808000">type</span><span style="color: #000000; text-decoration-color: #000000">=</span><span style="color: #008000; text-decoration-color: #008000">'ISBN'</span><span style="color: #000000; text-decoration-color: #000000">, </span><span style="color: #808000; text-decoration-color: #808000">identifier</span><span style="color: #000000; text-decoration-color: #000000">=</span><span style="color: #008000; text-decoration-color: #008000">'978-1-4648-1331-3'</span><span style="color: #000000; text-decoration-color: #000000; font-weight: bold">)]</span><span style="color: #000000; text-decoration-color: #000000">,</span><span style="color: #000000; text-decoration-color: #000000">        </span>...


# Azure AI Services

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



```python

```
