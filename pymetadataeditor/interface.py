import warnings
from json import JSONDecodeError
from ssl import SSLError as ssl_SSLError
from typing import Any, Callable, Dict, Iterable, List, Optional, Union

import pandas as pd
import requests

# from metadataschemas import image_schema
from metadataschemas import (
    document_schema,
    geospatial_schema,
    microdata_schema,
    script_schema,
    series_schema,
    table_schema,
    timeseries_db_schema,
    timeseries_schema,
    video_schema,
)
from metadataschemas.excel_interface import ExcelInterface
from metadataschemas.utils.utils import standardize_keys_in_dict
from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, PrivateAttr, SecretStr, model_validator
from requests.exceptions import HTTPError, SSLError

from pymetadataeditor.tools import update_metadata, validate_metadata

warnings.filterwarnings(
    "ignore", category=UserWarning, module="pydantic"
)  # suppresses warning when metadata passed as dict instead of a pydantic object

MetadataDict = Dict[
    str,
    Union[str, bytes, int, float, BaseModel, "MetadataDict", List["MetadataDict"], List[BaseModel], None],
]


class DeleteNotAppliedError(Exception):
    def __init__(self, message="Delete request not accepted by system.", response=None):
        super().__init__(message)
        self.response = response


class MetadataEditor(BaseModel, ExcelInterface):
    """
    MetadataEditor allows you to list and create projects in a metadata database.
    First obtain an API key.

    Then run

        from pymetadataeditor import MetadataEditor

        api_url = <Generally the required URL looks like 'https://<name_of_your_metadata_database>.org/index.php/api'>
        api_key = "<the api key you generated for accessing the metadata database"
        me = MetadataEditor(api_url = api_url, api_key = api_key)

    Then you can list and create new projects like so:

        me.list_projects()
        me.create_timeseries(idno = "<unique id of your metadata>", series_description = {...}, ...)
    """

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    api_url: AnyHttpUrl
    api_key: SecretStr = Field(repr=False)
    allow_http: bool = Field(
        default=False,
        description="API urls that begin HTTPS are favoured. Set allow_http=True to use of the less secure HTTP",
    )
    verify_ssl: bool = Field(
        default=True,
        description="Calls to the API are authenticated with an SSL certificate. "
        "Set verify_ssl=False to remove this requirement",
    )
    _metadata_types: dict = PrivateAttr(
        default={
            "document": document_schema.ScriptSchemaDraft,
            "geospatial": geospatial_schema.GeospatialSchema,
            #  "image": image_schema.ImageDataTypeSchema,
            "script": script_schema.ResearchProjectSchemaDraft,
            "series": series_schema.Series,
            "survey": microdata_schema.MicrodataSchema,
            "table": table_schema.Model,
            "timeseries": timeseries_schema.TimeseriesSchema,
            "timeseries_db": timeseries_db_schema.TimeseriesDatabaseSchema,
            "video": video_schema.Model,
        }
    )

    @model_validator(mode="after")
    def check_https(self) -> Any:
        if str(self.api_url).startswith("https") or self.allow_http:
            return self
        else:
            raise ValueError(
                f"URL scheme should be 'https' but got {self.api_url}"
                "To allow the less secure use of 'http', set allow_unsecure=True"
            )

    def write_empty_metadata_to_excel_for_geospatial(self, filename: str):
        raise NotImplementedError("Geospatial schema contains an infinite loop so cannot be written to excel")

    def write_empty_metadata_to_excel_for_image(self, filename: str):
        raise NotImplementedError("There's an issue with schema definition of image metadata causing __root__ errors")

    def _request(
        self,
        method: str,
        pth: str,
        json: Optional[MetadataDict] = None,
        params: Optional[Dict[str, Union[str, List[str]]]] = None,
        id: Optional[Union[int, str]] = None,
    ) -> Dict:
        """
        Sends a GET or POST request to the specified URL with the API key in the headers and returns the JSON response.

        Args:
            pth (str): The path appended to the API_URL to which the GET or POST request is sent.

        Returns:
            Dict[str, str]: The JSON response from the server, parsed into a dictionary.

        Raises:
            ValueError: If the URL does not start with 'https'.
            PermissionError: If the response status code is 403, indicating that access is denied.
            Exception: If the request fails due to other HTTP errors, with details of the status code and response text.
            Exception: If any other unexpected error occurs during the request.
        """
        method = method.lower()
        assert method in ["get", "post"], f"unknown method {method}"
        request_kwargs = {}
        if method == "post":
            assert params is None, "when using post, pass json not params"
            request_kwargs["json"] = json
        if method == "get" and params is not None:
            assert json is None, "when using post, pass params not json"
            request_kwargs["params"] = params

        if "{" in pth:
            assert id is not None, "If passing a url format, an id must be passed"
            pth = pth.format(id)
        url = str(self.api_url).strip("/") + "/" + pth.strip("/")
        # print(f"accessing {url}")
        try:
            response = None
            response = requests.request(
                method,
                url,
                verify=self.verify_ssl,
                headers={"x-api-key": self.api_key.get_secret_value()},
                **request_kwargs,
            )
            response.raise_for_status()
        except (SSLError, ssl_SSLError) as e:
            raise SSLError(
                f"Usually this means the admin of {self.api_url} has not verified an SSL certificate.\n"
                f"You can bypass the requirement by setting MetadataEditor.verify_ssl=False.\n{e}"
            ) from None
        except HTTPError as e:
            if response is None or response.status_code == 404:
                error_msg = (
                    f"Page not found. Try checking the URL.\nGenerally the required URL looks like "
                    f"'https://<name_of_your_metadata_database>.org/index.php/api', but the URL that was passed "
                    f"was '{self.api_url}'"
                )
                raise HTTPError(error_msg) from None
            elif response.status_code == 403:
                raise PermissionError("Access to that URL is denied. " "Check that the API key is correct") from None
            elif response.status_code == 400 and id is not None:
                raise PermissionError(f"Access to this id is denied. Check that '{id}' is correct") from e
            else:
                raise Exception(f"Status Code: {response.status_code}, Response: {response.text}") from e
        try:
            json_response = response.json()
        except (JSONDecodeError, requests.exceptions.JSONDecodeError) as e:
            raise JSONDecodeError(
                f"Error decoding JSON response: {e.msg}\nFull Response: {response}", e.doc, e.pos
            ) from e
        # if self.verify_ssl == False:
        # we must have shown this warning the first time, ok to silence thereafter
        return json_response

    def _get_request(
        self, pth: str, id: Optional[Union[int, str]] = None, params: Optional[Dict[str, Union[str, List[str]]]] = None
    ) -> Dict:
        """
        Args:
            pth (str): The path appended to the API_URL to which the GET request is sent.
            id (optional int or str): The id of a specific collection or project.
                                      If not none, then pth should contain '{}' where the id ought to go.
            params (optional dict): additional parameters to send with the get request such as 'keywords'

        Returns:
            Dict[str, str]: The JSON response from the server, parsed into a dictionary.
        """
        return self._request("get", pth=pth, id=id, params=params)

    def _post_request(self, pth: str, metadata: Optional[MetadataDict] = None, id: Optional[Union[int, str]] = None):
        """
        Args:
            pth (str): The path appended to the API_URL to which the POST request is sent.
            metadata (dict): The metadata to be sent with the POST request.

        Returns:
            Dict[str, str]: The JSON response from the server, parsed into a dictionary.
        """
        return self._request("post", pth=pth, id=id, json=metadata)

    def list_projects(
        self,
        keywords: Optional[Union[str, List[str]]] = None,
        metadata_type: Optional[str] = None,
        offset: int = 0,
        limit: Union[int, str] = 100,
        sort_by: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Lists all the projects associated with your API key.

        Args:

            keywords (optional str or list of str): Keywords for filtering projects by title and/or idno.
            metadata_type (optional str): If given, only projects of this type are returned.
            offset (int): Offset for pagination e.g. 10 to skip first 10 records. Default is 0.
            limit (int or str): Page size e.g. 10 to show 10 records. Default is 100.
                If limit='All' then all records are retrieved.
            sort_by (optional str): valid values: "title_asc", "title_desc", "updated_asc", "updated_desc".

        Returns:
            pd.DataFrame: Information about the projects
        """
        if isinstance(limit, str):
            assert limit.lower() == "all", f"Expected limit to be 'all' or a positive integer but got '{limit}'"
            new_offset = offset
            new_limit = 100
            dfs = []
            while True:
                df = self.list_projects(
                    keywords=keywords, metadata_type=metadata_type, offset=new_offset, limit=new_limit, sort_by=sort_by
                )
                dfs.append(df)
                if len(df) < new_limit:
                    break
                new_offset += new_limit
            return pd.concat(dfs)

        list_projects_get_path = "/editor"
        params = {"offset": offset, "limit": limit}
        if keywords is not None:
            if not isinstance(keywords, str) and isinstance(keywords, Iterable):
                keywords = "%".join(keywords)
            keywords = keywords.replace(" ", "%")
            params["keywords"] = keywords
        if metadata_type is not None:
            metadata_type = metadata_type.lower()
            assert (
                metadata_type in self._metadata_types.keys()
            ), f"{metadata_type} not found in {list(self._metadata_types.keys())}"
            params["type"] = metadata_type.replace("_", "-")
        if sort_by is not None:
            sort_by = sort_by.lower()
            valid_sort_by = ["title_asc", "title_desc", "updated_asc", "updated_desc"]
            assert sort_by in valid_sort_by, f"{sort_by} not valid, must be one of {valid_sort_by}"
            params["sort_by"] = sort_by
        response = self._get_request(pth=list_projects_get_path, params=params)
        # return response
        try:
            projects = response["projects"]
            projects = pd.DataFrame.from_dict(projects).set_index("id")
        except KeyError:  # is this the best way to cope with times when there are no projects?
            return pd.DataFrame(columns=["id", "created"]).set_index("id")
        return projects

    def get_project_by_id(self, id: int) -> pd.Series:
        """
        Args:
            id (int): the id of the project, not to be confused with the idno.

        Raises:
            Exception: You don't have permission to access this project - often this means the id is incorrect
        """
        #  todo(gblackadder) we could implement a get project by **idno** by using list projects and then filtering
        get_project_template = "/editor/{}"
        response = self._get_request(get_project_template, id=id)
        return pd.Series(response["project"])

    def get_project_metadata_by_id(
        self, id: int, exclude_unset: bool = True, as_object: bool = False
    ) -> Union[MetadataDict, BaseModel]:
        """
        Args:
            id (int): the id of the project, not to be confused with the idno.
            exclude_unset (bool): when returning a dictionary (that is when as_object is False), if True then fields
                that were not set or have a None value are removed from the dictionary. Defaults to True
            as_object (bool): If True, return the metadata as a pydantic object.
                Otherwise, return a dictionary. Defaults to False.

        Returns:
            Union[BaseModel, Dict]: The metadata as either a dictionary or an object.
        """
        project = self.get_project_by_id(id=id)
        project_type = project["type"].replace("-", "_")
        assert project_type in self._metadata_types, (
            f"this project is listed as a '{project_type}' type project but this is"
            f" unknown. Projects must be one of {list(self._metadata_types.keys())}"
        )
        metadata_object = self._metadata_types[project_type](**project["metadata"])
        if as_object:
            return metadata_object
        else:
            return metadata_object.model_dump(exclude_none=exclude_unset, exclude_unset=exclude_unset)

    def save_project_metadata_to_excel(self, id: int, filename: Optional[str] = None, title: Optional[str] = None):
        """
        Args:
            id (int): the id of the project, not to be confused with the idno.
            filename (Optional(str)): The path to the Excel file.
            title (Optional(str)): The title for the Excel sheet.

        Outputs:
            An Excel file containing the metadata from the pydantic object. The file can be updated as needed.
        """
        project = self.get_project_by_id(id=id)
        project_type = project["type"].lower().replace("-", "_")
        assert project_type in self._metadata_types, (
            f"this project is listed as a '{project_type}' type project but this is"
            f" unknown. Projects must be one of {list(self._metadata_types.keys())}"
        )
        metadata_object = self._metadata_types[project_type](**project["metadata"])
        self.save_metadata_to_excel(project_type, object=metadata_object, filename=filename, title=title)

    def delete_project_by_id(self, id: int):
        """
        Checks the project exists, deletes it, then checks it was deleted.

        Args:
            id (int): the id of the project, not to be confused with the idno.

        Raises:
            DeleteNotAppliedError: This can be the result of system admins blocking data deletion
        """
        pth = "editor/delete/{}"
        self._delete_by_id(pth=pth, id=id, checker_fn=self.get_project_by_id)

    def delete_collection_by_id(self, id: int):
        """
        Checks the collection exists, deletes it, then checks it was deleted.

        Args:
            id (int): the id of the colection.

        Raises:
            DeleteNotAppliedError: This can be the result of system admins blocking data deletion
        """
        pth = "collections/delete/{}"
        self._delete_by_id(pth=pth, id=id, checker_fn=self.get_collection_by_id)

    def _delete_by_id(self, pth: str, id: Union[int, str], checker_fn: Callable[[int], pd.Series]):
        """
        Internal, generic method for deleting either collections or projects
        """
        # first check that the project/collection is there to be deleted
        checker_fn(id)
        try:
            self._post_request(pth=pth, id=id)
        except JSONDecodeError:
            pass

        # check that the entity was deleted
        try:
            checker_fn(id)
        except (PermissionError, JSONDecodeError):
            pass  # evidently the entity was deleted because now it can't be found
        # except JSONDecodeError as e:

        else:
            raise DeleteNotAppliedError()

    def create_log_from_excel(self, metadata_type: str, filename: str) -> int:
        """
        Logs the metadata located in an appropriately formatted Excel file.

        To create a blank Excel file, formatted for a given metadata type call

            MetadataEditor.write_empty_metadata_to_excel(metadata_type, filename, title)

        There are also specific methods available for each metadatatype for which an Excel format is supported:

            MetadataEditor.write_empty_metadata_to_excel_for_document(filename, title)
            MetadataEditor.write_empty_metadata_to_excel_for_script(filename, title)
            MetadataEditor.write_empty_metadata_to_excel_for_series(filename, title)
            MetadataEditor.write_empty_metadata_to_excel_for_survey(filename, title)
            MetadataEditor.write_empty_metadata_to_excel_for_table(filename, title)
            MetadataEditor.write_empty_metadata_to_excel_for_timeseries(filename, title)
            MetadataEditor.write_empty_metadata_to_excel_for_timeseries_db(filename, title)
            MetadataEditor.write_empty_metadata_to_excel_for_video(filename, title)

        Args:
            metadata_type (str): the name of a supported metadata type, currently:
                    document, script, series, survey, table, timeseries, timeseries_DB, video
                Currently not supported:
                    geospatial, image
            filename (str): The path to the Excel file.

        Returns:
            int: The ID of the newly created document metadata
        """
        metadata_type = metadata_type.lower()
        ob = self.read_metadata_excel(metadata_type=metadata_type, filename=filename)
        return self._create_log(ob.model_dump(), metadata_type.replace("_", "-"))

    def create_log_of_document_from_excel(self, filename: str) -> int:
        return self.create_log_from_excel("document", filename=filename)

    def create_log_of_script_from_excel(self, filename: str) -> int:
        return self.create_log_from_excel("script", filename=filename)

    def create_log_of_series_from_excel(self, filename: str) -> int:
        raise NotImplementedError("series metadata are not accepted by the API. Try timeseries if applicable")
        # return self.create_log_from_excel("series", filename=filename)

    def create_log_of_survey_from_excel(self, filename: str) -> int:
        return self.create_log_from_excel("survey", filename=filename)

    def create_log_of_table_from_excel(self, filename: str) -> int:
        return self.create_log_from_excel("table", filename=filename)

    def create_log_of_timeseries_from_excel(self, filename: str) -> int:
        return self.create_log_from_excel("timeseries", filename=filename)

    def create_log_of_timeseries_db_from_excel(self, filename: str) -> int:
        return self.create_log_from_excel("timeseries_db", filename=filename)

    def create_log_of_video_from_excel(self, filename: str) -> int:
        return self.create_log_from_excel("video", filename=filename)

    def create_log_of_document(
        self,
        document_description: Union[Dict, document_schema.DocumentDescription],
        repositoryid: Optional[str] = None,
        published: Optional[int] = 0,
        overwrite: Optional[Union[Dict, document_schema.Overwrite]] = "no",
        metadata_information: Optional[Union[Dict, document_schema.MetadataInformation]] = None,
        provenance: Optional[Union[List[Dict], List[document_schema.ProvenanceSchema]]] = None,
        tags: Optional[Union[List[Dict], List[document_schema.Tag]]] = None,
        lda_topics: Optional[Union[List[Dict], List[document_schema.LdaTopic]]] = None,
        embeddings: Optional[Union[List[Dict], List[document_schema.Embedding]]] = None,
        additional: Optional[Dict] = None,
    ) -> int:
        """
        Creates a record of your *document* metadata

        Args:
            document_description (DocumentDescription or Dictionary): Description of the document. Required.
            repositoryid (Optional[str]): Collection ID that owns the survey. Defaults to None.
            published (Optional[int]): Status of the survey - 0=draft, 1=published. Defaults to 0.
            overwrite (Optional[Overwrite or Dictionary]): Overwrite survey if already exists? Defaults to 'no'.
            metadata_information (Optional[MetadataInformation or Dictionary]): Document metadata information
            provenance (Optional[List[ProvenanceSchema or Dictionary]]): List of provenance schemas. Defaults to None.
            tags (Optional[List[Tag or Dictionary]]): List of tags. Defaults to None.
            lda_topics (Optional[List[LdaTopic or Dictionary]]): List of LDA topics. Defaults to None.
            embeddings (Optional[List[Embedding or Dictionary]]): List of word embeddings. Defaults to None.
            additional (Optional[Dictionary]): Additional metadata not covered by the schema. Defaults to None.

        Returns:
            int: The ID of the newly created document metadata
        """
        document_metadata = {
            "document_description": document_description,
            "repositoryid": repositoryid,
            "published": published,
            "overwrite": overwrite,
            "metadata_information": metadata_information,
            "provenance": provenance,
            "tags": tags,
            "lda_topics": lda_topics,
            "embeddings": embeddings,
            "additional": additional,
        }
        return self._create_log(document_metadata, "document")

    def create_log_of_image(self):
        raise NotImplementedError("There's an issue with schema definition of image metadata causing __root__ errors")

    def create_log_of_geospatial(
        self,
        description: Union[Dict, geospatial_schema.Description],
        idno: Optional[str] = None,
        metadata_information: Optional[Union[Dict, geospatial_schema.MetadataInformation]] = None,
        provenance: Optional[List[Union[Dict, geospatial_schema.ProvenanceSchema]]] = None,
        tags: Optional[List[Union[Dict, geospatial_schema.Tag]]] = None,
        lda_topics: Optional[List[Union[Dict, geospatial_schema.LdaTopic]]] = None,
        embeddings: Optional[List[Union[Dict, geospatial_schema.Embedding]]] = None,
        additional: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        Creates a record of your *geospatial* metadata

        Args:
            description (Description or Dictionary): Geospatial schema. This field is required.
            idno (Optional[str]): Project unique identifier.
            metadata_information (Optional[MetadataInformation or Dictionary]): Document metadata information.
            provenance (Optional[List[ProvenanceSchema or Dictionary]]): Provenance.
            tags (Optional[List[Tag or Dictionary]]): List of Tags.
            lda_topics (Optional[List[LdaTopic or Dictionary]]): List of LDA topics.
            embeddings (Optional[List[Embedding or Dictionary]]): List of Word embeddings.
            additional (Optional[Dict[str, Any]]): Additional metadata.

        Returns:
            int: The ID of the newly created geospatial metadata
        """

        geospatial_metadata = {
            "idno": idno,
            "metadata_information": metadata_information,
            "description": description,
            "provenance": provenance,
            "tags": tags,
            "lda_topics": lda_topics,
            "embeddings": embeddings,
            "additional": additional,
        }
        return self._create_log(geospatial_metadata, "geospatial")

    def create_log_of_script(
        self,
        repositoryid: Optional[str] = None,
        published: Optional[int] = 0,
        overwrite: Optional[Union[Dict, script_schema.Overwrite]] = "no",
        doc_desc: Optional[Union[Dict, script_schema.DocDesc]] = None,
        project_desc: Optional[Union[Dict, script_schema.ProjectDesc]] = None,
        provenance: Optional[Union[List[Dict], List[script_schema.ProvenanceSchema]]] = None,
        tags: Optional[Union[List[Dict], List[script_schema.Tag]]] = None,
        lda_topics: Optional[Union[List[Dict], List[script_schema.LdaTopic]]] = None,
        embeddings: Optional[Union[List[Dict], List[script_schema.Embedding]]] = None,
        additional: Optional[Dict] = None,
    ) -> int:
        """
        Creates a record of your *script* metadata

        Args:
            repositoryid (Optional[str]): Collection ID that owns the project. Defaults to None.
            published (Optional[int]): Status of the project - 0=draft, 1=published. Defaults to 0.
            overwrite (Optional[Overwrite or Dictionary]): Overwrite document if already exists? Defaults to 'no'.
            doc_desc (Optional[DocDesc or Dictionary]): Description of the document. Defaults to None.
            project_desc (Optional[ProjectDesc or Dictionary]): Description of the research project. Defaults to None.
            provenance (Optional[List[ProvenanceSchema or Dictionary]]): List of provenance schemas. Defaults to None.
            tags (Optional[List[Tag or Dictionary]]): List of tags. Defaults to None.
            lda_topics (Optional[List[LdaTopic or Dictionary]]): List of LDA topics. Defaults to None.
            embeddings (Optional[List[Embedding or Dictionary]]): List of word embeddings. Defaults to None.
            additional (Optional[Dictionary]): Additional metadata not covered by the schema. Defaults to None.

        Returns:
            int: The ID of the newly created script metadata
        """
        script_metadata = {
            "repositoryid": repositoryid,
            "published": published,
            "overwrite": overwrite,
            "doc_desc": doc_desc,
            "project_desc": project_desc,
            "provenance": provenance,
            "tags": tags,
            "lda_topics": lda_topics,
            "embeddings": embeddings,
            "additional": additional,
        }
        return self._create_log(script_metadata, "script")

    def create_log_of_series(
        self,
        idno: str,
        name: str,
        db_idno: Optional[str] = None,
        aliases: Optional[List[Union[Dict, series_schema.Alias]]] = None,
        measurement_unit: Optional[str] = None,
        periodicity: Optional[str] = None,
        base_period: Optional[str] = None,
        definition_short: Optional[str] = None,
        definition_long: Optional[str] = None,
        definition_references: Optional[List[Union[Dict, series_schema.DefinitionReference]]] = None,
        related_concepts: Optional[List[Union[Dict, series_schema.RelatedConcept]]] = None,
        methodology: Optional[str] = None,
        imputation: Optional[str] = None,
        quality_checks: Optional[str] = None,
        quality_note: Optional[str] = None,
        series_break: Optional[str] = None,
        statistical_concept: Optional[str] = None,
        limitation: Optional[str] = None,
        topics: Optional[List[Union[Dict, series_schema.Topic]]] = None,
        relevance: Optional[str] = None,
        series_dates: Optional[List[Union[Dict, series_schema.SeriesDate]]] = None,
        geographic_units: Optional[List[Union[Dict, series_schema.GeographicUnit]]] = None,
        aggregation_method: Optional[str] = None,
        ser_access_license: Optional[Union[Dict, series_schema.SerAccessLicense]] = None,
        confidentiality: Optional[str] = None,
        confidentiality_status: Optional[str] = None,
        confidentiality_note: Optional[str] = None,
        series_links: Optional[List[Union[Dict, series_schema.SeriesLink]]] = None,
        api_documentation: Optional[Union[Dict, series_schema.ApiDocumentation]] = None,
        source: Optional[str] = None,
        source_note: Optional[str] = None,
        keywords: Optional[List[Union[Dict, series_schema.Keyword]]] = None,
        notes: Optional[List[Union[Dict, series_schema.Note]]] = None,
        related_indicators: Optional[List[Union[Dict, series_schema.RelatedIndicator]]] = None,
        compliance: Optional[List[Union[Dict, series_schema.ComplianceItem]]] = None,
        series_groups: Optional[List[Union[Dict, series_schema.SeriesGroup]]] = None,
    ) -> int:
        raise NotImplementedError("series metadata are not accepted by the API. Try timeseries if applicable")
        # """
        # Creates a record of your *series* metadata

        # Args:
        #     idno (str): Series unique ID. Required.
        #     name (str): Series Name. Required.
        #     db_idno (Optional[str]): Series database ID. Defaults to None.
        #     aliases (Optional[List[Alias or Dictionary]]): Series other names. Defaults to None.
        #     measurement_unit (Optional[str]): Series unit of measure. Defaults to None.
        #     periodicity (Optional[str]): Periodicity of data. Defaults to None.
        #     base_period (Optional[str]): Base period. Defaults to None.
        #     definition_short (Optional[str]): Short definition. Defaults to None.
        #     definition_long (Optional[str]): Long definition. Defaults to None.
        #     definition_references (Optional[List[DefinitionReference or Dictionary]]): URL to standard definition of
        #         the indicator (international or national standard). Defaults to None.
        #     related_concepts (Optional[List[RelatedConcept or Dictionary]]): Related concepts. Defaults to None.
        #     methodology (Optional[str]): Methodology. Defaults to None.
        #     imputation (Optional[str]): Imputations. Defaults to None.
        #     quality_checks (Optional[str]): Quality control methods. Defaults to None.
        #     quality_note (Optional[str]): Note on data quality. Defaults to None.
        #     series_break (Optional[str]): Breaks in series. Defaults to None.
        #     statistical_concept (Optional[str]): Statistical concept. Defaults to None.
        #     limitation (Optional[str]): Limitations and exceptions. Defaults to None.
        #     topics (Optional[List[Topic or Dictionary]]): Topics covered by the indicator. Defaults to None.
        #     relevance (Optional[str]): Relevance. Defaults to None.
        #     series_dates (Optional[List[SeriesDate or Dictionary]]): Series dates. Defaults to None.
        #     geographic_units (Optional[List[GeographicUnit or Dictionary]]): Geographic locations. Defaults to None.
        #     aggregation_method (Optional[str]): Aggregation method. Defaults to None.
        #     ser_access_license (Optional[SerAccessLicense or Dictionary]): Access license. Defaults to None.
        #     confidentiality (Optional[str]): Confidentiality statement. Defaults to None.
        #     confidentiality_status (Optional[str]): Confidentiality status. Defaults to None.
        #     confidentiality_note (Optional[str]): Confidentiality note. Defaults to None.
        #     series_links (Optional[List[SeriesLink or Dictionary]]): Links to API calls, websites, etc.
        #         Defaults to None.
        #     api_documentation (Optional[ApiDocumentation or Dictionary]): API Documentation. Defaults to None.
        #     source (Optional[str]): Original source. Defaults to None.
        #     source_note (Optional[str]): Notes from original source. Defaults to None.
        #     keywords (Optional[List[Keyword or Dictionary]]): Keywords. Defaults to None.
        #     notes (Optional[List[Note or Dictionary]]): Notes. Defaults to None.
        #     related_indicators (Optional[List[RelatedIndicator or Dictionary]]): Related indicators. Defaults to None.
        #     compliance (Optional[List[ComplianceItem or Dictionary]]): Compliance with international resolution.
        #         Defaults to None.
        #     series_groups (Optional[List[SeriesGroup or Dictionary]]): Series included in groups. Defaults to None.

        # Returns:
        #     int: The ID of the newly created series metadata
        # """
        # series_metadata = {
        #     "idno": idno,
        #     "name": name,
        #     "db_idno": db_idno,
        #     "aliases": aliases,
        #     "measurement_unit": measurement_unit,
        #     "periodicity": periodicity,
        #     "base_period": base_period,
        #     "definition_short": definition_short,
        #     "definition_long": definition_long,
        #     "definition_references": definition_references,
        #     "related_concepts": related_concepts,
        #     "methodology": methodology,
        #     "imputation": imputation,
        #     "quality_checks": quality_checks,
        #     "quality_note": quality_note,
        #     "series_break": series_break,
        #     "statistical_concept": statistical_concept,
        #     "limitation": limitation,
        #     "topics": topics,
        #     "relevance": relevance,
        #     "series_dates": series_dates,
        #     "geographic_units": geographic_units,
        #     "aggregation_method": aggregation_method,
        #     "ser_access_license": ser_access_license,
        #     "confidentiality": confidentiality,
        #     "confidentiality_status": confidentiality_status,
        #     "confidentiality_note": confidentiality_note,
        #     "series_links": series_links,
        #     "api_documentation": api_documentation,
        #     "source": source,
        #     "source_note": source_note,
        #     "keywords": keywords,
        #     "notes": notes,
        #     "related_indicators": related_indicators,
        #     "compliance": compliance,
        #     "series_groups": series_groups,
        # }
        # return self._create_log(series_metadata, "series")

    def create_log_of_table(
        self,
        repositoryid: Optional[str] = None,
        published: Optional[int] = 0,
        overwrite: Optional[Union[str, table_schema.Overwrite]] = "no",
        metadata_information: Optional[Union[Dict, table_schema.MetadataInformation]] = None,
        table_description: Optional[Union[Dict, table_schema.TableDescription]] = None,
        provenance: Optional[List[Union[Dict, table_schema.ProvenanceSchema]]] = None,
        tags: Optional[List[Union[Dict, table_schema.Tag]]] = None,
        lda_topics: Optional[List[Union[Dict, table_schema.LdaTopic]]] = None,
        embeddings: Optional[List[Union[Dict, table_schema.Embedding]]] = None,
        additional: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        Creates a record of your *table* metadata

        Args:
            repositoryid (Optional[str]): Collection ID that owns the document.
            published (Optional[int]): Status - 0=draft, 1=published. Defaults to 0.
            overwrite (Optional[Overwrite or str]): Overwrite document if already exists?. Defaults to 'no'.
            metadata_information (Optional[MetadataInformation or Dictionary]): Document metadata information.
            table_description (Optional[TableDescription or Dictionary]): Table Description.
            provenance (Optional[List[ProvenanceSchema or Dictionary]]): List of Provenances.
            tags (Optional[List[Tag or Dictionary]]): List of Tags.
            lda_topics (Optional[List[LdaTopic or Dictionary]]): List of LDA topics.
            embeddings (Optional[List[Embedding or Dictionary]]): List of word embeddings.
            additional (Optional[Dict[str, Any]]): Additional metadata.

        Returns:
            int: The ID of the newly created table metadata
        """
        table_metadata = {
            "repositoryid": repositoryid,
            "published": published,
            "overwrite": overwrite,
            "metadata_information": metadata_information,
            "table_description": table_description,
            "provenance": provenance,
            "tags": tags,
            "lda_topics": lda_topics,
            "embeddings": embeddings,
            "additional": additional,
        }
        return self._create_log(table_metadata, "table")

    def create_log_of_timeseries(
        self,
        idno: str,
        series_description: Union[Dict, timeseries_schema.SeriesDescription],
        metadata_information: Optional[Union[Dict, timeseries_schema.MetadataInformation]] = None,
        datacite: Optional[Union[Dict, timeseries_schema.DataciteSchema]] = None,
        provenance: Optional[List[Union[Dict, timeseries_schema.ProvenanceSchema]]] = None,
        tags: Optional[Union[Dict, List[timeseries_schema.Tag]]] = None,
        additional: Optional[Dict] = None,
    ):
        """
        Creates a record of your *timeseries* metadata

        Args:
            idno (str): The unique identifier for the timeseries.
            series_description (SeriesDescription or Dictionary): Can be an instance of SeriesDescription defined like
                SeriesDescription(idno="", name="", etc). Or as a dictionary like {"idno": "", "name": "", etc}
            metadata_information (Optional[MetadataInformation or Dictionary]): Information on who generated the
                documentation. Can be a MetadataInformation object or a dictionary. Defaults to None
            datacite (Optional[DataciteSchema or Dictionary]): DataCite metadata for generating DOI. Can be a
                DataciteSchema object or a Dictionary. Defaults to None.
            provenance (Optional[List[ProvenanceSchema or Dictionary]]): Can be a list of ProvenanceSchema objects or a
                list of dictionaries. Defaults to None.
            tags (Optional[List[Tag or Dictionary]]): Can be a list of Tag objects or a list of dictionaries.
                Defaults to None.
            additional (Optional[Dictionary]): Any other custom metadata not covered by the schema. A dictionary.
                Defaults to None.

        Returns:
            int: the id of the newly created metadata

        Examples:
        >>> from pymetadataeditor.schemas import (SeriesDescription,
        ...                                       MetadataInformation,
        ...                                       DataciteSchema,
        ...                                       ProvenanceSchema,
        ...                                       ProvenanceSchema,
        ...                                       Tag)
        >>> series_description = SeriesDescription(idno = "TS001", name = "Sample Timeseries")
        >>> metadata_information = MetadataInformation(title="Example of a Timeseries")
        >>> datacite = DataciteSchema(doi="10.1234/sample.doi")
        >>> tags = [Tag(tag="tag1"), Tag(tag="tag2", tag_group="example group")]
        >>> additional = {"key1": "value1", "key2": "value2"}

        >>> response = self.create_and_log_timeseries(
        ...     idno="TS001",
        ...     series_description=series_description,
        ...     metadata_information=metadata_information,
        ...     datacite=datacite,
        ...     tags=tags,
        ...     additional=additional
        ... )
        """
        metadata = {
            "idno": idno,
            "metadata_information": metadata_information,
            "series_description": series_description,
            "datacite": datacite,
            "provenance": provenance,
            "tags": tags,
            "additional": additional,
        }
        return self._create_log(metadata, "timeseries")

    def create_log_of_timeseries_db(
        self,
        database_description: Union[Dict, timeseries_db_schema.DatabaseDescription],
        published: Optional[int] = 0,
        overwrite: Optional[Union[str, timeseries_db_schema.Overwrite]] = "no",
        metadata_information: Optional[Union[Dict, timeseries_db_schema.MetadataInformation]] = None,
        provenance: Optional[List[Union[Dict, timeseries_db_schema.ProvenanceSchema]]] = None,
        additional: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        Creates a record of your *timeseries database* metadata

        Args:
            database_description (DatabaseDescription or Dictionary): Database Description. This field is required.
            published (Optional[int]): Status - 0=draft, 1=published. Defaults to 0.
            overwrite (Optional[Overwrite or str]): Overwrite database if already exists?. Defaults to 'no'.
            metadata_information (Optional[MetadataInformation or Dictionary]): Document metadata information.
            provenance (Optional[List[ProvenanceSchema or Dictionary]]): Provenance.
            additional (Optional[Dict[str, Any]]): Additional custom metadata.

        Returns:
            int: The ID of the newly created timeseries database metadata
        """
        timeseries_db_metadata = {
            "published": published,
            "overwrite": overwrite,
            "metadata_information": metadata_information,
            "database_description": database_description,
            "provenance": provenance,
            "additional": additional,
        }
        return self._create_log(timeseries_db_metadata, "timeseries_db")

    def create_log_of_survey(
        self,
        repositoryid: Optional[str] = None,
        access_policy: Optional[Union[str, microdata_schema.AccessPolicy]] = None,
        published: Optional[int] = None,
        overwrite: Optional[Union[str, microdata_schema.Overwrite]] = None,
        doc_desc: Optional[Union[Dict, microdata_schema.DocDesc]] = None,
        study_desc: Optional[Union[Dict, microdata_schema.StudyDesc]] = None,
        data_files: Optional[Union[List[Dict], List[microdata_schema.DatafileSchema]]] = None,
        variables: Optional[Union[List[Dict], List[microdata_schema.VariableSchema]]] = None,
        variable_groups: Optional[Union[List[Dict], List[microdata_schema.VariableGroupSchema]]] = None,
        provenance: Optional[Union[List[Dict], List[microdata_schema.ProvenanceSchema]]] = None,
        tags: Optional[Union[List[Dict], List[microdata_schema.Tag]]] = None,
        lda_topics: Optional[Union[List[Dict], List[microdata_schema.LdaTopic]]] = None,
        embeddings: Optional[Union[List[Dict], List[microdata_schema.Embedding]]] = None,
        additional: Optional[MetadataDict] = None,
    ):
        """
            Creates a record of your *survey microdata* metadata


        Args:
            repositoryid : Optional[str]
                The identifier for the repository where the survey microdata is to be stored.
            access_policy : Optional[Union[str, AccessPolicy]]
                The access policy for the survey data. Can be a string or an AccessPolicy object.
            published : Optional[int]
                The publication status of the survey data. Typically, 0 for unpublished and 1 for published.
            overwrite : Optional[Union[str, Overwrite]]
                Policy for overwriting existing data. Can be a string or an Overwrite object.
            doc_desc : Optional[Union[Dict, DocDesc]]
                Description of the documentation for the survey. Can be a dictionary or a DocDesc object.
            study_desc : Optional[Union[Dict, StudyDesc]]
                Description of the study. Can be a dictionary or a StudyDesc object.
            data_files : Optional[Union[List[Dict], List[DatafileSchema]]]
                List of data files associated with the survey. Each item can be a dictionary or a DatafileSchema object.
            variables : Optional[Union[List[Dict], List[VariableSchema]]]
                List of variables included in the survey. Each item can be a dictionary or a VariableSchema object.
            variable_groups : Optional[Union[List[Dict], List[VariableGroupSchema]]]
                List of variable groups included in the survey. Each item can be a dictionary or a VariableGroupSchema
                object.
            provenance : Optional[Union[List[Dict], List[ProvenanceSchema]]]
                Provenance information for the survey data. Each item can be a dictionary or a ProvenanceSchema object.
            tags : Optional[Union[List[Dict], List[Tag]]]
                Tags associated with the survey data. Each item can be a dictionary or a Tag object.
            lda_topics : Optional[Union[List[Dict], List[LdaTopic]]]
                List of LDA topics associated with the survey. Each item can be a dictionary or an LdaTopic object.
            embeddings : Optional[Union[List[Dict], List[Embedding]]]
                List of embeddings associated with the survey. Each item can be a dictionary or an Embedding object.
            additional : Optional[Dict[str, Any]]
                Any additional metadata to be associated with the survey data.

        Returns:
            int: the id of the newly created metadata

        >>> from pymetadataeditor.schemas import (
        ...     AccessPolicy,
        ...     DocDesc,
        ...     StudyDesc,
        ...     DatafileSchema,
        ...     VariableSchema,
        ...     VariableGroupSchema,
        ...     ProvenanceSchema,
        ...     Tag,
        ...     LdaTopic,
        ...     Embedding
        ... )
        >>> doc_desc = DocDesc(title="Survey Documentation")
        >>> study_desc = StudyDesc(title="Survey Study")
        >>> data_files = [DatafileSchema(id="file1", description="Data file 1")]
        >>> variables = [VariableSchema(id="var1", name="Variable 1")]
        >>> variable_groups = [VariableGroupSchema(id="group1", name="Group 1")]
        >>> provenance = [ProvenanceSchema(event="Created", date="2024-01-01")]
        >>> tags = [Tag(tag="tag1"), Tag(tag="tag2")]
        >>> lda_topics = [LdaTopic(id="topic1", description="Topic 1")]
        >>> embeddings = [Embedding(id="embed1", vector=[0.1, 0.2, 0.3])]
        >>> additional = {"key1": "value1", "key2": "value2"}

        >>> response = self.create_and_log_survey(
        ...     repositoryid="repo123",
        ...     access_policy=AccessPolicy(policy="open"),
        ...     published=1,
        ...     overwrite="yes",
        ...     doc_desc=doc_desc,
        ...     study_desc=study_desc,
        ...     data_files=data_files,
        ...     variables=variables,
        ...     variable_groups=variable_groups,
        ...     provenance=provenance,
        ...     tags=tags,
        ...     lda_topics=lda_topics,
        ...     embeddings=embeddings,
        ...     additional=additional
        ... )
        """
        metadata = {
            "repositoryid": repositoryid,
            "access_policy": access_policy,  # why access_policy on the microdata but not timeseries???
            "published": published,
            "overwrite": overwrite,  # similarly overwrite
            "doc_desc": doc_desc,
            "study_desc": study_desc,
            "data_files": data_files,
            "variables": variables,
            "variable_groups": variable_groups,
            "provenance": provenance,
            "tags": tags,
            "lda_topics": lda_topics,
            "embeddings": embeddings,
            "additional": additional,
        }
        return self._create_log(metadata, "survey")

    def create_log_of_video(
        self,
        video_description: Union[Dict, video_schema.VideoDescription],
        repositoryid: Optional[str] = None,
        published: Optional[int] = 0,
        overwrite: Optional[Union[str, video_schema.Overwrite]] = "no",
        metadata_information: Optional[Union[Dict, video_schema.MetadataInformation]] = None,
        provenance: Optional[List[Union[Dict, video_schema.ProvenanceSchema]]] = None,
        tags: Optional[List[Union[Dict, video_schema.Tag]]] = None,
        lda_topics: Optional[List[Union[Dict, video_schema.LdaTopic]]] = None,
        embeddings: Optional[List[Union[Dict, video_schema.Embedding]]] = None,
        additional: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        Creates a record of your *video* metadata

        Args:
            video_description (VideoDescription or Dictionary): Video metadata information. This field is required.
            repositoryid (Optional[str]): Collection ID that owns the document.
            published (Optional[int]): Status - 0=draft, 1=published. Defaults to 0.
            overwrite (Optional[Overwrite or str]): Overwrite document if already exists?. Defaults to 'no'.
            metadata_information (Optional[MetadataInformation or Dictionary]): Document metadata information.
            provenance (Optional[List[ProvenanceSchema or Dictionary]]): Provenance.
            tags (Optional[List[Tag or Dictionary]]): Tags.
            lda_topics (Optional[List[LdaTopic or Dictionary]]): LDA topics.
            embeddings (Optional[List[Embedding or Dictionary]]): Word embeddings.
            additional (Optional[Dict[str, Any]]): Additional metadata.

        Returns:
            int: The ID of the newly created video metadata
        """
        video_metadata = {
            "repositoryid": repositoryid,
            "published": published,
            "overwrite": overwrite,
            "metadata_information": metadata_information,
            "video_description": video_description,
            "provenance": provenance,
            "tags": tags,
            "lda_topics": lda_topics,
            "embeddings": embeddings,
            "additional": additional,
        }
        return self._create_log(video_metadata, "video")

    def _create_log(self, metadata: MetadataDict, metadata_type: str):
        assert metadata_type in self._metadata_types, (
            f"this project is listed as a '{metadata_type}' type project but this is"
            f" unknown. Projects must be one of {list(self._metadata_types.keys())}"
        )
        validate_metadata(metadata, self._metadata_types[metadata_type])
        md = self._metadata_types[metadata_type](**metadata)

        post_request_pth = f"/editor/create/{metadata_type.replace('_', '-')}"
        ret = self._post_request(pth=post_request_pth, metadata=md.model_dump(exclude_none=True, exclude_unset=True))
        return ret["id"]

    def update_by_id_from_excel(self, id: int, metadata_type: str, filename: str):
        """
        Updates the logged metadata based on an appropriately formatted Excel file.

        To save an existing project to Excel call:

            MetadataEditor.save_project_metadata_to_excel(id, filename, title):

        Args:
            metadata_type (str): the name of a supported metadata type, currently:
                    document, script, series, survey, table, timeseries, timeseries_DB, video
                Currently not supported:
                    geospatial, image
            filename (str): The path to the Excel file.

        Returns:
            int: The ID of the newly created document metadata
        """
        metadata_type = metadata_type.lower()
        ob = self.read_metadata_excel(metadata_type=metadata_type, filename=filename)
        self._update_by_id(id, metadata_type, ob.model_dump())

    def update_document_by_id_from_excel(self, id: int, filename: str):
        self.update_by_id_from_excel(id=id, metadata_type="document", filename=filename)

    def update_script_by_id_from_excel(self, id: int, filename: str):
        self.update_by_id_from_excel(id=id, metadata_type="script", filename=filename)

    def update_series_by_id_from_excel(self, id: int, filename: str):
        raise NotImplementedError("series metadata are not accepted by the API. Try timeseries if applicable")
        # self.update_by_id_from_excel(id = id, metadata_type='series', filename=filename)

    def update_survey_by_id_from_excel(self, id: int, filename: str):
        self.update_by_id_from_excel(id=id, metadata_type="survey", filename=filename)

    def update_table_by_id_from_excel(self, id: int, filename: str):
        self.update_by_id_from_excel(id=id, metadata_type="table", filename=filename)

    def update_timeseries_by_id_from_excel(self, id: int, filename: str):
        self.update_by_id_from_excel(id=id, metadata_type="timeseries", filename=filename)

    def update_timeseries_db_by_id_from_excel(self, id: int, filename: str):
        self.update_by_id_from_excel(id=id, metadata_type="timeseries_db", filename=filename)

    def update_video_by_id_from_excel(self, id: int, filename: str):
        self.update_by_id_from_excel(id=id, metadata_type="video", filename=filename)

    def update_document_by_id(
        self,
        id: int,
        document_description: Optional[Union[Dict, document_schema.DocumentDescription]] = None,
        repositoryid: Optional[str] = None,
        published: Optional[int] = None,
        overwrite: Optional[Union[Dict, document_schema.Overwrite]] = None,
        metadata_information: Optional[Union[Dict, document_schema.MetadataInformation]] = None,
        provenance: Optional[Union[List[Dict], List[document_schema.ProvenanceSchema]]] = None,
        tags: Optional[Union[List[Dict], List[document_schema.Tag]]] = None,
        lda_topics: Optional[Union[List[Dict], List[document_schema.LdaTopic]]] = None,
        embeddings: Optional[Union[List[Dict], List[document_schema.Embedding]]] = None,
        additional: Optional[Dict] = None,
    ):
        """
        Updates a record of your *document* metadata by ID

        Args:
            id (int): The ID of the document to update.
            document_description (Optional[DocumentDescription or Dictionary]): Description of the document. Leave
                blank if you don't want to replace the existing values.
            repositoryid (Optional[str]): Collection ID that owns the survey. Leave blank if you don't want to replace
                the existing values.
            published (Optional[int]): Status of the survey - 0=draft, 1=published. Leave blank if you don't want to
                replace the existing values.
            overwrite (Optional[Overwrite or Dictionary]): Overwrite survey if already exists? Leave blank if you don't
                want to replace the existing values.
            metadata_information (Optional[MetadataInformation or Dictionary]): Document metadata information. Leave
                blank if you don't want to replace the existing values.
            provenance (Optional[List[ProvenanceSchema or Dictionary]]): List of provenance schemas. Leave blank if you
                don't want to replace the existing values.
            tags (Optional[List[Tag or Dictionary]]): List of tags. Leave blank if you don't want to replace the
                existing values.
            lda_topics (Optional[List[LdaTopic or Dictionary]]): List of LDA topics. Leave blank if you don't want to
                replace the existing values.
            embeddings (Optional[List[Embedding or Dictionary]]): List of word embeddings. Leave blank if you don't
                want to replace the existing values.
            additional (Optional[Dictionary]): Additional metadata not covered by the schema. Leave blank if you don't
                want to replace the existing values.
        """
        update_data = {
            "document_description": document_description,
            "repositoryid": repositoryid,
            "published": published,
            "overwrite": overwrite,
            "metadata_information": metadata_information,
            "provenance": provenance,
            "tags": tags,
            "lda_topics": lda_topics,
            "embeddings": embeddings,
            "additional": additional,
        }
        self._update_by_id(id, "document", update_data)

    def update_image_by_id(self, id):
        raise NotImplementedError("There's an issue with schema definition of image metadata causing __root__ errors")

    def update_geospatial_by_id(
        self,
        id: int,
        description: Optional[Union[Dict, geospatial_schema.Description]] = None,
        idno: Optional[str] = None,
        metadata_information: Optional[Union[Dict, geospatial_schema.MetadataInformation]] = None,
        provenance: Optional[List[Union[Dict, geospatial_schema.ProvenanceSchema]]] = None,
        tags: Optional[List[Union[Dict, geospatial_schema.Tag]]] = None,
        lda_topics: Optional[List[Union[Dict, geospatial_schema.LdaTopic]]] = None,
        embeddings: Optional[List[Union[Dict, geospatial_schema.Embedding]]] = None,
        additional: Optional[Dict[str, Any]] = None,
    ):
        """
        Updates a record of your *geospatial* metadata by ID

        Args:
            id (int): The ID of the geospatial metadata to update.
            description (Optional[Description or Dictionary]): Description. Leave blank if you don't want to replace
                the existing values.
            idno (Optional[str]): Project unique identifier. Leave blank if you don't want to replace the existing
                values.
            metadata_information (Optional[MetadataInformation or Dictionary]): Document metadata information. Leave
                blank if you don't want to replace the existing values.
            provenance (Optional[List[ProvenanceSchema or Dictionary]]): Provenance. Leave blank if you don't want to
                replace the existing values.
            tags (Optional[List[Tag or Dictionary]]): Tags. Leave blank if you don't want to replace the existing
                values.
            lda_topics (Optional[List[LdaTopic or Dictionary]]): LDA topics. Leave blank if you don't want to replace
                the existing values.
            embeddings (Optional[List[Embedding or Dictionary]]): Word embeddings. Leave blank if you don't want to
                replace the existing values.
            additional (Optional[Dict[str, Any]]): Additional metadata. Leave blank if you don't want to replace the
                existing values.
        """
        update_data = {
            "idno": idno,
            "metadata_information": metadata_information,
            "description": description,
            "provenance": provenance,
            "tags": tags,
            "lda_topics": lda_topics,
            "embeddings": embeddings,
            "additional": additional,
        }
        self._update_by_id(id, "geospatial", update_data)

    def update_script_by_id(
        self,
        id: int,
        repositoryid: Optional[str] = None,
        published: Optional[int] = None,
        overwrite: Optional[Union[Dict, script_schema.Overwrite]] = None,
        doc_desc: Optional[Union[Dict, script_schema.DocDesc]] = None,
        project_desc: Optional[Union[Dict, script_schema.ProjectDesc]] = None,
        provenance: Optional[Union[List[Dict], List[script_schema.ProvenanceSchema]]] = None,
        tags: Optional[Union[List[Dict], List[script_schema.Tag]]] = None,
        lda_topics: Optional[Union[List[Dict], List[script_schema.LdaTopic]]] = None,
        embeddings: Optional[Union[List[Dict], List[script_schema.Embedding]]] = None,
        additional: Optional[Dict] = None,
    ):
        """
        Updates a record of your *script* metadata by ID

        Args:
            id (int): The ID of the script to update.
            repositoryid (Optional[str]): Collection ID that owns the project. Leave blank if you don't want to replace
                the existing values.
            published (Optional[int]): Status of the project - 0=draft, 1=published. Leave blank if you don't want to
                replace the existing values.
            overwrite (Optional[Overwrite or Dictionary]): Overwrite document if already exists? Leave blank if you
                don't want to replace the existing values.
            doc_desc (Optional[DocDesc or Dictionary]): Description of the document. Leave blank if you don't want to
                replace the existing values.
            project_desc (Optional[ProjectDesc or Dictionary]): Description of the research project. Leave blank if you
                don't want to replace the existing values.
            provenance (Optional[List[ProvenanceSchema or Dictionary]]): List of provenance schemas. Leave blank if you
                don't want to replace the existing values.
            tags (Optional[List[Tag or Dictionary]]): List of tags. Leave blank if you don't want to replace the
                existing values.
            lda_topics (Optional[List[LdaTopic or Dictionary]]): List of LDA topics. Leave blank if you don't want to
                replace the existing values.
            embeddings (Optional[List[Embedding or Dictionary]]): List of word embeddings. Leave blank if you don't
                want to replace the existing values.
            additional (Optional[Dictionary]): Additional metadata not covered by the schema. Leave blank if you don't
                want to replace the existing values.
        """
        update_data = {
            "repositoryid": repositoryid,
            "published": published,
            "overwrite": overwrite,
            "doc_desc": doc_desc,
            "project_desc": project_desc,
            "provenance": provenance,
            "tags": tags,
            "lda_topics": lda_topics,
            "embeddings": embeddings,
            "additional": additional,
        }
        self._update_by_id(id, "script", update_data)

    def update_series_by_id(
        self,
        id: int,
        idno: Optional[str] = None,
        name: Optional[str] = None,
        db_idno: Optional[str] = None,
        aliases: Optional[List[Union[Dict, series_schema.Alias]]] = None,
        measurement_unit: Optional[str] = None,
        periodicity: Optional[str] = None,
        base_period: Optional[str] = None,
        definition_short: Optional[str] = None,
        definition_long: Optional[str] = None,
        definition_references: Optional[List[Union[Dict, series_schema.DefinitionReference]]] = None,
        related_concepts: Optional[List[Union[Dict, series_schema.RelatedConcept]]] = None,
        methodology: Optional[str] = None,
        imputation: Optional[str] = None,
        quality_checks: Optional[str] = None,
        quality_note: Optional[str] = None,
        series_break: Optional[str] = None,
        statistical_concept: Optional[str] = None,
        limitation: Optional[str] = None,
        topics: Optional[List[Union[Dict, series_schema.Topic]]] = None,
        relevance: Optional[str] = None,
        series_dates: Optional[List[Union[Dict, series_schema.SeriesDate]]] = None,
        geographic_units: Optional[List[Union[Dict, series_schema.GeographicUnit]]] = None,
        aggregation_method: Optional[str] = None,
        ser_access_license: Optional[Union[Dict, series_schema.SerAccessLicense]] = None,
        confidentiality: Optional[str] = None,
        confidentiality_status: Optional[str] = None,
        confidentiality_note: Optional[str] = None,
        series_links: Optional[List[Union[Dict, series_schema.SeriesLink]]] = None,
        api_documentation: Optional[Union[Dict, series_schema.ApiDocumentation]] = None,
        source: Optional[str] = None,
        source_note: Optional[str] = None,
        keywords: Optional[List[Union[Dict, series_schema.Keyword]]] = None,
        notes: Optional[List[Union[Dict, series_schema.Note]]] = None,
        related_indicators: Optional[List[Union[Dict, series_schema.RelatedIndicator]]] = None,
        compliance: Optional[List[Union[Dict, series_schema.ComplianceItem]]] = None,
        series_groups: Optional[List[Union[Dict, series_schema.SeriesGroup]]] = None,
    ):
        raise NotImplementedError("series metadata are not accepted by the API. Try timeseries if applicable")
        # """
        # Updates a record of your *series* metadata by ID

        # Args:
        #     id (int): The ID of the series to update.
        #     idno (Optional[str]): Series unique ID. Leave blank if you don't want to replace the existing values.
        #     name (Optional[str]): Series Name. Leave blank if you don't want to replace the existing values.
        #     db_idno (Optional[str]): Series database ID. Leave blank if you don't want to replace the existing values.
        #     aliases (Optional[List[Alias or Dictionary]]): Series other names. Leave blank if you don't want to
        #         replace the existing values.
        #     measurement_unit (Optional[str]): Series unit of measure. Leave blank if you don't want to replace the
        #         existing values.
        #     periodicity (Optional[str]): Periodicity of data. Leave blank if you don't want to replace the existing
        #         values.
        #     base_period (Optional[str]): Base period. Leave blank if you don't want to replace the existing values.
        #     definition_short (Optional[str]): Short definition. Leave blank if you don't want to replace the existing
        #         values.
        #     definition_long (Optional[str]): Long definition. Leave blank if you don't want to replace the existing
        #         values.
        #     definition_references (Optional[List[DefinitionReference or Dictionary]]): URL to standard definition of
        #         the indicator (international or national standard). Leave blank if you don't want to replace the
        #         existing values.
        #     related_concepts (Optional[List[RelatedConcept or Dictionary]]): Related concepts. Leave blank if you
        #         don't want to replace the existing values.
        #     methodology (Optional[str]): Methodology. Leave blank if you don't want to replace the existing values.
        #     imputation (Optional[str]): Imputations. Leave blank if you don't want to replace the existing values.
        #     quality_checks (Optional[str]): Quality control methods. Leave blank if you don't want to replace the
        #         existing values.
        #     quality_note (Optional[str]): Note on data quality. Leave blank if you don't want to replace the existing
        #         values.
        #     series_break (Optional[str]): Breaks in series. Leave blank if you don't want to replace the existing
        #         values.
        #     statistical_concept (Optional[str]): Statistical concept. Leave blank if you don't want to replace the
        #         existing values.
        #     limitation (Optional[str]): Limitations and exceptions. Leave blank if you don't want to replace the
        #         existing values.
        #     topics (Optional[List[Topic or Dictionary]]): Topics covered by the indicator. Leave blank if you don't
        #         want to replace the existing values.
        #     relevance (Optional[str]): Relevance. Leave blank if you don't want to replace the existing values.
        #     series_dates (Optional[List[SeriesDate or Dictionary]]): Series dates. Leave blank if you don't want to
        #         replace the existing values.
        #     geographic_units (Optional[List[GeographicUnit or Dictionary]]): Geographic locations. Leave blank if you
        #         don't want to replace the existing values.
        #     aggregation_method (Optional[str]): Aggregation method. Leave blank if you don't want to replace the
        #         existing values.
        #     ser_access_license (Optional[SerAccessLicense or Dictionary]): Access license. Leave blank if you don't
        #         want to replace the existing values.
        #     confidentiality (Optional[str]): Confidentiality statement. Leave blank if you don't want to replace the
        #         existing values.
        #     confidentiality_status (Optional[str]): Confidentiality status. Leave blank if you don't want to replace
        #         the existing values.
        #     confidentiality_note (Optional[str]): Confidentiality note. Leave blank if you don't want to replace the
        #         existing values.
        #     series_links (Optional[List[SeriesLink or Dictionary]]): Links to API calls, websites, etc. Leave blank if
        #         you don't want to replace the existing values.
        #     api_documentation (Optional[ApiDocumentation or Dictionary]): API Documentation. Leave blank if you don't
        #         want to replace the existing values.
        #     source (Optional[str]): Original source. Leave blank if you don't want to replace the existing values.
        #     source_note (Optional[str]): Notes from original source. Leave blank if you don't want to replace the
        #         existing values.
        #     keywords (Optional[List[Keyword or Dictionary]]): Keywords. Leave blank if you don't want to replace the
        #         existing values.
        #     notes (Optional[List[Note or Dictionary]]): Notes. Leave blank if you don't want to replace the existing
        #         values.
        #     related_indicators (Optional[List[RelatedIndicator or Dictionary]]): Related indicators. Leave blank if
        #         you don't want to replace the existing values.
        #     compliance (Optional[List[ComplianceItem or Dictionary]]): Compliance with international resolution. Leave
        #         blank if you don't want to replace the existing values.
        #     series_groups (Optional[List[SeriesGroup or Dictionary]]): Series included in groups. Leave blank if you
        #         don't want to replace the existing values.
        # """
        # update_data = {
        #     "idno": idno,
        #     "name": name,
        #     "db_idno": db_idno,
        #     "aliases": aliases,
        #     "measurement_unit": measurement_unit,
        #     "periodicity": periodicity,
        #     "base_period": base_period,
        #     "definition_short": definition_short,
        #     "definition_long": definition_long,
        #     "definition_references": definition_references,
        #     "related_concepts": related_concepts,
        #     "methodology": methodology,
        #     "imputation": imputation,
        #     "quality_checks": quality_checks,
        #     "quality_note": quality_note,
        #     "series_break": series_break,
        #     "statistical_concept": statistical_concept,
        #     "limitation": limitation,
        #     "topics": topics,
        #     "relevance": relevance,
        #     "series_dates": series_dates,
        #     "geographic_units": geographic_units,
        #     "aggregation_method": aggregation_method,
        #     "ser_access_license": ser_access_license,
        #     "confidentiality": confidentiality,
        #     "confidentiality_status": confidentiality_status,
        #     "confidentiality_note": confidentiality_note,
        #     "series_links": series_links,
        #     "api_documentation": api_documentation,
        #     "source": source,
        #     "source_note": source_note,
        #     "keywords": keywords,
        #     "notes": notes,
        #     "related_indicators": related_indicators,
        #     "compliance": compliance,
        #     "series_groups": series_groups,
        # }

        # self._update_by_id(id, "series", update_data)

    def update_table_by_id(
        self,
        id: int,
        repositoryid: Optional[str] = None,
        published: Optional[int] = None,
        overwrite: Optional[Union[str, table_schema.Overwrite]] = None,
        metadata_information: Optional[Union[Dict, table_schema.MetadataInformation]] = None,
        table_description: Optional[Union[Dict, table_schema.TableDescription]] = None,
        provenance: Optional[List[Union[Dict, table_schema.ProvenanceSchema]]] = None,
        tags: Optional[List[Union[Dict, table_schema.Tag]]] = None,
        lda_topics: Optional[List[Union[Dict, table_schema.LdaTopic]]] = None,
        embeddings: Optional[List[Union[Dict, table_schema.Embedding]]] = None,
        additional: Optional[Dict[str, Any]] = None,
    ):
        """
        Updates a record of your *table* metadata by ID

        Args:
            id (int): The ID of the table to update.
            repositoryid (Optional[str]): Collection ID that owns the document. Leave blank if you don't want to
                replace the existing values.
            published (Optional[int]): Status - 0=draft, 1=published. Leave blank if you don't want to replace the
                existing values.
            overwrite (Optional[Overwrite or str]): Overwrite document if already exists?. Leave blank if you don't
                want to replace the existing values.
            metadata_information (Optional[MetadataInformation or Dictionary]): Document metadata information. Leave
                blank if you don't want to replace the existing values.
            table_description (Optional[TableDescription or Dictionary]): Table Description. Leave blank if you don't
                want to replace the existing values.
            provenance (Optional[List[ProvenanceSchema or Dictionary]]): List of Provenances. Leave blank if you don't
                want to replace the existing values.
            tags (Optional[List[Tag or Dictionary]]): List of Tags. Leave blank if you don't want to replace the
                existing values.
            lda_topics (Optional[List[LdaTopic or Dictionary]]): List of LDA topics. Leave blank if you don't want to
                replace the existing values.
            embeddings (Optional[List[Embedding or Dictionary]]): List of word embeddings. Leave blank if you don't
                want to replace the existing values.
            additional (Optional[Dict[str, Any]]): Additional metadata. Leave blank if you don't want to replace the
                existing values.
        """
        update_data = {
            "repositoryid": repositoryid,
            "published": published,
            "overwrite": overwrite,
            "metadata_information": metadata_information,
            "table_description": table_description,
            "provenance": provenance,
            "tags": tags,
            "lda_topics": lda_topics,
            "embeddings": embeddings,
            "additional": additional,
        }
        self._update_by_id(id, "table", update_data)

    def update_timeseries_by_id(
        self,
        id: int,
        series_description: Optional[Union[Dict, timeseries_schema.SeriesDescription]] = None,
        metadata_information: Optional[Union[Dict, timeseries_schema.MetadataInformation]] = None,
        datacite: Optional[Union[Dict, timeseries_schema.DataciteSchema]] = None,
        provenance: Optional[List[Union[Dict, timeseries_schema.ProvenanceSchema]]] = None,
        tags: Optional[Union[Dict, List[timeseries_schema.Tag]]] = None,
        additional: Optional[Dict] = None,
    ):
        """
        Args:
            id (int): the id of the project, not to be confused with the idno.
            series_description (Optional[SeriesDescription or Dictionary]): Can be an instance of SeriesDescription
                defined like SeriesDescription(idno="", name="", etc). Or as a dictionary like
                {"idno": "", "name": "", etc}. Leave blank if you don't want to replace the existing values.
            metadata_information (Optional[MetadataInformation or Dictionary]): Information on who generated the
                documentation. Can be a MetadataInformation object or a dictionary. Leave blank if you don't want to
                replace the existing values.
            datacite (Optional[DataciteSchema or Dictionary]): DataCite metadata for generating DOI. Can be a
                DataciteSchema object or a Dictionary. Leave blank if you don't want to replace the existing values.
            provenance (Optional[List[ProvenanceSchema or Dictionary]]): Can be a list of ProvenanceSchema objects or a
                list of dictionaries. Leave blank if you don't want to replace the existing values.
            tags (Optional[List[Tag or Dictionary]]): Can be a list of Tag objects or a list of dictionaries.
                Leave blank if you don't want to replace the existing values.
            additional (Optional[Dictionary]): Any other custom metadata not covered by the schema. A dictionary.
                Leave blank if you don't want to replace the existing values.

        """
        # todo(gblackadder) as implemented, if the user wants to update a single value within series_description, for
        # example, they need to write out the entire series description, writing out again the elements they don't want
        # changed. A good workflow would be to get metadata by id as a TimeSeriesMetadata object and help users update
        # that object. But only if there is a user friendly way of doing that.

        # todo(gblackadder) check that it's correct you can't update the idno. The documentation
        #   https://metadataeditorqa.worldbank.org/api-documentation/editor/#operation/createTimeseries
        #   implies you can but in my observation from calling the api, you cannot

        update_data = {
            "series_description": series_description,
            "metadata_information": metadata_information,
            "datacite": datacite,
            "provenance": provenance,
            "tags": tags,
            "additional": additional,
        }
        self._update_by_id(id, "timeseries", update_data)

    def update_timeseries_db_by_id(
        self,
        id: int,
        database_description: Optional[Union[Dict, timeseries_db_schema.DatabaseDescription]] = None,
        published: Optional[int] = None,
        overwrite: Optional[Union[str, timeseries_db_schema.Overwrite]] = None,
        metadata_information: Optional[Union[Dict, timeseries_db_schema.MetadataInformation]] = None,
        provenance: Optional[List[Union[Dict, timeseries_db_schema.ProvenanceSchema]]] = None,
        additional: Optional[Dict[str, Any]] = None,
    ):
        """
        Updates a record of your *timeseries database* metadata by ID

        Args:
            id (int): The ID of the timeseries database to update.
            published (Optional[int]): Status - 0=draft, 1=published. Leave blank if you don't want to replace the
                existing values.
            overwrite (Optional[Overwrite or str]): Overwrite database if already exists?. Leave blank if you don't
                want to replace the existing values.
            metadata_information (Optional[MetadataInformation or Dictionary]): Document metadata information. Leave
                blank if you don't want to replace the existing values.
            database_description (Optional[DatabaseDescription or Dictionary]): Database Description. Leave blank if
                you don't want to replace the existing values.
            provenance (Optional[List[ProvenanceSchema or Dictionary]]): Provenance. Leave blank if you don't want to
                replace the existing values.
            additional (Optional[Dict[str, Any]]): Additional custom metadata. Leave blank if you don't want to
                replace the existing values.
        """
        update_data = {
            "published": published,
            "overwrite": overwrite,
            "metadata_information": metadata_information,
            "database_description": database_description,
            "provenance": provenance,
            "additional": additional,
        }
        self._update_by_id(id, "timeseries_db", update_data)

    def update_survey_by_id(
        self,
        id: int,
        repositoryid: Optional[str] = None,
        access_policy: Optional[Union[str, microdata_schema.AccessPolicy]] = None,
        published: Optional[int] = None,
        overwrite: Optional[Union[str, microdata_schema.Overwrite]] = None,
        doc_desc: Optional[Union[Dict, microdata_schema.DocDesc]] = None,
        study_desc: Optional[Union[Dict, microdata_schema.StudyDesc]] = None,
        data_files: Optional[Union[List[Dict], List[microdata_schema.DatafileSchema]]] = None,
        variables: Optional[Union[List[Dict], List[microdata_schema.VariableSchema]]] = None,
        variable_groups: Optional[Union[List[Dict], List[microdata_schema.VariableGroupSchema]]] = None,
        provenance: Optional[Union[List[Dict], List[microdata_schema.ProvenanceSchema]]] = None,
        tags: Optional[Union[List[Dict], List[microdata_schema.Tag]]] = None,
        lda_topics: Optional[Union[List[Dict], List[microdata_schema.LdaTopic]]] = None,
        embeddings: Optional[Union[List[Dict], List[microdata_schema.Embedding]]] = None,
        additional: Optional[MetadataDict] = None,
    ):
        """
        Args:
            id (int): the id of the project.
            repositoryid : Optional[str]
                The identifier for the repository where the survey microdata is to be stored.
            access_policy : Optional[Union[str, AccessPolicy]]
                The access policy for the survey data. Can be a string or an AccessPolicy object.
            published : Optional[int]
                The publication status of the survey data. Typically, 0 for unpublished and 1 for published.
            overwrite : Optional[Union[str, Overwrite]]
                Policy for overwriting existing data. Can be a string or an Overwrite object.
            doc_desc : Optional[Union[Dict, DocDesc]]
                Description of the documentation for the survey. Can be a dictionary or a DocDesc object.
            study_desc : Optional[Union[Dict, StudyDesc]]
                Description of the study. Can be a dictionary or a StudyDesc object.
            data_files : Optional[Union[List[Dict], List[DatafileSchema]]]
                List of data files associated with the survey. Each item can be a dictionary or a DatafileSchema object.
            variables : Optional[Union[List[Dict], List[VariableSchema]]]
                List of variables included in the survey. Each item can be a dictionary or a VariableSchema object.
            variable_groups : Optional[Union[List[Dict], List[VariableGroupSchema]]]
                List of variable groups included in the survey. Each item can be a dictionary or a VariableGroupSchema
                object.
            provenance : Optional[Union[List[Dict], List[ProvenanceSchema]]]
                Provenance information for the survey data. Each item can be a dictionary or a ProvenanceSchema object.
            tags : Optional[Union[List[Dict], List[Tag]]]
                Tags associated with the survey data. Each item can be a dictionary or a Tag object.
            lda_topics : Optional[Union[List[Dict], List[LdaTopic]]]
                List of LDA topics associated with the survey. Each item can be a dictionary or an LdaTopic object.
            embeddings : Optional[Union[List[Dict], List[Embedding]]]
                List of embeddings associated with the survey. Each item can be a dictionary or an Embedding object.
            additional : Optional[Dict[str, Any]]
                Any additional metadata to be associated with the survey data.

        """
        # instead of by id, we could update by repositoryId if that is a unique identifier?
        update_data = {
            "repositoryid": repositoryid,
            "access_policy": access_policy,
            "published": published,
            "overwrite": overwrite,
            "doc_desc": doc_desc,
            "study_desc": study_desc,
            "data_files": data_files,
            "variables": variables,
            "variable_groups": variable_groups,
            "provenance": provenance,
            "tags": tags,
            "lda_topics": lda_topics,
            "embeddings": embeddings,
            "additional": additional,
        }
        self._update_by_id(id, "survey", update_data)

    def update_video_by_id(
        self,
        id: int,
        video_description: Optional[Union[Dict, video_schema.VideoDescription]] = None,
        repositoryid: Optional[str] = None,
        published: Optional[int] = None,
        overwrite: Optional[Union[str, video_schema.Overwrite]] = None,
        metadata_information: Optional[Union[Dict, video_schema.MetadataInformation]] = None,
        provenance: Optional[List[Union[Dict, video_schema.ProvenanceSchema]]] = None,
        tags: Optional[List[Union[Dict, video_schema.Tag]]] = None,
        lda_topics: Optional[List[Union[Dict, video_schema.LdaTopic]]] = None,
        embeddings: Optional[List[Union[Dict, video_schema.Embedding]]] = None,
        additional: Optional[Dict[str, Any]] = None,
    ):
        """
        Updates a record of your *video* metadata by ID

        Args:
            video_description (Optional[VideoDescription or Dictionary]): Video metadata information. Leave blank if
                you don't want to replace the existing values.
            id (int): The ID of the video to update.
            repositoryid (Optional[str]): Collection ID that owns the document. Leave blank if you don't want to
                replace the existing values.
            published (Optional[int]): Status - 0=draft, 1=published. Leave blank if you don't want to replace the
                existing values.
            overwrite (Optional[Overwrite or str]): Overwrite document if already exists?. Leave blank if you don't
                want to replace the existing values.
            metadata_information (Optional[MetadataInformation or Dictionary]): Document metadata information. Leave
                blank if you don't want to replace the existing values.
            provenance (Optional[List[ProvenanceSchema or Dictionary]]): Provenance. Leave blank if you don't want to
                replace the existing values.
            tags (Optional[List[Tag or Dictionary]]): Tags. Leave blank if you don't want to replace the existing
                values.
            lda_topics (Optional[List[LdaTopic or Dictionary]]): LDA topics. Leave blank if you don't want to replace
                the existing values.
            embeddings (Optional[List[Embedding or Dictionary]]): Word embeddings. Leave blank if you don't want to
                replace the existing values.
            additional (Optional[Dict[str, Any]]): Additional metadata. Leave blank if you don't want to replace the
                existing values.
        """

        update_data = {
            "repositoryid": repositoryid,
            "published": published,
            "overwrite": overwrite,
            "metadata_information": metadata_information,
            "video_description": video_description,
            "provenance": provenance,
            "tags": tags,
            "lda_topics": lda_topics,
            "embeddings": embeddings,
            "additional": additional,
        }
        self._update_by_id(id, "video", update_data)

    def _update_by_id(self, id: int, expected_project_type: str, new_metadata: Dict[str, Any]):
        assert expected_project_type in self._metadata_types
        project_data = self.get_project_by_id(id)
        project_type = project_data["type"].replace("-", "_")
        assert project_type in self._metadata_types, (
            f"this project is listed as a '{project_type}' type project but this is"
            f" unknown. Projects must be one of {list(self._metadata_types.keys())}"
        )
        assert expected_project_type == project_type, (
            f"You are trying to perform a {expected_project_type} update, "
            f"but the actual data is listed as {project_type}"
        )
        original_metadata = self.get_project_by_id(id)["metadata"]
        md = self._metadata_types[project_type](**original_metadata)

        new_metadata = standardize_keys_in_dict(new_metadata)
        md = update_metadata(md, **new_metadata)

        post_request_template_path = f"/editor/update/{project_type.replace('_', '-')}/" + "{}"
        self._post_request(
            post_request_template_path, id=id, metadata=md.model_dump(exclude_none=True, exclude_unset=True)
        )

    def list_collections(self) -> pd.DataFrame:
        """
        Lists all the collections associated with your API key.

        Returns:
            pd.DataFrame: Collection information
        """
        response = self._get_request("collections")
        if "collections" not in response or len(response["collections"]) == 0:
            return pd.DataFrame([], columns=["id", "title", "created"]).set_index("id")
        return pd.DataFrame(response["collections"]).set_index("id")

    def get_collection_by_id(self, id: int) -> pd.Series:
        """
        Args:
            id (int): the id of the collection.

        Returns:
            (pd.Series): a pandas series of the collection information

        Raises:
            Exception: You don't have permission to access this project - often this means the id is incorrect
        """
        collection_data = self._get_request("collections/{}", id=id)
        if "collection" not in collection_data:
            raise ValueError(f"API call was good but collection data missing from: {collection_data}")
        return pd.Series(collection_data["collection"])

    def create_collection(self, title: str, description: str):
        """
        Creates a new collection with the specified title and description.

        Args:
            title (str): The title of the collection.
            description (str): The description of the collection.

        Returns:
            (int): The id of the newly created collection
        """
        assert title != "", "The collection must have a title but an empty string was passed"
        ret = self._post_request("collections", metadata={"title": title, "description": description})
        return ret["collection"]

    def update_collection(self, id: int, title: Optional[str] = None, description: Optional[str] = None):
        """
            Updates the specified collection with a new title and/or description.

        Args:
            id (int): The unique identifier of the collection to update.
            title (Optional[str]): The new title of the collection. Defaults to None.
            description (Optional[str]): The new description of the collection. Defaults to None.

        Raises:
            Assertion error if both title and description are None, since we must update one or the other.
        """
        # todo(gblackadder): Is it clear this means update the title/description and not what data is in the collection?
        assert title is not None or description is not None, "can update title or description or both, but not neither"
        metadata = {}
        if title is not None:
            metadata["title"] = title
        if description is not None:
            metadata["description"] = description
        self._post_request("collections/update/{}", id=id, metadata=metadata)

    def list_projects_in_collection(
        self,
        collection: int,
        keywords: Optional[Union[str, List[str]]] = None,
        offset: int = 0,
        limit: Union[int, str] = 100,
        sort_by: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Retrieve projects that have been added to the given collection.

        Args:

            collection (int):
                The id of the collection.
            keyword (optional str):
                filter projects based on whether the project title or idno contains this keyword
            offset (int):
                Offset for pagination e.g. 10 to skip first 10 records. Default is 0.
            limit (int):
                The maximum number of projects to return, defaults to 100.
                If limit='All' then all records are retrieved.
            sort_by (optional str): valid values: "title_asc", "title_desc", "updated_asc", "updated_desc".

        Returns:

            pd.DataFrame:
                Information on the projects in the collection, such as id, idno, title and type.
        """

        if isinstance(limit, str):
            assert limit.lower() == "all", f"Expected limit to be 'all' or a positive integer but got '{limit}'"
            new_offset = offset
            new_limit = 100
            dfs = []
            while True:
                df = self.list_projects_in_collection(
                    collection=collection, keywords=keywords, offset=new_offset, limit=new_limit, sort_by=sort_by
                )
                dfs.append(df)
                if len(df) < new_limit:
                    break
                new_offset += new_limit
            return pd.concat(dfs)

        params = {"limit": limit, "offset": offset}
        if keywords is not None:
            if not isinstance(keywords, str) and isinstance(keywords, Iterable):
                keywords = "%".join(keywords)
            keywords = keywords.replace(" ", "%")
            params["keywords"] = keywords
        if sort_by is not None:
            sort_by = sort_by.lower()
            valid_sort_by = ["title_asc", "title_desc", "updated_asc", "updated_desc"]
            assert sort_by in valid_sort_by, f"{sort_by} not valid, must be one of {valid_sort_by}"
            params["sort_by"] = sort_by
        ret = self._get_request("editor?collection={}", id=collection, params=params)
        if ret["total"] > ret["limit"]:
            warnings.warn(
                f"There are {ret['total']} projects in this collection but a limit of {ret['limit']} were retreived",
                UserWarning,
            )
        if len(ret["projects"]) == 0:
            return pd.DataFrame([], columns=["id", "type", "idno", "title"]).set_index("id")
        return pd.DataFrame(ret["projects"]).set_index("id")

    def add_projects_to_collection(
        self, collection: Union[int, List[int]], id_format: str, projects: Union[int, List[int], str, List[str]]
    ):
        """
        Adds project or projects to specified collection or collections.

        This method associates one or more projects with one or more collections. The `collection`
        parameter can be a single collection ID or a list of collection IDs. The `projects` parameter
        can be a single project ID, a single project ID number (idno), a list of project IDs, or a list
        of project idnos. The `id_format` parameter specifies whether the project identifiers
        are in the form of IDs (integer) or idno (string).

        Args:

            collection : Union[int, List[int]]
                A single collection ID or a list of collection IDs to which projects should be added.

            id_format : str
                Specifies the format of the project identifiers. Must be either 'id' or 'idno'.

            projects : Union[int, List[int], str, List[str]]
                A single project ID, a single project idno, a list of project IDs, or a list of
                project idnos to be added to the specified collection(s).

        Raises:

            AssertionError
                If `id_format` is not 'id' or 'idno'.

            AssertionError
                If a project ID is not an integer when `id_format` is 'id'.

            AssertionError
                If a project ID number is not a string when `id_format` is 'idno'.

        Example:
            >>> client.add_projects_to_collection(collection=1, id_format='id', projects=[101, 102])
            >>> client.add_projects_to_collection(collection=[1, 2], id_format='idno', projects=['A101', 'A102'])
        """
        assert id_format.lower() in ["id", "idno"], f"id_format must be either 'id' or 'idno' but got '{id_format}'"
        if not isinstance(collection, Iterable) or isinstance(collection, str):
            collection = [collection]

        if not isinstance(projects, Iterable) or isinstance(projects, str):
            projects = [projects]
        if id_format.lower() == "id":
            for proj in projects:
                assert isinstance(proj, int), f"When passing ids the projects must be ints, but found: {proj}"
        else:
            for proj in projects:
                assert isinstance(proj, str), f"While passing idnos the projects must be strs but found: {proj}"
        self._post_request(
            "collections/add_projects",
            metadata={"collections": collection, "id_format": id_format, "projects": projects},
        )

    def remove_projects_from_collection(
        self, collection: Union[int, List[int]], id_format: str, projects: Union[int, List[int], str, List[str]]
    ):
        """
        Removes project or projects from specified collection or collections.

        This method dissociates one or more projects from one or more collections. The `collection`
        parameter can be a single collection ID or a list of collection IDs. The `projects` parameter
        can be a single project ID, a single project ID number (idno), a list of project IDs, or a list
        of project idnos. The `id_format` parameter specifies whether the project identifiers
        are in the form of IDs or idnos.

        Note that if the project(s) are not in the collection there is no error raised since either way the project
            will not be in the collection after this function executes

        Args

            collection : Union[int, List[int]]
                A single collection ID or a list of collection IDs to which projects should be removed.

            id_format : str
                Specifies the format of the project identifiers. Must be either 'id' or 'idno'.

            projects : Union[int, List[int], str, List[str]]
                A single project ID, a single project idno, a list of project IDs, or a list of
                project idnos to be removed from the specified collection(s).

        Raises:

            AssertionError
                If `id_format` is not 'id' or 'idno'.

            AssertionError
                If a project ID is not an integer when `id_format` is 'id'.

            AssertionError
                If a project ID number is not a string when `id_format` is 'idno'.


        Example:

            >>> client.remove_projects_from_collection(collection=1, id_format='id', projects=[101, 102])
            >>> client.remove_projects_from_collection(collection=[1, 2], id_format='idno', projects=['A101', 'A102'])

        """
        assert id_format.lower() in ["id", "idno"], f"id_format must be either 'id' or 'idno' but got '{id_format}'"
        if not isinstance(projects, Iterable) or isinstance(projects, str):
            projects = [projects]
        if id_format.lower() == "id":
            for proj in projects:
                assert isinstance(proj, int), f"When passing ids the projects must be ints, but found: {proj}"
        else:
            for proj in projects:
                assert isinstance(proj, str), f"While passing idnos the projects must be strs but found: {proj}"

        self._post_request(
            "collections/remove_projects",
            metadata={"collections": collection, "id_format": id_format, "projects": projects},
        )

    def list_templates(self) -> pd.DataFrame:
        """
        Retrieves templates, both standard and any custom templates

        Returns:
            pd.DataFrame: A DataFrame containing the templates. If none are found, an empty DataFrame is returned.
        """
        response = self._get_request("templates")
        if "templates" not in response or len(response["templates"]) == 0:
            return pd.DataFrame([], columns=["uid", "template_type", "name", "template"])
        else:
            return pd.DataFrame([v_item for _, v in response["templates"].items() for v_item in v])

    def get_template_by_uid(self, uid: str) -> pd.Series:
        """
        Retrieves given template by *UID*, not id.

        Args:
            uid (str): The Unique Identifier of the template to retrieve.

        Returns:
            pd.Series: A pandas Series containing the template details.
        """
        response = self._get_request("templates/{}", uid)
        if "result" not in response:
            raise KeyError(
                f"No template found although API call appeared successful for that UPI.\nResponse: {response}"
            )
        else:
            return pd.Series(response["result"], name=response["result"]["name"])

    def set_template_for_collection(self, collection_id: int, template_uid: str):
        """
        Set the specified template to be used for all metadata of its type (for example survey, timeseries, or
            document metadata) in the collection.

        Args:
            collection_id (int): the id of the collection.
            template_uid (str): The Unique Identifier of the template to apply to the collection.
        """
        # check collection exists
        self.get_collection_by_id(collection_id)
        template = self.get_template_by_uid(uid=template_uid)
        template_type = template["data_type"]
        self._post_request(
            "collections/template",
            metadata={"collection_id": collection_id, "template_uid": template_uid, "project_type": template_type},
        )

    def delete_template(self, uid: str):
        """
        Deletes the given template.

        Args:
            uid (str): The Unique Identifier of the template to delete.

        """
        self._delete_by_id("templates/delete/{}", id=uid, checker_fn=self.get_template_by_uid)
