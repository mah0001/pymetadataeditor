"""Publish-to-NADA API wrappers (synchronous endpoints)."""

from typing import Any, Dict, Optional, Union

from .jobs import _normalize_project_id
from .requester import RequestsWithSpecificErrors


class PublishClient:
    """Synchronous publish endpoints under /publish/*."""

    def __init__(self, api: RequestsWithSpecificErrors):
        self._api = api

    def catalog_connections(self) -> Dict:
        """List NADA catalog connections for the current API user."""
        return self._api.get_request(pth="publish/catalog_connections")

    def catalog_info(
        self,
        project_id: Union[int, str],
        catalog_connection_id: int,
    ) -> Dict:
        """Prefetch NADA collections, access codes, and existing study info."""
        pid = _normalize_project_id(project_id)
        return self._api.get_request(
            pth=f"publish/catalog_info/{pid}/{int(catalog_connection_id)}"
        )

    def metadata(
        self,
        project_id: Union[int, str],
        catalog_connection_id: int,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict:
        """Publish project metadata synchronously.

        Calls ``POST /publish/{project_id}/{catalog_connection_id}`` with NADA
        options (``access_policy``, ``published``, ``repositoryid``, etc.) merged
        into the exported project JSON before posting to the catalog.
        """
        pid = _normalize_project_id(project_id)
        return self._api.post_request(
            pth=f"publish/{pid}/{int(catalog_connection_id)}",
            json=options or {},
        )

    def generate_json(self, project_id: Union[int, str]) -> Dict:
        """Write the project JSON from the current metadata (``GET editor/generate_json/{id}``).

        Publishing metadata also does this; call it to refresh the JSON file explicitly.
        """
        pid = _normalize_project_id(project_id)
        return self._api.get_request(pth=f"editor/generate_json/{pid}")

    def indicator(
        self,
        project_id: Union[int, str],
        catalog_connection_id: int,
        publish_dsd: bool = True,
        dsd_overwrite: bool = False,
        dsd_force: bool = False,
        publish_indicator_data: bool = True,
        timeout: Optional[float] = None,
    ) -> Dict:
        """Publish an indicator project's data structure and/or data to NADA (synchronous).

        Calls ``POST /publish/indicator/{project_id}/{catalog_connection_id}``. With ``dsd_overwrite``, the
        data structure is re-imported only when it differs from NADA's copy; ``dsd_force`` re-imports anyway
        (re-importing flags every NADA study on that structure for re-sync).
        Returns ``{"dsd": ..., "data": ...}``.
        """
        pid = _normalize_project_id(project_id)
        body = {
            "publish_dsd": bool(publish_dsd),
            "dsd_overwrite": bool(dsd_overwrite),
            "dsd_force": bool(dsd_force),
            "publish_indicator_data": bool(publish_indicator_data),
        }
        return self._api.post_request(
            pth=f"publish/indicator/{pid}/{int(catalog_connection_id)}", json=body, timeout=timeout
        )
