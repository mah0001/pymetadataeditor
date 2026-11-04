"""Helpers to prepare indicator data for import (pandas).

Typical flow for a publication-style wide table::

    long = wide_to_long(df, id_vars=["Country", "Sex"])
    long = split_value_flags(long)                 # "12.3 e [1]" -> OBS_VALUE, OBS_STATUS, NOTE_MARKERS
    long = markers_to_note_ids(long, {"[1]": "N01"})
    long = add_labels(long, {"REF_AREA": country_codes})
    check_observation_key(long, ["INDICATOR_ID", "REF_AREA", "SEX", "TIME_PERIOD"])
    write_notes_csv(notes, "notes.csv")
"""

import re
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Union

import pandas as pd

#: Publication flags -> SDMX CL_OBS_STATUS codes.
DEFAULT_FLAG_CODES = {"e": "E", "p": "P", "b": "B", "f": "F", "i": "I", "u": "U"}
#: Missing-value markers -> OBS_STATUS (value left empty).
DEFAULT_MISSING = {"..": "O", "n/a": "O", "na": "O", "-": "O", "x": "O"}

_MARKER_RE = re.compile(r"\[[^\]]+\]")


def wide_to_long(
    df: pd.DataFrame,
    id_vars: Sequence[str],
    time_name: str = "TIME_PERIOD",
    value_name: str = "OBS_VALUE",
    strip_headers: bool = True,
) -> pd.DataFrame:
    """Unpivot a wide table (one column per period) into one row per observation.

    Values are kept as text so flags and markers can be split afterwards; period headers are trimmed.
    """
    long = df.melt(id_vars=list(id_vars), var_name=time_name, value_name=value_name)
    if strip_headers:
        long[time_name] = long[time_name].astype(str).str.strip()
    long[value_name] = long[value_name].astype("string")
    return long


def split_value_flags(
    df: pd.DataFrame,
    value_col: str = "OBS_VALUE",
    status_col: str = "OBS_STATUS",
    markers_col: str = "NOTE_MARKERS",
    flag_codes: Optional[Mapping[str, str]] = None,
    missing: Optional[Mapping[str, str]] = None,
    default_status: str = "A",
    thousands_sep: str = ",",
) -> pd.DataFrame:
    """Split cells like ``"12.3 e [1]"`` into a numeric value, a status code and footnote markers.

    - Footnote markers (``[1]``, ``[a]``) go to ``markers_col`` (several joined with ``;``).
    - A trailing flag letter (``e``, ``p`` ...) becomes ``status_col`` via ``flag_codes``.
    - Missing markers (``..``, ``n/a`` ...) leave the value empty and set the status via ``missing``.
    - Thousands separators are removed. Unparseable values are left empty with status ``O``.
    """
    flag_codes = {k.lower(): v for k, v in (flag_codes or DEFAULT_FLAG_CODES).items()}
    missing = {k.lower(): v for k, v in (missing or DEFAULT_MISSING).items()}
    out = df.copy()
    values: List[Optional[float]] = []
    statuses: List[str] = []
    markers: List[str] = []
    for raw in out[value_col].tolist():
        text = "" if raw is None or (isinstance(raw, float) and pd.isna(raw)) or raw is pd.NA else str(raw).strip()
        found = _MARKER_RE.findall(text)
        markers.append(";".join(found))
        text = _MARKER_RE.sub(" ", text).strip()
        status = default_status
        value: Optional[float] = None
        lowered = text.lower()
        if lowered in missing:
            status = missing[lowered]
        elif text:
            parts = text.split()
            if len(parts) > 1 and parts[-1].lower() in flag_codes:
                status = flag_codes[parts[-1].lower()]
                parts = parts[:-1]
            elif len(parts) == 1 and len(text) > 1 and text[-1].lower() in flag_codes and text[:-1].strip():
                status = flag_codes[text[-1].lower()]
                parts = [text[:-1]]
            number = "".join(parts).replace(thousands_sep, "") if thousands_sep else "".join(parts)
            try:
                value = float(number)
            except ValueError:
                value, status = None, missing.get("..", "O")
        else:
            status = missing.get("..", "O")
        values.append(value)
        statuses.append(status)
    out[value_col] = values
    out[status_col] = statuses
    out[markers_col] = markers
    return out


def strip_markers(series: pd.Series) -> pd.Series:
    """Remove footnote markers (``[1]``) from labels or headers, e.g. ``"Calmeria [2]"`` -> ``"Calmeria"``."""
    return series.astype(str).str.replace(_MARKER_RE, "", regex=True).str.strip()


def markers_to_note_ids(
    df: pd.DataFrame,
    marker_map: Mapping[str, str],
    markers_col: str = "NOTE_MARKERS",
    note_col: str = "NOTE_ID",
    extra: Optional[pd.Series] = None,
    drop_markers: bool = True,
) -> pd.DataFrame:
    """Turn markers (``"[1];[3]"``) into note IDs (``"N01;N03"``) using ``marker_map``.

    ``extra`` (optional, aligned with ``df``) adds IDs per row, e.g. row or column notes that the publication
    marked on a label or header: ``extra = (df.REF_AREA == "XCA").map({True: "N02", False: ""})``.
    Unknown markers raise ValueError.
    """
    out = df.copy()
    ids_col: List[str] = []
    extras = extra.tolist() if extra is not None else [""] * len(out)
    for raw, more in zip(out[markers_col].fillna("").tolist(), extras):
        ids: List[str] = []
        for marker in [m for m in str(raw).split(";") if m]:
            if marker not in marker_map:
                raise ValueError(f"Unknown footnote marker {marker!r}")
            if marker_map[marker] not in ids:
                ids.append(marker_map[marker])
        for note_id in [m.strip() for m in str(more or "").split(";") if m.strip()]:
            if note_id not in ids:
                ids.append(note_id)
        ids_col.append(";".join(ids))
    out[note_col] = ids_col
    if drop_markers:
        out = out.drop(columns=[markers_col])
    return out


def add_labels(
    df: pd.DataFrame,
    lookups: Mapping[str, Union[Mapping[str, str], pd.DataFrame]],
    label_suffix: str = "_LABEL",
    code_from: Optional[Mapping[str, str]] = None,
) -> pd.DataFrame:
    """Add ``<COL>_LABEL`` columns right after their code columns.

    ``lookups``: column -> {code: label} or a DataFrame with ``code`` and ``label`` columns.
    ``code_from``: optional column -> source column holding names to map to codes first
    (e.g. ``{"REF_AREA": "Country"}`` with ``lookups["REF_AREA"]`` keyed by name -> code).
    """
    out = df.copy()
    for col, lookup in lookups.items():
        mapping = dict(zip(lookup["code"], lookup["label"])) if isinstance(lookup, pd.DataFrame) else dict(lookup)
        if code_from and col in code_from:
            out[col] = out[code_from[col]].map(mapping)
            continue
        label_col = col + label_suffix
        labels = out[col].map(mapping)
        if label_col in out.columns:
            out[label_col] = labels
        else:
            out.insert(out.columns.get_loc(col) + 1, label_col, labels)
    return out


def check_observation_key(df: pd.DataFrame, key_cols: Sequence[str]) -> pd.DataFrame:
    """Rows whose observation key (e.g. indicator, area, sex, period) appears more than once."""
    dup = df.duplicated(subset=list(key_cols), keep=False)
    return df[dup].sort_values(list(key_cols))


def write_notes_csv(
    notes: Union[Iterable[Mapping[str, str]], Mapping[str, str]],
    path: str,
    indicator_id: Optional[str] = None,
    column: str = "NOTE_ID",
) -> pd.DataFrame:
    """Write a notes CSV for ``me.indicators.notes.import_csv`` (``note_id, indicator_id, scope, column, note``).

    ``notes``: ``{note_id: text}`` or a list of dicts with ``note_id``/``id``, ``note`` and optional
    ``indicator_id``, ``scope`` (``cell``/``table``), ``column``.
    """
    rows = []
    items = [{"note_id": k, "note": v} for k, v in notes.items()] if isinstance(notes, Mapping) else list(notes)
    for item in items:
        note_id = item.get("note_id") or item.get("id")
        scope = item.get("scope") or "cell"
        rows.append({
            "note_id": note_id,
            "indicator_id": item.get("indicator_id") or indicator_id or "",
            "scope": scope,
            "column": item.get("column") or (column if scope == "cell" else ""),
            "note": item.get("note", ""),
        })
    table = pd.DataFrame(rows, columns=["note_id", "indicator_id", "scope", "column", "note"])
    table.to_csv(path, index=False, encoding="utf-8")
    return table
