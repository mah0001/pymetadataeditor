"""Helpers to iterate over paged API listings without loading everything at once."""

from typing import Any, Callable, Dict, Iterable, Iterator, List, Optional, Union


def join_values(value: Union[str, int, Iterable[Union[str, int]]]) -> str:
    """Comma-join a list of filter values; pass strings and ints through."""
    if isinstance(value, (str, int)):
        return str(value)
    return ",".join(str(v) for v in value)


def iter_offset_pages(
    fetch: Callable[[int, int], Dict],
    items_key: str,
    page_size: int,
    max_items: Optional[int] = None,
    id_key: Optional[str] = "id",
    total_key: str = "total",
) -> Iterator[Dict[str, Any]]:
    """Yield items from an endpoint paged with ``limit`` / ``offset``.

    ``fetch(limit, offset)`` returns one page. Stops at the server total (``total_key``, when given), on a
    short or empty page, or after ``max_items``. Items already seen (same ``id_key``) are skipped.
    """
    if page_size < 1:
        raise ValueError("page_size must be at least 1")
    offset, yielded = 0, 0
    seen = set()
    while True:
        limit = page_size if max_items is None else min(page_size, max_items - yielded)
        if limit <= 0:
            return
        response = fetch(limit, offset)
        batch: List[Dict] = response.get(items_key) or []
        for item in batch:
            if id_key is not None and isinstance(item, dict) and id_key in item:
                if item[id_key] in seen:
                    continue
                seen.add(item[id_key])
            yield item
            yielded += 1
            if max_items is not None and yielded >= max_items:
                return
        offset += len(batch)
        total = response.get(total_key)
        if len(batch) < limit or (total is not None and offset >= int(total)):
            return


def iter_numbered_pages(
    fetch: Callable[[int, int], Dict],
    items_key: str,
    per_page: int,
    max_items: Optional[int] = None,
) -> Iterator[Dict[str, Any]]:
    """Yield items from an endpoint paged with ``page`` / ``per_page``.

    ``fetch(page, per_page)`` returns one page with a ``total``.
    """
    if per_page < 1:
        raise ValueError("per_page must be at least 1")
    page, yielded = 1, 0
    while True:
        response = fetch(page, per_page)
        batch: List[Dict] = response.get(items_key) or []
        for item in batch:
            yield item
            yielded += 1
            if max_items is not None and yielded >= max_items:
                return
        total = response.get("total")
        if len(batch) < per_page or (total is not None and page * per_page >= int(total)):
            return
        page += 1
