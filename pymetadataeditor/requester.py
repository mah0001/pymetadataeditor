from io import BufferedReader
from json import JSONDecodeError
from ssl import SSLError as ssl_SSLError
from typing import Any, Dict, List, Optional, Union

import requests
from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, SecretStr, model_validator
from requests.exceptions import HTTPError, SSLError


class RequestsWithSpecificErrors(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    api_url: AnyHttpUrl
    api_key: SecretStr = Field(repr=False)
    allow_http: bool = Field(
        default=False,
        description="API urls that begin HTTPS are favoured. Set allow_http=True to use of the less secure HTTP",
    )
    verify_ssl: bool = Field(
        default=True,
        description="Calls to the API are authenticated with an SSL certificate. "
        "Set verify_ssl=False to remove this requirement",
    )

    @model_validator(mode="after")
    def _check_https(self) -> Any:
        if str(self.api_url).startswith("https") or self.allow_http:
            return self
        else:
            raise ValueError(
                f"URL scheme should be 'https' but got {self.api_url}"
                "To allow the less secure use of 'http', set allow_unsecure=True"
            )

    def _request(
        self,
        method: str,
        pth: str,
        json: Optional[Dict] = None,
        params: Optional[Dict[str, Union[str, List[str]]]] = None,
        id: Optional[Union[int, str]] = None,
        data: Optional[Dict[str, str]] = None,
        files: Optional[Dict[str, BufferedReader]] = None,
    ) -> Dict:
        """
        Sends a GET or POST request to the specified URL with the API key in the headers and returns the JSON response.

        Args:
            method (str): Either post or get
            pth (str): The path appended to the API_URL to which the GET or POST request is sent.

        Returns:
            Dict[str, str]: The JSON response from the server, parsed into a dictionary.

        Raises:
            ValueError: If the URL does not start with 'https'.
            PermissionError: If the response status code is 403, indicating that access is denied.
            Exception: If the request fails due to other HTTP errors, with details of the status code and response text.
            Exception: If any other unexpected error occurs during the request.
        """
        method = method.lower()
        assert method in ["get", "post"], f"unknown method {method}"
        request_kwargs = {}
        if method == "post":
            assert params is None, "when using post, pass json not params"
            request_kwargs["json"] = json
            if data is not None:
                request_kwargs["data"] = data
            if files is not None:
                request_kwargs["files"] = files
        if method == "get" and params is not None:
            assert json is None, "when using get, pass params not json"
            request_kwargs["params"] = params

        if "{" in pth:
            assert id is not None, "If passing a url format, an id must be passed"
            pth = pth.format(id)
        url = str(self.api_url).strip("/") + "/" + pth.strip("/")
        try:
            response = None
            response = requests.request(
                method,
                url,
                verify=self.verify_ssl,
                headers={"x-api-key": self.api_key.get_secret_value()},
                **request_kwargs,
            )
            response.raise_for_status()
        except (SSLError, ssl_SSLError) as e:
            raise SSLError(
                f"Usually this means the admin of {self.api_url} has not verified an SSL certificate.\n"
                f"You can bypass the requirement by setting MetadataEditor.verify_ssl=False.\n{e}"
            ) from None
        except HTTPError as e:
            if response is None or response.status_code == 404:
                error_msg = (
                    f"Page not found. Try checking the URL.\nGenerally the required URL looks like "
                    f"'https://<name_of_your_metadata_database>.org/index.php/api', but the URL that was passed "
                    f"was '{self.api_url}'"
                )
                raise HTTPError(error_msg) from None
            elif response.status_code == 403:
                raise PermissionError(
                    f"Access to that URL is denied for {url} " "Check that the API key is correct"
                ) from e
            elif response.status_code == 400 and "message" in response.text:
                if isinstance(response.text, dict):
                    error_message = response.text["message"]
                else:
                    error_message = response.text
                raise PermissionError(error_message) from e
            else:
                raise HTTPError(f"Status Code: {response.status_code}, Response: {response.text}") from e
        try:
            json_response = response.json()
        except (JSONDecodeError, requests.exceptions.JSONDecodeError) as e:
            raise JSONDecodeError(
                f"Error decoding JSON response: {e.msg}\n{response.text}\nFull Response: {response}", e.doc, e.pos
            ) from e
        # if self.verify_ssl == False:
        # we must have shown this warning the first time, ok to silence thereafter
        return json_response

    def get_request(
        self, pth: str, id: Optional[Union[int, str]] = None, params: Optional[Dict[str, Union[str, List[str]]]] = None
    ) -> Dict:
        """
        Args:
            pth (str): The path appended to the API_URL to which the GET request is sent.
            id (optional int or str): The id of a specific collection or project.
                                        If not none, then pth should contain '{}' where the id ought to go.
            params (optional dict): additional parameters to send with the get request such as 'keywords'

        Returns:
            Dict[str, str]: The JSON response from the server, parsed into a dictionary.
        """
        return self._request("get", pth=pth, id=id, params=params)

    def post_request(
        self,
        pth: str,
        json: Optional[Dict] = None,
        id: Optional[Union[int, str]] = None,
        data: Optional[Dict[str, str]] = None,
        files: Optional[Dict[str, BufferedReader]] = None,
    ):
        """
        Args:
            pth (str): The path appended to the API_URL to which the POST request is sent.
            json (optional dict): The JSON data to send with the POST request.
            id (optional int or str): The id of a specific project, collection or template etc.
                                        If not none, then pth should contain '{}' where the id ought to go.
            data (optional dict): The data to send with the POST request.
            files (optional dict): The files to send with the POST request.

        Returns:
            Dict[str, str]: The JSON response from the server, parsed into a dictionary.
        """
        return self._request("post", pth=pth, id=id, json=json, data=data, files=files)
