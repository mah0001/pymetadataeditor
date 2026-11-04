"""Thin collection endpoint wrappers for the Metadata Editor API."""

from typing import Dict, Iterable, List, Optional, Union

from .requester import RequestsWithSpecificErrors


class CollectionsClient:
    """Collection-focused thin wrappers around API endpoints."""

    def __init__(self, api: RequestsWithSpecificErrors):
        self._api = api

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

    def list_projects(self, collection_id: int) -> Dict:
        """List projects in a collection (OpenAPI POST /collections/projects)."""
        return self._api.post_request(
            pth="/collections/projects",
            params={"collection_id": collection_id},
        )

    def count_projects(self, collection_id: int) -> int:
        """Count projects in a collection via the editor listing endpoint."""
        response = self._api.get_request(
            pth="/editor",
            params={"offset": 0, "limit": 1, "collection": str(collection_id)},
        )
        return int(response["total"])

    def list_projects_via_editor(
        self,
        collection_id: int,
        limit: int = 100,
        offset: int = 0,
        keywords: Optional[Union[str, List[str]]] = None,
        sort_by: Optional[str] = None,
    ) -> Dict:
        """List projects in a collection using GET /editor?collection=."""
        params: Dict[str, Union[int, str]] = {"limit": limit, "offset": offset, "collection": str(collection_id)}
        if keywords is not None:
            if not isinstance(keywords, str) and isinstance(keywords, Iterable):
                keywords = "%".join(keywords)
            params["keywords"] = str(keywords).replace(" ", "%")
        if sort_by is not None:
            sort_by = sort_by.lower()
            valid_sort_by = ["title_asc", "title_desc", "updated_asc", "updated_desc"]
            assert sort_by in valid_sort_by, f"{sort_by} not valid, must be one of {valid_sort_by}"
            params["sort_by"] = sort_by
        return self._api.get_request(pth="/editor", params=params)

    def list_projects_all(
        self,
        collection_id: int,
        page_size: int = 500,
        keywords: Optional[Union[str, List[str]]] = None,
        sort_by: Optional[str] = None,
    ) -> Dict:
        """Fetch all projects in a collection by paging through GET /editor."""
        offset = 0
        projects: List[Dict] = []
        while True:
            response = self.list_projects_via_editor(
                collection_id=collection_id,
                limit=page_size,
                offset=offset,
                keywords=keywords,
                sort_by=sort_by,
            )
            batch = response.get("projects", [])
            projects.extend(batch)
            if len(batch) < page_size:
                break
            offset += page_size
        return {"projects": projects, "total": len(projects)}

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
