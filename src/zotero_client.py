from __future__ import annotations

import copy
import html
import secrets
from typing import Any

import requests

from .dedupe import extract_extra_identifier, normalize_title
from .http_utils import build_retry_session
from .models import ExistingItem


class ZoteroClient:
    def __init__(self, library_id: str, api_key: str, library_type: str = "user", session: requests.Session | None = None) -> None:
        if not library_id or not api_key:
            raise ValueError("ZOTERO_LIBRARY_ID and ZOTERO_API_KEY are required")
        if library_type not in {"user", "group"}:
            raise ValueError("ZOTERO_LIBRARY_TYPE must be 'user' or 'group'")
        self.library_id = library_id
        self.api_key = api_key
        self.library_type = library_type
        self.session = session or build_retry_session()
        self.api_root = "https://api.zotero.org"
        self.base_url = f"https://api.zotero.org/{library_type}s/{library_id}"
        self._collections_cache: dict[str, str] | None = None
        self._items_cache: list[ExistingItem] | None = None
        self._template_cache: dict[str, dict[str, Any]] = {}
        self._child_notes_cache: dict[str, list[str]] = {}

    def seed_collections_cache(self, collections: dict[str, str]) -> None:
        self._collections_cache = dict(collections)

    def seed_items_cache(self, items: list[ExistingItem]) -> None:
        self._items_cache = list(items)

    def get_all_collections(self) -> dict[str, str]:
        if self._collections_cache is not None:
            return dict(self._collections_cache)
        collections: dict[str, str] = {}
        start = 0
        while True:
            response = self.session.get(
                f"{self.base_url}/collections",
                headers=self._headers(),
                params={"format": "json", "limit": 100, "start": start},
                timeout=30,
            )
            response.raise_for_status()
            payload = response.json()
            if not payload:
                break
            for item in payload:
                collections[item["data"]["name"]] = item["key"]
            if len(payload) < 100:
                break
            start += 100
        self._collections_cache = dict(collections)
        return collections

    def get_all_top_level_items(self) -> list[ExistingItem]:
        if self._items_cache is not None:
            return list(self._items_cache)
        existing: list[ExistingItem] = []
        start = 0
        while True:
            response = self.session.get(
                f"{self.base_url}/items/top",
                headers=self._headers(),
                params={"format": "json", "include": "data", "limit": 100, "start": start},
                timeout=30,
            )
            response.raise_for_status()
            payload = response.json()
            if not payload:
                break
            for item in payload:
                data = item["data"]
                item_type = data.get("itemType", "")
                if item_type in {"attachment", "note"}:
                    continue
                existing.append(
                    ExistingItem(
                        key=item["key"],
                        version=int(item["version"]),
                        item_type=item_type,
                        data=data,
                        title=data.get("title", ""),
                        title_norm=normalize_title(data.get("title", "")),
                        pmid=extract_extra_identifier(data.get("extra", ""), "PMID"),
                        doi=(data.get("DOI") or extract_extra_identifier(data.get("extra", ""), "DOI")).strip(),
                        isbn=(data.get("ISBN") or extract_extra_identifier(data.get("extra", ""), "ISBN")).strip(),
                    )
                )
            if len(payload) < 100:
                break
            start += 100
        self._items_cache = list(existing)
        return existing

    def get_item_template(self, item_type: str) -> dict[str, Any]:
        if item_type in self._template_cache:
            return copy.deepcopy(self._template_cache[item_type])
        response = self.session.get(
            f"{self.api_root}/items/new",
            headers=self._headers(),
            params={"itemType": item_type},
            timeout=30,
        )
        response.raise_for_status()
        template = response.json()
        self._template_cache[item_type] = copy.deepcopy(template)
        return template

    def get_child_notes(self, parent_key: str) -> list[str]:
        if parent_key in self._child_notes_cache:
            return list(self._child_notes_cache[parent_key])
        response = self.session.get(
            f"{self.base_url}/items/{parent_key}/children",
            headers=self._headers(),
            params={"format": "json", "include": "data", "itemType": "note"},
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        notes = [item["data"].get("note", "") for item in payload]
        self._child_notes_cache[parent_key] = list(notes)
        return notes

    def create_item(self, payload: dict[str, Any]) -> dict[str, Any]:
        saved = self._write_items([payload], versioned=False)[0]
        self._items_cache = None
        return saved

    def update_item(self, payload: dict[str, Any]) -> dict[str, Any]:
        saved = self._write_items([payload], versioned=True)[0]
        self._items_cache = None
        return saved

    def create_child_note(self, parent_key: str, note_text: str) -> dict[str, Any]:
        template = self.get_item_template("note")
        template["parentItem"] = parent_key
        template["note"] = note_to_html(note_text)
        saved = self.create_item(template)
        self._child_notes_cache.pop(parent_key, None)
        return saved

    def create_collection(self, name: str, parent_collection: str | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {"name": name}
        if parent_collection:
            payload["parentCollection"] = parent_collection
        saved = self._write_collections([payload])[0]
        self._collections_cache = None
        return saved

    def _write_items(self, payload: list[dict[str, Any]], versioned: bool) -> list[dict[str, Any]]:
        headers = self._headers(write=True)
        if not versioned:
            headers["Zotero-Write-Token"] = secrets.token_hex(16)
        response = self.session.post(f"{self.base_url}/items", headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        body = response.json()
        saved: list[dict[str, Any]] = []
        failed = body.get("failed", {})
        if failed:
            first_error = next(iter(failed.values()))
            raise RuntimeError(first_error.get("message", "Zotero write failed"))
        successful = body.get("successful", {})
        for index in sorted(successful, key=int):
            saved.append(successful[index])
        return saved

    def _headers(self, write: bool = False) -> dict[str, str]:
        headers = {"Zotero-API-Key": self.api_key}
        if write:
            headers["Content-Type"] = "application/json"
        return headers

    def _write_collections(self, payload: list[dict[str, Any]]) -> list[dict[str, Any]]:
        headers = self._headers(write=True)
        headers["Zotero-Write-Token"] = secrets.token_hex(16)
        response = self.session.post(f"{self.base_url}/collections", headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        body = response.json()
        saved: list[dict[str, Any]] = []
        failed = body.get("failed", {})
        if failed:
            first_error = next(iter(failed.values()))
            raise RuntimeError(first_error.get("message", "Zotero collection write failed"))
        successful = body.get("successful", {})
        for index in sorted(successful, key=int):
            saved.append(successful[index])
        return saved


def note_to_html(note_text: str) -> str:
    escaped = html.escape(note_text.strip())
    return "".join(f"<p>{line}</p>" for line in escaped.splitlines() if line.strip()) or "<p></p>"
