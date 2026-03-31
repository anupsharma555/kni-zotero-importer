from __future__ import annotations

import re
from typing import Iterable

from .models import ImportEntry, ImportResult, ParsedImportEntry


FIELD_ALIASES = {
    "collection": "collection_name",
    "collections": "collection_name",
    "folder": "collection_name",
    "group": "collection_name",
    "pmid": "pmid",
    "pubmed id": "pmid",
    "pubmedid": "pmid",
    "title": "title",
    "article title": "title",
    "tags": "tags",
    "tag": "tags",
    "keywords": "tags",
    "note": "note",
    "notes": "note",
    "summary": "note",
    "type": "item_type",
    "item type": "item_type",
    "source type": "item_type",
    "url": "url",
    "link": "url",
    "doi": "doi",
    "isbn": "isbn",
}

NULLISH_VALUES = {"", "n/a", "na", "none", "null", "not available", "not_applicable"}


def _split_blocks(text: str) -> list[str]:
    blocks: list[list[str]] = []
    current: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if line.strip() == "END":
            break
        if not line.strip():
            if current:
                blocks.append(current)
                current = []
            continue
        current.append(line)
    if current:
        blocks.append(current)
    return ["\n".join(block) for block in blocks]


def _append_value(store: dict[str, list[str]], field_name: str, value: str) -> None:
    store.setdefault(field_name, []).append(value.strip())


def _normalize_tags(raw_values: Iterable[str]) -> list[str]:
    tags: list[str] = []
    seen: set[str] = set()
    for raw_value in raw_values:
        for part in raw_value.split(";"):
            cleaned = part.strip()
            if cleaned and cleaned.lower() not in seen:
                tags.append(cleaned)
                seen.add(cleaned.lower())
    return tags


def parse_entries(text: str) -> list[ImportEntry]:
    parsed, errors = parse_entries_with_errors(text)
    if errors:
        first = errors[0]
        raise ValueError(first.message)
    return [item.entry for item in parsed]


def parse_entries_with_errors(text: str) -> tuple[list[ParsedImportEntry], list[ImportResult]]:
    entries: list[ImportEntry] = []
    parsed_entries: list[ParsedImportEntry] = []
    errors: list[ImportResult] = []
    for index, block in enumerate(_split_blocks(text), start=1):
        try:
            entry = _parse_block(block)
            entries.append(entry)
            parsed_entries.append(ParsedImportEntry(index=index, entry=entry))
        except Exception as exc:
            errors.append(
                ImportResult(
                    index=index,
                    status="error",
                    action="failed",
                    collection_name=_guess_field_value(block, "collection_name"),
                    title=_guess_field_value(block, "title"),
                    message=str(exc),
                    raw_block=block,
                )
            )
    return parsed_entries, errors


def _parse_block(block: str) -> ImportEntry:
    raw_fields: dict[str, list[str]] = {}
    if _looks_like_compact_block(block) and _try_parse_compact_block(block, raw_fields):
        return _build_entry(raw_fields, block)
    current_field = ""
    for line in block.splitlines():
        parsed = _parse_labeled_line(line)
        if parsed is not None:
            alias, value = parsed
            current_field = alias
            _append_value(raw_fields, alias, value)
            continue
        if not current_field:
            raise ValueError(f"Unable to parse line: {line}")
        _append_value(raw_fields, current_field, line)
    return _build_entry(raw_fields, block)


def _build_entry(raw_fields: dict[str, list[str]], block: str) -> ImportEntry:
    collection_name = " ".join(raw_fields.get("collection_name", [])).strip()
    if not collection_name:
        raise ValueError(f"Each entry must include Collection. Problem block:\n{block}")

    pmid = _normalize_optional_identifier(" ".join(raw_fields.get("pmid", [])).strip())

    entry = ImportEntry(
        collection_name=collection_name,
        pmid=pmid,
        title=" ".join(raw_fields.get("title", [])).strip(),
        tags=_normalize_tags(raw_fields.get("tags", [])),
        note="\n".join(raw_fields.get("note", [])).strip(),
        item_type=" ".join(raw_fields.get("item_type", [])).strip(),
        url=" ".join(raw_fields.get("url", [])).strip(),
        doi=" ".join(raw_fields.get("doi", [])).strip(),
        isbn=" ".join(raw_fields.get("isbn", [])).strip(),
        raw_block=block,
    )
    if entry.pmid and not entry.pmid.isdigit():
        raise ValueError(f"PMID must be numeric: {entry.pmid}")
    if not entry.pmid and not entry.title:
        raise ValueError("Each entry must include either PMID or Title.")
    return entry


def _try_parse_compact_block(block: str, raw_fields: dict[str, list[str]]) -> bool:
    lines = [line.strip() for line in block.splitlines() if line.strip()]
    if len(lines) != 1:
        return False

    parts = [part.strip() for part in lines[0].split("|") if part.strip()]
    if not parts:
        return False

    first = parts[0]
    compact_collection = first
    first_parsed = _parse_labeled_line(first)
    if first_parsed is not None:
        alias, value = first_parsed
        if alias != "collection_name":
            return False
        compact_collection = value.strip()
    else:
        compact_collection = _strip_leading_enumerator(first)
    if not compact_collection:
        return False
    raw_fields["collection_name"] = [compact_collection]

    for part in parts[1:]:
        parsed = _parse_labeled_line(part, compact_mode=True)
        if parsed is None:
            raise ValueError(f"Unable to parse compact field: {part}")
        alias, value = parsed
        _append_value(raw_fields, alias, value)
    return True


def _looks_like_compact_block(block: str) -> bool:
    lines = [line.strip() for line in block.splitlines() if line.strip()]
    if len(lines) != 1:
        return False
    parts = [part.strip() for part in lines[0].split("|") if part.strip()]
    if len(parts) < 2:
        return False
    first = parts[0]
    first_parsed = _parse_labeled_line(first)
    if first_parsed is not None:
        return first_parsed[0] == "collection_name"
    compact_collection = _strip_leading_enumerator(first)
    return bool(compact_collection)


def _strip_leading_enumerator(value: str) -> str:
    cleaned = value.strip()
    while cleaned and cleaned[0].isdigit():
        cleaned = cleaned[1:]
    return cleaned.lstrip(").:- ").strip()


def _normalize_label(label: str) -> str:
    lowered = label.strip().lower()
    lowered = re.sub(r"^[\-\*\u2022]+\s*", "", lowered)
    lowered = re.sub(r"\s+", " ", lowered)
    return lowered.strip(" :.-")


def _parse_labeled_line(line: str, compact_mode: bool = False) -> tuple[str, str] | None:
    stripped = line.strip()
    if not stripped:
        return None

    stripped = re.sub(r"^[\-\*\u2022]+\s*", "", stripped)
    stripped = re.sub(r"^\d+[\)\.\-:]\s*", "", stripped)
    match = re.match(r"^([A-Za-z][A-Za-z0-9 /&_()-]*?)\s*[:=-]\s*(.+)$", stripped)
    if match:
        label = _normalize_label(match.group(1))
        alias = FIELD_ALIASES.get(label)
        if alias:
            return alias, match.group(2).strip()

    if compact_mode:
        match = re.match(r"^([A-Za-z][A-Za-z0-9 /&_()-]*?)\s+(.+)$", stripped)
        if match:
            label = _normalize_label(match.group(1))
            alias = FIELD_ALIASES.get(label)
            if alias:
                return alias, match.group(2).strip()
    return None


def _normalize_optional_identifier(value: str) -> str:
    normalized = value.strip()
    if normalized.lower() in NULLISH_VALUES:
        return ""
    return normalized


def _guess_field_value(block: str, field_alias: str) -> str:
    for line in block.splitlines():
        parsed = _parse_labeled_line(line)
        if parsed is None:
            continue
        alias, value = parsed
        if alias == field_alias:
            return value.strip()
    return ""
