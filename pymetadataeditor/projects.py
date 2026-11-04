"""Thin project endpoint wrappers for the Metadata Editor API."""

from typing import Any, Dict, Iterable, Iterator, List, Optional, Union

from .api_types import ProjectIdOrIdno, normalize_project_type
from .paging import iter_offset_pages, join_values
from .requester import RequestsWithSpecificErrors
from .utils import validate_json_patches

#: Values accepted by ``sort_by`` on ``GET /editor``.
SORT_OPTIONS = ("title_asc", "title_desc", "updated_asc", "updated_desc", "id_asc", "id_desc")
#: Values accepted by ``ownership`` on ``GET /editor``.
OWNERSHIP_OPTIONS = ("self", "shared", "self,shared")

ListFilter = Union[str, int, Iterable[Union[str, int]]]

#: Marks ``patch_one`` calls without a ``value`` (None is a valid JSON Patch value).
_NO_VALUE: Any = object()


class ProjectsClient:
    """Project-focused thin wrappers around API endpoints."""

    def __init__(self, api: RequestsWithSpecificErrors):
        self._api = api

    def count(self, **filters: Any) -> int:
        """Count projects visible to the API key (accepts the same filters as :meth:`list`)."""
        return int(self.list(limit=1, **filters)["total"])

    def list(
        self,
        limit: int = 100,
        offset: int = 0,
        keywords: Optional[Union[str, List[str]]] = None,
        metadata_type: Optional[ListFilter] = None,
        sort_by: Optional[str] = None,
        date_start: Optional[str] = None,
        date_end: Optional[str] = None,
        collection: Optional[ListFilter] = None,
        exclude_collections: bool = False,
        ownership: Optional[str] = None,
        users: Optional[ListFilter] = None,
        tag: Optional[ListFilter] = None,
        created_by: Optional[ListFilter] = None,
        changed_by: Optional[ListFilter] = None,
    ) -> Dict:
        """List one page of projects (summary fields, no metadata).

        Args:
            limit: page size (``GET /editor`` default 100). Pages of more than 100 omit ``versions``.
            offset: number of projects to skip.
            keywords: search title, idno and study idno. A list is joined with spaces.
            metadata_type: project type(s), e.g. ``"indicator"`` or ``["microdata", "document"]``.
            sort_by: one of ``title_asc``, ``title_desc``, ``updated_asc``, ``updated_desc`` (default),
                ``id_asc``, ``id_desc``.
            date_start: projects changed on or after this date (``YYYY-MM-DD``).
            date_end: projects changed on or before this date (``YYYY-MM-DD``).
            collection: collection id(s).
            exclude_collections: return projects *not* in ``collection``.
            ownership: ``self``, ``shared`` or ``self,shared``.
            users: user id(s) who created or last changed the project.
            tag: tag id(s).
            created_by: creator user id(s).
            changed_by: last editor user id(s).

        Returns:
            ``{status, total, found, offset, limit, projects, filters}``.
        """
        params: Dict[str, Union[int, str]] = {"offset": offset, "limit": limit}
        if keywords is not None:
            params["keywords"] = keywords if isinstance(keywords, str) else " ".join(str(k) for k in keywords)
        if sort_by is not None:
            sort_by = sort_by.lower()
            if sort_by not in SORT_OPTIONS:
                raise ValueError(f"sort_by must be one of {SORT_OPTIONS}, got {sort_by!r}")
            params["sort_by"] = sort_by
        if ownership is not None:
            ownership = ownership.replace(" ", "").lower()
            if ownership == "shared,self":
                ownership = "self,shared"
            if ownership not in OWNERSHIP_OPTIONS:
                raise ValueError(f"ownership must be one of {OWNERSHIP_OPTIONS}, got {ownership!r}")
            params["ownership"] = ownership
        if exclude_collections:
            if collection is None:
                raise ValueError("exclude_collections needs collection")
            params["exclude_collections"] = "true"
        for key, value in (
            ("type", metadata_type),
            ("collection", collection),
            ("users", users),
            ("tag", tag),
            ("created_by", created_by),
            ("changed_by", changed_by),
        ):
            if value is not None:
                params[key] = join_values(value)
        if date_start is not None:
            params["date_start"] = date_start
        if date_end is not None:
            params["date_end"] = date_end
        return self._api.get_request(pth="/editor", params=params)

    def iter_all(self, page_size: int = 500, max_items: Optional[int] = None, **filters: Any) -> Iterator[Dict]:
        """Yield projects one at a time, fetching ``page_size`` per request.

        Accepts the filters of :meth:`list`. Defaults to ``sort_by="id_asc"`` so that projects edited while
        paging are neither skipped nor repeated.

        Example:
            ```python
            for project in me.projects.iter_all(metadata_type="indicator"):
                print(project["id"], project["title"])
            ```
        """
        filters.setdefault("sort_by", "id_asc")
        return iter_offset_pages(
            lambda limit, offset: self.list(limit=limit, offset=offset, **filters),
            items_key="projects",
            page_size=page_size,
            max_items=max_items,
        )

    def list_all(self, page_size: int = 500, max_items: Optional[int] = None, **filters: Any) -> Dict:
        """Fetch all matching projects into memory: ``{"projects": [...], "total": n}``.

        Prefer :meth:`iter_all` for large catalogs.
        """
        projects = list(self.iter_all(page_size=page_size, max_items=max_items, **filters))
        return {"projects": projects, "total": len(projects)}

    def facets(self) -> Dict:
        """Filter values with counts: project types, collection tree, ownership (``GET /editor/facets``)."""
        return self._api.get_request(pth="/editor/facets")

    def get(self, project_id: ProjectIdOrIdno, version: Optional[str] = None) -> Dict:
        """Get a project by internal id or idno, including its full metadata."""
        params = {"version": version} if version is not None else None
        return self._api.get_request("/editor/{}", id=project_id, params=params)

    def basic_info(self, project_id: ProjectIdOrIdno) -> Dict:
        """Get a project's id, idno, type, title, template and version fields, without the metadata."""
        return self._api.get_request("/editor/basic_info/{}", id=project_id)

    def resolve_id(self, project_id: ProjectIdOrIdno) -> int:
        """Numeric project id for an id or idno (an idno is looked up with :meth:`basic_info`)."""
        text = str(project_id).strip()
        if text.isdigit():
            return int(text)
        return int(self._basic_info_field(text, "id"))

    def resolve_idno(self, project_id: ProjectIdOrIdno) -> str:
        """Project idno for an id or idno (checks that the project exists)."""
        return str(self._basic_info_field(project_id, "idno"))

    def _basic_info_field(self, project_id: ProjectIdOrIdno, field: str) -> Any:
        response = self.basic_info(project_id)
        value = (response.get("project") or {}).get(field) if isinstance(response, dict) else None
        if value is None:
            raise ValueError(f"Project not found: {project_id!r}")
        return value

    def create(self, project_type: str, metadata: Dict) -> Dict:
        """Create a project using API-native type and metadata."""
        endpoint = f"/editor/create/{normalize_project_type(project_type)}"
        return self._api.post_request(pth=endpoint, json=metadata)

    def update(self, project_id: ProjectIdOrIdno, project_type: str, metadata: Dict) -> Dict:
        """Update a project using API-native type and metadata."""
        endpoint = f"/editor/update/{normalize_project_type(project_type)}/" + "{}"
        return self._api.post_request(pth=endpoint, id=project_id, json=metadata)

    def patch(
        self,
        project_id: ProjectIdOrIdno,
        patches: List[Dict],
        project_type: Optional[str] = None,
        validate: bool = True,
    ) -> Dict:
        """Apply JSON Patch operations (RFC 6902) to a project's metadata.

        Args:
            project_id: numeric project id or idno.
            patches: operations such as ``{"op": "replace", "path": "/series_description/name", "value": "..."}``;
                they are checked (op, ``value`` / ``from``) and a missing leading ``/`` is added.
            project_type: the project's type; looked up with :meth:`basic_info` when not given.
            validate: validate the patched metadata against the schema (the server rejects invalid results).
        """
        patches = validate_json_patches(patches)
        if project_type is None:
            project_type = str(self._basic_info_field(project_id, "type"))
        endpoint = f"editor/patch/{normalize_project_type(project_type)}/" + "{}"
        return self._api.post_request(pth=endpoint, id=project_id, json={"patches": patches, "validate": validate})

    def patch_one(
        self,
        project_id: ProjectIdOrIdno,
        op: str,
        path: str,
        value: Any = _NO_VALUE,
        from_path: Optional[str] = None,
        project_type: Optional[str] = None,
        validate: bool = True,
    ) -> Dict:
        """Apply one JSON Patch operation to a project's metadata (see :meth:`patch`).

        ``value`` is required for ``add``, ``replace`` and ``test`` and may be any JSON value, including None;
        ``from_path`` is the ``from`` of ``move`` and ``copy``.
        """
        patch: Dict[str, Any] = {"op": op, "path": path}
        if value is not _NO_VALUE:
            patch["value"] = value
        if from_path is not None:
            patch["from"] = from_path
        return self.patch(project_id, [patch], project_type=project_type, validate=validate)

    def delete(self, project_id: ProjectIdOrIdno) -> Dict:
        """Delete a project by internal id or idno (POST, for environments that block GET deletes)."""
        return self._api.post_request(pth="/editor/delete/{}", id=project_id)

    def get_json(
        self,
        project_id: ProjectIdOrIdno,
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
        return self._api.get_request("/editor/json/{}", id=project_id, params=params if params else None)

    def get_json_field(
        self,
        project_id: ProjectIdOrIdno,
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
        return self._api.get_request("/editor/json_field/{}", id=project_id, params=params)

    def generate_json(self, project_id: ProjectIdOrIdno) -> Dict:
        """Write the project JSON file from the current metadata (``GET editor/generate_json/{id}``).

        Publishing metadata does this too; call it to refresh the file explicitly.
        """
        return self._api.get_request("/editor/generate_json/{}", id=project_id)

    def generate_pdf(
        self,
        project_id: ProjectIdOrIdno,
        include_private_fields: Optional[int] = None,
        template_uid: Optional[str] = None,
    ) -> Dict:
        """Generate PDF documentation for a project."""
        params: Dict[str, Union[int, str]] = {}
        if include_private_fields is not None:
            params["include_private_fields"] = include_private_fields
        if template_uid is not None:
            params["template_uid"] = template_uid
        return self._api.get_request("/editor/generate_pdf/{}", id=project_id, params=params if params else None)

    def import_file(self, project_type: str, file_path: str) -> Dict:
        """Import project metadata or package file."""
        with open(file_path, "rb") as f:
            files = {"file": f}
            data = {"type": project_type}
            return self._api.post_request("/importproject/", data=data, files=files)

    def list_versions(self, project_id: ProjectIdOrIdno, version: Optional[str] = None) -> Dict:
        """List versions for a project."""
        params = {"version": version} if version is not None else None
        return self._api.get_request("/versions/{}", id=project_id, params=params)

    def create_version(self, project_id: ProjectIdOrIdno, version_type: str, version_notes: str) -> Dict:
        """Create a new version for a project."""
        payload: Dict[str, Union[str, int]] = {
            "id": project_id,
            "version_type": version_type,
            "version_notes": version_notes,
        }
        return self._api.post_request("/versions/create", json=payload)

    def delete_version(self, project_id: ProjectIdOrIdno, version: str) -> Dict:
        """Delete a project version by project id/idno and version string."""
        return self._api.post_request("/versions/delete", json={"id": project_id, "version": version})

    def delete_version_by_id(self, version_project_id: ProjectIdOrIdno) -> Dict:
        """Delete a project version by the version's own project id (the main project cannot be deleted this way)."""
        return self._api.post_request("/versions/delete_by_id", json={"id": version_project_id})
