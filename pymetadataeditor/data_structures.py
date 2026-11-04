"""Data structure (DSD) registry wrappers for the Metadata Editor API."""

import csv
import json
from typing import Any, Dict, Iterable, List, Optional, Union
from urllib.parse import quote

from .requester import RequestsWithSpecificErrors

ComponentSpec = Dict[str, Any]

#: Column roles guessed from common SDMX-style column names (override with ``roles``).
DEFAULT_ROLES = {
    "INDICATOR_ID": "indicator_id",
    "INDICATOR_NAME": "indicator_name",
    "TIME_PERIOD": "time_period",
    "OBS_VALUE": "observation_value",
    "REF_AREA": "geography",
    "FREQ": "periodicity",
}

REQUIRED_ROLES = ("indicator_id", "time_period", "observation_value")

#: Roles that can carry a codelist built from a code/label column pair.
_CODELIST_ROLES = ("indicator_id", "geography", "dimension", "periodicity", "measure", "attribute")


def components_from_csv(
    csv_path: str,
    roles: Optional[Dict[str, str]] = None,
    footnote_columns: Iterable[str] = (),
    label_suffix: str = "_LABEL",
    label_columns: str = "codelist",
    delimiter: str = ",",
) -> List[ComponentSpec]:
    """Build the ``components`` payload for :meth:`DataStructuresClient.import_components_csv` from a CSV header.

    - Roles: ``roles`` (column -> column_type), else :data:`DEFAULT_ROLES`, else ``dimension`` when the column
      has a label column, else ``attribute``.
    - ``X`` + ``X<label_suffix>``: a codelist built from the pair (``mode: from_csv``).
    - ``footnote_columns``: annotation columns with ``display_role="footnote"`` (note IDs), no codelist.
    - Label columns: ``"codelist"`` uses them only to build the codelist; ``"attribute"`` also keeps them as
      attribute columns right after their code column (labels stored with the data).

    Raises ValueError when a required role (indicator_id, time_period, observation_value) is missing.
    """
    if label_columns not in ("codelist", "attribute"):
        raise ValueError("label_columns must be 'codelist' or 'attribute'")
    with open(csv_path, newline="", encoding="utf-8-sig") as handle:
        header = next(csv.reader(handle, delimiter=delimiter))
    header = [h.strip() for h in header if h.strip()]
    present = {h.upper(): h for h in header}
    roles_upper = {k.upper(): v for k, v in (roles or {}).items()}
    footnotes = {c.upper() for c in footnote_columns}
    suffix = label_suffix.upper()

    def label_of(col: str) -> Optional[str]:
        return present.get(col.upper() + suffix)

    components: List[ComponentSpec] = []
    for col in header:
        up = col.upper()
        if up.endswith(suffix) and up[: -len(suffix)] in present:
            continue  # label column: handled with its code column
        if up in footnotes:
            components.append({"name": col, "column_type": roles_upper.get(up, "annotation"), "csv_column": col,
                               "display_role": "footnote"})
            continue
        role = roles_upper.get(up) or DEFAULT_ROLES.get(up) or ("dimension" if label_of(col) else "attribute")
        comp: ComponentSpec = {"name": col, "column_type": role, "csv_column": col}
        label_col = label_of(col)
        if label_col and role in _CODELIST_ROLES:
            comp["codelist"] = {"mode": "from_csv", "code_column": col, "label_column": label_col}
        components.append(comp)
        if label_col and label_columns == "attribute":
            components.append({"name": label_col, "column_type": "attribute", "csv_column": label_col})

    found = {c["column_type"] for c in components}
    missing = [r for r in REQUIRED_ROLES if r not in found]
    if missing:
        raise ValueError(f"No column for required role(s): {', '.join(missing)}. Pass roles={{column: role}}.")
    return components


def _seg(value: Union[int, str]) -> str:
    """URL path segment for an id or idno."""
    return quote(str(value).strip(), safe="")


class DataStructuresClient:
    """Global data structure registry: DSDs, their components, import and export.

    A DSD describes the columns of indicator data. Each component has a ``column_type``
    (indicator_id, time_period, observation_value, geography, dimension, periodicity, measure,
    attribute, annotation, indicator_name), optionally a codelist, and metadata such as
    ``display_role`` (``"footnote"``: the column holds note IDs).
    """

    def __init__(self, api: RequestsWithSpecificErrors):
        self._api = api

    # ── structures ────────────────────────────────────────────────────────────

    def list(
        self, search: Optional[str] = None, status: Optional[str] = None, page: int = 1, per_page: int = 50
    ) -> Dict:
        """List data structures (paged)."""
        params: Dict[str, Union[int, str]] = {"page": page, "per_page": per_page}
        if search:
            params["search"] = search
        if status:
            params["status"] = status
        return self._api.get_request(pth="data_structures", params=params)

    def get(self, structure: Union[int, str], with_components: bool = True) -> Dict:
        """Get a data structure by id, with its components."""
        return self._api.get_request(
            pth=f"data_structures/single/{_seg(structure)}", params={"with_components": int(bool(with_components))}
        )

    def get_by_identity(self, agency: str, name: str, version: Optional[str] = None) -> Dict:
        """Get a data structure by agency, name and (optionally) version."""
        params = {"agency": agency, "name": name}
        if version:
            params["version"] = version
        return self._api.get_request(pth="data_structures/by_identity", params=params)

    def lookup(self, idno_or_id: Union[int, str], with_components: bool = True) -> Dict:
        """Get a data structure by idno or id."""
        return self._api.get_request(
            pth=f"data_structures/lookup/{_seg(idno_or_id)}", params={"with_components": int(bool(with_components))}
        )

    def create(
        self,
        name: str,
        agency: Optional[str] = None,
        version: Optional[str] = None,
        title: Optional[str] = None,
        description: Optional[str] = None,
        **fields: Any,
    ) -> Dict:
        """Create an (empty) data structure. Returns ``{status, id, data_structure}``."""
        body: Dict[str, Any] = {"name": name, **fields}
        for key, value in (("agency", agency), ("version", version), ("title", title), ("description", description)):
            if value is not None:
                body[key] = value
        return self._api.post_request(pth="data_structures/create", json=body)

    def update(self, structure_id: int, **fields: Any) -> Dict:
        """Update structure fields (title, description, status, ...)."""
        return self._api.post_request(pth=f"data_structures/update/{int(structure_id)}", json=fields)

    def delete(self, structure_id: int) -> Dict:
        """Delete a data structure."""
        return self._api.post_request(pth=f"data_structures/delete/{int(structure_id)}", json={})

    def duplicate(self, structure_id: int, **fields: Any) -> Dict:
        """Duplicate a data structure (e.g. as a new version)."""
        return self._api.post_request(pth=f"data_structures/duplicate/{int(structure_id)}", json=fields)

    def versions(self, idno_or_id: Union[int, str]) -> Dict:
        """List versions of a data structure."""
        return self._api.get_request(pth=f"data_structures/versions/{_seg(idno_or_id)}")

    def projects(self, idno_or_id: Union[int, str], page: int = 1, per_page: int = 50) -> Dict:
        """Projects bound to a data structure."""
        return self._api.get_request(
            pth=f"data_structures/projects/{_seg(idno_or_id)}", params={"page": page, "per_page": per_page}
        )

    def validate(self, structure_id: int) -> Dict:
        """Validate a data structure (required roles, duplicates, codelists, display roles)."""
        return self._api.get_request(pth=f"data_structures/validate/{int(structure_id)}")

    # ── components ────────────────────────────────────────────────────────────

    def components(self, structure_id: int) -> List[Dict]:
        """Components of a data structure, in order."""
        response = self.get(structure_id, with_components=True)
        structure = response.get("data_structure", {}) if isinstance(response, dict) else {}
        return structure.get("components", []) or []

    def add_component(
        self,
        structure_id: int,
        name: str,
        column_type: str,
        label: Optional[str] = None,
        data_type: Optional[str] = None,
        codelist_id: Optional[int] = None,
        display_role: Optional[str] = None,
        sort_order: Optional[int] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> Dict:
        """Add a component (column) to a data structure.

        ``display_role="footnote"`` (attribute/annotation only) marks a column holding note IDs.
        """
        body: Dict[str, Any] = {"name": name, "column_type": column_type}
        for key, value in (
            ("label", label),
            ("data_type", data_type),
            ("codelist_id", codelist_id),
            ("display_role", display_role),
            ("sort_order", sort_order),
            ("description", description),
            ("metadata", metadata),
        ):
            if value is not None:
                body[key] = value
        return self._api.post_request(pth=f"data_structures/components/{int(structure_id)}", json=body)

    def update_component(self, component_id: int, **fields: Any) -> Dict:
        """Update a component (label, column_type, data_type, codelist_id, sort_order, display_role, ...).

        ``display_role`` is merged into the component metadata; ``""`` or ``"none"`` removes it.
        """
        return self._api.post_request(pth=f"data_structures/component_update/{int(component_id)}", json=fields)

    def delete_component(self, component_id: int) -> Dict:
        """Delete a component."""
        return self._api.post_request(pth=f"data_structures/component_delete/{int(component_id)}", json={})

    def import_components_csv(
        self,
        structure_id: int,
        components: List[ComponentSpec],
        csv_path: Optional[str] = None,
        upload_id: Optional[str] = None,
        dry_run: bool = True,
        overwrite: bool = False,
        delimiter: str = ",",
        timeout: Optional[float] = None,
    ) -> Dict:
        """Create or update components from a CSV (and build codelists from code/label columns).

        Each component: ``{"name", "column_type", "csv_column", "label"?, "display_role"?,
        "codelist"?: {"mode": "from_csv", "code_column", "label_column"} or {"mode": "global", "codelist_id"}}``.
        Defaults to a dry run: read ``summary.components_preview`` and ``codelist_resolutions``, then call
        again with ``dry_run=False``.
        """
        if (csv_path is None) == (upload_id is None):
            raise ValueError("Pass exactly one of csv_path or upload_id")
        payload = {"delimiter": delimiter, "dry_run": bool(dry_run), "overwrite": bool(overwrite), "components": components}
        pth = f"data_structures/import_components_csv/{int(structure_id)}"
        if upload_id is not None:
            return self._api.post_request(pth=pth, json={**payload, "upload_id": upload_id}, timeout=timeout)
        with open(csv_path, "rb") as handle:
            return self._api.post_request(
                pth=pth, data={"payload": json.dumps(payload)}, files={"file": handle}, timeout=timeout
            )

    def create_from_csv(
        self,
        name: str,
        csv_path: str,
        agency: Optional[str] = None,
        version: Optional[str] = None,
        title: Optional[str] = None,
        roles: Optional[Dict[str, str]] = None,
        footnote_columns: Iterable[str] = (),
        label_suffix: str = "_LABEL",
        label_columns: str = "codelist",
        dry_run: bool = False,
        delimiter: str = ",",
    ) -> Dict:
        """Create a data structure and its components (and codelists) from a data CSV.

        Components come from :func:`components_from_csv`. Returns ``{"structure_id", "components",
        "create", "import", "validation"}``. With ``dry_run=True`` the structure is created but the
        components are only previewed (``import.summary.components_preview``).
        """
        components = components_from_csv(
            csv_path, roles=roles, footnote_columns=footnote_columns, label_suffix=label_suffix,
            label_columns=label_columns, delimiter=delimiter,
        )
        created = self.create(name, agency=agency, version=version, title=title)
        structure_id = int(created.get("id") or created.get("data_structure", {}).get("id"))
        imported = self.import_components_csv(
            structure_id, components, csv_path=csv_path, dry_run=dry_run, delimiter=delimiter
        )
        validation = None if dry_run else self.validate(structure_id)
        return {"structure_id": structure_id, "components": components, "create": created, "import": imported,
                "validation": validation}

    # ── import / export ───────────────────────────────────────────────────────

    def import_json(
        self, data_structure: Union[Dict, str], overwrite: bool = False, dry_run: bool = False
    ) -> Dict:
        """Import a data structure (and inline codelists) from a dict or a JSON file path.

        The dict can be the full export (``{"data_structure": {...}}``) or just the structure.
        """
        if isinstance(data_structure, str):
            with open(data_structure, encoding="utf-8") as handle:
                data_structure = json.load(handle)
        body = data_structure if "data_structure" in data_structure else {"data_structure": data_structure}
        body = {**body, "overwrite": bool(overwrite), "dry_run": bool(dry_run)}
        return self._api.post_request(pth="data_structures/import_json", json=body)

    def export(self, idno_or_id: Union[int, str], out_path: Optional[str] = None) -> Dict:
        """Export a data structure as JSON (structure, components, codelists). Optionally save to ``out_path``."""
        response = self._api.get_request(pth=f"data_structures/export/{_seg(idno_or_id)}")
        if out_path:
            with open(out_path, "w", encoding="utf-8") as handle:
                json.dump(response, handle, indent=2, ensure_ascii=False)
        return response

    def import_sdmx(self, file_path: str, overwrite_codelists: bool = False) -> Dict:
        """Import an SDMX-ML structure file (DSD and codelists)."""
        with open(file_path, "rb") as handle:
            return self._api.post_request(
                pth="data_structures/import_sdmx",
                files={"file": handle},
                params={"overwrite_codelists": int(bool(overwrite_codelists))},
            )
