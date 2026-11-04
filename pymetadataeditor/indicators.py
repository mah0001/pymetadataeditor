"""Indicator project wrappers: data structure binding, data import/export, chart data and data notes."""

import json
import os
import tempfile
from typing import TYPE_CHECKING, Any, Dict, Iterable, List, Optional, Union
from urllib.parse import quote

from .requester import RequestsWithSpecificErrors

if TYPE_CHECKING:  # pragma: no cover
    import pandas as pd

    from .projects import ProjectsClient
    from .publish import PublishClient
    from .uploads import UploadsClient

ProjectRef = Union[int, str]

#: Files above this size are sent with a resumable upload instead of a single multipart request.
UPLOAD_THRESHOLD_BYTES = 20 * 1024 * 1024


def _seg(value: ProjectRef) -> str:
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

    def list(self, project: ProjectRef) -> Dict:
        """Footnote columns and all data notes: ``{footnote_columns, notes}``."""
        return self._api.get_request(pth=f"indicator_dsd/notes/{_seg(project)}")

    def import_csv(
        self,
        project: ProjectRef,
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
        pth = f"indicator_dsd/notes_import/{_seg(project)}"
        if upload_id is not None:
            return self._api.post_request(pth=pth, data={**form, "upload_id": upload_id})
        with open(csv_path, "rb") as handle:
            return self._api.post_request(pth=pth, data=form, files={"file": handle})

    def check(self, project: ProjectRef) -> Dict:
        """Check note IDs used in the data against the project notes: ``{valid, errors, warnings, ...}``."""
        return self._api.get_request(pth=f"indicator_dsd/notes_check/{_seg(project)}")

    def set(self, project: ProjectRef, notes: List[Dict[str, Any]], project_type: str = "indicator") -> Dict:
        """Replace all data notes of a project (list of ``{"id", "note", "scope"?, "column"?}``)."""
        clean = []
        for note in notes:
            if not note.get("id") or note.get("note") is None:
                raise ValueError(f"Each note needs an id and a note: {note!r}")
            if ";" in str(note["id"]):
                raise ValueError(f"Note id must not contain ';': {note['id']!r}")
            clean.append({k: v for k, v in note.items() if v is not None})
        return self._projects.patch(
            project, project_type, [{"op": "add", "path": "/data_notes", "value": clean}], validate=False
        )

    def add(
        self,
        project: ProjectRef,
        note_id: str,
        note: str,
        scope: Optional[str] = None,
        column: Optional[str] = None,
        project_type: str = "indicator",
    ) -> Dict:
        """Add or update one note (by ID)."""
        notes = [n for n in self.list(project).get("notes", []) if str(n.get("id")) != str(note_id)]
        entry: Dict[str, Any] = {"id": note_id, "note": note}
        if column:
            entry["column"] = column
        if scope and scope != "cell":
            entry["scope"] = scope
        return self.set(project, notes + [entry], project_type=project_type)

    def remove(self, project: ProjectRef, note_id: str, project_type: str = "indicator") -> Dict:
        """Remove one note (by ID)."""
        notes = [n for n in self.list(project).get("notes", []) if str(n.get("id")) != str(note_id)]
        return self.set(project, notes, project_type=project_type)


class IndicatorsClient:
    """Indicator projects: bind a registry data structure, import and export data, chart data, notes.

    ``project`` is a numeric project id or the project idno.
    """

    def __init__(
        self,
        api: RequestsWithSpecificErrors,
        projects: "ProjectsClient",
        uploads: "UploadsClient",
        publish: Optional["PublishClient"] = None,
    ):
        self._api = api
        self._projects = projects
        self._uploads = uploads
        self._publish = publish
        self.notes = IndicatorNotesClient(api, projects, uploads)

    def project_id(self, project: ProjectRef) -> int:
        """Numeric project id for an id or idno (publish endpoints need the numeric id)."""
        text = str(project).strip()
        if text.isdigit():
            return int(text)
        response = self._projects.get(text)
        pid = (response.get("project") or {}).get("id") if isinstance(response, dict) else None
        if pid is None:
            raise ValueError(f"Project not found: {project!r}")
        return int(pid)

    # ── data structure binding ────────────────────────────────────────────────

    def get_dsd(self, project: ProjectRef) -> Dict:
        """Columns of the project's data structure."""
        return self._api.get_request(pth=f"indicator_dsd/{_seg(project)}")

    def validate(self, project: ProjectRef) -> Dict:
        """Validate the data structure and data (includes the data notes checks)."""
        return self._api.get_request(pth=f"indicator_dsd/validate/{_seg(project)}")

    def binding(self, project: ProjectRef) -> Dict:
        """Current binding: data structure, indicator ID value, implied FREQ, data state."""
        return self._api.get_request(pth=f"indicator_dsd/binding/{_seg(project)}")

    def bind(
        self,
        project: ProjectRef,
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
        return self._api.post_request(pth=f"indicator_dsd/bind_global/{_seg(project)}", json=body)

    def update_binding(
        self, project: ProjectRef, indicator_id_value: Optional[str] = None, implied_freq_code: Optional[str] = None
    ) -> Dict:
        """Set the indicator ID value (rows imported from a CSV) and/or the series FREQ."""
        body: Dict[str, Any] = {}
        if indicator_id_value is not None:
            body["indicator_id_value"] = indicator_id_value
        if implied_freq_code is not None:
            body["implied_freq_code"] = implied_freq_code
        if not body:
            raise ValueError("Pass indicator_id_value and/or implied_freq_code")
        return self._api.post_request(pth=f"indicator_dsd/update_binding/{_seg(project)}", json=body)

    def unbind(self, project: ProjectRef) -> Dict:
        """Remove the data structure binding."""
        return self._api.post_request(pth=f"indicator_dsd/unbind/{_seg(project)}", json={})

    def reset(self, project: ProjectRef) -> Dict:
        """Drop the project's timeseries data (full reset)."""
        return self._api.post_request(pth=f"indicator_dsd/reset/{_seg(project)}", json={})

    # ── data import ───────────────────────────────────────────────────────────

    def prepare_data(
        self,
        project: ProjectRef,
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
        pth = f"indicator_dsd/data_upload_prepare/{_seg(project)}"
        if upload_id is not None:
            return self._api.post_request(pth=pth, data={**form, "upload_id": upload_id}, timeout=timeout)
        with open(csv_path, "rb") as handle:
            return self._api.post_request(pth=pth, data=form, files={"file": handle}, timeout=timeout)

    def import_data(
        self,
        project: ProjectRef,
        wait: bool = True,
        keep_extra_csv_columns: bool = False,
        implied_freq_code: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> Dict:
        """Import the prepared CSV for the bound indicator ID value (replaces the project's data).

        The result includes ``data_notes``: notes read from text columns, generated note IDs and the
        reference checks.
        """
        body: Dict[str, Any] = {"wait": bool(wait), "keep_extra_csv_columns": bool(keep_extra_csv_columns)}
        if implied_freq_code:
            body["implied_freq_code"] = implied_freq_code
        return self._api.post_request(
            pth=f"indicator_dsd/data_upload_import/{_seg(project)}", json=body, timeout=timeout
        )

    # ── data access ───────────────────────────────────────────────────────────

    def data_rows(
        self, project: ProjectRef, offset: int = 0, limit: int = 50, filters: Optional[Dict[str, List[str]]] = None
    ) -> Dict:
        """A page of imported rows (``filters``: column → list of values)."""
        params: Dict[str, Union[int, str]] = {"offset": offset, "limit": limit}
        if filters:
            params["filters"] = json.dumps(filters)
        return self._api.get_request(pth=f"indicator_dsd/data_rows/{_seg(project)}", params=params)

    def data_values(
        self, project: ProjectRef, code_column: str, label_column: Optional[str] = None, limit: int = 5000
    ) -> Dict:
        """Distinct values (and labels) of a column in the imported data."""
        params: Dict[str, Union[int, str]] = {"code_column": code_column, "limit": limit}
        if label_column:
            params["label_column"] = label_column
        return self._api.get_request(pth=f"indicator_dsd/data_values/{_seg(project)}", params=params)

    def export_data(self, project: ProjectRef, out_path: str, timeout: Optional[float] = None) -> str:
        """Download the imported data as CSV (DSD columns, in DSD order) to ``out_path``."""
        response = self._api.get_request(pth=f"indicator_dsd/data_export/{_seg(project)}", raw=True, timeout=timeout)
        return _save(response, out_path)

    def delete_data(self, project: ProjectRef) -> Dict:
        """Delete the project's imported data."""
        return self._api.post_request(pth=f"indicator_dsd/data_delete/{_seg(project)}", json={})

    def recompute(self, project: ProjectRef) -> Dict:
        """Recompute derived time columns (after changing FREQ or time format)."""
        return self._api.post_request(pth=f"indicator_dsd/data_recompute/{_seg(project)}", json={})

    def job(self, project: ProjectRef, job_id: str) -> Dict:
        """Status of a data job (import without ``wait``, recompute)."""
        return self._api.get_request(pth=f"indicator_dsd/job/{_seg(project)}", params={"job_id": job_id})

    def chart_data(
        self,
        project: ProjectRef,
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
        return self._api.post_request(pth=f"indicator_dsd/chart_data/{_seg(project)}", json=body)

    # ── workflow helpers ──────────────────────────────────────────────────────

    def load_csv(
        self,
        project: ProjectRef,
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
            report["binding"] = self.bind(project, data_structure_id, data_structure_reference)
        if indicator_id_value is not None or implied_freq_code is not None:
            report["binding"] = self.update_binding(project, indicator_id_value, implied_freq_code)
        report["prepare"] = self.prepare_data(
            project, csv_path=csv_path, delimiter=delimiter, keep_extra_csv_columns=keep_extra_csv_columns,
            timeout=timeout,
        )
        if indicator_id_value is not None:
            found = [str(v.get("value")) for v in report["prepare"].get("indicator_values", []) or []]
            if found and str(indicator_id_value) not in found:
                raise ValueError(
                    f"Indicator ID {indicator_id_value!r} not found in {csv_path} (found: {', '.join(found[:20])})"
                )
        report["import"] = self.import_data(
            project, wait=True, keep_extra_csv_columns=keep_extra_csv_columns, timeout=timeout
        )
        if notes_csv:
            report["notes_import"] = self.notes.import_csv(project, csv_path=notes_csv, delimiter=delimiter)
        report["notes_check"] = self.notes.check(project)
        return report

    def load_dataframe(self, project: ProjectRef, df: "pd.DataFrame", **kwargs: Any) -> Dict:
        """Write a DataFrame to a temporary UTF-8 CSV and call :meth:`load_csv` with it."""
        handle = tempfile.NamedTemporaryFile(prefix="indicator_", suffix=".csv", delete=False)
        handle.close()
        try:
            df.to_csv(handle.name, index=False, encoding="utf-8")
            return self.load_csv(project, handle.name, **kwargs)
        finally:
            os.unlink(handle.name)

    def load_many(
        self,
        csv_path: str,
        projects: Dict[str, ProjectRef],
        notes_csv: Optional[str] = None,
        stop_on_error: bool = False,
        **kwargs: Any,
    ) -> List[Dict]:
        """Load one CSV holding several indicators into several projects (``{indicator_id: project}``).

        Returns one row per indicator: ``{indicator_id, project, status, rows, notes_errors, error}``.
        """
        results = []
        for indicator_id, project in projects.items():
            row: Dict[str, Any] = {"indicator_id": indicator_id, "project": project, "status": "ok", "rows": None,
                                   "notes_errors": None, "error": None}
            try:
                report = self.load_csv(project, csv_path, indicator_id_value=indicator_id, notes_csv=notes_csv,
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

    def publish(
        self,
        project: ProjectRef,
        catalog_connection_id: int,
        publish_metadata: bool = True,
        publish_dsd: bool = True,
        dsd_overwrite: bool = True,
        dsd_force: bool = False,
        publish_indicator_data: bool = True,
        metadata_options: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> Dict:
        """Publish an indicator project to NADA: metadata, data structure, then data.

        The data structure is re-imported only when it differs from NADA's copy (``dsd_force`` re-imports
        anyway). ``metadata_options`` are the NADA options (``published``, ``access_policy``,
        ``repositoryid``, ``overwrite``). Returns ``{"metadata", "dsd", "data"}``.
        """
        if self._publish is None:
            raise RuntimeError("IndicatorsClient was created without a PublishClient")
        project = self.project_id(project)
        out: Dict[str, Any] = {"metadata": None, "dsd": None, "data": None}
        if publish_metadata:
            options = {"overwrite": "yes", **(metadata_options or {})}
            out["metadata"] = self._publish.metadata(project, catalog_connection_id, options=options)
        if publish_dsd:
            out["dsd"] = self._publish.indicator(
                project, catalog_connection_id, publish_dsd=True, dsd_overwrite=dsd_overwrite, dsd_force=dsd_force,
                publish_indicator_data=False, timeout=timeout,
            ).get("dsd")
        if publish_indicator_data:
            out["data"] = self._publish.indicator(
                project, catalog_connection_id, publish_dsd=False, publish_indicator_data=True, timeout=timeout,
            ).get("data")
        return out
