"""Resumable (chunked) file uploads for the Metadata Editor API."""

import math
import os
from typing import Callable, Dict, Optional

from .requester import RequestsWithSpecificErrors

DEFAULT_CHUNK_SIZE = 5 * 1024 * 1024


class UploadsClient:
    """Resumable uploads: ``POST uploads/init``, ``POST uploads/chunk/{id}``, ``GET uploads/status/{id}``.

    The returned ``upload_id`` can be passed to endpoints that accept one (data import, notes import,
    DSD component import, codelist import).
    """

    def __init__(self, api: RequestsWithSpecificErrors):
        self._api = api

    def limits(self) -> Dict:
        """Server upload limits (``max_chunk_size``, ``recommended_chunk_size``, ``max_file_size``)."""
        return self._api.get_request(pth="uploads/limits")

    def status(self, upload_id: str) -> Dict:
        """Status of an upload (received chunks, completion)."""
        return self._api.get_request(pth="uploads/status/{}", id=upload_id)

    def delete(self, upload_id: str) -> Dict:
        """Delete an upload and its chunks."""
        return self._api.delete_request(pth="uploads/{}", id=upload_id)

    def upload(
        self,
        file_path: str,
        chunk_size: Optional[int] = None,
        progress: Optional[Callable[[int, int], None]] = None,
        timeout: Optional[float] = None,
    ) -> str:
        """Upload a local file in chunks and return its ``upload_id``.

        Args:
            file_path: local file to upload.
            chunk_size: bytes per chunk; defaults to the server's recommended size (or 5 MB).
            progress: optional callback ``progress(chunks_sent, total_chunks)``.
            timeout: seconds per request.
        """
        if not os.path.isfile(file_path):
            raise FileNotFoundError(file_path)
        total_size = os.path.getsize(file_path)
        if chunk_size is None:
            chunk_size = self._recommended_chunk_size()
        chunk_size = max(1, int(chunk_size))
        total_chunks = max(1, math.ceil(total_size / chunk_size))
        filename = os.path.basename(file_path)

        init = self._api.post_request(
            pth="uploads/init",
            json={
                "filename": filename,
                "total_size": max(total_size, 1),
                "total_chunks": total_chunks,
                "chunk_size": chunk_size,
            },
            timeout=timeout,
        )
        upload_id = init.get("upload_id") if isinstance(init, dict) else None
        if not upload_id:
            raise ValueError(f"uploads/init did not return an upload_id: {init!r}")

        with open(file_path, "rb") as handle:
            for number in range(total_chunks):
                data = handle.read(chunk_size)
                self._api.post_request(
                    pth="uploads/chunk/{}",
                    id=upload_id,
                    data={"chunk_number": str(number)},
                    files={"chunk": (filename, data, "application/octet-stream")},
                    timeout=timeout,
                )
                if progress is not None:
                    progress(number + 1, total_chunks)
        return upload_id

    def _recommended_chunk_size(self) -> int:
        try:
            limits = self.limits()
            size = int(limits.get("recommended_chunk_size") or limits.get("max_chunk_size") or 0)
            return size if size > 0 else DEFAULT_CHUNK_SIZE
        except Exception:
            return DEFAULT_CHUNK_SIZE
