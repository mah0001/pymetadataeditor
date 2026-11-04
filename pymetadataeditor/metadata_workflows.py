"""Higher-level metadata workflows (templates, validation, Excel/pydantic I/O)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Optional, Union

from metadataschemas.utils.utils import merge_dicts, standardize_keys_in_dict
from pydantic import BaseModel, ValidationError

from .api_types import ProjectIdOrIdno, normalize_project_type
from .constants import DICT_MODES, EXCEL_MODES, PYDANTIC_MODES
from .exceptions import TemplateError
from .utils import remove_empty_from_dict

if TYPE_CHECKING:
    from .interface import MetadataEditor

#: Microdata parts stored by the editor outside the project metadata.
MICRODATA_TABLES = ("data_files", "variables", "variable_groups")


class MetadataWorkflowsClient:
    """Template-aware metadata operations built on top of thin API clients."""

    def __init__(self, editor: "MetadataEditor"):
        self._editor = editor

    def _add_microdata_tables(
        self, project_id: ProjectIdOrIdno, project: Dict, include_variables: bool = False
    ) -> None:
        """Add a microdata project's data files, variables and variable groups to ``project["metadata"]``.

        The editor stores these outside the project metadata; the JSON export returns them.
        """
        try:
            project_type = self._editor._mm.standardize_metadata_name(project.get("type", ""))
        except ValueError:
            return
        if project_type != "microdata":
            return
        export = self._editor.projects.get_json(project_id, exclude_variables=None if include_variables else 1)
        metadata = project.get("metadata") or {}
        for key in MICRODATA_TABLES:
            if key == "variables" and not include_variables:
                continue
            if export.get(key) and not metadata.get(key):
                metadata[key] = export[key]
        project["metadata"] = metadata

    def get(
        self,
        project_id: ProjectIdOrIdno,
        output_mode: str,
        template_uid: Optional[str] = None,
        simplify: bool = True,
        filename: Optional[str] = None,
        title: Optional[str] = None,
        debug: bool = False,
        include_variables: bool = False,
    ) -> Union[BaseModel, Dict, str]:
        """Return project metadata as dict, pydantic model, or Excel file.

        For microdata, the data files and variable groups (stored apart from the study metadata) are included.
        ``include_variables=True`` also adds the variables, which can be large.
        """
        output_mode = output_mode.lower().strip()
        if output_mode not in DICT_MODES + EXCEL_MODES + PYDANTIC_MODES:
            raise ValueError(f"output_mode must be 'pydantic', 'dict' or 'excel' but found '{output_mode}'")

        template_uid = template_uid.lower().strip() if template_uid is not None else None
        if template_uid == "none" and output_mode not in DICT_MODES:
            raise ValueError("When template_uid='none' then output_mode must be 'dict'")

        project = self._editor.projects.get(project_id)["project"]
        self._add_microdata_tables(project_id, project, include_variables=include_variables)

        if template_uid == "none":
            return project["metadata"]

        if template_uid == "default":
            _, _, template_uid = self._editor._get_metadata_class_and_type_and_UID(project["type"])
            if template_uid is None:
                raise ValueError(
                    f"Cannot apply default template to metadata type '{project['type']}' as "
                    f"no default template is set for this type"
                )
            if template_uid == project.get("template_uid"):
                template_uid = None

        if template_uid is not None:
            klass, _, uid = self._editor._get_template_class_and_type_and_UID(template_uid)
            skeleton_object = self._editor.make_metadata_outline(uid, output_mode="dict")
            validation_error_msg = (
                f"The stored metadata conflicts with the specified {project['type']} template with UID '{uid}'"
            )
        elif project.get("template_uid"):
            uid = project["template_uid"]
            klass, _, uid = self._editor._get_template_class_and_type_and_UID(uid)
            skeleton_object = self._editor.make_metadata_outline(uid, output_mode="dict")
            validation_error_msg = (
                f"The stored metadata conflicts with the assigned {project['type']} template "
                f"with UID '{project['template_uid']}'"
            )
        else:
            klass, metadata_type, uid = self._editor._get_metadata_class_and_type_and_UID(project["type"])
            skeleton_object = self._editor.make_metadata_outline(metadata_type, output_mode="dict")
            validation_error_msg = f"The stored metadata conflicts with the default {project['type']} template"
            if uid is not None:
                validation_error_msg += f" with UID '{uid}'"

        if debug:
            print(f"\nskeleton_object = {skeleton_object}\n")
            print(f"\nproject_metadata = {project['metadata']}\n")

        combined_dict = merge_dicts(
            skeleton_object,
            remove_empty_from_dict(project["metadata"]),
            skeleton_mode=True,
        )
        combined_dict = standardize_keys_in_dict(combined_dict)
        if debug:
            print(f"combined_dict = {combined_dict}\n")
        try:
            metadata_object = klass.model_validate(standardize_keys_in_dict(combined_dict), strict=False)
        except ValidationError as e:
            raise TemplateError(
                f"{validation_error_msg}, consider rerunning metadata.get with "
                f"output_mode='dict' and template_uid='none' or changing the assigned template",
                response=e,
            ) from e

        return self._editor._process_metadata_output(
            metadata_object=metadata_object,
            output_mode=output_mode,
            filename=filename,
            title=title,
            simplify=simplify,
        )

    def create(
        self,
        metadata: Union[BaseModel, Dict, str],
        metadata_type_or_template_uid: Optional[str] = None,
    ) -> int:
        """Validate metadata and create a project; returns new project id."""
        metadata_obj, metadata_type, _ = self._editor._process_metadata_input(metadata, metadata_type_or_template_uid)
        payload = remove_empty_from_dict(
            metadata_obj.model_dump(mode="json", exclude_none=True, exclude_unset=True)
        )
        response = self._editor.projects.create(normalize_project_type(metadata_type), payload)
        return int(response["id"])

    def update(
        self,
        project_id: ProjectIdOrIdno,
        new_metadata: Union[BaseModel, Dict, str],
    ) -> None:
        """Validate and update project metadata (subset updates supported for dict input)."""
        project_data = self._editor.projects.get(project_id)["project"]
        try:
            project_type = self._editor._mm.standardize_metadata_name(project_data["type"])
        except ValueError as e:
            raise ValueError(
                f"Unknown metadata type {project_data['type']}. The metadata type is required to "
                f"set the metadata API endpoint path, therefore we cannot update the metadata."
            ) from e

        project_uid = project_data.get("template_uid") or None
        if project_uid:
            metadata_type_or_template_uid = project_uid
        else:
            metadata_type_or_template_uid = project_type

        if not isinstance(new_metadata, dict):
            if isinstance(new_metadata, BaseModel):
                metadata_type = (
                    new_metadata._metadata_type__
                    if isinstance(new_metadata._metadata_type__, str)
                    else new_metadata._metadata_type__.default
                )
                uid = (
                    new_metadata._template_uid__
                    if isinstance(new_metadata._template_uid__, str)
                    else new_metadata._template_uid__.default
                    if hasattr(new_metadata._template_uid__, "default")
                    else None
                )
            else:
                metadata_info = self._editor._mm.get_metadata_type_info_from_excel_file(new_metadata)
                metadata_type = metadata_info["metadata_type"]
                uid = metadata_info.get("template_uid", None)
            if uid is not None and project_uid != uid:
                raise ValueError(
                    f"The template UID of the existing project is {project_uid} but the template UID "
                    f"of the new metadata is {uid}.\n"
                    f"The template of the new metadata should be changed to match the existing project "
                    f"uid='{project_uid}' or change the template of the existing project to match the new metadata "
                    f"uid='{uid}'."
                )
            if uid is None and metadata_type != project_type:
                raise ValueError(
                    f"The metadata type of the existing project is {project_type} but the metadata type "
                    f"of the new metadata is {metadata_type}."
                )

        metadata_obj, metadata_type, uid = self._editor._process_metadata_input(
            new_metadata, metadata_type_or_template_uid
        )

        if project_type != metadata_type:
            raise ValueError(
                f"The metadata type of the existing project is {project_type} but the metadata type "
                f"of the new metadata is {metadata_type}."
            )

        if uid is not None and project_uid is not None and project_uid != uid:
            raise ValueError(
                f"The template UID of the existing project is {project_uid} but the template UID "
                f"of the new metadata is {uid}.\n"
                "This could cause issues if the templates are incompatible.\n"
                f"You should change the template of the new metadata to match the existing project "
                f"uid='{project_uid}' or change the template of the existing project to match the new metadata "
                f"uid='{uid}'."
            )

        payload = remove_empty_from_dict(
            metadata_obj.model_dump(mode="json", exclude_none=True, exclude_unset=True)
        )
        self._editor.projects.update(project_id, normalize_project_type(metadata_type), payload)
