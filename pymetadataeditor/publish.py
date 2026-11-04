"""Publish-to-NADA API wrappers (synchronous endpoints)."""

from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Tuple

from .api_types import ProjectIdOrIdno
from .jobs import _normalize_project_id
from .requester import RequestsWithSpecificErrors

if TYPE_CHECKING:  # pragma: no cover
    from .projects import ProjectsClient


class PublishClient:
    """Synchronous publish endpoints under ``/publish/*``: each call returns once NADA has answered.

    To publish in the background instead, queue a job with ``me.jobs.queue_publish_to_nada``. These
    endpoints need the numeric project id; an idno is resolved first.
    """

    def __init__(self, api: RequestsWithSpecificErrors, projects: Optional["ProjectsClient"] = None):
        self._api = api
        self._projects = projects

    def _pid(self, project_id: ProjectIdOrIdno) -> int:
        pid = _normalize_project_id(project_id)
        if isinstance(pid, int):
            return pid
        if self._projects is None:
            raise ValueError("Publish endpoints need a numeric project id; use projects.resolve_id for an idno")
        return self._projects.resolve_id(pid)

    # ── catalog connections ───────────────────────────────────────────────────

    def catalog_connections(self) -> Dict:
        """List NADA catalog connections for the current API user."""
        return self._api.get_request(pth="publish/catalog_connections")

    def create_catalog_connection(self, title: str, url: str, api_key: Optional[str] = None, **fields: Any) -> Dict:
        """Create a NADA catalog connection for the current API user (``type``, ``is_official`` as fields)."""
        body: Dict[str, Any] = {"title": title, "url": url, **fields}
        if api_key is not None:
            body["api_key"] = api_key
        return self._api.post_request(pth="publish/catalog_connections", json=body)

    def catalog_info(
        self,
        project_id: ProjectIdOrIdno,
        catalog_connection_id: int,
    ) -> Dict:
        """Prefetch NADA collections, access codes, and existing study info."""
        pid = self._pid(project_id)
        return self._api.get_request(
            pth=f"publish/catalog_info/{pid}/{int(catalog_connection_id)}"
        )

    # ── publish steps ─────────────────────────────────────────────────────────

    def metadata(
        self,
        project_id: ProjectIdOrIdno,
        catalog_connection_id: int,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict:
        """Publish project metadata.

        Calls ``POST /publish/{project_id}/{catalog_connection_id}`` with NADA options (``access_policy``,
        ``published``, ``repositoryid``, ``overwrite``, ...). The project JSON is regenerated first.
        """
        pid = self._pid(project_id)
        return self._api.post_request(
            pth=f"publish/{pid}/{int(catalog_connection_id)}",
            json=options or {},
        )

    def indicator_data(
        self,
        project_id: ProjectIdOrIdno,
        catalog_connection_id: int,
        publish_dsd: bool = True,
        dsd_overwrite: bool = False,
        dsd_force: bool = False,
        publish_indicator_data: bool = True,
        timeout: Optional[float] = None,
    ) -> Dict:
        """Publish an indicator project's data structure and/or data to NADA.

        Calls ``POST /publish/indicator/{project_id}/{catalog_connection_id}``. With ``dsd_overwrite``, the
        data structure is re-imported only when it differs from NADA's copy; ``dsd_force`` re-imports anyway
        (re-importing flags every NADA study on that structure for re-sync).
        Returns ``{"dsd": ..., "data": ...}``.
        """
        pid = self._pid(project_id)
        body = {
            "publish_dsd": bool(publish_dsd),
            "dsd_overwrite": bool(dsd_overwrite),
            "dsd_force": bool(dsd_force),
            "publish_indicator_data": bool(publish_indicator_data),
        }
        return self._api.post_request(
            pth=f"publish/indicator/{pid}/{int(catalog_connection_id)}", json=body, timeout=timeout
        )

    def thumbnail(self, project_id: ProjectIdOrIdno, catalog_connection_id: int) -> Dict:
        """Upload the project thumbnail to the NADA study."""
        pid = self._pid(project_id)
        return self._api.post_request(pth=f"publish/thumbnail/{pid}/{int(catalog_connection_id)}", json={})

    def resources(self, project_id: ProjectIdOrIdno, catalog_connection_id: int) -> List[Dict]:
        """Publish all external resources of the project (and their files), overwriting NADA's copies."""
        pid = self._pid(project_id)
        return self._api.post_request(
            pth=f"publish/external_resources/{pid}/{int(catalog_connection_id)}", json={}
        )

    def resource(
        self,
        project_id: ProjectIdOrIdno,
        catalog_connection_id: int,
        resource_id: int,
        overwrite: bool = False,
        nada_upload_id: Optional[str] = None,
    ) -> Dict:
        """Publish one external resource (and its file).

        The file is sent to NADA in one request; ``nada_upload_id`` attaches a file already sent with NADA's
        resumable upload instead.
        """
        pid = self._pid(project_id)
        body: Dict[str, Any] = {"resource_id": int(resource_id), "overwrite": "yes" if overwrite else "no"}
        if nada_upload_id:
            body["nada_upload_id"] = nada_upload_id
        return self._api.post_request(
            pth=f"publish/external_resource/{pid}/{int(catalog_connection_id)}", json=body
        )

    def delete_nada_resources(self, project_id: ProjectIdOrIdno, catalog_connection_id: int) -> Dict:
        """Delete all external resources of the project's study in NADA."""
        pid = self._pid(project_id)
        return self._api.post_request(
            pth=f"publish/nada_resources_delete_all/{pid}/{int(catalog_connection_id)}", json={}
        )

    def list_files(self, project_id: ProjectIdOrIdno) -> Dict:
        """Files uploaded to the project's external resources: ``{files}``."""
        pid = self._pid(project_id)
        return self._api.get_request(pth=f"publish/files/{pid}")

    # ── all steps ─────────────────────────────────────────────────────────────

    def project(
        self,
        project_id: ProjectIdOrIdno,
        catalog_connection_id: int,
        *,
        publish_metadata: bool = True,
        publish_thumbnail: bool = True,
        publish_resources: bool = True,
        publish_dsd: bool = False,
        dsd_overwrite: bool = False,
        dsd_force: bool = False,
        publish_indicator_data: bool = False,
        delete_nada_resources: bool = False,
        options: Optional[Dict[str, Any]] = None,
        stop_on_error: bool = False,
        timeout: Optional[float] = None,
    ) -> Dict:
        """Publish a project to NADA now, step by step: the same steps as ``me.jobs.queue_publish_to_nada``.

        Steps, in order: metadata, data structure and indicator data (indicator projects), thumbnail,
        delete NADA resources, resources. A failed step is recorded and the next one runs, unless
        ``stop_on_error``. ``options`` are the NADA options for the metadata. Returns ``{"results", "errors"}``
        keyed by step.
        """
        project_id = self._pid(project_id)
        steps: List[Tuple[str, bool, Callable[[], Any]]] = [
            ("metadata", publish_metadata,
             lambda: self.metadata(project_id, catalog_connection_id, options=options)),
            ("dsd", publish_dsd,
             lambda: self.indicator_data(
                 project_id, catalog_connection_id, publish_dsd=True, dsd_overwrite=dsd_overwrite,
                 dsd_force=dsd_force, publish_indicator_data=False, timeout=timeout,
             ).get("dsd")),
            ("indicator_data", publish_indicator_data,
             lambda: self.indicator_data(
                 project_id, catalog_connection_id, publish_dsd=False, publish_indicator_data=True, timeout=timeout,
             ).get("data")),
            ("thumbnail", publish_thumbnail, lambda: self.thumbnail(project_id, catalog_connection_id)),
            ("nada_resources_delete", delete_nada_resources,
             lambda: self.delete_nada_resources(project_id, catalog_connection_id)),
            ("resources", publish_resources, lambda: self.resources(project_id, catalog_connection_id)),
        ]
        results: Dict[str, Any] = {}
        errors: Dict[str, str] = {}
        for name, enabled, run in steps:
            if not enabled:
                continue
            try:
                results[name] = run()
            except Exception as exc:  # noqa: BLE001 - reported per step, like the publish job
                errors[name] = str(exc)
                if stop_on_error:
                    break
        return {"results": results, "errors": errors}
