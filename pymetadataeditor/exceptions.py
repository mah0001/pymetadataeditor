"""Package-specific exceptions."""

import json
import re
from typing import Any, Dict, List, Optional

from requests.exceptions import HTTPError


class ApiError(HTTPError):
    """An HTTP error from the Metadata Editor API with the server's message and error list.

    Subclass of ``requests.exceptions.HTTPError``, so existing ``except HTTPError`` handlers still apply.

    Attributes:
        status_code: HTTP status code.
        message: ``message`` from the response body (or the raw body text).
        errors: list of error items (from ``errors`` or a ``VALIDATION_FAILED: [...]`` message), if any.
        body: the decoded JSON body, or None.
    """

    def __init__(self, status_code: int, message: str, errors: Optional[List[Any]] = None,
                 body: Optional[Dict] = None, response=None, url: str = ""):
        self.status_code = status_code
        self.message = message
        self.errors = errors or []
        self.body = body
        self.url = url
        text = f"HTTP {status_code}: {message}"
        if self.errors:
            text += "\n" + "\n".join(f"  - {_format_error_item(e)}" for e in self.errors)
        super().__init__(text, response=response)

    @classmethod
    def from_response(cls, response, url: str = "") -> "ApiError":
        """Build from a ``requests.Response`` with an error status."""
        body = None
        try:
            body = response.json()
        except ValueError:
            body = None
        message = ""
        errors: List[Any] = []
        if isinstance(body, dict):
            message = str(body.get("message") or body.get("detail") or body.get("status") or "")
            if isinstance(body.get("errors"), list):
                errors = list(body["errors"])
        elif isinstance(body, str):
            message = body
        if not message:
            message = (response.text or "")[:2000]
        match = re.match(r"^\s*VALIDATION_FAILED:\s*(\[.*\])\s*$", message, re.S)
        if match and not errors:
            try:
                errors = json.loads(match.group(1))
                message = "VALIDATION_FAILED"
            except ValueError:
                pass
        return cls(response.status_code, message, errors=errors, body=body if isinstance(body, dict) else None,
                   response=response, url=url)


def _format_error_item(item: Any) -> str:
    if isinstance(item, dict):
        path = item.get("path")
        msg = item.get("message", item)
        return f"{path}: {msg}" if path else str(msg)
    return str(item)


class DeleteNotAppliedError(Exception):
    """Exception raised when a delete request is not accepted by the system."""

    def __init__(self, message="Delete request not accepted by system.", response=None):
        super().__init__(message)
        self.response = response


class TemplateError(Exception):
    """Exception raised when there is an error with a template."""

    def __init__(self, message="Error with template", response=None):
        super().__init__(message)
        self.message = message
        self.response = response

    def __str__(self):
        if self.response:
            return f"{self.response}\n\n{self.message}"
        return self.message
