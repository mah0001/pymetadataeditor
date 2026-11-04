"""Thin project endpoint wrappers for the Metadata Editor API."""

from typing import Any, Dict, List, Optional, Union

from .api_types import normalize_project_type
from .requester import RequestsWithSpecificErrors
from .utils import validate_json_patches


class ProjectsClient:
    """Project-focused thin wrappers around API endpoints."""

    def __init__(self, api: RequestsWithSpecificErrors):
        self._api = api

    def count(self) -> int:
        """Count projects visible to the API key."""
        response = self._api.get_request(pth="/editor", params={"offset": 0, "limit": 1})
        return response["total"]

    def list(
        self,
        limit: int = 100,
        offset: int = 0,
        keywords: Optional[Union[str, List[str]]] = None,
        metadata_type: Optional[str] = None,
        sort_by: Optional[str] = None,
        date_start: Optional[str] = None,
        date_end: Optional[str] = None,
        collection: Optional[str] = None,
        exclude_collections: Optional[str] = None,
        ownership: Optional[str] = None,
        users: Optional[str] = None,
    ) -> Dict:
        """List projects using API-native query parameters."""
        params: Dict[str, Union[int, str]] = {"offset": offset, "limit": limit}
        if keywords is not None:
            if isinstance(keywords, list):
                params["keywords"] = "%".join(keywords)
            else:
                params["keywords"] = keywords
        if metadata_type is not None:
            params["type"] = metadata_type
        if sort_by is not None:
            params["sort_by"] = sort_by
        if date_start is not None:
            params["date_start"] = date_start
        if date_end is not None:
            params["date_end"] = date_end
        if collection is not None:
            params["collection"] = collection
        if exclude_collections is not None:
            params["exclude_collections"] = exclude_collections
        if ownership is not None:
            params["ownership"] = ownership
        if users is not None:
            params["users"] = users
        return self._api.get_request(pth="/editor", params=params)

    def list_all(
        self,
        page_size: int = 500,
        **kwargs: Any,
    ) -> Dict:
        """Fetch all projects by paging through /editor."""
        offset = 0
        projects: List[Dict] = []
        while True:
            response = self.list(limit=page_size, offset=offset, **kwargs)
            batch = response.get("projects", [])
            projects.extend(batch)
            if len(batch) < page_size:
                break
            offset += page_size
        return {"projects": projects, "total": len(projects)}

    def get(self, id: Union[int, str], version: Optional[str] = None) -> Dict:
        """Get a project by internal id or idno (API-dependent)."""
        params = {"version": version} if version is not None else None
        return self._api.get_request("/editor/{}", id=id, params=params)

    def create(self, project_type: str, metadata: Dict) -> Dict:
        """Create a project using API-native type and metadata."""
        endpoint = f"/editor/create/{normalize_project_type(project_type)}"
        return self._api.post_request(pth=endpoint, json=metadata)

    def update(self, id: Union[int, str], project_type: str, metadata: Dict) -> Dict:
        """Update a project using API-native type and metadata."""
        endpoint = f"/editor/update/{normalize_project_type(project_type)}/" + "{}"
        return self._api.post_request(pth=endpoint, id=id, json=metadata)

    def patch(self, id: Union[int, str], project_type: str, patches: List[Dict], validate: bool = False) -> Dict:
        """Patch a project metadata document."""
        endpoint = f"editor/patch/{normalize_project_type(project_type)}/" + "{}"
        return self._api.post_request(pth=endpoint, id=id, json={"patches": patches, "validate": validate})

    def patch_one(
        self,
        id: Union[int, str],
        project_type: str,
        op: str,
        path: str,
        value: Optional[str] = None,
        validate: bool = False,
    ) -> Dict:
        """Apply a single JSON Patch operation to project metadata."""
        patch = {"op": op, "path": path}
        if value is not None:
            patch["value"] = value
        patches = validate_json_patches([patch])
        return self.patch(id, project_type, patches, validate=validate)

    def delete(self, id: Union[int, str]) -> Dict:
        """Delete a project by internal id or idno (POST, for environments that block GET deletes)."""
        return self._api.post_request(pth="/editor/delete/{}", id=id)

    def get_json(
        self,
        id: Union[int, str],
        version: Optional[str] = None,
        exclude_variables: Optional[int] = None,
        exclude_private_fields: Optional[int] = None,
        external_resources: Optional[int] = None,
        admin_metadata: Optional[int] = None,
    ) -> Dict:
        """Get project metadata JSON export."""
        params: Dict[str, Union[str, int]] = {}
        if version is not None:
            params["version"] = version
        if exclude_variables is not None:
            params["exclude_variables"] = exclude_variables
        if exclude_private_fields is not None:
            params["exclude_private_fields"] = exclude_private_fields
        if external_resources is not None:
            params["external_resources"] = external_resources
        if admin_metadata is not None:
            params["admin_metadata"] = admin_metadata
        return self._api.get_request("/editor/json{}", id=id, params=params if params else None)

    def get_json_field(
        self,
        id: Union[int, str],
        path: str,
        version: Optional[str] = None,
        exclude_variables: Optional[int] = None,
        exclude_private_fields: Optional[int] = None,
        external_resources: Optional[int] = None,
        admin_metadata: Optional[int] = None,
    ) -> Dict:
        """Get a single value from exported JSON by JSON Pointer."""
        params: Dict[str, Union[str, int]] = {"path": path}
        if version is not None:
            params["version"] = version
        if exclude_variables is not None:
            params["exclude_variables"] = exclude_variables
        if exclude_private_fields is not None:
            params["exclude_private_fields"] = exclude_private_fields
        if external_resources is not None:
            params["external_resources"] = external_resources
        if admin_metadata is not None:
            params["admin_metadata"] = admin_metadata
        return self._api.get_request("/editor/json-field/{}", id=id, params=params)

    def generate_pdf(
        self, id: Union[int, str], include_private_fields: Optional[int] = None, template_uid: Optional[str] = None
    ) -> Dict:
        """Generate PDF documentation for a project."""
        params: Dict[str, Union[int, str]] = {}
        if include_private_fields is not None:
            params["include_private_fields"] = include_private_fields
        if template_uid is not None:
            params["template_uid"] = template_uid
        return self._api.get_request("/editor/generate_pdf/{}", id=id, params=params if params else None)

    def import_project(self, project_type: str, file_path: str) -> Dict:
        """Import project metadata or package file."""
        with open(file_path, "rb") as f:
            files = {"file": f}
            data = {"type": project_type}
            return self._api.post_request("/importproject/", data=data, files=files)

    def list_versions(self, id: Union[int, str], version: Optional[str] = None) -> Dict:
        """List versions for a project."""
        params = {"version": version} if version is not None else None
        return self._api.get_request("/versions/{}", id=id, params=params)

    def create_version(self, id: Union[int, str], version_type: str, version_notes: str) -> Dict:
        """Create a new version for a project."""
        payload: Dict[str, Union[str, int]] = {"id": id, "version_type": version_type, "version_notes": version_notes}
        return self._api.post_request("/versions/create", json=payload)

    def delete_version(self, id: Union[int, str], version: str) -> Dict:
        """Delete a project version by project id/idno and version string."""
        return self._api.post_request("/versions/delete", json={"id": id, "version": version})

    def delete_version_by_id(self, id: Union[int, str], version: str) -> Dict:
        """Delete a project version by project id/idno and version id."""
        return self._api.post_request("/versions/delete_by_id", json={"id": id, "version": version})
