"""Thin external-resource endpoint wrappers for the Metadata Editor API."""

from typing import Dict, Optional, Union

from .requester import RequestsWithSpecificErrors


class ResourcesClient:
    """External-resource thin wrappers around API endpoints."""

    def __init__(self, api: RequestsWithSpecificErrors):
        self._api = api

    def list(self, project_id: Union[int, str]) -> Dict:
        """List resources attached to a project."""
        return self._api.get_request(pth="/resources/{}", id=project_id)

    def create(
        self,
        project_id: Union[int, str],
        dctype: str,
        title: str,
        author: Optional[str] = None,
        dcdate: Optional[str] = None,
        country: Optional[str] = None,
        language: Optional[str] = None,
        contributor: Optional[str] = None,
        publisher: Optional[str] = None,
        rights: Optional[str] = None,
        description: Optional[str] = None,
        abstract: Optional[str] = None,
        toc: Optional[str] = None,
        filename: Optional[str] = None,
        file_path: Optional[str] = None,
        overwrite: Optional[bool] = None,
    ) -> Dict:
        """Create a resource (multipart upload when file_path is set)."""
        data = self._resource_form_fields(
            dctype=dctype,
            title=title,
            author=author,
            dcdate=dcdate,
            country=country,
            language=language,
            contributor=contributor,
            publisher=publisher,
            rights=rights,
            description=description,
            abstract=abstract,
            toc=toc,
            filename=filename,
            overwrite=overwrite,
        )
        upload_path = file_path
        if upload_path is not None:
            with open(upload_path, "rb") as handle:
                return self._api.post_request(
                    pth="/resources/{}",
                    id=project_id,
                    data=data,
                    files={"file": handle},
                )
        return self._api.post_request(pth="/resources/{}", id=project_id, data=data)

    def update(
        self,
        project_id: Union[int, str],
        resource_id: Union[int, str],
        dctype: str,
        title: str,
        author: Optional[str] = None,
        dcdate: Optional[str] = None,
        country: Optional[str] = None,
        language: Optional[str] = None,
        contributor: Optional[str] = None,
        publisher: Optional[str] = None,
        rights: Optional[str] = None,
        description: Optional[str] = None,
        abstract: Optional[str] = None,
        toc: Optional[str] = None,
        filename: Optional[str] = None,
        file_path: Optional[str] = None,
        overwrite: Optional[bool] = None,
    ) -> Dict:
        """Update a resource (multipart upload when file_path is set)."""
        data = self._resource_form_fields(
            dctype=dctype,
            title=title,
            author=author,
            dcdate=dcdate,
            country=country,
            language=language,
            contributor=contributor,
            publisher=publisher,
            rights=rights,
            description=description,
            abstract=abstract,
            toc=toc,
            filename=filename,
            overwrite=overwrite,
        )
        pth = f"/resources/{project_id}/{resource_id}"
        if file_path is not None:
            with open(file_path, "rb") as handle:
                return self._api.post_request(pth=pth, data=data, files={"file": handle})
        return self._api.post_request(pth=pth, data=data)

    def delete(self, project_id: Union[int, str], resource_id: Union[int, str]) -> Dict:
        """Delete a resource from a project."""
        pth = f"/resources/delete/{project_id}/{resource_id}"
        return self._api.post_request(pth=pth)

    def import_file(self, project_id: Union[int, str], file_path: str) -> Dict:
        """Import resources from a file."""
        with open(file_path, "rb") as handle:
            return self._api.post_request(
                pth=f"/resources/import/{project_id}",
                files={"file": handle},
            )

    @staticmethod
    def _resource_form_fields(
        dctype: str,
        title: str,
        author: Optional[str],
        dcdate: Optional[str],
        country: Optional[str],
        language: Optional[str],
        contributor: Optional[str],
        publisher: Optional[str],
        rights: Optional[str],
        description: Optional[str],
        abstract: Optional[str],
        toc: Optional[str],
        filename: Optional[str],
        overwrite: Optional[bool],
    ) -> Dict[str, str]:
        data: Dict[str, str] = {"dctype": dctype, "title": title}
        optional = {
            "author": author,
            "dcdate": dcdate,
            "country": country,
            "language": language,
            "contributor": contributor,
            "publisher": publisher,
            "rights": rights,
            "description": description,
            "abstract": abstract,
            "toc": toc,
            "filename": filename,
        }
        for key, value in optional.items():
            if value is not None:
                data[key] = value
        if overwrite is not None:
            data["overwrite"] = "true" if overwrite else "false"
        return data
