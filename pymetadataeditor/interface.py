import warnings
from json import JSONDecodeError
from ssl import SSLError as ssl_SSLError
from typing import Any, Callable, Dict, Iterable, List, Optional, Union

import pandas as pd
import requests
from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, PrivateAttr, SecretStr, model_validator
from requests.exceptions import HTTPError, SSLError

import pymetadataeditor.schemas.survey_schema as sms
import pymetadataeditor.schemas.timeseries_schema as tss
from pymetadataeditor.schemas.common_schemas import SchemaBaseModel
from pymetadataeditor.tools import update_metadata, validate_metadata

warnings.filterwarnings(
    "ignore", category=UserWarning, module="pydantic"
)  # suppresses warning when metadata passed as dict instead of a pydantic object

MetadataDict = Dict[
    str,
    Union[str, bytes, int, float, SchemaBaseModel, "MetadataDict", List["MetadataDict"], List[SchemaBaseModel], None],
]


class DeleteNotAppliedError(Exception):
    def __init__(self, message="Delete request not accepted by system.", response=None):
        super().__init__(message)
        self.response = response


class MetadataEditor(BaseModel):
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
        default={"timeseries": tss.TimeseriesSchema, "survey": sms.SurveyMicrodataSchema}
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

    def _request(
        self, method: str, pth: str, json: Optional[MetadataDict] = None, id: Optional[Union[int, str]] = None
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
            assert "json" != None, "when using post, json cannot be none"
            request_kwargs["json"] = json

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
        except JSONDecodeError as e:
            raise JSONDecodeError(response) from e
        return json_response

    def _get_request(self, pth: str, id: Optional[Union[int, str]] = None) -> Dict:
        """
        Args:
            pth (str): The path appended to the API_URL to which the GET request is sent.

        Returns:
            Dict[str, str]: The JSON response from the server, parsed into a dictionary.
        """
        return self._request("get", pth=pth, id=id)

    def _post_request(self, pth: str, metadata: Optional[MetadataDict] = None, id: Optional[Union[int, str]] = None):
        """
        Args:
            pth (str): The path appended to the API_URL to which the POST request is sent.
            metadata (dict): The metadata to be sent with the POST request.

        Returns:
            Dict[str, str]: The JSON response from the server, parsed into a dictionary.
        """
        return self._request("post", pth=pth, id=id, json=metadata)

    def list_projects(self) -> pd.DataFrame:
        """
        Lists all the projects associated with your API key.

        Returns:
            pd.DataFrame: Projects sorted by the date on which they were created
        """
        list_projects_get_path = "/editor"
        response = self._get_request(list_projects_get_path)
        try:
            projects = response["projects"]
        except KeyError:  # is this the best way to cope with new accounts with no projects?
            return pd.DataFrame()
        return pd.DataFrame.from_dict(projects).set_index("id").sort_values("created")

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
    ) -> Union[MetadataDict, SchemaBaseModel]:
        """
        Args:
            id (int): the id of the project, not to be confused with the idno.
            exclude_unset (bool): when returning a dictionary (that is when as_object is False), if True then fields
                that were not set or have a None value are removed from the dictionary. Defaults to True
            as_object (bool): If True, return the metadata as a pydantic object.
                Otherwise, return a dictionary. Defaults to False.

        Returns:
            Union[SchemaBaseModel, Dict]: The metadata as either a dictionary or an object.
        """
        project = self.get_project_by_id(id=id)
        project_type = project["type"]
        assert project_type in self._metadata_types, (
            f"this project is listed as a '{project_type}' type project but this is"
            f" unknown. Projects must be one of {list(self._metadata_types.keys())}"
        )
        metadata_object = self._metadata_types[project_type](**project["metadata"])
        if as_object:
            return metadata_object
        else:
            return metadata_object.model_dump(exclude_none=exclude_unset, exclude_unset=exclude_unset)

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
        except PermissionError:
            pass  # evidently the entity was deleted because now it can't be found
        # except JSONDecodeError as e:

        else:
            raise DeleteNotAppliedError()

    def create_and_log_timeseries(
        self,
        idno: str,
        series_description: Union[Dict, tss.SeriesDescription],
        metadata_information: Optional[Union[Dict, tss.MetadataInformation]] = None,
        datacite: Optional[Union[Dict, tss.DataciteSchema]] = None,
        provenance: Optional[List[Union[Dict, tss.ProvenanceSchema]]] = None,
        tags: Optional[Union[Dict, List[tss.Tag]]] = None,
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
        return self._create_and_log(metadata, "timeseries")

    def create_and_log_survey_microdata(
        self,
        repositoryid: Optional[str] = None,
        access_policy: Optional[Union[str, sms.AccessPolicy]] = None,
        published: Optional[int] = None,
        overwrite: Optional[Union[str, sms.Overwrite]] = None,
        doc_desc: Optional[Union[Dict, sms.DocDesc]] = None,
        study_desc: Optional[Union[Dict, sms.StudyDesc]] = None,
        data_files: Optional[Union[List[Dict], List[sms.DatafileSchema]]] = None,
        variables: Optional[Union[List[Dict], List[sms.VariableSchema]]] = None,
        variable_groups: Optional[Union[List[Dict], List[sms.VariableGroupSchema]]] = None,
        provenance: Optional[Union[List[Dict], List[sms.ProvenanceSchema]]] = None,
        tags: Optional[Union[List[Dict], List[sms.Tag]]] = None,
        lda_topics: Optional[Union[List[Dict], List[sms.LdaTopic]]] = None,
        embeddings: Optional[Union[List[Dict], List[sms.Embedding]]] = None,
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

        >>> response = self.create_and_log_survey_microdata(
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
        return self._create_and_log(metadata, "survey")

    def _create_and_log(self, metadata: MetadataDict, metadata_type: str):
        assert metadata_type in self._metadata_types, (
            f"this project is listed as a '{metadata_type}' type project but this is"
            f" unknown. Projects must be one of {list(self._metadata_types.keys())}"
        )
        validate_metadata(metadata, self._metadata_types[metadata_type])
        md = self._metadata_types[metadata_type](**metadata)

        post_request_pth = f"/editor/create/{metadata_type}"
        ret = self._post_request(pth=post_request_pth, metadata=md.model_dump(exclude_none=True, exclude_unset=True))
        return ret["id"]

    def update_timeseries_by_id(
        self,
        id: int,
        # idno: Optional[str] = None,
        series_description: Optional[Union[Dict, tss.SeriesDescription]] = None,
        metadata_information: Optional[Union[Dict, tss.MetadataInformation]] = None,
        datacite: Optional[Union[Dict, tss.DataciteSchema]] = None,
        provenance: Optional[List[Union[Dict, tss.ProvenanceSchema]]] = None,
        tags: Optional[Union[Dict, List[tss.Tag]]] = None,
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

        self._update_by_id(
            id,
            "timeseries",
            series_description=series_description,
            metadata_information=metadata_information,
            datacite=datacite,
            provenance=provenance,
            tags=tags,
            additional=additional,
        )

    def update_survey_microdata_by_id(
        self,
        id: int,
        repositoryid: Optional[str] = None,
        access_policy: Optional[Union[str, sms.AccessPolicy]] = None,
        published: Optional[int] = None,
        overwrite: Optional[Union[str, sms.Overwrite]] = None,
        doc_desc: Optional[Union[Dict, sms.DocDesc]] = None,
        study_desc: Optional[Union[Dict, sms.StudyDesc]] = None,
        data_files: Optional[Union[List[Dict], List[sms.DatafileSchema]]] = None,
        variables: Optional[Union[List[Dict], List[sms.VariableSchema]]] = None,
        variable_groups: Optional[Union[List[Dict], List[sms.VariableGroupSchema]]] = None,
        provenance: Optional[Union[List[Dict], List[sms.ProvenanceSchema]]] = None,
        tags: Optional[Union[List[Dict], List[sms.Tag]]] = None,
        lda_topics: Optional[Union[List[Dict], List[sms.LdaTopic]]] = None,
        embeddings: Optional[Union[List[Dict], List[sms.Embedding]]] = None,
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
        self._update_by_id(
            id,
            "survey",
            repositoryid=repositoryid,
            access_policy=access_policy,
            published=published,
            overwrite=overwrite,
            doc_desc=doc_desc,
            study_desc=study_desc,
            data_files=data_files,
            variables=variables,
            variable_groups=variable_groups,
            provenance=provenance,
            tags=tags,
            lda_topics=lda_topics,
            embeddings=embeddings,
            additional=additional,
        )

    def _update_by_id(self, id: int, expected_project_type: str, **kwargs):
        assert expected_project_type in self._metadata_types
        project_data = self.get_project_by_id(id)
        project_type = project_data["type"]
        assert project_type in self._metadata_types, (
            f"this project is listed as a '{project_type}' type project but this is"
            f" unknown. Projects must be one of {list(self._metadata_types.keys())}"
        )
        assert expected_project_type == project_type, (
            f"You are trying to perform a {expected_project_type} update, "
            f"but the actual data is listed as {project_type}"
        )
        metadata = self.get_project_by_id(id)["metadata"]
        md = self._metadata_types[project_type](**metadata)

        md = update_metadata(md, **kwargs)

        post_request_template_path = f"/editor/update/{project_type}/" + "{}"
        self._post_request(
            post_request_template_path, id=id, metadata=md.model_dump(exclude_none=True, exclude_unset=True)
        )

    def list_collections(self) -> pd.DataFrame:
        """
        Lists all the collections associated with your API key.

        Returns:
            pd.DataFrame: Collections sorted by the date on which they were created
        """
        response = self._get_request("collections")
        if "collections" not in response or len(response["collections"]) == 0:
            return pd.DataFrame([], columns=["id", "title", "created"]).set_index("id")
        return pd.DataFrame(response["collections"]).set_index("id").sort_values("created")

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

    def list_projects_in_collection(self, collection: int) -> pd.DataFrame:
        """
        Retrieve projects that have been added to the given collection.

        Args:

            collection (int):
                The id of the collection

        Returns:

            pd.DataFrame:
                Information on the projects in the collection, such as id, idno, title and type
        """

        ret = self._get_request("editor?collection={}&limit=100", id=collection)
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

            ValueError
                If a specified collection ID does not exist.

            ValueError
                If a specified project ID or idno does not exist.

            AssertionError
                If a project ID is not an integer when `id_format` is 'id'.

            AssertionError
                If a project ID number is not a string when `id_format` is 'idno'.

        Example:
            >>> client.add_projects_to_collection(collection=1, id_format='id', projects=[101, 102])
            >>> client.add_projects_to_collection(collection=[1, 2], id_format='idno', projects=['A101', 'A102'])
        """
        self._manage_projects_in_collections("add", collection=collection, id_format=id_format, projects=projects)

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

            ValueError
                If a specified collection ID does not exist.

            AssertionError
                If a project ID is not an integer when `id_format` is 'id'.

            AssertionError
                If a project ID number is not a string when `id_format` is 'idno'.


        Example:

            >>> client.remove_projects_from_collection(collection=1, id_format='id', projects=[101, 102])
            >>> client.remove_projects_from_collection(collection=[1, 2], id_format='idno', projects=['A101', 'A102'])

        """
        self._manage_projects_in_collections("remove", collection=collection, id_format=id_format, projects=projects)

    def _manage_projects_in_collections(
        self,
        operation: str,
        collection: Union[int, List[int]],
        id_format: str,
        projects: Union[int, List[int], str, List[str]],
    ):
        assert operation in ["add", "remove"], f"expected operation to be add or remove but found '{operation}'"
        assert id_format.lower() in ["id", "idno"], f"id_format must be either 'id' or 'idno' but got '{id_format}'"
        collection_ids = self.list_collections().index
        if operation == "add":
            if not isinstance(collection, Iterable) or isinstance(collection, str):
                collection = [collection]
            for c in collection:
                if c not in collection_ids and str(c) not in collection_ids:
                    raise ValueError(f"Collection {c} not found")
        else:
            if collection not in collection_ids and str(collection) not in collection_ids:
                raise ValueError(f"Collection {collection} not found")
        if not isinstance(projects, Iterable) or isinstance(projects, str):
            projects = [projects]
        if id_format.lower() == "id":
            for proj in projects:
                assert isinstance(proj, int), f"When passing ids the projects must be ints, but found: {proj}"
        else:
            for proj in projects:
                assert isinstance(proj, str), f"While passing idnos the projects must be strs but found: {proj}"

        # note, no need to check if the projects exist in the collection.
        # the user is saying they don't want the project in the collection so if it's not in there to begin with then
        # that's what they wanted anyway
        if operation == "add":
            known_projects = self.list_projects()
            if id_format == "id":
                project_ids = known_projects.index
            else:
                project_ids = known_projects.idno.values
            for proj in projects:
                if proj not in project_ids and str(proj) not in project_ids:
                    raise ValueError(f"Project {proj} not found in {project_ids}")

        collection_key = "collections" if operation == "add" else "collection_id"
        self._post_request(
            f"collections/{operation}_projects",
            metadata={collection_key: collection, "id_format": id_format, "projects": projects},
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
