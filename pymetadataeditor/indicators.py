"""Indicator project wrappers: data structure binding, data import/export, chart data and data notes."""

import json
import os
import tempfile
import time
from typing import TYPE_CHECKING, Any, Dict, Iterable, Iterator, List, Optional, Union
from urllib.parse import quote

from .api_types import ProjectIdOrIdno
from .paging import iter_offset_pages
from .requester import RequestsWithSpecificErrors

if TYPE_CHECKING:  # pragma: no cover
    import pandas as pd

    from .projects import ProjectsClient
    from .uploads import UploadsClient

#: Files above this size are sent with a resumable upload instead of a single multipart request.
UPLOAD_THRESHOLD_BYTES = 20 * 1024 * 1024
#: Server maximum for ``limit`` on ``GET indicator_dsd/data_rows``.
DATA_ROWS_MAX_PAGE_SIZE = 200


def _seg(value: ProjectIdOrIdno) -> str:
    """URL path segment for a project id or idno."""
    return quote(str(value).strip(), safe="")


def _save(response, out_path: str) -> str:
    with open(out_path, "wb") as handle:
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            handle.write(chunk)
    return out_path


class IndicatorNotesClient:
    """Data notes of an indicator project.

    The data holds note IDs in footnote columns (DSD components with ``display_role="footnote"``,
    several IDs separated by ``;``). The note text is stored once per note in the project metadata
    ``data_notes``: ``{"id", "note", "scope"?: "cell"|"table", "column"?}``. Table notes
    (``scope="table"``) apply to the whole indicator.
    """

    def __init__(self, api: RequestsWithSpecificErrors, projects: "ProjectsClient", uploads: "UploadsClient"):
        self._api = api
        self._projects = projects
        self._uploads = uploads

    def list(self, project_id: ProjectIdOrIdno) -> Dict:
        """Footnote columns and all data notes: ``{footnote_columns, notes}``."""
        return self._api.get_request(pth=f"indicator_dsd/notes/{_seg(project_id)}")

    def import_csv(
        self,
        project_id: ProjectIdOrIdno,
        csv_path: Optional[str] = None,
        upload_id: Optional[str] = None,
        dry_run: bool = False,
        replace: bool = False,
        delimiter: str = ",",
    ) -> Dict:
        """Import notes from a CSV with columns ``note_id, note`` (optional ``indicator_id, scope, column``).

        Rows for other indicators are skipped; notes are added or updated by ID (``replace=True`` also
        removes notes not in the file). Returns ``{summary, notes_count, checks}``.
        """
        if (csv_path is None) == (upload_id is None):
            raise ValueError("Pass exactly one of csv_path or upload_id")
        form = {"dry_run": "1" if dry_run else "0", "replace": "1" if replace else "0", "delimiter": delimiter}
        pth = f"indicator_dsd/notes_import/{_seg(project_id)}"
        if upload_id is not None:
            return self._api.post_request(pth=pth, data={**form, "upload_id": upload_id})
        with open(csv_path, "rb") as handle:
            return self._api.post_request(pth=pth, data=form, files={"file": handle})

    def check(self, project_id: ProjectIdOrIdno) -> Dict:
        """Check note IDs used in the data against the project notes: ``{valid, errors, warnings, ...}``."""
        return self._api.get_request(pth=f"indicator_dsd/notes_check/{_seg(project_id)}")

    def set(self, project_id: ProjectIdOrIdno, notes: List[Dict[str, Any]], project_type: str = "indicator") -> Dict:
        """Replace all data notes of a project (list of ``{"id", "note", "scope"?, "column"?}``)."""
        clean = []
        for note in notes:
            if not note.get("id") or note.get("note") is None:
                raise ValueError(f"Each note needs an id and a note: {note!r}")
            if ";" in str(note["id"]):
                raise ValueError(f"Note id must not contain ';': {note['id']!r}")
            clean.append({k: v for k, v in note.items() if v is not None})
        return self._projects.patch(
            project_id, project_type, [{"op": "add", "path": "/data_notes", "value": clean}], validate=False
        )

    def add(
        self,
        project_id: ProjectIdOrIdno,
        note_id: str,
        note: str,
        scope: Optional[str] = None,
        column: Optional[str] = None,
        project_type: str = "indicator",
    ) -> Dict:
        """Add or update one note (by ID)."""
        notes = [n for n in self.list(project_id).get("notes", []) if str(n.get("id")) != str(note_id)]
        entry: Dict[str, Any] = {"id": note_id, "note": note}
        if column:
            entry["column"] = column
        if scope and scope != "cell":
            entry["scope"] = scope
        return self.set(project_id, notes + [entry], project_type=project_type)

    def remove(self, project_id: ProjectIdOrIdno, note_id: str, project_type: str = "indicator") -> Dict:
        """Remove one note (by ID)."""
        notes = [n for n in self.list(project_id).get("notes", []) if str(n.get("id")) != str(note_id)]
        return self.set(project_id, notes, project_type=project_type)


class IndicatorsClient:
    """Indicator projects: bind a registry data structure, import and export data, chart data, notes.

    ``project_id`` is the numeric project id or the project idno.
    """

    def __init__(
        self,
        api: RequestsWithSpecificErrors,
        projects: "ProjectsClient",
        uploads: "UploadsClient",
    ):
        self._api = api
        self._projects = projects
        self._uploads = uploads
        self.notes = IndicatorNotesClient(api, projects, uploads)

    # ── data structure binding ────────────────────────────────────────────────

    def get_dsd(self, project_id: ProjectIdOrIdno, detailed: bool = False, resolve_codelists: bool = False) -> Dict:
        """Columns of the project's data structure: ``{columns}``.

        ``detailed=True`` adds full column metadata; ``resolve_codelists=True`` adds the codes of each column.
        """
        params: Dict[str, int] = {}
        if detailed:
            params["detailed"] = 1
        if resolve_codelists:
            params["resolve_codelists"] = 1
        return self._api.get_request(pth=f"indicator_dsd/{_seg(project_id)}", params=params or None)

    def validate(self, project_id: ProjectIdOrIdno) -> Dict:
        """Validate the data structure and data (includes the data notes checks)."""
        return self._api.get_request(pth=f"indicator_dsd/validate/{_seg(project_id)}")

    def binding(self, project_id: ProjectIdOrIdno) -> Dict:
        """Current binding: data structure, indicator ID value, implied FREQ, data state."""
        return self._api.get_request(pth=f"indicator_dsd/binding/{_seg(project_id)}")

    def bind(
        self,
        project_id: ProjectIdOrIdno,
        data_structure_id: Optional[int] = None,
        data_structure_reference: Optional[Union[str, Dict[str, str]]] = None,
    ) -> Dict:
        """Bind a registry data structure to the project (by id, or by idno / {agency, name, version})."""
        if (data_structure_id is None) == (data_structure_reference is None):
            raise ValueError("Pass exactly one of data_structure_id or data_structure_reference")
        if data_structure_id is not None:
            body: Dict[str, Any] = {"data_structure_id": int(data_structure_id)}
        else:
            ref = data_structure_reference
            body = {"data_structure_reference": {"idno": ref} if isinstance(ref, str) else ref}
        return self._api.post_request(pth=f"indicator_dsd/bind_global/{_seg(project_id)}", json=body)

    def update_binding(
        self,
        project_id: ProjectIdOrIdno,
        indicator_id_value: Optional[str] = None,
        implied_freq_code: Optional[str] = None,
    ) -> Dict:
        """Set the indicator ID value (rows imported from a CSV) and/or the series FREQ."""
        body: Dict[str, Any] = {}
        if indicator_id_value is not None:
            body["indicator_id_value"] = indicator_id_value
        if implied_freq_code is not None:
            body["implied_freq_code"] = implied_freq_code
        if not body:
            raise ValueError("Pass indicator_id_value and/or implied_freq_code")
        return self._api.post_request(pth=f"indicator_dsd/update_binding/{_seg(project_id)}", json=body)

    def unbind(self, project_id: ProjectIdOrIdno) -> Dict:
        """Remove the data structure binding."""
        return self._api.post_request(pth=f"indicator_dsd/unbind/{_seg(project_id)}", json={})

    def reset(self, project_id: ProjectIdOrIdno) -> Dict:
        """Drop the project's timeseries data (full reset)."""
        return self._api.post_request(pth=f"indicator_dsd/reset/{_seg(project_id)}", json={})

    # ── data import ───────────────────────────────────────────────────────────

    def prepare_data(
        self,
        project_id: ProjectIdOrIdno,
        csv_path: Optional[str] = None,
        upload_id: Optional[str] = None,
        delimiter: str = ",",
        keep_extra_csv_columns: bool = False,
        timeout: Optional[float] = None,
    ) -> Dict:
        """Upload a data CSV and check it against the data structure.

        Returns the header check, the distinct indicator ID values, and ignored columns. Large files
        are sent with a resumable upload automatically.
        """
        if (csv_path is None) == (upload_id is None):
            raise ValueError("Pass exactly one of csv_path or upload_id")
        if csv_path is not None and os.path.getsize(csv_path) > UPLOAD_THRESHOLD_BYTES:
            upload_id = self._uploads.upload(csv_path, timeout=timeout)
            csv_path = None
        form = {"delimiter": delimiter, "keep_extra_csv_columns": "1" if keep_extra_csv_columns else "0"}
        pth = f"indicator_dsd/data_upload_prepare/{_seg(project_id)}"
        if upload_id is not None:
            return self._api.post_request(pth=pth, data={**form, "upload_id": upload_id}, timeout=timeout)
        with open(csv_path, "rb") as handle:
            return self._api.post_request(pth=pth, data=form, files={"file": handle}, timeout=timeout)

    def import_data(
        self,
        project_id: ProjectIdOrIdno,
        wait: bool = True,
        keep_extra_csv_columns: bool = False,
        implied_freq_code: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> Dict:
        """Import the prepared CSV for the bound indicator ID value (replaces the project's data).

        The import runs as a data job. With ``wait=True`` the server waits for it (up to 30 minutes); with
        ``wait=False`` the result has a ``job_id`` for :meth:`get_data_job` / :meth:`wait_data_job`. The result
        includes ``data_notes``: notes read from text columns, generated note IDs and the reference checks.
        """
        body: Dict[str, Any] = {"wait": bool(wait), "keep_extra_csv_columns": bool(keep_extra_csv_columns)}
        if implied_freq_code:
            body["implied_freq_code"] = implied_freq_code
        return self._api.post_request(
            pth=f"indicator_dsd/data_upload_import/{_seg(project_id)}", json=body, timeout=timeout
        )

    # ── data access ───────────────────────────────────────────────────────────

    def data_rows(
        self,
        project_id: ProjectIdOrIdno,
        offset: int = 0,
        limit: int = 50,
        filters: Optional[Dict[str, List[str]]] = None,
    ) -> Dict:
        """A page of imported rows (``filters``: column → list of values). ``limit`` is at most 200.

        Use :meth:`iter_data_rows` to read more, or :meth:`export_data` to download everything as CSV.
        """
        if not 1 <= int(limit) <= DATA_ROWS_MAX_PAGE_SIZE:
            raise ValueError(f"limit must be between 1 and {DATA_ROWS_MAX_PAGE_SIZE}")
        params: Dict[str, Union[int, str]] = {"offset": offset, "limit": limit}
        if filters:
            params["filters"] = json.dumps(filters)
        return self._api.get_request(pth=f"indicator_dsd/data_rows/{_seg(project_id)}", params=params)

    def iter_data_rows(
        self,
        project_id: ProjectIdOrIdno,
        filters: Optional[Dict[str, List[str]]] = None,
        max_items: Optional[int] = None,
    ) -> Iterator[Dict]:
        """Yield imported rows one at a time, 200 per request."""
        def fetch(limit: int, offset: int) -> Dict:
            return self.data_rows(project_id, offset=offset, limit=limit, filters=filters).get("data") or {}

        return iter_offset_pages(
            fetch,
            items_key="rows",
            page_size=DATA_ROWS_MAX_PAGE_SIZE,
            max_items=max_items,
            id_key=None,
            total_key="total_row_count",
        )

    def data_values(
        self, project_id: ProjectIdOrIdno, code_column: str, label_column: Optional[str] = None, limit: int = 5000
    ) -> Dict:
        """Distinct values (and labels) of a column in the imported data."""
        params: Dict[str, Union[int, str]] = {"code_column": code_column, "limit": limit}
        if label_column:
            params["label_column"] = label_column
        return self._api.get_request(pth=f"indicator_dsd/data_values/{_seg(project_id)}", params=params)

    def export_data(self, project_id: ProjectIdOrIdno, out_path: str, timeout: Optional[float] = None) -> str:
        """Download the imported data as CSV (DSD columns, in DSD order) to ``out_path``."""
        response = self._api.get_request(pth=f"indicator_dsd/data_export/{_seg(project_id)}", raw=True, timeout=timeout)
        return _save(response, out_path)

    def delete_data(self, project_id: ProjectIdOrIdno) -> Dict:
        """Delete the project's imported data."""
        return self._api.post_request(pth=f"indicator_dsd/data_delete/{_seg(project_id)}", json={})

    # ── data jobs ─────────────────────────────────────────────────────────────
    # Data jobs run in the data service, not the editor job queue (``me.jobs``); they are keyed by ``job_id``.

    def queue_recompute(
        self,
        project_id: ProjectIdOrIdno,
        wait: bool = False,
        timeout_seconds: int = 1800,
        interval_seconds: float = 3.0,
    ) -> Dict:
        """Queue a recompute of the derived time columns (after changing FREQ or time format).

        Returns ``{job_id, ...}``; ``wait=True`` returns the finished job (see :meth:`wait_data_job`).
        """
        submit = self._api.post_request(pth=f"indicator_dsd/data_recompute/{_seg(project_id)}", json={})
        if not wait:
            return submit
        job_id = submit.get("job_id") if isinstance(submit, dict) else None
        if not job_id:
            raise ValueError(f"The server did not return a job_id: {submit!r}")
        return self.wait_data_job(
            project_id, job_id, timeout_seconds=timeout_seconds, interval_seconds=interval_seconds
        )

    def get_data_job(self, project_id: ProjectIdOrIdno, job_id: str) -> Dict:
        """Status of a data job (import without ``wait``, recompute): ``{status, job, ...}``."""
        return self._api.get_request(pth=f"indicator_dsd/job/{_seg(project_id)}", params={"job_id": job_id})

    def wait_data_job(
        self,
        project_id: ProjectIdOrIdno,
        job_id: str,
        timeout_seconds: int = 1800,
        interval_seconds: float = 3.0,
    ) -> Dict:
        """Poll :meth:`get_data_job` until the job is ``done`` or ``error``, or the timeout passes.

        Returns ``{job_id, status, timed_out, job}``.
        """
        deadline = time.monotonic() + timeout_seconds
        while True:
            job = self.get_data_job(project_id, job_id).get("job") or {}
            status = job.get("status") if isinstance(job, dict) else None
            if status in ("done", "error"):
                return {"job_id": job_id, "status": status, "timed_out": False, "job": job}
            if time.monotonic() >= deadline:
                return {"job_id": job_id, "status": status, "timed_out": True, "job": job}
            time.sleep(interval_seconds)

    def chart_data(
        self,
        project_id: ProjectIdOrIdno,
        geography: Optional[Iterable[str]] = None,
        dimensions: Optional[Dict[str, List[str]]] = None,
        time_period_start: Optional[str] = None,
        time_period_end: Optional[str] = None,
    ) -> Dict:
        """Chart records for a selection, with note IDs per record, the note text used, and table notes."""
        body: Dict[str, Any] = {}
        if geography:
            body["geography"] = list(geography)
        if dimensions:
            body["dimensions"] = dimensions
        if time_period_start:
            body["time_period_start"] = time_period_start
        if time_period_end:
            body["time_period_end"] = time_period_end
        return self._api.post_request(pth=f"indicator_dsd/chart_data/{_seg(project_id)}", json=body)

    # ── workflow helpers ──────────────────────────────────────────────────────

    def load_csv(
        self,
        project_id: ProjectIdOrIdno,
        csv_path: str,
        indicator_id_value: Optional[str] = None,
        data_structure_id: Optional[int] = None,
        data_structure_reference: Optional[Union[str, Dict[str, str]]] = None,
        notes_csv: Optional[str] = None,
        implied_freq_code: Optional[str] = None,
        keep_extra_csv_columns: bool = False,
        delimiter: str = ",",
        timeout: Optional[float] = None,
    ) -> Dict:
        """Load a data CSV into an indicator project in one call.

        Steps: bind the data structure (if given), set the indicator ID value (if given), prepare and
        import the data, then import the notes CSV (if given) and check the note references.

        Returns ``{"binding", "prepare", "import", "notes_import", "notes_check"}`` (missing steps are None).
        """
        report: Dict[str, Any] = {"binding": None, "prepare": None, "import": None, "notes_import": None,
                                  "notes_check": None}
        if data_structure_id is not None or data_structure_reference is not None:
            report["binding"] = self.bind(project_id, data_structure_id, data_structure_reference)
        if indicator_id_value is not None or implied_freq_code is not None:
            report["binding"] = self.update_binding(project_id, indicator_id_value, implied_freq_code)
        report["prepare"] = self.prepare_data(
            project_id, csv_path=csv_path, delimiter=delimiter, keep_extra_csv_columns=keep_extra_csv_columns,
            timeout=timeout,
        )
        if indicator_id_value is not None:
            found = [str(v.get("value")) for v in report["prepare"].get("indicator_values", []) or []]
            if found and str(indicator_id_value) not in found:
                raise ValueError(
                    f"Indicator ID {indicator_id_value!r} not found in {csv_path} (found: {', '.join(found[:20])})"
                )
        report["import"] = self.import_data(
            project_id, wait=True, keep_extra_csv_columns=keep_extra_csv_columns, timeout=timeout
        )
        if notes_csv:
            report["notes_import"] = self.notes.import_csv(project_id, csv_path=notes_csv, delimiter=delimiter)
        report["notes_check"] = self.notes.check(project_id)
        return report

    def load_dataframe(self, project_id: ProjectIdOrIdno, df: "pd.DataFrame", **kwargs: Any) -> Dict:
        """Write a DataFrame to a temporary UTF-8 CSV and call :meth:`load_csv` with it."""
        handle = tempfile.NamedTemporaryFile(prefix="indicator_", suffix=".csv", delete=False)
        handle.close()
        try:
            df.to_csv(handle.name, index=False, encoding="utf-8")
            return self.load_csv(project_id, handle.name, **kwargs)
        finally:
            os.unlink(handle.name)

    def load_many(
        self,
        csv_path: str,
        projects: Dict[str, ProjectIdOrIdno],
        notes_csv: Optional[str] = None,
        stop_on_error: bool = False,
        **kwargs: Any,
    ) -> List[Dict]:
        """Load one CSV holding several indicators into several projects (``{indicator_id: project_id}``).

        Returns one row per indicator: ``{indicator_id, project_id, status, rows, notes_errors, error}``.
        """
        results = []
        for indicator_id, project_id in projects.items():
            row: Dict[str, Any] = {"indicator_id": indicator_id, "project_id": project_id, "status": "ok", "rows": None,
                                   "notes_errors": None, "error": None}
            try:
                report = self.load_csv(project_id, csv_path, indicator_id_value=indicator_id, notes_csv=notes_csv,
                                       **kwargs)
                job = (report.get("import") or {}).get("job") or {}
                row["rows"] = (job.get("result") or {}).get("row_count") if isinstance(job, dict) else None
                row["notes_errors"] = len((report.get("notes_check") or {}).get("errors") or [])
            except Exception as exc:  # noqa: BLE001 - reported per indicator
                row["status"] = "failed"
                row["error"] = str(exc)
                if stop_on_error:
                    results.append(row)
                    raise
            results.append(row)
        return results
