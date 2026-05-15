"""The interface between pyMetadataEditor and the Metadata Editor API."""

import warnings
from io import BufferedReader
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Dict, Iterable, List, Optional, Tuple, Type, Union

import pandas as pd
import tiktoken
from markitdown import MarkItDown
from metadataschemas.metadata_manager import MetadataManager
from metadataschemas.utils.schema_base_model import SchemaBaseModel

# from metadataschemas.utils.quick_start import make_skeleton
from metadataschemas.utils.utils import merge_dicts, standardize_keys_in_dict
from openai import AzureOpenAI, OpenAI
from pydantic import BaseModel, ValidationError
from urllib3.exceptions import InsecureRequestWarning

from pymetadataeditor.llm_helpers import (
    _iterated_validated_update_to_outline,
    _prepend_draft_drop_non_str,
    call_per_field,
    get_date_as_text,
    json_to_markdown,
)
from pymetadataeditor.api_client import ApiClient
from pymetadataeditor.collections import CollectionsClient
from pymetadataeditor.metadata_workflows import MetadataWorkflowsClient
from pymetadataeditor.projects import ProjectsClient
from pymetadataeditor.requester import RequestsWithSpecificErrors
from pymetadataeditor.resources import ResourcesClient
from pymetadataeditor.templates import pydantic_from_template
from pymetadataeditor.templates_client import TemplatesClient

from .constants import DICT_MODES, EXCEL_MODES, PYDANTIC_MODES
from .exceptions import TemplateError
from .utils import remove_empty_from_dict, validate_json_patches

__all__ = ["MetadataEditor", "TemplateError"]

shown_insecure_request_warnings = set()


# Define a custom function to display warnings once only for unique InsecureRequestWarning messages
def custom_showwarning(message, category, filename, lineno, file=None, line=None):
    global shown_insecure_request_warnings
    # Only handle InsecureRequestWarning
    if category is InsecureRequestWarning:
        # Check if this message has already been shown
        warning_key = (str(message), filename, lineno)
        if warning_key not in shown_insecure_request_warnings:
            # Show the warning and add the message to the set
            warnings._showwarnmsg_impl(warnings.WarningMessage(message, category, filename, lineno, file, line))
            shown_insecure_request_warnings.add(warning_key)
    else:
        # Pass other warnings through without suppression
        warnings._showwarnmsg_impl(warnings.WarningMessage(message, category, filename, lineno, file, line))


# Set the warnings to always trigger, but filter them through custom_showwarning
warnings.simplefilter("always", InsecureRequestWarning)
warnings.showwarning = custom_showwarning


class MetadataEditor:
    """pyMetadataEditor helps create and manage metadata in a Metadata Editor database.

    pyMetadataEditor allows you to list, create, update and delete projects, manage collections and list templates in
      a metadata database.

    You can save metadata to an Excel file. Or use OpenAI to draft metadata from files or web pages.

    First obtain an API key and pase it into a file called '.env' in the root of your project. The contents of the
        file should look like this:

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
    me.projects.list(limit=100)
    indicator_metadata = me.make_metadata_outline("indicator", "pydantic")
    # update the indicator metadata as needed.

    # View nicely formatted metadata
    indicator_metadata.pretty_print()

    # Then log the metadata to the database
    me.metadata.create(dict_of_indicator, "indicator")
    ```
    """

    def __init__(self, api_url: str, api_key: str, allow_http: bool = False, verify_ssl: bool = True):
        """Create a new MetadataEditor object connected to an instance of a Metadata Editor database.

        Args:
            api_url (str): the URL typically looks like 'https://<name_of_your_metadata_database>.org/index.php/api'
            api_key (str): typically this is created through the web interface of the metadata system.
            allow_http (bool): whether to allow calls to the metadata system when the URL begins "http" instead of the
                more secure "https". Defaults to False.
            verify_ssl (bool): Although it is good practice for API requests to verify SSL, some systems do not allow
                this so setting verify_ssl=False may be required. Defaults to True.

        Example:
        ```python
        from pymetadataeditor import MetadataEditor
        import os

        api_url = os.getenv("METADATA_API_URL")
        api_key = os.getenv("METADATA_API_KEY")
        me = MetadataEditor(api_url = api_url, api_key = api_key)
        ```
        """
        self._apinterface = RequestsWithSpecificErrors(
            api_url=api_url, api_key=api_key, allow_http=allow_http, verify_ssl=verify_ssl
        )
        self._mm = MetadataManager()
        self._templates = {}
        self._default_templates = None
        self.api = ApiClient(self._apinterface)
        self.projects = ProjectsClient(self._apinterface)
        self.collections = CollectionsClient(self._apinterface)
        self.templates = TemplatesClient(self._apinterface, template_cache=self._templates)
        self.resources = ResourcesClient(self._apinterface)
        self.metadata = MetadataWorkflowsClient(self)

    ####################################################################################################################
    # Generic API requests
    ####################################################################################################################

    def generic_api_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        json: Optional[Dict] = None,
        files: Optional[Dict[str, BufferedReader]] = None,
        id: Optional[Union[int, str]] = None,
    ) -> Dict:
        """Make a generic API request to the Metadata Editor API.

        Prefer sub-clients (`projects`, `collections`, …) or `me.api.get/post/put/delete`.
        This method remains for backward compatibility.

        Args:
            method (str): HTTP verb — GET, POST, PUT, or DELETE.
            endpoint (str): Path relative to the API base URL (may include ``{}`` with ``id``).
            params (optional dict): Query string parameters.
            data (optional dict): Form fields (POST/PUT).
            json (optional dict): JSON body (POST/PUT).
            files (optional dict): Multipart files (POST/PUT).
            id (optional): Value substituted into ``{}`` in ``endpoint``.

        Returns:
            Dict: Parsed JSON response from the API.
        """
        return self.api.request(
            method=method,
            path=endpoint,
            id=id,
            params=params,
            data=data,
            json=json,
            files=files,
        )

    ####################################################################################################################
    # METADATA Input and Output
    ####################################################################################################################

    def _process_metadata_input(
        self, metadata: Union[SchemaBaseModel, Dict, str], metadata_type_or_template_uid: Optional[str] = None
    ) -> Tuple[BaseModel, str, None | str]:
        """Internal function to process metadata input, converting it to a pydantic object if necessary.

        Args:
            metadata (Union[BaseModel, Dict, str]): The metadata to process.
            metadata_type_or_template_uid (Optional[str]): The metadata type or template UID. Required if metadata is a
                dictionary otherwise ignored.

        Returns:
            BaseModel: The metadata object.
            str: The metadata type.
            None | str: The template UID if the metadata is from a template, otherwise None.
        """
        if isinstance(metadata, BaseModel):
            metadata_type, uid = (
                metadata._metadata_type__
                if isinstance(metadata._metadata_type__, str)
                else metadata._metadata_type__.default,
                metadata._template_uid__
                if isinstance(metadata._template_uid__, str)
                else metadata._template_uid__.default
                if hasattr(metadata._template_uid__, "default")
                else None,
            )  # self._lookup_metadata_type_and_uid(metadata)
        elif isinstance(metadata, dict):
            if metadata_type_or_template_uid is None:
                raise ValueError("metadata_type_or_template_uid must be passed when metadata is a dictionary")
            klass, metadata_type, uid = self._get_metadata_class_and_type_and_UID(metadata_type_or_template_uid)
            metadata = klass.model_validate(metadata, strict=False)
        else:
            # if metadata_type_or_template_uid is None:
            metadata_info = self._mm.get_metadata_type_info_from_excel_file(metadata)
            metadata_type = metadata_info["metadata_type"]
            uid = metadata_info.get("template_uid", None)
            if uid is not None:
                klass = self._get_template_class_and_type_and_UID(uid)[0]
            else:
                klass = self._get_metadata_class_and_type_and_UID(metadata_type)[0]
            metadata = self._mm.read_metadata_from_excel(metadata, klass, verbose=False)
        return metadata, metadata_type, uid

    def _process_metadata_output(
        self,
        metadata_object: BaseModel,
        output_mode: str,
        filename: Optional[str] = None,
        title: Optional[str] = None,
        simplify: Optional[bool] = None,
    ) -> Union[BaseModel, Dict, str]:
        """Internal function to output metadata in a given format - dict, pydantic or excel.

        Args:
            metadata_object (BaseModel): The metadata object to output.
            output_mode (str): The output mode. Must be 'dict', 'pydantic' or 'excel'.
            filename (Optional[str]): If output_mode=='excel', the path to the Excel file.
                If None, defaults to {name of metadata type}_metadata.xlsx
            title (Optional[str]): If output_mode=='excel', the title for the Excel sheet.
                If None, defaults to '{name of metadata type} Metadata'
            simplify (Optional[bool]): If output_mode=='dict', then if simplify=True, only elements that were explicitly
                set with non-null, non-empty values are returned in the dictionary. Default behaviour is False

        Returns:
            Union[BaseModel, Dict, str]: The output metadata.
        """
        assert output_mode in DICT_MODES + EXCEL_MODES + PYDANTIC_MODES, (
            f"mode should be 'pydantic', 'dict' or 'excel' but found '{output_mode}'"
        )
        if output_mode in PYDANTIC_MODES:
            return metadata_object
        elif output_mode in DICT_MODES:
            if simplify is None:
                simplify = False
            metadata_dict = metadata_object.model_dump(mode="json", exclude_none=simplify, exclude_unset=simplify)
            if simplify:
                return remove_empty_from_dict(metadata_dict)
            else:
                return metadata_dict
        else:
            metadata_type = (
                metadata_object._metadata_type__
                if isinstance(metadata_object._metadata_type__, str)
                else metadata_object._metadata_type__.default
            )
            # metadata_type, _ = self._lookup_metadata_type_and_uid(metadata_object)
            return self._mm.save_metadata_to_excel(
                metadata_model=metadata_object,
                filename=filename,
                title=title,
                metadata_type=metadata_type,
            )

    ####################################################################################################################
    # Metadata Classes
    ####################################################################################################################

    def _get_template_class_and_type_and_UID(
        self, template_uid: str, apply_template_rules: bool = True
    ) -> Tuple[Type[BaseModel], str, str]:
        """Internal function to return the class of a given template UID, it's type and UID.

        Template rules are requirements on fields such as max_length of a string is 10 characters. We generally want
            such rules if they're specified, but OpenAI strucutured output doesn't allow for such rules so when making
            LLM calls we need to ignore rules.

        Args:
            template_uid (str): The UID of the template.
            apply_template_rules (bool): Whether to apply template rules. Defaults to True.

        Returns:
            Type[BaseModel]: The Pydantic class of the template.
            str: The metadata type, such as 'document', 'geospatial', or 'image'.
            str: The template UID.
        """
        if template_uid in self._templates and "class" in self._templates[template_uid] and apply_template_rules:
            return self._templates[template_uid]["class"], self._templates[template_uid]["metadata_type"], template_uid
        try:
            temp = self._ensure_template_cached(template_uid)
        except (KeyError, PermissionError) as e:
            # not a template either
            raise TemplateError(
                f"{template_uid} is not a known template uid - consider using an alternative template "
                f"from client.templates.list()",
                response=e,
            )
        else:
            metadata_type = self._templates[template_uid]["metadata_type"]
            if "class" not in self._templates[template_uid] or apply_template_rules is False:
                try:
                    parent_schema = self._mm.metadata_class_from_name(metadata_type)
                except ValueError:
                    warnings.warn(
                        f"Could not find a metadata class for template type '{metadata_type}', UID '{template_uid}'. "
                        f"Building a class from the template without a parent schema."
                    )
                    parent_schema = SchemaBaseModel

                klass = pydantic_from_template(
                    temp.template,
                    parent_schema=parent_schema,
                    uid=template_uid,
                    name=temp.name,
                    metadata_type=metadata_type,
                    apply_rules=apply_template_rules,
                )
                if apply_template_rules:
                    self._templates[template_uid]["class"] = klass
            else:
                klass = self._templates[template_uid]["class"]
            return klass, metadata_type, template_uid

    def _get_metadata_class_and_type_and_UID(
        self, metadata_type_or_template_uid: str, apply_template_rules: bool = True
    ) -> Tuple[Type[BaseModel], str, None | str]:
        """Internal function to return the class of a given metadata type or template UID, it's type and UID.

        Template rules are requirements on fields such as max_length of a string is 10 characters. We generally want
            such rules if they're specified, but OpenAI strucutured output doesn't allow for such rules so when making
            LLM calls we need to ignore rules.

        Args:
            metadata_type_or_template_uid (str): The metadata type or template UID.
            apply_template_rules (bool): Whether to apply template rules. Defaults to True.

        Returns:
            Type[BaseModel]: The pydantic class of the metadata.
            str: The metadata type such as 'document', 'geospatial', 'image' etc.
            None | str: The template UID if the metadata is from a template, otherwise None.
        """
        try:
            metadata_type = self._mm.standardize_metadata_name(metadata_type_or_template_uid)
        except ValueError:
            # assume must be template
            return self._get_template_class_and_type_and_UID(
                metadata_type_or_template_uid, apply_template_rules=apply_template_rules
            )
        else:
            if self._default_templates is None:
                self._refresh_default_templates_cache()

            if (
                self._default_templates is not None
                and metadata_type in self._default_templates.data_type.values
                and self._default_templates[self._default_templates.data_type == metadata_type].iloc[0].uid != ""
            ):
                return self._get_template_class_and_type_and_UID(
                    self._default_templates[self._default_templates.data_type == metadata_type].iloc[0].uid,
                    apply_template_rules=apply_template_rules,
                )
            else:
                klass = self._mm.metadata_class_from_name(metadata_type)
                return klass, metadata_type, None

    def get_metadata_class(self, metadata_type_or_template_uid: str) -> Type[BaseModel]:
        """Create a pydantic class of a given metadata type or template UID.

        If a metadata type is passed then the class will be created from the default template of that type.

        Args:
            metadata_type_or_template_uid (str): The metadata type or template UID.

        Returns:
            Type[BaseModel]: The pydantic class of the metadata.

        Examples:
        ```python
        me = MetadataEditor(api_url=..., api_key=...)
        indicator_metadata_class = me.get_metadata_class("indicator")
        specific_metadata_class = me.get_metadata_class("timeseries-system-en")
        ```
        """
        return self._get_metadata_class_and_type_and_UID(
            metadata_type_or_template_uid.strip(), apply_template_rules=True
        )[0]

    def make_metadata_outline(
        self,
        metadata_type_or_template_uid: str,
        output_mode: str,
        filename: Optional[str] = None,
        title: Optional[str] = None,
    ) -> Union[Dict, BaseModel, Path]:
        """Creates a skeleton outline of a given metadata type.

        Since the metadata can be quite complex, it's useful to start with all the possible fields and their subfields.

        Args:
            metadata_type_or_template_uid (str):The type of a supported metadata type, currently:
                    document, geospatial, image, indicator, indicators_db, microdata, resource, script, table, video
                If passed as a template UID then this template is retreived and an outline created.
            output_mode (str): The type of output. Must be 'dict', 'pydantic' or 'excel'.
            filename (Optional[str]): If output_mode=='excel', the path to the Excel file.
                If None, defaults to {name of metadata type}_metadata.xlsx
            title (Optional[str]): If output_mode=='excel', the title for the Excel sheet.
                If None, defaults to '{name of metadata type} Metadata'

        Returns:
            `BaseModel` | `Dict` | `str`: If `output_mode == 'dict'`, a dictionary is returned.
                If `output_mode == 'pydantic'`, a pydantic model object is returned.
                If `output_mode == 'excel'`, the metadata was saved to a file and the filename is returned.

        Examples:
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
        """
        metadata_class = self.get_metadata_class(metadata_type_or_template_uid)
        # metadata_object = make_skeleton(metadata_class, debug=False)
        metadata_object = self._mm.create_metadata_outline(metadata_class)
        return self._process_metadata_output(
            metadata_object=metadata_object,
            output_mode=output_mode,
            filename=filename,
            title=title,
        )

    ####################################################################################################################
    # Automatic Metadata Creation
    ####################################################################################################################

    def draft_metadata_from_files(
        self,
        llm_api_key: str,
        files: List[str] | str,
        output_mode: str,
        metadata_type_or_template_uid: str,
        metadata_producer_organization: Optional[str] = None,
        # prefix: Optional[str] = "?",
        filename: Optional[str] = None,
        title: Optional[str] = None,
        llm_model_name="gpt-4o",
        tokenizer_model="o200k_base",
        max_tokens=128_000,
        llm_base_url: Optional[str] = None,
        azure_deployment_name: Optional[str] = None,
    ) -> Union[BaseModel, Dict, str]:
        """Automatically generate *draft* metadata for a project based on local files or web pages.

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

        Args:
            llm_api_key (str): The API key for the LLM API.
            files (List[str] | str): The path to the file or a list of paths to the files from which to base metadata.
            output_mode (str): The type of output. Must be 'dict', 'pydantic' or 'excel'.
            metadata_type_or_template_uid (str): The type of metadata to create or the UID of a template to use.
            metadata_producer_organization (Optional[str]): The name of the organisation producing the metadata.
            filename (Optional[str]): If output_mode=='excel', the path to the Excel file.
                If None and output_mode=='excel', defaults to {name of metadata type}_metadata.xlsx
            title (Optional[str]): If output_mode=='excel', the title for the Excel sheet.
                If None and mode=='excel', defaults to '{name of metadata type} Metadata'
            llm_model_name (str): The model to use. Defaults to "gpt-4o". Note any model must accept a response
                format (also called structured output). Usually you should leave this to the default value.
                The option is provided in case OpenAI deprecated the 4o model.
            tokenizer_model (str): The tokenizer model to use. Defaults to "o200k_base". Note this should be the
                tokenizer corresponding to the OpenAI model used. Usually you should leave this to the default value.
                The option is provided in case OpenAI deprecated the 4o model.
            max_tokens (int): The maximum number of tokens to use when sending the content to OpenAI.
                Defaults to 128_000, which has been the typical maximum for the 4o model.
            llm_base_url (Optional[str]): The base URL for the LLM API. If None, the default URL is used which
                sends the request to OpenAI. Alternatively, this can be the base URL for a local LLM instance such as
                Ollama or a private deployment of an LLM model. If using Azure OpenAI, this should be the Azure
                endpoint URL (eg "https://my-azure-openai-resource.openai.azure.com/") and the azure_deployment_name
                parameter should also be set.
            azure_deployment_name (Optional[str]): Used when an organization has its own deployment of an LLM model in
                Azure, possibly for privacy reasons. Be sure to provide the llm_base_url parameter as well which should
                be the Azure endpoint URL.

        Returns:
            (Union[BaseModel, Dict, str]): If mode == 'dict', a dictionary is returned. If mode == 'pydantic', a
                pydantic model object is returned. If mode == 'excel' then the metadata was saved to a file and the
                filename is returned.

        Example:
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
        """
        #  prefix (Optional[str]): A prefix to add to the metadata. Defaults to '?'. If None, no prefix is added.

        metadata_class_no_rules, metadata_type, _ = self._get_metadata_class_and_type_and_UID(
            metadata_type_or_template_uid, apply_template_rules=False
        )
        enc = tiktoken.get_encoding(tokenizer_model)
        if azure_deployment_name is None:
            client = OpenAI(api_key=llm_api_key, base_url=llm_base_url)
        else:
            client = AzureOpenAI(
                api_key=llm_api_key,
                azure_endpoint=llm_base_url,
                azure_deployment=azure_deployment_name,
                api_version="2024-10-01",
            )

        system_prompt = f"You are an expert on producing {metadata_type} documentation. "
        system_prompt += (
            "Based on the user content, write project metadata. "
            "If you are unsure about the correct metadata values, leave them blank. "
            "Do not guess. Accuracy is more important than completeness. "
        )

        # "You are an expert on survey microdata documentation. Based on the user content alone, write project metadata.
        # If you are unsure about the correct metadata values, leave them blank. Do not guess. Accuracy is more
        # important than completeness."},

        messages = [
            {"role": "system", "content": system_prompt},
        ]

        md = MarkItDown(llm_client=client, llm_model=llm_model_name)

        if isinstance(files, str):
            files = [files]

        out = f"The metadata is being produced today, {get_date_as_text()}."
        if metadata_producer_organization is not None:
            out += f" The metadata is being produced by {metadata_producer_organization}.\n\n"
        for doc in files:
            out += "################################################\n\n"
            out += f"# {doc}\n\n"
            out += md.convert(doc).text_content + "\n\n"
            user_message = [{"role": "user", "content": out}]
            num_tokens = len(enc.encode(messages[0]["content"]) + enc.encode(user_message[0]["content"]))
            if num_tokens > max_tokens:
                warnings.warn(
                    f"Caution - after importing {doc} the token count will be {num_tokens} which exceeds the maximum of"
                    f" {max_tokens}, truncating the content and proceeding."
                )
            else:
                print(f"Reading {doc}, running token count is {num_tokens}")
        messages += user_message

        endpoint_name = llm_base_url if llm_base_url is not None else "OpenAI"
        print(f"Sending to {endpoint_name}, this may take a few minutes...")
        try:
            completion = client.beta.chat.completions.parse(
                model=llm_model_name,
                messages=messages,
                response_format=metadata_class_no_rules,
            )

            message = completion.choices[0].message
            if not message.parsed:
                raise ValueError(message.refusal)

            metadata_dict = message.parsed.model_dump(exclude_none=True, exclude_unset=True)
        except ValidationError:
            metadata_dict = call_per_field(metadata_class_no_rules, client, llm_model_name, messages).model_dump(
                exclude_none=True, exclude_unset=True
            )
        # if prefix:
        #     metadata_dict = self._prepend_draft_drop_non_str(metadata_dict, prefix)
        metadata_class_with_rules = self.get_metadata_class(metadata_type_or_template_uid)
        metadata_with_rules = _iterated_validated_update_to_outline(metadata_class_with_rules, metadata_dict)

        return self._process_metadata_output(
            metadata_object=metadata_with_rules,
            output_mode=output_mode,
            filename=filename,
            title=title,
        )

    def augment_metadata_from_files(
        self,
        input_metadata: Union[BaseModel, Dict, str],
        llm_api_key: str,
        files: List[str] | str,
        output_mode: str,
        metadata_type_or_template_uid: Optional[str] = None,
        metadata_producer_organization: Optional[str] = None,
        prefix: Optional[str] = None,
        filename: Optional[str] = None,
        title: Optional[str] = None,
        llm_model_name="gpt-4o",
        tokenizer_model="o200k_base",
        max_tokens=128_000,
        llm_base_url: Optional[str] = None,
        azure_deployment_name: Optional[str] = None,
    ) -> Union[BaseModel, Dict, str]:
        """Augment existing metadata with information from files or web pages.

        Since the metadata is being augmented, the new metadata can be given a prefix to indicate it is new.

        Args:
            input_metadata (Union[BaseModel, Dict, str]): The existing metadata to augment. Can be a dictionary, a
                pydantic model or a path to an Excel file.
            llm_api_key (str): The API key for the LLM API.
            files (List[str] | str): The path to the file or a list of paths to the files from which to base metadata.
            output_mode (str): The type of output. Must be 'dict', 'pydantic' or 'excel'.
            metadata_type_or_template_uid (Optional[str]): The type of metadata to create or the UID of a template to
                use. If None then the type will be inferred from the input_metadata.
            metadata_producer_organization (Optional[str]): The name of the organisation producing the metadata.
            prefix (Optional[str]): A prefix to add to the new metadata. If None, no prefix is added.
            filename (Optional[str]): If output_mode=='excel', the path to the Excel file.
                If None and output_mode=='excel', defaults to {name of metadata type}_metadata.xlsx
            title (Optional[str]): If output_mode=='excel', the title for the Excel sheet.
                If None and mode=='excel', defaults to '{name of metadata type} Metadata'
            llm_model_name (str): The OpenAI model to use. Defaults to "gpt-4o". Note any model must accept a response
                format (also called structured output). Usually you should leave this to the default value.
                The option is provided in case OpenAI deprecated the 4o model.
            tokenizer_model (str): The tokenizer model to use. Defaults to "o200k_base". Note this should be the
                tokenizer corresponding to the OpenAI model used. Usually you should leave this to the default value.
                The option is provided in case OpenAI deprecated the 4o model.
            max_tokens (int): The maximum number of tokens to use when sending the content to OpenAI.
                Defaults to 128_000, which has been the typical maximum for the 4o model.
            llm_base_url (Optional[str]): The base URL for the LLM API. If None, the default URL is used which
                sends the request to OpenAI. Alternatively, this can be the base URL for a local LLM instance such as
                Ollama or a private deployment of an LLM model. If using Azure OpenAI, this should be the Azure
                endpoint URL (eg "https://my-azure-openai-resource.openai.azure.com/") and the azure_deployment_name
                parameter should also be set.
            azure_deployment_name (Optional[str]): Used when an organization has its own deployment of an LLM model in
                Azure, possibly for privacy reasons. Be sure to provide the llm_base_url parameter as well which should
                be the Azure endpoint URL.

        Returns:
            Union[BaseModel, Dict, str]: The augmented metadata.

        Example:
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
        """
        #  prefix (Optional[str]): A prefix to add to the metadata. Defaults to '?'. If None, no prefix is added.

        if isinstance(input_metadata, str):
            input_metadata = pd.read_excel(input_metadata, sheet_name=0).to_dict(orient="records")[0]

        metadata_type_or_template_uid = self._process_metadata_input(input_metadata, metadata_type_or_template_uid)[2]

        if metadata_type_or_template_uid is None:
            raise ValueError("metadata_type_or_template_uid must be passed when input_metadata is a dictionary")

        old_metadata = self.change_mode_or_template(
            input_metadata, output_mode="dict", input_template_uid=metadata_type_or_template_uid, simplify=True
        )

        klass = self.get_metadata_class(metadata_type_or_template_uid)

        old_metadata = _iterated_validated_update_to_outline(klass, updates=old_metadata)

        old_metadata = self.change_mode_or_template(old_metadata, output_mode="dict", simplify=True)
        old_metadata_md = "# Previously written metadata\n\n"
        old_metadata_md += json_to_markdown(old_metadata, level=2)

        with NamedTemporaryFile(delete=True, suffix=".txt") as f:
            f.write(old_metadata_md.encode("utf-8"))
            f.flush()

        if metadata_type_or_template_uid is None:
            if isinstance(input_metadata, dict):
                raise ValueError("metadata_type_or_template_uid must be passed when input_metadata is a dictionary")

            _, _, metadata_type_or_template_uid = self._process_metadata_input(
                input_metadata, metadata_type_or_template_uid
            )

        old_metadata = self.change_mode_or_template(
            input_metadata, output_mode="dict", input_template_uid=metadata_type_or_template_uid, simplify=True
        )

        klass = self.get_metadata_class(metadata_type_or_template_uid)

        old_metadata = _iterated_validated_update_to_outline(klass, updates=old_metadata)

        old_metadata = self.change_mode_or_template(old_metadata, output_mode="dict", simplify=True)
        old_metadata_md = "# Prevsiouly written metadata\n\n"
        old_metadata_md += json_to_markdown(old_metadata, level=2)

        with NamedTemporaryFile(delete=True, suffix=".txt") as f:
            f.write(old_metadata_md.encode("utf-8"))
            f.flush()  # Ensure the content is written to disk
            file_path = f.name

            if isinstance(files, str):
                files = [files]
            files = [file_path] + files

            new_metadata = self.draft_metadata_from_files(
                llm_api_key=llm_api_key,
                files=files,
                metadata_type_or_template_uid=metadata_type_or_template_uid,
                metadata_producer_organization=metadata_producer_organization,
                output_mode="dict",
                # prefix=prefix,
                filename=None,
                title=None,
                llm_model_name=llm_model_name,
                tokenizer_model=tokenizer_model,
                max_tokens=max_tokens,
                llm_base_url=llm_base_url,
                azure_deployment_name=azure_deployment_name,
            )

        if new_metadata is None or len(new_metadata) == 0:
            raise ValueError("No metadata was generated from the files.")

        if prefix:
            new_metadata = _prepend_draft_drop_non_str(new_metadata, prefix=prefix)

        combined_metadata = merge_dicts(old_metadata, new_metadata)

        metadata_object = _iterated_validated_update_to_outline(klass, updates=combined_metadata)
        return self._process_metadata_output(
            metadata_object=metadata_object,
            output_mode=output_mode,
            filename=filename,
            title=title,
        )

    # def log_project_admin_metadata(
    #         self, id: int, metadata: Union[BaseModel, Dict, str], metadata_type_or_template_uid: Optional[str] = None
    # ) -> int:
    #     """Validates and logs admin metadata which can be a dictionary, a pydantic model or a path to an Excel file.

    #     Args:
    #         id (int): The ID of the project to associate the metadata with.
    #         metadata (dictionary or BaseModel or str): If str, it's assumed this is a path to an appropriately
    #             formatted Excel file.
    #         admin_metadata_template_uid (str, optional): The UID of the admin metadata template to use.
    #             otherwise the UID associated with the pydantic model or the Excel file will be used.

    #     Returns:
    #         int: The ID of the newly created admin metadata
    #     """
    #     metadata, metadata_type, uid = self._process_metadata_input(metadata, metadata_type_or_template_uid)
    #     post_request_pth = "admin-metadata/data/"
    #     post_json = {
    #         "project_id": id,
    #         "template_uid": uid,
    #         "metadata": remove_empty_from_dict(metadata.model_dump(mode="json",
    #                                                                exclude_none=True,
    #                                                                exclude_unset=True)),
    #     }
    #     ret = self._apinterface.post_request(
    #         pth=post_request_pth,
    #         json=post_json,
    #         id=id,
    #     )
    #     return ret

    def _refresh_default_templates_cache(self) -> pd.DataFrame:
        """Load default template mappings from the API into an internal DataFrame cache."""
        response = self.templates.list()
        if "templates" not in response or len(response["templates"]) == 0:
            return pd.DataFrame([], columns=["uid", "template_type", "name", "template"])
        templates = pd.DataFrame([v_item for _, v in response["templates"].items() for v_item in v])
        if "default" in templates and "uid" in templates and "data_type" in templates:
            self._default_templates = templates[templates.default].drop_duplicates("uid").drop_duplicates("data_type")

            def standardize(row):
                try:
                    return self._mm.standardize_metadata_name(row["data_type"])
                except ValueError:
                    return row["data_type"]

            self._default_templates["data_type"] = self._default_templates.apply(standardize, axis=1)
        return templates

    def _ensure_template_cached(self, uid: str) -> pd.Series:
        """Fetch a template from the API (or cache) and build its pydantic class when needed."""
        if uid in self._templates:
            return self._templates[uid]["template"]
        response = self.templates.get(uid)
        if "result" not in response:
            raise KeyError(f"No result returned.\nResponse: {response}")

        temp = pd.Series(response["result"], name=response["result"]["name"])
        try:
            standard_type_name = self._mm.standardize_metadata_name(temp.data_type)
        except ValueError:
            standard_type_name = temp.data_type
        self._templates[uid] = {"template": temp, "metadata_type": standard_type_name}
        try:
            try:
                parent_schema = self._mm.metadata_class_from_name(temp.data_type)
            except ValueError:
                warnings.warn(
                    f"Could not find a metadata class for template type '{standard_type_name}', UID '{uid}'. "
                    f"Building a class from the template without a parent schema."
                )
                parent_schema = SchemaBaseModel
            klass = pydantic_from_template(
                temp.template, parent_schema=parent_schema, uid=uid, name=temp.name, metadata_type=standard_type_name
            )
            self._templates[uid]["class"] = klass
        finally:
            return temp

    def change_mode_or_template(
        self,
        metadata: Union[BaseModel, Dict, str],
        output_mode: str,
        output_template_uid: Optional[str] = None,
        input_template_uid: Optional[str] = None,
        filename: Optional[str] = None,
        title: Optional[str] = None,
        simplify: Optional[bool] = None,
    ) -> Union[BaseModel, Dict, str]:
        """Change the mode or template of a metadata object.

        In terms of modes, you can convert
            - a dict to a pydantic model, or vice versa,
            - a dict to an Excel file, or vice versa,
            - a pydantic model to an Excel file, or vice versa

        And in terms of templates, you can convert a metadata object from one template to another.

        Args:
            metadata (Union[BaseModel, Dict, str]): The metadata to process.
            output_mode (str): The output mode. Must be 'dict', 'pydantic' or 'excel'.
            output_template_uid (Optional[str]): The UID of the new template. If None then the existing template is
                used.
            input_template_uid (Optional[str]): The UID of the input template. Required if the metadata is a dictionary.
                Ignored if metadata is a pydantic model or a path to an Excel file.
            filename (Optional[str]): If output_mode=='excel', the path to the Excel file.
                If None, defaults to {name of metadata type}_metadata.xlsx
            title (Optional[str]): If output_mode=='excel', the title for the Excel sheet.
                If None, defaults to '{name of metadata type} Metadata'
            simplify (Optional[bool]): If output_mode=='dict', then if simplify=True, only elements that were explicitly
                set with non-null, non-empty values are returned in the dictionary. Default behaviour is False

        Returns:
            Union[BaseModel, Dict, str]: The updated metadata object.
        """
        metadata, metadata_type, uid = self._process_metadata_input(metadata, input_template_uid)

        if not (output_template_uid is None or output_template_uid == uid):
            new_klass, new_type, _ = self._get_metadata_class_and_type_and_UID(output_template_uid)
            try:
                # metadata = new_klass.model_validate(
                #     remove_empty_from_dict(metadata.model_dump(mode="json", exclude_none=True, exclude_unset=True)),
                #     strict=False,
                # )
                metadata = _iterated_validated_update_to_outline(
                    new_klass, updates=metadata.model_dump(mode="json", exclude_none=True, exclude_unset=True)
                )
            except ValidationError as e:
                raise TemplateError(
                    f"Could not coerce metadata from the {metadata_type} template with UID "
                    f"'{input_template_uid}' to {new_type} template with UID '{output_template_uid}'",
                    e,
                )
            if metadata_type != new_type:
                warnings.warn(
                    f"The metadata type of the logged project is {metadata_type} but the metadata type "
                    f"of the new template is {new_type}, which could lead to data loss."
                )

        return self._process_metadata_output(
            metadata_object=metadata,
            output_mode=output_mode,
            filename=filename,
            title=title,
            simplify=simplify,
        )

    ####################################################################################################################
    # EXCEL INTERFACE
    ####################################################################################################################

    def save_metadata_to_excel(
        self,
        metadata_model: BaseModel | dict | str,
        metadata_type_or_template_uid: Optional[str] = None,
        filename: Optional[str] = None,
        title: Optional[str] = None,
    ) -> str:
        """Save a metadata object to an Excel file.

        Args:
            metadata_model (BaseModel|dict|str): The pydantic object, python dictionary or path to an Excel file.
            metadata_type_or_template_uid (Optional[str]): If the metadata is a dictionary, this is the UID of the
                template to use. Ignored if metadata is a pydantic model or a path to an Excel file.
            filename (Optional[str]): The path to the output Excel file. Defaults to {name}_metadata.xlsx
            title (Optional[str]): The title for the output Excel sheet. Defaults to '{name} Metadata'

        Returns:
            str: The path to the saved Excel file.
        """
        processed_model = self._process_metadata_input(
            metadata_model, metadata_type_or_template_uid=metadata_type_or_template_uid
        )[0]
        return self._process_metadata_output(
            metadata_object=processed_model, output_mode="excel", filename=filename, title=title
        )

    def read_metadata_from_excel(
        self,
        filename: str,
        output_mode: str = "pydantic",
        exclude_unset=True,
    ) -> Union[BaseModel, Dict]:
        """Read metadata from an Excel file.

        Args:
            filename (str): The path to the Excel file.
            output_mode (str): The output mode. Must be 'pydantic' or 'dict'.
            exclude_unset (bool): If mode=='dict', then if exclude_unset=True, only elements that were explicitly set
                with non-null, non-empty values are returned in the dictionary.

        Returns:
            Union[BaseModel, Dict]: The metadata object or dictionary.
        """
        assert output_mode not in EXCEL_MODES, (
            f"read_metadata_from_excel output_mode should be 'pydantic' or 'dict' but found '{output_mode}'"
        )
        object = self._process_metadata_input(filename)[0]
        return self._process_metadata_output(object, output_mode, simplify=exclude_unset)
