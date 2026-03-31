from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import ExistingItem


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_iso8601(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


class CacheStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.collections_path = self.root / "zotero_collections.json"
        self.items_path = self.root / "zotero_items.json"

    def load_collections(self, max_age_seconds: int) -> dict[str, str] | None:
        payload = self._load_json(self.collections_path)
        if not payload or self._is_stale(payload, max_age_seconds):
            return None
        collections = payload.get("collections")
        return dict(collections) if isinstance(collections, dict) else None

    def save_collections(self, collections: dict[str, str]) -> None:
        self._write_json(
            self.collections_path,
            {"saved_at": utc_now_iso(), "collections": collections},
        )

    def load_items(self, max_age_seconds: int) -> list[ExistingItem] | None:
        payload = self._load_json(self.items_path)
        if not payload or self._is_stale(payload, max_age_seconds):
            return None
        items_raw = payload.get("items")
        if not isinstance(items_raw, list):
            return None
        items: list[ExistingItem] = []
        for item_raw in items_raw:
            if not isinstance(item_raw, dict):
                continue
            items.append(
                ExistingItem(
                    key=str(item_raw.get("key", "")),
                    version=int(item_raw.get("version", 0)),
                    item_type=str(item_raw.get("item_type", "")),
                    data=dict(item_raw.get("data", {})),
                    title=str(item_raw.get("title", "")),
                    title_norm=str(item_raw.get("title_norm", "")),
                    pmid=str(item_raw.get("pmid", "")),
                    doi=str(item_raw.get("doi", "")),
                    isbn=str(item_raw.get("isbn", "")),
                )
            )
        return items

    def save_items(self, items: list[ExistingItem]) -> None:
        self._write_json(
            self.items_path,
            {"saved_at": utc_now_iso(), "items": [asdict(item) for item in items]},
        )

    def _load_json(self, path: Path) -> dict[str, Any] | None:
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    def _write_json(self, path: Path, payload: dict[str, Any]) -> None:
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def _is_stale(self, payload: dict[str, Any], max_age_seconds: int) -> bool:
        saved_at = parse_iso8601(str(payload.get("saved_at", "")))
        if saved_at is None:
            return True
        age = (datetime.now(timezone.utc) - saved_at).total_seconds()
        return age > max_age_seconds
