"""Codelist registry wrappers for the Metadata Editor API."""

import json
from typing import Any, Dict, List, Optional, Union
from urllib.parse import quote

from .requester import RequestsWithSpecificErrors


def _seg(value: Union[int, str]) -> str:
    return quote(str(value).strip(), safe="")


def _save(response, out_path: str) -> str:
    with open(out_path, "wb") as handle:
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            handle.write(chunk)
    return out_path


class CodelistsClient:
    """Global codelist registry: codelists, codes, labels, translations, import and export."""

    def __init__(self, api: RequestsWithSpecificErrors):
        self._api = api

    # ── codelists ─────────────────────────────────────────────────────────────

    def list(
        self,
        search: Optional[str] = None,
        agency: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict:
        """List codelists."""
        params: Dict[str, Union[int, str]] = {"limit": limit, "offset": offset}
        for key, value in (("search", search), ("agency", agency), ("status", status)):
            if value:
                params[key] = value
        return self._api.get_request(pth="codelists", params=params)

    def get(self, codelist_id: int) -> Dict:
        """Get a codelist by id."""
        return self._api.get_request(pth=f"codelists/{int(codelist_id)}")

    def get_by_identity(self, agency: str, name: str, version: Optional[str] = None) -> Dict:
        """Get a codelist by agency, name and (optionally) version."""
        params = {"agency": agency, "name": name}
        if version:
            params["version"] = version
        return self._api.get_request(pth="codelists/lookup_by_identity", params=params)

    def versions(self, name: str, agency: Optional[str] = None) -> Dict:
        """Versions of a codelist."""
        params = {"agency": agency} if agency else None
        return self._api.get_request(pth=f"codelists/versions/{_seg(name)}", params=params)

    def create(self, name: str, agency: Optional[str] = None, version: Optional[str] = None, **fields: Any) -> Dict:
        """Create a codelist (title, description, status, ... as keyword fields)."""
        body: Dict[str, Any] = {"name": name, **fields}
        if agency is not None:
            body["agency"] = agency
        if version is not None:
            body["version"] = version
        return self._api.post_request(pth="codelists", json=body)

    def update(self, codelist_id: int, **fields: Any) -> Dict:
        """Update codelist fields."""
        return self._api.post_request(pth=f"codelists/{int(codelist_id)}", json=fields)

    def delete(self, codelist_id: int) -> Dict:
        """Delete a codelist."""
        return self._api.post_request(pth=f"codelists/delete/{int(codelist_id)}", json={})

    # ── codes ─────────────────────────────────────────────────────────────────

    def codes(
        self,
        codelist_id: int,
        search: Optional[str] = None,
        language: Optional[str] = None,
        limit: int = 500,
        offset: int = 0,
    ) -> Dict:
        """Codes of a codelist (with labels)."""
        params: Dict[str, Union[int, str]] = {"limit": limit, "offset": offset}
        if search:
            params["search"] = search
        if language:
            params["language"] = language
        return self._api.get_request(pth=f"codelists/codes/{int(codelist_id)}", params=params)

    def add_code(self, codelist_id: int, code: str, label: Optional[str] = None, **fields: Any) -> Dict:
        """Add a code (``label``, ``labels``, ``sort_order``, ``parent_id`` ... as keyword fields)."""
        body: Dict[str, Any] = {"code": code, **fields}
        if label is not None:
            body["label"] = label
        return self._api.post_request(pth=f"codelists/codes/{int(codelist_id)}", json=body)

    def add_codes(self, codelist_id: int, codes: List[Dict[str, Any]]) -> List[Dict]:
        """Add several codes (each ``{"code", "label"?, ...}``); one request per code."""
        return [self.add_code(codelist_id, **dict(item)) for item in codes]

    def update_code(self, code_id: int, **fields: Any) -> Dict:
        """Update a code."""
        return self._api.post_request(pth=f"codelists/codes/{int(code_id)}", json=fields)

    def delete_code(self, code_id: int) -> Dict:
        """Delete a code."""
        return self._api.post_request(pth=f"codelists/code_delete/{int(code_id)}", json={})

    # ── translations ──────────────────────────────────────────────────────────

    def translations(self, codelist_id: int) -> Dict:
        """Translations of a codelist."""
        return self._api.get_request(pth=f"codelists/codelist_translations/{int(codelist_id)}")

    def set_translation(self, codelist_id: int, **fields: Any) -> Dict:
        """Add or update a codelist translation (``language``, ``title``, ``description`` ...)."""
        return self._api.post_request(pth=f"codelists/codelist_translations/{int(codelist_id)}", json=fields)

    # ── import / export ───────────────────────────────────────────────────────

    def import_csv(self, codelist_id: int, csv_path: str, dry_run: bool = False, replace: bool = True) -> Dict:
        """Import codes from a CSV into a codelist (replaces existing codes by default)."""
        with open(csv_path, "rb") as handle:
            return self._api.post_request(
                pth=f"codelists/import_csv/{int(codelist_id)}",
                files={"file": handle},
                params={"dry_run": int(bool(dry_run)), "replace": int(bool(replace))},
            )

    def import_json(self, codelist: Union[Dict, str], overwrite: bool = False, dry_run: bool = False) -> Dict:
        """Import a codelist from a dict or JSON file path (``{"codelist": {...}}`` or the flat shape)."""
        if isinstance(codelist, str):
            with open(codelist, encoding="utf-8") as handle:
                codelist = json.load(handle)
        body = {**codelist, "overwrite": bool(overwrite), "dry_run": bool(dry_run)}
        return self._api.post_request(pth="codelists/import_json", json=body)

    def import_sdmx(self, file_path: str, dry_run: bool = False, replace: bool = False) -> Dict:
        """Import codelists from an SDMX-ML structure file."""
        with open(file_path, "rb") as handle:
            return self._api.post_request(
                pth="codelists/import_sdmx",
                files={"file": handle},
                params={"dry_run": int(bool(dry_run)), "replace": int(bool(replace))},
            )

    def export_json(self, codelist_id: int, out_path: Optional[str] = None) -> Dict:
        """Export a codelist as JSON. Optionally save to ``out_path``."""
        response = self._api.get_request(pth=f"codelists/export_json/{int(codelist_id)}")
        if out_path:
            with open(out_path, "w", encoding="utf-8") as handle:
                json.dump(response, handle, indent=2, ensure_ascii=False)
        return response

    def export_csv(self, codelist_id: int, out_path: str) -> str:
        """Download a codelist as CSV to ``out_path``."""
        return _save(self._api.get_request(pth=f"codelists/export_csv/{int(codelist_id)}", raw=True), out_path)

    def export_sdmx(self, codelist_id: int, out_path: str, version: str = "2.1") -> str:
        """Download a codelist as SDMX-ML to ``out_path``."""
        response = self._api.get_request(
            pth=f"codelists/export_sdmx/{int(codelist_id)}", params={"version": version}, raw=True
        )
        return _save(response, out_path)
