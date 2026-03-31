from __future__ import annotations

import csv
import os
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from .cache_store import CacheStore
from .collection_map import CollectionResolver
from .dedupe import ItemIndex, find_duplicate, normalize_title
from .models import ExistingItem, ImportEntry, ImportReport, ImportResult, PubMedRecord, ResolvedCollection
from .parser import parse_entries_with_errors
from .pubmed_client import PubMedClient
from .zotero_client import ZoteroClient


class ImportRuntime:
    def __init__(self, zotero: ZoteroClient, pubmed: PubMedClient, cache_store: CacheStore | None = None) -> None:
        self.zotero = zotero
        self.pubmed = pubmed
        self.cache_store = cache_store
        self._resolver: CollectionResolver | None = None
        self._item_index: ItemIndex | None = None
        self._collections_loaded = False
        self._items_loaded = False

    @classmethod
    def from_env(cls) -> "ImportRuntime":
        load_dotenv()
        cache_root = Path(__file__).resolve().parents[1] / ".cache"
        cache_store = CacheStore(cache_root)
        zotero = ZoteroClient(
            library_id=os.environ.get("ZOTERO_LIBRARY_ID", "").strip(),
            api_key=os.environ.get("ZOTERO_API_KEY", "").strip(),
            library_type=os.environ.get("ZOTERO_LIBRARY_TYPE", "user").strip() or "user",
        )
        pubmed = PubMedClient(
            api_key=os.environ.get("NCBI_API_KEY", "").strip(),
            tool=os.environ.get("NCBI_TOOL", "KNI_Zotero_Importer").strip() or "KNI_Zotero_Importer",
            email=os.environ.get("NCBI_EMAIL", "").strip(),
        )
        runtime = cls(zotero=zotero, pubmed=pubmed, cache_store=cache_store)
        runtime._seed_from_disk_cache()
        return runtime

    @property
    def resolver(self) -> CollectionResolver:
        if self._resolver is None:
            collections = self.zotero.get_all_collections()
            self._resolver = CollectionResolver(collections)
            self._collections_loaded = True
            self._persist_collections_cache(collections)
        return self._resolver

    @property
    def item_index(self) -> ItemIndex:
        if self._item_index is None:
            items = self.zotero.get_all_top_level_items()
            self._item_index = ItemIndex(items)
            self._items_loaded = True
            self._persist_items_cache(items)
        return self._item_index

    def sync_saved_item(self, item: ExistingItem) -> None:
        self.item_index.add_or_replace(item)
        self._persist_items_cache(self.item_index.items)

    def refresh(self) -> None:
        collections = self.zotero.get_all_collections()
        items = self.zotero.get_all_top_level_items()
        self._resolver = CollectionResolver(collections)
        self._item_index = ItemIndex(items)
        self._collections_loaded = True
        self._items_loaded = True
        self._persist_collections_cache(collections)
        self._persist_items_cache(items)

    def refresh_collections(self) -> dict[str, str]:
        self.zotero._collections_cache = None
        collections = self.zotero.get_all_collections()
        self._resolver = CollectionResolver(collections)
        self._collections_loaded = True
        self._persist_collections_cache(collections)
        return collections

    def _seed_from_disk_cache(self) -> None:
        if self.cache_store is None:
            return
        collections = self.cache_store.load_collections(max_age_seconds=24 * 60 * 60)
        if collections:
            self.zotero.seed_collections_cache(collections)
            self._resolver = CollectionResolver(collections)
            self._collections_loaded = True
        items = self.cache_store.load_items(max_age_seconds=10 * 60)
        if items:
            self.zotero.seed_items_cache(items)
            self._item_index = ItemIndex(items)
            self._items_loaded = True

    def _persist_collections_cache(self, collections: dict[str, str]) -> None:
        if self.cache_store is not None:
            self.cache_store.save_collections(collections)

    def _persist_items_cache(self, items: list[ExistingItem]) -> None:
        if self.cache_store is not None:
            self.cache_store.save_items(items)


def run_import_from_text(text: str, dry_run: bool = False, runtime: ImportRuntime | None = None) -> ImportReport:
    return run_import_from_text_with_options(
        text=text,
        dry_run=dry_run,
        runtime=runtime,
        create_missing_collections=False,
    )


def run_import_from_text_with_options(
    text: str,
    dry_run: bool = False,
    runtime: ImportRuntime | None = None,
    create_missing_collections: bool = False,
) -> ImportReport:
    parsed_entries, errors = parse_entries_with_errors(text)
    runtime = runtime or ImportRuntime.from_env()

    results: list[ImportResult] = list(errors)
    errors = list(errors)

    for parsed_entry in parsed_entries:
        index = parsed_entry.index
        entry = parsed_entry.entry
        try:
            result = _process_entry(
                entry=entry,
                index=index,
                runtime=runtime,
                dry_run=dry_run,
                create_missing_collections=create_missing_collections,
            )
            results.append(result)
        except Exception as exc:
            error = ImportResult(
                index=index,
                status="error",
                action="failed",
                collection_name=entry.collection_name,
                title=entry.title,
                message=str(exc),
                raw_block=entry.raw_block,
            )
            results.append(error)
            errors.append(error)

    report = ImportReport(results=results, errors=errors, dry_run=dry_run)
    _write_logs(report)
    return report


def _process_entry(
    entry: ImportEntry,
    index: int,
    runtime: ImportRuntime,
    dry_run: bool,
    create_missing_collections: bool,
) -> ImportResult:
    resolved_collection, collection_message = _resolve_or_create_collection(
        runtime=runtime,
        requested_name=entry.collection_name,
        allow_create_missing=create_missing_collections,
        dry_run=dry_run,
    )
    entry_type = entry.resolved_item_type()
    record = runtime.pubmed.fetch_by_pmid(entry.pmid) if entry.pmid else None
    if entry.pmid and record is None and not entry.title:
        raise ValueError(f"Unable to fetch PubMed metadata for PMID {entry.pmid}")

    duplicate = find_duplicate(entry, record, runtime.item_index)
    target_title = entry.title or (record.title if record else "")

    if duplicate:
        item_key = duplicate.key
        update_payload = _build_update_payload(duplicate, entry, record, resolved_collection.key)
        notes_to_add = _note_needed(runtime.zotero, duplicate.key, entry.note) if entry.note else False
        if dry_run:
            action = "would-update"
        else:
            if update_payload:
                saved = runtime.zotero.update_item(update_payload)
                duplicate = _existing_from_saved(saved)
                runtime.sync_saved_item(duplicate)
                item_key = duplicate.key
            if notes_to_add:
                runtime.zotero.create_child_note(duplicate.key, entry.note)
            action = "updated" if update_payload or notes_to_add else "skipped"
        return ImportResult(
            index=index,
            status="ok",
            action=action,
            collection_name=resolved_collection.resolved_name,
            item_key=item_key,
            title=target_title or duplicate.title,
            message=_combine_messages("matched existing item", collection_message),
        )

    create_payload = _build_create_payload(runtime.zotero, entry, record, resolved_collection.key, entry_type)
    if dry_run:
        return ImportResult(
            index=index,
            status="ok",
            action="would-create",
            collection_name=resolved_collection.resolved_name,
            title=target_title,
            message=_combine_messages("new item", collection_message),
        )

    saved = runtime.zotero.create_item(create_payload)
    created = _existing_from_saved(saved)
    runtime.sync_saved_item(created)
    if entry.note:
        runtime.zotero.create_child_note(created.key, entry.note)
    return ImportResult(
        index=index,
        status="ok",
        action="created",
        collection_name=resolved_collection.resolved_name,
        item_key=created.key,
        title=target_title,
        message=_combine_messages("new item", collection_message),
    )


def _resolve_or_create_collection(
    runtime: ImportRuntime,
    requested_name: str,
    allow_create_missing: bool,
    dry_run: bool,
) -> tuple[ResolvedCollection, str]:
    try:
        return runtime.resolver.resolve(requested_name), ""
    except ValueError:
        if not allow_create_missing:
            raise

    normalized_name = requested_name.strip()
    if not normalized_name:
        raise ValueError("Collection name cannot be empty.")

    if dry_run:
        return (
            ResolvedCollection(
                requested_name=requested_name,
                resolved_name=normalized_name,
                key="DRYRUN00",
            ),
            "collection would be created",
        )

    runtime.zotero.create_collection(normalized_name)
    collections = runtime.zotero.get_all_collections()
    runtime._resolver = CollectionResolver(collections)
    runtime._persist_collections_cache(collections)
    return runtime.resolver.resolve(normalized_name), "collection created"


def _combine_messages(primary: str, secondary: str) -> str:
    if not secondary:
        return primary
    return f"{primary}; {secondary}"


def _build_create_payload(
    zotero: ZoteroClient,
    entry: ImportEntry,
    record: PubMedRecord | None,
    collection_key: str,
    item_type: str,
) -> dict[str, Any]:
    template = zotero.get_item_template(item_type)
    template["collections"] = [collection_key]
    template["tags"] = [{"tag": tag} for tag in entry.tags]

    if item_type == "journalArticle" and record is not None:
        _apply_if_supported(template, "title", record.title or entry.title)
        _apply_if_supported(template, "creators", record.creators)
        _apply_if_supported(template, "publicationTitle", record.journal)
        _apply_if_supported(template, "volume", record.volume)
        _apply_if_supported(template, "issue", record.issue)
        _apply_if_supported(template, "pages", record.pages)
        _apply_if_supported(template, "date", record.date)
        _apply_if_supported(template, "DOI", entry.doi or record.doi)
        _apply_if_supported(template, "url", entry.url or record.url)
        _apply_if_supported(template, "abstractNote", record.abstract)
        template["extra"] = _merge_extra(template.get("extra", ""), pmid=record.pmid, pmcid=record.pmcid)
        return template

    _apply_if_supported(template, "title", entry.title or (record.title if record else ""))
    _apply_if_supported(template, "url", entry.url)
    _apply_if_supported(template, "DOI", entry.doi or (record.doi if record else ""))
    _apply_if_supported(template, "ISBN", entry.isbn)
    if item_type in {"webpage", "blogPost"}:
        _apply_if_supported(template, "accessDate", datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    extra = _merge_extra(template.get("extra", ""), pmid=entry.pmid, doi=entry.doi, isbn=entry.isbn)
    if extra:
        template["extra"] = extra
    return template


def _build_update_payload(
    existing: ExistingItem,
    entry: ImportEntry,
    record: PubMedRecord | None,
    collection_key: str,
) -> dict[str, Any] | None:
    payload: dict[str, Any] = {"key": existing.key, "version": existing.version}
    changed = False

    existing_collections = list(existing.data.get("collections", []))
    if collection_key not in existing_collections:
        payload["collections"] = existing_collections + [collection_key]
        changed = True

    existing_tags = {tag.get("tag", "").strip().lower() for tag in existing.data.get("tags", [])}
    missing_tags = [tag for tag in entry.tags if tag.lower() not in existing_tags]
    if missing_tags:
        payload["tags"] = list(existing.data.get("tags", [])) + [{"tag": tag} for tag in missing_tags]
        changed = True

    new_extra = _merge_extra(
        existing.data.get("extra", ""),
        pmid=entry.pmid or (record.pmid if record else ""),
        pmcid=record.pmcid if record else "",
        doi=entry.doi or (record.doi if record else ""),
        isbn=entry.isbn,
    )
    if new_extra != (existing.data.get("extra", "") or ""):
        payload["extra"] = new_extra
        changed = True

    if not existing.data.get("DOI") and (entry.doi or (record.doi if record else "")):
        payload["DOI"] = entry.doi or (record.doi if record else "")
        changed = True

    return payload if changed else None


def _apply_if_supported(payload: dict[str, Any], key: str, value: Any) -> None:
    if key in payload and value not in ("", None, [], {}):
        payload[key] = value


def _merge_extra(existing_extra: str, pmid: str = "", pmcid: str = "", doi: str = "", isbn: str = "") -> str:
    lines = [line.strip() for line in (existing_extra or "").splitlines() if line.strip()]
    existing_labels = {line.split(":", 1)[0].strip().lower() for line in lines if ":" in line}
    additions = []
    if pmid and "pmid" not in existing_labels:
        additions.append(f"PMID: {pmid}")
    if pmcid and "pmcid" not in existing_labels:
        additions.append(f"PMCID: {pmcid}")
    if doi and "doi" not in existing_labels:
        additions.append(f"DOI: {doi}")
    if isbn and "isbn" not in existing_labels:
        additions.append(f"ISBN: {isbn}")
    merged = lines + additions
    return "\n".join(merged).strip()


def _note_needed(zotero: ZoteroClient, parent_key: str, note_text: str) -> bool:
    note_norm = normalize_title(note_text)
    for existing_note in zotero.get_child_notes(parent_key):
        if normalize_title(_strip_html(existing_note)) == note_norm:
            return False
    return True


def _strip_html(value: str) -> str:
    return value.replace("<p>", "\n").replace("</p>", "").replace("<br>", "\n").replace("<br/>", "\n")


def _existing_from_saved(saved: dict[str, Any]) -> ExistingItem:
    data = saved["data"]
    return ExistingItem(
        key=saved["key"],
        version=int(saved["version"]),
        item_type=data.get("itemType", ""),
        data=data,
        title=data.get("title", ""),
        title_norm=normalize_title(data.get("title", "")),
        pmid=_extract_extra(data, "PMID"),
        doi=(data.get("DOI") or _extract_extra(data, "DOI")).strip(),
        isbn=(data.get("ISBN") or _extract_extra(data, "ISBN")).strip(),
    )


def _extract_extra(data: dict[str, Any], label: str) -> str:
    for line in (data.get("extra", "") or "").splitlines():
        if ":" not in line:
            continue
        left, right = line.split(":", 1)
        if left.strip().lower() == label.lower():
            return right.strip()
    return ""


def _write_logs(report: ImportReport) -> None:
    logs_dir = Path(__file__).resolve().parents[1] / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    import_report = logs_dir / "import_report.csv"
    errors_report = logs_dir / "errors.csv"
    _write_csv(import_report, report.results)
    _write_csv(errors_report, report.errors)


def _write_csv(path: Path, rows: list[ImportResult]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["timestamp", "index", "status", "action", "collection_name", "item_key", "title", "message"],
        )
        writer.writeheader()
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        for row in rows:
            payload = asdict(row)
            payload["timestamp"] = timestamp
            writer.writerow(payload)
