from __future__ import annotations

import re
import unicodedata

from .models import ExistingItem, ImportEntry, PubMedRecord


def normalize_title(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    normalized = normalized.encode("ascii", "ignore").decode("ascii")
    normalized = normalized.lower()
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def extract_extra_identifier(extra: str, label: str) -> str:
    pattern = re.compile(rf"^{re.escape(label)}\s*:\s*(.+)$", re.IGNORECASE | re.MULTILINE)
    match = pattern.search(extra or "")
    return match.group(1).strip() if match else ""


class ItemIndex:
    def __init__(self, items: list[ExistingItem]) -> None:
        self.items = items
        self.by_pmid = {item.pmid: item for item in items if item.pmid}
        self.by_doi = {item.doi.lower(): item for item in items if item.doi}
        self.by_isbn = {item.isbn.replace("-", ""): item for item in items if item.isbn}
        self.by_title = {item.title_norm: item for item in items if item.title_norm}

    def add_or_replace(self, item: ExistingItem) -> None:
        self.items = [existing for existing in self.items if existing.key != item.key] + [item]
        self.__init__(self.items)


def find_duplicate(entry: ImportEntry, record: PubMedRecord | None, item_index: ItemIndex) -> ExistingItem | None:
    pmid = entry.pmid or (record.pmid if record else "")
    if pmid and pmid in item_index.by_pmid:
        return item_index.by_pmid[pmid]

    doi = (entry.doi or (record.doi if record else "")).strip().lower()
    if doi and doi in item_index.by_doi:
        return item_index.by_doi[doi]

    isbn = entry.isbn.replace("-", "")
    if isbn and isbn in item_index.by_isbn:
        return item_index.by_isbn[isbn]

    title = entry.title or (record.title if record else "")
    title_norm = normalize_title(title)
    if title_norm and title_norm in item_index.by_title:
        return item_index.by_title[title_norm]
    return None
