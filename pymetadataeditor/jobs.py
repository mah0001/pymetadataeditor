"""Background job queue wrappers for the Metadata Editor API."""

import time
from typing import TYPE_CHECKING, Any, Dict, Iterator, Optional, Union

from requests.exceptions import HTTPError

from .api_types import ProjectIdOrIdno
from .paging import iter_offset_pages
from .requester import RequestsWithSpecificErrors

if TYPE_CHECKING:  # pragma: no cover
    from .projects import ProjectsClient


def _normalize_project_id(project_id: ProjectIdOrIdno, *, arg_name: str = "project_id") -> Union[int, str]:
    """Accept numeric id or idno string for job payloads."""
    if project_id is None:
        raise ValueError(f"{arg_name} is required")
    if isinstance(project_id, bool):
        raise ValueError(f"{arg_name} must be a numeric id or idno string")
    if isinstance(project_id, int):
        return project_id
    if isinstance(project_id, float):
        if not project_id.is_integer():
            raise ValueError(f"{arg_name} must be a finite integer project id")
        return int(project_id)

    text = str(project_id).strip()
    if not text or text.upper() == "NA":
        raise ValueError(f"{arg_name} is empty or invalid")
    if text.isdigit():
        return int(text)
    return text


def _is_http_not_found(exc: HTTPError) -> bool:
    response = getattr(exc, "response", None)
    return response is not None and response.status_code == 404


class JobsClient:
    """The editor's background job queue: queue jobs, poll their status, list jobs.

    Methods that start with ``queue_`` return as soon as the job is queued (``{status, uuid, job}``). Pass
    ``wait=True`` to block until the job finishes; the result is then that of :meth:`wait`.
    """

    _TERMINAL_STATUSES = frozenset({"completed", "failed", "cancelled"})
    #: Server maximum for ``limit`` on ``GET /jobs``.
    MAX_PAGE_SIZE = 100

    def __init__(self, api: RequestsWithSpecificErrors, projects: Optional["ProjectsClient"] = None):
        self._api = api
        self._projects = projects

    def available(self) -> bool:
        """Return True when ``GET /jobs/types`` is reachable on this server."""
        try:
            self.types()
            return True
        except HTTPError as exc:
            if _is_http_not_found(exc):
                return False
            raise

    def queue(
        self,
        job_type: str,
        payload: Dict[str, Any],
        *,
        priority: int = 0,
        max_attempts: int = 3,
    ) -> Dict:
        """Queue a job of any type (``POST /jobs``); see :meth:`types` for the job types."""
        return self._api.post_request(
            pth="jobs",
            json={
                "job_type": job_type,
                "payload": payload,
                "priority": int(priority),
                "max_attempts": int(max_attempts),
            },
        )

    def types(self) -> Dict:
        """List job types registered on the Metadata Editor instance."""
        return self._api.get_request(pth="jobs/types")

    def queue_publish_to_nada(
        self,
        project_id: ProjectIdOrIdno,
        catalog_connection_id: int,
        *,
        wait: bool = False,
        timeout_seconds: int = 1800,
        interval_seconds: float = 5.0,
        show_progress: bool = False,
        publish_metadata: bool = True,
        publish_thumbnail: bool = True,
        publish_resources: bool = True,
        publish_dsd: bool = False,
        dsd_overwrite: bool = False,
        dsd_force: bool = False,
        publish_indicator_data: bool = False,
        delete_nada_resources: bool = False,
        options: Optional[Dict[str, Any]] = None,
        priority: int = 0,
        max_attempts: int = 3,
    ) -> Dict:
        """Queue a publish-to-NADA job for a project (``POST /jobs/publish_to_nada``).

        Runs the same steps as :meth:`PublishClient.project`, on the server's worker. ``wait=True`` blocks
        until the job finishes (see :meth:`wait`).
        """
        body: Dict[str, Any] = {
            "project_id": _normalize_project_id(project_id),
            "catalog_connection_id": int(catalog_connection_id),
            "publish_metadata": bool(publish_metadata),
            "publish_thumbnail": bool(publish_thumbnail),
            "publish_resources": bool(publish_resources),
            "publish_dsd": bool(publish_dsd),
            "dsd_overwrite": bool(dsd_overwrite),
            "dsd_force": bool(dsd_force),
            "publish_indicator_data": bool(publish_indicator_data),
            "delete_nada_resources": bool(delete_nada_resources),
            "priority": int(priority),
            "max_attempts": int(max_attempts),
        }
        if options:
            body["options"] = options
        submit = self._api.post_request(pth="jobs/publish_to_nada", json=body)
        if not wait:
            return submit
        return self._wait_for_submitted(submit, timeout_seconds, interval_seconds, show_progress)

    def queue_indicator_data_import(
        self,
        project_id: ProjectIdOrIdno,
        upload_id: str,
        indicator_value: str,
        *,
        wait: bool = False,
        timeout_seconds: int = 1800,
        interval_seconds: float = 5.0,
        show_progress: bool = False,
        delimiter: str = ",",
        priority: int = 0,
        max_attempts: int = 1,
    ) -> Dict:
        """Queue an indicator data import from a completed upload (``POST /jobs/import_indicator_data``).

        Imports the rows whose indicator_id column equals ``indicator_value``. Get ``upload_id`` from
        ``me.uploads.upload(path)``. ``wait=True`` blocks until the job finishes (see :meth:`wait`).
        """
        body: Dict[str, Any] = {
            "project_id": _normalize_project_id(project_id),
            "upload_id": str(upload_id),
            "indicator_value": str(indicator_value),
            "delimiter": delimiter,
            "priority": int(priority),
            "max_attempts": int(max_attempts),
        }
        submit = self._api.post_request(pth="jobs/import_indicator_data", json=body)
        if not wait:
            return submit
        return self._wait_for_submitted(submit, timeout_seconds, interval_seconds, show_progress)

    def _wait_for_submitted(
        self, submit: Dict, timeout_seconds: int, interval_seconds: float, show_progress: bool
    ) -> Dict:
        """Wait for a job just queued; the result includes the queue response as ``submit_response``."""
        job_uuid = submit.get("uuid") if isinstance(submit, dict) else None
        if not job_uuid:
            raise ValueError(f"The server did not return a job uuid: {submit!r}")
        result = self.wait(
            job_uuid, timeout_seconds=timeout_seconds, interval_seconds=interval_seconds, show_progress=show_progress
        )
        result["submit_response"] = submit
        return result

    def get(self, job_uuid: str) -> Dict:
        """Get full job details including payload and result."""
        if not job_uuid or not str(job_uuid).strip():
            raise ValueError("job_uuid is required")
        return self._api.get_request(pth="jobs/{}", id=str(job_uuid).strip())

    def list(
        self,
        *,
        status: Optional[str] = None,
        job_type: Optional[str] = None,
        project_id: Optional[ProjectIdOrIdno] = None,
        user_id: Optional[int] = None,
        active: Optional[bool] = None,
        history: Optional[bool] = None,
        stale: Optional[bool] = None,
        created_from: Optional[str] = None,
        created_to: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict:
        """List one page of background jobs: ``{total, found, limit, offset, jobs, ...}``.

        ``limit`` is at most 100 (server maximum); use :meth:`iter_all` for more. ``created_from`` and
        ``created_to`` take ``YYYY-MM-DD`` or ``YYYY-MM-DD HH:MM:SS``. A ``project_id`` idno is resolved to the
        numeric id first. Non-admin users only see their own jobs.
        """
        if not 1 <= int(limit) <= self.MAX_PAGE_SIZE:
            raise ValueError(f"limit must be between 1 and {self.MAX_PAGE_SIZE}; use jobs.iter_all() for more")
        params: Dict[str, Union[int, str]] = {
            "limit": int(limit),
            "offset": int(offset),
        }
        if status is not None:
            params["status"] = status
        if job_type is not None:
            params["job_type"] = job_type
        if project_id is not None:
            pid = _normalize_project_id(project_id)
            if not isinstance(pid, int):
                if self._projects is None:
                    raise ValueError("jobs.list needs a numeric project id; use projects.resolve_id for an idno")
                pid = self._projects.resolve_id(pid)
            params["project_id"] = pid
        if user_id is not None:
            params["user_id"] = int(user_id)
        if active is True:
            params["active"] = "1"
        if history is True:
            params["history"] = "1"
        if stale is True:
            params["stale"] = "1"
        if created_from:
            params["created_from"] = created_from
        if created_to:
            params["created_to"] = created_to
        return self._api.get_request(pth="jobs", params=params)

    def iter_all(self, max_items: Optional[int] = None, **filters: Any) -> Iterator[Dict]:
        """Yield jobs one at a time, 100 per request (accepts the filters of :meth:`list`)."""
        return iter_offset_pages(
            lambda limit, offset: self.list(limit=limit, offset=offset, **filters),
            items_key="jobs",
            page_size=self.MAX_PAGE_SIZE,
            max_items=max_items,
            id_key="uuid",
        )

    def wait(
        self,
        job_uuid: str,
        *,
        timeout_seconds: int = 1800,
        interval_seconds: float = 5.0,
        show_progress: bool = False,
    ) -> Dict:
        """Poll ``GET /jobs/{uuid}`` until the job reaches a terminal state or times out."""
        if not job_uuid or not str(job_uuid).strip():
            raise ValueError("job_uuid is required")
        job_uuid = str(job_uuid).strip()
        deadline = time.monotonic() + timeout_seconds
        last_response: Optional[Dict] = None

        while True:
            last_response = self.get(job_uuid)
            job = last_response.get("job") if isinstance(last_response, dict) else None
            job_status = job.get("status") if isinstance(job, dict) else None

            if show_progress and job_status is not None:
                print(f"  Job {job_uuid} — status: {job_status}")

            if job_status in self._TERMINAL_STATUSES:
                return {
                    "uuid": job_uuid,
                    "status": job_status,
                    "timed_out": False,
                    "job": job,
                    "response": last_response,
                }

            if time.monotonic() >= deadline:
                return {
                    "uuid": job_uuid,
                    "status": job_status,
                    "timed_out": True,
                    "job": job,
                    "response": last_response,
                }

            time.sleep(interval_seconds)
