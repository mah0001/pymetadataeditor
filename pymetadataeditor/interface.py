import json
import warnings
from io import BufferedReader
from json import JSONDecodeError
from pathlib import Path
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
from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, SecretStr, model_validator
from requests.exceptions import HTTPError, SSLError

warnings.filterwarnings(
    "ignore", category=UserWarning, module="pydantic"
)  # suppresses warning when metadata passed as dict instead of a pydantic object


class DeleteNotAppliedError(Exception):
    def __init__(self, message="Delete request not accepted by system.", response=None):
        super().__init__(message)
        self.response = response


class APInterface(BaseModel):
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
        self,
        method: str,
        pth: str,
        json: Optional[Dict] = None,
        params: Optional[Dict[str, Union[str, List[str]]]] = None,
        id: Optional[Union[int, str]] = None,
        data: Optional[Dict[str, str]] = None,
        files: Optional[Dict[str, BufferedReader]] = None,
    ) -> Dict:
        """
        Sends a GET or POST request to the specified URL with the API key in the headers and returns the JSON response.

        Args:
            method (str): Either post or get
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
            if data is not None:
                request_kwargs["data"] = data
            if files is not None:
                request_kwargs["files"] = files
        if method == "get" and params is not None:
            assert json is None, "when using get, pass params not json"
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
            elif response.status_code == 400 and id is not None and "message" in response.text:
                if isinstance(response.text, dict):
                    message = response.text["message"]
                else:
                    message = response.text
                error_message = f"Access to this id is denied. {message}"
                raise PermissionError(error_message) from e
            else:
                raise Exception(f"Status Code: {response.status_code}, Response: {response.text}") from e
        try:
            json_response = response.json()
        except (JSONDecodeError, requests.exceptions.JSONDecodeError) as e:
            raise JSONDecodeError(
                f"Error decoding JSON response: {e.msg}\n{response.text}\nFull Response: {response}", e.doc, e.pos
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

    def _post_request(
        self,
        pth: str,
        metadata: Optional[Dict] = None,
        id: Optional[Union[int, str]] = None,
        data: Optional[Dict[str, str]] = None,
        files: Optional[Dict[str, BufferedReader]] = None,
    ):
        """
        Args:
            pth (str): The path appended to the API_URL to which the POST request is sent.
            metadata (dict): The metadata to be sent with the POST request.

        Returns:
            Dict[str, str]: The JSON response from the server, parsed into a dictionary.
        """
        return self._request("post", pth=pth, id=id, json=metadata, data=data, files=files)


class MetadataEditor:
    def __init__(self, api_url: str, api_key: str, allow_http: bool = False, verify_ssl: bool = True):
        """
        MetadataEditor allows you to list, create, update and delete projects, manage collections and list templates in
          a metadata database.

        First obtain an API key.

        Then run

            from pymetadataeditor import MetadataEditor

            api_url = "<url of the API>"
            api_key = "<the api key you generated for accessing the metadata database>"
            me = MetadataEditor(api_url = api_url, api_key = api_key)

        Then you can list and create new projects like so:

            me.list_projects(limit=100)
            dict_of_timeseries = me.outline_metadata("timeseries", "dict")
            <update the timeseries metadata dictionary as needed>
            me.create_project_log("timeseries", dict_of_timeseries)

        Args:
            api_url (str): the URL typically looks like 'https://<name_of_your_metadata_database>.org/index.php/api'
            api_key (str): typically this is created through the web interface of the metadata system
            allow_http (bool): whether to allow calls to the metadata system when the URL begins "http" instead of the
                more secure "https". Defaults to False.
            verify_ssl (bool): Although it is good practice for API requests to verify SSL, some systems do not allow
                this so setting verify_ssl=False may be required. Defaults to True.
        """
        self._apinterface = APInterface(api_url=api_url, api_key=api_key, allow_http=allow_http, verify_ssl=verify_ssl)
        self._ei = ExcelInterface()
        self._metadata_types = {
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

    def count_projects(self) -> int:
        """
        Count the number of projects you have access to

        Returns:
            int: The number of projects
        """
        list_projects_get_path = "/editor"
        params = {"offset": 0, "limit": 1}
        response = self._apinterface._get_request(pth=list_projects_get_path, params=params)
        return response["total"]

    def list_projects(
        self,
        limit: Union[int, str],
        keywords: Optional[Union[str, List[str]]] = None,
        metadata_type: Optional[str] = None,
        offset: int = 0,
        sort_by: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Lists all the projects associated with your API key.

        Args:

            limit (int or str): Page size e.g. 10 to show 10 records. If limit='All' then all records are retrieved.
            keywords (optional str or list of str): Keywords for filtering projects by title and/or idno.
            metadata_type (optional str): If given, only projects of this type are returned.
            offset (int): Offset for pagination e.g. 10 to skip first 10 records. Default is 0.
            sort_by (optional str): valid values: "title_asc", "title_desc", "updated_asc", "updated_desc".

        Returns:
            pd.DataFrame: Information about the projects
        """
        if isinstance(limit, str):
            assert limit.lower() == "all", f"Expected limit to be 'All' or a positive integer but got '{limit}'"
            new_offset = offset
            new_limit = 500
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
        response = self._apinterface._get_request(pth=list_projects_get_path, params=params)
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

        Returns:
            pd.Series: project information

        Raises:
            Exception: You don't have permission to access this project - often this means the id is incorrect
        """
        #  todo(gblackadder) we could implement a get project by **idno** by using list projects and then filtering
        get_project_template = "/editor/{}"
        response = self._apinterface._get_request(get_project_template, id=id)
        return pd.Series(response["project"])

    def list_resources_by_id(self, id: int) -> pd.DataFrame:
        """
        List documentation (Reports, Questionnaires, Tables, etc.) for a project

        Args:
            id (int): project id

        Returns:
            (pd.DataFrame): resource information including titles, subtitles, authors and file formats
        """
        response = self._apinterface._get_request("resources/{}", id=id)
        if "resources" in response and len(response["resources"]) > 0:
            return pd.DataFrame(response["resources"])
        else:
            return pd.DataFrame(columns=["id", "sid", "dctype", "title", "subtitle", "author", "filename", "dcformat"])

    def create_resource(
        self,
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
        filename: Optional[str] = None,
    ) -> int:
        """
        Log a new resource associated with the project (Reports, Questionnaires, Tables, etc.)

        If filename is provided then the file is uploaded and logged.

        Args:
            project_id (int): The project id the resource is associated with.
            dctype (str): The type of the resource (e.g., 'txt', 'pdf').
            title (str): The title of the resource.
            author (Optional[str]): The author of the resource. Defaults to None.
            dcdate (Optional[str]): The date of the resource. Defaults to None.
            country (Optional[str]): The country associated with the resource. Defaults to None.
            language (Optional[str]): The language of the resource. Defaults to None.
            contributor (Optional[str]): The contributor to the resource. Defaults to None.
            publisher (Optional[str]): The publisher of the resource. Defaults to None.
            rights (Optional[str]): The rights associated with the resource. Defaults to None.
            description (Optional[str]): A brief description of the resource. Defaults to None.
            abstract (Optional[str]): An abstract summarizing the resource. Defaults to None.
            toc (Optional[str]): The table of contents of the resource. Defaults to None.
            filename (Optional[str]): The filename of the resource which will be uploaded. Defaults to None.

        Returns:
            int: The unique identifier of the logged resource.
        """
        data = {
            "dctype": dctype,
            "title": title,
            "author": author,
            "dcdate": dcdate,
            "country": country,
            "language": language,
            "contributor": contributor,
            "publisher": publisher,
            "rights": rights,
            "description": description,
            "abstract": abstract,
            "toc": toc,
        }

        if filename is not None:
            files = {"file": open(filename, "rb")}
        else:
            files = None

        response = self._apinterface._post_request(pth="resources/{}", id=project_id, data=data, files=files)
        return int(response["resource"]["id"])

    def update_resource(
        self,
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
        filename: Optional[str] = None,
    ) -> int:
        """
        Log a new resource associated with the project (Reports, Questionnaires, Tables, etc.)

        If filename is provided then the file is uploaded and logged.

        Args:
            project_id (int): The project id the resource is associated with.
            resource_id (int): The id of the resource.
            dctype (str): The type of the resource (e.g., 'txt', 'pdf').
            title (str): The title of the resource.
            author (Optional[str]): The author of the resource. Defaults to None.
            dcdate (Optional[str]): The date of the resource. Defaults to None.
            country (Optional[str]): The country associated with the resource. Defaults to None.
            language (Optional[str]): The language of the resource. Defaults to None.
            contributor (Optional[str]): The contributor to the resource. Defaults to None.
            publisher (Optional[str]): The publisher of the resource. Defaults to None.
            rights (Optional[str]): The rights associated with the resource. Defaults to None.
            description (Optional[str]): A brief description of the resource. Defaults to None.
            abstract (Optional[str]): An abstract summarizing the resource. Defaults to None.
            toc (Optional[str]): The table of contents of the resource. Defaults to None.
            filename (Optional[str]): The filename of the resource which will be uploaded. Defaults to None.
        """

        data = {
            "dctype": dctype,
            "title": title,
            "author": author,
            "dcdate": dcdate,
            "country": country,
            "language": language,
            "contributor": contributor,
            "publisher": publisher,
            "rights": rights,
            "description": description,
            "abstract": abstract,
            "toc": toc,
        }

        if filename is not None:
            files = {"file": open(filename, "rb")}
        else:
            files = None

        self._apinterface._post_request(pth="resources/{}/" + f"{resource_id}", id=project_id, data=data, files=files)

    @staticmethod
    def _remove_empty_from_dict(old_dict: Dict) -> Dict:
        """Helper function for removing entries from dictionaries that look like:
        [{'name': ''}]
        """
        new_dict = {}
        for k, v in old_dict.items():
            if v is None:
                continue
            if isinstance(v, str):
                if v != "":
                    new_dict[k] = v
            elif isinstance(v, dict):
                new_sub_dict = MetadataEditor._remove_empty_from_dict(v)
                if len(new_sub_dict) > 0:
                    new_dict[k] = new_sub_dict
            elif isinstance(v, list):
                new_list = []
                for elem in v:
                    if elem is None:
                        continue
                    if isinstance(elem, dict):
                        new_elem = MetadataEditor._remove_empty_from_dict(elem)
                        if len(new_elem) > 0:
                            new_list.append(new_elem)
                    elif isinstance(elem, str):
                        if elem != "":
                            new_list.append(elem)
                    else:
                        new_list.append(elem)
                if len(new_list) > 0:
                    new_dict[k] = new_list
            else:
                new_dict[k] = v
        return new_dict

    def get_project_metadata_by_id(
        self,
        id: int,
        mode: str,
        exclude_unset: bool = True,
        filename: Optional[str] = None,
        title: Optional[str] = None,
    ) -> Union[Dict, BaseModel, str]:
        """
        Args:
            id (int): the id of the project, not to be confused with the idno.
            mode (str): The type of output. Must be 'dict', 'pydantic' or 'excel'.
            exclude_unset (bool): If mode=='dict', then if exclude_unset=True, only elements that were explicitly set
                with non-null, non-empty values are returned in the dictionary.
            filename (Optional[str]): If mode=='excel' then this is the path to the Excel file.
                If None and mode=='excel', defaults to {metadata_type}_metadata.xlsx
            title (Optional[str]): If mode=='excel' then the title for the Excel sheet.
                If None and mode=='excel', defaults to '{metadata_type} Metadata'

        Returns:
            Union[Dict, BaseModel, str]:
                If mode == 'dict', a dictionary is returned.
                If mode == 'pydantic', a pydantic model object is returned.
                If mode=='excel' then the metadata was saved to a file and the filename is returned.
        """
        mode = mode.lower()
        assert mode in [
            "excel",
            "dict",
            "dictionary",
            "pydantic",
            "model",
            "basemodel",
            "object",
        ], f"mode should be 'excel', 'dict' or 'pydantic' but found '{mode}'"
        project = self.get_project_by_id(id=id)
        metadata_type = project["type"].replace("-", "_")
        if (metadata_type not in self._metadata_types or metadata_type == "geospatial") and mode in [
            "dict",
            "dictionary",
        ]:
            # if the method is unknown then we can still return a dict since we retrieved something
            return project["metadata"]
        assert metadata_type in self._metadata_types, (
            f"this project is listed as a '{metadata_type}' type project but this is"
            f" not supported. Try using mode='dict' to view the metadata in raw form."
        )

        metadata_object = self._ei.inflate_read_data_to_schema(
            metadata_type=metadata_type, read_object=project["metadata"]
        )
        # metadata_object = self._metadata_types[metadata_type](**project["metadata"])
        if mode in ["pydantic", "model", "basemodel", "object"]:
            return metadata_object
        elif mode in ["dict", "dictionary"]:
            if not exclude_unset:
                return metadata_object.model_dump(mode="json")
            else:
                metadata_dict = metadata_object.model_dump(
                    mode="json", exclude_none=exclude_unset, exclude_unset=exclude_unset
                )
                return self._remove_empty_from_dict(metadata_dict)
        else:
            return self._ei.save_metadata_to_excel(
                metadata_type, object=metadata_object, filename=filename, title=title
            )

    def delete_project_by_id(self, id: int):
        """
        If the project exists then delete it and check it was deleted.

        Args:
            id (int): the id of the project, not to be confused with the idno.

        Raises:
            DeleteNotAppliedError: This can be the result of system admins blocking data deletion
        """
        pth = "editor/delete/{}"
        self._delete_by_id(pth=pth, id=id, checker_fn=self.get_project_by_id)

    def delete_collection_by_id(self, id: int):
        """
        If the collection exists then deletes it and check it was deleted.

        Args:
            id (int): the id of the colection.

        Raises:
            DeleteNotAppliedError: This can be the result of system admins blocking data deletion
        """
        pth = "collections/delete/{}"
        self._delete_by_id(pth=pth, id=id, checker_fn=self.get_collection_by_id)

    def delete_resource_by_id(self, project_id, resource_id):
        """
        If the resource exists then deletes it and check it was deleted.

        Args:
            project_id (int): The project id the resource is associated with.
            resource_id (int): The id of the resource.

        Raises:
            DeleteNotAppliedError: This can be the result of system admins blocking data deletion
        """

        def check_exists(resource_id):
            resource_ids = self.list_resources_by_id(project_id)["id"].apply(int).values
            if resource_id not in resource_ids:
                raise IndexError(f"{resource_id} not in list of resources for project id {project_id}")

        pth = f"resources/delete/{project_id}/" + "{}"
        self._delete_by_id(pth, resource_id, checker_fn=check_exists)

    def _delete_by_id(self, pth: str, id: Union[int, str], checker_fn: Callable[[int], pd.Series]):
        """
        Internal, generic method for deleting either collections or projects or similar.
        """
        # # first check that the project/collection is there to be deleted
        # checker_fn(id)
        try:
            self._apinterface._post_request(pth=pth, id=id)
        except JSONDecodeError:
            pass

        # check that the entity was deleted
        try:
            checker_fn(id)
        except (PermissionError, JSONDecodeError, IndexError):
            pass  # evidently the entity was deleted because now it can't be found
        else:
            raise DeleteNotAppliedError()

    def outline_metadata(
        self, metadata_type: str, mode: str, filename: Optional[str] = None, title: Optional[str] = None
    ) -> Union[Dict, BaseModel, Path]:
        """
        Creates a skeleton outline of a given metadata type. Since the metadata can be quite complex, this function
        creates all the possible fields and their subfields.

        Args:
            metadata_type (str):
                The name of a supported metadata type, currently:
                    document, script, series, survey, table, timeseries, timeseries_DB, video
                Currently not supported:
                    geospatial, image
            mode (str): The type of output. Must be 'dict', 'pydantic' or 'excel'.
            filename (Optional[str]): If mode=='excel', the path to the Excel file.
                If None, defaults to {metadata_type}_metadata.xlsx
            title (Optional[str]): If mode=='excel', the title for the Excel sheet.
                If None, defaults to '{metadata_type} Metadata'

        Returns:
            Union[Dict, BaseModel, str]:
                If mode == 'dict', a dictionary is returned.
                If mode == 'pydantic', a pydantic model object is returned.
                If mode=='excel' then the metadata was saved to a file and the filename is returned.

        Examples:

            me = MetadataEditor(api_url=..., api_key=...)

            timeseries_dict = me.outline_metadata("timeseries", "dict")
            timeseries_dict['metadata_information']['idno'] = "my_idno"

            timeseries_pydantic = me.outline_metadata("timeseries", "pydantic")
            timeseries_pydantic.metadata_information.idno = "my_idno"

            path_to_timeseries_excel_file = me.outline_metadata("timeseries", "excel")
        """
        assert metadata_type in self._metadata_types, (
            f"this project is listed as a '{metadata_type}' type project but this is"
            f" unknown. Projects must be one of {list(self._metadata_types.keys())}"
        )
        mode = mode.lower()
        assert mode in [
            "excel",
            "dict",
            "dictionary",
            "pydantic",
            "model",
            "basemodel",
            "object",
        ], f"mode should be 'excel', 'dict' or 'pydantic' but found '{mode}'"
        if mode == "excel":
            return self._ei.write_outline_metadata_to_excel(metadata_type, filename=filename, title=title)
        else:
            pydantic_object = self._ei.type_to_outline(metadata_type)
            if mode in ["pydantic", "model", "basemodel", "object"]:
                return pydantic_object
            else:
                return pydantic_object.model_dump(mode="json")

    def print_metadata(self, metadata: Union[Dict, BaseModel, str], metadata_type: Optional[str] = None):
        """
        Helper function to nicely print the metedata.

        Args:
            metadata (dictionary or BaseModel or str):
                If str, it's assumed this is a path to an appropriately formatted Excel file
            metadata_type (optional str):
                If the metadata is passed as an Excel file then the type of metadata it contains must be given.
                Excel supported metadata types are:
                    document, script, series, survey, table, timeseries, timeseries_DB, video
                Currently not supported for Excel:
                    geospatial, image
        """
        if isinstance(metadata, str):
            assert metadata_type in self._metadata_types, (
                f"this project is listed as a '{metadata_type}' type project but this is"
                f" unknown. Projects must be one of {list(self._metadata_types.keys())}"
            )
            metadata = self._ei.read_metadata_excel(metadata_type, metadata)
            metadata = metadata.model_dump(mode="json")
        elif isinstance(metadata, BaseModel):
            metadata = metadata.model_dump(mode="json")
        print(json.dumps(metadata, indent="  "))

    def create_project_log(self, metadata_type: str, metadata: Union[Dict, BaseModel, str]):
        """
        Validates and logs metadata which can be a dictionary, a pydantic model or a path to an Excel spreadsheet.

        Args:
            metadata_type (str):
                the name of a supported metadata type, currently:
                    document, script, series, survey, table, timeseries, timeseries_DB, video
                Currently not supported:
                    image
                Note that geospatial is supported when the metadata is a dict or pydantic model, but not as Excel file.
            metadata (dictionary or BaseModel or str):
                If str, it's assumed this is a path to an appropriately formatted Excel file

        Returns:
            int: The ID of the newly created document metadata

        Raises:
            NotImplementedError:
                geospatial and image metadata types are currently not supported in Excel mode, use dictionaries or
                    pydantic models instead.

        """
        assert metadata_type in self._metadata_types, (
            f"this project is listed as a '{metadata_type}' type project but this is"
            f" unknown. Projects must be one of {list(self._metadata_types.keys())}"
        )

        if isinstance(metadata, str):
            metadata = self._ei.read_metadata_excel(metadata_type, metadata)

        self._metadata_types[metadata_type].model_validate(metadata, strict=True)
        # validate_metadata(metadata, self._metadata_types[metadata_type])
        md = self._metadata_types[metadata_type](**metadata)

        post_request_pth = f"/editor/create/{metadata_type.replace('_', '-')}"
        ret = self._apinterface._post_request(
            pth=post_request_pth, metadata=md.model_dump(mode="json", exclude_none=True, exclude_unset=True)
        )
        return ret["id"]

    def update_project_log_by_id(self, id: int, new_metadata: Union[Dict, BaseModel, str]):
        """
        Updates the record of the metadata. If a dictionary is passed that only contains a subset of the possible keys
            then the remaining values not mentioned are left as is.

        Args:
            id (int):
                The ID of the metadata to update.
            new_metadata (dictionary, BaseModel or str):
                If str, it's assumed this is a path to an appropriately formatted Excel file
        """
        # (todo) figure out the best way to allow users to replace all or only some of the metadata and also to delete
        # existing metadata without replacing it with new specific values
        project_data = self.get_project_by_id(id)
        metadata_type = project_data["type"].replace("-", "_")
        assert metadata_type in self._metadata_types, (
            f"this project is listed as a '{metadata_type}' type project but this is"
            f" unknown. Projects must be one of {list(self._metadata_types.keys())}"
        )
        if metadata_type == "geospatial":
            assert isinstance(new_metadata, dict), "geospatial data not yet supported in pydantic or excel modes"
            md = new_metadata
        else:
            md = self.get_project_metadata_by_id(id, mode="pydantic")

            if isinstance(new_metadata, str):
                new_metadata = self._ei.read_metadata_excel(new_metadata)
                new_metadata = new_metadata.model_dump(mode="json")
            elif isinstance(new_metadata, BaseModel):
                new_metadata = new_metadata.model_dump(mode="json")

            new_metadata = standardize_keys_in_dict(new_metadata)
            md = md.model_copy(update=new_metadata)
            md = md.model_dump(mode="json", exclude_none=True, exclude_unset=True)

        post_request_template_path = f"/editor/update/{metadata_type.replace('_', '-')}/" + "{}"
        self._apinterface._post_request(
            post_request_template_path,
            id=id,
            metadata=md,
        )

    def list_collections(self) -> pd.DataFrame:
        """
        Lists all the collections associated with your API key.

        Returns:
            pd.DataFrame: Collection information
        """
        response = self._apinterface._get_request("collections")
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
        collection_data = self._apinterface._get_request("collections/{}", id=id)
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
        ret = self._apinterface._post_request("collections", metadata={"title": title, "description": description})
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
        self._apinterface._post_request("collections/update/{}", id=id, metadata=metadata)

    def count_projects_in_collection(self, collection: int) -> int:
        """
        Count the number of projects you have access to

        Args:
            collection (int):
                The id of the collection.

        Returns:
            int: The number of projects
        """
        params = {"offset": 0, "limit": 1}
        response = self._apinterface._get_request("editor?collection={}", id=collection, params=params)
        return response["total"]

    def list_projects_in_collection(
        self,
        collection: int,
        limit: Union[int, str],
        keywords: Optional[Union[str, List[str]]] = None,
        offset: int = 0,
        sort_by: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Retrieve projects that have been added to the given collection.

        Args:

            collection (int):
                The id of the collection.
            limit (int):
                The maximum number of projects to return. If limit='All' then all records are retrieved.
            keyword (optional str):
                filter projects based on whether the project title or idno contains this keyword
            offset (int):
                Offset for pagination e.g. 10 to skip first 10 records. Default is 0.
            sort_by (optional str):
                valid values: "title_asc", "title_desc", "updated_asc", "updated_desc".

        Returns:

            pd.DataFrame:
                Information on the projects in the collection, such as id, idno, title and type.
        """

        if isinstance(limit, str):
            assert limit.lower() == "all", f"Expected limit to be 'all' or a positive integer but got '{limit}'"
            new_offset = offset
            new_limit = 500
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
        ret = self._apinterface._get_request("editor?collection={}", id=collection, params=params)
        # if ret["total"] > ret["limit"]:
        #     warnings.warn(
        #         f"There are {ret['total']} projects in this collection but a limit of {ret['limit']} were retreived",
        #         UserWarning,
        #     )
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
        self._apinterface._post_request(
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

        self._apinterface._post_request(
            "collections/remove_projects",
            metadata={"collections": collection, "id_format": id_format, "projects": projects},
        )

    def list_templates(self) -> pd.DataFrame:
        """
        Retrieves templates, both standard and any custom templates

        Returns:
            pd.DataFrame: A DataFrame containing the templates. If none are found, an empty DataFrame is returned.
        """
        response = self._apinterface._get_request("templates")
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
        response = self._apinterface._get_request("templates/{}", uid)
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
        self._apinterface._post_request(
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
