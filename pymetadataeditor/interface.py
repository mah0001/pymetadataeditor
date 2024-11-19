import json
import warnings
from io import BufferedReader
from json import JSONDecodeError
from pathlib import Path
from ssl import SSLError as ssl_SSLError
from typing import Any, Callable, Dict, Iterable, List, Optional, Type, Union

import pandas as pd
import requests
from metadataschemas.metadata_manager import MetadataManager
from metadataschemas.utils.quick_start import make_skeleton
from metadataschemas.utils.utils import merge_dicts, standardize_keys_in_dict
from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, SecretStr, model_validator
from requests.exceptions import HTTPError, SSLError
from urllib3.exceptions import InsecureRequestWarning

from pymetadataeditor.templates import pydantic_from_template

from .utils import remove_empty_from_dict, validate_json_patches

__all__ = ["MetadataEditor", "DeleteNotAppliedError"]

warnings.filterwarnings(
    "ignore", category=UserWarning, module="pydantic"
)  # suppresses warning when metadata passed as dict instead of a pydantic object

# Create a flag for tracking if the warning was shown
shown_insecure_warning = False


# Define a custom function to display warnings only once
def custom_showwarning(message, category, filename, lineno, file=None, line=None):
    global shown_insecure_warning
    if category is InsecureRequestWarning and not shown_insecure_warning:
        # Show the warning and set the flag
        warnings._showwarnmsg_impl(warnings.WarningMessage(message, category, filename, lineno, file, line))
        shown_insecure_warning = True


# Set the warnings to always trigger, but filter them through custom_showwarning
warnings.simplefilter("always", InsecureRequestWarning)
warnings.showwarning = custom_showwarning


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
            elif response.status_code == 400 and "message" in response.text:
                if isinstance(response.text, dict):
                    error_message = response.text["message"]
                else:
                    error_message = response.text
                raise PermissionError(error_message) from e
            else:
                raise HTTPError(f"Status Code: {response.status_code}, Response: {response.text}") from e
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
        json: Optional[Dict] = None,
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
        return self._request("post", pth=pth, id=id, json=json, data=data, files=files)


class MetadataEditor:
    def __init__(self, api_url: str, api_key: str, allow_http: bool = False, verify_ssl: bool = True):
        """
        MetadataEditor allows you to list, create, update and delete projects, manage collections and list templates in
          a metadata database.

        First obtain an API key and pase it into a file called '.env' in the root of your project. The contents of the
            file should look like this:

            METADATA_API_URL=https://<name_of_your_metadata_database>.org/index.php/api
            METADATA_API_KEY=your_api_key

        Then in python run

            from pymetadataeditor import MetadataEditor
            import os

            api_url = os.getenv("METADATA_API_URL")
            api_key = os.getenv("METADATA_API_KEY")
            me = MetadataEditor(api_url = api_url, api_key = api_key)

        Then you can list and create new projects like so:

            me.list_projects(limit=100)
            dict_of_indicator = me.outline_metadata("indicator", "dict")
            <update the indicator metadata dictionary as needed>
            me.create_project_log("indicator", dict_of_indicator)

        Args:
            api_url (str): the URL typically looks like 'https://<name_of_your_metadata_database>.org/index.php/api'
            api_key (str): typically this is created through the web interface of the metadata system
            allow_http (bool): whether to allow calls to the metadata system when the URL begins "http" instead of the
                more secure "https". Defaults to False.
            verify_ssl (bool): Although it is good practice for API requests to verify SSL, some systems do not allow
                this so setting verify_ssl=False may be required. Defaults to True.
        """
        self._apinterface = APInterface(api_url=api_url, api_key=api_key, allow_http=allow_http, verify_ssl=verify_ssl)
        self._mm = MetadataManager()
        self._templates = {}
        self._default_templates = None
        self._template_class_to_metadata_type = {}

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
            metadata_type = self._mm.standardize_metadata_name(metadata_type)
            params["type"] = metadata_type
        if sort_by is not None:
            sort_by = sort_by.lower()
            valid_sort_by = ["title_asc", "title_desc", "updated_asc", "updated_desc"]
            assert sort_by in valid_sort_by, f"{sort_by} not valid, must be one of {valid_sort_by}"
            params["sort_by"] = sort_by
        response = self._apinterface._get_request(pth=list_projects_get_path, params=params)
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

    def get_resources_by_id(self, id: int) -> pd.DataFrame:
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

    def log_resource(
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
        Log a new resource associated with a project (Reports, Questionnaires, Tables, etc.)

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
        Update the log of resource associated with a project (Reports, Questionnaires, Tables, etc.)

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

    def simplify_metadata(self, metadata: Union[Dict, BaseModel, str], template_uid: Optional[str] = None) -> Dict:
        """
        Returns a dictionary of only the elements that have values, exluding Nones, empty strings,
          empty lists and empty dictionaries.

        Args:
            metadata (dictionary or BaseModel or str):
                Can be a dictionary, a pydantic object or a string. If string, it's assumed this is a path to an
                appropriately formatted Excel file.

            template_uid (Optional str):
                If you are reading metadata from an excel file *and* if that metadata is from a template then you must
                pass in the UID of that template. Otherwise this can be ignored.

        Returns:
            (dict): a metadata dictionary of set elements.
        """
        if isinstance(metadata, str):
            if template_uid is not None and template_uid != "":
                metadata_class = self.get_metadata_class(template_uid)
            else:
                metadata_class = None
            metadata = self._mm.read_metadata_from_excel(metadata, metadata_class)
        if isinstance(metadata, BaseModel):
            metadata = metadata.model_dump(mode="json", exclude_defaults=False, exclude_none=True, exclude_unset=False)
        return remove_empty_from_dict(metadata)

    def get_project_metadata_by_id(
        self,
        id: int,
        mode: str,
        exclude_unset: bool = True,
        filename: Optional[str] = None,
        title: Optional[str] = None,
        debug: bool = False,
    ) -> Union[Dict, BaseModel, str]:
        """
        Args:
            id (int): the id of the project, not to be confused with the idno.
            mode (str): The type of output. Must be 'dict', 'pydantic' or 'excel'.
            exclude_unset (bool): If mode=='dict', then if exclude_unset=True, only elements that were explicitly set
                with non-null, non-empty values are returned in the dictionary.
            filename (Optional[str]): If mode=='excel' then this is the path to the Excel file.
                If None and mode=='excel', defaults to {name of metadata type}_metadata.xlsx
            title (Optional[str]): If mode=='excel' then the title for the Excel sheet.
                If None and mode=='excel', defaults to '{name of metadata type} Metadata'

        Returns:
            Union[Dict, BaseModel, str]:
                If mode == 'dict', a dictionary is returned.
                If mode == 'pydantic', a pydantic model object is returned.
                If mode == 'excel' then the metadata was saved to a file and the filename is returned.
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
        try:
            metadata_name = self._mm.standardize_metadata_name(project["type"])
        except ValueError as e:
            # unknown metadata type can still be returned as a dict
            if mode not in [
                "dict",
                "dictionary",
            ]:
                raise ValueError(
                    f"Unknown metadata type {project['type']}. Use mode='dict' to view the metadata in raw form."
                ) from e
            else:
                return project["metadata"]
        if "template_uid" in project and project.template_uid is not None and project.template_uid != "":
            metadata_name = project.template_uid
        skeleton_object = self.make_metadata_outline(metadata_name, mode="dict")
        if debug:
            print(f"\nproject_metadata = {project['metadata']}\n")
        combined_dict = merge_dicts(
            skeleton_object,
            project["metadata"],
            skeleton_mode=True,
        )
        combined_dict = standardize_keys_in_dict(combined_dict)
        if debug:
            print(f"combined_dict = {combined_dict}\n")
        schema = self.get_metadata_class(metadata_type_or_template_uid=metadata_name)
        metadata_object = schema.model_validate(standardize_keys_in_dict(combined_dict))

        if mode in ["pydantic", "model", "basemodel", "object"]:
            return metadata_object
        elif mode in ["dict", "dictionary"]:
            metadata_dict = metadata_object.model_dump(
                mode="json", exclude_none=exclude_unset, exclude_unset=exclude_unset
            )
            if exclude_unset:
                return remove_empty_from_dict(metadata_dict)
            else:
                return metadata_dict
        else:
            return self._mm.save_metadata_to_excel(
                object=metadata_object,
                filename=filename,
                title=title,
                parent_metadata_name=self._template_class_to_metadata_type.get(schema, None),
            )

    def save_metadata_to_excel(
        self,
        object: BaseModel,
        filename: Optional[str] = None,
        title: Optional[str] = None,
        verbose: bool = False,
    ) -> str:
        """
        Save a metadata object to an Excel file.

        Args:
            object (BaseModel): The pydantic object to save to the Excel file.
            filename (Optional[str]): The path to the Excel file. Defaults to {name}_metadata.xlsx
            title (Optional[str]): The title for the Excel sheet. Defaults to '{name} Metadata'
            verbose (bool): If True, print debug information on the file creation.

        Returns:
            str: The path to the saved Excel file.
        """
        # parent_metadata_name = self._template_class_to_metadata_type.get(object.__class__, None)
        parent_metadata_name = self._template_class_to_metadata_type.get(type(object), None)
        return self._mm.save_metadata_to_excel(object, filename, title, parent_metadata_name, verbose)

    def read_metadata_from_excel(
        self,
        filename: str,
        metadata_class: Optional[Type[BaseModel]] = None,
        mode: str = "pydantic",
        exclude_unset=True,
    ) -> Union[BaseModel, Dict]:
        """
        Read metadata from an Excel file.

        Args:
            filename (str): The path to the Excel file.
            metadata_class (Optional[Type[BaseModel]]): The pydantic class of the metadata. Required if the metadata is
                of a template type.
            mode (str): The output mode. Must be 'pydantic' or 'dict'.
            exclude_unset (bool): If mode=='dict', then if exclude_unset=True, only elements that were explicitly set
                with non-null, non-empty values are returned in the dictionary.

        Returns:
            Union[BaseModel, Dict]: The metadata object or dictionary.
        """
        parent_name = self._template_class_to_metadata_type.get(
            metadata_class, self._template_class_to_metadata_type.get(type(metadata_class), None)
        )
        assert parent_name is not None, "metadata_class must be a pydantic class or a string"
        object = self._mm.read_metadata_from_excel(filename, metadata_class, parent_name, verbose=False)

        if mode == "pydantic" or mode == "model" or mode == "basemodel" or mode == "object":
            return object
        elif mode == "dict" or mode == "dictionary":
            return remove_empty_from_dict(
                object.model_dump(mode="json", exclude_none=exclude_unset, exclude_unset=exclude_unset)
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
            resource_ids = self.get_resources_by_id(project_id)["id"].apply(int).values
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
        except (PermissionError, JSONDecodeError, IndexError, HTTPError):
            pass  # evidently the entity was deleted because now it can't be found
        else:
            raise DeleteNotAppliedError()

    def _get_template_class(self, template_uid: str) -> Type[BaseModel]:
        if template_uid in self._templates:
            return self._templates[template_uid]["class"]
        try:
            temp = self.get_template_by_uid(template_uid)
        except (KeyError, PermissionError):
            # not a template either
            raise ValueError(f"{template_uid} is not a known metadata type nor a known template uid")
        else:
            metadata_type = temp.data_type
            parent_schema = self._mm.metadata_class_from_name(metadata_type)
            klass = pydantic_from_template(temp.template, parent_schema=parent_schema, name=temp.name)
            self._templates[template_uid] = {
                "template": temp,
                "metadata_type": metadata_type,
                "class": klass,
            }
            self._template_class_to_metadata_type[klass] = metadata_type
            return klass

    def get_metadata_class(self, metadata_type_or_template_uid: str) -> Type[BaseModel]:
        try:
            metadata_type = self._mm.standardize_metadata_name(metadata_type_or_template_uid)
        except ValueError:
            # assume must be template
            return self._get_template_class(metadata_type_or_template_uid)
        else:
            # check if there is a default template:
            if self._default_templates is None:
                _ = self.list_templates()

            if (
                self._default_templates is not None
                and metadata_type in self._default_templates.data_type.values
                and self._default_templates[self._default_templates.data_type == metadata_type].iloc[0].uid != ""
            ):
                return self._get_template_class(
                    self._default_templates[self._default_templates.data_type == metadata_type].iloc[0].uid
                )
            else:
                return self._mm.metadata_class_from_name(metadata_type)

    def make_metadata_outline(
        self, metadata_type_or_template_uid: str, mode: str, filename: Optional[str] = None, title: Optional[str] = None
    ) -> Union[Dict, BaseModel, Path]:
        """
        Creates a skeleton outline of a given metadata type. Since the metadata can be quite complex, this function
        creates all the possible fields and their subfields.

        Args:
            metadata_type_or_template_uid (str):
                The type of a supported metadata type, currently:
                    document, geospatial, image, indicator, indicators_db, microdata, resource, script, table, video
                If passed as a template UID then this template is retreived and an outline created.
            mode (str): The type of output. Must be 'dict', 'pydantic' or 'excel'.
            filename (Optional[str]): If mode=='excel', the path to the Excel file.
                If None, defaults to {name of metadata type}_metadata.xlsx
            title (Optional[str]): If mode=='excel', the title for the Excel sheet.
                If None, defaults to '{name of metadata type} Metadata'

        Returns:
            Union[Dict, BaseModel, str]:
                If mode == 'dict', a dictionary is returned.
                If mode == 'pydantic', a pydantic model object is returned.
                If mode=='excel' then the metadata was saved to a file and the filename is returned.

        Examples:

            me = MetadataEditor(api_url=..., api_key=...)

            indicator_dict = me.outline_metadata("indicator", "dict")
            indicator_dict['metadata_information']['idno'] = "my_idno"

            indicator_pydantic = me.outline_metadata("indicator", "pydantic")
            indicator_pydantic.metadata_information.idno = "my_idno"

            path_to_indicator_excel_file = me.outline_metadata("indicator", "excel")
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
        metadata_class = self.get_metadata_class(metadata_type_or_template_uid)
        if mode == "excel":
            return self._mm.write_metadata_outline_to_excel(metadata_class, filename=filename, title=title)
        else:
            metadata_object = make_skeleton(metadata_class, debug=False)
            if mode in ["pydantic", "model", "basemodel", "object"]:
                return metadata_object
            else:
                return metadata_object.model_dump(mode="json")

    def print_metadata(
        self, metadata: Union[Dict, BaseModel, str], template_uid: Optional[str] = None, simplify: bool = False
    ):
        """
        Helper function to nicely print the metadata.

        Args:
            metadata (dictionary or BaseModel or str):
                If str, it's assumed this is a path to an appropriately formatted Excel file

            template_uid (Optional str):
                If you are reading metadata from an excel file *and* if that metadata is from a non default template
                  then you must pass in the UID of that template. Otherwise this can be ignored.

            simplify (bool):
                If True, the metadata will be simplified to exclude Nones, empty strings, empty lists, and
                  empty dictionaries.
        """
        if simplify:
            metadata = self.simplify_metadata(metadata, template_uid)
        elif isinstance(metadata, str):
            if template_uid is not None and template_uid != "":
                metadata_class = self.get_metadata_class(template_uid)
            else:
                metadata_class = None
            metadata = self._mm.read_metadata_from_excel(metadata, metadata_class)
            metadata = metadata.model_dump(mode="json")
        elif isinstance(metadata, BaseModel):
            metadata = metadata.model_dump(mode="json")
        print(json.dumps(metadata, indent="  "))

    def create_project_log(self, metadata_type_or_template_uid: str, metadata: Union[Dict, BaseModel, str]) -> int:
        """
        Validates and logs metadata which can be a dictionary, a pydantic model or a path to an Excel spreadsheet.

        Args:
            metadata_type_or_template_uid (str):
                if passing in a simple type then the supported metadata types are currently:
                    document, geospatial, image, indicator, indicators_db, microdata, resource, script, table, video
                Alternatively you can pass in the UID of a template.
            metadata (dictionary or BaseModel or str):
                If str, it's assumed this is a path to an appropriately formatted Excel file

        Returns:
            int: The ID of the newly created document metadata

        Raises:
            NotImplementedError:
                geospatial and image metadata types are currently not supported in Excel mode, use dictionaries or
                    pydantic models instead.

        """
        metadata_class = self.get_metadata_class(metadata_type_or_template_uid)
        try:
            metadata_type = self._mm.standardize_metadata_name(metadata_type_or_template_uid)
        except ValueError:
            if metadata_type_or_template_uid in self._templates:
                metadata_type = self._templates[metadata_type_or_template_uid]["metadata_type"]
            else:
                raise ValueError(f"Retreived metadata class but it was not in cache = {self._templates}")

        if isinstance(metadata, str):
            metadata = self._mm.read_metadata_from_excel(metadata, metadata_class)
        metadata_class.model_validate(metadata, strict=True)
        if isinstance(metadata, dict):
            metadata = metadata_class(**metadata)

        if metadata_type == "indicator":
            metadata_type = "timeseries"
        elif metadata_type == "indicators_db":
            metadata_type = "timeseries_db"
        elif metadata_type == "microdata":
            metadata_type = "survey"
        post_request_pth = f"/editor/create/{metadata_type.replace('_', '-')}"
        # ret = self._apinterface._post_request(
        #     pth=post_request_pth, json=metadata.model_dump(mode="json", exclude_none=False, exclude_unset=False)
        # )
        ret = self._apinterface._post_request(
            pth=post_request_pth,
            json=remove_empty_from_dict(metadata.model_dump(mode="json", exclude_none=True, exclude_unset=True)),
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
        project_data = self.get_project_by_id(id)
        metadata_type = self._mm.standardize_metadata_name(project_data["type"])
        if (
            "template_uid" in project_data
            and project_data["template_uid"] is not None
            and project_data["template_uid"] != ""
        ):
            metadata_class = self.get_metadata_class(project_data["template_uid"])
        else:
            metadata_class = self.get_metadata_class(metadata_type)

        md = self.get_project_metadata_by_id(id, mode="pydantic")

        if isinstance(new_metadata, str):
            new_metadata = self._mm.read_metadata_from_excel(new_metadata, metadata_class)
            new_metadata = new_metadata.model_dump(mode="json")
        elif isinstance(new_metadata, BaseModel):
            new_metadata = new_metadata.model_dump(mode="json")

        new_metadata = standardize_keys_in_dict(new_metadata)
        md = md.model_copy(update=new_metadata)
        md = merge_dicts(md.model_dump(mode="json", exclude_none=True, exclude_unset=True), new_metadata)

        md = metadata_class.model_validate(md)
        md = remove_empty_from_dict(md.model_dump(mode="json", exclude_none=True, exclude_unset=True))

        if metadata_type == "indicator":
            metadata_type = "timeseries"
        elif metadata_type == "indicators_db":
            metadata_type = "timeseries_db"
        elif metadata_type == "microdata":
            metadata_type = "survey"
        post_request_template_path = f"/editor/update/{metadata_type.replace('_', '-')}/" + "{}"
        self._apinterface._post_request(
            post_request_template_path,
            id=id,
            json=md,
        )

    def patch_update_project_log_by_id(self, id: int, op: str, path: str, value: Optional[str] = None):
        """
        Add, update, or remove parts of a project's metadata using a single JSON Patch operation.

        "JSON Patch is a format for describing changes to a JSON document. It can be used to avoid sending a whole
        document when only a part has changed." - https://jsonpatch.com/ accessed 2024-08-20

        This method applies a single JSON Patch operation to update the metadata of a project specified by its ID.

        Args:
            id (int): The unique identifier of the project whose metadata is to be updated.
            op (str): The JSON Patch operation to be applied. Valid operations are "add", "remove",
                "replace", and "test".
            path (str): The path in the project's metadata where the operation will be applied, using JSON
                Pointer notation.
            value (Optional[str]): The value to be added, replaced, or tested. Not required for "remove" operations.

        Raises:
            ValueError: If the provided operation, path, or value is invalid.

        JSON Patch Operations:
            - "add": Adds a value to the specified path. If the path already exists, the value is replaced.
            - "remove": Removes the value at the specified path.
            - "replace": Replaces the value at the specified path with a new value.
            - "test": Tests that the value at the specified path matches a given value.

        Path Notation:
            - The `path` is a string that uses a slash (`/`) notation to specify the location within the JSON document.
            For example, `/author` refers to the "author" field, and `/metadata/title` refers to the "title" field
            inside the "metadata" object. If the path does not start with a `/`, the method will automatically
            prepend it.

        Usage:
            ```python
            metadata_editor.patch_update_project_log_by_id(id=123, op="add", path="/author", value="John Doe")
            ```
        """
        project_data = self.get_project_by_id(id)
        metadata_name = project_data["type"]
        pth = f"editor/patch/{metadata_name}/"

        patches = {"op": op, "path": path}
        if value is not None:
            patches["value"] = value
        if isinstance(patches, dict):
            patches = [patches]
        patches = validate_json_patches(patches)  # depend on serverside validation
        self._apinterface._post_request(pth=pth + "{}", id=id, json={"patches": patches, "validate": True})

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
        ret = self._apinterface._post_request("collections", json={"title": title, "description": description})
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
        # Is it clear this updates title/description of the collection and not the data in the collection?
        assert title is not None or description is not None, "can update title or description or both, but not neither"
        metadata = {}
        if title is not None:
            metadata["title"] = title
        if description is not None:
            metadata["description"] = description
        self._apinterface._post_request("collections/update/{}", id=id, json=metadata)

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
            json={"collections": collection, "id_format": id_format, "projects": projects},
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
            json={"collections": collection, "id_format": id_format, "projects": projects},
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
            templates = pd.DataFrame([v_item for _, v in response["templates"].items() for v_item in v])
            if "default" in templates and "uid" in templates and "data_type" in templates:
                self._default_templates = (
                    templates[templates.default].drop_duplicates("uid").drop_duplicates("data_type")
                )

                # in place replace each value of data_type with the standardised version
                def standardize(row):
                    try:
                        return self._mm.standardize_metadata_name(row["data_type"])
                    except ValueError:
                        return row["data_type"]

                self._default_templates["data_type"] = self._default_templates.apply(standardize, axis=1)
            return templates

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
            temp = pd.Series(response["result"], name=response["result"]["name"])
            if uid in self._templates:
                try:
                    metadata_type = temp.data_type
                    parent_schema = self.get_metadata_class(metadata_type)
                    klass = pydantic_from_template(temp.template, parent_schema=parent_schema, name=temp.name)
                    self._templates[uid] = {"template": temp, "metadata_type": metadata_type, "class": klass}
                finally:
                    return temp
            else:
                return temp

    def set_template_for_collection(self, collection_id: int, template_uid: str):
        """
        Set the specified template to be used for all metadata of its type (for example microdata, indicator, or
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
            json={"collection_id": collection_id, "template_uid": template_uid, "project_type": template_type},
        )

    def delete_template(self, uid: str):
        """
        Deletes the given template.

        Args:
            uid (str): The Unique Identifier of the template to delete.

        """
        if uid in self._templates:
            self._templates.pop(uid, None)
        self._delete_by_id("templates/delete/{}", id=uid, checker_fn=self.get_template_by_uid)
