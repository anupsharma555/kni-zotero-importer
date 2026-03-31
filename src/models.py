from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


SUPPORTED_ITEM_TYPES = {
    "journalarticle": "journalArticle",
    "journal article": "journalArticle",
    "article": "journalArticle",
    "blogpost": "blogPost",
    "blog post": "blogPost",
    "webpage": "webpage",
    "web page": "webpage",
    "book": "book",
    "report": "report",
    "conferencepaper": "conferencePaper",
    "conference paper": "conferencePaper",
    "preprint": "preprint",
    "document": "document",
}


@dataclass(slots=True)
class ImportEntry:
    collection_name: str
    pmid: str = ""
    title: str = ""
    tags: list[str] = field(default_factory=list)
    note: str = ""
    item_type: str = ""
    url: str = ""
    doi: str = ""
    isbn: str = ""
    raw_block: str = ""

    def resolved_item_type(self) -> str:
        if self.item_type:
            key = self.item_type.strip().lower()
            if key in SUPPORTED_ITEM_TYPES:
                return SUPPORTED_ITEM_TYPES[key]
            raise ValueError(f"Unsupported item type: {self.item_type}")
        if self.pmid:
            return "journalArticle"
        if self.url:
            return "webpage"
        return "document"


@dataclass(slots=True)
class ResolvedCollection:
    requested_name: str
    resolved_name: str
    key: str


@dataclass(slots=True)
class PubMedRecord:
    pmid: str
    title: str = ""
    abstract: str = ""
    journal: str = ""
    volume: str = ""
    issue: str = ""
    pages: str = ""
    date: str = ""
    doi: str = ""
    pmcid: str = ""
    url: str = ""
    creators: list[dict[str, str]] = field(default_factory=list)


@dataclass(slots=True)
class ExistingItem:
    key: str
    version: int
    item_type: str
    data: dict[str, Any]
    title: str = ""
    title_norm: str = ""
    pmid: str = ""
    doi: str = ""
    isbn: str = ""


@dataclass(slots=True)
class ImportResult:
    index: int
    status: str
    action: str
    collection_name: str
    item_key: str = ""
    title: str = ""
    message: str = ""
    raw_block: str = ""


@dataclass(slots=True)
class ParsedImportEntry:
    index: int
    entry: ImportEntry


@dataclass(slots=True)
class ImportReport:
    results: list[ImportResult]
    errors: list[ImportResult]
    dry_run: bool = False

    @property
    def has_errors(self) -> bool:
        return bool(self.errors)

    def render_text(self) -> str:
        lines = [
            f"Dry run: {'yes' if self.dry_run else 'no'}",
            f"Processed: {len(self.results)}",
            f"Errors: {len(self.errors)}",
            "",
        ]
        for result in self.results:
            detail = f"[{result.status}] entry {result.index}: {result.action}"
            if result.title:
                detail += f" | {result.title}"
            if result.collection_name:
                detail += f" | collection={result.collection_name}"
            if result.item_key:
                detail += f" | key={result.item_key}"
            if result.message:
                detail += f" | {result.message}"
            lines.append(detail)
        if self.errors:
            lines.append("")
            lines.append("Error details:")
            for error in self.errors:
                lines.append(f"- entry {error.index}: {error.message}")
                if error.raw_block:
                    lines.append("  retry block:")
                    for block_line in error.raw_block.splitlines():
                        lines.append(f"    {block_line}")
        return "\n".join(lines)
