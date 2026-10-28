"""Thin template endpoint wrappers for the Metadata Editor API."""

from typing import Dict, Optional

from .requester import RequestsWithSpecificErrors


class TemplatesClient:
    """Template-focused thin wrappers around API endpoints."""

    def __init__(self, api: RequestsWithSpecificErrors, template_cache: Optional[Dict] = None):
        self._api = api
        self._cache = template_cache

    def list(self) -> Dict:
        """List all templates."""
        return self._api.get_request(pth="/templates")

    def get(self, uid: str) -> Dict:
        """Get a template by UID."""
        return self._api.get_request(pth="/templates/{}", id=uid)

    def create(self, template: Dict) -> Dict:
        """Create a template."""
        return self._api.post_request(pth="/templates", json=template)

    def update(self, uid: str, template: Dict) -> Dict:
        """Update a template by UID."""
        return self._api.post_request(pth="/templates/update/{}", id=uid, json=template)

    def delete(self, uid: str) -> Dict:
        """Delete a template by UID."""
        response = self._api.post_request(pth="/templates/delete/{}", id=uid)
        if self._cache is not None:
            self._cache.pop(uid, None)
        return response

    def duplicate(self, uid: str) -> Dict:
        """Duplicate a template by UID."""
        return self._api.post_request(pth="/templates/duplicate/{}", id=uid)

    def translation_keys(self, uid: str, lang: Optional[str] = None) -> Dict:
        """Get translation keys for a template."""
        params = {"lang": lang} if lang is not None else None
        return self._api.get_request(pth="/templates/translation_keys/{}", id=uid, params=params)
