"""Thin collection endpoint wrappers for the Metadata Editor API."""

from typing import TYPE_CHECKING, Any, Dict, Iterator, List, Optional, Union

from .requester import RequestsWithSpecificErrors

if TYPE_CHECKING:  # pragma: no cover
    from .projects import ProjectsClient


class CollectionsClient:
    """Collection-focused thin wrappers around API endpoints."""

    def __init__(self, api: RequestsWithSpecificErrors, projects: Optional["ProjectsClient"] = None):
        self._api = api
        if projects is None:
            from .projects import ProjectsClient

            projects = ProjectsClient(api)
        self._projects = projects

    def list(self) -> Dict:
        """List collections visible to the API key."""
        return self._api.get_request(pth="/collections")

    def get(self, id: Union[int, str]) -> Dict:
        """Get a collection by id."""
        return self._api.get_request(pth="/collections/{}", id=id)

    def create(self, title: str, description: str) -> Dict:
        """Create a collection."""
        assert title != "", "The collection must have a title but an empty string was passed"
        return self._api.post_request(pth="/collections", json={"title": title, "description": description})

    def update(
        self,
        id: Union[int, str],
        title: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Dict:
        """Update collection title and/or description."""
        assert title is not None or description is not None, "can update title or description or both, but not neither"
        payload: Dict[str, str] = {}
        if title is not None:
            payload["title"] = title
        if description is not None:
            payload["description"] = description
        return self._api.post_request(pth="/collections/update/{}", id=id, json=payload)

    def delete(self, id: Union[int, str]) -> Dict:
        """Delete a collection by id (POST, for environments that block HTTP DELETE)."""
        return self._api.post_request(pth="/collections/delete/{}", id=id)

    def copy(self, source_id: int, target_id: int) -> Dict:
        """Copy projects and users from one collection to another."""
        return self._api.post_request(
            pth="/collections/copy",
            json={"source_id": source_id, "target_id": target_id},
        )

    def move(self, source_id: int, target_id: int) -> Dict:
        """Move a collection under another collection."""
        return self._api.post_request(
            pth="/collections/move",
            json={"source_id": source_id, "target_id": target_id},
        )

    def permissions(self) -> Dict:
        """Get the API user's collection permission levels."""
        return self._api.get_request(pth="/collections/permissions")

    def count_projects(self, collection_id: int) -> int:
        """Count projects in a collection."""
        return self._projects.count(collection=collection_id)

    def list_projects(
        self,
        collection_id: int,
        limit: int = 100,
        offset: int = 0,
        keywords: Optional[Union[str, List[str]]] = None,
        sort_by: Optional[str] = None,
        **filters: Any,
    ) -> Dict:
        """List one page of projects in a collection (``GET /editor?collection=``).

        Accepts the filters of :meth:`ProjectsClient.list`.
        """
        return self._projects.list(
            limit=limit, offset=offset, keywords=keywords, sort_by=sort_by, collection=collection_id, **filters
        )

    def iter_projects(
        self, collection_id: int, page_size: int = 500, max_items: Optional[int] = None, **filters: Any
    ) -> Iterator[Dict]:
        """Yield the projects of a collection one at a time (accepts the filters of :meth:`list_projects`)."""
        return self._projects.iter_all(
            page_size=page_size, max_items=max_items, collection=collection_id, **filters
        )

    def add_projects(
        self,
        collections: Union[int, List[int]],
        id_format: str,
        projects: Union[int, List[int], str, List[str]],
    ) -> Dict:
        """Add projects to one or more collections."""
        id_format = id_format.lower()
        assert id_format in ["id", "idno"], f"id_format must be either 'id' or 'idno' but got '{id_format}'"
        collection_ids = collections if isinstance(collections, list) else [collections]
        project_ids = projects if isinstance(projects, list) else [projects]
        if id_format == "id":
            for proj in project_ids:
                assert isinstance(proj, int), f"When passing ids the projects must be ints, but found: {proj}"
        else:
            for proj in project_ids:
                assert isinstance(proj, str), f"When passing idnos the projects must be strs but found: {proj}"
        return self._api.post_request(
            pth="/collections/add_projects",
            json={"collections": collection_ids, "id_format": id_format, "projects": project_ids},
        )

    def remove_projects(
        self,
        collections: Union[int, List[int]],
        id_format: str,
        projects: Union[int, List[int], str, List[str]],
    ) -> Dict:
        """Remove projects from one or more collections."""
        id_format = id_format.lower()
        assert id_format in ["id", "idno"], f"id_format must be either 'id' or 'idno' but got '{id_format}'"
        collection_ids = collections if isinstance(collections, list) else [collections]
        project_ids = projects if isinstance(projects, list) else [projects]
        if id_format == "id":
            for proj in project_ids:
                assert isinstance(proj, int), f"When passing ids the projects must be ints, but found: {proj}"
        else:
            for proj in project_ids:
                assert isinstance(proj, str), f"When passing idnos the projects must be strs but found: {proj}"
        return self._api.post_request(
            pth="/collections/remove_projects",
            json={"collections": collection_ids, "id_format": id_format, "projects": project_ids},
        )

    def set_template(self, collection_id: int, template_uid: str, project_type: str) -> Dict:
        """Set the default template for a project type within a collection."""
        return self._api.post_request(
            pth="/collections/template",
            json={
                "collection_id": collection_id,
                "template_uid": template_uid,
                "project_type": project_type,
            },
        )
