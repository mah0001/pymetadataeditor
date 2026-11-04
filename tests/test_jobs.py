"""Unit tests for JobsClient."""

from typing import Dict, Optional

import pytest
import requests

from pymetadataeditor import MetadataEditor
from pymetadataeditor.jobs import _normalize_project_id


class JobsMockResponse:
    def __init__(self, status_code: int, json_data: Optional[Dict] = None, text: str = ""):
        self.status_code = status_code
        self._json_data = json_data or {}
        self.text = text or str(json_data)

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError(f"{self.status_code} Error", response=self)

    def json(self) -> Dict:
        return self._json_data


@pytest.fixture
def jobs_editor(monkeypatch):
    calls = []

    def mock_request(method, url, **kwargs):
        calls.append({"method": method, "url": url, "kwargs": kwargs})
        if method.lower() == "post" and url.endswith("/jobs/publish_to_nada"):
            return JobsMockResponse(
                201,
                {
                    "status": "success",
                    "uuid": "job-uuid-1",
                    "job": {"uuid": "job-uuid-1", "status": "pending", "job_type": "publish_project"},
                },
            )
        if method.lower() == "post" and url.endswith("/jobs"):
            return JobsMockResponse(
                201,
                {
                    "status": "success",
                    "uuid": "job-uuid-fallback",
                    "job": {"uuid": "job-uuid-fallback", "status": "pending", "job_type": "publish_project"},
                },
            )
        if method.lower() == "get" and "/jobs/job-uuid-1" in url:
            return JobsMockResponse(
                200,
                {
                    "status": "success",
                    "job": {
                        "uuid": "job-uuid-1",
                        "status": "completed",
                        "job_type": "publish_project",
                        "result": {"project_id": 123},
                    },
                },
            )
        if method.lower() == "get" and url.endswith("/jobs"):
            return JobsMockResponse(
                200,
                {"status": "success", "total": 1, "found": 1, "jobs": [{"uuid": "job-uuid-1", "status": "completed"}]},
            )
        return JobsMockResponse(404, {"status": "failed", "message": "not found"})

    monkeypatch.setattr(requests, "request", mock_request)
    editor = MetadataEditor(api_url="https://example.com/index.php/api", api_key="test")  # pragma: allowlist secret
    editor._jobs_calls = calls  # type: ignore[attr-defined]
    return editor


def test_normalize_project_id():
    assert _normalize_project_id(123) == 123
    assert _normalize_project_id("456") == 456
    assert _normalize_project_id("MY-IDNO") == "MY-IDNO"
    with pytest.raises(ValueError):
        _normalize_project_id("")
    with pytest.raises(ValueError):
        _normalize_project_id("NA")


def test_publish_to_nada_payload(jobs_editor):
    response = jobs_editor.jobs.publish_to_nada(
        project_id="MY-IDNO",
        catalog_connection_id=2,
        publish_resources=False,
        options={"access_policy": "licensed", "published": 1},
    )
    assert response["uuid"] == "job-uuid-1"
    call = jobs_editor._jobs_calls[0]  # type: ignore[attr-defined]
    body = call["kwargs"]["json"]
    assert body["project_id"] == "MY-IDNO"
    assert body["catalog_connection_id"] == 2
    assert body["publish_resources"] is False
    assert body["options"]["access_policy"] == "licensed"


def test_get_job(jobs_editor):
    response = jobs_editor.jobs.get("job-uuid-1")
    assert response["job"]["status"] == "completed"


def test_list_jobs(jobs_editor):
    response = jobs_editor.jobs.list(job_type="publish_project", status="completed", limit=10)
    assert response["found"] == 1
    call = jobs_editor._jobs_calls[-1]  # type: ignore[attr-defined]
    assert call["kwargs"]["params"]["job_type"] == "publish_project"


def test_wait_until_complete(jobs_editor, monkeypatch):
    monkeypatch.setattr("pymetadataeditor.jobs.time.sleep", lambda _: None)
    result = jobs_editor.jobs.wait("job-uuid-1", interval_seconds=0.01)
    assert result["timed_out"] is False
    assert result["status"] == "completed"
    assert result["job"]["result"]["project_id"] == 123


def test_publish_to_nada_and_wait(jobs_editor, monkeypatch):
    monkeypatch.setattr("pymetadataeditor.jobs.time.sleep", lambda _: None)
    result = jobs_editor.jobs.publish_to_nada_and_wait(
        123,
        1,
        publish_resources=False,
        options={"access_policy": "open"},
    )
    assert result["status"] == "completed"
    assert result["submit_response"]["uuid"] == "job-uuid-1"

