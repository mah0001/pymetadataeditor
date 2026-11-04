"""Background job queue wrappers for the Metadata Editor API."""

import time
from typing import Any, Dict, Optional, Union

from requests.exceptions import HTTPError

from .requester import RequestsWithSpecificErrors


def _normalize_project_id(project_id: Union[int, str], *, arg_name: str = "project_id") -> Union[int, str]:
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
    """Job queue wrappers (publish to NADA, poll status, list jobs)."""

    _TERMINAL_STATUSES = frozenset({"completed", "failed", "cancelled"})

    def __init__(self, api: RequestsWithSpecificErrors):
        self._api = api

    def available(self) -> bool:
        """Return True when ``GET /jobs/types`` is reachable on this server."""
        try:
            self.types()
            return True
        except HTTPError as exc:
            if _is_http_not_found(exc):
                return False
            raise

    def create(
        self,
        job_type: str,
        payload: Dict[str, Any],
        *,
        priority: int = 0,
        max_attempts: int = 3,
    ) -> Dict:
        """Queue ``POST /jobs`` with an explicit job type and payload."""
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

    def publish_to_nada(
        self,
        project_id: Union[int, str],
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
        priority: int = 0,
        max_attempts: int = 3,
    ) -> Dict:
        """Queue a publish-to-NADA job for a single project.

        Calls ``POST /jobs/publish_to_nada``.
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
        return self._api.post_request(pth="jobs/publish_to_nada", json=body)

    def import_indicator_data(
        self,
        project_id: Union[int, str],
        upload_id: str,
        indicator_value: str,
        *,
        delimiter: str = ",",
        priority: int = 0,
        max_attempts: int = 1,
    ) -> Dict:
        """Queue an indicator data import from a completed upload (``POST /jobs/import_indicator_data``).

        Imports the rows whose indicator_id column equals ``indicator_value``. Get ``upload_id`` from
        ``me.uploads.upload(path)``. Returns ``{status, uuid, job}``.
        """
        body: Dict[str, Any] = {
            "project_id": _normalize_project_id(project_id),
            "upload_id": str(upload_id),
            "indicator_value": str(indicator_value),
            "delimiter": delimiter,
            "priority": int(priority),
            "max_attempts": int(max_attempts),
        }
        return self._api.post_request(pth="jobs/import_indicator_data", json=body)

    def import_indicator_data_and_wait(
        self,
        project_id: Union[int, str],
        upload_id: str,
        indicator_value: str,
        *,
        timeout_seconds: int = 1800,
        interval_seconds: float = 5.0,
        show_progress: bool = False,
        **kwargs: Any,
    ) -> Dict:
        """Queue :meth:`import_indicator_data` and wait until the job finishes or times out."""
        submit = self.import_indicator_data(project_id, upload_id, indicator_value, **kwargs)
        job_uuid = submit.get("uuid") if isinstance(submit, dict) else None
        if not job_uuid:
            raise ValueError(f"import_indicator_data did not return a job uuid: {submit!r}")
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
        project_id: Optional[Union[int, str]] = None,
        user_id: Optional[int] = None,
        active: Optional[bool] = None,
        history: Optional[bool] = None,
        stale: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict:
        """List background jobs with optional filters."""
        params: Dict[str, Union[int, str]] = {
            "limit": int(limit),
            "offset": int(offset),
        }
        if status is not None:
            params["status"] = status
        if job_type is not None:
            params["job_type"] = job_type
        if project_id is not None:
            params["project_id"] = _normalize_project_id(project_id)
        if user_id is not None:
            params["user_id"] = int(user_id)
        if active is True:
            params["active"] = "1"
        if history is True:
            params["history"] = "1"
        if stale is True:
            params["stale"] = "1"
        return self._api.get_request(pth="jobs", params=params)

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

    def publish_to_nada_and_wait(
        self,
        project_id: Union[int, str],
        catalog_connection_id: int,
        *,
        timeout_seconds: int = 1800,
        interval_seconds: float = 5.0,
        show_progress: bool = False,
        **publish_kwargs: Any,
    ) -> Dict:
        """Submit ``publish_to_nada`` and block until the job completes or times out."""
        submit_response = self.publish_to_nada(
            project_id,
            catalog_connection_id,
            **publish_kwargs,
        )

        job_uuid = submit_response.get("uuid") if isinstance(submit_response, dict) else None
        if not job_uuid:
            raise ValueError(
                "publish_to_nada did not return a job uuid: "
                f"{submit_response!r}"
            )

        wait_result = self.wait(
            job_uuid,
            timeout_seconds=timeout_seconds,
            interval_seconds=interval_seconds,
            show_progress=show_progress,
        )
        wait_result["submit_response"] = submit_response
        return wait_result
