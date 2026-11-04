"""Generic HTTP verb wrappers for calling any Metadata Editor API path."""

from io import BufferedReader
from typing import Dict, List, Optional, Union

from .requester import RequestsWithSpecificErrors


class ApiClient:
    """Call API endpoints directly when no typed sub-client method exists yet."""

    def __init__(self, api: RequestsWithSpecificErrors):
        self._api = api

    def request(
        self,
        method: str,
        path: str,
        id: Optional[Union[int, str]] = None,
        params: Optional[Dict[str, Union[str, List[str]]]] = None,
        json: Optional[Dict] = None,
        data: Optional[Dict[str, str]] = None,
        files: Optional[Dict[str, BufferedReader]] = None,
    ) -> Dict:
        """Issue an HTTP request against a path relative to the configured API base URL."""
        return self._api.request(
            method=method,
            pth=path,
            id=id,
            params=params,
            json=json,
            data=data,
            files=files,
        )

    def get(
        self,
        path: str,
        id: Optional[Union[int, str]] = None,
        params: Optional[Dict[str, Union[str, List[str]]]] = None,
    ) -> Dict:
        """GET request."""
        return self.request("get", path, id=id, params=params)

    def post(
        self,
        path: str,
        id: Optional[Union[int, str]] = None,
        json: Optional[Dict] = None,
        data: Optional[Dict[str, str]] = None,
        files: Optional[Dict[str, BufferedReader]] = None,
        params: Optional[Dict[str, Union[str, List[str]]]] = None,
    ) -> Dict:
        """POST request. Prefer POST delete routes when DELETE is blocked by your network."""
        return self.request("post", path, id=id, params=params, json=json, data=data, files=files)

    def put(
        self,
        path: str,
        id: Optional[Union[int, str]] = None,
        json: Optional[Dict] = None,
        data: Optional[Dict[str, str]] = None,
        files: Optional[Dict[str, BufferedReader]] = None,
        params: Optional[Dict[str, Union[str, List[str]]]] = None,
    ) -> Dict:
        """PUT request."""
        return self.request("put", path, id=id, params=params, json=json, data=data, files=files)

    def delete(
        self,
        path: str,
        id: Optional[Union[int, str]] = None,
        params: Optional[Dict[str, Union[str, List[str]]]] = None,
    ) -> Dict:
        """DELETE request. Many editor deletes use POST instead (e.g. `/editor/delete/{{id}}`)."""
        return self.request("delete", path, id=id, params=params)
